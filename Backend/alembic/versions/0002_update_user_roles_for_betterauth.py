"""update user roles for BetterAuth RBAC

Revision ID: 0002_roles
Revises: 0001_initial_crm_models
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_roles"
down_revision: Union[str, Sequence[str], None] = "0001_initial_crm_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_ROLES = (
    "super_admin",
    "sales_manager",
    "sales_rep",
    "marketing_manager",
    "marketing_rep",
    "customer_success",
    "read_only",
)

OLD_ROLES = (
    "admin",
    "manager",
    "sales_rep",
    "marketing",
    "customer_success",
    "support",
    "viewer",
)

OLD_TO_NEW = {
    "admin": "super_admin",
    "manager": "sales_manager",
    "sales_rep": "sales_rep",
    "marketing": "marketing_manager",
    "customer_success": "customer_success",
    "support": "customer_success",
    "viewer": "read_only",
}

NEW_TO_OLD = {
    "super_admin": "admin",
    "sales_manager": "manager",
    "sales_rep": "sales_rep",
    "marketing_manager": "marketing",
    "marketing_rep": "marketing",
    "customer_success": "customer_success",
    "read_only": "viewer",
}

ROLE_COLUMN = '"role"'


def _enum_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _case_cast(column_name: str, mapping: dict[str, str], enum_name: str) -> str:
    cases = " ".join(
        f"WHEN '{old_value}' THEN '{new_value}'"
        for old_value, new_value in mapping.items()
    )
    return f"(CASE {column_name}::text {cases} ELSE {column_name}::text END)::{enum_name}"


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute(f"CREATE TYPE user_role AS ENUM ({_enum_values(NEW_ROLES)})")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role "
        f"USING {_case_cast(ROLE_COLUMN, OLD_TO_NEW, 'user_role')}"
    )
    op.execute(
        "ALTER TABLE roles ALTER COLUMN name TYPE user_role "
        f"USING {_case_cast('name', OLD_TO_NEW, 'user_role')}"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'sales_rep'")
    op.execute("DROP TYPE user_role_old")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TYPE user_role RENAME TO user_role_new")
    op.execute(f"CREATE TYPE user_role AS ENUM ({_enum_values(OLD_ROLES)})")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role "
        f"USING {_case_cast(ROLE_COLUMN, NEW_TO_OLD, 'user_role')}"
    )
    op.execute(
        "ALTER TABLE roles ALTER COLUMN name TYPE user_role "
        f"USING {_case_cast('name', NEW_TO_OLD, 'user_role')}"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'sales_rep'")
    op.execute("DROP TYPE user_role_new")
