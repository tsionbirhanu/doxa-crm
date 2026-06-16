from __future__ import annotations

import os
from datetime import date, datetime, timezone
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
from app.models import DealStatus, UserRoleName
import app.routers.deals as deals_router_module
from app.schemas.deals import DealResponse
from app.services.deals import get_forecast, get_kanban
from app.services.pipeline import move_deal_to_stage


class FakeResult:
    def __init__(self, value=None, values=None, rows=None):
        self.value = value
        self.values = values or []
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.rows or self.values


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []

    async def execute(self, statement):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, value):
        return None


def make_user(*, user_id: UUID | None = None, role: UserRoleName = UserRoleName.sales_manager):
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


def make_stage(*, stage_id: UUID | None = None, pipeline_id: UUID | None = None, name="Proposal Sent", probability=50.0, order_index=2):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=stage_id or uuid4(),
        pipeline_id=pipeline_id or uuid4(),
        name=name,
        probability=probability,
        order_index=order_index,
        created_at=now,
        updated_at=now,
    )


def make_deal(*, deal_id: UUID | None = None, pipeline_id: UUID | None = None, stage_id: UUID | None = None, owner_id: UUID | None = None, value=Decimal("10000.00"), probability=50.0):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=deal_id or uuid4(),
        title="Acme Pilot",
        value=value,
        currency="USD",
        pipeline_id=pipeline_id or uuid4(),
        stage_id=stage_id or uuid4(),
        probability=probability,
        expected_close=date(2026, 7, 1),
        contact_id=uuid4(),
        account_id=uuid4(),
        owner_id=owner_id or uuid4(),
        status=DealStatus.open,
        lost_reason=None,
        closed_at=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_deal_response(deal_id: UUID | None = None, owner_id: UUID | None = None) -> DealResponse:
    deal = make_deal(deal_id=deal_id, owner_id=owner_id)
    return DealResponse(
        id=deal.id,
        title=deal.title,
        value=deal.value,
        currency=deal.currency,
        pipeline_id=deal.pipeline_id,
        pipeline_name="New Business",
        stage_id=deal.stage_id,
        stage_name="Proposal Sent",
        probability=deal.probability,
        expected_close=deal.expected_close,
        contact_id=deal.contact_id,
        contact_name="Ada Lovelace",
        account_id=deal.account_id,
        account_name="Acme",
        owner_id=deal.owner_id,
        owner_name="Sales Manager",
        status=deal.status,
        lost_reason=deal.lost_reason,
        closed_at=deal.closed_at,
        is_active=deal.is_active,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
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
async def test_create_deal_route(app, monkeypatch):
    owner = make_user()
    app.dependency_overrides[get_current_user] = lambda: owner
    deal_response = make_deal_response(owner_id=owner.id)

    async def fake_create_deal(db, deal_in, current_user):
        assert deal_in.title == "Acme Pilot"
        assert current_user.id == owner.id
        return deal_response

    monkeypatch.setattr(deals_router_module.deals_service, "create_deal", fake_create_deal)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/deals/",
            json={
                "title": "Acme Pilot",
                "value": "10000.00",
                "pipeline_id": str(uuid4()),
                "stage_id": str(uuid4()),
                "expected_close": "2026-07-01",
                "contact_id": str(uuid4()),
                "account_id": str(uuid4()),
            },
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Acme Pilot"


@pytest.mark.asyncio
async def test_stage_move_sets_won_and_logs_history():
    pipeline_id = uuid4()
    from_stage_id = uuid4()
    to_stage = make_stage(pipeline_id=pipeline_id, name="Closed Won", probability=100.0, order_index=4)
    deal = make_deal(pipeline_id=pipeline_id, stage_id=from_stage_id)
    user = make_user()
    db = FakeSession([FakeResult(value=to_stage)])

    moved = await move_deal_to_stage(db, deal, to_stage.id, user)

    assert moved.stage_id == to_stage.id
    assert moved.status == DealStatus.won
    assert moved.closed_at is not None
    assert len(db.added) == 1
    assert db.added[0].from_stage_id == from_stage_id
    assert db.added[0].to_stage_id == to_stage.id


@pytest.mark.asyncio
async def test_forecast_calculation_groups_weighted_revenue():
    user = make_user()
    stage_a = make_stage(name="Qualification", probability=25.0)
    stage_b = make_stage(name="Negotiation", probability=75.0)
    deal_a = make_deal(stage_id=stage_a.id, value=Decimal("1000.00"), probability=25.0)
    deal_b = make_deal(stage_id=stage_a.id, value=Decimal("2000.00"), probability=25.0)
    deal_c = make_deal(stage_id=stage_b.id, value=Decimal("4000.00"), probability=75.0)
    db = FakeSession([FakeResult(rows=[(deal_a, stage_a), (deal_b, stage_a), (deal_c, stage_b)])])

    forecast = await get_forecast(db, user)

    assert forecast.total_open == 7000.0
    assert forecast.total_weighted == 3750.0
    assert forecast.by_stage[0].stage == "Qualification"
    assert forecast.by_stage[0].count == 2


@pytest.mark.asyncio
async def test_kanban_grouping_places_deals_under_stages():
    user = make_user()
    pipeline_id = uuid4()
    stage_a = make_stage(pipeline_id=pipeline_id, name="Prospecting", probability=10.0, order_index=0)
    stage_b = make_stage(pipeline_id=pipeline_id, name="Proposal Sent", probability=50.0, order_index=1)
    deal_a = make_deal(pipeline_id=pipeline_id, stage_id=stage_a.id)
    deal_b = make_deal(pipeline_id=pipeline_id, stage_id=stage_b.id)
    db = FakeSession([FakeResult(values=[stage_a, stage_b]), FakeResult(values=[deal_a, deal_b])])

    kanban = await get_kanban(db, user, pipeline_id=pipeline_id)

    assert len(kanban.stages) == 2
    assert kanban.stages[0].name == "Prospecting"
    assert [deal.id for deal in kanban.stages[0].deals] == [deal_a.id]
    assert [deal.id for deal in kanban.stages[1].deals] == [deal_b.id]
