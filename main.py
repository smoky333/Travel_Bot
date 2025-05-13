import asyncio
import logging
import os
from dotenv import load_dotenv

# 1. ЗАГРУЖАЕМ .ENV В САМОМ НАЧАЛЕ!
load_dotenv()

# 2. НАСТРАИВАЕМ ЛОГИРОВАНИЕ ТОЖЕ В НАЧАЛЕ!
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Теперь можно делать остальные импорты
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from handlers.user_commands import user_commands_router
from handlers.trip_planning_handlers import trip_planning_router

# +++ ИМПОРТЫ ДЛЯ РАБОТЫ С БД +++
# Из db_setup нам нужна только фабрика сессий AsyncSessionLocal
from database.db_setup import AsyncSessionLocal
from middlewares.db_middleware import DbSessionMiddleware # Убедись, что путь к мидлвари правильный


async def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_key_present_in_main = os.getenv("GEMINI_API_KEY")

    if not bot_token:
        logging.error("ОШИБКА: Не найден TELEGRAM_BOT_TOKEN в файле .env! Проверь.")
        return

    if not gemini_key_present_in_main:
        logging.warning(
            "ПРЕДУПРЕЖДЕНИЕ в main: GEMINI_API_KEY не определен после load_dotenv(). Проверь .env и порядок вызовов.")
    else:
        logging.info("INFO в main: GEMINI_API_KEY найден после load_dotenv().")

    # +++ ИНИЦИАЛИЗАЦИЯ БД НЕ ТРЕБУЕТСЯ ЗДЕСЬ, Alembic управляет схемой +++
    logging.info("Схема БД управляется Alembic. Пропуск явной инициализации таблиц в main.py.")


    # +++ ИНИЦИАЛИЗАЦИЯ ДИСПЕТЧЕРА И РЕГИСТРАЦИЯ MIDDLEWARE +++
    dp = Dispatcher()

    # AsyncSessionLocal импортируется из database.db_setup и является нашей фабрикой сессий
    session_pool = AsyncSessionLocal

    # Регистрируем DbSessionMiddleware глобально для всех апдейтов
    dp.update.middleware(DbSessionMiddleware(session_pool=session_pool))
    logging.info("DbSessionMiddleware зарегистрирована.")


    # +++ РЕГИСТРАЦИЯ РОУТЕРОВ +++
    dp.include_router(user_commands_router)
    dp.include_router(trip_planning_router)
    logging.info("Роутеры зарегистрированы.")

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    logging.info("Бот запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске или работе бота: {e}", exc_info=True)
    finally:
        logging.info("Бот остановлен.")
        # Если твой async_engine требует явного закрытия при остановке приложения:
        from database.db_setup import async_engine
        if async_engine:
            logging.info("Закрытие соединения с БД (engine.dispose)...")
            await async_engine.dispose()
            logging.info("Соединение с БД успешно закрыто.")


if __name__ == '__main__':
    asyncio.run(main())