"""add webhook subscriptions and logs

Revision ID: 0010_webhooks
Revises: 0009_task_logs
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_webhooks"
down_revision: Union[str, Sequence[str], None] = "0009_task_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_subscriptions",
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.String(length=120)), server_default=sa.text("'{}'::varchar[]"), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_subscriptions")),
    )
    op.create_table(
        "webhook_logs",
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("signature", sa.String(length=255), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["webhook_subscriptions.id"], name=op.f("fk_webhook_logs_subscription_id_webhook_subscriptions"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_logs")),
    )
    op.create_index(op.f("ix_webhook_logs_direction"), "webhook_logs", ["direction"], unique=False)
    op.create_index(op.f("ix_webhook_logs_event_type"), "webhook_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_webhook_logs_status"), "webhook_logs", ["status"], unique=False)
    op.create_index(op.f("ix_webhook_logs_subscription_id"), "webhook_logs", ["subscription_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_webhook_logs_subscription_id"), table_name="webhook_logs")
    op.drop_index(op.f("ix_webhook_logs_status"), table_name="webhook_logs")
    op.drop_index(op.f("ix_webhook_logs_event_type"), table_name="webhook_logs")
    op.drop_index(op.f("ix_webhook_logs_direction"), table_name="webhook_logs")
    op.drop_table("webhook_logs")
    op.drop_table("webhook_subscriptions")
