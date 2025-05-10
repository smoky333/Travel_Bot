import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, \
    ContentType
from aiogram.fsm.context import FSMContext

from handlers.trip_planning_states import TripPlanning
from utils.ai_integration import get_travel_recommendations


# ==============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ФОРМАТИРОВАНИЯ РЕКОМЕНДАЦИИ
# ==============================================================================
async def _format_recommendation_text(recommendation: dict) -> str:
    """
    Формирует красивый текстовый блок для одной рекомендации.
    """
    rec_type_map = {
        "route": "🗺️ Маршрут", "transport_option": "🚌 Транспорт", "hotel": "🏨 Отель",
        "museum": "🏛️ Музей", "restaurant": "🍽️ Ресторан", "event": "🎉 Событие",
        "activity": "🤸 Активность"
    }
    rec_type_emoji = rec_type_map.get(recommendation.get("type", "unknown"), "⭐")

    text_parts = [
        f"<b>{rec_type_emoji}: {recommendation.get('name', 'Без названия')}</b>"
    ]

    if recommendation.get('address'):
        text_parts.append(f"📍 <b>Адрес:</b> {recommendation.get('address')}")

    if recommendation.get('description'):
        text_parts.append(f"📝 <i>{recommendation.get('description')}</i>")

    details = recommendation.get("details")
    if details and isinstance(details, dict):
        detail_str_parts = []
        if recommendation.get("type") == "route" and details.get("route_type"):
            detail_str_parts.append(f"Тип маршрута: {details['route_type']}")
        if recommendation.get("type") == "route" and details.get("stops"):
            stops_str = ", ".join([s.get('name', 'Остановка') for s in details['stops'][:3]])
            if len(details['stops']) > 3:
                stops_str += " и др."
            detail_str_parts.append(f"Остановки: {stops_str}")
        if recommendation.get("type") == "hotel" and details.get("stars"):
            stars_value = details.get('stars')
            if isinstance(stars_value, (int, float)) and stars_value > 0:
                stars_text = '⭐' * int(stars_value)
                detail_str_parts.append(f"{stars_text} ({stars_value} звезд)")
            elif stars_value:
                detail_str_parts.append(f"Звезд: {stars_value}")
        if recommendation.get("type") == "hotel" and details.get("amenities"):
            amenities_str = ", ".join(details['amenities'][:3])
            if len(details['amenities']) > 3:
                amenities_str += " и др."
            detail_str_parts.append(f"Удобства: {amenities_str}")
        if recommendation.get("type") == "restaurant" and details.get("cuisine_type"):
            cuisine_str = ", ".join(details['cuisine_type']) if isinstance(details['cuisine_type'], list) else details[
                'cuisine_type']
            detail_str_parts.append(f"Кухня: {cuisine_str}")
        if recommendation.get("type") == "restaurant" and details.get("average_bill"):
            detail_str_parts.append(f"Средний чек: {details['average_bill']}")
        if recommendation.get("type") == "event" and details.get("event_dates"):
            dates_str = " - ".join(details['event_dates']) if isinstance(details['event_dates'], list) else details[
                'event_dates']
            detail_str_parts.append(f"Даты проведения: {dates_str}")

        if detail_str_parts:
            text_parts.append("\n<b>Детали:</b>\n" + "\n".join([f"  - {d}" for d in detail_str_parts]))

    if recommendation.get('distance_or_time'):
        text_parts.append(f"🚗/🚶 <b>Расстояние/Время:</b> {recommendation.get('distance_or_time')}")
    if recommendation.get('price_estimate'):
        price_est = recommendation.get('price_estimate')
        if price_est and str(price_est).lower() != "null":
            text_parts.append(f"💰 <b>Цена:</b> {price_est}")
    if recommendation.get('rating'):
        text_parts.append(f"🌟 <b>Рейтинг:</b> {recommendation.get('rating')}/5")
    if recommendation.get('opening_hours'):
        oh = recommendation.get('opening_hours')
        if oh and str(oh).lower() != "null":
            text_parts.append(f"⏰ <b>Часы работы:</b> {oh}")

    return "\n\n".join(text_parts)


# ==============================================================================
# ОСНОВНОЙ РОУТЕР ДЛЯ ПЛАНИРОВАНИЯ ПОЕЗДКИ
# ==============================================================================
trip_planning_router = Router(name="trip_planning_router")


# Обработчик команды /plan_trip
@trip_planning_router.message(Command("plan_trip"))
async def cmd_plan_trip(message: Message, state: FSMContext):
    await message.answer(
        "Отлично! Начнем планирование вашей идеальной поездки. ✨\n\n"
        "<b>Шаг 1: Пункт назначения</b>\n"
        "📍 Пожалуйста, напишите город или страну, куда вы хотите поехать. "
        "Или, если вы уже там, можете отправить свою текущую геолокацию (нажав на скрепку 📎 и выбрав 'Геопозиция').",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TripPlanning.waiting_for_location)
    logging.info(f"Пользователь {message.from_user.id} начал планирование. Переведен в состояние waiting_for_location.")


# Обработчик для получения ответа на вопрос о локации (текстовый ввод)
@trip_planning_router.message(TripPlanning.waiting_for_location, F.text)
async def process_location_text(message: Message, state: FSMContext):
    logging.info(f"СРАБОТАЛ process_location_text для пользователя {message.from_user.id}")
    await state.update_data(user_location_text=message.text.strip())
    await state.update_data(user_location_geo=None)
    user_data = await state.get_data()
    logging.info(f"Данные от пользователя {message.from_user.id} после ввода текстовой локации: {user_data}")
    await _ask_for_interests(message, state)


# Обработчик для получения геолокации от пользователя
@trip_planning_router.message(TripPlanning.waiting_for_location, F.content_type == ContentType.LOCATION)
async def process_location_geo(message: Message, state: FSMContext):
    logging.info(f"СРАБОТАЛ process_location_geo для пользователя {message.from_user.id}")
    user_latitude = message.location.latitude
    user_longitude = message.location.longitude

    await state.update_data(user_location_geo=[user_latitude, user_longitude])
    await state.update_data(user_location_text=None)

    user_data = await state.get_data()
    logging.info(
        f"Пользователь {message.from_user.id} отправил геолокацию: [{user_latitude}, {user_longitude}]. Данные state: {user_data}")

    await message.answer(
        f"🌍 Геолокация получена: Широта {user_latitude:.4f}, Долгота {user_longitude:.4f}.\n"
        "Отлично!"
    )
    await _ask_for_interests(message, state)


async def _ask_for_interests(message: Message, state: FSMContext):
    """Вспомогательная функция для вопроса об интересах."""
    user_data = await state.get_data()  # Получаем данные, чтобы извлечь язык
    lang = user_data.get("user_language", "ru")  # По умолчанию русский

    # TODO: Здесь нужно будет использовать словарь BOT_MESSAGES для локализации этого вопроса
    # Пока оставляем на русском для простоты этого шага
    prompt_text = (
        "<b>Шаг 2: Ваши интересы</b> 🎨🏞️🏛️🛍️\n"
        "Напишите, пожалуйста, через запятую, что вас больше всего интересует в поездке. Например: "
        "<i>архитектура, природа, гастрономия, шопинг, история, искусство, ночная жизнь, семейный отдых</i>."
    )
    if lang == "en":
        prompt_text = (
            "<b>Step 2: Your Interests</b> 🎨🏞️🏛️🛍️\n"
            "Please list your interests, separated by commas. For example: "
            "<i>architecture, nature, gastronomy, shopping, history, art, nightlife, family vacation</i>."
        )
    elif lang == "fr":
        prompt_text = (
            "<b>Étape 2 : Vos centres d'intérêt</b> 🎨🏞️🏛️🛍️\n"
            "Veuillez énumérer vos centres d'intérêt, séparés par des virgules. Par exemple: "
            "<i>architecture, nature, gastronomie, shopping, histoire, art, vie nocturne, vacances en famille</i>."
        )

    await message.answer(prompt_text)
    await state.set_state(TripPlanning.waiting_for_interests)
    logging.info(f"Пользователь {message.from_user.id} переведен в состояние waiting_for_interests.")


# Обработчик для получения ответа на вопрос об интересах
@trip_planning_router.message(TripPlanning.waiting_for_interests, F.text)
async def process_interests(message: Message, state: FSMContext):
    await state.update_data(user_interests_text=message.text.strip())
    user_data = await state.get_data()
    logging.info(f"Данные от пользователя {message.from_user.id} после ввода интересов: {user_data}")

    lang = user_data.get("user_language", "ru")

    # TODO: Локализовать тексты кнопок и сообщения
    button_text_low = "💰 Эконом (Low)"
    button_text_mid = "💰💰 Средний (Mid)"
    button_text_premium = "💰💰💰 Премиум (Premium)"
    prompt_text_budget = "<b>Шаг 3: Ваш бюджет</b> 💳\nПожалуйста, выберите предполагаемый уровень расходов на поездку:"

    if lang == "en":
        button_text_low = "💰 Economy (Low)"
        button_text_mid = "💰💰 Standard (Mid)"
        button_text_premium = "💰💰💰 Premium"
        prompt_text_budget = "<b>Step 3: Your Budget</b> 💳\nPlease select your estimated spending level for the trip:"
    elif lang == "fr":
        button_text_low = "💰 Économique (Low)"
        button_text_mid = "💰💰 Moyen (Mid)"
        button_text_premium = "💰💰💰 Premium"
        prompt_text_budget = "<b>Étape 3 : Votre Budget</b> 💳\nVeuillez sélectionner votre niveau de dépenses estimé pour le voyage :"

    budget_buttons = [
        [InlineKeyboardButton(text=button_text_low, callback_data="budget_low")],
        [InlineKeyboardButton(text=button_text_mid, callback_data="budget_mid")],
        [InlineKeyboardButton(text=button_text_premium, callback_data="budget_premium")]
    ]
    budget_keyboard = InlineKeyboardMarkup(inline_keyboard=budget_buttons)

    # Сообщение о принятых интересах тоже нужно локализовать
    interests_accepted_text = f"Отлично! Ваши интересы: {message.text}.\n\n"
    if lang == "en":
        interests_accepted_text = f"Great! Your interests: {message.text}.\n\n"
    elif lang == "fr":
        interests_accepted_text = f"Parfait ! Vos centres d'intérêt : {message.text}.\n\n"

    await message.answer(
        interests_accepted_text + prompt_text_budget,
        reply_markup=budget_keyboard
    )
    await state.set_state(TripPlanning.waiting_for_budget)
    logging.info(f"Пользователь {message.from_user.id} переведен в состояние waiting_for_budget.")


# Обработчик для нажатия кнопки бюджета
@trip_planning_router.callback_query(TripPlanning.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget_callback(callback_query: CallbackQuery, state: FSMContext):
    selected_budget_code = callback_query.data.split("_")[1]
    await state.update_data(user_budget=selected_budget_code)

    user_data = await state.get_data()  # Получаем данные, чтобы извлечь язык
    lang = user_data.get("user_language", "ru")
    logging.info(f"Данные от пользователя {callback_query.from_user.id} после выбора бюджета: {user_data}")

    # TODO: Локализовать тексты
    budget_selected_text = f"Бюджет выбран: {selected_budget_code.capitalize()}"
    prompt_dates_text = (
        "<b>Шаг 4: Даты поездки</b> 📅\n"
        "Пожалуйста, напишите даты начала и окончания вашей поездки.\n"
        "Например: <i>2025-05-10 to 2025-05-12</i> или <i>с 10 по 12 мая 2025</i>.\n"
        "Если точных дат нет, можно указать примерную продолжительность, например, <i>неделя в июле</i> или <i>3 дня</i>."
    )
    if lang == "en":
        budget_selected_text = f"Budget selected: {selected_budget_code.capitalize()}"
        prompt_dates_text = (
            "<b>Step 4: Trip Dates</b> 📅\n"
            "Please enter the start and end dates of your trip.\n"
            "For example: <i>2025-05-10 to 2025-05-12</i> or <i>from May 10 to 12, 2025</i>.\n"
            "If you don't have exact dates, you can specify an approximate duration, e.g., <i>a week in July</i> or <i>3 days</i>."
        )
    elif lang == "fr":
        budget_selected_text = f"Budget sélectionné : {selected_budget_code.capitalize()}"
        prompt_dates_text = (
            "<b>Étape 4 : Dates du voyage</b> 📅\n"
            "Veuillez indiquer les dates de début et de fin de votre voyage.\n"
            "Par exemple : <i>2025-05-10 to 2025-05-12</i> ou <i>du 10 au 12 mai 2025</i>.\n"
            "Si vous n'avez pas de dates exactes, vous pouvez spécifier une durée approximative, par exemple, <i>une semaine en juillet</i> ou <i>3 jours</i>."
        )

    await callback_query.message.edit_text(f"{budget_selected_text}.\n\n{prompt_dates_text}")
    await callback_query.answer(text=budget_selected_text, show_alert=False)
    await state.set_state(TripPlanning.waiting_for_trip_dates)
    logging.info(f"Пользователь {callback_query.from_user.id} переведен в состояние waiting_for_trip_dates.")


# Обработчик для получения ответа на вопрос о датах поездки
@trip_planning_router.message(TripPlanning.waiting_for_trip_dates, F.text)
async def process_trip_dates(message: Message, state: FSMContext):
    await state.update_data(user_trip_dates_text=message.text.strip())
    user_data = await state.get_data()  # Получаем данные, чтобы извлечь язык
    lang = user_data.get("user_language", "ru")
    logging.info(f"Данные от пользователя {message.from_user.id} после ввода дат: {user_data}")

    # TODO: Локализовать тексты
    dates_accepted_text = f"Даты приняты: {message.text}.\n\n"
    prompt_transport_text = (
        "<b>Шаг 5: Предпочтения по транспорту</b> 🚶🚗🚌🚲\n"
        "Напишите, пожалуйста, через запятую, какие виды транспорта вы предпочитаете использовать в поездке. "
        "Например: <i>пешком, автомобиль, общественный транспорт, велосипед, такси</i>."
    )
    if lang == "en":
        dates_accepted_text = f"Dates accepted: {message.text}.\n\n"
        prompt_transport_text = (
            "<b>Step 5: Transport Preferences</b> 🚶🚗🚌🚲\n"
            "Please list your preferred modes of transport, separated by commas. "
            "For example: <i>walking, car, public transport, bicycle, taxi</i>."
        )
    elif lang == "fr":
        dates_accepted_text = f"Dates acceptées : {message.text}.\n\n"
        prompt_transport_text = (
            "<b>Étape 5 : Préférences de transport</b> 🚶🚗🚌🚲\n"
            "Veuillez indiquer vos modes de transport préférés, séparés par des virgules. "
            "Par exemple : <i>marche, voiture, transports en commun, vélo, taxi</i>."
        )

    await message.answer(dates_accepted_text + prompt_transport_text)
    await state.set_state(TripPlanning.waiting_for_transport_prefs)
    logging.info(f"Пользователь {message.from_user.id} переведен в состояние waiting_for_transport_prefs.")


# Обработчик для получения ответа на вопрос о предпочтениях по транспорту
@trip_planning_router.message(TripPlanning.waiting_for_transport_prefs, F.text)
async def process_transport_prefs(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(user_transport_prefs_text=message.text.strip())
    final_user_data = await state.get_data()
    lang = final_user_data.get("user_language", "ru")
    logging.info(f"Все собранные данные от пользователя {message.from_user.id}: {final_user_data}")

    # TODO: Локализовать тексты
    transport_accepted_text = f"Предпочтения по транспорту приняты: {message.text}.\n\n"
    generating_text = "🎉 <b>Отлично! Вы предоставили всю основную информацию!</b>\nПодбираю для вас лучшие варианты... Это может занять несколько секунд ✨"

    if lang == "en":
        transport_accepted_text = f"Transport preferences accepted: {message.text}.\n\n"
        generating_text = "🎉 <b>Great! You've provided all the basic information!</b>\nFinding the best options for you... This might take a few seconds ✨"
    elif lang == "fr":
        transport_accepted_text = f"Préférences de transport acceptées : {message.text}.\n\n"
        generating_text = "🎉 <b>Parfait ! Vous avez fourni toutes les informations de base !</b>\nRecherche des meilleures options pour vous... Cela может prendre quelques secondes ✨"

    await message.answer(transport_accepted_text + generating_text)
    await state.clear()

    recommendations_json, accompanying_text = await get_travel_recommendations(final_user_data)

    if recommendations_json and accompanying_text:
        # Сопроводительный текст уже должен быть на нужном языке от Gemini
        await message.answer(accompanying_text)

        if "recommendations" in recommendations_json:
            for rec in recommendations_json["recommendations"]:
                # Текст рекомендации уже должен быть на нужном языке от Gemini
                formatted_text = await _format_recommendation_text(rec)  # Форматирование HTML остается

                buttons = []
                booking_url = rec.get('booking_link')
                button_book_text = "🔗 Бронь/Билеты"
                button_map_text = "🗺️ На карте"
                if lang == "en":
                    button_book_text = "🔗 Book/Tickets"
                    button_map_text = "🗺️ On Map"
                elif lang == "fr":
                    button_book_text = "🔗 Réserver/Billets"
                    button_map_text = "🗺️ Sur la carte"

                if booking_url and isinstance(booking_url,
                                              str) and booking_url.strip().lower() != "null" and booking_url.strip() != "":
                    buttons.append(InlineKeyboardButton(text=button_book_text, url=booking_url))

                coords = rec.get('coordinates')
                if coords and isinstance(coords, list) and len(coords) == 2:
                    try:
                        lat, lon = float(coords[0]), float(coords[1])
                        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        buttons.append(InlineKeyboardButton(text=button_map_text, url=maps_url))
                    except (ValueError, TypeError):
                        logging.warning(f"Некорректные координаты для кнопки 'На карте': {coords}")

                reply_markup = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

                images = rec.get("images", [])
                photo_sent = False
                if images and isinstance(images, list) and images[0] and isinstance(images[0], str):
                    try:
                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=images[0],
                            caption=formatted_text,
                            # Этот текст уже отформатирован и должен быть на нужном языке от Gemini
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                        photo_sent = True
                    except Exception as e:
                        logging.warning(f"Ошибка отправки фото {images[0]}: {e}. Попытка отправить только текст.")

                if not photo_sent:
                    await message.answer(formatted_text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            # TODO: Локализовать это сообщение
            no_recs_text = "К сожалению, в полученном ответе от AI нет раздела 'recommendations'."
            if lang == "en":
                no_recs_text = "Unfortunately, the AI response does not contain a 'recommendations' section."
            elif lang == "fr":
                no_recs_text = "Malheureusement, la réponse de l'IA ne contient pas de section 'recommendations'."
            await message.answer(no_recs_text)
    else:
        error_text_to_send = accompanying_text or "К сожалению, не удалось получить рекомендации от AI. Попробуйте позже."
        # TODO: Локализовать accompanying_text или это общее сообщение об ошибке
        if lang == "en" and not accompanying_text:
            error_text_to_send = "Sorry, couldn't get recommendations from AI. Please try again later."
        elif lang == "fr" and not accompanying_text:
            error_text_to_send = "Désolé, impossible d'obtenir des recommandations de l'IA. Veuillez réessayer plus tard."
        await message.answer(error_text_to_send)

    logging.info(f"Пользователь {message.from_user.id} получил ответ от AI. FSM состояние очищено.")