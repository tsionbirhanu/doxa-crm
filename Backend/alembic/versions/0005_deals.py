"""add sales pipeline deal lifecycle fields

Revision ID: 0005_deals
Revises: 0004_leads
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_deals"
down_revision: Union[str, Sequence[str], None] = "0004_leads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "deals",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_table(
        "deal_stage_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_stage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name=op.f("fk_deal_stage_history_changed_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name=op.f("fk_deal_stage_history_deal_id_deals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_stage_id"],
            ["pipeline_stages.id"],
            name=op.f("fk_deal_stage_history_from_stage_id_pipeline_stages"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["to_stage_id"],
            ["pipeline_stages.id"],
            name=op.f("fk_deal_stage_history_to_stage_id_pipeline_stages"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deal_stage_history")),
    )
    op.create_index(op.f("ix_deal_stage_history_changed_by"), "deal_stage_history", ["changed_by"])
    op.create_index(op.f("ix_deal_stage_history_deal_id"), "deal_stage_history", ["deal_id"])
    op.create_index(op.f("ix_deal_stage_history_from_stage_id"), "deal_stage_history", ["from_stage_id"])
    op.create_index(op.f("ix_deal_stage_history_to_stage_id"), "deal_stage_history", ["to_stage_id"])


def downgrade() -> None:
    op.drop_table("deal_stage_history")
    op.drop_column("deals", "is_active")
    op.drop_column("deals", "closed_at")
