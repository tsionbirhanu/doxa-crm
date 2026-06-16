from __future__ import annotations

import json
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db, require_role
from app.models import User
from app.schemas.webhooks import (
    CalendarEventPayload,
    EmailInboundPayload,
    LeadFormPayload,
    WebhookAck,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
)
from app.services import webhooks as webhooks_service
from app.utils.webhooks import verify_hmac_signature
from app.workers import webhook_tasks

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

T = TypeVar("T", bound=BaseModel)


@router.post("/lead-form", response_model=WebhookAck)
async def receive_lead_form(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> WebhookAck:
    payload, webhook_log = await _prepare_inbound_webhook(
        request,
        db,
        event_type="lead_form",
        schema=LeadFormPayload,
        signature=x_webhook_signature or x_hub_signature_256,
    )
    webhook_tasks.process_lead_form.apply_async(args=[payload.model_dump(mode="json"), str(webhook_log.id)])
    return WebhookAck()


@router.post("/email-inbound", response_model=WebhookAck)
async def receive_email_inbound(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> WebhookAck:
    payload, webhook_log = await _prepare_inbound_webhook(
        request,
        db,
        event_type="email_inbound",
        schema=EmailInboundPayload,
        signature=x_webhook_signature or x_hub_signature_256,
    )
    webhook_tasks.process_email_inbound.apply_async(args=[payload.model_dump(mode="json", by_alias=True), str(webhook_log.id)])
    return WebhookAck()


@router.post("/calendar-event", response_model=WebhookAck)
async def receive_calendar_event(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> WebhookAck:
    payload, webhook_log = await _prepare_inbound_webhook(
        request,
        db,
        event_type="calendar_event",
        schema=CalendarEventPayload,
        signature=x_webhook_signature or x_hub_signature_256,
    )
    webhook_tasks.process_calendar_event.apply_async(args=[payload.model_dump(mode="json"), str(webhook_log.id)])
    return WebhookAck()


@router.get("/subscriptions", response_model=list[WebhookSubscriptionResponse])
async def list_subscriptions(
    current_user: Annotated[User, Depends(require_role("super_admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WebhookSubscriptionResponse]:
    return await webhooks_service.list_subscriptions(db)


@router.post("/subscriptions", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_in: WebhookSubscriptionCreate,
    current_user: Annotated[User, Depends(require_role("super_admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WebhookSubscriptionResponse:
    return await webhooks_service.create_subscription(db, subscription_in)


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: UUID,
    current_user: Annotated[User, Depends(require_role("super_admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await webhooks_service.delete_subscription(db, subscription_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _prepare_inbound_webhook(
    request: Request,
    db: AsyncSession,
    *,
    event_type: str,
    schema: type[T],
    signature: str | None,
) -> tuple[T, object]:
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        await webhooks_service.log_inbound_webhook(
            db,
            event_type=event_type,
            status="rejected",
            payload={"raw_size": len(body)},
            signature=signature,
            error="Unsupported content type",
        )
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Content-Type must be application/json")

    if not verify_hmac_signature(body, signature or "", get_settings().webhook_secret):
        await webhooks_service.log_inbound_webhook(
            db,
            event_type=event_type,
            status="rejected",
            payload={"raw_size": len(body)},
            signature=signature,
            error="Invalid HMAC signature",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    try:
        raw_payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        await webhooks_service.log_inbound_webhook(
            db,
            event_type=event_type,
            status="rejected",
            payload={"raw_size": len(body)},
            signature=signature,
            error="Invalid JSON payload",
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    try:
        payload = schema.model_validate(raw_payload)
    except ValidationError as exc:
        await webhooks_service.log_inbound_webhook(
            db,
            event_type=event_type,
            status="rejected",
            payload=_safe_payload(raw_payload),
            signature=signature,
            error="Invalid webhook payload",
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    webhook_log = await webhooks_service.log_inbound_webhook(
        db,
        event_type=event_type,
        status="accepted",
        payload=_safe_payload(payload.model_dump(mode="json", by_alias=True)),
        signature=signature,
    )
    return payload, webhook_log


def _safe_payload(payload: dict) -> dict:
    cleaned = dict(payload)
    for key in {"body", "html", "text"}:
        if key in cleaned and isinstance(cleaned[key], str) and len(cleaned[key]) > 1000:
            cleaned[key] = f"{cleaned[key][:1000]}..."
    return cleaned
