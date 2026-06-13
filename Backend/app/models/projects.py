from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProjectHealth(str, enum.Enum):
    green = "green"
    yellow = "yellow"
    red = "red"


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    health: Mapped[ProjectHealth] = mapped_column(
        SQLEnum(ProjectHealth, name="project_health"),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    portal_token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    account = relationship("Account")
    deal = relationship("Deal")
    owner = relationship("User")
    milestones: Mapped[list[Milestone]] = relationship(
        "Milestone",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list[ProjectDocument]] = relationship(
        "ProjectDocument",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class Milestone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "milestones"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="milestones")


class ProjectDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_documents"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    project: Mapped[Project] = relationship("Project", back_populates="documents")
    uploader = relationship("User")
