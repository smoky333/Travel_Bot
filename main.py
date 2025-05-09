
import asyncio  # Этот инструмент помогает делать несколько дел одновременно (как жонглёр)
import logging  # Этот инструмент будет записывать, что делает наш бот (как дневник)
import os       # Этот инструмент поможет нам работать с операционной системой, например, читать переменные

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode # Чтобы бот понимал красивое оформление текста (жирный, курсив)
from dotenv import load_dotenv      # Этот инструмент загрузит наш секретный токен из файла .env
from aiogram.client.default import DefaultBotProperties # Этот инструмент позволит боту получать свой ID
from handlers.user_commands import user_commands_router


# Настраиваем "дневник" (логирование), чтобы видеть сообщения от бота в консоли
logging.basicConfig(level=logging.INFO)

# Главная функция, где будет происходить вся магия
async def main():
    # Загружаем наши секреты (токен) из файла .env
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    # Проверяем, нашли ли мы токен. Если нет, бот не сможет работать.
    if not bot_token:
        logging.error("ОШИБКА: Не найден TELEGRAM_BOT_TOKEN в файле .env! Проверь, что он там есть и правильно написан.")
        return # Выходим из функции, если токена нет

    # Создаём "мозг" бота (Dispatcher) и самого "бота" (Bot)
    # "Мозг" будет решать, как отвечать на сообщения
    dp = Dispatcher()

    # Подключаем наш новый распределитель команд к главному мозгу бота
    dp.include_router(user_commands_router)


    # "Бот" будет отправлять и получать сообщения. ParseMode.HTML означает, что мы сможем делать текст жирным, курсивом и т.д.
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    logging.info("Бот запускается...")

    # Эта команда удаляет все "старые" сообщения, которые бот мог пропустить, пока был выключен
    # Это полезно во время разработки, чтобы не получать кучу старых команд при каждом запуске
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем бота, чтобы он начал слушать сообщения от пользователей
    # Он будет работать, пока мы его не остановим (Ctrl+C в терминале)
    await dp.start_polling(bot)

# Эта специальная строчка говорит Python: "Если этот файл запускают напрямую, то выполни функцию main()"
if __name__ == '__main__':
    asyncio.run(main()) # Запускаем нашу главную функцию