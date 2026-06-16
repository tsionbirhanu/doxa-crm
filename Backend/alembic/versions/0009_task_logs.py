"""add celery task logs

Revision ID: 0009_task_logs
Revises: 0008_reports
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_task_logs"
down_revision: Union[str, Sequence[str], None] = "0008_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_report_snapshots_report_type_date",
        "report_snapshots",
        ["report_type", "date"],
    )
    op.create_table(
        "task_logs",
        sa.Column("task_id", sa.String(length=255), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_logs")),
    )
    op.create_index(op.f("ix_task_logs_status"), "task_logs", ["status"], unique=False)
    op.create_index(op.f("ix_task_logs_task_id"), "task_logs", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_logs_task_name"), "task_logs", ["task_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_task_logs_task_name"), table_name="task_logs")
    op.drop_index(op.f("ix_task_logs_task_id"), table_name="task_logs")
    op.drop_index(op.f("ix_task_logs_status"), table_name="task_logs")
    op.drop_table("task_logs")
    op.drop_constraint("uq_report_snapshots_report_type_date", "report_snapshots", type_="unique")
