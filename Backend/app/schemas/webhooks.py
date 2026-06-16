from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models import LeadSource

WEBHOOK_EVENT_TYPES = {
    "lead.created",
    "lead.converted",
    "deal.won",
    "deal.lost",
    "deal.stage_changed",
    "project.health_changed",
}


class LeadFormPayload(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    phone: str = Field(default="", max_length=50)
    company: str = Field(default="", max_length=255)
    source: LeadSource = LeadSource.website
    utm_source: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=120)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Ada Lovelace",
                "email": "ada@acme.com",
                "phone": "+15555550123",
                "company": "Acme",
                "source": "website",
            }
        }
    )


class EmailInboundPayload(BaseModel):
    from_email: str = Field(min_length=3, max_length=320, alias="from")
    to_email: str | None = Field(default=None, alias="to")
    subject: str = Field(default="(no subject)", max_length=255)
    body: str | None = None
    html: str | None = None
    text: str | None = None


class CalendarEventPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    start: datetime
    end: datetime
    attendees: list[str] = Field(default_factory=list)
    type: Literal["meeting"] = "meeting"


class WebhookAck(BaseModel):
    status: Literal["ok"] = "ok"


class WebhookSubscriptionCreate(BaseModel):
    url: HttpUrl
    events: list[str] = Field(min_length=1)
    secret: str = Field(min_length=16, max_length=255)
    is_active: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/crm-webhook",
                "events": ["lead.created", "deal.won"],
                "secret": "replace-with-shared-secret",
                "is_active": True,
            }
        }
    )


class WebhookSubscriptionResponse(BaseModel):
    id: UUID
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
