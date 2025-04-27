"""add_model_name_to_messages

Revision ID: c80a297164ec
Revises: 637f3b560cdd
Create Date: 2025-04-26 10:21:59.213948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c80a297164ec'
down_revision: Union[str, None] = '637f3b560cdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 既存のmessagesテーブルにmodel_nameカラムを追加
    op.add_column('messages', sa.Column('model_name', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # model_nameカラムを削除
    op.drop_column('messages', 'model_name')
