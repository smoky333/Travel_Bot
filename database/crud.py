from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional, Tuple

from .models import User, Feedback, FeedbackType


# ========== User Operations ==========

async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    """Получает пользователя по его Telegram ID."""
    result = await db.execute(select(User).filter(User.telegram_id == telegram_id))
    return result.scalars().first()


async def create_or_update_user_language(db: AsyncSession, telegram_id: int, language_code: str) -> User:
    """
    Создает нового пользователя, если он не существует, или обновляет язык существующего.
    Возвращает объект пользователя.
    """
    user = await get_user_by_telegram_id(db, telegram_id)
    if user:
        if user.language_code != language_code:
            user.language_code = language_code
            # db.add(user) # Не нужно для обновления, SQLAlchemy отслеживает изменения
            await db.commit()
            await db.refresh(user)
    else:
        user = User(telegram_id=telegram_id, language_code=language_code)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def get_user_language(db: AsyncSession, telegram_id: int) -> Optional[str]:
    """Получает код языка пользователя по его Telegram ID."""
    user = await get_user_by_telegram_id(db, telegram_id)
    return user.language_code if user else None


# ========== Feedback Operations ==========

async def add_or_update_feedback(
    db: AsyncSession,
    user_telegram_id: int,
    recommendation_id: str,
    feedback_type: FeedbackType
) -> Feedback:
    """
    Добавляет новый отзыв или обновляет существующий для данной рекомендации от пользователя.
    """
    # Сначала проверяем, есть ли уже отзыв от этого пользователя на эту рекомендацию
    stmt = select(Feedback).filter_by(
        user_telegram_id=user_telegram_id,
        recommendation_id=recommendation_id
    )
    result = await db.execute(stmt)
    existing_feedback = result.scalars().first()

    if existing_feedback:
        # Если отзыв уже существует, обновляем его тип
        if existing_feedback.feedback_type != feedback_type:
            existing_feedback.feedback_type = feedback_type
            # db.add(existing_feedback) # Не нужно, SQLAlchemy отслеживает
            await db.commit()
            await db.refresh(existing_feedback)
        return existing_feedback
    else:
        # Если отзыва нет, создаем новый
        # Сначала убедимся, что пользователь существует или создадим его
        # (хотя обычно пользователь уже будет создан при выборе языка)
        user = await get_user_by_telegram_id(db, user_telegram_id)
        if not user:
            # Если вдруг пользователя нет, создаем его с языком по умолчанию (например, 'en')
            # или можно вызвать ошибку, если язык обязателен на этом этапе
            # Для простоты, создадим с 'en'. В реальном приложении это место нужно продумать.
            user = User(telegram_id=user_telegram_id, language_code='en') #TODO: Подумать над default lang
            db.add(user)
            # Не делаем commit/refresh здесь, т.к. будет ниже при добавлении фидбека

        new_feedback = Feedback(
            user_telegram_id=user_telegram_id,
            recommendation_id=recommendation_id,
            feedback_type=feedback_type
        )
        db.add(new_feedback)
        await db.commit()
        await db.refresh(new_feedback)
        return new_feedback


async def get_user_feedback_history(
    db: AsyncSession,
    user_telegram_id: int
) -> Tuple[List[str], List[str]]:
    """
    Получает историю лайков и дизлайков пользователя.
    Возвращает кортеж: (список ID понравившихся рекомендаций, список ID не понравившихся).
    """
    liked_stmt = select(Feedback.recommendation_id).filter_by(
        user_telegram_id=user_telegram_id,
        feedback_type=FeedbackType.LIKE
    )
    disliked_stmt = select(Feedback.recommendation_id).filter_by(
        user_telegram_id=user_telegram_id,
        feedback_type=FeedbackType.DISLIKE
    )

    liked_results = await db.execute(liked_stmt)
    disliked_results = await db.execute(disliked_stmt)

    liked_ids = [row[0] for row in liked_results.fetchall()]
    disliked_ids = [row[0] for row in disliked_results.fetchall()]

    return liked_ids, disliked_ids


async def remove_feedback(
    db: AsyncSession,
    user_telegram_id: int,
    recommendation_id: str
):
    """
    Удаляет отзыв пользователя на конкретную рекомендацию.
    (Может быть полезно, если пользователь хочет "отменить" лайк/дизлайк,
    и мы не хотим хранить это как отдельный тип фидбека).
    """
    stmt = delete(Feedback).where(
        Feedback.user_telegram_id == user_telegram_id,
        Feedback.recommendation_id == recommendation_id
    )
    await db.execute(stmt)
    await db.commit()