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
        GEMINI_API_KEY = None  # Устанавливаем в None, чтобы последующие вызовы не пытались использовать невалидный ключ
else:
    logging.warning("AI Integration: GEMINI_API_KEY не найден в переменных окружения. API Gemini не будет работать.")


def _prepare_user_data_for_prompt(user_data_raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Подготавливает данные пользователя для вставки в промт.
    """
    prepared_data: Dict[str, Any] = {}

    location_value = "не указано"
    user_location_geo = user_data_raw.get('user_location_geo')
    user_location_text = user_data_raw.get('user_location_text')

    if user_location_geo and isinstance(user_location_geo, list) and len(user_location_geo) == 2:
        lat, lon = user_location_geo
        location_value = f"координаты: {lat},{lon}"
    elif user_location_text and isinstance(user_location_text, str) and user_location_text.strip():
        location_value = user_location_text
    prepared_data['user_location'] = location_value

    interests_list: List[str] = []
    user_interests_text = user_data_raw.get('user_interests_text')
    if user_interests_text and isinstance(user_interests_text, str) and user_interests_text.strip():
        interests_list = [i.strip() for i in user_interests_text.split(',') if i.strip()]

    prepared_data['user_preferences'] = {
        "interests": interests_list,
        "budget": user_data_raw.get('user_budget', "mid"),  # mid как дефолт если не указан
        # Добавляем проверку типов для остальных полей, если они могут быть не строками/списками
        "dietary_restrictions": user_data_raw.get('user_dietary_restrictions', []),
        "accessibility_needs": user_data_raw.get('user_accessibility_needs', []),
        "preferred_pace": user_data_raw.get('user_preferred_pace', "moderate"),
    }

    prepared_data['trip_duration_text'] = user_data_raw.get('user_trip_dates_text', "не указано")

    transport_list: List[str] = []
    user_transport_prefs_text = user_data_raw.get('user_transport_prefs_text')
    if user_transport_prefs_text and isinstance(user_transport_prefs_text, str) and user_transport_prefs_text.strip():
        transport_list = [t.strip() for t in user_transport_prefs_text.split(',') if t.strip()]
    prepared_data['transport_preferences'] = transport_list

    prepared_data['user_language'] = user_data_raw.get('user_language', 'ru')  # Дефолт 'ru'

    # --- Новое/уточненное для "еще рекомендаций" ---
    prepared_data['request_type'] = user_data_raw.get('request_type', 'initial')

    # previously_shown_ids используется в промпте, поэтому формируем его здесь
    if prepared_data['request_type'] == 'more_options':
        previously_shown_ids_value = user_data_raw.get('current_session_shown_ids', [])
        # Убедимся, что это список строк (ID)
        if isinstance(previously_shown_ids_value, list):
            prepared_data['previously_shown_ids'] = [str(item_id) for item_id in previously_shown_ids_value if
                                                     isinstance(item_id, (str, int))]
        else:
            prepared_data['previously_shown_ids'] = []
            logging.warning(
                f"AI Integration: current_session_shown_ids имеет неверный тип: {type(previously_shown_ids_value)}")
    else:
        prepared_data['previously_shown_ids'] = []
    # --- Конец нового/уточненного ---

    history_for_ai = []
    liked_ids = user_data_raw.get('liked_recommendation_ids', [])
    if liked_ids and isinstance(liked_ids, list):
        # Убедимся, что ID в истории это строки
        string_liked_ids = [str(item_id) for item_id in liked_ids if isinstance(item_id, (str, int))]
        if string_liked_ids:
            history_for_ai.append({"type": "user_feedback_positive", "item_ids": string_liked_ids})

    disliked_ids = user_data_raw.get('disliked_recommendation_ids', [])
    if disliked_ids and isinstance(disliked_ids, list):
        string_disliked_ids = [str(item_id) for item_id in disliked_ids if isinstance(item_id, (str, int))]
        if string_disliked_ids:
            history_for_ai.append({"type": "user_feedback_negative", "item_ids": string_disliked_ids})

    prepared_data['history'] = history_for_ai

    # Используем json.dumps для отладки, чтобы видеть строки как есть, без одинарных кавычек Python
    logging.debug(
        f"AI Integration: Подготовленные данные для промпта: {json.dumps(prepared_data, ensure_ascii=False, indent=2)}")
    return prepared_data


async def get_travel_recommendations(
        user_data_raw: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not GEMINI_API_KEY:
        logging.error("AI Integration: API ключ для Gemini не настроен или невалиден.")
        return None, "Ошибка конфигурации: API ключ для AI не найден или не работает. Проверьте настройки."

    logging.info(
        f"AI Integration: Получены сырые данные от пользователя для get_travel_recommendations: {user_data_raw}")
    prepared = _prepare_user_data_for_prompt(user_data_raw)

    prompt_template = f"""<role>
Ты — «Travel Bot», высококлассный AI-ассистент для путешественников. Твоя главная цель — предоставлять персонализированные, полезные и вдохновляющие рекомендации. 
Ты должен строго следовать инструкциям по формату ответа и содержанию.
</role>

<task>
Проанализируй предоставленные "Входные данные от пользователя" и сгенерируй для него план путешествия.
</task>

## ОБЯЗАТЕЛЬНЫЕ ИНСТРУКЦИИ ДЛЯ ТЕБЯ, AI:
1.  **ФОРМАТ ОТВЕТА**: Твой ответ ДОЛЖЕН БЫТЬ ТОЛЬКО ОДНИМ JSON объектом. Никакого текста до или после этого JSON. Никакой Markdown разметки (типа ```json ... ```) вокруг JSON.
2.  **ЯЗЫК ОТВЕТА**: АБСОЛЮТНО ВЕСЬ текст в твоем ответе (все строковые значения в JSON и текст в `textual_summary`) ДОЛЖЕН БЫТЬ СТРОГО на языке, указанном в поле `user_language` во Входных данных. Это КРИТИЧЕСКИ ВАЖНО.
3.  **СТРУКТУРА JSON**: JSON объект должен иметь ДВА ключа на верхнем уровне:
    *   `"structured_recommendations"`: JSON объект, содержащий `query_summary` и список `recommendations`.
    *   `"textual_summary"`: Строка с дружелюбным и полезным сопроводительным текстом для пользователя (2-4 абзаца) на языке `user_language`, кратко суммирующим предложенный план.
4.  **ЭКРАНИРОВАНИЕ В JSON**: Если внутри строковых значений JSON (например, в полях "name", "description", "address") встречаются символы кавычек ("), ты ОБЯЗАН экранировать их как \\". Например: "name": "Отель \\"Цитадель\\"" - правильно. "name": "Отель "Цитадель"" - НЕПРАВИЛЬНО.
5.  **КАЧЕСТВО И РАЗНООБРАЗИЕ РЕКОМЕНДАЦИЙ**:
    *   Предлагай РАЗНООБРАЗНЫЕ, ИНТЕРЕСНЫЕ и РЕЛЕВАНТНЫЕ варианты, соответствующие `user_preferences`.
    *   Если по какому-то критерию качественных вариантов мало (например, низкий бюджет в дорогом городе), лучше предложи меньше (или даже ни одного для этой категории), но честно укажи на это в `textual_summary` и, возможно, предложи более широкие альтернативы.
    *   Старайся предлагать 1-2 варианта для отелей, 1-2 для ресторанов, и 2-3 для достопримечательностей/маршрутов/активностей, если это возможно и соответствует запросу.
6.  **АКТУАЛЬНОСТЬ ИНФОРМАЦИИ**:
    *   Для цен, часов работы и другой информации, которая может меняться, старайся давать наиболее общие или типичные данные.
    *   Если ты не уверен в актуальности, ОБЯЗАТЕЛЬНО добавь в `description` или `textual_summary` фразу вроде "Рекомендуется проверить актуальные часы работы/цены на официальном сайте." на языке `user_language`.
7.  **УЧЕТ ИСТОРИИ ПОЛЬЗОВАТЕЛЯ (`history`)**:
    *   Если в `history` есть записи с `type: "user_feedback_negative"`, **КАТЕГОРИЧЕСКИ ИЗБЕГАЙ** предложений рекомендаций с `id` из списка `item_ids` этого фидбека.
    *   Если в `history` есть записи с `type: "user_feedback_positive"`, рассматривай `item_ids` как примеры того, что нравится пользователю. Постарайся предложить НОВЫЕ, но ПОХОЖИЕ по духу/типу/ценовой категории рекомендации. **Не предлагай те же самые ID повторно, если только нет других подходящих вариантов.**
8.  **ОБРАБОТКА ТИПА ЗАПРОСА (`request_type` и `previously_shown_ids`):**
    *   Если `request_type` равен `"initial"`, генерируй первоначальный набор рекомендаций.
    *   Если `request_type` равен `"more_options"`, это запрос на ДОПОЛНИТЕЛЬНЫЕ рекомендации. В этом случае:
        *   **АБСОЛЮТНО НЕОБХОДИМО ИСКЛЮЧИТЬ И НЕ ПОВТОРЯТЬ** рекомендации с идентификаторами (`id`), которые уже были показаны пользователю и перечислены в поле `previously_shown_ids`. Это строгое требование. Предлагай только СОВЕРШЕННО НОВЫЕ ID.
        *   Если ты не можешь найти достаточно новых релевантных вариантов, лучше верни меньше рекомендаций или даже пустой список `recommendations` (т.е. `[]`), чем повторять уже показанные ID.
        *   Старайся предложить НОВЫЕ варианты, которые дополняют или расширяют предыдущие предложения, но соответствуют интересам и предпочтениям пользователя.
        *   Учитывай `history` (лайки/дизлайки) как обычно.
    *   Если `previously_shown_ids` пуст, даже при `request_type: "more_options"`, веди себя как при `initial`.

### Входные данные от пользователя (АНАЛИЗИРУЙ ИХ ВНИМАТЕЛЬНО)
user_location: "{prepared['user_location']}"
user_preferences: {json.dumps(prepared['user_preferences'], ensure_ascii=False)}
trip_duration_text: "{prepared['trip_duration_text']}"
transport_preferences: {json.dumps(prepared['transport_preferences'], ensure_ascii=False)}
history: {json.dumps(prepared['history'], ensure_ascii=False)} 
user_language: "{prepared['user_language']}"
request_type: "{prepared['request_type']}"
previously_shown_ids: {json.dumps(prepared['previously_shown_ids'], ensure_ascii=False)}

### ДЕТАЛЬНАЯ СПЕЦИФИКАЦИЯ для JSON объекта в "structured_recommendations"
#### 1. Поле `query_summary` (JSON объект):
- `"location_interpreted"`: Строка. Город/регион, который ты определил (на языке `user_language`).
- `"trip_days"`: Строка. Примерное количество дней (например, "3 дня") или JSON `null`.
- `"main_interests"`: Список строк. Ключевые интересы пользователя (на языке `user_language`).

#### 2. Поле `recommendations` (СПИСОК JSON объектов):
Каждый объект в списке `recommendations` ДОЛЖЕН содержать следующие поля:
- `"id"`: Строка. Уникальный ID (только латиница, цифры, подчеркивания, например, "hotel_grand_paris_01").
- `"type"`: Строка. Один из: "route", "hotel", "museum", "restaurant", "event", "activity".
- `"name"`: Строка. Название (на языке `user_language`).
- `"address"`: Строка. Адрес (на языке `user_language`) или JSON `null`.
- `"coordinates"`: **Список из ДВУХ ЧИСЕЛ** [широта, долгота] (например, [48.8584, 2.2945]) ИЛИ JSON `null`. **КАТЕГОРИЧЕСКИ НЕ ИСПОЛЬЗУЙ строки "null" или списки типа `["null"]`**.
- `"description"`: Строка. Краткое (2-4 предложения), но привлекательное описание (на языке `user_language`).
- `"details"`: JSON объект. Дополнительная информация. Если деталей нет, используй пустой объект `{{}}`.
    - Для `"type": "route"`: `{{ "route_type": "<пеший/автомобильный/велосипедный>", "stops": [{{ "name": "<Название Остановки>", "coordinates": [48.8600, 2.3350], "description": "<Краткое описание остановки>" }}] }}` (в `stops` может быть несколько объектов).
    - Для `"type": "hotel"`: `{{ "stars": <число от 1 до 5 ИЛИ null>, "amenities": ["<Удобство 1>", "<Удобство 2>"] }}` (список строк).
    - Для `"type": "restaurant"`: `{{ "cuisine_type": ["<Тип кухни 1>", "<Тип кухни 2>"], "average_bill": "<Примерный средний счет, например '20-40 EUR'>" }}`.
    - Для `"type": "event"`: `{{ "event_dates": ["<YYYY-MM-DD>"], "ticket_info": "<Информация о билетах, например 'От 25 EUR'>" }}`.
    - Для `"type": "museum"` или `"type": "activity"`: `{{ "ticket_info": "<Информация о билетах или 'Бесплатно'>" }}` (если платно).
- `"distance_or_time"`: Строка (например, "500 м от центра", "Около 3 часов") или JSON `null`.
- `"price_estimate"`: Строка (например, "Бесплатно", "20-30 EUR с человека") или JSON `null`.
- `"rating"`: Число от 1.0 до 5.0 (например, 4.7) или JSON `null`.
- `"opening_hours"`: Строка (например, "10:00-18:00 (Вт-Вс)") или JSON `null`.
- `"booking_link"`: **URL (строка) на ОФИЦИАЛЬНЫЙ сайт или ИЗВЕСТНЫЙ агрегатор ИЛИ JSON `null`. НЕ ВЫДУМЫВАЙ URL. НЕ ИСПОЛЬЗУЙ строку "null".**
- `"images"`: **Список URL картинок (строки). Предпочтительны ссылки на Wikimedia Commons или официальные сайты. Если РЕАЛЬНЫХ и РАБОЧИХ ссылок нет, верни ПУСТОЙ СПИСОК `[]`. НЕ ИСПОЛЬЗУЙ строки "null", ["null"] или недействительные URL.**

### Пример твоего ИДЕАЛЬНОГО ответа (ТОЛЬКО этот JSON, строго на языке `user_language` (пример ниже на русском для наглядности структуры)):
{{
  "structured_recommendations": {{
    "query_summary": {{
      "location_interpreted": "Париж, Франция", 
      "trip_days": "2 дня",
      "main_interests": ["искусство", "гастрономия"]
    }},
    "recommendations": [
      {{
        "id": "hotel_le_bristol_paris_01",
        "type": "hotel",
        "name": "Отель Le Bristol Paris",
        "address": "112 Rue du Faubourg Saint-Honoré, 75008 Париж, Франция",
        "coordinates": [48.8725, 2.3153],
        "description": "Один из самых престижных дворцовых отелей Парижа, известный своим исключительным сервисом и изысканными интерьерами.",
        "details": {{ "stars": 5, "amenities": ["Бассейн на крыше", "Спа-центр Epicure", "Три ресторана Мишлен"] }},
        "distance_or_time": "Рядом с Елисейскими Полями",
        "price_estimate": "От 1200 EUR/ночь",
        "rating": 4.9,
        "opening_hours": "Круглосуточно",
        "booking_link": "https://www.oetkercollection.com/hotels/le-bristol-paris/booking/",
        "images": ["https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Le_Bristol_Paris_Exterior.jpg/800px-Le_Bristol_Paris_Exterior.jpg"]
      }},
      {{
        "id": "route_montmartre_discovery_02",
        "type": "route",
        "name": "Открытие Монмартра",
        "address": "Монмартр, Париж, Франция",
        "coordinates": [48.8867, 2.3431],
        "description": "Живописный пешеходный маршрут по богемному району Монмартр, включая базилику Сакре-Кёр и площадь Тертр.",
        "details": {{ 
            "route_type": "пеший", 
            "stops": [
                {{ "name": "Базилика Сакре-Кёр", "coordinates": [48.8867, 2.3431], "description": "Начните с потрясающего вида на город." }}, 
                {{ "name": "Площадь Тертр", "coordinates": [48.8865, 2.3406], "description": "Площадь художников." }}
            ] 
        }},
        "distance_or_time": "Около 2-3 часов",
        "price_estimate": "Бесплатно (кроме сувениров)",
        "rating": 4.7,
        "opening_hours": null,
        "booking_link": null,
        "images": [] 
      }}
    ]
  }},
  "textual_summary": "Для вашей поездки в Париж, предлагаю вам окунуться в роскошь отеля Le Bristol и исследовать очаровательные улочки Монмартра. Это сочетание элегантности и парижского шарма сделает ваше путешествие незабываемым. Рекомендую проверить часы работы достопримечательностей перед посещением."
}}
"""
    # Раскомментируйте для детальной отладки самого промпта перед отправкой
    # logging.info(f"AI Integration DEBUG PROMPT:\n{prompt_template}")

    try:
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-latest')  # Используем более новую модель, если доступна
        logging.info("AI Integration: Отправка запроса к Gemini...")

        response = await model.generate_content_async(prompt_template)

        ai_text = ''
        # Улучшенная логика извлечения текста из ответа Gemini
        try:
            if hasattr(response, 'text') and response.text:
                ai_text = response.text
            elif hasattr(response,
                         'parts') and response.parts:  # Для некоторых моделей ответ может быть в response.parts
                ai_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            elif hasattr(response, 'candidates') and response.candidates and \
                    response.candidates[0].content and response.candidates[0].content.parts:
                ai_text = "".join(p.text for p in response.candidates[0].content.parts if hasattr(p, 'text'))
            else:  # Попытка извлечь из более глубокой структуры, если предыдущие не сработали
                ai_text = response.candidates[0].content.parts[0].text
        except (AttributeError, IndexError, TypeError) as e_extract:
            logging.warning(
                f"AI Integration: Не удалось стандартными способами извлечь текст из ответа Gemini. Ошибка: {e_extract}. Сырой ответ: {response}")
            # Если ничего не извлеклось, ai_text останется пустым

        if not ai_text:  # Проверка после всех попыток извлечения
            logging.error(
                f"AI Integration: Ответ Gemini пустой или не содержит извлекаемого текста. Сырой ответ: {response}")
            return None, "AI не смог сгенерировать текстовый ответ. Пожалуйста, проверьте логи."

        ai_text = ai_text.strip()
        # Очистка от Markdown JSON-обертки
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
                          f"Ответ Gemini, который не удалось распарсить (первые 1000 символов):\n{ai_text[:1000]}")
            return None, f"AI вернул некорректный JSON. (Ошибка: {e})"

        # Валидация основной структуры ответа
        structured = data.get('structured_recommendations')
        summary = data.get('textual_summary')

        if not isinstance(structured, dict):
            logging.error(
                f"AI Integration: 'structured_recommendations' отсутствует или не словарь. Получено: {type(structured)}. Ответ: {data}")
            return None, "AI вернул 'structured_recommendations' в неожиданном формате."
        if not isinstance(summary, str):
            logging.error(
                f"AI Integration: 'textual_summary' отсутствует или не строка. Получено: {type(summary)}. Ответ: {data}")
            return None, "AI вернул 'textual_summary' в неожиданном формате."

        query_summary_val = structured.get("query_summary")
        recommendations_list = structured.get("recommendations")

        if not isinstance(query_summary_val, dict) or not isinstance(recommendations_list, list):
            logging.error(
                f"AI Integration: Неверная внутренняя структура 'structured_recommendations'. query_summary: {type(query_summary_val)}, recommendations: {type(recommendations_list)}. Ответ: {structured}")
            return None, "AI вернул 'structured_recommendations' с неверной внутренней структурой."

        if not recommendations_list:  # Если список рекомендаций пуст
            logging.info("AI Integration: Gemini вернул пустой список 'recommendations'.")
            # Это не ошибка, а нормальный ответ, если AI ничего не нашел.
            # structured и summary будут возвращены, хэндлер решит, что делать.

        # Опциональная дополнительная валидация каждой рекомендации
        for idx, rec_item in enumerate(recommendations_list):
            if not isinstance(rec_item, dict):
                logging.warning(f"AI Integration: Элемент #{idx} в 'recommendations' не является словарем: {rec_item}")
                # Можно обработать: удалить элемент, вернуть ошибку и т.д.
            else:
                # Пример проверки обязательных полей
                if not rec_item.get("id") or not rec_item.get("type") or not rec_item.get("name"):
                    logging.warning(
                        f"AI Integration: Элемент #{idx} в 'recommendations' не содержит обязательных полей id/type/name: ID='{rec_item.get('id')}', Type='{rec_item.get('type')}', Name='{rec_item.get('name')}'")

        logging.info("AI Integration: Успешно получили и распарсили рекомендации от Gemini.")
        return structured, summary

    except Exception as e:
        # Логируем с exc_info=True для полного трейсбека
        logging.error(f"AI Integration: Непредвиденная ошибка при работе с Gemini API: {e}", exc_info=True)
        return None, f"Непредвиденная ошибка при обращении к AI: {type(e).__name__}. Детали в логах сервера."