import json
import logging
import os
import google.generativeai as genai
from typing import Tuple, Dict, Any, List, Optional

# Настройка логирования должна быть в main.py (глобально, до импортов)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

    location_value = "не указано"
    if user_data_raw.get('user_location_geo'):
        lat, lon = user_data_raw['user_location_geo']
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

    prepared_data['history'] = user_data_raw.get('history', [])
    prepared_data['user_language'] = user_data_raw.get('user_language', 'ru')  # По умолчанию русский

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

    # Для отладки подготовленных данных (можно изменить уровень логирования или раскомментировать)
    # logging.info(f"AI Integration: Prepared data for prompt: {json.dumps(prepared, ensure_ascii=False, indent=2)}")

    prompt_template = f"""<task>
Разработать AI-ассистента для путешественников «Travel Bot», который генерирует персонализированные рекомендации.
</task>

## Инструкция для AI
Ты — Travel Bot, дружелюбный и осведомленный гид.
Твоя ГЛАВНАЯ ЗАДАЧА — вернуть ТОЛЬКО JSON объект, без каких-либо вводных слов или markdown разметки типа ```json ... ```.
**КРИТИЧЕСКИ ВАЖНО: Весь твой ответ, включая АБСОЛЮТНО ВСЕ текстовые значения в JSON (такие как name, address, description, textual_summary, и любые другие строки), должен быть СТРОГО на языке, указанном в поле `user_language` во Входных данных.**

JSON объект должен содержать два ключа верхнего уровня:
1.  `"structured_recommendations"`: JSON объект со списком рекомендаций, как описано ниже.
2.  `"textual_summary"`: Строка с сопроводительным текстовым советом для пользователя (2-3 абзаца) на языке `user_language`.

### Входные данные от пользователя
user_location: "{prepared['user_location']}"
user_preferences: {json.dumps(prepared['user_preferences'], ensure_ascii=False)}
trip_duration_text: "{prepared['trip_duration_text']}"
transport_preferences: {json.dumps(prepared['transport_preferences'], ensure_ascii=False)}
history: {json.dumps(prepared['history'], ensure_ascii=False)}
user_language: "{prepared['user_language']}"

### Структура и содержание для "structured_recommendations"
Поле `query_summary` должно содержать:
- `location_interpreted`: Строка, название города/региона, которое ты понял (на языке `user_language`).
- `trip_days`: Строка, количество дней (например, "3 дня") или строковый литерал "null", если неясно.
- `main_interests`: Список основных интересов пользователя (строки на языке `user_language`).

Поле `recommendations` должно быть списком объектов. Каждый объект рекомендации должен иметь СЛЕДУЮЩИЕ ПОЛЯ:
- `id`: Уникальный строковый ID (латиница, цифры, подчеркивания, например "hotel_grand_123").
- `type`: Строка, тип рекомендации ("route", "hotel", "museum", "restaurant", "event", "activity").
- `name`: Строка, название объекта/маршрута (на языке `user_language`).
- `address`: Строка, адрес (на языке `user_language`, если применимо) или строковый литерал "null".
- `coordinates`: Список из двух чисел [широта, долгота] или строковый литерал "null".
- `description`: Строка, краткое описание (2-4 предложения на языке `user_language`).
- `details`: JSON объект с дополнительной информацией, специфичной для типа:
    - Для `"type": "route"`: {{ "route_type": "<пеший/автомобильный/велосипедный>", "stops": [{{ "name": "<Название остановки>", "coordinates": [lat,lon], "description": "<Описание>" }}] }}
    - Для `"type": "hotel"`: {{ "stars": <число_звезд_от_1_до_5_или_null>, "amenities": ["<удобство1>", "<удобство2>"] }}
    - Для `"type": "restaurant"`: {{ "cuisine_type": ["<тип_кухни1>", "<тип_кухни2>"], "average_bill": "<примерный_счет>" }}
    - Для `"type": "event"`: {{ "event_dates": ["<YYYY-MM-DD>"], "ticket_info": "<инфо_о_билетах>" }}
    - Для `"type": "museum"` или `"activity"` с билетами: {{ "ticket_info": "<инфо_о_билетах>" }}
    - Если деталей нет, используй пустой объект {{}}.
- `distance_or_time`: Строка (например, "5 км от центра", "3 часа на осмотр") или строковый литерал "null".
- `price_estimate`: Строка (например, "Вход свободный", "25 EUR", "100-150 USD/ночь") или строковый литерал "null".
- `rating`: Число от 1.0 до 5.0 или строковый литерал "null".
- `opening_hours`: Строка (например, "Пн-Пт: 10:00-19:00") или строковый литерал "null".
- `booking_link`: URL (строка) для бронирования/билетов или строковый литерал "null". Постарайся найти РЕАЛЬНЫЙ URL, если это возможно.
- `images`: Список URL картинок (строки) или пустой список []. Постарайся найти РЕАЛЬНЫЕ URL.

### Пример твоего ответа (ТОЛЬКО этот JSON, строго на языке `user_language`):
{{
  "structured_recommendations": {{
    "query_summary": {{
      "location_interpreted": "Париж, Франция", 
      "trip_days": "3 дня",
      "main_interests": ["искусство", "история"]
    }},
    "recommendations": [
      {{
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
        "images": ["https://example.com/splendide_facade.jpg", "https://example.com/splendide_room.jpg"]
      }},
      {{
        "id": "museum_louvre_002",
        "type": "museum",
        "name": "Лувр",
        "address": "Rue de Rivoli, Париж, Франция",
        "coordinates": [48.8606, 2.3376],
        "description": "Один из крупнейших и самых известных художественных музеев мира. Дом Моны Лизы и Венеры Милосской.",
        "details": {{ "ticket_info": "От 17 EUR, рекомендуется бронировать заранее" }},
        "distance_or_time": "Центр Парижа",
        "price_estimate": "17-22 EUR",
        "rating": 4.9,
        "opening_hours": "09:00–18:00, Закрыт по вторникам",
        "booking_link": "https://www.ticketlouvre.fr",
        "images": ["https://example.com/louvre_pyramid.jpg"]
      }}
    ]
  }},
  "textual_summary": "Для вашей поездки в Париж, я рекомендую остановиться в роскошном отеле 'Сплендид' и обязательно посетить всемирно известный музей Лувр. Не забудьте забронировать билеты в Лувр заранее, чтобы избежать очередей!"
}}
"""
    # Для отладки полного промта:
    # logging.info(f"AI Integration DEBUG PROMPT:\n{prompt_template}")

    try:
        model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest')
        logging.info("AI Integration: Отправка запроса к Gemini...")

        # Конфигурация генерации, если нужно управлять температурой или другими параметрами
        # generation_config = genai.types.GenerationConfig(temperature=0.7)
        # response = await model.generate_content_async(prompt_template, generation_config=generation_config)

        response = await model.generate_content_async(prompt_template)

        ai_text = ''
        # Более надежное извлечение текста
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
                pass  # ai_text останется пустым, если и здесь не найдем

        if not ai_text:
            logging.error(
                f"AI Integration: Ответ Gemini пустой или не содержит извлекаемого текста. Сырой ответ: {response}")
            return None, "AI не смог сгенерировать текстовый ответ. Пожалуйста, проверьте логи."

        # Очистка от Markdown JSON обертки
        ai_text = ai_text.strip()
        if ai_text.startswith('```json'):
            ai_text = ai_text[len('```json'):].strip()  # Убираем ```json и возможные пробелы/переносы
        if ai_text.endswith('```'):
            ai_text = ai_text[:-len('```')].strip()  # Убираем ``` и возможные пробелы/переносы

        logging.info(
            f"AI Integration: Очищенный текст от Gemini (ожидаем JSON, первые 500 символов): {ai_text[:500]}...")

        try:
            data = json.loads(ai_text)
        except json.JSONDecodeError as e:
            logging.error(f"AI Integration: Ошибка декодирования JSON от Gemini: {e}. "
                          f"Ответ Gemini, который не удалось распарсить:\n{ai_text}")
            return None, f"AI вернул некорректный JSON. (Ошибка: {e})"

        structured = data.get('structured_recommendations')
        summary = data.get('textual_summary')

        if not isinstance(structured, dict) or not isinstance(summary, str):
            logging.error(
                f"AI Integration: Неверный формат ключей в JSON от Gemini. "
                f"structured: {type(structured)}, summary: {type(summary)}. "
                f"Распарсенные данные: {data}"
            )
            return None, "AI вернул данные в неверном формате (неверные типы или отсутствуют ключи)"

        logging.info("AI Integration: Успешно получили и распарсили рекомендации от Gemini.")
        return structured, summary

    except Exception as e:
        logging.error(f"AI Integration: Непредвиденная ошибка при работе с Gemini API: {e}", exc_info=True)
        return None, f"Непредвиденная ошибка при обращении к AI: {type(e).__name__}"