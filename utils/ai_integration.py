import json
import logging
import os
import google.generativeai as genai
from typing import Tuple, Dict, Any, List, Optional

# Настройка логирования должна быть в main.py (глобально, до импортов)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logging.info("AI Integration: Gemini API Key успешно сконфигурирован.")
    except Exception as e:
        logging.error(f"AI Integration: Ошибка при конфигурации Gemini API ключа: {e}", exc_info=True)
        GEMINI_API_KEY = None
else:
    logging.warning("AI Integration: GEMINI_API_KEY не найден в переменных окружения. API Gemini не будет работать.")


def _prepare_user_data_for_prompt(user_data_raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Подготавливает данные пользователя для вставки в промт.
    """
    prepared_data: Dict[str, Any] = {}

    location_value = "не указано"  # Значение по умолчанию
    if user_data_raw.get('user_location_geo'):
        lat, lon = user_data_raw['user_location_geo']
        # Для Gemini лучше передать что-то, что он может геокодировать, если нет названия города.
        # Строка "координаты: lat,lon" может быть менее эффективна, чем просто передача lat,lon
        # и просьба определить местоположение. Однако, наш промт сейчас ожидает строку.
        # Оставим пока так, но это место для возможного улучшения (например, если бы AI мог принимать объект location).
        location_value = f"координаты: {lat},{lon}"
    elif user_data_raw.get('user_location_text'):
        location_value = user_data_raw.get('user_location_text')
    prepared_data['user_location'] = location_value

    interests_list: List[str] = []
    if user_data_raw.get('user_interests_text'):
        interests_list = [i.strip() for i in user_data_raw['user_interests_text'].split(',') if i.strip()]

    prepared_data['user_preferences'] = {
        "interests": interests_list,
        "budget": user_data_raw.get('user_budget', "mid"),
        "dietary_restrictions": user_data_raw.get('user_dietary_restrictions', []),
        "accessibility_needs": user_data_raw.get('user_accessibility_needs', []),
        "preferred_pace": user_data_raw.get('user_preferred_pace', "moderate"),
    }

    prepared_data['trip_duration_text'] = user_data_raw.get('user_trip_dates_text', "не указано")

    transport_list: List[str] = []
    if user_data_raw.get('user_transport_prefs_text'):
        transport_list = [t.strip() for t in user_data_raw['user_transport_prefs_text'].split(',') if t.strip()]
    prepared_data['transport_preferences'] = transport_list

    prepared_data['history'] = user_data_raw.get('history', [])  # Пока всегда пустой
    prepared_data['user_language'] = user_data_raw.get('user_language', 'ru')

    return prepared_data


async def get_travel_recommendations(
        user_data_raw: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Запрашивает рекомендации у модели Gemini.
    Возвращает кортеж (structured_recommendations, textual_summary) или (None, error_message).
    """
    if not GEMINI_API_KEY:
        logging.error("AI Integration: API ключ для Gemini не настроен или невалиден.")
        return None, "Ошибка конфигурации: API ключ для AI не найден или не работает. Проверьте настройки."

    logging.info(f"AI Integration: Получены сырые данные от пользователя: {user_data_raw}")
    prepared = _prepare_user_data_for_prompt(user_data_raw)

    # Для отладки можно раскомментировать, если уровень логирования INFO
    # logging.info(f"AI Integration: Prepared data for prompt: {json.dumps(prepared, ensure_ascii=False, indent=2)}")

    prompt_template = f"""<task>
Ты — «Travel Bot», AI-ассистент для путешественников. Твоя задача — генерировать персонализированные рекомендации.
</task>

## ОБЩИЕ ИНСТРУКЦИИ ДЛЯ ТЕБЯ, AI:
1.  **ФОРМАТ ОТВЕТА**: Ты ДОЛЖЕН вернуть ТОЛЬКО один JSON объект. Никакого текста до или после JSON, никакой Markdown разметки (типа ```json ... ```).
2.  **ЯЗЫК ОТВЕТА**: АБСОЛЮТНО ВЕСЬ текст в твоем ответе (включая все значения строковых полей в JSON и текст в `textual_summary`) ДОЛЖЕН БЫТЬ СТРОГО на языке, указанном в поле `user_language` во Входных данных.
3.  **СТРУКТУРА JSON**: JSON объект должен иметь два ключа верхнего уровня:
    *   `"structured_recommendations"`: JSON объект, содержащий `query_summary` и список `recommendations`.
    *   `"textual_summary"`: Строка с дружелюбным сопроводительным текстом для пользователя (2-4 абзаца) на языке `user_language`.
4.  **КАЧЕСТВО РЕКОМЕНДАЦИЙ**:
    *   Предлагай РАЗНООБРАЗНЫЕ и АКТУАЛЬНЫЕ варианты.
    *   Если по какому-то критерию качественных вариантов мало, лучше предложи меньше, но лучших, или честно укажи на это в `textual_summary`.
    *   Старайся предлагать не менее 1-2 вариантов для отелей и ресторанов, и 2-3 для достопримечательностей/активностей, если это релевантно.

### Входные данные от пользователя (Используй их для генерации)
user_location: "{prepared['user_location']}"
user_preferences: {json.dumps(prepared['user_preferences'], ensure_ascii=False)}
trip_duration_text: "{prepared['trip_duration_text']}"
transport_preferences: {json.dumps(prepared['transport_preferences'], ensure_ascii=False)}
history: {json.dumps(prepared['history'], ensure_ascii=False)}
user_language: "{prepared['user_language']}"

### ДЕТАЛЬНАЯ СПЕЦИФИКАЦИЯ для JSON объекта в "structured_recommendations"

#### 1. Поле `query_summary` (объект):
- `"location_interpreted"`: Строка. Название города/региона, которое ты понял из `user_location` (на языке `user_language`).
- `"trip_days"`: Строка. Примерное количество дней поездки (например, "3 дня", "около недели") или JSON `null`, если неясно из `trip_duration_text`.
- `"main_interests"`: Список строк. Основные интересы пользователя, которые ты выделил (на языке `user_language`).

#### 2. Поле `recommendations` (список объектов):
Каждый объект в списке `recommendations` должен содержать СЛЕДУЮЩИЕ ПОЛЯ:
- `"id"`: Строка. Уникальный ID (латиница, цифры, подчеркивания, например, "hotel_le_grand_paris_01").
- `"type"`: Строка. Один из: "route", "hotel", "museum", "restaurant", "event", "activity".
- `"name"`: Строка. Название (на языке `user_language`).
- `"address"`: Строка. Полный адрес (на языке `user_language`, если применимо) или JSON `null`.
- `"coordinates"`: **Список из ДВУХ ЧИСЕЛ** [широта, долгота] (например, [48.8584, 2.2945]) ИЛИ JSON `null`, если точные координаты неизвестны. **НЕ используй строки типа "null" или ["null"]**.
- `"description"`: Строка. Краткое, привлекательное описание (2-4 предложения на языке `user_language`).
- `"details"`: JSON объект с дополнительной информацией, специфичной для `type`. Если деталей нет, используй пустой объект `{{}}`.
    - Для `"type": "route"`: `{{ "route_type": "<тип_маршрута>", "stops": [{{ "name": "<Название>", "coordinates": [lat,lon], "description": "<Описание>" }}] }}`
    - Для `"type": "hotel"`: `{{ "stars": <число_1_до_5_или_null>, "amenities": ["<удобство1>", "<удобство2>"] }}`
    - Для `"type": "restaurant"`: `{{ "cuisine_type": ["<кухня1>", "<кухня2>"], "average_bill": "<~счет>" }}`
    - Для `"type": "event"`: `{{ "event_dates": ["<YYYY-MM-DD>"], "ticket_info": "<билеты>" }}`
    - Для `"type": "museum"` или `"activity"`: `{{ "ticket_info": "<билеты>" }}` (если платно)
- `"distance_or_time"`: Строка (например, "500 м от центра", "3 часа") или JSON `null`.
- `"price_estimate"`: Строка (например, "бесплатно", "20-30 EUR") или JSON `null`.
- `"rating"`: Число от 1.0 до 5.0 или JSON `null`.
- `"opening_hours"`: Строка (например, "10:00-18:00, Вт-Сб") или JSON `null`.
- `"booking_link"`: **URL (строка) для бронирования/билетов (старайся найти РЕАЛЬНЫЙ URL) ИЛИ JSON `null`. НЕ используй строку "null".**
- `"images"`: **Список URL картинок (строки). Старайся найти 1-2 РЕАЛЬНЫХ URL. Если нет, верни ПУСТОЙ СПИСОК `[]`. НЕ используй строки типа "null" или ["null"] или недействительные URL.**

### Пример твоего ИДЕАЛЬНОГО ответа (ТОЛЬКО этот JSON, строго на языке `user_language`):
{{  // Начало всего JSON ответа AI
  "structured_recommendations": {{ // Начало structured_recommendations
    "query_summary": {{
      "location_interpreted": "Париж, Франция", 
      "trip_days": "3 дня",
      "main_interests": ["искусство", "история"]
    }},
    "recommendations": [
      {{ // Начало первой рекомендации
        "id": "hotel_paris_splendide_001",
        "type": "hotel",
        "name": "Отель Сплендид Париж",
        "address": "1 Rue de la Paix, Париж, Франция",
        "coordinates": [48.8697, 2.3306],
        "description": "Элегантный отель рядом с Вандомской площадью, предлагающий роскошные номера и первоклассный сервис.",
        "details": {{ "stars": 5, "amenities": ["Спа", "Ресторан для гурманов", "Wi-Fi"] }},
        "distance_or_time": "В центре города",
        "price_estimate": "От 400 EUR/ночь",
        "rating": 4.8,
        "opening_hours": "Круглосуточно",
        "booking_link": "https://www.example-hotel-splendide.com/booking",
        "images": ["https://upload.wikimedia.org/wikipedia/commons/a/a2/Hotel_Splendide_Royal_Roma.jpg"]
      }},
      {{ // Начало второй рекомендации
        "id": "museum_louvre_002",
        "type": "museum",
        "name": "Лувр",
        "address": "Rue de Rivoli, Париж, Франция",
        "coordinates": null, // Пример JSON null
        "description": "Один из крупнейших и самых известных художественных музеев мира.",
        "details": {{ "ticket_info": "От 17 EUR" }},
        "distance_or_time": null,
        "price_estimate": "17-22 EUR",
        "rating": 4.9,
        "opening_hours": "09:00–18:00, Вт - выходной",
        "booking_link": null, // Пример JSON null
        "images": [] // Пример пустого списка
      }}
    ]
  }}, // Конец structured_recommendations
  "textual_summary": "Для вашей поездки в Париж я подобрал несколько отличных вариантов. Рекомендую остановиться в отеле 'Сплендид' и, конечно, посетить Лувр. Приятного путешествия!"
}}  // Конец всего JSON ответа AI
"""
    # Для отладки полного промта:
    # logging.info(f"AI Integration DEBUG PROMPT:\n{prompt_template}")

    try:
        model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest')
        logging.info("AI Integration: Отправка запроса к Gemini...")

        response = await model.generate_content_async(prompt_template)

        ai_text = ''
        # Извлечение текста из ответа
        if hasattr(response, 'text') and response.text:
            ai_text = response.text
        elif hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                ai_text += getattr(part, 'text', '')
        elif hasattr(response, 'candidates') and response.candidates:
            try:
                if response.candidates[0].content.parts:
                    ai_text = "".join(p.text for p in response.candidates[0].content.parts if hasattr(p, 'text'))
            except (AttributeError, IndexError, TypeError):
                logging.warning("AI Integration: Не удалось извлечь текст из response.candidates.")
                pass

        if not ai_text:
            logging.error(
                f"AI Integration: Ответ Gemini пустой или не содержит извлекаемого текста. Сырой ответ: {response}")
            return None, "AI не смог сгенерировать текстовый ответ. Пожалуйста, проверьте логи."

        # Очистка от Markdown JSON обертки
        ai_text = ai_text.strip()
        if ai_text.startswith('```json'):
            ai_text = ai_text[len('```json'):].strip()
        if ai_text.endswith('```'):
            ai_text = ai_text[:-len('```')].strip()

        logging.info(
            f"AI Integration: Очищенный текст от Gemini (ожидаем JSON, первые 500 символов): {ai_text[:500]}...")

        try:
            data = json.loads(ai_text)
        except json.JSONDecodeError as e:
            logging.error(f"AI Integration: Ошибка декодирования JSON от Gemini: {e}. "
                          f"Ответ Gemini, который не удалось распарсить (первые 1000 символов):\n{ai_text[:1000]}")  # Выводим часть ответа
            return None, f"AI вернул некорректный JSON. (Ошибка: {e})"

        structured = data.get('structured_recommendations')
        summary = data.get('textual_summary')

        # Более строгие проверки типов
        if not isinstance(structured, dict):
            logging.error(
                f"AI Integration: 'structured_recommendations' отсутствует или не является словарем. Получено: {type(structured)}. Ответ: {data}")
            return None, "AI вернул 'structured_recommendations' в неожиданном формате."
        if not isinstance(summary, str):
            logging.error(
                f"AI Integration: 'textual_summary' отсутствует или не является строкой. Получено: {type(summary)}. Ответ: {data}")
            return None, "AI вернул 'textual_summary' в неожиданном формате."

        # Дополнительная проверка структуры structured_recommendations
        if not isinstance(structured.get("query_summary"), dict) or \
                not isinstance(structured.get("recommendations"), list):
            logging.error(
                f"AI Integration: Неверная внутренняя структура 'structured_recommendations'. Ответ: {structured}")
            return None, "AI вернул 'structured_recommendations' с неверной внутренней структурой."

        logging.info("AI Integration: Успешно получили и распарсили рекомендации от Gemini.")
        return structured, summary

    except Exception as e:
        logging.error(f"AI Integration: Непредвиденная ошибка при работе с Gemini API: {e}", exc_info=True)
        return None, f"Непредвиденная ошибка при обращении к AI: {type(e).__name__}"