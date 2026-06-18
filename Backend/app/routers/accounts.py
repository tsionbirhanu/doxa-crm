from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import ACCOUNT_WRITE_ROLES
from app.dependencies import get_current_user, get_db, require_role
from app.models import AccountTier, User
from app.schemas.accounts import AccountCreate, AccountDealResponse, AccountResponse, AccountUpdate
from app.schemas.contacts import ContactResponse
from app.services import accounts as accounts_service

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    tier: AccountTier | None = None,
    owner_id: UUID | None = None,
) -> list[AccountResponse]:
    return await accounts_service.list_accounts(
        db,
        current_user,
        page=page,
        page_size=page_size,
        tier=tier,
        owner_id=owner_id,
    )


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_in: AccountCreate,
    current_user: Annotated[User, Depends(require_role(*ACCOUNT_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    return await accounts_service.create_account(db, account_in, current_user)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    return await accounts_service.get_account(db, account_id, current_user)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    account_in: AccountUpdate,
    current_user: Annotated[User, Depends(require_role(*ACCOUNT_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    return await accounts_service.update_account(db, account_id, account_in, current_user)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    current_user: Annotated[User, Depends(require_role(*ACCOUNT_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await accounts_service.soft_delete_account(db, account_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{account_id}/contacts", response_model=list[ContactResponse])
async def list_account_contacts(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ContactResponse]:
    return await accounts_service.list_account_contacts(
        db,
        account_id,
        current_user,
        page=page,
        page_size=page_size,
    )


@router.get("/{account_id}/deals", response_model=list[AccountDealResponse])
async def list_account_deals(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[AccountDealResponse]:
    return await accounts_service.list_account_deals(
        db,
        account_id,
        current_user,
        page=page,
        page_size=page_size,
    )
