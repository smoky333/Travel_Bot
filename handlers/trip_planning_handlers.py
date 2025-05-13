import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, \
    ContentType
from aiogram.fsm.context import FSMContext

from handlers.trip_planning_states import TripPlanning
from utils.ai_integration import get_travel_recommendations
from utils.localization import get_text


# ==============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ФОРМАТИРОВАНИЯ РЕКОМЕНДАЦИИ
# ==============================================================================
async def _format_recommendation_text(recommendation: dict, lang: str = "ru") -> str:
    logging.debug(
        f"Форматирование рекомендации (lang={lang}): ID={recommendation.get('id')}, Тип={recommendation.get('type')}")
    # logging.debug(f"Полные детали для форматирования: {recommendation.get('details')}") # Раскомментировать для глубокой отладки деталей

    rec_type_map_general = {
        "route": "🗺️", "hotel": "🏨", "museum": "🏛️",
        "restaurant": "🍽️", "event": "🎉", "activity": "🤸",
        "transport_option": "🚌"
    }
    rec_type = recommendation.get("type", "unknown")

    name_from_ai = recommendation.get('name', get_text('text_no_name', lang))
    text_parts = [f"<b>{rec_type_map_general.get(rec_type, '⭐')}: {name_from_ai}</b>"]

    address = recommendation.get('address')
    if address and str(address).lower() != "null" and str(address).strip() != "":
        text_parts.append(f"📍 <b>{get_text('text_address', lang)}:</b> {address}")

    description = recommendation.get('description')
    if description and str(description).strip() != "":  # Добавил проверку на непустую строку
        text_parts.append(f"📝 <i>{description}</i>")

    details = recommendation.get("details")
    detail_str_parts = []

    if details and isinstance(details, dict) and details:
        logging.debug(f"Обработка 'details' для rec_id {recommendation.get('id')}: {details}")
        if rec_type == "route":
            route_type_val = details.get("route_type")
            if route_type_val and str(route_type_val).strip():
                detail_str_parts.append(f"<b>{get_text('detail_route_type', lang)}:</b> {route_type_val}")

            stops_list = details.get("stops")
            if stops_list and isinstance(stops_list, list) and stops_list:
                stops_names = []
                for stop_item in stops_list[:3]:
                    if isinstance(stop_item, dict) and stop_item.get("name"):
                        stops_names.append(stop_item['name'])
                if stops_names:
                    stops_text = " → ".join(stops_names)
                    if len(stops_list) > 3:
                        stops_text += f" {get_text('text_and_more', lang)}"
                    detail_str_parts.append(f"<b>{get_text('detail_stops', lang)}:</b> {stops_text}")

        elif rec_type == "hotel":
            stars_value = details.get("stars")
            if stars_value is not None and str(stars_value).lower() != 'null':  # Проверяем и на None
                try:
                    stars_num = int(stars_value)
                    if 0 < stars_num <= 5:
                        detail_str_parts.append(
                            f"<b>{get_text('detail_hotel_stars', lang)}:</b> {'⭐' * stars_num} ({stars_num})")
                    elif stars_num != 0:  # Если 0, не выводим
                        detail_str_parts.append(f"<b>{get_text('detail_hotel_stars', lang)}:</b> {stars_value}")
                except (ValueError, TypeError):
                    if str(stars_value).strip():  # Выводим как строку, если не пусто
                        detail_str_parts.append(f"<b>{get_text('detail_hotel_stars', lang)}:</b> {stars_value}")

            amenities = details.get("amenities")
            if amenities and isinstance(amenities, list) and amenities:
                amenities_text = ", ".join(amenities[:4])
                if len(amenities) > 4:
                    amenities_text += f" {get_text('text_and_more', lang)}"
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
            if average_bill and str(average_bill).lower() != 'null' and str(average_bill).strip() != "":
                detail_str_parts.append(f"<b>{get_text('detail_restaurant_avg_bill', lang)}:</b> {average_bill}")

        elif rec_type == "event":
            event_dates = details.get("event_dates")
            if event_dates:
                if isinstance(event_dates, list) and event_dates:
                    detail_str_parts.append(f"<b>{get_text('detail_event_dates', lang)}:</b> {', '.join(event_dates)}")
                elif isinstance(event_dates, str) and event_dates.strip() and event_dates.lower() != 'null':
                    detail_str_parts.append(f"<b>{get_text('detail_event_dates', lang)}:</b> {event_dates}")

            ticket_info = details.get("ticket_info")
            if ticket_info and str(ticket_info).lower() != 'null' and str(ticket_info).strip() != "":
                detail_str_parts.append(f"<b>{get_text('detail_ticket_info', lang)}:</b> {ticket_info}")

        elif rec_type in ["museum", "activity"]:
            ticket_info = details.get("ticket_info")
            if ticket_info and str(ticket_info).lower() != 'null' and str(ticket_info).strip() != "":
                detail_str_parts.append(f"<b>{get_text('detail_ticket_info', lang)}:</b> {ticket_info}")

    if detail_str_parts:
        text_parts.append(
            f"\n<b>{get_text('text_details_header', lang)}:</b>\n" + "\n".join([f"  • {d}" for d in detail_str_parts]))

    dist_time = recommendation.get('distance_or_time')
    if dist_time and str(dist_time).lower() != "null" and str(dist_time).strip() != "":
        text_parts.append(f"🚗/🚶 <b>{get_text('text_distance_time', lang)}:</b> {dist_time}")

    price_est = recommendation.get('price_estimate')
    if price_est and str(price_est).lower() != "null" and str(price_est).strip() != "":
        text_parts.append(f"💰 <b>{get_text('text_price', lang)}:</b> {price_est}")

    rating_val = recommendation.get('rating')
    if rating_val is not None and str(rating_val).lower() != "null":  # Проверяем и на None
        try:
            rating_float = float(rating_val)
            if rating_float > 0:  # Не выводим рейтинг 0.0
                text_parts.append(f"🌟 <b>{get_text('text_rating', lang)}:</b> {rating_float:.1f}/5")
            elif isinstance(rating_val, str) and rating_val.strip() and rating_val.strip() not in ["0",
                                                                                                   "0.0"]:  # Если это нечисловая строка и не "0"
                text_parts.append(f"🌟 <b>{get_text('text_rating', lang)}:</b> {rating_val}")
        except (ValueError, TypeError):
            if str(rating_val).strip():  # Выводим как строку, если не пусто
                text_parts.append(f"🌟 <b>{get_text('text_rating', lang)}:</b> {rating_val}")

    oh = recommendation.get('opening_hours')
    if oh and str(oh).lower() != "null" and str(oh).strip() != "":
        text_parts.append(f"⏰ <b>{get_text('text_opening_hours', lang)}:</b> {oh}")

    return "\n\n".join(text_parts)


# ==============================================================================
# ОСНОВНОЙ РОУТЕР ДЛЯ ПЛАНИРОВАНИЯ ПОЕЗДКИ
# ==============================================================================
trip_planning_router = Router(name="trip_planning_router")


async def get_user_language(state: FSMContext, default_lang: str = "ru") -> str:
    user_data = await state.get_data()
    return user_data.get("user_language", default_lang)


@trip_planning_router.message(Command("plan_trip"))
async def cmd_plan_trip(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    current_data = await state.get_data()
    user_language_to_keep = current_data.get('user_language')
    liked_ids_to_keep = current_data.get('liked_recommendation_ids', [])  # Сохраняем
    disliked_ids_to_keep = current_data.get('disliked_recommendation_ids', [])  # Сохраняем

    new_state_data = {}
    if user_language_to_keep:
        new_state_data['user_language'] = user_language_to_keep
    new_state_data['liked_recommendation_ids'] = liked_ids_to_keep  # Переносим
    new_state_data['disliked_recommendation_ids'] = disliked_ids_to_keep  # Переносим

    await state.set_data(new_state_data)  # Очищаем всё, КРОМЕ языка и истории лайков
    logging.info(f"Данные FSM перед началом нового планирования (после частичной очистки): {await state.get_data()}")

    await message.answer(
        get_text("start_planning_prompt", lang) + "\n\n" +
        get_text("step1_location_prompt", lang),
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TripPlanning.waiting_for_location)
    logging.info(
        f"Пользователь {message.from_user.id} начал планирование ({lang}). Состояние: {await state.get_state()}")


@trip_planning_router.message(TripPlanning.waiting_for_location, F.text)
async def process_location_text(message: Message, state: FSMContext):
    logging.info("!!! DEBUG: ВНУТРИ process_location_text !!!")
    lang = await get_user_language(state)
    logging.info(f"process_location_text для пользователя {message.from_user.id} ({lang})")
    await state.update_data(user_location_text=message.text.strip(), user_location_geo=None)
    logging.info(f"Данные после текстовой локации: {await state.get_data()}")
    await message.answer(get_text("location_received_text", lang, location_text=message.text))
    await _ask_for_interests(message, state, lang)


@trip_planning_router.message(TripPlanning.waiting_for_location, F.content_type == ContentType.LOCATION)
async def process_location_geo(message: Message, state: FSMContext):
    logging.info("!!! DEBUG: ВНУТРИ process_location_geo !!!")
    lang = await get_user_language(state)
    logging.info(f"process_location_geo для пользователя {message.from_user.id} ({lang})")
    lat, lon = message.location.latitude, message.location.longitude
    await state.update_data(user_location_geo=[lat, lon], user_location_text=None)
    logging.info(f"Данные после геолокации: {await state.get_data()}")
    await message.answer(get_text("location_geo_received_text", lang, latitude=lat, longitude=lon))
    await _ask_for_interests(message, state, lang)


@trip_planning_router.message(TripPlanning.waiting_for_location)
async def log_unhandled_location_input(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    logging.warning(
        f"Пользователь {message.from_user.id} ({lang}) в состоянии waiting_for_location "
        f"прислал НЕОБРАБОТАННОЕ сообщение (не текст и не геолокация). Тип контента: {message.content_type}. "
        f"Текст (если есть): '{message.text}'."
    )
    # await message.answer(get_text("error_unrecognized_location_input", lang)) # Добавить ключ в localization.py


async def _ask_for_interests(message: Message, state: FSMContext, lang: str):
    await message.answer(get_text("step2_interests_prompt", lang))
    await state.set_state(TripPlanning.waiting_for_interests)
    logging.info(f"Пользователь {message.from_user.id} ({lang}) переведен в состояние: {await state.get_state()}")


@trip_planning_router.message(TripPlanning.waiting_for_interests, F.text)
async def process_interests(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    await state.update_data(user_interests_text=message.text.strip())
    logging.info(f"Данные после ввода интересов: {await state.get_data()}")
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
    logging.info(f"Пользователь {message.from_user.id} ({lang}) переведен в состояние: {await state.get_state()}")


@trip_planning_router.callback_query(TripPlanning.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget_callback(callback_query: CallbackQuery, state: FSMContext):
    lang = await get_user_language(state)
    code = callback_query.data.split("_")[1]
    await state.update_data(user_budget=code)
    logging.info(f"Данные после выбора бюджета: {await state.get_data()}")

    budget_name_key = f"budget_option_{code}"
    budget_full_name = get_text(budget_name_key, lang)
    budget_display_name_cleaned = budget_full_name.split(" ", 1)[
        -1] if " " in budget_full_name and not budget_full_name.startswith("<L10N_ERROR") else budget_full_name

    await callback_query.message.edit_text(
        get_text("budget_selected_text", lang, selected_budget=budget_display_name_cleaned) + "\n\n" +
        get_text("step4_dates_prompt", lang)
    )
    await callback_query.answer(
        text=get_text("budget_selected_text", lang, selected_budget=budget_display_name_cleaned), show_alert=False)
    await state.set_state(TripPlanning.waiting_for_trip_dates)
    logging.info(
        f"Пользователь {callback_query.from_user.id} ({lang}) переведен в состояние: {await state.get_state()}")


@trip_planning_router.message(TripPlanning.waiting_for_trip_dates, F.text)
async def process_trip_dates(message: Message, state: FSMContext):
    lang = await get_user_language(state)
    await state.update_data(user_trip_dates_text=message.text.strip())
    logging.info(f"Данные после ввода дат: {await state.get_data()}")
    await message.answer(
        get_text("dates_received_text", lang, dates_text=message.text) + "\n\n" +
        get_text("step5_transport_prompt", lang)
    )
    await state.set_state(TripPlanning.waiting_for_transport_prefs)
    logging.info(f"Пользователь {message.from_user.id} ({lang}) переведен в состояние: {await state.get_state()}")


@trip_planning_router.message(TripPlanning.waiting_for_transport_prefs, F.text)
async def process_transport_prefs(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(user_transport_prefs_text=message.text.strip())
    final_user_data_for_ai = await state.get_data()  # Эти данные пойдут в AI
    lang = final_user_data_for_ai.get("user_language", "ru")
    logging.info(
        f"Все собранные данные от пользователя {message.from_user.id} ({lang}) для AI: {final_user_data_for_ai}")

    await message.answer(
        get_text("transport_received_text", lang, transport_text=message.text) + "\n\n" +
        get_text("all_data_collected_prompt", lang)
    )

    # НЕ ОЧИЩАЕМ state полностью, а только выходим из FSM TripPlanning,
    # чтобы user_language и история лайков/дизлайков сохранились в state для обработчиков feedback.
    await state.set_state(None)
    logging.info(
        f"Пользователь {message.from_user.id} ({lang}) завершил FSM TripPlanning. Текущие данные в state: {await state.get_data()}")

    recommendations_json, accompanying_text = await get_travel_recommendations(
        final_user_data_for_ai)  # Передаем данные, которые были до очистки FSM

    if recommendations_json and accompanying_text:
        await message.answer(accompanying_text)

        if "recommendations" in recommendations_json and isinstance(recommendations_json["recommendations"], list):
            for rec_idx, rec in enumerate(recommendations_json["recommendations"]):
                if not isinstance(rec, dict):
                    logging.warning(f"Элемент #{rec_idx} в recommendations не словарь: {rec}")
                    continue

                formatted_text = await _format_recommendation_text(rec, lang)

                buttons_row1 = []
                buttons_row2 = []

                button_book_text = get_text("button_book_tickets", lang)
                button_map_text = get_text("button_on_map", lang)
                button_like_text = get_text("button_like", lang)
                button_dislike_text = get_text("button_dislike", lang)

                # Генерируем ID для обратной связи. Если AI не дал ID, создаем временный.
                # Важно, чтобы этот ID был стабильным для одной и той же рекомендации в рамках одного ответа AI.
                recommendation_id_for_feedback = rec.get("id")
                if not recommendation_id_for_feedback or not isinstance(recommendation_id_for_feedback,
                                                                        str) or not recommendation_id_for_feedback.strip():
                    recommendation_id_for_feedback = f"temp_rec_{message.chat.id}_{message.message_id}_{rec_idx}"
                    logging.warning(
                        f"AI не предоставил ID для рекомендации, используется временный: {recommendation_id_for_feedback}")

                booking_url = rec.get('booking_link')
                if booking_url and isinstance(booking_url,
                                              str) and booking_url.lower() != "null" and booking_url.strip():
                    buttons_row1.append(InlineKeyboardButton(text=button_book_text, url=booking_url))

                coords = rec.get('coordinates')
                if coords and isinstance(coords, list) and len(coords) == 2:
                    try:
                        lat, lon = float(coords[0]), float(coords[1])  # Убедимся, что это числа
                        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        buttons_row1.append(InlineKeyboardButton(text=button_map_text, url=maps_url))
                    except (ValueError, TypeError):
                        logging.warning(
                            f"Некорректные координаты для rec_id {recommendation_id_for_feedback}: {coords}")

                buttons_row2.append(InlineKeyboardButton(text=f"👍 {button_like_text}",
                                                         callback_data=f"feedback_like_{recommendation_id_for_feedback}"))
                buttons_row2.append(InlineKeyboardButton(text=f"👎 {button_dislike_text}",
                                                         callback_data=f"feedback_dislike_{recommendation_id_for_feedback}"))

                all_buttons_rows = []
                if buttons_row1: all_buttons_rows.append(buttons_row1)
                all_buttons_rows.append(buttons_row2)  # Лайк/дизлайк всегда добавляем

                reply_markup = InlineKeyboardMarkup(inline_keyboard=all_buttons_rows) if all_buttons_rows else None

                images = rec.get("images", [])
                photo_sent = False
                if images and isinstance(images, list) and images and \
                        isinstance(images[0], str) and images[0].lower() != "null" and images[0].strip():
                    try:
                        await bot.send_photo(
                            chat_id=message.chat.id, photo=images[0], caption=formatted_text,
                            reply_markup=reply_markup, parse_mode="HTML"
                        )
                        photo_sent = True
                    except Exception as e:
                        logging.warning(
                            f"Ошибка отправки фото {images[0]} для rec_id {recommendation_id_for_feedback}: {e}. Отправка текста.")

                if not photo_sent:
                    await message.answer(formatted_text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await message.answer(get_text("no_recommendations_in_response_text", lang))
    else:
        error_key = "ai_response_error_text"
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

    logging.info(
        f"Пользователь {message.from_user.id} ({lang}) получил ответ от AI. FSM TripPlanning состояние обработано (сохранен язык и история).")


# ==============================================================================
# ОБРАБОТЧИКИ ДЛЯ КНОПОК ЛАЙК/ДИЗЛАЙК
# ==============================================================================
async def _update_feedback_buttons(callback_query: CallbackQuery, recommendation_id: str, feedback_message_key: str,
                                   lang: str):
    feedback_message = get_text(feedback_message_key, lang)
    new_buttons_list = []
    if callback_query.message and callback_query.message.reply_markup:
        for row in callback_query.message.reply_markup.inline_keyboard:
            new_row = []
            for button in row:
                if not button.callback_data or \
                        not (button.callback_data == f"feedback_like_{recommendation_id}" or \
                             button.callback_data == f"feedback_dislike_{recommendation_id}"):
                    new_row.append(button)
            if new_row: new_buttons_list.append(new_row)

    new_reply_markup = InlineKeyboardMarkup(inline_keyboard=new_buttons_list) if new_buttons_list else None

    if callback_query.message:
        try:
            if new_reply_markup:
                await callback_query.message.edit_reply_markup(reply_markup=new_reply_markup)
                await callback_query.answer(feedback_message, show_alert=False)
            else:
                # Если других кнопок не осталось, просто удаляем клавиатуру
                await callback_query.message.edit_reply_markup(reply_markup=None)
                # И добавляем текст фидбека к сообщению, если хотим
                # await callback_query.message.edit_text(callback_query.message.text + f"\n\n<i>{feedback_message}</i>", parse_mode="HTML")
                await callback_query.answer(feedback_message, show_alert=False)  # Показываем короткое уведомление
        except Exception as e:
            logging.error(f"Ошибка при обновлении кнопок/сообщения после фидбека ({recommendation_id}): {e}",
                          exc_info=True)
            await callback_query.answer(feedback_message, show_alert=True)
    else:
        await callback_query.answer(feedback_message, show_alert=True)


@trip_planning_router.callback_query(F.data.startswith("feedback_like_"))
async def process_feedback_like(callback_query: CallbackQuery, state: FSMContext):
    recommendation_id = callback_query.data[len("feedback_like_"):]
    lang = await get_user_language(state)
    current_data = await state.get_data()
    liked_ids = current_data.get("liked_recommendation_ids", [])
    disliked_ids = current_data.get("disliked_recommendation_ids", [])
    if recommendation_id not in liked_ids: liked_ids.append(recommendation_id)
    if recommendation_id in disliked_ids: disliked_ids.remove(recommendation_id)
    await state.update_data(liked_recommendation_ids=liked_ids, disliked_recommendation_ids=disliked_ids)
    logging.info(
        f"Пользователь {callback_query.from_user.id} ({lang}) ЛАЙКНУЛ ID: {recommendation_id}. State: {await state.get_data()}")
    await _update_feedback_buttons(callback_query, recommendation_id, "feedback_thanks_like", lang)


@trip_planning_router.callback_query(F.data.startswith("feedback_dislike_"))
async def process_feedback_dislike(callback_query: CallbackQuery, state: FSMContext):
    recommendation_id = callback_query.data[len("feedback_dislike_"):]
    lang = await get_user_language(state)
    current_data = await state.get_data()
    liked_ids = current_data.get("liked_recommendation_ids", [])
    disliked_ids = current_data.get("disliked_recommendation_ids", [])
    if recommendation_id not in disliked_ids: disliked_ids.append(recommendation_id)
    if recommendation_id in liked_ids: liked_ids.remove(recommendation_id)
    await state.update_data(liked_recommendation_ids=liked_ids, disliked_recommendation_ids=disliked_ids)
    logging.info(
        f"Пользователь {callback_query.from_user.id} ({lang}) ДИЗЛАЙКНУЛ ID: {recommendation_id}. State: {await state.get_data()}")
    await _update_feedback_buttons(callback_query, recommendation_id, "feedback_thanks_dislike", lang)