# utils/localization.py
import logging
from typing import Dict, Any, Optional, List

# СЛОВАРЬ С ПОДДЕРЖИВАЕМЫМИ ЯЗЫКАМИ И ИХ КОДАМИ
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en",
    "🇫🇷 Français": "fr",
}

# Словари с переводами
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # --- Тексты для user_commands.py ---
    "welcome_language_selected": {
        "ru": "🇷🇺 Отлично! Выбран русский язык.\nЯ твой персональный Travel Bot.\nГотов помочь спланировать твое лучшее путешествие!\n\nЧтобы начать планирование, используй команду /plan_trip",
        "en": "🇬🇧 Great! English language selected.\nI am your personal Travel Bot.\nReady to help you plan your best trip!\n\nTo start planning, use the /plan_trip command.",
        "fr": "🇫🇷 Parfait ! Langue française sélectionnée.\nJe suis votre Travel Bot personnel.\nPrêt à vous aider à planifier votre meilleur voyage !\n\nPour commencer la planification, utilisez la commande /plan_trip"
    },
    "language_selection_prompt": {
        "ru": "👋 Привет! Пожалуйста, выберите язык:",
        "en": "👋 Hello! Please select your language:",
        "fr": "👋 Bonjour ! Veuillez sélectionner votre langue :"
    },
    # >>> НАЧАЛО ДОБАВЛЕННЫХ КЛЮЧЕЙ
    "welcome_back": {
        "ru": "С возвращением! Я вижу, вы предпочитаете <b>{language}</b> язык.\n\nНачните планирование с /plan_trip или смените язык командой /language.",
        "en": "Welcome back! I see you prefer the <b>{language}</b> language.\n\nStart planning with /plan_trip or change your language with the /language command.",
        "fr": "Bon retour ! Je vois que vous préférez la langue <b>{language}</b>.\n\nCommencez à planifier avec /plan_trip ou changez de langue avec la commande /language."
    },
    "db_error_lang_save": {
        "ru": "⚠️ Произошла ошибка при сохранении вашего выбора языка. Пожалуйста, попробуйте позже или свяжитесь с поддержкой.",
        "en": "⚠️ An error occurred while saving your language preference. Please try again later or contact support.",
        "fr": "⚠️ Une erreur s'est produite lors de l'enregistrement de votre préférence linguistique. Veuillez réessayer plus tard ou contacter le support."
    },
    # <<< КОНЕЦ ДОБАВЛЕННЫХ КЛЮЧЕЙ
    # --- Тексты для trip_planning_handlers.py (FSM) ---
    "start_planning_prompt": {
        "ru": "Отлично! Начнем планирование вашей идеальной поездки. ✨",
        "en": "Great! Let's start planning your perfect trip. ✨",
        "fr": "Parfait ! Commençons à planifier votre voyage idéal. ✨"
    },
    "step1_location_prompt": {
        "ru": "<b>Шаг 1: Пункт назначения</b>\n📍 Пожалуйста, напишите город или страну, куда вы хотите поехать. Или, если вы уже там, можете отправить свою текущую геолокацию (нажав на скрепку 📎 и выбрав 'Геопозиция').",
        "en": "<b>Step 1: Destination</b>\n📍 Please write the city or country you want to travel to. Or, if you are already there, you can send your current geolocation (by clicking the paperclip 📎 and selecting 'Location').",
        "fr": "<b>Étape 1 : Destination</b>\n📍 Veuillez écrire la ville ou le pays où vous souhaitez vous rendre. Ou, si vous y êtes déjà, vous pouvez envoyer votre géolocalisation actuelle (en cliquant sur le trombone 📎 et en sélectionnant 'Position')."
    },
    "location_received_text": {
        "ru": "Принято! Вы указали: {location_text}.",
        "en": "Got it! You specified: {location_text}.",
        "fr": "Reçu ! Vous avez spécifié : {location_text}."
    },
    "location_geo_received_text": {
        "ru": "🌍 Геолокация получена: Широта {latitude:.4f}, Долгота {longitude:.4f}.\nОтлично! Теперь расскажите о ваших интересах.",
        "en": "🌍 Geolocation received: Latitude {latitude:.4f}, Longitude {longitude:.4f}.\nGreat! Now tell me about your interests.",
        "fr": "🌍 Géolocalisation reçue : Latitude {latitude:.4f}, Longitude {longitude:.4f}.\nParfait ! Maintenant, parlez-moi de vos centres d'intérêt."
    },
    "step2_interests_prompt": {
        "ru": "<b>Шаг 2: Ваши интересы</b> 🎨🏞️🏛️🛍️\nНапишите, пожалуйста, через запятую, что вас больше всего интересует в поездке. Например: <i>архитектура, природа, гастрономия, шопинг, история, искусство, ночная жизнь, семейный отдых</i>.",
        "en": "<b>Step 2: Your Interests</b> 🎨🏞️🏛️🛍️\nPlease write, separated by commas, what interests you most on your trip. For example: <i>architecture, nature, gastronomy, shopping, history, art, nightlife, family vacation</i>.",
        "fr": "<b>Étape 2 : Vos centres d'intérêt</b> 🎨🏞️🏛️🛍️\nVeuillez écrire, séparés par des virgules, ce qui vous intéresse le plus lors de votre voyage. Par exemple : <i>architecture, nature, gastronomie, shopping, histoire, art, vie nocturne, vacances en famille</i>."
    },
    "interests_received_text": {
        "ru": "Отлично! Ваши интересы: {interests_text}.",
        "en": "Great! Your interests: {interests_text}.",
        "fr": "Parfait ! Vos centres d'intérêt : {interests_text}."
    },
    "step3_budget_prompt": {
        "ru": "<b>Шаг 3: Ваш бюджет</b> 💳\nПожалуйста, выберите предполагаемый уровень расходов на поездку:",
        "en": "<b>Step 3: Your Budget</b> 💳\nPlease select your estimated spending level for the trip:",
        "fr": "<b>Étape 3 : Votre budget</b> 💳\nVeuillez sélectionner votre niveau de dépenses estimé pour le voyage :"
    },
    "budget_option_low": {"ru": "💰 Эконом (Low)", "en": "💰 Economy (Low)", "fr": "💰 Économique (Bas)"},
    "budget_option_mid": {"ru": "💰💰 Средний (Mid)", "en": "💰💰 Standard (Mid)", "fr": "💰💰 Moyen (Moyen)"},
    "budget_option_premium": {"ru": "💰💰💰 Премиум (Premium)", "en": "💰💰💰 Premium", "fr": "💰💰💰 Premium"},
    "budget_selected_text": {
        "ru": "Бюджет выбран: {selected_budget}",
        "en": "Budget selected: {selected_budget}",
        "fr": "Budget sélectionné : {selected_budget}"
    },
    "step4_dates_prompt": {
        "ru": "<b>Шаг 4: Даты поездки</b> 📅\nПожалуйста, напишите даты начала и окончания вашей поездки.\nНапример: <i>2025-05-10 to 2025-05-12</i> или <i>с 10 по 12 мая 2025</i>.\nЕсли точных дат нет, можно указать примерную продолжительность, например, <i>неделя в июле</i> или <i>3 дня</i>.",
        "en": "<b>Step 4: Trip Dates</b> 📅\nPlease write the start and end dates of your trip.\nFor example: <i>2025-05-10 to 2025-05-12</i> or <i>from May 10 to May 12, 2025</i>.\nIf you don't have exact dates, you can specify an approximate duration, e.g., <i>a week in July</i> or <i>3 days</i>.",
        "fr": "<b>Étape 4 : Dates du voyage</b> 📅\nVeuillez écrire les dates de début et de fin de votre voyage.\nPar exemple : <i>2025-05-10 to 2025-05-12</i> ou <i>du 10 au 12 mai 2025</i>.\nSi vous n'avez pas de dates exactes, vous pouvez spécifier une durée approximative, par exemple, <i>une semaine en juillet</i> ou <i>3 jours</i>."
    },
    "dates_received_text": {
        "ru": "Даты приняты: {dates_text}.",
        "en": "Dates accepted: {dates_text}.",
        "fr": "Dates acceptées : {dates_text}."
    },
    "step5_transport_prompt": {
        "ru": "<b>Шаг 5: Предпочтения по транспорту</b> 🚶🚗🚌🚲\nНапишите, пожалуйста, через запятую, какие виды транспорта вы предпочитаете использовать в поездке. Например: <i>пешком, автомобиль, общественный транспорт, велосипед, такси</i>.",
        "en": "<b>Step 5: Transport Preferences</b> 🚶🚗🚌🚲\nPlease write, separated by commas, which types of transport you prefer to use on your trip. For example: <i>walking, car, public transport, bicycle, taxi</i>.",
        "fr": "<b>Étape 5 : Préférences de transport</b> 🚶🚗🚌🚲\nVeuillez écrire, séparés par des virgules, les types de transport que vous préférez utiliser pendant votre voyage. Par exemple : <i>à pied, voiture, transports en commun, vélo, taxi</i>."
    },
    "transport_received_text": {
        "ru": "Предпочтения по транспорту приняты: {transport_text}.",
        "en": "Transport preferences accepted: {transport_text}.",
        "fr": "Préférences de transport acceptées : {transport_text}."
    },
    "all_data_collected_prompt": {
        "ru": "🎉 <b>Отлично! Вы предоставили всю основную информацию!</b>\nПодбираю для вас лучшие варианты... Это может занять несколько секунд ✨",
        "en": "🎉 <b>Great! You have provided all the basic information!</b>\nFinding the best options for you... This may take a few seconds ✨",
        "fr": "🎉 <b>Parfait ! Vous avez fourni toutes les informations de base !</b>\nRecherche des meilleures options pour vous... Cela peut prendre quelques secondes ✨"
    },
    # --- Тексты для кнопок и форматирования рекомендаций ---
    "button_book_tickets": {"ru": "🔗 Бронь/Билеты", "en": "🔗 Book/Tickets", "fr": "🔗 Réserver/Billets"},
    "button_on_map": {"ru": "🗺️ На карте", "en": "🗺️ On Map", "fr": "🗺️ Sur la carte"},
    "button_like": {"ru": "Нравится", "en": "Like", "fr": "J'aime"},
    "button_dislike": {"ru": "Не нравится", "en": "Dislike", "fr": "Je n'aime pas"},
    "feedback_thanks_like": {
        "ru": "Спасибо, ваш голос учтен!",
        "en": "Thanks, your feedback is saved!",
        "fr": "Merci, votre avis est enregistré !"
    },
    "feedback_thanks_dislike": {
        "ru": "Понятно, спасибо за отзыв.",
        "en": "Got it, thanks for your feedback.",
        "fr": "Compris, merci pour votre avis."
    },
    "text_no_name": {"ru": "Без названия", "en": "No Name", "fr": "Sans Nom"},
    "text_address": {"ru": "Адрес", "en": "Address", "fr": "Adresse"},
    "text_details_header": {"ru": "Детали", "en": "Details", "fr": "Détails"},
    "detail_route_type": {"ru": "Тип маршрута", "en": "Route Type", "fr": "Type d'itinéraire"},
    "detail_stops": {"ru": "Остановки", "en": "Stops", "fr": "Arrêts"},
    "text_stop": {"ru": "Остановка", "en": "Stop", "fr": "Arrêt"},
    "text_and_more": {"ru": "и др.", "en": "and more", "fr": "et plus"},
    "detail_hotel_stars": {"ru": "Звезд", "en": "Stars", "fr": "Étoiles"},
    "detail_hotel_stars_suffix": {"ru": "звезд(ы)", "en": "stars", "fr": "étoiles"},
    "detail_hotel_amenities": {"ru": "Удобства", "en": "Amenities", "fr": "Équipements"},
    "detail_restaurant_cuisine": {"ru": "Кухня", "en": "Cuisine", "fr": "Cuisine"},
    "detail_restaurant_avg_bill": {"ru": "Средний чек", "en": "Average Bill", "fr": "Note Moyenne"},
    "detail_event_dates": {"ru": "Даты проведения", "en": "Event Dates", "fr": "Dates de l'événement"},
    "detail_ticket_info": {"ru": "Информация о билетах", "en": "Ticket Info", "fr": "Infos Billets"},
    "text_distance_time": {"ru": "Расстояние/Время", "en": "Distance/Time", "fr": "Distance/Temps"},
    "text_price": {"ru": "Цена", "en": "Price", "fr": "Prix"},
    "text_rating": {"ru": "Рейтинг", "en": "Rating", "fr": "Évaluation"},
    "text_opening_hours": {"ru": "Часы работы", "en": "Opening Hours", "fr": "Horaires d'ouverture"},
    # --- Сообщения об ошибках ---
    "ai_response_error_text": {
        "ru": "К сожалению, не удалось получить рекомендации от AI. Попробуйте позже.",
        "en": "Sorry, couldn't get recommendations from AI. Please try again later.",
        "fr": "Désolé, impossible d'obtenir des recommandations de l'IA. Veuillez réessayer plus tard."
    },
    "ai_json_decode_error_text": {
        "ru": "AI вернул некорректный JSON. Пожалуйста, попробуйте еще раз. (Отладка: {error_details})",
        "en": "AI returned invalid JSON. Please try again. (Debug: {error_details})",
        "fr": "L'IA a renvoyé un JSON non valide. Veuillez réessayer. (Débogage : {error_details})"
    },
    "ai_unexpected_format_text": {
        "ru": "AI вернул данные в неожиданном формате. Пожалуйста, сообщите разработчику.",
        "en": "AI returned data in an unexpected format. Please inform the developer.",
        "fr": "L'IA a renvoyé des données dans un format inattendu. Veuillez informer le développeur."
    },
    "ai_unexpected_error_text": {
        "ru": "Произошла непредвиденная ошибка при обращении к AI: {error_type}. Пожалуйста, сообщите разработчику.",
        "en": "An unexpected error occurred while contacting AI: {error_type}. Please inform the developer.",
        "fr": "Une erreur inattendue s'est produite lors de la communication avec l'IA : {error_type}. Veuillez informer le développeur."
    },
    "no_recommendations_in_response_text": {
        "ru": "К сожалению, в полученном ответе от AI нет раздела 'recommendations'.",
        "en": "Unfortunately, the AI response does not contain a 'recommendations' section.",
        "fr": "Malheureusement, la réponse de l'IA ne contient pas de section 'recommendations'."
    }
}

DEFAULT_LANGUAGE = "ru" # По умолчанию, если язык пользователя не определен или не поддерживается


def get_text(key: str, lang_code: Optional[str] = None, **kwargs: Any) -> str:
    """
    Возвращает локализованный текст по ключу и коду языка.
    Поддерживает форматирование с помощью kwargs.
    Экранирует плейсхолдер ошибки для безопасного вывода в HTML.
    """
    # Определяем язык, который будем использовать
    effective_lang_code = lang_code
    if not effective_lang_code or effective_lang_code not in SUPPORTED_LANGUAGES.values():
        effective_lang_code = DEFAULT_LANGUAGE
        if lang_code: # Логируем, если запрошенный язык не поддерживается, но не был None
             logging.debug(f"Localization: Запрошенный язык '{lang_code}' не поддерживается или отсутствует. Используется язык по умолчанию '{DEFAULT_LANGUAGE}'.")


    translation_dict = TRANSLATIONS.get(key)
    if translation_dict:
        text_template = translation_dict.get(effective_lang_code)
        # Если перевод на целевом языке отсутствует, пытаемся взять перевод на языке по умолчанию
        if not text_template and effective_lang_code != DEFAULT_LANGUAGE:
            text_template = translation_dict.get(DEFAULT_LANGUAGE)
            if text_template:
                 logging.debug(f"Localization: Перевод для ключа '{key}' на языке '{effective_lang_code}' отсутствует. Используется перевод на языке по умолчанию '{DEFAULT_LANGUAGE}'.")


        if text_template:
            try:
                return text_template.format(**kwargs)
            except KeyError as e:
                logging.error(
                    f"Localization: Отсутствует ключ форматирования '{e}' для текста '{key}' на языке '{effective_lang_code}'. Шаблон: '{text_template}' Kwargs: {kwargs}")
                # Возвращаем шаблон без форматирования, чтобы хоть что-то показать, но с логом ошибки
                return text_template
        else:
            # Случай, когда ключ есть в TRANSLATIONS, но нет перевода ни на запрошенный язык, ни на язык по умолчанию
            logging.warning(f"Localization: Ключ '{key}' найден, но отсутствует перевод как для '{effective_lang_code}', так и для языка по умолчанию '{DEFAULT_LANGUAGE}'.")

    else:
        logging.warning(f"Localization: Ключ '{key}' не найден в словаре TRANSLATIONS.")

    # Плейсхолдер, если ключ не найден или нет перевода
    # Используем html.escape для безопасности, если это будет рендериться как HTML
    # import html
    # error_placeholder = html.escape(f"[L10N_ERROR: Key '{key}' for lang '{effective_lang_code}' not found]")
    error_placeholder = f"<L10N_ERROR: {key}_FOR_{effective_lang_code}>" # Оставляем твой вариант, если HTML не критичен здесь
    return error_placeholder