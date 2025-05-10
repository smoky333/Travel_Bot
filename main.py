import asyncio
import logging
import os
from dotenv import load_dotenv

# 1. ЗАГРУЖАЕМ .ENV В САМОМ НАЧАЛЕ!
load_dotenv()

# 2. НАСТРАИВАЕМ ЛОГИРОВАНИЕ ТОЖЕ В НАЧАЛЕ!
# Уровень логирования INFO, формат сообщения: ВРЕМЯ УРОВЕНЬ СООБЩЕНИЕ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Теперь можно делать остальные импорты
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from handlers.user_commands import user_commands_router
# trip_planning_router импортирует ai_integration, который читает GEMINI_API_KEY
from handlers.trip_planning_handlers import trip_planning_router


# Главная функция, где будет происходить вся магия
async def main():
    # load_dotenv() уже вызван глобально выше

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_key_present_in_main = os.getenv("GEMINI_API_KEY")  # Для проверки

    if not bot_token:
        logging.error("ОШИБКА: Не найден TELEGRAM_BOT_TOKEN в файле .env! Проверь.")
        return

    if not gemini_key_present_in_main:
        # Это сообщение не должно появиться, если GEMINI_API_KEY есть в .env
        # и load_dotenv() сработал правильно
        logging.warning(
            "ПРЕДУПРЕЖДЕНИЕ в main: GEMINI_API_KEY не определен после load_dotenv(). Проверь .env и порядок вызовов.")
    else:
        logging.info("INFO в main: GEMINI_API_KEY найден после load_dotenv().")

    dp = Dispatcher()

    dp.include_router(user_commands_router)
    dp.include_router(trip_planning_router)

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    logging.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    # logging.basicConfig() уже вызван глобально выше
    asyncio.run(main())