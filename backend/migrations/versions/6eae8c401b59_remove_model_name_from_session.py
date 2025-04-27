"""remove_model_name_from_session

Revision ID: d2f8a1b3e621
Revises: c80a297164ec
Create Date: 2025-04-26 13:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d2f8a1b3e621"
down_revision: Union[str, None] = "c80a297164ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 既存のNULLデータをデフォルト値で更新
    op.execute("UPDATE messages SET model_name = 'llama3' WHERE model_name IS NULL")

    # Messageテーブルのmodel_nameをNOT NULL制約に変更
    op.alter_column("messages", "model_name", nullable=False)

    # ChatSessionテーブルからmodel_nameカラムを削除
    op.drop_column("chat_sessions", "model_name")


def downgrade() -> None:
    """Downgrade schema."""
    # ChatSessionテーブルにmodel_nameカラムを追加し直す
    op.add_column("chat_sessions", sa.Column("model_name", sa.String(), nullable=True))

    # 既存のセッションにデフォルト値を設定（各セッションの最初のメッセージのモデルを使用）
    op.execute(
        """
    UPDATE chat_sessions cs
    SET model_name = (
        SELECT model_name
        FROM messages m
        WHERE m.session_id = cs.id
        ORDER BY m.created_at
        LIMIT 1
    )
    """
    )

    # デフォルト値がセットできなかった場合はデフォルト値を設定
    op.execute(
        "UPDATE chat_sessions SET model_name = 'llama3' WHERE model_name IS NULL"
    )

    # NOT NULL制約を追加
    op.alter_column("chat_sessions", "model_name", nullable=False)

    # Messageテーブルのmodel_nameをNULLABLE制約に戻す
    op.alter_column("messages", "model_name", nullable=True)
