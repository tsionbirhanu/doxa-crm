from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WebhookLog, WebhookSubscription
from app.schemas.webhooks import WEBHOOK_EVENT_TYPES, WebhookSubscriptionCreate, WebhookSubscriptionResponse


async def log_inbound_webhook(
    db: AsyncSession,
    *,
    event_type: str,
    status: str,
    payload: dict,
    signature: str | None = None,
    error: str | None = None,
) -> WebhookLog:
    webhook_log = WebhookLog(
        direction="inbound",
        event_type=event_type,
        status=status,
        signature=signature,
        payload=payload,
        error=error,
    )
    db.add(webhook_log)
    await db.commit()
    await db.refresh(webhook_log)
    return webhook_log


async def update_webhook_log_status(
    db: AsyncSession,
    log_id: UUID,
    *,
    status: str,
    error: str | None = None,
    response_body: str | None = None,
    status_code: int | None = None,
) -> None:
    webhook_log = await db.get(WebhookLog, log_id)
    if webhook_log is None:
        return
    webhook_log.status = status
    webhook_log.error = error
    webhook_log.response_body = response_body
    webhook_log.status_code = status_code
    await db.commit()


async def get_webhook_log(db: AsyncSession, log_id: UUID) -> WebhookLog | None:
    return await db.get(WebhookLog, log_id)


async def list_subscriptions(db: AsyncSession) -> list[WebhookSubscriptionResponse]:
    result = await db.execute(select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc()))
    return [WebhookSubscriptionResponse.model_validate(subscription) for subscription in result.scalars().all()]


async def create_subscription(
    db: AsyncSession,
    subscription_in: WebhookSubscriptionCreate,
) -> WebhookSubscriptionResponse:
    invalid_events = sorted(set(subscription_in.events) - WEBHOOK_EVENT_TYPES)
    if invalid_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported webhook events: {', '.join(invalid_events)}",
        )

    subscription = WebhookSubscription(
        url=str(subscription_in.url),
        events=subscription_in.events,
        secret=subscription_in.secret,
        is_active=subscription_in.is_active,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return WebhookSubscriptionResponse.model_validate(subscription)


async def delete_subscription(db: AsyncSession, subscription_id: UUID) -> None:
    subscription = await db.get(WebhookSubscription, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")
    await db.delete(subscription)
    await db.commit()
