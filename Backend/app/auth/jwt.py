from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

from app.config import get_settings

ALGORITHM = "HS256"


def _auth_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
    except ExpiredSignatureError as exc:
        raise _auth_exception("Token has expired") from exc
    except JWTError as exc:
        raise _auth_exception("Invalid authentication credentials") from exc

    if not isinstance(payload, dict):
        raise _auth_exception("Invalid authentication credentials")

    return payload
