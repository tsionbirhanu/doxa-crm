"""add marketing campaign metrics and attribution

Revision ID: 0006_campaigns
Revises: 0005_deals
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_campaigns"
down_revision: Union[str, Sequence[str], None] = "0005_deals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

campaign_metric_event_type = postgresql.ENUM(
    "sent",
    "opened",
    "clicked",
    "replied",
    "converted",
    name="campaign_metric_event_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    campaign_metric_event_type.create(bind, checkfirst=True)

    op.add_column("campaign_sequence_steps", sa.Column("variant", sa.String(length=1), nullable=True))
    op.add_column("leads", sa.Column("utm_source", sa.String(length=120), nullable=True))
    op.add_column("leads", sa.Column("utm_campaign", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("utm_medium", sa.String(length=120), nullable=True))

    op.create_table(
        "campaign_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", campaign_metric_event_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_campaign_metrics_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name=op.f("fk_campaign_metrics_contact_id_contacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["campaign_sequence_steps.id"],
            name=op.f("fk_campaign_metrics_step_id_campaign_sequence_steps"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_metrics")),
    )
    op.create_index(op.f("ix_campaign_metrics_campaign_id"), "campaign_metrics", ["campaign_id"])
    op.create_index(op.f("ix_campaign_metrics_contact_id"), "campaign_metrics", ["contact_id"])
    op.create_index(op.f("ix_campaign_metrics_step_id"), "campaign_metrics", ["step_id"])


def downgrade() -> None:
    op.drop_table("campaign_metrics")
    op.drop_column("leads", "utm_medium")
    op.drop_column("leads", "utm_campaign")
    op.drop_column("leads", "utm_source")
    op.drop_column("campaign_sequence_steps", "variant")

    bind = op.get_bind()
    campaign_metric_event_type.drop(bind, checkfirst=True)
