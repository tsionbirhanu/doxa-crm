from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:password@example.supabase.co:5432/postgres?ssl=require"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars"
os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_KEY"] = "test-supabase-key"

from app.config import get_settings

get_settings.cache_clear()

from app.dependencies import get_current_user, get_db
from app.main import create_app
from app.models import (
    AccountTier,
    ActivityType,
    DealStatus,
    TaskPriority,
    TaskStatus,
    UserRoleName,
)
import app.routers.accounts as accounts_router_module
import app.routers.contacts as contacts_router_module
from app.schemas.accounts import AccountResponse
from app.schemas.contacts import ContactResponse, ContactTimelineItem
from app.services.contacts import get_contact_timeline


class FakeResult:
    def __init__(self, value=None, values=None, scalar_value=None):
        self.value = value
        self.values = values or []
        self.scalar_value = scalar_value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.scalar_value

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, results):
        self.results = list(results)

    async def execute(self, statement):
        return self.results.pop(0)


def make_user(
    *,
    user_id: UUID | None = None,
    role: UserRoleName = UserRoleName.sales_manager,
):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=user_id or uuid4(),
        email="manager@example.com",
        full_name="Sales Manager",
        role=role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_account_response(account_id: UUID | None = None) -> AccountResponse:
    now = datetime.now(timezone.utc)
    return AccountResponse(
        id=account_id or uuid4(),
        name="Acme Corp",
        industry="Software",
        size="100-250",
        website="https://acme.example",
        address={"city": "Austin"},
        tier=AccountTier.smb,
        owner_id=uuid4(),
        owner_name="Sales Manager",
        custom_fields={"region": "west", "priority": True},
        is_active=True,
        linked_contact_count=2,
        total_deal_value=Decimal("12500.00"),
        created_at=now,
        updated_at=now,
    )


def make_contact_response(contact_id: UUID | None = None) -> ContactResponse:
    now = datetime.now(timezone.utc)
    return ContactResponse(
        id=contact_id or uuid4(),
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+15555550123",
        title="CTO",
        account_id=uuid4(),
        account_name="Acme Corp",
        owner_id=uuid4(),
        owner_name="Sales Manager",
        tags=["vip", "technical"],
        custom_fields={"preferred_channel": "email"},
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def app():
    test_app = create_app()
    current_user = make_user()

    async def override_get_db():
        yield object()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = lambda: current_user
    return test_app


@pytest.mark.asyncio
async def test_list_accounts_route_supports_pagination_and_filters(app, monkeypatch):
    owner_id = uuid4()
    account_response = make_account_response()

    async def fake_list_accounts(db, current_user, *, page, page_size, tier, owner_id: UUID | None, search: str | None):
        assert page == 2
        assert page_size == 5
        assert tier == AccountTier.smb
        assert owner_id is not None
        assert search == "Acme"
        return [account_response]

    monkeypatch.setattr(accounts_router_module.accounts_service, "list_accounts", fake_list_accounts)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/accounts/?page=2&page_size=5&tier=smb&owner_id={owner_id}&search=Acme"
        )

    assert response.status_code == 200
    assert response.json()[0]["linked_contact_count"] == 2


@pytest.mark.asyncio
async def test_get_account_route_returns_contact_count_and_deal_value(app, monkeypatch):
    account_id = uuid4()
    account_response = make_account_response(account_id)

    async def fake_get_account(db, account_id_arg, current_user):
        assert account_id_arg == account_id
        return account_response

    monkeypatch.setattr(accounts_router_module.accounts_service, "get_account", fake_get_account)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/accounts/{account_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(account_id)
    assert response.json()["linked_contact_count"] == 2
    assert Decimal(response.json()["total_deal_value"]) == Decimal("12500.00")


@pytest.mark.asyncio
async def test_account_create_rejects_nested_custom_fields(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/accounts/",
            json={
                "name": "Bad Custom Fields",
                "industry": "Software",
                "size": "1-10",
                "website": "https://bad.example",
                "tier": "startup",
                "custom_fields": {"nested": {"not": "allowed"}},
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_contacts_route_supports_filters_search_and_sort(app, monkeypatch):
    account_id = uuid4()
    owner_id = uuid4()
    contact_response = make_contact_response()

    async def fake_list_contacts(
        db,
        current_user,
        *,
        page,
        page_size,
        search,
        account_id: UUID | None,
        owner_id: UUID | None,
        tag,
        sort_by,
    ):
        assert page == 3
        assert page_size == 10
        assert search == "ada"
        assert account_id is not None
        assert owner_id is not None
        assert tag == "vip"
        assert sort_by == "company"
        return [contact_response]

    monkeypatch.setattr(contacts_router_module.contacts_service, "list_contacts", fake_list_contacts)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/contacts/"
            f"?page=3&page_size=10&search=ada&account_id={account_id}"
            f"&owner_id={owner_id}&tag=vip&sort_by=company"
        )

    assert response.status_code == 200
    assert response.json()[0]["account_name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_create_contact_route_accepts_scalar_custom_fields(app, monkeypatch):
    contact_response = make_contact_response()

    async def fake_create_contact(db, contact_in, current_user):
        assert contact_in.custom_fields == {"score": 12, "newsletter": True}
        return contact_response

    monkeypatch.setattr(contacts_router_module.contacts_service, "create_contact", fake_create_contact)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/contacts/",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "phone": "+15555550123",
                "title": "CTO",
                "custom_fields": {"score": 12, "newsletter": True},
            },
        )

    assert response.status_code == 201
    assert response.json()["email"] == "ada@example.com"


@pytest.mark.asyncio
async def test_get_contact_route_returns_enriched_detail(app, monkeypatch):
    contact_id = uuid4()
    contact_response = make_contact_response(contact_id)

    async def fake_get_contact(db, contact_id_arg, current_user):
        assert contact_id_arg == contact_id
        return contact_response

    monkeypatch.setattr(contacts_router_module.contacts_service, "get_contact", fake_get_contact)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/contacts/{contact_id}")

    assert response.status_code == 200
    assert response.json()["owner_name"] == "Sales Manager"


@pytest.mark.asyncio
async def test_timeline_endpoint_returns_unified_items(app, monkeypatch):
    contact_id = uuid4()
    now = datetime.now(timezone.utc)
    timeline = [
        ContactTimelineItem(
            id=uuid4(),
            type="note",
            title="Discovery notes",
            occurred_at=now,
            description="Asked about migration timeline",
            metadata={"activity_type": "note"},
        )
    ]

    async def fake_get_contact_timeline(db, contact_id_arg, current_user):
        assert contact_id_arg == contact_id
        return timeline

    monkeypatch.setattr(
        contacts_router_module.contacts_service,
        "get_contact_timeline",
        fake_get_contact_timeline,
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/contacts/{contact_id}/timeline")

    assert response.status_code == 200
    assert response.json()[0]["type"] == "note"


@pytest.mark.asyncio
async def test_timeline_service_merges_activities_tasks_notes_and_deals_chronologically():
    contact_id = uuid4()
    owner = make_user(role=UserRoleName.sales_rep)
    now = datetime.now(timezone.utc)
    contact = SimpleNamespace(id=contact_id, owner_id=owner.id, is_active=True)
    note = SimpleNamespace(
        id=uuid4(),
        type=ActivityType.note,
        subject="Call notes",
        body="Customer asked for a pilot",
        outcome=None,
        duration_minutes=None,
        contact_id=contact_id,
        completed_at=now,
        scheduled_at=None,
        created_at=now - timedelta(days=3),
    )
    activity = SimpleNamespace(
        id=uuid4(),
        type=ActivityType.email,
        subject="Follow-up email",
        body="Sent summary",
        outcome="sent",
        duration_minutes=None,
        contact_id=contact_id,
        completed_at=now - timedelta(hours=1),
        scheduled_at=None,
        created_at=now - timedelta(days=2),
    )
    task = SimpleNamespace(
        id=uuid4(),
        title="Prepare proposal",
        description="Draft proposal",
        status=TaskStatus.pending,
        priority=TaskPriority.high,
        contact_id=contact_id,
        completed_at=None,
        due_at=now + timedelta(days=1),
        created_at=now - timedelta(days=1),
    )
    deal = SimpleNamespace(
        id=uuid4(),
        title="Expansion",
        value=Decimal("5000.00"),
        currency="USD",
        status=DealStatus.open,
        probability=0.5,
        contact_id=contact_id,
        expected_close=date.today() + timedelta(days=2),
    )
    fake_db = FakeSession(
        [
            FakeResult(value=contact),
            FakeResult(values=[note, activity]),
            FakeResult(values=[task]),
            FakeResult(values=[deal]),
        ]
    )

    timeline = await get_contact_timeline(fake_db, contact_id, owner)

    assert {item.type for item in timeline} == {"note", "activity", "task", "deal"}
    assert timeline == sorted(timeline, key=lambda item: item.occurred_at, reverse=True)
