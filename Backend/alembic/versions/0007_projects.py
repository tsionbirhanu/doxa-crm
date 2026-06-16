"""add project portal and document storage fields

Revision ID: 0007_projects
Revises: 0006_campaigns
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_projects"
down_revision: Union[str, Sequence[str], None] = "0006_campaigns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "projects",
        "deal_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "projects",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "project_documents",
        sa.Column("filename", sa.String(length=255), server_default="", nullable=False),
    )
    op.add_column(
        "project_documents",
        sa.Column("file_size", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("project_documents", sa.Column("mime_type", sa.String(length=255), nullable=True))
    op.add_column(
        "project_documents",
        sa.Column("storage_key", sa.String(length=1000), server_default="", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("project_documents", "storage_key")
    op.drop_column("project_documents", "mime_type")
    op.drop_column("project_documents", "file_size")
    op.drop_column("project_documents", "filename")
    op.drop_column("projects", "is_active")
    op.alter_column(
        "projects",
        "deal_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
