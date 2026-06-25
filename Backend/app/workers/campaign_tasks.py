from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import (
    Campaign,
    CampaignEnrollment,
    CampaignEnrollmentStatus,
    CampaignMetric,
    CampaignMetricEventType,
    CampaignSequenceStep,
    CampaignStatus,
    Contact,
)
from app.utils.email import send_email
from app.workers.celery_app import celery_app
from app.workers.task_logging import execute_with_retry

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.campaign_tasks.process_campaign_step",
)
def process_campaign_step(self, enrollment_id: str) -> dict[str, Any]:
    return execute_with_retry(
        self,
        self.name,
        lambda: _process_campaign_step(UUID(str(enrollment_id))),
        {"enrollment_id": enrollment_id},
    )


async def _process_campaign_step(enrollment_id: UUID) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        enrollment_result = await db.execute(
            select(CampaignEnrollment).where(CampaignEnrollment.id == enrollment_id)
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if enrollment is None:
            return {"status": "missing_enrollment"}

        if enrollment.status != CampaignEnrollmentStatus.active:
            return {"status": "skipped", "reason": enrollment.status.value}

        campaign_result = await db.execute(select(Campaign).where(Campaign.id == enrollment.campaign_id))
        campaign = campaign_result.scalar_one_or_none()
        if campaign is None:
            return {"status": "missing_campaign"}

        if campaign.status != CampaignStatus.active:
            return {"status": "skipped", "reason": campaign.status.value}

        contact_result = await db.execute(select(Contact).where(Contact.id == enrollment.contact_id))
        contact = contact_result.scalar_one_or_none()
        if contact is None:
            return {"status": "missing_contact"}

        step_result = await db.execute(
            select(CampaignSequenceStep).where(
                CampaignSequenceStep.campaign_id == enrollment.campaign_id,
                CampaignSequenceStep.step_index == enrollment.step_index,
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            enrollment.status = CampaignEnrollmentStatus.completed
            await db.commit()
            return {"status": "completed", "reason": "no_step"}

        sent_metric_result = await db.execute(
            select(CampaignMetric).where(
                CampaignMetric.campaign_id == enrollment.campaign_id,
                CampaignMetric.contact_id == enrollment.contact_id,
                CampaignMetric.step_id == step.id,
                CampaignMetric.event_type == CampaignMetricEventType.sent,
            )
        )
        already_sent = sent_metric_result.scalar_one_or_none() is not None
        if not already_sent:
            await send_email_via_resend(contact.email, step.subject, step.body or "")
            db.add(
                CampaignMetric(
                    campaign_id=enrollment.campaign_id,
                    contact_id=enrollment.contact_id,
                    step_id=step.id,
                    event_type=CampaignMetricEventType.sent,
                )
            )

        next_step_result = await db.execute(
            select(CampaignSequenceStep).where(
                CampaignSequenceStep.campaign_id == enrollment.campaign_id,
                CampaignSequenceStep.step_index == enrollment.step_index + 1,
            )
        )
        next_step = next_step_result.scalar_one_or_none()
        if next_step is None:
            enrollment.status = CampaignEnrollmentStatus.completed
            await db.commit()
            return {"status": "completed", "step_id": str(step.id), "already_sent": already_sent}

        enrollment.step_index = next_step.step_index
        await db.commit()
        process_campaign_step.apply_async(
            args=[str(enrollment.id)],
            countdown=next_step.delay_days * 86400,
        )
        return {
            "status": "scheduled_next",
            "step_id": str(step.id),
            "next_step_id": str(next_step.id),
            "already_sent": already_sent,
        }


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.campaign_tasks.enroll_contact_in_campaign",
)
def enroll_contact_in_campaign(self, campaign_id: str, contact_id: str) -> dict[str, Any]:
    return execute_with_retry(
        self,
        self.name,
        lambda: _enroll_contact_in_campaign(UUID(str(campaign_id)), UUID(str(contact_id))),
        {"campaign_id": campaign_id, "contact_id": contact_id},
    )


async def _enroll_contact_in_campaign(campaign_id: UUID, contact_id: UUID) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        campaign_result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = campaign_result.scalar_one_or_none()
        if campaign is None:
            return {"status": "missing_campaign"}

        existing_result = await db.execute(
            select(CampaignEnrollment).where(
                CampaignEnrollment.campaign_id == campaign_id,
                CampaignEnrollment.contact_id == contact_id,
            )
        )
        enrollment = existing_result.scalar_one_or_none()
        if enrollment is None:
            enrollment = CampaignEnrollment(campaign_id=campaign_id, contact_id=contact_id)
            db.add(enrollment)
            await db.flush()
        else:
            enrollment.status = CampaignEnrollmentStatus.active
            enrollment.step_index = 0

        await db.commit()
        if campaign.status == CampaignStatus.active:
            process_campaign_step.apply_async(args=[str(enrollment.id)], countdown=0)
        return {"status": "enrolled", "enrollment_id": str(enrollment.id)}


async def send_email_via_resend(to_email: str, subject: str, body: str) -> dict[str, Any]:
    sent = await asyncio.to_thread(send_email, to_email, subject, body)
    if not sent:
        raise RuntimeError("Campaign email could not be sent")
    return {"id": "sent", "to": to_email}
