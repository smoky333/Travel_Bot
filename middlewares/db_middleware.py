# middlewares/db_middleware.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession # async_sessionmaker это тип для session_pool

# Если AsyncSessionLocal из db_setup.py это уже sessionmaker,
# то тип session_pool может быть просто callable, возвращающий AsyncSession,
# или можно использовать from sqlalchemy.orm import sessionmaker as OrmSessionMaker
# и типизировать session_pool: OrmSessionMaker[AsyncSession]
# Но async_sessionmaker[AsyncSession] (из sqlalchemy.ext.asyncio) тоже должен подойти,
# т.к. sessionmaker() из sqlalchemy.orm возвращает объект, который соответствует этому протоколу.


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: Callable[[], AsyncSession]): # Уточнил тип для session_pool
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session: # session_pool здесь вызывается как фабрика
            data["session"] = session
            return await handler(event, data)