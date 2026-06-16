from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models import (
    Activity,
    ActivityType,
    Contact,
    Deal,
    Lead,
    User,
    UserRoleName,
    WebhookLog,
    WebhookSubscription,
)
from app.schemas.webhooks import CalendarEventPayload, EmailInboundPayload, LeadFormPayload
from app.services.lead_assignment import assign_lead
from app.services.lead_scoring import calculate_lead_score
from app.services.webhook_dispatcher import dispatch_event
from app.services.webhooks import get_webhook_log, update_webhook_log_status
from app.utils.webhooks import build_hmac_signature
from app.workers.celery_app import celery_app
from app.workers.task_logging import execute_with_retry

DEAL_REFERENCE_PATTERN = re.compile(r"\[DEAL-([0-9a-fA-F-]{36})\]")


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.webhook_tasks.process_lead_form",
)
def process_lead_form(self, payload: dict[str, Any], log_id: str) -> dict[str, Any]:
    return execute_with_retry(
        self,
        self.name,
        lambda: _process_lead_form(payload, UUID(str(log_id))),
        {"log_id": log_id},
    )


async def _process_lead_form(payload: dict[str, Any], log_id: UUID | None = None) -> dict[str, Any]:
    lead_in = LeadFormPayload(**payload)
    async with AsyncSessionLocal() as db:
        if log_id and await _already_processed(db, log_id):
            return {"status": "already_processed", "log_id": str(log_id)}

        lead = Lead(
            full_name=lead_in.full_name,
            email=lead_in.email,
            phone=lead_in.phone,
            company=lead_in.company,
            source=lead_in.source,
            assigned_to=await _assign_inbound_lead(db, lead_in),
            utm_source=lead_in.utm_source,
            utm_campaign=lead_in.utm_campaign,
            utm_medium=lead_in.utm_medium,
        )
        db.add(lead)
        await db.flush()
        lead.score = await calculate_lead_score(db, lead)
        await db.commit()
        await db.refresh(lead)
        await dispatch_event(
            db,
            "lead.created",
            {"lead_id": str(lead.id), "email": lead.email, "company": lead.company, "score": lead.score},
        )
        if log_id:
            await update_webhook_log_status(db, log_id, status="processed", response_body="lead created")
        return {"status": "ok", "lead_id": str(lead.id)}


async def _assign_inbound_lead(db, lead_in: LeadFormPayload) -> UUID:
    draft_lead = Lead(
        full_name=lead_in.full_name,
        email=lead_in.email,
        phone=lead_in.phone,
        company=lead_in.company,
        source=lead_in.source,
    )
    return await assign_lead(db, draft_lead, method="round_robin")


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.webhook_tasks.process_email_inbound",
)
def process_email_inbound(self, payload: dict[str, Any], log_id: str) -> dict[str, Any]:
    return execute_with_retry(
        self,
        self.name,
        lambda: _process_email_inbound(payload, UUID(str(log_id))),
        {"log_id": log_id},
    )


async def _process_email_inbound(payload: dict[str, Any], log_id: UUID | None = None) -> dict[str, Any]:
    email_in = EmailInboundPayload(**payload)
    async with AsyncSessionLocal() as db:
        if log_id and await _already_processed(db, log_id):
            return {"status": "already_processed", "log_id": str(log_id)}

        result = await db.execute(
            select(Contact).where(
                func.lower(Contact.email) == email_in.from_email.lower(),
                Contact.is_active.is_(True),
            )
        )
        contact = result.scalar_one_or_none()
        if contact is None:
            if log_id:
                await update_webhook_log_status(db, log_id, status="processed", response_body="no matching contact")
            return {"status": "no_contact"}

        deal_id = await _extract_deal_id(db, email_in.subject)
        body = email_in.body or email_in.text or email_in.html or ""
        activity = Activity(
            type=ActivityType.email,
            subject=email_in.subject,
            body=body,
            outcome=f"Inbound email from {email_in.from_email}",
            contact_id=contact.id,
            account_id=contact.account_id,
            deal_id=deal_id,
            owner_id=contact.owner_id,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(activity)
        await db.commit()
        await db.refresh(activity)
        if log_id:
            await update_webhook_log_status(db, log_id, status="processed", response_body="email activity created")
        return {"status": "ok", "activity_id": str(activity.id), "contact_id": str(contact.id)}


async def _extract_deal_id(db, subject: str) -> UUID | None:
    match = DEAL_REFERENCE_PATTERN.search(subject or "")
    if not match:
        return None
    try:
        deal_id = UUID(match.group(1))
    except ValueError:
        return None
    result = await db.execute(select(Deal.id).where(Deal.id == deal_id, Deal.is_active.is_(True)))
    return result.scalar_one_or_none()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.webhook_tasks.process_calendar_event",
)
def process_calendar_event(self, payload: dict[str, Any], log_id: str) -> dict[str, Any]:
    return execute_with_retry(
        self,
        self.name,
        lambda: _process_calendar_event(payload, UUID(str(log_id))),
        {"log_id": log_id},
    )


async def _process_calendar_event(payload: dict[str, Any], log_id: UUID | None = None) -> dict[str, Any]:
    event_in = CalendarEventPayload(**payload)
    async with AsyncSessionLocal() as db:
        if log_id and await _already_processed(db, log_id):
            return {"status": "already_processed", "log_id": str(log_id)}

        normalized_attendees = [email.lower() for email in event_in.attendees]
        if not normalized_attendees:
            if log_id:
                await update_webhook_log_status(db, log_id, status="processed", response_body="no attendees")
            return {"status": "no_contacts", "activity_count": 0}

        result = await db.execute(
            select(Contact).where(
                func.lower(Contact.email).in_(normalized_attendees),
                Contact.is_active.is_(True),
            )
        )
        contacts = list(result.scalars().all())
        for contact in contacts:
            db.add(
                Activity(
                    type=ActivityType.meeting,
                    subject=event_in.title,
                    body=f"Calendar event {event_in.event_id}",
                    outcome="Synced from Google Calendar",
                    contact_id=contact.id,
                    account_id=contact.account_id,
                    owner_id=contact.owner_id,
                    scheduled_at=event_in.start,
                    completed_at=event_in.end,
                )
            )
        await db.commit()
        if log_id:
            await update_webhook_log_status(db, log_id, status="processed", response_body="calendar event processed")
        return {"status": "ok", "activity_count": len(contacts)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.webhook_tasks.deliver_webhook_event",
)
def deliver_webhook_event(self, subscription_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return execute_with_retry(
        self,
        self.name,
        lambda: _deliver_webhook_event(UUID(str(subscription_id)), event_type, payload),
        {"subscription_id": subscription_id, "event_type": event_type},
    )


async def _deliver_webhook_event(subscription_id: UUID, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        subscription = await db.get(WebhookSubscription, subscription_id)
        if subscription is None or not subscription.is_active or event_type not in subscription.events:
            return {"status": "skipped"}

        body = {"event": event_type, "payload": payload}
        body_bytes = _json_bytes(body)
        signature = build_hmac_signature(body_bytes, subscription.secret)
        webhook_log = WebhookLog(
            direction="outbound",
            event_type=event_type,
            status="started",
            url=subscription.url,
            signature=signature,
            payload=body,
            subscription_id=subscription.id,
        )
        db.add(webhook_log)
        await db.commit()
        await db.refresh(webhook_log)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    subscription.url,
                    content=body_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                    },
                )
                response.raise_for_status()
        except Exception as exc:
            await update_webhook_log_status(db, webhook_log.id, status="error", error=str(exc))
            raise

        await update_webhook_log_status(
            db,
            webhook_log.id,
            status="success",
            status_code=response.status_code,
            response_body=response.text[:2000],
        )
        return {"status": "delivered", "subscription_id": str(subscription.id), "status_code": response.status_code}


async def _already_processed(db, log_id: UUID) -> bool:
    webhook_log = await get_webhook_log(db, log_id)
    return webhook_log is not None and webhook_log.status == "processed"


def _json_bytes(payload: dict[str, Any]) -> bytes:
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
