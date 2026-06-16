from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, TaskStatus

audit_logger = logging.getLogger("audit")


async def check_overdue_tasks(db: AsyncSession) -> list[Task]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Task)
        .where(
            Task.due_at.is_not(None),
            Task.due_at < now,
            Task.completed_at.is_(None),
            Task.status != TaskStatus.completed,
        )
        .order_by(Task.due_at.asc())
    )
    overdue_tasks = list(result.scalars().all())

    for task in overdue_tasks:
        audit_logger.info(
            "overdue_task task_id=%s owner_id=%s due_at=%s title=%s",
            task.id,
            task.owner_id,
            task.due_at,
            task.title,
        )

    return overdue_tasks
