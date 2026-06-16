from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Lead
from app.services.lead_scoring import calculate_lead_score
from app.workers.celery_app import celery_app
from app.workers.task_logging import execute_with_retry


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.lead_tasks.recalculate_lead_scores",
)
def recalculate_lead_scores(self) -> dict[str, Any]:
    return execute_with_retry(self, self.name, _recalculate_lead_scores)


async def _recalculate_lead_scores() -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.is_active.is_(True)).order_by(Lead.created_at.asc()))
        leads = list(result.scalars().all())
        updated_count = 0

        for lead in leads:
            new_score = await calculate_lead_score(db, lead)
            if lead.score != new_score:
                lead.score = new_score
                updated_count += 1

        await db.commit()
        return {"status": "ok", "checked_count": len(leads), "updated_count": updated_count}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.lead_tasks.recalculate_lead_score",
)
def recalculate_lead_score(self, lead_id: str) -> dict[str, Any]:
    return execute_with_retry(
        self,
        self.name,
        lambda: _recalculate_lead_score(UUID(str(lead_id))),
        {"lead_id": lead_id},
    )


async def _recalculate_lead_score(lead_id: UUID) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.is_active.is_(True)))
        lead = result.scalar_one_or_none()
        if lead is None:
            return {"status": "missing_lead", "lead_id": str(lead_id)}

        new_score = await calculate_lead_score(db, lead)
        changed = lead.score != new_score
        lead.score = new_score
        await db.commit()
        return {"status": "ok", "lead_id": str(lead.id), "score": new_score, "changed": changed}
