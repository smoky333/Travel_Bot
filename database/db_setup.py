# database/db_setup.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

from .models import Base # Импортируем Base из нашего models.py

# Загружаем переменные окружения (если еще не загружены глобально в main.py)
# load_dotenv() # Лучше, чтобы это было сделано в main.py

DATABASE_USER = os.getenv("POSTGRES_USER", "your_user")
DATABASE_PASSWORD = os.getenv("POSTGRES_PASSWORD", "your_password")
DATABASE_HOST = os.getenv("POSTGRES_HOST", "localhost")
DATABASE_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_NAME = os.getenv("POSTGRES_DB", "travel_bot_db")

DATABASE_URL = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

async_engine = create_async_engine(DATABASE_URL, echo=False) # echo=True для отладки SQL запросов
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

async def create_db_and_tables():
    async with async_engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Для удаления таблиц при разработке (ОСТОРОЖНО!)
        await conn.run_sync(Base.metadata.create_all)
    logging.info("База данных и таблицы успешно созданы/проверены.")

async def get_db_session() -> AsyncSession:
    """Зависимость для получения сессии БД."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Для Alembic (управление миграциями) нам также понадобится синхронный URL
# Это нужно, так как Alembic не всегда хорошо работает с asyncpg напрямую для некоторых операций.
SYNC_DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"