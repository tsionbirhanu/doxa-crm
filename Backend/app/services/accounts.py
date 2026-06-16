from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import exists, func, or_, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, AccountTier, Contact, Deal, User, UserRoleName
from app.schemas.accounts import AccountCreate, AccountDealResponse, AccountResponse, AccountUpdate
from app.services.contacts import build_contact_response, contact_visibility_filter
from app.services import search as search_service

SALES_REP_ROLE = UserRoleName.sales_rep.value


def _role_value(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def _is_sales_rep(user: User) -> bool:
    return _role_value(user) == SALES_REP_ROLE


def _pagination(page: int, page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    return (page - 1) * page_size, page_size


def account_visibility_filter(current_user: User):
    if _is_sales_rep(current_user):
        owned_contact_exists = exists(
            select(Contact.id).where(
                Contact.account_id == Account.id,
                Contact.owner_id == current_user.id,
                Contact.is_active.is_(True),
            )
        )
        return or_(Account.owner_id == current_user.id, owned_contact_exists)

    return true()


def _account_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Account not found",
    )


async def build_account_response(db: AsyncSession, account: Account) -> AccountResponse:
    owner_result = await db.execute(select(User.full_name).where(User.id == account.owner_id))
    owner_name = owner_result.scalar_one_or_none()

    contact_count_result = await db.execute(
        select(func.count(Contact.id)).where(
            Contact.account_id == account.id,
            Contact.is_active.is_(True),
        )
    )
    linked_contact_count = int(contact_count_result.scalar_one() or 0)

    deal_value_result = await db.execute(
        select(func.coalesce(func.sum(Deal.value), 0)).where(Deal.account_id == account.id)
    )
    total_deal_value = deal_value_result.scalar_one() or Decimal("0")

    return AccountResponse(
        id=account.id,
        name=account.name,
        industry=account.industry,
        size=account.size,
        website=account.website,
        address=dict(account.address or {}),
        tier=account.tier,
        owner_id=account.owner_id,
        owner_name=owner_name,
        custom_fields=dict(account.custom_fields or {}),
        is_active=account.is_active,
        linked_contact_count=linked_contact_count,
        total_deal_value=total_deal_value,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


async def list_accounts(
    db: AsyncSession,
    current_user: User,
    *,
    page: int = 1,
    page_size: int = 20,
    tier: AccountTier | None = None,
    owner_id: UUID | None = None,
) -> list[AccountResponse]:
    offset, limit = _pagination(page, page_size)

    query = select(Account).where(
        Account.is_active.is_(True),
        account_visibility_filter(current_user),
    )

    if tier:
        query = query.where(Account.tier == tier)

    if owner_id:
        query = query.where(Account.owner_id == owner_id)

    query = query.order_by(Account.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)

    return [await build_account_response(db, account) for account in result.scalars().all()]


async def get_account_model(
    db: AsyncSession,
    account_id: UUID,
    current_user: User,
) -> Account:
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.is_active.is_(True),
            account_visibility_filter(current_user),
        )
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise _account_not_found()

    return account


async def get_account(
    db: AsyncSession,
    account_id: UUID,
    current_user: User,
) -> AccountResponse:
    account = await get_account_model(db, account_id, current_user)
    return await build_account_response(db, account)


async def create_account(
    db: AsyncSession,
    account_in: AccountCreate,
    current_user: User,
) -> AccountResponse:
    account_data = account_in.model_dump()
    account_data["owner_id"] = account_data.get("owner_id") or current_user.id

    if _is_sales_rep(current_user) and account_data["owner_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales reps can only assign accounts to themselves",
        )

    account = Account(**account_data)
    db.add(account)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account could not be created",
        ) from exc

    await db.refresh(account)
    response = await build_account_response(db, account)
    await search_service.sync_account_to_search(response)
    return response


async def update_account(
    db: AsyncSession,
    account_id: UUID,
    account_in: AccountUpdate,
    current_user: User,
) -> AccountResponse:
    account = await get_account_model(db, account_id, current_user)
    update_data = account_in.model_dump(exclude_unset=True)

    if _is_sales_rep(current_user) and update_data.get("owner_id") not in {None, current_user.id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales reps can only assign accounts to themselves",
        )

    for field_name, value in update_data.items():
        if field_name in {"name", "industry", "size", "website", "tier", "owner_id"} and value is None:
            continue
        setattr(account, field_name, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account update conflicts with existing data",
        ) from exc

    await db.refresh(account)
    response = await build_account_response(db, account)
    await search_service.sync_account_to_search(response)
    return response


async def soft_delete_account(
    db: AsyncSession,
    account_id: UUID,
    current_user: User,
) -> None:
    account = await get_account_model(db, account_id, current_user)
    account.is_active = False
    await db.commit()
    await search_service.delete_account_from_search(str(account_id))


async def list_account_contacts(
    db: AsyncSession,
    account_id: UUID,
    current_user: User,
    *,
    page: int = 1,
    page_size: int = 20,
):
    await get_account_model(db, account_id, current_user)
    offset, limit = _pagination(page, page_size)

    result = await db.execute(
        select(Contact)
        .where(
            Contact.account_id == account_id,
            Contact.is_active.is_(True),
            contact_visibility_filter(current_user),
        )
        .order_by(Contact.last_name.asc(), Contact.first_name.asc())
        .offset(offset)
        .limit(limit)
    )

    return [await build_contact_response(db, contact) for contact in result.scalars().all()]


async def list_account_deals(
    db: AsyncSession,
    account_id: UUID,
    current_user: User,
    *,
    page: int = 1,
    page_size: int = 20,
) -> list[AccountDealResponse]:
    await get_account_model(db, account_id, current_user)
    offset, limit = _pagination(page, page_size)

    result = await db.execute(
        select(Deal)
        .where(Deal.account_id == account_id)
        .order_by(Deal.expected_close.desc(), Deal.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return [AccountDealResponse.model_validate(deal) for deal in result.scalars().all()]
