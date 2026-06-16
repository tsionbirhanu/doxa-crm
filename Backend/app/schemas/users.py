from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import UserRoleName


class NameAliasMixin(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def accept_name_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "name" in data and "full_name" not in data:
            return {**data, "full_name": data["name"]}
        return data


class UserCreate(NameAliasMixin):
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRoleName = UserRoleName.sales_rep
    is_active: bool = True


class UserUpdate(NameAliasMixin):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRoleName | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRoleName
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
