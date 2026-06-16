from __future__ import annotations

from typing import Any

from app.database import AsyncSessionLocal
from app.services.project_health import update_project_health as update_project_health_service
from app.workers.celery_app import celery_app
from app.workers.task_logging import execute_with_retry


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.project_tasks.update_project_health",
)
def update_project_health(self) -> dict[str, Any]:
    return execute_with_retry(self, self.name, _update_project_health)


async def _update_project_health() -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        updated_count = await update_project_health_service(db)
        return {"status": "ok", "updated_count": updated_count}
