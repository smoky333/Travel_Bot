# database/models.py
from sqlalchemy import Column, String, BigInteger, Enum as SAEnum, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    telegram_id = Column(BigInteger, primary_key=True) # Индекс для PK создается автоматически
    language_code = Column(String(10), nullable=True)
    # Для created_at и updated_at с server_default, nullable=False обычно предпочтительнее
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, language_code='{self.language_code}')>"

class FeedbackType(enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"

class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(BigInteger, primary_key=True, autoincrement=True) # Индекс для PK создается автоматически
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_id = Column(String, nullable=False, index=True)
    feedback_type = Column(SAEnum(FeedbackType, name="feedbacktype_enum", create_constraint=True), nullable=False)
    # Переименовал timestamp в created_at для единообразия
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user = relationship("User", back_populates="feedbacks")
    __table_args__ = (
        UniqueConstraint('user_telegram_id', 'recommendation_id', name='uq_user_recommendation_feedback'),
    )
    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_telegram_id}, rec_id='{self.recommendation_id}', type='{self.feedback_type.value}')>"