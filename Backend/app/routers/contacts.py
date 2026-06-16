from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models import User
from app.schemas.contacts import (
    ContactCreate,
    ContactResponse,
    ContactTagsUpdate,
    ContactTimelineItem,
    ContactUpdate,
)
from app.services import contacts as contacts_service

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("/", response_model=list[ContactResponse])
async def list_contacts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    account_id: UUID | None = None,
    owner_id: UUID | None = None,
    tag: str | None = None,
    sort_by: Literal["created_at", "last_name", "company"] = "created_at",
) -> list[ContactResponse]:
    return await contacts_service.list_contacts(
        db,
        current_user,
        page=page,
        page_size=page_size,
        search=search,
        account_id=account_id,
        owner_id=owner_id,
        tag=tag,
        sort_by=sort_by,
    )


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact_in: ContactCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactResponse:
    return await contacts_service.create_contact(db, contact_in, current_user)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactResponse:
    return await contacts_service.get_contact(db, contact_id, current_user)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    contact_in: ContactUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactResponse:
    return await contacts_service.update_contact(db, contact_id, contact_in, current_user)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await contacts_service.soft_delete_contact(db, contact_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{contact_id}/export", response_model=dict)
async def export_contact_data(
    contact_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await contacts_service.export_contact_data(db, contact_id, current_user)


@router.delete("/{contact_id}/purge", response_model=dict)
async def purge_contact_data(
    contact_id: UUID,
    confirmation_token: str,
    current_user: Annotated[User, Depends(require_role("super_admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await contacts_service.purge_contact_data(db, contact_id, current_user, confirmation_token)


@router.get("/{contact_id}/timeline", response_model=list[ContactTimelineItem])
async def get_contact_timeline(
    contact_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ContactTimelineItem]:
    return await contacts_service.get_contact_timeline(db, contact_id, current_user)


@router.post("/{contact_id}/tags", response_model=ContactResponse)
async def add_contact_tags(
    contact_id: UUID,
    tags_in: ContactTagsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactResponse:
    return await contacts_service.add_contact_tags(db, contact_id, tags_in, current_user)


@router.delete("/{contact_id}/tags/{tag}", response_model=ContactResponse)
async def remove_contact_tag(
    contact_id: UUID,
    tag: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactResponse:
    return await contacts_service.remove_contact_tag(db, contact_id, tag, current_user)
