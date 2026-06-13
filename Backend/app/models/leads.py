from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LeadSource(str, enum.Enum):
    website = "website"
    referral = "referral"
    social = "social"
    cold_outreach = "cold_outreach"
    event = "event"
    campaign = "campaign"


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    disqualified = "disqualified"
    converted = "converted"


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leads"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[LeadSource] = mapped_column(
        SQLEnum(LeadSource, name="lead_source"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    status: Mapped[LeadStatus] = mapped_column(
        SQLEnum(LeadStatus, name="lead_status"),
        nullable=False,
        default=LeadStatus.new,
        server_default=LeadStatus.new.value,
    )
    assigned_to: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    assignee = relationship("User")
    campaign = relationship("Campaign")
