"""add_gpt5_nano_to_aimodelid_enum

Revision ID: 8a1b2c3d4e5f
Revises: 69eb925ebbf5
Create Date: 2025-08-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8a1b2c3d4e5f"
down_revision: Union[str, None] = "69eb925ebbf5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rebuild aimodelid_enum with uppercase labels only and include GPT_5_NANO.

    This creates a new enum type with the desired labels, casts the dependent
    columns to the new type with explicit mapping (including mapping any
    'gpt-5-nano' data to 'GPT_5_NANO'), drops the old type, and renames the
    new type back to aimodelid_enum. This yields a clean, deterministic state
    without leaving conditional branches for legacy labels.
    """
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'aimodelid_enum') THEN
                RAISE EXCEPTION 'aimodelid_enum does not exist';
            END IF;

            -- Create a new enum type with the canonical (uppercase) labels
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'aimodelid_enum_new') THEN
                CREATE TYPE aimodelid_enum_new AS ENUM ('QWEN3_8B','GPT_4_1_NANO','GPT_5_NANO');
            END IF;

            -- Alter token_limits.model_id
            ALTER TABLE token_limits
            ALTER COLUMN model_id TYPE aimodelid_enum_new
            USING (
                CASE
                    WHEN model_id::text = 'gpt-5-nano' THEN 'GPT_5_NANO'
                    ELSE model_id::text
                END
            )::aimodelid_enum_new;

            -- Alter messages.model_id
            ALTER TABLE messages
            ALTER COLUMN model_id TYPE aimodelid_enum_new
            USING (
                CASE
                    WHEN model_id::text = 'gpt-5-nano' THEN 'GPT_5_NANO'
                    ELSE model_id::text
                END
            )::aimodelid_enum_new;

            -- Drop old type and rename new one
            DROP TYPE aimodelid_enum;
            ALTER TYPE aimodelid_enum_new RENAME TO aimodelid_enum;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Irreversible: removing enum labels is non-trivial in PostgreSQL."""
    # No-op on downgrade.
    pass
