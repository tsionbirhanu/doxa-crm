"""add reporting quota and snapshot fields

Revision ID: 0008_reports
Revises: 0007_projects
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_reports"
down_revision: Union[str, Sequence[str], None] = "0007_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deals",
        sa.Column("type", sa.String(length=80), server_default="new_business", nullable=False),
    )
    op.create_index(op.f("ix_deals_type"), "deals", ["type"], unique=False)

    op.add_column(
        "report_snapshots",
        sa.Column("date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
    )
    op.alter_column(
        "report_snapshots",
        "generated_by",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.create_table(
        "sales_quotas",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("quota_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_sales_quotas_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales_quotas")),
        sa.UniqueConstraint("user_id", "period_start", "period_end", name="uq_sales_quotas_user_period"),
    )
    op.create_index(op.f("ix_sales_quotas_user_id"), "sales_quotas", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_quotas_user_id"), table_name="sales_quotas")
    op.drop_table("sales_quotas")

    op.alter_column(
        "report_snapshots",
        "generated_by",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("report_snapshots", "date")

    op.drop_index(op.f("ix_deals_type"), table_name="deals")
    op.drop_column("deals", "type")
