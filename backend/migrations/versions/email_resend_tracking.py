"""Add email resend tracking table

Revision ID: email_resend_tracking
Revises: dcb93fbca40b
Create Date: 2025-05-06 07:42:06.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'email_resend_tracking'
down_revision = 'dcb93fbca40b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'email_resend_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('last_resend_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resend_count_hour', sa.Integer(), nullable=False, default=1),
        sa.Column('resend_count_day', sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_resend_tracking_email'), 'email_resend_tracking', ['email'], unique=False)
    op.create_index(op.f('ix_email_resend_tracking_id'), 'email_resend_tracking', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_email_resend_tracking_id'), table_name='email_resend_tracking')
    op.drop_index(op.f('ix_email_resend_tracking_email'), table_name='email_resend_tracking')
    op.drop_table('email_resend_tracking')
