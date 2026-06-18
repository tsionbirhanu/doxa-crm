from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.dependencies import get_current_user, get_db
from app.main import create_app
from app.models import UserRoleName


def make_user(role: UserRoleName = UserRoleName.read_only):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        email=f"{role.value}@example.com",
        full_name=role.value.replace("_", " ").title(),
        role=role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def app():
    test_app = create_app()

    async def override_get_db():
        yield object()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = lambda: make_user(UserRoleName.read_only)
    return test_app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "post",
            "/api/v1/accounts/",
            {
                "name": "Acme",
                "industry": "Software",
                "size": "51-200",
                "website": "https://acme.example",
                "tier": "enterprise",
            },
        ),
        (
            "post",
            "/api/v1/contacts/",
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "phone": "+15555550123",
                "title": "CTO",
            },
        ),
        (
            "post",
            "/api/v1/leads/",
            {
                "full_name": "Grace Hopper",
                "email": "grace@example.com",
                "phone": "+15555550124",
                "company": "Navy Labs",
                "source": "referral",
            },
        ),
        (
            "post",
            "/api/v1/deals/",
            {
                "title": "Acme New Business",
                "value": "25000.00",
                "pipeline_id": str(uuid4()),
                "expected_close": date.today().isoformat(),
                "contact_id": str(uuid4()),
                "account_id": str(uuid4()),
            },
        ),
        (
            "post",
            "/api/v1/activities/",
            {
                "type": "call",
                "subject": "Intro call",
                "body": "Discussed requirements",
                "contact_id": str(uuid4()),
            },
        ),
        (
            "post",
            "/api/v1/tasks/",
            {
                "title": "Follow up",
                "contact_id": str(uuid4()),
            },
        ),
        (
            "post",
            "/api/v1/campaigns/",
            {
                "name": "June Nurture",
                "type": "email",
                "start_date": date.today().isoformat(),
                "end_date": date.today().isoformat(),
                "budget": "1000.00",
            },
        ),
        (
            "post",
            "/api/v1/projects/",
            {
                "name": "Acme Onboarding",
                "account_id": str(uuid4()),
                "start_date": date.today().isoformat(),
                "end_date": date.today().isoformat(),
            },
        ),
        ("post", "/api/v1/pipelines/", {"name": "Enterprise Sales"}),
        (
            "post",
            "/api/v1/users/",
            {
                "email": "new.user@example.com",
                "full_name": "New User",
                "role": "sales_rep",
            },
        ),
    ],
)
async def test_read_only_user_cannot_write_any_module(app, method, path, payload):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await getattr(client, method)(path, json=payload)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_sales_manager_cannot_create_users(app):
    app.dependency_overrides[get_current_user] = lambda: make_user(UserRoleName.sales_manager)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "new.user@example.com",
                "full_name": "New User",
                "role": "sales_rep",
            },
        )

    assert response.status_code == 403
