from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "doxa_crm",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    beat_schedule={},
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_serializer="json",
    task_serializer="json",
    task_track_started=True,
    timezone="UTC",
)
