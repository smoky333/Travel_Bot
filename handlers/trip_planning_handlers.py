from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.trip_planning_states import TripPlanning # Импортируем наши состояния

# Создаем новый роутер специально для логики планирования поездки
trip_planning_router = Router(name="trip_planning_router")

# Обработчик команды /plan_trip
@trip_planning_router.message(Command("plan_trip"))
async def cmd_plan_trip(message: Message, state: FSMContext):
    await message.answer(
        "Отлично! Начнем планирование вашей идеальной поездки. ✨\n\n"
        "<b>Шаг 1: Пункт назначения</b>\n"
        "📍 Пожалуйста, напишите город или страну, куда вы хотите поехать. "
        "Или, если вы уже там, можете отправить свою текущую геолокацию (нажав на скрепку 📎 и выбрав 'Геопозиция').",
        reply_markup=ReplyKeyboardRemove() # Убираем любые предыдущие обычные клавиатуры (если были)
    )
    # Переводим пользователя в состояние "ожидания локации"
    await state.set_state(TripPlanning.waiting_for_location)
    print(f"Пользователь {message.from_user.id} начал планирование. Переведен в состояние waiting_for_location.")

# Обработчик для получения ответа на вопрос о локации (текстовый ввод)
@trip_planning_router.message(TripPlanning.waiting_for_location, F.text)
async def process_location_text(message: Message, state: FSMContext):
    # Сохраняем введенную локацию в "память" FSM для этого пользователя
    await state.update_data(user_location_text=message.text.strip())

    user_data = await state.get_data()
    print(f"Данные от пользователя {message.from_user.id} после ввода локации: {user_data}")

    # Задаем следующий вопрос про интересы
    await message.answer(
        f"Принято! Вы указали: {message.text}.\n\n"
        "<b>Шаг 2: Ваши интересы</b> 🎨🏞️🏛️🛍️\n"
        "Напишите, пожалуйста, через запятую, что вас больше всего интересует в поездке. Например: "
        "<i>архитектура, природа, гастрономия, шопинг, история, искусство, ночная жизнь, семейный отдых</i>."
    )
    # Переводим пользователя в состояние "ожидания интересов"
    await state.set_state(TripPlanning.waiting_for_interests)
    print(f"Пользователь {message.from_user.id} переведен в состояние waiting_for_interests.")

# TODO: Добавить обработчик для геолокации (message: ContentType.LOCATION) в состоянии waiting_for_location


# Обработчик для получения ответа на вопрос об интересах
@trip_planning_router.message(TripPlanning.waiting_for_interests, F.text)
async def process_interests(message: Message, state: FSMContext):
    # Сохраняем интересы.
    await state.update_data(user_interests_text=message.text.strip())

    user_data = await state.get_data()
    print(f"Данные от пользователя {message.from_user.id} после ввода интересов: {user_data}")

    # Создаем клавиатуру с вариантами бюджета
    budget_buttons = [
        [InlineKeyboardButton(text="💰 Эконом (Low)", callback_data="budget_low")],
        [InlineKeyboardButton(text="💰💰 Средний (Mid)", callback_data="budget_mid")],
        [InlineKeyboardButton(text="💰💰💰 Премиум (Premium)", callback_data="budget_premium")]
    ]
    budget_keyboard = InlineKeyboardMarkup(inline_keyboard=budget_buttons)

    # Задаем следующий вопрос про бюджет
    await message.answer(
        f"Отлично! Ваши интересы: {message.text}.\n\n"
        "<b>Шаг 3: Ваш бюджет</b> 💳\n"
        "Пожалуйста, выберите предполагаемый уровень расходов на поездку:",
        reply_markup=budget_keyboard # Прикрепляем нашу клавиатуру с кнопками
    )
    # Переводим пользователя в состояние "ожидания бюджета"
    await state.set_state(TripPlanning.waiting_for_budget)
    print(f"Пользователь {message.from_user.id} переведен в состояние waiting_for_budget.")


# Обработчик для нажатия кнопки бюджета
@trip_planning_router.callback_query(TripPlanning.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget_callback(callback_query: CallbackQuery, state: FSMContext):
    selected_budget = callback_query.data.split("_")[1]

    await state.update_data(user_budget=selected_budget)

    user_data = await state.get_data()
    print(f"Данные от пользователя {callback_query.from_user.id} после выбора бюджета: {user_data}")

    # Убираем кнопки после нажатия (редактируем исходное сообщение)
    await callback_query.message.edit_text(
        f"Бюджет выбран: {selected_budget.capitalize()}.\n\n"
        "<b>Следующий шаг: Даты поездки</b> (это мы добавим очень скоро!)\n\n"
        "Спасибо! На этом сбор данных пока завершен (временно)."
    )
    await callback_query.answer(text=f"Вы выбрали бюджет: {selected_budget.capitalize()}", show_alert=False)

    # TODO: Задать вопрос про даты и перейти в следующее состояние
    await state.clear() # Пока что очищаем состояние
    print(f"Пользователь {callback_query.from_user.id} завершил (временно) ввод. Состояние очищено.")