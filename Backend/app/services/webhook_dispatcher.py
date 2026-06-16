from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WebhookSubscription


async def dispatch_event(db: AsyncSession, event_type: str, payload: dict[str, Any]) -> int:
    from app.workers.webhook_tasks import deliver_webhook_event

    result = await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True),
            WebhookSubscription.events.any(event_type),
        )
    )
    subscriptions = list(result.scalars().all())
    for subscription in subscriptions:
        deliver_webhook_event.apply_async(args=[str(subscription.id), event_type, payload])
    return len(subscriptions)
