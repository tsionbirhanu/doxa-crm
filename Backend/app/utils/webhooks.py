from __future__ import annotations

import hmac
from hashlib import sha256


def verify_hmac_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False

    expected = hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()
    normalized = signature.strip()
    if normalized.startswith("sha256="):
        normalized = normalized.removeprefix("sha256=")

    return hmac.compare_digest(expected, normalized)


def build_hmac_signature(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()
    return f"sha256={digest}"
