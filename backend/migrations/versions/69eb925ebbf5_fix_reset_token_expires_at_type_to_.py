"""fix_reset_token_expires_at_type_to_datetime

Revision ID: 69eb925ebbf5
Revises: cc12785e15bb
Create Date: 2025-06-24 13:05:45.545424

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "69eb925ebbf5"
down_revision: Union[str, None] = "cc12785e15bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # reset_token_expires_atをVARCHARからTIMESTAMP WITH TIME ZONEに変換
    # PostgreSQLでは明示的なUSING句が必要（既存データはISO形式の文字列）
    op.drop_index("ix_users_reset_token_expires_at", table_name="users")
    op.execute(
        """
        ALTER TABLE users 
        ALTER COLUMN reset_token_expires_at 
        TYPE TIMESTAMP WITH TIME ZONE 
        USING CASE 
            WHEN reset_token_expires_at IS NULL OR reset_token_expires_at = '' THEN NULL
            ELSE reset_token_expires_at::timestamp with time zone
        END
    """
    )
    op.create_index(
        "ix_users_reset_token_expires_at",
        "users",
        ["reset_token_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_users_reset_token_expires_at", table_name="users")
    
    # TIMESTAMP WITH TIME ZONEからVARCHARに戻す（downgrade）
    op.execute(
        """
        ALTER TABLE users 
        ALTER COLUMN reset_token_expires_at 
        TYPE VARCHAR 
        USING reset_token_expires_at::text
    """
    )
    
    op.create_index(
        "ix_users_reset_token_expires_at",
        "users",
        ["reset_token_expires_at"],
        unique=False,
    )
