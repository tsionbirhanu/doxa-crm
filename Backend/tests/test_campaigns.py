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
from app.models import (
    CampaignEnrollmentStatus,
    CampaignMetricEventType,
    CampaignSequenceChannel,
    CampaignStatus,
    CampaignType,
    UserRoleName,
)
import app.routers.campaigns as campaigns_router_module
import app.services.campaigns as campaigns_service
from app.schemas.campaigns import (
    CampaignEnrollmentResponse,
    CampaignEnrollRequest,
    CampaignMetricsResponse,
    CampaignResponse,
    CampaignStepResponse,
)
from app.workers import campaign_tasks


class FakeResult:
    def __init__(self, value=None, values=None, rows=None, scalar_value=None):
        self.value = value
        self.values = values or []
        self.rows = rows or []
        self.scalar_value = scalar_value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.scalar_value

    def scalars(self):
        return self

    def all(self):
        return self.rows or self.values


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True

    async def flush(self):
        return None

    async def refresh(self, value):
        return None


def make_user(user_id: UUID | None = None):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=user_id or uuid4(),
        email="marketer@example.com",
        full_name="Marketing Manager",
        role=UserRoleName.marketing_manager,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_campaign_response(campaign_id: UUID | None = None, owner_id: UUID | None = None) -> CampaignResponse:
    now = datetime.now(timezone.utc)
    return CampaignResponse(
        id=campaign_id or uuid4(),
        name="Spring Outreach",
        type=CampaignType.email,
        status=CampaignStatus.draft,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        target_segment={"tier": "smb"},
        budget=Decimal("1500.00"),
        owner_id=owner_id or uuid4(),
        owner_name="Marketing Manager",
        enrollment_count=0,
        metrics=CampaignMetricsResponse(sent=0, opened=0, clicked=0, replied=0, converted=0),
        created_at=now,
        updated_at=now,
    )


def make_enrollment_response(campaign_id: UUID, contact_id: UUID) -> CampaignEnrollmentResponse:
    now = datetime.now(timezone.utc)
    return CampaignEnrollmentResponse(
        id=uuid4(),
        campaign_id=campaign_id,
        contact_id=contact_id,
        contact_name="Ada Lovelace",
        contact_email="ada@example.com",
        enrolled_at=now,
        step_index=0,
        status=CampaignEnrollmentStatus.unsubscribed,
        created_at=now,
        updated_at=now,
    )


def make_step_response(campaign_id: UUID, step_id: UUID | None = None, step_index: int = 0) -> CampaignStepResponse:
    now = datetime.now(timezone.utc)
    return CampaignStepResponse(
        id=step_id or uuid4(),
        campaign_id=campaign_id,
        step_index=step_index,
        channel=CampaignSequenceChannel.email,
        subject="Hello",
        body="Welcome",
        delay_days=1,
        variant="A",
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
async def test_create_campaign_route(app, monkeypatch):
    owner = make_user()
    app.dependency_overrides[get_current_user] = lambda: owner
    campaign_response = make_campaign_response(owner_id=owner.id)

    async def fake_create_campaign(db, campaign_in, current_user):
        assert campaign_in.name == "Spring Outreach"
        assert current_user.id == owner.id
        return campaign_response

    monkeypatch.setattr(campaigns_router_module.campaigns_service, "create_campaign", fake_create_campaign)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/campaigns/",
            json={
                "name": "Spring Outreach",
                "type": "email",
                "start_date": "2026-06-01",
                "end_date": "2026-06-30",
                "target_segment": {"tier": "smb"},
                "budget": "1500.00",
            },
        )

    assert response.status_code == 201
    assert response.json()["name"] == "Spring Outreach"


@pytest.mark.asyncio
async def test_enroll_contacts_route(app, monkeypatch):
    campaign_id = uuid4()
    contact_id = uuid4()
    enrollment_response = make_enrollment_response(campaign_id, contact_id)

    async def fake_enroll_contacts(db, campaign_id_arg, enroll_in):
        assert campaign_id_arg == campaign_id
        assert enroll_in.contact_ids == [contact_id]
        return [enrollment_response]

    monkeypatch.setattr(campaigns_router_module.campaigns_service, "enroll_contacts", fake_enroll_contacts)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/enroll",
            json={"contact_ids": [str(contact_id)]},
        )

    assert response.status_code == 200
    assert response.json()[0]["contact_id"] == str(contact_id)


@pytest.mark.asyncio
async def test_enroll_contacts_is_idempotent_for_active_enrollment(monkeypatch):
    campaign_id = uuid4()
    contact_id = uuid4()
    now = datetime.now(timezone.utc)
    contact = SimpleNamespace(id=contact_id, first_name="Ada", last_name="Lovelace", email="ada@example.com")
    enrollment = SimpleNamespace(
        id=uuid4(),
        campaign_id=campaign_id,
        contact_id=contact_id,
        enrolled_at=now,
        step_index=2,
        status=CampaignEnrollmentStatus.active,
        created_at=now,
        updated_at=now,
    )
    db = FakeSession(
        [
            FakeResult(value=SimpleNamespace(id=campaign_id, status=CampaignStatus.active)),
            FakeResult(value=contact),
            FakeResult(value=enrollment),
            FakeResult(value=contact),
        ]
    )
    scheduled: list[UUID] = []

    monkeypatch.setattr(campaigns_service, "_schedule_campaign_step", scheduled.append)

    result = await campaigns_service.enroll_contacts(
        db,
        campaign_id,
        CampaignEnrollRequest(contact_ids=[contact_id]),
    )

    assert result[0].contact_id == contact_id
    assert enrollment.status == CampaignEnrollmentStatus.active
    assert enrollment.step_index == 2
    assert scheduled == []


@pytest.mark.asyncio
async def test_enroll_contacts_restarts_unsubscribed_enrollment(monkeypatch):
    campaign_id = uuid4()
    contact_id = uuid4()
    old_enrolled_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    contact = SimpleNamespace(id=contact_id, first_name="Ada", last_name="Lovelace", email="ada@example.com")
    enrollment = SimpleNamespace(
        id=uuid4(),
        campaign_id=campaign_id,
        contact_id=contact_id,
        enrolled_at=old_enrolled_at,
        step_index=3,
        status=CampaignEnrollmentStatus.unsubscribed,
        created_at=now,
        updated_at=now,
    )
    db = FakeSession(
        [
            FakeResult(value=SimpleNamespace(id=campaign_id, status=CampaignStatus.active)),
            FakeResult(value=contact),
            FakeResult(value=enrollment),
            FakeResult(value=contact),
        ]
    )
    scheduled: list[UUID] = []

    monkeypatch.setattr(campaigns_service, "_schedule_campaign_step", scheduled.append)

    result = await campaigns_service.enroll_contacts(
        db,
        campaign_id,
        CampaignEnrollRequest(contact_ids=[contact_id]),
    )

    assert result[0].status == CampaignEnrollmentStatus.active
    assert enrollment.status == CampaignEnrollmentStatus.active
    assert enrollment.step_index == 0
    assert enrollment.enrolled_at > old_enrolled_at
    assert scheduled == [enrollment.id]


@pytest.mark.asyncio
async def test_enroll_contacts_does_not_schedule_draft_campaign(monkeypatch):
    campaign_id = uuid4()
    contact_id = uuid4()
    now = datetime.now(timezone.utc)
    contact = SimpleNamespace(id=contact_id, first_name="Ada", last_name="Lovelace", email="ada@example.com")
    enrollment = SimpleNamespace(
        id=uuid4(),
        campaign_id=campaign_id,
        contact_id=contact_id,
        enrolled_at=now,
        step_index=0,
        status=CampaignEnrollmentStatus.unsubscribed,
        created_at=now,
        updated_at=now,
    )
    db = FakeSession(
        [
            FakeResult(value=SimpleNamespace(id=campaign_id, status=CampaignStatus.draft)),
            FakeResult(value=contact),
            FakeResult(value=enrollment),
            FakeResult(value=contact),
        ]
    )
    scheduled: list[UUID] = []

    monkeypatch.setattr(campaigns_service, "_schedule_campaign_step", scheduled.append)

    result = await campaigns_service.enroll_contacts(
        db,
        campaign_id,
        CampaignEnrollRequest(contact_ids=[contact_id]),
    )

    assert result[0].status == CampaignEnrollmentStatus.active
    assert enrollment.status == CampaignEnrollmentStatus.active
    assert scheduled == []


@pytest.mark.asyncio
async def test_sequence_step_crud_routes(app, monkeypatch):
    campaign_id = uuid4()
    step_id = uuid4()
    created_step = make_step_response(campaign_id, step_id)
    updated_step = make_step_response(campaign_id, step_id)
    updated_step.subject = "Updated subject"

    async def fake_add_step(db, campaign_id_arg, step_in):
        assert campaign_id_arg == campaign_id
        assert step_in.variant == "A"
        return created_step

    async def fake_update_step(db, campaign_id_arg, step_id_arg, step_in):
        assert campaign_id_arg == campaign_id
        assert step_id_arg == step_id
        assert step_in.subject == "Updated subject"
        return updated_step

    async def fake_delete_step(db, campaign_id_arg, step_id_arg):
        assert campaign_id_arg == campaign_id
        assert step_id_arg == step_id

    monkeypatch.setattr(campaigns_router_module.campaigns_service, "add_step", fake_add_step)
    monkeypatch.setattr(campaigns_router_module.campaigns_service, "update_step", fake_update_step)
    monkeypatch.setattr(campaigns_router_module.campaigns_service, "delete_step", fake_delete_step)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/steps",
            json={"subject": "Hello", "body": "Welcome", "delay_days": 1, "variant": "A"},
        )
        update_response = await client.patch(
            f"/api/v1/campaigns/{campaign_id}/steps/{step_id}",
            json={"subject": "Updated subject"},
        )
        delete_response = await client.delete(f"/api/v1/campaigns/{campaign_id}/steps/{step_id}")

    assert create_response.status_code == 201
    assert create_response.json()["variant"] == "A"
    assert update_response.status_code == 200
    assert update_response.json()["subject"] == "Updated subject"
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_process_campaign_step_sends_email_records_metric_and_schedules_next(monkeypatch):
    campaign_id = uuid4()
    contact_id = uuid4()
    enrollment_id = uuid4()
    current_step_id = uuid4()
    next_step_id = uuid4()
    enrollment = SimpleNamespace(
        id=enrollment_id,
        campaign_id=campaign_id,
        contact_id=contact_id,
        step_index=0,
        status=CampaignEnrollmentStatus.active,
    )
    contact = SimpleNamespace(id=contact_id, email="ada@example.com")
    current_step = SimpleNamespace(
        id=current_step_id,
        campaign_id=campaign_id,
        step_index=0,
        subject="Hello",
        body="Welcome",
        delay_days=0,
    )
    next_step = SimpleNamespace(
        id=next_step_id,
        campaign_id=campaign_id,
        step_index=1,
        subject="Follow up",
        body="Checking in",
        delay_days=2,
    )
    db = FakeSession(
        [
            FakeResult(value=enrollment),
            FakeResult(value=SimpleNamespace(id=campaign_id, status=CampaignStatus.active)),
            FakeResult(value=contact),
            FakeResult(value=current_step),
            FakeResult(value=None),
            FakeResult(value=next_step),
        ]
    )
    scheduled: dict[str, object] = {}

    async def fake_send_email(to_email, subject, body):
        assert to_email == "ada@example.com"
        assert subject == "Hello"
        return {"id": "email_123"}

    def fake_apply_async(*, args, countdown):
        scheduled["args"] = args
        scheduled["countdown"] = countdown

    monkeypatch.setattr(campaign_tasks, "AsyncSessionLocal", lambda: db)
    monkeypatch.setattr(campaign_tasks, "send_email_via_resend", fake_send_email)
    monkeypatch.setattr(campaign_tasks.process_campaign_step, "apply_async", fake_apply_async)

    result = await campaign_tasks._process_campaign_step(enrollment_id)

    assert result["status"] == "scheduled_next"
    assert enrollment.step_index == 1
    assert db.committed is True
    assert db.added[0].event_type == CampaignMetricEventType.sent
    assert scheduled["args"] == [str(enrollment_id)]
    assert scheduled["countdown"] == 172800


@pytest.mark.asyncio
async def test_process_campaign_step_skips_paused_campaign(monkeypatch):
    campaign_id = uuid4()
    contact_id = uuid4()
    enrollment_id = uuid4()
    enrollment = SimpleNamespace(
        id=enrollment_id,
        campaign_id=campaign_id,
        contact_id=contact_id,
        step_index=0,
        status=CampaignEnrollmentStatus.active,
    )
    db = FakeSession(
        [
            FakeResult(value=enrollment),
            FakeResult(value=SimpleNamespace(id=campaign_id, status=CampaignStatus.paused)),
        ]
    )

    monkeypatch.setattr(campaign_tasks, "AsyncSessionLocal", lambda: db)

    result = await campaign_tasks._process_campaign_step(enrollment_id)

    assert result == {"status": "skipped", "reason": "paused"}
    assert db.committed is False
