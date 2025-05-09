from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.trip_planning_states import TripPlanning  # Импортируем наши состояния
from utils.ai_integration import get_travel_recommendations


# ==============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ФОРМАТИРОВАНИЯ РЕКОМЕНДАЦИИ
# ==============================================================================
async def _format_recommendation_text(recommendation: dict) -> str:  # Оставим async для гибкости
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
            stars_text = '⭐' * int(details['stars']) if isinstance(details.get('stars'), (int, float)) and details[
                'stars'] > 0 else str(details['stars'])
            detail_str_parts.append(f"{stars_text} ({details['stars']} звезд)")
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
        text_parts.append(f"💰 <b>Цена:</b> {recommendation.get('price_estimate')}")
    if recommendation.get('rating'):
        text_parts.append(f"🌟 <b>Рейтинг:</b> {recommendation.get('rating')}/5")
    if recommendation.get('opening_hours'):
        text_parts.append(f"⏰ <b>Часы работы:</b> {recommendation.get('opening_hours')}")

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
    print(f"Пользователь {message.from_user.id} начал планирование. Переведен в состояние waiting_for_location.")


# Обработчик для получения ответа на вопрос о локации (текстовый ввод)
@trip_planning_router.message(TripPlanning.waiting_for_location, F.text)
async def process_location_text(message: Message, state: FSMContext):
    await state.update_data(user_location_text=message.text.strip())
    user_data = await state.get_data()
    print(f"Данные от пользователя {message.from_user.id} после ввода локации: {user_data}")

    await message.answer(
        f"Принято! Вы указали: {message.text}.\n\n"
        "<b>Шаг 2: Ваши интересы</b> 🎨🏞️🏛️🛍️\n"
        "Напишите, пожалуйста, через запятую, что вас больше всего интересует в поездке. Например: "
        "<i>архитектура, природа, гастрономия, шопинг, история, искусство, ночная жизнь, семейный отдых</i>."
    )
    await state.set_state(TripPlanning.waiting_for_interests)
    print(f"Пользователь {message.from_user.id} переведен в состояние waiting_for_interests.")


# TODO: Добавить обработчик для геолокации (message: ContentType.LOCATION) в состоянии waiting_for_location

# Обработчик для получения ответа на вопрос об интересах
@trip_planning_router.message(TripPlanning.waiting_for_interests, F.text)
async def process_interests(message: Message, state: FSMContext):
    await state.update_data(user_interests_text=message.text.strip())
    user_data = await state.get_data()
    print(f"Данные от пользователя {message.from_user.id} после ввода интересов: {user_data}")

    budget_buttons = [
        [InlineKeyboardButton(text="💰 Эконом (Low)", callback_data="budget_low")],
        [InlineKeyboardButton(text="💰💰 Средний (Mid)", callback_data="budget_mid")],
        [InlineKeyboardButton(text="💰💰💰 Премиум (Premium)", callback_data="budget_premium")]
    ]
    budget_keyboard = InlineKeyboardMarkup(inline_keyboard=budget_buttons)

    await message.answer(
        f"Отлично! Ваши интересы: {message.text}.\n\n"
        "<b>Шаг 3: Ваш бюджет</b> 💳\n"
        "Пожалуйста, выберите предполагаемый уровень расходов на поездку:",
        reply_markup=budget_keyboard
    )
    await state.set_state(TripPlanning.waiting_for_budget)
    print(f"Пользователь {message.from_user.id} переведен в состояние waiting_for_budget.")


# Обработчик для нажатия кнопки бюджета
@trip_planning_router.callback_query(TripPlanning.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget_callback(callback_query: CallbackQuery, state: FSMContext):
    selected_budget = callback_query.data.split("_")[1]
    await state.update_data(user_budget=selected_budget)
    user_data_budget = await state.get_data()
    print(f"Данные от пользователя {callback_query.from_user.id} после выбора бюджета: {user_data_budget}")

    await callback_query.message.edit_text(
        f"Бюджет выбран: {selected_budget.capitalize()}.\n\n"
        "<b>Шаг 4: Даты поездки</b> 📅\n"
        "Пожалуйста, напишите даты начала и окончания вашей поездки.\n"
        "Например: <i>2025-05-10 to 2025-05-12</i> или <i>с 10 по 12 мая 2025</i>.\n"
        "Если точных дат нет, можно указать примерную продолжительность, например, <i>неделя в июле</i> или <i>3 дня</i>."
    )
    await callback_query.answer(text=f"Бюджет: {selected_budget.capitalize()}", show_alert=False)
    await state.set_state(TripPlanning.waiting_for_trip_dates)
    print(f"Пользователь {callback_query.from_user.id} переведен в состояние waiting_for_trip_dates.")


# Обработчик для получения ответа на вопрос о датах поездки
@trip_planning_router.message(TripPlanning.waiting_for_trip_dates, F.text)
async def process_trip_dates(message: Message, state: FSMContext):
    await state.update_data(user_trip_dates_text=message.text.strip())
    user_data_dates = await state.get_data()
    print(f"Данные от пользователя {message.from_user.id} после ввода дат: {user_data_dates}")

    await message.answer(
        f"Даты приняты: {message.text}.\n\n"
        "<b>Шаг 5: Предпочтения по транспорту</b> 🚶🚗🚌🚲\n"
        "Напишите, пожалуйста, через запятую, какие виды транспорта вы предпочитаете использовать в поездке. "
        "Например: <i>пешком, автомобиль, общественный транспорт, велосипед, такси</i>."
    )
    await state.set_state(TripPlanning.waiting_for_transport_prefs)
    print(f"Пользователь {message.from_user.id} переведен в состояние waiting_for_transport_prefs.")


# Обработчик для получения ответа на вопрос о предпочтениях по транспорту
@trip_planning_router.message(TripPlanning.waiting_for_transport_prefs, F.text)
async def process_transport_prefs(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(user_transport_prefs_text=message.text.strip())
    final_user_data = await state.get_data()
    print(f"Все собранные данные от пользователя {message.from_user.id}: {final_user_data}")

    await message.answer(
        f"Предпочтения по транспорту приняты: {message.text}.\n\n"
        "🎉 <b>Отлично! Вы предоставили всю основную информацию!</b>\n"
        "Подбираю для вас лучшие варианты... Это может занять несколько секунд ✨"
    )
    await state.clear()

    recommendations_json, accompanying_text = await get_travel_recommendations(final_user_data)

    if recommendations_json and accompanying_text:
        await message.answer(accompanying_text)

        if "recommendations" in recommendations_json:
            for rec in recommendations_json["recommendations"]:
                formatted_text = await _format_recommendation_text(rec)  # Вызов нашей функции

                buttons = []
                if rec.get('booking_link'):
                    buttons.append(InlineKeyboardButton(text="🔗 Бронь/Билеты", url=rec.get('booking_link')))

                coords = rec.get('coordinates')
                if coords and isinstance(coords, list) and len(coords) == 2:
                    lat, lon = coords
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    buttons.append(InlineKeyboardButton(text="🗺️ На карте", url=maps_url))

                reply_markup = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

                images = rec.get("images", [])
                if images:
                    try:
                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=images[0],
                            caption=formatted_text,
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Ошибка отправки фото {images[0]}: {e}. Отправляю текстом.")
                        await message.answer(formatted_text, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await message.answer(formatted_text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await message.answer("В полученном ответе от AI нет раздела 'recommendations'.")
    else:
        error_text = accompanying_text or "Не удалось получить рекомендации от AI. Попробуйте позже."
        await message.answer(error_text)

    print(f"Пользователь {message.from_user.id} получил ответ от AI (заглушки). FSM состояние очищено.")