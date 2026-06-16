from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

SEARCH_INDEXES = {
    "contacts": {
        "searchableAttributes": ["last_name", "first_name", "email", "company"],
        "filterableAttributes": ["owner_id", "account_id", "tags"],
    },
    "deals": {
        "searchableAttributes": ["title", "contact_name", "account_name"],
        "filterableAttributes": ["owner_id", "stage_id", "status"],
    },
    "accounts": {
        "searchableAttributes": ["name", "industry", "website"],
        "filterableAttributes": ["owner_id", "tier"],
    },
    "leads": {
        "searchableAttributes": ["full_name", "email", "company"],
        "filterableAttributes": ["assigned_to", "status", "source"],
    },
}


@dataclass(slots=True)
class AsyncMeilisearch:
    url: str | None
    api_key: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(self, method: str, path: str, *, json: Any | None = None) -> Any:
        if not self.enabled:
            return None

        assert self.url is not None
        async with httpx.AsyncClient(base_url=self.url.rstrip("/"), timeout=15) as client:
            response = await client.request(method, path, headers=self._headers, json=json)
            if response.status_code == 404 and method == "DELETE":
                return None
            if response.status_code == 409 and path == "/indexes":
                return None
            response.raise_for_status()
            if not response.content:
                return None
            return response.json()

    async def create_index(self, index: str, primary_key: str = "id") -> None:
        await self._request("POST", "/indexes", json={"uid": index, "primaryKey": primary_key})

    async def update_settings(self, index: str, settings: dict[str, list[str]]) -> None:
        await self._request("PATCH", f"/indexes/{index}/settings", json=settings)

    async def add_or_replace_documents(self, index: str, documents: list[dict[str, Any]]) -> None:
        if not documents:
            return
        await self._request("POST", f"/indexes/{index}/documents", json=documents)

    async def delete_document(self, index: str, document_id: str) -> None:
        await self._request("DELETE", f"/indexes/{index}/documents/{document_id}")

    async def search(self, index: str, query: str, *, limit: int = 20, filter: str | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"q": query, "limit": limit}
        if filter:
            payload["filter"] = filter
        result = await self._request("POST", f"/indexes/{index}/search", json=payload)
        return list((result or {}).get("hits", []))


def get_search_client() -> AsyncMeilisearch:
    settings = get_settings()
    return AsyncMeilisearch(settings.meilisearch_url, settings.meilisearch_api_key)


async def ensure_search_indexes() -> None:
    client = get_search_client()
    for index, settings in SEARCH_INDEXES.items():
        await client.create_index(index)
        await client.update_settings(index, settings)


async def sync_to_search(index: str, document_id: str, data: dict[str, Any]) -> None:
    if index not in SEARCH_INDEXES:
        raise ValueError(f"Unknown search index: {index}")
    document = {"id": str(document_id), **_json_safe(data)}
    try:
        await get_search_client().add_or_replace_documents(index, [document])
    except Exception:
        logger.exception("search_sync_failed index=%s document_id=%s", index, document_id)


async def delete_from_search(index: str, document_id: str) -> None:
    if index not in SEARCH_INDEXES:
        raise ValueError(f"Unknown search index: {index}")
    try:
        await get_search_client().delete_document(index, str(document_id))
    except Exception:
        logger.exception("search_delete_failed index=%s document_id=%s", index, document_id)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value
