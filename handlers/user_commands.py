from aiogram import Router                  # Роутер - это как распределитель задач для разных команд
from aiogram.filters import CommandStart    # Фильтр, который ловит именно команду /start
from aiogram.types import Message           # Message - это объект сообщения, которое прислал пользователь

# Создаем новый "распределитель" только для команд пользователя
# Мы дадим ему имя, чтобы потом в main.py было понятно, что это за распределитель
user_commands_router = Router(name="user_commands_router")

# Это "декоратор". Он говорит: "Эй, распределитель! Если придет команда /start, выполни функцию ниже"
@user_commands_router.message(CommandStart())
async def handle_start_command(message: Message):
    # message.from_user содержит информацию о пользователе, который написал боту
    user_name = message.from_user.full_name  # Получаем полное имя пользователя
    user_id = message.from_user.id            # Получаем его уникальный ID в Telegram

    # Формируем приветственное сообщение. Используем f-строку для вставки имени.
    # <b>...</b> сделает текст жирным (мы же указали ParseMode.HTML при создании бота)
    text = f"Привет, <b>{user_name}</b>! 👋\nЯ твой персональный Travel Bot.\nГотов помочь спланировать твое лучшее путешествие!\n\nЧтобы начать, используй команду /plan_trip (но она пока не работает 😉)."

    # Отвечаем пользователю этим сообщением
    await message.answer(text)

    # Можно также отправить что-то в консоль для отладки (необязательно)
    print(f"Пользователь {user_name} (ID: {user_id}) нажал /start")