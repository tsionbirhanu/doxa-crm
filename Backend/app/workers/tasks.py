from __future__ import annotations

from datetime import datetime, timezone

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.health_check")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
