from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import ReportSnapshot
from app.services import reports
from app.workers.celery_app import celery_app
from app.workers.task_logging import execute_with_retry


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.report_tasks.generate_daily_snapshots",
)
def generate_daily_snapshots(self) -> dict[str, int | str]:
    return execute_with_retry(self, self.name, _generate_daily_snapshots)


async def _generate_daily_snapshots() -> dict[str, int | str]:
    snapshot_date = date.today()
    async with AsyncSessionLocal() as db:
        pipeline_rows = await reports.pipeline_summary(db, use_snapshot=False)
        lead_rows = await reports.lead_volume(db, use_snapshot=False)
        activity_rows = await reports.activity_volume(db, use_snapshot=False)

        snapshots = {
            "pipeline_summary": (
                "Daily Pipeline Summary",
                {"rows": [row.model_dump(mode="json") for row in pipeline_rows]},
            ),
            "lead_volume": (
                "Daily Lead Volume",
                {"rows": [row.model_dump(mode="json") for row in lead_rows]},
            ),
            "activity_volume": (
                "Daily Activity Volume",
                {"rows": [row.model_dump(mode="json") for row in activity_rows]},
            ),
        }

        upserted_count = 0
        for report_type, (name, data) in snapshots.items():
            result = await db.execute(
                select(ReportSnapshot).where(
                    ReportSnapshot.report_type == report_type,
                    ReportSnapshot.date == snapshot_date,
                )
            )
            snapshot = result.scalar_one_or_none()
            if snapshot is None:
                snapshot = ReportSnapshot(
                    name=name,
                    report_type=report_type,
                    date=snapshot_date,
                    filters={},
                    data=data,
                    generated_by=None,
                )
                db.add(snapshot)
            else:
                snapshot.name = name
                snapshot.filters = {}
                snapshot.data = data
            upserted_count += 1

        await db.commit()
        return {
            "status": "ok",
            "snapshot_count": upserted_count,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
