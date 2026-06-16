from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead, User, UserRoleName

ROUND_ROBIN_STATE: defaultdict[str, int] = defaultdict(int)
TERRITORY_RULES: list[dict[str, str]] = []


def _lead_email_domain(lead: Lead) -> str:
    return lead.email.rsplit("@", 1)[-1].lower() if "@" in lead.email else ""


async def assign_lead(
    db: AsyncSession,
    lead: Lead,
    *,
    method: str = "manual",
    user_id: UUID | None = None,
    territory: str | None = None,
) -> UUID:
    if method == "manual":
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required for manual assignment",
            )
        return await _validate_user(db, user_id)

    if method == "territory":
        territory_user_id = await _match_territory(db, lead)
        if territory_user_id is not None:
            return territory_user_id
        return await _round_robin(db, territory or "default")

    if method == "round_robin":
        return await _round_robin(db, territory or "default")

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported assignment method",
    )


async def _validate_user(db: AsyncSession, user_id: UUID) -> UUID:
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found",
        )

    return user.id


async def _round_robin(db: AsyncSession, territory: str) -> UUID:
    result = await db.execute(
        select(User)
        .where(User.role == UserRoleName.sales_rep, User.is_active.is_(True))
        .order_by(User.created_at.asc())
    )
    users = list(result.scalars().all())

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active sales reps available for assignment",
        )

    index = ROUND_ROBIN_STATE[territory] % len(users)
    ROUND_ROBIN_STATE[territory] += 1
    return users[index].id


async def _match_territory(db: AsyncSession, lead: Lead) -> UUID | None:
    company = lead.company.lower()
    domain = _lead_email_domain(lead)

    for rule in TERRITORY_RULES:
        if rule.get("company", "").lower() and rule["company"].lower() in company:
            return await _validate_user(db, UUID(rule["user_id"]))
        if rule.get("domain", "").lower() and rule["domain"].lower() == domain:
            return await _validate_user(db, UUID(rule["user_id"]))

    return None
