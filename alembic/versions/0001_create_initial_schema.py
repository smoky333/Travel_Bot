# alembic/versions/0001_create_initial_schema.py
"""create_initial_schema

Revision ID: 0001
Revises:
Create Date: 2025-05-13 XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    feedbacktype_enum = postgresql.ENUM('LIKE', 'DISLIKE', name='feedbacktype_enum', create_type=False)
    feedbacktype_enum.create(op.get_bind(), checkfirst=True)

    op.create_table('users',
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('telegram_id', name=op.f('pk_users'))
    )

    op.create_table('feedbacks',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('recommendation_id', sa.String(), nullable=False),
        sa.Column('feedback_type', feedbacktype_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_telegram_id'], ['users.telegram_id'], name=op.f('fk_feedbacks_user_telegram_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_feedbacks')),
        sa.UniqueConstraint('user_telegram_id', 'recommendation_id', name=op.f('uq_feedbacks_user_recommendation_feedback'))
    )
    op.create_index(op.f('ix_feedbacks_recommendation_id'), 'feedbacks', ['recommendation_id'], unique=False)
    op.create_index(op.f('ix_feedbacks_user_telegram_id'), 'feedbacks', ['user_telegram_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_feedbacks_user_telegram_id'), table_name='feedbacks')
    op.drop_index(op.f('ix_feedbacks_recommendation_id'), table_name='feedbacks')
    op.drop_table('feedbacks')
    op.drop_table('users')
    postgresql.ENUM(name='feedbacktype_enum').drop(op.get_bind(), checkfirst=False)