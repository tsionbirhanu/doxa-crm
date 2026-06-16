from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: str
    type: str
    title: str
    subtitle: str | None = None
    url: str


class GlobalSearchResponse(BaseModel):
    contacts: list[SearchResult] = Field(default_factory=list)
    deals: list[SearchResult] = Field(default_factory=list)
    accounts: list[SearchResult] = Field(default_factory=list)
    leads: list[SearchResult] = Field(default_factory=list)
