from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRoleName(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    sales_rep = "sales_rep"
    marketing = "marketing"
    customer_success = "customer_success"
    support = "support"
    viewer = "viewer"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRoleName] = mapped_column(
        SQLEnum(UserRoleName, name="user_role"),
        nullable=False,
        default=UserRoleName.sales_rep,
        server_default=UserRoleName.sales_rep.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    role_assignments: Mapped[list[UserRole]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[UserRoleName] = mapped_column(
        SQLEnum(UserRoleName, name="user_role"),
        nullable=False,
        unique=True,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user_roles: Mapped[list[UserRole]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_id_role_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped[User] = relationship("User", back_populates="role_assignments")
    role: Mapped[Role] = relationship("Role", back_populates="user_roles")
