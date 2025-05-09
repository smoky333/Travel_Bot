from aiogram import Router, F       # F - это удобный способ создавать фильтры
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove # ReplyKeyboardRemove - чтобы убирать клавиатуру
from aiogram.fsm.context import FSMContext           # FSMContext - это "память" бота для каждого пользователя

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

# Обработчик для получения ответа на вопрос о локации
# Он сработает, ТОЛЬКО если пользователь находится в состоянии waiting_for_location
@trip_planning_router.message(TripPlanning.waiting_for_location, F.text) # F.text - значит, ждем текстовое сообщение
async def process_location(message: Message, state: FSMContext):
    # Сохраняем введенную локацию в "память" FSM для этого пользователя
    # message.text - это текст, который написал пользователь
    await state.update_data(user_location_text=message.text)

    # Для отладки выведем сохраненные данные (пока только локация)
    user_data = await state.get_data()
    print(f"Данные от пользователя {message.from_user.id} после ввода локации: {user_data}")

    # Задаем следующий вопрос (пока что просто выводим сообщение, что этот шаг пропустим)
    # TODO: Задать вопрос про интересы и перейти в состояние waiting_for_interests
    await message.answer(
        f"Принято! Вы указали: {message.text}.\n\n"
        "<b>Шаг 2: Ваши интересы</b> (этот шаг мы пока пропустим в разработке, но скоро добавим!)\n\n"
        "Спасибо! На этом сбор данных пока закончен (временно)."
    )
    # TODO: Вместо этого нужно будет перейти к следующему вопросу и состоянию
    await state.clear() # Пока что очищаем состояние, так как это конец (временный)
    print(f"Пользователь {message.from_user.id} завершил (временно) ввод. Состояние очищено.")

# TODO: Добавить обработчик для геолокации (message: ContentType.LOCATION) в состоянии waiting_for_location