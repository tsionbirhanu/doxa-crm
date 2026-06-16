from __future__ import annotations

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@example.supabase.co:5432/postgres?ssl=require",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret-that-is-at-least-32-chars")

from app.models import UserRoleName


def make_test_user(*, user_id: UUID | None = None, role: UserRoleName = UserRoleName.sales_manager):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=user_id or uuid4(),
        email=f"{role.value}@example.com",
        full_name=role.value.replace("_", " ").title(),
        role=role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def super_admin_user():
    return make_test_user(role=UserRoleName.super_admin)


@pytest.fixture
def sales_manager_user():
    return make_test_user(role=UserRoleName.sales_manager)


@pytest.fixture
def sales_rep_user():
    return make_test_user(role=UserRoleName.sales_rep)


@pytest.fixture
def read_only_user():
    return make_test_user(role=UserRoleName.read_only)
