from __future__ import annotations

from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.workers.task_logging import execute_with_retry


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.tasks.health_check",
)
def health_check(self) -> dict[str, str]:
    return execute_with_retry(self, self.name, _health_check)


async def _health_check() -> dict[str, str]:
    return {"status": "ok", "checked_at": datetime.now(timezone.utc).isoformat()}
