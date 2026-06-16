from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from app.auth.jwt import decode_access_token
from app.config import get_settings
from app.dependencies import require_role
from app.models import UserRoleName
from tests.conftest import make_test_user


def test_decode_access_token_happy_path():
    settings = get_settings()
    token = jwt.encode(
        {"sub": "user-1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.secret_key,
        algorithm="HS256",
    )

    assert decode_access_token(token)["sub"] == "user-1"


def test_decode_access_token_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc:
        decode_access_token("not-a-jwt")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_role_allows_and_rejects_roles():
    allowed_dependency = require_role("super_admin")
    denied_dependency = require_role("sales_manager")
    user = make_test_user(role=UserRoleName.super_admin)

    assert await allowed_dependency(user) is user
    with pytest.raises(HTTPException) as exc:
        await denied_dependency(user)

    assert exc.value.status_code == 403
