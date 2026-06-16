from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.models import User
from app.schemas.search import GlobalSearchResponse
from app.services import search as search_service

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/global", response_model=GlobalSearchResponse)
async def global_search(
    current_user: Annotated[User, Depends(get_current_user)],
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> GlobalSearchResponse:
    return await search_service.global_search(q, current_user, limit=limit)
