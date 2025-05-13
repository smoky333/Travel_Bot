import logging
from typing import Union, Dict, Any, List
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, \
    ContentType
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.trip_planning_states import TripPlanning
from utils.ai_integration import get_travel_recommendations
from utils.localization import get_text


# from database.models import FeedbackType
# from database import crud

async def _format_recommendation_text(recommendation: dict, lang: str = "ru") -> str:
    # КОД ФУНКЦИИ _format_recommendation_text ОСТАЕТСЯ ТЕМ ЖЕ, ЧТО И В ПРЕДЫДУЩЕМ ОТВЕТЕ
    # (Я его здесь сократил для краткости полного файла)
    logging.debug(
        f"Форматирование рекомендации (lang={lang}): ID={recommendation.get('id')}, Тип={recommendation.get('type')}")
    rec_type_map_general = {"route": "🗺️", "hotel": "🏨", "museum": "🏛️", "restaurant": "🍽️", "event": "🎉",
                            "activity": "🤸", "transport_option": "🚌"}
    rec_type = recommendation.get("type", "unknown")
    name_from_ai = recommendation.get('name', get_text('text_no_name', lang))
    text_parts = [f"<b>{rec_type_map_general.get(rec_type, '⭐')}: {name_from_ai}</b>"]
    address = recommendation.get('address')
    if address and isinstance(address, str) and address.lower() != "null" and address.strip() != "": text_parts.append(
        f"📍 <b>{get_text('text_address', lang)}:</b> {address}")
    description = recommendation.get('description')
    if description and isinstance(description, str) and description.strip() != "": text_parts.append(
        f"📝 <i>{description}</i>")
    details = recommendation.get("details")
    detail_str_parts = []
    if details and isinstance(details, dict) and details:
        if rec_type == "route":
            route_type_val = details.get("route_type")
            if route_type_val and isinstance(route_type_val, str) and route_type_val.strip(): detail_str_parts.append(
                f"<b>{get_text('detail_route_type', lang)}:</b> {route_type_val}")
            stops_list = details.get("stops")
            if stops_list and isinstance(stops_list, list) and stops_list:
                stops_names = [s['name'] for s in stops_list[:3] if isinstance(s, dict) and s.get("name")]
                if stops_names:
                    stops_text = " → ".join(stops_names)
                    if len(stops_list) > 3: stops_text += f" {get_text('text_and_more', lang)}"
                    detail_str_parts.append(f"<b>{get_text('detail_stops', lang)}:</b> {stops_text}")
        elif rec_type == "hotel":  # ... и так далее, вся твоя логика форматирования деталей ...
            stars_value = details.get("stars")
            if stars_value is not None and str(stars_value).lower() != 'null':
                try:
                    stars_num = int(stars_value)
                    if 0 < stars_num <= 5:
                        detail_str_parts.append(
                            f"<b>{get_text('detail_hotel_stars', lang)}:</b> {'⭐' * stars_num} ({stars_num})")
                    elif stars_num != 0:
                        detail_str_parts.append(f"<b>{get_text('detail_hotel_stars', lang)}:</b> {stars_value}")
                except (ValueError, TypeError):
                    if isinstance(stars_value, str) and str(stars_value).strip(): detail_str_parts.append(
                        f"<b>{get_text('detail_hotel_stars', lang)}:</b> {stars_value}")
            amenities = details.get("amenities")
            if amenities and isinstance(amenities, list) and amenities:
                amenities_text = ", ".join(amenities[:4])
                if len(amenities) > 4: amenities_text += f" {get_text('text_and_more', lang)}"
                detail_str_parts.append(f"<b>{get_text('detail_hotel_amenities', lang)}:</b> {amenities_text}")
        elif rec_type == "restaurant":
            cuisine_types = details.get("cuisine_type")
            if cuisine_types:
                if isinstance(cuisine_types, list) and cuisine_types:
                    detail_str_parts.append(
                        f"<b>{get_text('detail_restaurant_cuisine', lang)}:</b> {', '.join(cuisine_types)}")
                elif isinstance(cuisine_types, str) and cuisine_types.strip() and cuisine_types.lower() != 'null':
                    detail_str_parts.append(f"<b>{get_text('detail_restaurant_cuisine', lang)}:</b> {cuisine_types}")
            average_bill = details.get("average_bill")
            if average_bill and isinstance(average_bill,
                                           str) and average_bill.lower() != 'null' and average_bill.strip() != "": detail_str_parts.append(
                f"<b>{get_text('detail_restaurant_avg_bill', lang)}:</b> {average_bill}")
        elif rec_type == "event":
            event_dates = details.get("event_dates")
            if event_dates:
                if isinstance(event_dates, list) and event_dates:
                    detail_str_parts.append(f"<b>{get_text('detail_event_dates', lang)}:</b> {', '.join(event_dates)}")
                elif isinstance(event_dates, str) and event_dates.strip() and event_dates.lower() != 'null':
                    detail_str_parts.append(f"<b>{get_text('detail_event_dates', lang)}:</b> {event_dates}")
            ticket_info = details.get("ticket_info")
            if ticket_info and isinstance(ticket_info,
                                          str) and ticket_info.lower() != 'null' and ticket_info.strip() != "": detail_str_parts.append(
                f"<b>{get_text('detail_ticket_info', lang)}:</b> {ticket_info}")
        elif rec_type in ["museum", "activity"]:
            ticket_info = details.get("ticket_info")
            if ticket_info and isinstance(ticket_info,
                                          str) and ticket_info.lower() != 'null' and ticket_info.strip() != "": detail_str_parts.append(
                f"<b>{get_text('detail_ticket_info', lang)}:</b> {ticket_info}")
    if detail_str_parts: text_parts.append(
        f"\n<b>{get_text('text_details_header', lang)}:</b>\n" + "\n".join([f"  • {d}" for d in detail_str_parts]))
    dist_time = recommendation.get('distance_or_time')
    if dist_time and isinstance(dist_time,
                                str) and dist_time.lower() != "null" and dist_time.strip() != "": text_parts.append(
        f"🚗/🚶 <b>{get_text('text_distance_time', lang)}:</b> {dist_time}")
    price_est = recommendation.get('price_estimate')
    if price_est and isinstance(price_est,
                                str) and price_est.lower() != "null" and price_est.strip() != "": text_parts.append(
        f"💰 <b>{get_text('text_price', lang)}:</b> {price_est}")
    rating_val = recommendation.get('rating')
    if rating_val is not None and str(rating_val).lower() != "null":
        try:
            rating_float = float(rating_val)
            if rating_float > 0:
                text_parts.append(f"🌟 <b>{get_text('text_rating', lang)}:</b> {rating_float:.1f}/5")
            elif isinstance(rating_val, str) and rating_val.strip() and rating_val.strip().lower() not in ["0", "0.0",
                                                                                                           "null"]:
                text_parts.append(f"🌟 <b>{get_text('text_rating', lang)}:</b> {rating_val}")
        except (ValueError, TypeError):
            if isinstance(rating_val,
                          str) and rating_val.strip() and rating_val.strip().lower() != "null": text_parts.append(
                f"🌟 <b>{get_text('text_rating', lang)}:</b> {rating_val}")
    oh = recommendation.get('opening_hours')
    if oh and isinstance(oh, str) and oh.lower() != "null" and oh.strip() != "": text_parts.append(
        f"⏰ <b>{get_text('text_opening_hours', lang)}:</b> {oh}")
    return "\n\n".join(text_parts)


trip_planning_router = Router(name="trip_planning_router")


async def get_user_language(state: FSMContext, default_lang: str = "ru") -> str:
    user_data = await state.get_data()
    return user_data.get("user_language", default_lang)


async def _send_recommendations_batch(
        target_message_entity: Union[Message, CallbackQuery],
        bot: Bot,
        recommendations_list: List[Dict[str, Any]],
        lang: str,
        is_more_request: bool = False
) -> List[str]:
    shown_ids_this_batch = []
    if isinstance(target_message_entity, CallbackQuery):
        chat_id = target_message_entity.message.chat.id
        base_message_id = target_message_entity.message.message_id  # Для генерации уникальных временных ID
        message_to_answer_or_send_new = target_message_entity.message
    else:
        chat_id = target_message_entity.chat.id
        base_message_id = target_message_entity.message_id
        message_to_answer_or_send_new = target_message_entity

    if not recommendations_list:  # Если список пуст (например, после фильтрации)
        no_recs_key = "ai_no_more_recommendations_found" if is_more_request else "ai_no_recommendations_found"
        await message_to_answer_or_send_new.answer(get_text(no_recs_key, lang))
        return shown_ids_this_batch

    for rec_idx, rec_data in enumerate(recommendations_list):
        if not isinstance(rec_data, dict):
            logging.warning(f"Элемент #{rec_idx} в recommendations не словарь: {rec_data}")
            continue

        rec_id_for_log = rec_data.get("id", f"temp_id_log_{rec_idx}")  # Для логов, если ID нет
        logging.info(f"--- Обработка рекомендации ID: {rec_id_for_log} ---")

        formatted_text = await _format_recommendation_text(rec_data, lang)
        buttons_row1 = []  # Кнопки Бронь/На карте
        buttons_row2 = []  # Кнопки Лайк/Дизлайк

        recommendation_id_for_feedback = rec_data.get("id")
        if not recommendation_id_for_feedback or not isinstance(recommendation_id_for_feedback,
                                                                str) or not recommendation_id_for_feedback.strip():
            id_prefix = "temp_more_rec_" if is_more_request else "temp_rec_"
            recommendation_id_for_feedback = f"{id_prefix}{chat_id}_{base_message_id}_{rec_idx}"
            logging.warning(
                f"AI не предоставил ID для рекомендации (name: {rec_data.get('name')}), используется временный: {recommendation_id_for_feedback}")
        shown_ids_this_batch.append(recommendation_id_for_feedback)

        # Формирование кнопок "Бронь/Билеты"
        booking_url_value = rec_data.get('booking_link')
        # Промпт просит JSON null, если ссылки нет. Python превратит это в None.

        # --- НАЧАЛО ПРОВЕРКИ ДЛЯ booking_url_value ---
        is_valid_booking_url_condition = False  # Флаг для отладки
        if booking_url_value:  # Шаг 1: Убедимся, что это не None и не пустая строка
            if isinstance(booking_url_value, str):  # Шаг 2: Убедимся, что это строка
                cleaned_booking_url = booking_url_value.strip()
                if cleaned_booking_url and cleaned_booking_url.lower() not in ["null",
                                                                               "none"]:  # Шаг 3: Не "null", "none" и не пустая после strip
                    if cleaned_booking_url.startswith("http://") or cleaned_booking_url.startswith(
                            "https://"):  # Шаг 4: Валидный URL
                        is_valid_booking_url_condition = True
        # --- КОНЕЦ ПРОВЕРКИ ДЛЯ booking_url_value ---

        if is_valid_booking_url_condition:
            logging.debug(
                f"Rec ID: {recommendation_id_for_feedback} - Добавляем кнопку 'Бронь/Билеты' URL: {booking_url_value}")
            buttons_row1.append(InlineKeyboardButton(text=get_text("button_book_tickets", lang),
                                                     url=booking_url_value.strip()))  # Добавил strip() для URL
        else:
            logging.debug(
                f"Rec ID: {recommendation_id_for_feedback} - НЕТ кнопки 'Бронь/Билеты'. booking_link: '{booking_url_value}' (тип: {type(booking_url_value)}), Условие: {is_valid_booking_url_condition}")

        # Формирование кнопок "На карте"
        coords_value = rec_data.get('coordinates')
        # Промпт просит список из 2 чисел или JSON null.

        # --- НАЧАЛО ПРОВЕРКИ ДЛЯ coords_value ---
        is_valid_coords_condition = False  # Флаг для отладки
        lat, lon = None, None  # Инициализируем
        if isinstance(coords_value, list) and len(coords_value) == 2:  # Шаг 1: Список из двух элементов
            try:
                val1 = coords_value[0]
                val2 = coords_value[1]
                # AI может прислать числа как строки, поэтому float() обязателен
                # Также AI может прислать строку "null" или None внутри списка
                if val1 is not None and str(val1).lower() != "null" and \
                        val2 is not None and str(val2).lower() != "null":
                    lat = float(val1)
                    lon = float(val2)
                    is_valid_coords_condition = True  # Шаг 2: Успешная конвертация в float
            except (ValueError, TypeError, IndexError) as e_coord:
                logging.warning(
                    f"Rec ID: {recommendation_id_for_feedback} - Ошибка конвертации координат: {coords_value}, ошибка: {e_coord}. Кнопка 'На карте' не будет добавлена.")
                is_valid_coords_condition = False  # Явно ставим False при ошибке
        # --- КОНЕЦ ПРОВЕРКИ ДЛЯ coords_value ---

        if is_valid_coords_condition:  # Проверяем флаг
            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            logging.debug(
                f"Rec ID: {recommendation_id_for_feedback} - Добавляем кнопку 'На карте'. Coords: [{lat},{lon}]")
            buttons_row1.append(InlineKeyboardButton(text=get_text("button_on_map", lang), url=maps_url))
        else:
            logging.debug(
                f"Rec ID: {recommendation_id_for_feedback} - НЕТ кнопки 'На карте'. coordinates: {coords_value} (тип: {type(coords_value)}), Условие: {is_valid_coords_condition}")

        buttons_row2.append(InlineKeyboardButton(text=f"👍 {get_text('button_like', lang)}",
                                                 callback_data=f"feedback_like_{recommendation_id_for_feedback}"))
        buttons_row2.append(InlineKeyboardButton(text=f"👎 {get_text('button_dislike', lang)}",
                                                 callback_data=f"feedback_dislike_{recommendation_id_for_feedback}"))

        all_buttons_rows = []
        if buttons_row1:  # Если есть кнопки в первом ряду (Бронь/На карте)
            all_buttons_rows.append(buttons_row1)
        all_buttons_rows.append(buttons_row2)  # Ряд с Лайк/Дизлайк добавляется всегда

        reply_markup = InlineKeyboardMarkup(inline_keyboard=all_buttons_rows)

        images = rec_data.get("images", [])
        photo_sent = False
        if images and isinstance(images, list) and images and isinstance(images[0], str) and images[0].strip() and \
                images[0].lower() != "null":
            try:
                await bot.send_photo(chat_id=chat_id, photo=images[0], caption=formatted_text,
                                     reply_markup=reply_markup, parse_mode="HTML")
                photo_sent = True
            except Exception as e:
                logging.warning(
                    f"Ошибка отправки фото {images[0]} для rec_id {recommendation_id_for_feedback}: {e}. Отправка текста.")

        if not photo_sent:
            await message_to_answer_or_send_new.answer(formatted_text, reply_markup=reply_markup, parse_mode="HTML")

    return shown_ids_this_batch


@trip_planning_router.message(Command("plan_trip"))
async def cmd_plan_trip(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_data = await state.get_data()
    user_language_to_keep = current_data.get('user_language')

    await state.clear()
    if user_language_to_keep:
        await state.update_data(user_language=user_language_to_keep)

    # Эти списки будут заполняться в текущей сессии.
    # liked/disliked_recommendation_ids для AI будут браться из БД (в будущем) + дополняться из state текущей сессии.
    await state.update_data(
        liked_recommendation_ids=[],
        disliked_recommendation_ids=[],
        current_session_shown_ids=[]
    )
    lang = await get_user_language(state)
    logging.info(
        f"Данные FSM после очистки и перед началом нового планирования для {user_id}: {await state.get_data()}")
    await message.answer(
        get_text("start_planning_prompt", lang) + "\n\n" +
        get_text("step1_location_prompt", lang),
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TripPlanning.waiting_for_location)


# --- Хэндлеры FSM (остаются без изменений) ---
@trip_planning_router.message(TripPlanning.waiting_for_location, F.text)
async def process_location_text(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    await state.update_data(user_location_text=message.text.strip(), user_location_geo=None)
    await message.answer(get_text("location_received_text", lang, location_text=message.text))
    await _ask_for_interests(message, state, lang)


@trip_planning_router.message(TripPlanning.waiting_for_location, F.content_type == ContentType.LOCATION)
async def process_location_geo(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    lat, lon = message.location.latitude, message.location.longitude
    await state.update_data(user_location_geo=[lat, lon], user_location_text=None)
    await message.answer(get_text("location_geo_received_text", lang, latitude=lat, longitude=lon))
    await _ask_for_interests(message, state, lang)


@trip_planning_router.message(TripPlanning.waiting_for_location)
async def log_unhandled_location_input(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    logging.warning(f"Пользователь {message.from_user.id} ({lang}) в состоянии waiting_for_location "
                    f"прислал НЕОБРАБОТАННОЕ сообщение. Тип: {message.content_type}.")


async def _ask_for_interests(message: Message, state: FSMContext, lang: str):
    await message.answer(get_text("step2_interests_prompt", lang))
    await state.set_state(TripPlanning.waiting_for_interests)


@trip_planning_router.message(TripPlanning.waiting_for_interests, F.text)
async def process_interests(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    await state.update_data(user_interests_text=message.text.strip())
    buttons = [
        [InlineKeyboardButton(text=get_text("budget_option_low", lang), callback_data="budget_low")],
        [InlineKeyboardButton(text=get_text("budget_option_mid", lang), callback_data="budget_mid")],
        [InlineKeyboardButton(text=get_text("budget_option_premium", lang), callback_data="budget_premium")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        get_text("interests_received_text", lang, interests_text=message.text) + "\n\n" +
        get_text("step3_budget_prompt", lang),
        reply_markup=keyboard
    )
    await state.set_state(TripPlanning.waiting_for_budget)


@trip_planning_router.callback_query(TripPlanning.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget_callback(callback_query: CallbackQuery, state: FSMContext):
    lang = await get_user_language(state)
    code = callback_query.data.split("_")[1]
    await state.update_data(user_budget=code)
    budget_name_key = f"budget_option_{code}"
    budget_full_name = get_text(budget_name_key, lang)
    budget_display_name_cleaned = budget_full_name.split(" ", 1)[
        -1] if " " in budget_full_name and not budget_full_name.startswith("<L10N_ERROR") else budget_full_name
    await callback_query.message.edit_text(
        get_text("budget_selected_text", lang, selected_budget=budget_display_name_cleaned) + "\n\n" +
        get_text("step4_dates_prompt", lang)
    )
    await callback_query.answer()
    await state.set_state(TripPlanning.waiting_for_trip_dates)


@trip_planning_router.message(TripPlanning.waiting_for_trip_dates, F.text)
async def process_trip_dates(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    await state.update_data(user_trip_dates_text=message.text.strip())
    await message.answer(
        get_text("dates_received_text", lang, dates_text=message.text) + "\n\n" +
        get_text("step5_transport_prompt", lang)
    )
    await state.set_state(TripPlanning.waiting_for_transport_prefs)


# --- Конец FSM хэндлеров ---

@trip_planning_router.message(TripPlanning.waiting_for_transport_prefs, F.text)
async def process_transport_prefs_and_get_initial_recs(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    await state.update_data(user_transport_prefs_text=message.text.strip())

    fsm_collected_data = await state.get_data()
    lang = fsm_collected_data.get("user_language", "ru")

    await message.answer(
        get_text("transport_received_text", lang, transport_text=message.text) + "\n\n" +
        get_text("all_data_collected_prompt", lang)
    )

    initial_ai_request_data = {
        'user_language': lang,
        'user_location_text': fsm_collected_data.get('user_location_text'),
        'user_location_geo': fsm_collected_data.get('user_location_geo'),
        'user_interests_text': fsm_collected_data.get('user_interests_text'),
        'user_budget': fsm_collected_data.get('user_budget'),
        'user_trip_dates_text': fsm_collected_data.get('user_trip_dates_text'),
        'user_transport_prefs_text': fsm_collected_data.get('user_transport_prefs_text'),
        'liked_recommendation_ids': fsm_collected_data.get('liked_recommendation_ids', []),
        'disliked_recommendation_ids': fsm_collected_data.get('disliked_recommendation_ids', []),
        'request_type': 'initial',
        'current_session_shown_ids': fsm_collected_data.get('current_session_shown_ids', [])
        # Должен быть [] после cmd_plan_trip
    }
    logging.info(f"Данные для ПЕРВОГО AI запроса от {user_id} ({lang}): {initial_ai_request_data}")

    recommendations_json, accompanying_text = await get_travel_recommendations(initial_ai_request_data)

    all_shown_ids_this_round: List[str] = []
    recommendation_items_exist = False

    if recommendations_json and accompanying_text:
        await message.answer(accompanying_text)
        recommendation_items_from_ai = recommendations_json.get("recommendations")

        if isinstance(recommendation_items_from_ai, list):
            # Для первого запроса фильтрация не так критична, т.к. current_session_shown_ids должен быть пуст,
            # но оставим для консистентности и на случай, если AI вдруг повторит что-то из истории (хотя промпт это запрещает)
            already_shown_ids_set = set(initial_ai_request_data['current_session_shown_ids'])
            unique_recs_to_show = []
            if recommendation_items_from_ai:  # Только если список не пуст
                for rec_item in recommendation_items_from_ai:
                    rec_id = rec_item.get("id")
                    if rec_id and rec_id not in already_shown_ids_set:
                        unique_recs_to_show.append(rec_item)
                    elif rec_id:  # Дубликат
                        logging.info(
                            f"AI (initial) вернул ID, который уже есть в (пустом) shown_ids: {rec_id}. Игнорируем.")
                    elif not rec_id:  # Нет ID
                        unique_recs_to_show.append(rec_item)

            if unique_recs_to_show:
                recommendation_items_exist = True
                all_shown_ids_this_round = await _send_recommendations_batch(
                    message, bot, unique_recs_to_show, lang, is_more_request=False
                )
            # Если unique_recs_to_show пуст, _send_recommendations_batch вызовет get_text("ai_no_recommendations_found", lang)
            elif not unique_recs_to_show and recommendation_items_from_ai:  # Были только дубликаты или невалидные
                await message.answer(get_text("ai_no_recommendations_found", lang))

        else:  # recommendations не список или отсутствует
            logging.error(f"Ключ 'recommendations' отсутствует или не список в ответе AI: {recommendations_json}")
            await message.answer(get_text("no_recommendations_in_response_text", lang))
    else:  # Ошибка от get_travel_recommendations
        error_key = "ai_response_error_text"
        # ... (обработка ошибок, как и раньше) ...
        error_details = ""
        if accompanying_text:
            if " некорректный JSON" in accompanying_text:
                error_key = "ai_json_decode_error_text"
            elif "Непредвиденная ошибка" in accompanying_text:
                error_key = "ai_unexpected_error_text"
            elif "неверном формате" in accompanying_text:
                error_key = "ai_unexpected_format_text"
            try:
                error_details = accompanying_text.split("Ошибка: ", 1)[1].rstrip(
                    ")") if "(Ошибка: " in accompanying_text else accompanying_text.split(": ", 1)[-1].rstrip(".")
            except IndexError:
                error_details = accompanying_text if len(accompanying_text) < 50 else "детали см. в логах"
        await message.answer(get_text(error_key, lang, error_details=error_details, error_type=error_details))

    await state.update_data(current_session_shown_ids=all_shown_ids_this_round)

    if recommendation_items_exist:
        more_recs_button = InlineKeyboardButton(text=get_text("button_more_recs", lang),
                                                callback_data="more_recs_request")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[more_recs_button]])
        await message.answer(get_text("prompt_more_recs_available", lang), reply_markup=keyboard)
    elif recommendations_json and not recommendation_items_exist:  # Был ответ от AI, но рекомендации пустые (или все отфильтрованы)
        await message.answer(get_text("ai_no_recommendations_found", lang))

    await state.set_state(None)
    logging.info(f"Пользователь {user_id} ({lang}) получил ПЕРВЫЙ набор. Данные в state: {await state.get_data()}")


@trip_planning_router.callback_query(F.data == "more_recs_request")
async def process_more_recs_request(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback_query.from_user.id
    await callback_query.answer()

    current_state_data = await state.get_data()
    lang = current_state_data.get("user_language", "ru")

    location_present = current_state_data.get('user_location_text') or current_state_data.get('user_location_geo')
    if not location_present or not current_state_data.get('user_interests_text'):
        logging.warning(
            f"Запрос 'еще рекомендаций' от {user_id}, но state не содержит FSM данных. State: {current_state_data}")
        await callback_query.message.answer(get_text("error_state_lost_for_more_recs", lang))
        return

    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logging.info(
            f"Не удалось убрать кнопку 'Еще рекомендации' с сообщения {callback_query.message.message_id} для {user_id}: {e}")

    await callback_query.message.answer(get_text("generating_more_recs_prompt", lang))

    # Собираем все необходимые данные из state
    ai_request_data_for_more = {
        'user_language': lang,
        'user_location_text': current_state_data.get('user_location_text'),
        'user_location_geo': current_state_data.get('user_location_geo'),
        'user_interests_text': current_state_data.get('user_interests_text'),
        'user_budget': current_state_data.get('user_budget'),
        'user_trip_dates_text': current_state_data.get('user_trip_dates_text'),
        'user_transport_prefs_text': current_state_data.get('user_transport_prefs_text'),
        'liked_recommendation_ids': current_state_data.get('liked_recommendation_ids', []),
        'disliked_recommendation_ids': current_state_data.get('disliked_recommendation_ids', []),
        'current_session_shown_ids': current_state_data.get('current_session_shown_ids', []),
        # Это поле будет использовано в _prepare_user_data_for_prompt для previously_shown_ids
        'request_type': 'more_options'
    }
    logging.info(f"Данные для AI ('еще' рекомендации) для {user_id}: {ai_request_data_for_more}")

    recommendations_json, accompanying_text = await get_travel_recommendations(ai_request_data_for_more)

    newly_shown_ids_this_batch: List[str] = []
    new_recommendation_items_exist = False

    if recommendations_json and accompanying_text:
        await callback_query.message.answer(accompanying_text)

        all_new_recs_from_ai = recommendations_json.get("recommendations")
        if isinstance(all_new_recs_from_ai, list):
            already_shown_ids_set = set(current_state_data.get('current_session_shown_ids', []))
            unique_new_recs_to_show = []
            if all_new_recs_from_ai:  # Только если список не пуст
                for rec_item in all_new_recs_from_ai:
                    rec_id = rec_item.get("id")
                    if rec_id and rec_id not in already_shown_ids_set:
                        unique_new_recs_to_show.append(rec_item)
                    elif rec_id:
                        logging.info(f"AI (more_options) вернул ID, который уже был показан: {rec_id}. Фильтруем.")
                    elif not rec_id:
                        unique_new_recs_to_show.append(rec_item)

            if unique_new_recs_to_show:
                new_recommendation_items_exist = True
                newly_shown_ids_this_batch = await _send_recommendations_batch(
                    callback_query, bot, unique_new_recs_to_show, lang, is_more_request=True
                )
            # Если unique_new_recs_to_show пуст, _send_recommendations_batch обработает это и отправит "больше ничего не найдено"
            elif not unique_new_recs_to_show and all_new_recs_from_ai:  # Были только дубликаты
                await callback_query.message.answer(get_text("ai_no_more_recommendations_found", lang))


        else:
            logging.error(f"Ключ 'recommendations' отсутствует или не список в 'еще' ответе AI: {recommendations_json}")
            await callback_query.message.answer(get_text("no_recommendations_in_response_text", lang))
    else:
        error_key = "ai_response_error_text"  # ... (обработка ошибок)
        error_details = ""
        if accompanying_text:
            if " некорректный JSON" in accompanying_text:
                error_key = "ai_json_decode_error_text"
            elif "Непредвиденная ошибка" in accompanying_text:
                error_key = "ai_unexpected_error_text"
            elif "неверном формате" in accompanying_text:
                error_key = "ai_unexpected_format_text"
            try:
                error_details = accompanying_text.split("Ошибка: ", 1)[1].rstrip(
                    ")") if "(Ошибка: " in accompanying_text else accompanying_text.split(": ", 1)[-1].rstrip(".")
            except IndexError:
                error_details = accompanying_text if len(accompanying_text) < 50 else "детали см. в логах"
        await callback_query.message.answer(
            get_text(error_key, lang, error_details=error_details, error_type=error_details))

    if new_recommendation_items_exist:
        previously_shown_ids = current_state_data.get('current_session_shown_ids', [])
        updated_shown_ids = list(set(previously_shown_ids + newly_shown_ids_this_batch))
        await state.update_data(current_session_shown_ids=updated_shown_ids)

        more_recs_button = InlineKeyboardButton(text=get_text("button_more_recs", lang),
                                                callback_data="more_recs_request")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[more_recs_button]])
        await callback_query.message.answer(get_text("prompt_more_recs_available", lang), reply_markup=keyboard)
    # Если new_recommendation_items_exist is False, но был ответ от AI,
    # то сообщение "ai_no_more_recommendations_found" уже было отправлено из _send_recommendations_batch или после фильтрации.
    # Не нужно отправлять его здесь еще раз, если только не было ошибки от AI.
    elif recommendations_json and not new_recommendation_items_exist and not newly_shown_ids_this_batch:
        # Этот блок сработает, если unique_new_recs_to_show был пуст Изначально, а не после фильтрации.
        # _send_recommendations_batch уже должен был обработать пустой список.
        # Но на всякий случай, если AI вернул { "recommendations": [] }
        if isinstance(recommendations_json.get("recommendations"), list) and not recommendations_json.get(
                "recommendations"):
            await callback_query.message.answer(get_text("ai_no_more_recommendations_found", lang))

    logging.info(f"Пользователь {user_id} ({lang}) получил ДОП. набор. Данные в state: {await state.get_data()}")


async def _update_feedback_buttons(callback_query: CallbackQuery, recommendation_id: str, feedback_message_key: str,
                                   lang: str):
    # КОД ФУНКЦИИ _update_feedback_buttons ОСТАЕТСЯ ТЕМ ЖЕ, ЧТО И В ПРЕДЫДУЩЕМ ОТВЕТЕ
    feedback_message = get_text(feedback_message_key, lang)
    new_buttons_list = []
    if callback_query.message and callback_query.message.reply_markup:
        for row_idx, row in enumerate(callback_query.message.reply_markup.inline_keyboard):
            new_row = []
            is_feedback_row = False
            for button in row:
                if button.callback_data and \
                        (button.callback_data.startswith(f"feedback_like_{recommendation_id}") or \
                         button.callback_data.startswith(f"feedback_dislike_{recommendation_id}")):
                    is_feedback_row = True
                    break
                new_row.append(button)
            if not is_feedback_row and new_row:
                new_buttons_list.append(new_row)
            elif is_feedback_row:
                logging.debug(f"Ряд кнопок для {recommendation_id} (лайк/дизлайк) удален.")
    new_reply_markup = InlineKeyboardMarkup(inline_keyboard=new_buttons_list) if new_buttons_list else None
    try:
        if new_reply_markup:
            await callback_query.message.edit_reply_markup(reply_markup=new_reply_markup)
        else:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.answer(feedback_message, show_alert=False)
    except Exception as e:
        logging.error(f"Ошибка при обновлении кнопок после фидбека для {recommendation_id}: {e}", exc_info=True)
        await callback_query.answer(feedback_message, show_alert=True)


@trip_planning_router.callback_query(F.data.startswith("feedback_like_"))
async def process_feedback_like(callback_query: CallbackQuery, state: FSMContext):  # , session: AsyncSession):
    # КОД ФУНКЦИИ process_feedback_like ОСТАЕТСЯ ТЕМ ЖЕ, ЧТО И В ПРЕДЫДУЩЕМ ОТВЕТЕ
    recommendation_id = callback_query.data[len("feedback_like_"):]
    lang = await get_user_language(state)
    current_data = await state.get_data()
    liked_ids: List[str] = current_data.get("liked_recommendation_ids", [])
    disliked_ids: List[str] = current_data.get("disliked_recommendation_ids", [])
    if recommendation_id not in liked_ids: liked_ids.append(recommendation_id)
    if recommendation_id in disliked_ids: disliked_ids.remove(recommendation_id)
    await state.update_data(liked_recommendation_ids=liked_ids, disliked_recommendation_ids=disliked_ids)
    logging.info(
        f"Пользователь {callback_query.from_user.id} ({lang}) ЛАЙКНУЛ ID: {recommendation_id}. State: {await state.get_data()}")
    await _update_feedback_buttons(callback_query, recommendation_id, "feedback_thanks_like", lang)


@trip_planning_router.callback_query(F.data.startswith("feedback_dislike_"))
async def process_feedback_dislike(callback_query: CallbackQuery, state: FSMContext):  # , session: AsyncSession):
    # КОД ФУНКЦИИ process_feedback_dislike ОСТАЕТСЯ ТЕМ ЖЕ, ЧТО И В ПРЕДЫДУЩЕМ ОТВЕТЕ
    recommendation_id = callback_query.data[len("feedback_dislike_"):]
    lang = await get_user_language(state)
    current_data = await state.get_data()
    liked_ids: List[str] = current_data.get("liked_recommendation_ids", [])
    disliked_ids: List[str] = current_data.get("disliked_recommendation_ids", [])
    if recommendation_id not in disliked_ids: disliked_ids.append(recommendation_id)
    if recommendation_id in liked_ids: liked_ids.remove(recommendation_id)
    await state.update_data(liked_recommendation_ids=liked_ids, disliked_recommendation_ids=disliked_ids)
    logging.info(
        f"Пользователь {callback_query.from_user.id} ({lang}) ДИЗЛАЙКНУЛ ID: {recommendation_id}. State: {await state.get_data()}")
    await _update_feedback_buttons(callback_query, recommendation_id, "feedback_thanks_dislike", lang)