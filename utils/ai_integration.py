import json
import logging
import os
import google.generativeai as genai
from typing import Tuple, Dict, Any, List, Optional

# Настройка логирования должна быть в main.py, чтобы применяться глобально
# Если она здесь, она может быть переопределена или не примениться к другим модулям.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logging.info("AI Integration: Gemini API Key успешно сконфигурирован.")
    except Exception as e:
        logging.error(f"AI Integration: Ошибка при конфигурации Gemini API ключа: {e}")
        GEMINI_API_KEY = None
else:
    logging.warning("AI Integration: GEMINI_API_KEY не найден. API Gemini не будет работать.")


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
        return None, "Ошибка: API ключ для AI не найден или не работает."

    logging.info(f"AI Integration: Получены данные от пользователя: {user_data_raw}")
    prepared = _prepare_user_data_for_prompt(user_data_raw)
    # Для отладки можно раскомментировать следующую строку или изменить уровень логирования на DEBUG
    # logging.info(f"AI Integration: Prepared data for prompt: {json.dumps(prepared, ensure_ascii=False, indent=2)}")

    # ВАЖНО: Для f-string, чтобы получить литеральную фигурную скобку { в итоговой строке, нужно писать {{.
    # Соответственно, } это }}.
    prompt_template = f"""<task>
Разработать AI-ассистента для путешественников — «Travel Bot», который генерирует персонализированные рекомендации.
</task>

## Инструкция для AI
Ты — Travel Bot. Твоя задача - вернуть ТОЛЬКО JSON объект. 
**ВАЖНО: Весь твой ответ, включая все текстовые значения в JSON и в textual_summary, должен быть СТРОГО на языке, указанном в поле `user_language` во Входных данных.**
Этот JSON объект должен содержать два ключа верхнего уровня: "structured_recommendations" (который содержит JSON как в примере ниже) и "textual_summary" (который содержит сопроводительный текстовый совет для пользователя).
Постарайся включить поля "coordinates" (список из двух чисел [широта, долгота]) и "booking_link" (URL или строковый литерал "null", если ссылки нет) для каждой рекомендации, где это уместно.

### Входные данные от пользователя
user_location: "{prepared['user_location']}"
user_preferences: {json.dumps(prepared['user_preferences'], ensure_ascii=False)}
trip_duration_text: "{prepared['trip_duration_text']}"
transport_preferences: {json.dumps(prepared['transport_preferences'], ensure_ascii=False)}
history: {json.dumps(prepared['history'], ensure_ascii=False)}
user_language: "{prepared['user_language']}"

### Ожидаемый формат твоего ответа (ТОЛЬКО этот JSON):
{{  // Открывающая скобка для всего JSON
  "structured_recommendations": {{ // Открывающая для structured_recommendations
    "query_summary": {{ // Открывающая для query_summary
      "location_interpreted": "<Название города на языке user_language>",
      "trip_days": "<Кол-во дней, например '3 дня'>",
      "main_interests": ["<интерес1 на языке user_language>", "<интерес2 на языке user_language>"]
    }}, // Закрывающая для query_summary
    "recommendations": [
      {{ // Открывающая для первой рекомендации
        "id": "rec_hotel_001",
        "type": "hotel",
        "name": "<Название отеля на языке user_language>",
        "address": "<Адрес отеля на языке user_language>",
        "coordinates": [48.8584, 2.2945], 
        "description": "<Описание отеля на языке user_language (2-3 предложения)>",
        "details": {{ "stars": 4, "amenities": ["Wi-Fi", "<завтрак на языке user_language>"] }},
        "price_estimate": "<Цена, например 'От 150 EUR/ночь'>",
        "rating": 4.5,
        "booking_link": "https://example.com/booking/hotel_example", 
        "images": ["https://example.com/image_hotel_1.jpg"],
        "opening_hours": "круглосуточно" 
      }}, // Закрывающая для первой рекомендации
      {{ // Открывающая для второй рекомендации
        "id": "rec_restaurant_001",
        "type": "restaurant",
        "name": "<Название ресторана на языке user_language>",
        "address": "<Адрес ресторана на языке user_language>",
        "coordinates": [48.8580, 2.2950],
        "description": "<Описание ресторана на языке user_language>",
        "details": {{ "cuisine_type": ["<кухня1 на языке user_language>", "<кухня2 на языке user_language>"], "average_bill": "<Средний чек, например '30-50 EUR'>"}},
        "price_estimate": "null", 
        "rating": 4.2,
        "booking_link": "null", 
        "images": ["https://example.com/image_restaurant_1.jpg"],
        "opening_hours": "12:00 - 23:00" 
      }}  // Закрывающая для второй рекомендации
    ] // Закрывающая для списка recommendations
  }}, // Закрывающая для structured_recommendations
  "textual_summary": "<Твой сопроводительный текстовый совет (2-3 абзаца) на языке user_language.>"
}}  // Закрывающая для всего JSON
"""
    # Для отладки полного промта, можно раскомментировать:
    # logging.info(f"DEBUG PROMPT:\n{prompt_template}")

    try:
        model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest')
        logging.info("AI Integration: Отправка запроса к Gemini...")
        response = await model.generate_content_async(prompt_template)  # Исправлено: передаем prompt_template

        ai_text = ''
        if hasattr(response, 'text') and response.text:
            ai_text = response.text
        elif hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                ai_text += getattr(part, 'text', '')

        if not ai_text:
            try:
                if response.candidates and response.candidates[0].content.parts:
                    ai_text = "".join(p.text for p in response.candidates[0].content.parts if hasattr(p, 'text'))
            except (AttributeError, IndexError, TypeError):
                pass

        if not ai_text:
            logging.error(f"AI Integration: Ответ Gemini пустой или не содержит текста. Сырой ответ: {response}")
            return None, "AI не смог сгенерировать текстовый ответ."

        ai_text = ai_text.strip()
        if ai_text.startswith('```json'):
            ai_text = ai_text[len('```json'):]
        if ai_text.endswith('```'):
            ai_text = ai_text[:-len('```')]
        ai_text = ai_text.strip()

        logging.info(f"AI Integration: Текст от Gemini (ожидаем JSON, первые 300 символов): {ai_text[:300]}...")

        data = json.loads(ai_text)
        structured = data.get('structured_recommendations')
        summary = data.get('textual_summary')

        if not isinstance(structured, dict) or not isinstance(summary, str):
            logging.error(
                f"AI Integration: Неверный формат ключей в JSON от Gemini. structured: {type(structured)}, summary: {type(summary)}")
            return None, "AI вернул данные в неверном формате (неверные типы ключей)"

        logging.info("AI Integration: Успешно получили и распарсили рекомендации от Gemini.")
        return structured, summary

    except json.JSONDecodeError as e:
        logging.error(f"AI Integration: Ошибка декодирования AI-ответа (не JSON): {e}. Ответ был: {ai_text}")
        return None, f"AI вернул некорректный JSON. Попробуйте снова. (Ошибка: {e})"
    except Exception as e:
        logging.error(f"AI Integration: Непредвиденная ошибка при работе с Gemini: {e}", exc_info=True)
        return None, f"Непредвиденная ошибка при обращении к AI: {type(e).__name__}"