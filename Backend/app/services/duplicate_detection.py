from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead
from app.schemas.leads import DuplicateLeadPair

FUZZY_MATCH_THRESHOLD = 0.85


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _name_company_key(lead: Lead | dict[str, Any]) -> str:
    if isinstance(lead, dict):
        return f"{_normalize(lead.get('full_name'))} {_normalize(lead.get('company'))}".strip()
    return f"{_normalize(lead.full_name)} {_normalize(lead.company)}".strip()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


async def detect_duplicate_pairs(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
) -> list[DuplicateLeadPair]:
    result = await db.execute(
        select(Lead).where(Lead.is_active.is_(True)).order_by(Lead.created_at.asc())
    )
    leads = list(result.scalars().all())
    pairs: list[DuplicateLeadPair] = []

    for index, lead in enumerate(leads):
        for other in leads[index + 1 :]:
            duplicate = compare_leads(lead, other)
            if duplicate is not None:
                pairs.append(duplicate)

    offset = (max(page, 1) - 1) * min(max(page_size, 1), 100)
    limit = min(max(page_size, 1), 100)
    return pairs[offset : offset + limit]


def compare_leads(lead: Lead, other: Lead) -> DuplicateLeadPair | None:
    if _normalize(lead.email) and _normalize(lead.email) == _normalize(other.email):
        return DuplicateLeadPair(
            lead_id=lead.id,
            duplicate_lead_id=other.id,
            similarity_score=1.0,
            reason="email",
        )

    if _normalize(lead.phone) and _normalize(lead.phone) == _normalize(other.phone):
        return DuplicateLeadPair(
            lead_id=lead.id,
            duplicate_lead_id=other.id,
            similarity_score=1.0,
            reason="phone",
        )

    score = _similarity(_name_company_key(lead), _name_company_key(other))
    if score >= FUZZY_MATCH_THRESHOLD:
        return DuplicateLeadPair(
            lead_id=lead.id,
            duplicate_lead_id=other.id,
            similarity_score=round(score, 4),
            reason="name_company",
        )

    return None


async def find_duplicates_for_payload(
    db: AsyncSession,
    payload: dict[str, Any],
) -> list[DuplicateLeadPair]:
    result = await db.execute(select(Lead).where(Lead.is_active.is_(True)))
    leads = list(result.scalars().all())
    duplicates: list[DuplicateLeadPair] = []

    for lead in leads:
        email_matches = _normalize(payload.get("email")) == _normalize(lead.email)
        phone_matches = _normalize(payload.get("phone")) == _normalize(lead.phone)
        fuzzy_score = _similarity(_name_company_key(payload), _name_company_key(lead))

        if email_matches or phone_matches or fuzzy_score >= FUZZY_MATCH_THRESHOLD:
            duplicates.append(
                DuplicateLeadPair(
                    lead_id=lead.id,
                    duplicate_lead_id=lead.id,
                    similarity_score=1.0 if email_matches or phone_matches else round(fuzzy_score, 4),
                    reason="email" if email_matches else "phone" if phone_matches else "name_company",
                )
            )

    return duplicates
