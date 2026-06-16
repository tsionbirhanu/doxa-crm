from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select

from app.database import AsyncSessionLocal
from app.models import Activity, Deal, DealStatus, TaskLog, User
from app.services.notifications import check_overdue_tasks as check_overdue_tasks_service
from app.utils.email import send_email
from app.workers.celery_app import celery_app
from app.workers.task_logging import execute_with_retry


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.notification_tasks.check_overdue_tasks",
)
def check_overdue_tasks(self) -> dict[str, Any]:
    return execute_with_retry(self, self.name, _check_overdue_tasks)


async def _check_overdue_tasks() -> dict[str, Any]:
    today = date.today().isoformat()
    async with AsyncSessionLocal() as db:
        overdue_tasks = await check_overdue_tasks_service(db)
        notified = 0

        for task in overdue_tasks:
            notification_key = f"overdue-task:{task.id}:{today}"
            if await _notification_already_logged(db, notification_key):
                continue

            owner = await db.get(User, task.owner_id)
            if owner is not None:
                sent = await _send_notification_email(
                    owner.email,
                    f"Overdue task: {task.title}",
                    f"<p>Your task <strong>{task.title}</strong> is overdue.</p>",
                )
                if not sent:
                    raise RuntimeError(f"Overdue task notification failed for task {task.id}")

            _add_notification_log(
                db,
                notification_key,
                "notification.overdue_task",
                {
                    "task_id": str(task.id),
                    "owner_id": str(task.owner_id),
                    "due_at": task.due_at.isoformat() if task.due_at else None,
                },
            )
            notified += 1

        await db.commit()
        return {"status": "ok", "overdue_count": len(overdue_tasks), "notified_count": notified}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.notification_tasks.send_deal_stale_alert",
)
def send_deal_stale_alert(self) -> dict[str, Any]:
    return execute_with_retry(self, self.name, _send_deal_stale_alert)


async def _send_deal_stale_alert() -> dict[str, Any]:
    today = date.today().isoformat()
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    latest_activity = (
        select(Activity.deal_id, func.max(Activity.created_at).label("last_activity_at"))
        .where(Activity.deal_id.is_not(None))
        .group_by(Activity.deal_id)
        .subquery()
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Deal, User, latest_activity.c.last_activity_at)
            .join(User, User.id == Deal.owner_id)
            .outerjoin(latest_activity, latest_activity.c.deal_id == Deal.id)
            .where(
                Deal.is_active.is_(True),
                Deal.status == DealStatus.open,
                or_(latest_activity.c.last_activity_at.is_(None), latest_activity.c.last_activity_at < cutoff),
            )
            .order_by(Deal.expected_close.asc())
        )
        rows = result.all()
        notified = 0

        for deal, owner, last_activity_at in rows:
            notification_key = f"deal-stale:{deal.id}:{today}"
            if await _notification_already_logged(db, notification_key):
                continue

            sent = await _send_notification_email(
                owner.email,
                f"Stale deal: {deal.title}",
                f"<p>The deal <strong>{deal.title}</strong> has had no activity in 14 days.</p>",
            )
            if not sent:
                raise RuntimeError(f"Stale deal notification failed for deal {deal.id}")

            _add_notification_log(
                db,
                notification_key,
                "notification.stale_deal",
                {
                    "deal_id": str(deal.id),
                    "owner_id": str(owner.id),
                    "last_activity_at": last_activity_at.isoformat() if last_activity_at else None,
                },
            )
            notified += 1

        await db.commit()
        return {"status": "ok", "stale_count": len(rows), "notified_count": notified}


async def _send_notification_email(to: str, subject: str, html: str) -> bool:
    import asyncio

    return await asyncio.to_thread(send_email, to, subject, html)


async def _notification_already_logged(db, notification_key: str) -> bool:
    result = await db.execute(
        select(TaskLog.id).where(
            TaskLog.task_id == notification_key,
            TaskLog.status == "success",
        )
    )
    return result.scalar_one_or_none() is not None


def _add_notification_log(db, notification_key: str, task_name: str, details: dict) -> None:
    now = datetime.now(timezone.utc)
    db.add(
        TaskLog(
            task_id=notification_key,
            task_name=task_name,
            status="success",
            started_at=now,
            finished_at=now,
            details=details,
        )
    )
