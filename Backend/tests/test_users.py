from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

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

from app.auth.jwt import ALGORITHM, decode_access_token
from app.dependencies import get_current_user, get_db
from app.main import create_app
from app.models import UserRoleName
from app.routers import users as users_router_module
from app.services.users import get_user


SECRET_KEY = get_settings().secret_key


class FakeResult:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values or []

    async def execute(self, statement):
        return FakeResult(self.value, self.values)


def make_user(
    *,
    user_id: UUID | None = None,
    role: UserRoleName = UserRoleName.sales_rep,
    is_active: bool = True,
):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=user_id or uuid4(),
        email="user@example.com",
        full_name="Test User",
        role=role,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def make_token(payload: dict) -> str:
    claims = {
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        **payload,
    }
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture
def app():
    test_app = create_app()

    async def override_get_db():
        yield object()

    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


@pytest.mark.asyncio
async def test_decode_access_token_accepts_valid_hs256_token():
    user_id = uuid4()
    token = make_token({"sub": str(user_id), "aud": "doxa-crm"})

    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)


@pytest.mark.asyncio
async def test_decode_access_token_rejects_expired_token():
    token = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_decodes_token_and_fetches_active_user():
    user_id = uuid4()
    db_user = make_user(user_id=user_id)
    token = make_token({"sub": str(user_id)})

    current_user = await get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        FakeSession(value=db_user),
    )

    assert current_user.id == user_id


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_user():
    db_user = make_user(is_active=False)
    token = make_token({"email": db_user.email})

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            FakeSession(value=db_user),
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_list_users_requires_super_admin_or_sales_manager(app):
    app.dependency_overrides[get_current_user] = lambda: make_user(
        role=UserRoleName.sales_rep,
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/users/")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_allows_sales_manager(app, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: make_user(
        role=UserRoleName.sales_manager,
    )
    listed_user = make_user(role=UserRoleName.marketing_rep)

    async def fake_list_users(db):
        return [listed_user]

    monkeypatch.setattr(users_router_module.users_service, "list_users", fake_list_users)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/users/")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(listed_user.id)


@pytest.mark.asyncio
async def test_create_user_accepts_metadata_only_for_super_admin(app, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: make_user(
        role=UserRoleName.super_admin,
    )

    async def fake_create_user(db, user_in):
        assert not hasattr(user_in, "password")
        return make_user(role=user_in.role)

    monkeypatch.setattr(users_router_module.users_service, "create_user", fake_create_user)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "created@example.com",
                "name": "Created User",
                "role": "customer_success",
            },
        )

    assert response.status_code == 201
    assert response.json()["role"] == "customer_success"


@pytest.mark.asyncio
async def test_get_user_returns_404_when_missing():
    with pytest.raises(HTTPException) as exc_info:
        await get_user(FakeSession(value=None), uuid4())

    assert exc_info.value.status_code == 404
