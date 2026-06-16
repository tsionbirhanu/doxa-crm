from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity, ActivityType, Contact, User
from app.schemas.activities import ActivityCreate, ActivityResponse, ActivityUpdate, EmailLogCreate


def _pagination(page: int, page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    return (page - 1) * page_size, page_size


def _not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found")


async def list_activities(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    type_filter: ActivityType | None = None,
    owner_id: UUID | None = None,
    lead_id: UUID | None = None,
    contact_id: UUID | None = None,
    deal_id: UUID | None = None,
    account_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[ActivityResponse]:
    offset, limit = _pagination(page, page_size)
    query = select(Activity)

    if type_filter:
        query = query.where(Activity.type == type_filter)
    if owner_id:
        query = query.where(Activity.owner_id == owner_id)
    if lead_id:
        query = query.where(Activity.lead_id == lead_id)
    if contact_id:
        query = query.where(Activity.contact_id == contact_id)
    if deal_id:
        query = query.where(Activity.deal_id == deal_id)
    if account_id:
        query = query.where(Activity.account_id == account_id)
    if date_from:
        query = query.where(Activity.created_at >= date_from)
    if date_to:
        query = query.where(Activity.created_at <= date_to)

    result = await db.execute(query.order_by(Activity.created_at.desc()).offset(offset).limit(limit))
    return [ActivityResponse.model_validate(activity) for activity in result.scalars().all()]


async def get_activity_model(db: AsyncSession, activity_id: UUID) -> Activity:
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if activity is None:
        raise _not_found("Activity")
    return activity


async def get_activity(db: AsyncSession, activity_id: UUID) -> ActivityResponse:
    return ActivityResponse.model_validate(await get_activity_model(db, activity_id))


async def create_activity(
    db: AsyncSession,
    activity_in: ActivityCreate,
    current_user: User,
) -> ActivityResponse:
    data = activity_in.model_dump()
    data["owner_id"] = data.get("owner_id") or current_user.id
    activity = Activity(**data)
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return ActivityResponse.model_validate(activity)


async def update_activity(
    db: AsyncSession,
    activity_id: UUID,
    activity_in: ActivityUpdate,
) -> ActivityResponse:
    activity = await get_activity_model(db, activity_id)

    for field_name, value in activity_in.model_dump(exclude_unset=True).items():
        setattr(activity, field_name, value)

    await db.commit()
    await db.refresh(activity)
    return ActivityResponse.model_validate(activity)


async def delete_activity(db: AsyncSession, activity_id: UUID) -> None:
    activity = await get_activity_model(db, activity_id)
    await db.delete(activity)
    await db.commit()


async def log_email_activity(
    db: AsyncSession,
    email_in: EmailLogCreate,
    current_user: User,
) -> ActivityResponse:
    result = await db.execute(
        select(Contact).where(
            Contact.email == email_in.contact_email,
            Contact.is_active.is_(True),
        )
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        raise _not_found("Contact")

    activity = Activity(
        type=ActivityType.email,
        subject=email_in.subject,
        body=email_in.body,
        outcome=f"Email logged from {email_in.from_email} to {email_in.to_email}",
        contact_id=contact.id,
        account_id=contact.account_id,
        owner_id=current_user.id,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return ActivityResponse.model_validate(activity)
