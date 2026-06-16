from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Account, Contact, Deal, Lead
from app.services.accounts import build_account_response
from app.services.contacts import build_contact_response
from app.services.deals import build_deal_response
from app.services.leads import build_lead_response
from app.services import search as search_service
from app.utils.search import ensure_search_indexes
from app.workers.celery_app import celery_app
from app.workers.task_logging import execute_with_retry


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.search_tasks.reindex_all",
)
def reindex_all(self) -> dict[str, Any]:
    return execute_with_retry(self, self.name, _reindex_all)


async def _reindex_all() -> dict[str, Any]:
    await ensure_search_indexes()
    async with AsyncSessionLocal() as db:
        counts = {
            "contacts": await _reindex_contacts(db),
            "deals": await _reindex_deals(db),
            "accounts": await _reindex_accounts(db),
            "leads": await _reindex_leads(db),
        }
        return {"status": "ok", "counts": counts}


async def _reindex_contacts(db) -> int:
    result = await db.execute(select(Contact).where(Contact.is_active.is_(True)).order_by(Contact.created_at.asc()))
    contacts = list(result.scalars().all())
    for contact in contacts:
        await search_service.sync_contact_to_search(await build_contact_response(db, contact))
    return len(contacts)


async def _reindex_deals(db) -> int:
    result = await db.execute(select(Deal).where(Deal.is_active.is_(True)).order_by(Deal.created_at.asc()))
    deals = list(result.scalars().all())
    for deal in deals:
        await search_service.sync_deal_to_search(await build_deal_response(db, deal))
    return len(deals)


async def _reindex_accounts(db) -> int:
    result = await db.execute(select(Account).where(Account.is_active.is_(True)).order_by(Account.created_at.asc()))
    accounts = list(result.scalars().all())
    for account in accounts:
        await search_service.sync_account_to_search(await build_account_response(db, account))
    return len(accounts)


async def _reindex_leads(db) -> int:
    result = await db.execute(select(Lead).where(Lead.is_active.is_(True)).order_by(Lead.created_at.asc()))
    leads = list(result.scalars().all())
    for lead in leads:
        await search_service.sync_lead_to_search(await build_lead_response(db, lead))
    return len(leads)
