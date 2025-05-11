import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, \
    ContentType
from aiogram.fsm.context import FSMContext

from handlers.trip_planning_states import TripPlanning
from utils.ai_integration import get_travel_recommendations
from utils.localization import get_text  # <--- ИМПОРТИРУЕМ get_text


# ==============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ФОРМАТИРОВАНИЯ РЕКОМЕНДАЦИИ (остается как есть)
# ==============================================================================
async def _format_recommendation_text(recommendation: dict,
                                      lang: str = "ru") -> str:  # Добавил lang для возможных будущих локализаций здесь
    """
    Формирует красивый текстовый блок для одной рекомендации.
    Тексты из recommendation УЖЕ ДОЛЖНЫ БЫТЬ на нужном языке от AI.
    Эта функция в основном про HTML форматирование и структуру.
    """
    rec_type_map_general = {"route": "🗺️", "transport_option": "🚌", "hotel": "🏨", "museum": "🏛️", "restaurant": "🍽️",
                            "event": "🎉", "activity": "🤸"}
    rec_type_default_name_key = {
        "route": "rec_type_route_default", "hotel": "rec_type_hotel_default",
        "museum": "rec_type_museum_default", "restaurant": "rec_type_restaurant_default",
        # Добавь ключи для других типов, если они нужны в get_text
    }

    rec_type = recommendation.get("type", "unknown")
    type_name_key = rec_type_default_name_key.get(rec_type, f"rec_type_{rec_type}_default")  # ключ для get_text

    # Пытаемся получить локализованное название типа, если есть, иначе используем сам тип
    # Для этого в localization.py должны быть ключи типа rec_type_route_default_ru, rec_type_route_default_en и т.д.
    # Пока что оставим простой вариант с эмодзи + название из recommendation, которое уже должно быть локализовано AI
    rec_type_display = f"{rec_type_map_general.get(rec_type, '⭐')} {recommendation.get('type_name_localized_by_ai', rec_type.capitalize())}"
    # ^ AI должен вернуть локализованное название типа в поле type_name_localized_by_ai, если мы этого хотим,
    # но проще, если AI сам локализует поле "name" рекомендации, а тип мы обрабатываем здесь.
    # Оставим как было: эмодзи + name (которое уже от AI на нужном языке)

    text_parts = [
        f"<b>{rec_type_map_general.get(rec_type, '⭐')}: {recommendation.get('name', get_text('text_no_name', lang))}</b>"
    ]

    if recommendation.get('address') and str(recommendation.get('address')).lower() != "null":
        text_parts.append(f"📍 <b>{get_text('text_address', lang)}:</b> {recommendation.get('address')}")

    if recommendation.get('description'):
        text_parts.append(f"📝 <i>{recommendation.get('description')}</i>")

    details = recommendation.get("details")
    if details and isinstance(details, dict):
        detail_str_parts = []
        # ... (остальная логика для details, она уже работает с данными от AI) ...
        # Например, если AI вернул "cuisine_type": ["Итальянская", "Пицца"] на русском,
        # то так и отобразится. Если на французском, то тоже.
        # Здесь локализация нужна только для заголовков типа "Тип маршрута:", "Удобства:"
        if recommendation.get("type") == "route" and details.get("route_type"):
            detail_str_parts.append(f"{get_text('detail_route_type', lang)}: {details['route_type']}")
        if recommendation.get("type") == "route" and details.get("stops"):
            stops_str = ", ".join([s.get('name', get_text('text_stop', lang)) for s in details['stops'][:3]])
            if len(details['stops']) > 3:
                stops_str += f" {get_text('text_and_more', lang)}"
            detail_str_parts.append(f"{get_text('detail_stops', lang)}: {stops_str}")
        # ... и так далее для других деталей ...

        if detail_str_parts:
            text_parts.append(f"\n<b>{get_text('text_details_header', lang)}:</b>\n" + "\n".join(
                [f"  - {d}" for d in detail_str_parts]))

    if recommendation.get('distance_or_time') and str(recommendation.get('distance_or_time')).lower() != "null":
        text_parts.append(
            f"🚗/🚶 <b>{get_text('text_distance_time', lang)}:</b> {recommendation.get('distance_or_time')}")

    price_est = recommendation.get('price_estimate')
    if price_est and str(price_est).lower() != "null":
        text_parts.append(f"💰 <b>{get_text('text_price', lang)}:</b> {price_est}")

    rating_val = recommendation.get('rating')
    if rating_val and str(rating_val).lower() != "null":
        try:  # Попытка преобразовать в float, если это число
            rating_float = float(rating_val)
            text_parts.append(f"🌟 <b>{get_text('text_rating', lang)}:</b> {rating_float:.1f}/5")
        except ValueError:  # Если не число, выводим как есть
            text_parts.append(f"🌟 <b>{get_text('text_rating', lang)}:</b> {rating_val}")

    oh = recommendation.get('opening_hours')
    if oh and str(oh).lower() != "null":
        text_parts.append(f"⏰ <b>{get_text('text_opening_hours', lang)}:</b> {oh}")

    return "\n\n".join(text_parts)


# ==============================================================================
# ОСНОВНОЙ РОУТЕР ДЛЯ ПЛАНИРОВАНИЯ ПОЕЗДКИ
# ==============================================================================
trip_planning_router = Router(name="trip_planning_router")


async def get_user_language(state: FSMContext, default_lang: str = "ru") -> str:
    """Вспомогательная функция для получения языка пользователя из состояния."""
    user_data = await state.get_data()
    return user_data.get("user_language", default_lang)


# Обработчик команды /plan_trip
@trip_planning_router.message(Command("plan_trip"))
async def cmd_plan_trip(message: Message, state: FSMContext):
    lang = await get_user_language(state)

    await message.answer(
        get_text("start_planning_prompt", lang) + "\n\n" +
        get_text("step1_location_prompt", lang),
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TripPlanning.waiting_for_location)
    logging.info(
        f"Пользователь {message.from_user.id} начал планирование ({lang}). Переведен в состояние waiting_for_location.")


# Обработчик для получения ответа на вопрос о локации (текстовый ввод)
@trip_planning_router.message(TripPlanning.waiting_for_location, F.text)
async def process_location_text(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    logging.info(f"СРАБОТАЛ process_location_text для пользователя {message.from_user.id} ({lang})")

    await state.update_data(user_location_text=message.text.strip(), user_location_geo=None)
    user_data = await state.get_data()  # Обновленные данные
    logging.info(f"Данные от пользователя {message.from_user.id} ({lang}) после ввода текстовой локации: {user_data}")

    await message.answer(get_text("location_received_text", lang, location_text=message.text))
    await _ask_for_interests(message, state, lang)  # Передаем lang


# Обработчик для получения геолокации от пользователя
@trip_planning_router.message(TripPlanning.waiting_for_location, F.content_type == ContentType.LOCATION)
async def process_location_geo(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    logging.info(f"СРАБОТАЛ process_location_geo для пользователя {message.from_user.id} ({lang})")

    user_latitude = message.location.latitude
    user_longitude = message.location.longitude

    await state.update_data(user_location_geo=[user_latitude, user_longitude], user_location_text=None)
    user_data = await state.get_data()  # Обновленные данные
    logging.info(
        f"Пользователь {message.from_user.id} ({lang}) отправил геолокацию: [{user_latitude}, {user_longitude}]. Данные state: {user_data}")

    await message.answer(
        get_text("location_geo_received_text", lang, latitude=user_latitude, longitude=user_longitude)
    )
    await _ask_for_interests(message, state, lang)  # Передаем lang


async def _ask_for_interests(message: Message, state: FSMContext, lang: str):  # Принимает lang
    """Вспомогательная функция для вопроса об интересах."""
    await message.answer(get_text("step2_interests_prompt", lang))
    await state.set_state(TripPlanning.waiting_for_interests)
    logging.info(f"Пользователь {message.from_user.id} ({lang}) переведен в состояние waiting_for_interests.")


# Обработчик для получения ответа на вопрос об интересах
@trip_planning_router.message(TripPlanning.waiting_for_interests, F.text)
async def process_interests(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    await state.update_data(user_interests_text=message.text.strip())
    user_data = await state.get_data()
    logging.info(f"Данные от пользователя {message.from_user.id} ({lang}) после ввода интересов: {user_data}")

    budget_buttons = [
        [InlineKeyboardButton(text=get_text("budget_option_low", lang), callback_data="budget_low")],
        [InlineKeyboardButton(text=get_text("budget_option_mid", lang), callback_data="budget_mid")],
        [InlineKeyboardButton(text=get_text("budget_option_premium", lang), callback_data="budget_premium")]
    ]
    budget_keyboard = InlineKeyboardMarkup(inline_keyboard=budget_buttons)

    await message.answer(
        get_text("interests_received_text", lang, interests_text=message.text) + "\n\n" +
        get_text("step3_budget_prompt", lang),
        reply_markup=budget_keyboard
    )
    await state.set_state(TripPlanning.waiting_for_budget)
    logging.info(f"Пользователь {message.from_user.id} ({lang}) переведен в состояние waiting_for_budget.")


# Обработчик для нажатия кнопки бюджета
@trip_planning_router.callback_query(TripPlanning.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget_callback(callback_query: CallbackQuery, state: FSMContext):
    lang = await get_user_language(state)
    selected_budget_code = callback_query.data.split("_")[1]
    await state.update_data(user_budget=selected_budget_code)

    user_data = await state.get_data()
    logging.info(f"Данные от пользователя {callback_query.from_user.id} ({lang}) после выбора бюджета: {user_data}")

    # Получаем локализованное название бюджета для сообщения
    budget_display_name = ""
    if selected_budget_code == "low":
        budget_display_name = get_text("budget_option_low", lang)
    elif selected_budget_code == "mid":
        budget_display_name = get_text("budget_option_mid", lang)
    elif selected_budget_code == "premium":
        budget_display_name = get_text("budget_option_premium", lang)

    # Удаляем эмодзи из budget_display_name, если он там есть, для чистоты сообщения
    budget_display_name_cleaned = budget_display_name.split(" ", 1)[
        -1] if " " in budget_display_name else budget_display_name

    await callback_query.message.edit_text(
        get_text("budget_selected_text", lang, selected_budget=budget_display_name_cleaned) + "\n\n" +
        get_text("step4_dates_prompt", lang)
    )
    await callback_query.answer(
        text=get_text("budget_selected_text", lang, selected_budget=budget_display_name_cleaned), show_alert=False)
    await state.set_state(TripPlanning.waiting_for_trip_dates)
    logging.info(f"Пользователь {callback_query.from_user.id} ({lang}) переведен в состояние waiting_for_trip_dates.")


# Обработчик для получения ответа на вопрос о датах поездки
@trip_planning_router.message(TripPlanning.waiting_for_trip_dates, F.text)
async def process_trip_dates(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    await state.update_data(user_trip_dates_text=message.text.strip())
    user_data = await state.get_data()
    logging.info(f"Данные от пользователя {message.from_user.id} ({lang}) после ввода дат: {user_data}")

    await message.answer(
        get_text("dates_received_text", lang, dates_text=message.text) + "\n\n" +
        get_text("step5_transport_prompt", lang)
    )
    await state.set_state(TripPlanning.waiting_for_transport_prefs)
    logging.info(f"Пользователь {message.from_user.id} ({lang}) переведен в состояние waiting_for_transport_prefs.")


# Обработчик для получения ответа на вопрос о предпочтениях по транспорту
@trip_planning_router.message(TripPlanning.waiting_for_transport_prefs, F.text)
async def process_transport_prefs(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(user_transport_prefs_text=message.text.strip())
    final_user_data = await state.get_data()
    lang = final_user_data.get("user_language", "ru")  # Получаем язык из финальных данных
    logging.info(f"Все собранные данные от пользователя {message.from_user.id} ({lang}): {final_user_data}")

    await message.answer(
        get_text("transport_received_text", lang, transport_text=message.text) + "\n\n" +
        get_text("all_data_collected_prompt", lang)
    )
    await state.clear()  # Очищаем состояние FSM после сбора всех данных

    recommendations_json, accompanying_text = await get_travel_recommendations(final_user_data)

    if recommendations_json and accompanying_text:
        # Сопроводительный текст уже должен быть на нужном языке от Gemini
        await message.answer(accompanying_text)

        if "recommendations" in recommendations_json and isinstance(recommendations_json["recommendations"], list):
            for rec in recommendations_json["recommendations"]:
                if not isinstance(rec, dict):  # Проверка, что каждый элемент - словарь
                    logging.warning(f"Некорректный элемент в списке recommendations: {rec}")
                    continue

                # Передаем язык в функцию форматирования
                formatted_text = await _format_recommendation_text(rec, lang)

                buttons = []
                button_book_text = get_text("button_book_tickets", lang)
                button_map_text = get_text("button_on_map", lang)

                booking_url = rec.get('booking_link')
                if booking_url and isinstance(booking_url,
                                              str) and booking_url.strip().lower() != "null" and booking_url.strip() != "":
                    buttons.append(InlineKeyboardButton(text=button_book_text, url=booking_url))

                coords = rec.get('coordinates')
                if coords and isinstance(coords, list) and len(coords) == 2:
                    try:
                        # Убедимся, что координаты - числа
                        lat, lon = float(coords[0]), float(coords[1])
                        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        buttons.append(InlineKeyboardButton(text=button_map_text, url=maps_url))
                    except (ValueError, TypeError):
                        logging.warning(
                            f"Некорректные координаты для кнопки 'На карте': {coords} в рекомендации: {rec.get('id')}")

                reply_markup = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

                images = rec.get("images", [])
                photo_sent = False
                if images and isinstance(images, list) and images and isinstance(images[0], str) and images[
                    0].strip().lower() != "null" and images[0].strip() != "":
                    try:
                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=images[0],
                            caption=formatted_text,
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                        photo_sent = True
                    except Exception as e:
                        logging.warning(
                            f"Ошибка отправки фото {images[0]} для rec_id {rec.get('id')}: {e}. Попытка отправить только текст.")

                if not photo_sent:
                    await message.answer(formatted_text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await message.answer(get_text("no_recommendations_in_response_text", lang))
    else:
        # accompanying_text здесь может содержать сообщение об ошибке от get_travel_recommendations
        error_key = "ai_response_error_text"  # Ключ по умолчанию
        error_details = ""
        if accompanying_text:
            if " некорректный JSON" in accompanying_text:
                error_key = "ai_json_decode_error_text"
                try:  # Пытаемся извлечь детали ошибки из сообщения
                    error_details = accompanying_text.split("(Ошибка: ", 1)[1].rstrip(")")
                except IndexError:
                    error_details = "детали неизвестны"
            elif "Непредвиденная ошибка" in accompanying_text:
                error_key = "ai_unexpected_error_text"
                try:
                    error_details = accompanying_text.split(": ", 1)[1].rstrip(".")
                except IndexError:
                    error_details = "детали неизвестны"
            elif "неверном формате" in accompanying_text:  # "AI вернул данные в неверном формате"
                error_key = "ai_unexpected_format_text"

        await message.answer(get_text(error_key, lang, error_details=error_details, error_type=error_details))

    logging.info(f"Пользователь {message.from_user.id} ({lang}) получил ответ от AI. FSM состояние очищено.")