from __future__ import annotations

import json
import os
from datetime import datetime, timezone
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
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret-that-is-at-least-32-chars"

from app.config import get_settings

get_settings.cache_clear()

from app.dependencies import get_current_user, get_db
from app.main import create_app
from app.models import ActivityType, UserRoleName
import app.routers.webhooks as webhooks_router_module
from app.utils.webhooks import build_hmac_signature, verify_hmac_signature
from app.workers import webhook_tasks


class FakeResult:
    def __init__(self, value=None, values=None, row_values=None):
        self.value = value
        self.values = values or []
        self.row_values = row_values or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.values


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

    async def get(self, model, object_id):
        return None

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True

    async def refresh(self, value):
        now = datetime.now(timezone.utc)
        if getattr(value, "id", None) is None:
            value.id = uuid4()
        if getattr(value, "created_at", None) is None:
            value.created_at = now
        if getattr(value, "updated_at", None) is None:
            value.updated_at = now


def make_user(*, user_id: UUID | None = None, role: UserRoleName = UserRoleName.super_admin):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=user_id or uuid4(),
        email="admin@example.com",
        full_name="Admin",
        role=role,
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


def test_verify_hmac_signature_accepts_sha256_prefix_and_rejects_tampering():
    payload = b'{"email":"ada@example.com"}'
    signature = build_hmac_signature(payload, "shared-secret")

    assert verify_hmac_signature(payload, signature, "shared-secret") is True
    assert verify_hmac_signature(payload, signature.removeprefix("sha256="), "shared-secret") is True
    assert verify_hmac_signature(payload + b"!", signature, "shared-secret") is False


@pytest.mark.asyncio
async def test_lead_form_webhook_validates_signature_logs_and_queues(app, monkeypatch):
    payload = {
        "full_name": "Ada Lovelace",
        "email": "ada@acme.com",
        "phone": "+15555550123",
        "company": "Acme",
        "source": "website",
    }
    body = json.dumps(payload).encode("utf-8")
    signature = build_hmac_signature(body, get_settings().webhook_secret)
    queued: dict[str, object] = {}
    webhook_log_id = uuid4()

    async def fake_log_inbound_webhook(db, **kwargs):
        assert kwargs["event_type"] == "lead_form"
        assert kwargs["status"] == "accepted"
        assert kwargs["payload"]["email"] == "ada@acme.com"
        return SimpleNamespace(id=webhook_log_id)

    def fake_apply_async(*, args):
        queued["args"] = args

    monkeypatch.setattr(webhooks_router_module.webhooks_service, "log_inbound_webhook", fake_log_inbound_webhook)
    monkeypatch.setattr(webhooks_router_module.webhook_tasks.process_lead_form, "apply_async", fake_apply_async)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/lead-form",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": signature},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert queued["args"][0]["email"] == "ada@acme.com"
    assert queued["args"][1] == str(webhook_log_id)


@pytest.mark.asyncio
async def test_email_inbound_worker_matches_sender_contact_and_deal(monkeypatch):
    contact_id = uuid4()
    deal_id = uuid4()
    owner_id = uuid4()
    account_id = uuid4()
    contact = SimpleNamespace(
        id=contact_id,
        email="ada@example.com",
        account_id=account_id,
        owner_id=owner_id,
        is_active=True,
    )
    db = FakeSession([FakeResult(value=contact), FakeResult(value=deal_id)])

    monkeypatch.setattr(webhook_tasks, "AsyncSessionLocal", lambda: db)

    result = await webhook_tasks._process_email_inbound(
        {
            "from": "ada@example.com",
            "to": "sales@example.com",
            "subject": f"Re: Proposal [DEAL-{deal_id}]",
            "body": "Looks good.",
        },
        None,
    )

    assert result["status"] == "ok"
    activity = db.added[0]
    assert activity.type == ActivityType.email
    assert activity.contact_id == contact_id
    assert activity.account_id == account_id
    assert activity.deal_id == deal_id
    assert activity.owner_id == owner_id
