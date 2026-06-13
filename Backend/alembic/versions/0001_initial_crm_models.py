"""initial CRM models

Revision ID: 0001_initial_crm_models
Revises:
Create Date: 2026-06-13 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_crm_models"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM(
    "admin",
    "manager",
    "sales_rep",
    "marketing",
    "customer_success",
    "support",
    "viewer",
    name="user_role",
    create_type=False,
)
campaign_type = postgresql.ENUM(
    "email",
    "event",
    "social",
    "cold_call",
    name="campaign_type",
    create_type=False,
)
campaign_status = postgresql.ENUM(
    "draft",
    "active",
    "paused",
    "completed",
    name="campaign_status",
    create_type=False,
)
campaign_enrollment_status = postgresql.ENUM(
    "active",
    "completed",
    "unsubscribed",
    name="campaign_enrollment_status",
    create_type=False,
)
campaign_sequence_channel = postgresql.ENUM(
    "email",
    "call",
    "task",
    "social",
    name="campaign_sequence_channel",
    create_type=False,
)
lead_source = postgresql.ENUM(
    "website",
    "referral",
    "social",
    "cold_outreach",
    "event",
    "campaign",
    name="lead_source",
    create_type=False,
)
lead_status = postgresql.ENUM(
    "new",
    "contacted",
    "qualified",
    "disqualified",
    "converted",
    name="lead_status",
    create_type=False,
)
account_tier = postgresql.ENUM(
    "enterprise",
    "smb",
    "startup",
    name="account_tier",
    create_type=False,
)
custom_field_entity_type = postgresql.ENUM(
    "lead",
    "contact",
    "account",
    "deal",
    "project",
    name="custom_field_entity_type",
    create_type=False,
)
custom_field_type = postgresql.ENUM(
    "text",
    "number",
    "date",
    "boolean",
    "select",
    "json",
    name="custom_field_type",
    create_type=False,
)
deal_status = postgresql.ENUM(
    "open",
    "won",
    "lost",
    name="deal_status",
    create_type=False,
)
activity_type = postgresql.ENUM(
    "call",
    "email",
    "meeting",
    "note",
    "task",
    name="activity_type",
    create_type=False,
)
task_status = postgresql.ENUM(
    "pending",
    "in_progress",
    "completed",
    "cancelled",
    name="task_status",
    create_type=False,
)
task_priority = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "urgent",
    name="task_priority",
    create_type=False,
)
project_health = postgresql.ENUM(
    "green",
    "yellow",
    "red",
    name="project_health",
    create_type=False,
)

ENUMS = (
    user_role,
    campaign_type,
    campaign_status,
    campaign_enrollment_status,
    campaign_sequence_channel,
    lead_source,
    lead_status,
    account_tier,
    custom_field_entity_type,
    custom_field_type,
    deal_status,
    activity_type,
    task_status,
    task_priority,
    project_health,
)


def uuid_pk_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    for enum_type in ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        uuid_pk_column(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, server_default="sales_rep", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "roles",
        uuid_pk_column(),
        sa.Column("name", user_role, nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("name", name=op.f("uq_roles_name")),
    )

    op.create_table(
        "user_roles",
        uuid_pk_column(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_user_roles_role_id_roles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_roles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_roles")),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_id_role_id"),
    )
    op.create_index(op.f("ix_user_roles_role_id"), "user_roles", ["role_id"], unique=False)
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=False)

    op.create_table(
        "campaigns",
        uuid_pk_column(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", campaign_type, nullable=False),
        sa.Column("status", campaign_status, server_default="draft", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "target_segment",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("budget", sa.Numeric(14, 2), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_campaigns_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaigns")),
    )
    op.create_index(op.f("ix_campaigns_owner_id"), "campaigns", ["owner_id"], unique=False)

    op.create_table(
        "accounts",
        uuid_pk_column(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=120), nullable=False),
        sa.Column("size", sa.String(length=120), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=False),
        sa.Column(
            "address",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("tier", account_tier, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_accounts_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
    )
    op.create_index(op.f("ix_accounts_owner_id"), "accounts", ["owner_id"], unique=False)

    op.create_table(
        "contacts",
        uuid_pk_column(),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=64)),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
        sa.Column(
            "custom_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_contacts_account_id_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_contacts_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contacts")),
    )
    op.create_index(op.f("ix_contacts_account_id"), "contacts", ["account_id"], unique=False)
    op.create_index(op.f("ix_contacts_owner_id"), "contacts", ["owner_id"], unique=False)

    op.create_table(
        "contact_tags",
        uuid_pk_column(),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contact_tags")),
        sa.UniqueConstraint("name", name=op.f("uq_contact_tags_name")),
    )

    op.create_table(
        "custom_fields",
        uuid_pk_column(),
        sa.Column("entity_type", custom_field_entity_type, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("field_type", custom_field_type, nullable=False),
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_custom_fields")),
        sa.UniqueConstraint("entity_type", "name", name="uq_custom_fields_entity_type_name"),
    )

    op.create_table(
        "leads",
        uuid_pk_column(),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("source", lead_source, nullable=False),
        sa.Column("score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", lead_status, server_default="new", nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["assigned_to"],
            ["users.id"],
            name=op.f("fk_leads_assigned_to_users"),
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_leads_campaign_id_campaigns"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leads")),
    )
    op.create_index(op.f("ix_leads_assigned_to"), "leads", ["assigned_to"], unique=False)
    op.create_index(op.f("ix_leads_campaign_id"), "leads", ["campaign_id"], unique=False)

    op.create_table(
        "pipelines",
        uuid_pk_column(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipelines")),
    )

    op.create_table(
        "pipeline_stages",
        uuid_pk_column(),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["pipelines.id"],
            name=op.f("fk_pipeline_stages_pipeline_id_pipelines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_stages")),
        sa.UniqueConstraint(
            "pipeline_id",
            "order_index",
            name="uq_pipeline_stages_pipeline_id_order_index",
        ),
    )
    op.create_index(
        op.f("ix_pipeline_stages_pipeline_id"),
        "pipeline_stages",
        ["pipeline_id"],
        unique=False,
    )

    op.create_table(
        "deals",
        uuid_pk_column(),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("expected_close", sa.Date(), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", deal_status, server_default="open", nullable=False),
        sa.Column("lost_reason", sa.String(length=500), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_deals_account_id_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name=op.f("fk_deals_contact_id_contacts"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_deals_owner_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["pipelines.id"],
            name=op.f("fk_deals_pipeline_id_pipelines"),
        ),
        sa.ForeignKeyConstraint(
            ["stage_id"],
            ["pipeline_stages.id"],
            name=op.f("fk_deals_stage_id_pipeline_stages"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deals")),
    )
    op.create_index(op.f("ix_deals_account_id"), "deals", ["account_id"], unique=False)
    op.create_index(op.f("ix_deals_contact_id"), "deals", ["contact_id"], unique=False)
    op.create_index(op.f("ix_deals_owner_id"), "deals", ["owner_id"], unique=False)
    op.create_index(op.f("ix_deals_pipeline_id"), "deals", ["pipeline_id"], unique=False)
    op.create_index(op.f("ix_deals_stage_id"), "deals", ["stage_id"], unique=False)

    op.create_table(
        "deal_collaborators",
        uuid_pk_column(),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=80), server_default="collaborator", nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name=op.f("fk_deal_collaborators_deal_id_deals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_deal_collaborators_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deal_collaborators")),
        sa.UniqueConstraint("deal_id", "user_id", name="uq_deal_collaborators_deal_id_user_id"),
    )
    op.create_index(
        op.f("ix_deal_collaborators_deal_id"),
        "deal_collaborators",
        ["deal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deal_collaborators_user_id"),
        "deal_collaborators",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "activities",
        uuid_pk_column(),
        sa.Column("type", activity_type, nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(length=255), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_activities_account_id_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name=op.f("fk_activities_contact_id_contacts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name=op.f("fk_activities_deal_id_deals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            name=op.f("fk_activities_lead_id_leads"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_activities_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activities")),
    )
    op.create_index(op.f("ix_activities_account_id"), "activities", ["account_id"], unique=False)
    op.create_index(op.f("ix_activities_contact_id"), "activities", ["contact_id"], unique=False)
    op.create_index(op.f("ix_activities_deal_id"), "activities", ["deal_id"], unique=False)
    op.create_index(op.f("ix_activities_lead_id"), "activities", ["lead_id"], unique=False)
    op.create_index(op.f("ix_activities_owner_id"), "activities", ["owner_id"], unique=False)

    op.create_table(
        "tasks",
        uuid_pk_column(),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status, server_default="pending", nullable=False),
        sa.Column("priority", task_priority, server_default="medium", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_tasks_account_id_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name=op.f("fk_tasks_activity_id_activities"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name=op.f("fk_tasks_contact_id_contacts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name=op.f("fk_tasks_deal_id_deals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            name=op.f("fk_tasks_lead_id_leads"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_tasks_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )
    op.create_index(op.f("ix_tasks_account_id"), "tasks", ["account_id"], unique=False)
    op.create_index(op.f("ix_tasks_activity_id"), "tasks", ["activity_id"], unique=False)
    op.create_index(op.f("ix_tasks_contact_id"), "tasks", ["contact_id"], unique=False)
    op.create_index(op.f("ix_tasks_deal_id"), "tasks", ["deal_id"], unique=False)
    op.create_index(op.f("ix_tasks_lead_id"), "tasks", ["lead_id"], unique=False)
    op.create_index(op.f("ix_tasks_owner_id"), "tasks", ["owner_id"], unique=False)

    op.create_table(
        "campaign_enrollments",
        uuid_pk_column(),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("step_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", campaign_enrollment_status, server_default="active", nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_campaign_enrollments_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name=op.f("fk_campaign_enrollments_contact_id_contacts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_enrollments")),
        sa.UniqueConstraint(
            "campaign_id",
            "contact_id",
            name="uq_campaign_enrollments_campaign_id_contact_id",
        ),
    )
    op.create_index(
        op.f("ix_campaign_enrollments_campaign_id"),
        "campaign_enrollments",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_campaign_enrollments_contact_id"),
        "campaign_enrollments",
        ["contact_id"],
        unique=False,
    )

    op.create_table(
        "campaign_sequence_steps",
        uuid_pk_column(),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("channel", campaign_sequence_channel, nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("delay_days", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_campaign_sequence_steps_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_sequence_steps")),
        sa.UniqueConstraint(
            "campaign_id",
            "step_index",
            name="uq_campaign_sequence_steps_campaign_id_step_index",
        ),
    )
    op.create_index(
        op.f("ix_campaign_sequence_steps_campaign_id"),
        "campaign_sequence_steps",
        ["campaign_id"],
        unique=False,
    )

    op.create_table(
        "projects",
        uuid_pk_column(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("health", project_health, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portal_token", sa.String(length=128), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_projects_account_id_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name=op.f("fk_projects_deal_id_deals"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_projects_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("portal_token", name=op.f("uq_projects_portal_token")),
    )
    op.create_index(op.f("ix_projects_account_id"), "projects", ["account_id"], unique=False)
    op.create_index(op.f("ix_projects_deal_id"), "projects", ["deal_id"], unique=False)
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)

    op.create_table(
        "milestones",
        uuid_pk_column(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_milestones_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_milestones")),
    )
    op.create_index(op.f("ix_milestones_project_id"), "milestones", ["project_id"], unique=False)

    op.create_table(
        "project_documents",
        uuid_pk_column(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=1000), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_documents_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            name=op.f("fk_project_documents_uploaded_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_documents")),
    )
    op.create_index(
        op.f("ix_project_documents_project_id"),
        "project_documents",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_documents_uploaded_by"),
        "project_documents",
        ["uploaded_by"],
        unique=False,
    )

    op.create_table(
        "report_snapshots",
        uuid_pk_column(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("report_type", sa.String(length=120), nullable=False),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["generated_by"],
            ["users.id"],
            name=op.f("fk_report_snapshots_generated_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_snapshots")),
    )
    op.create_index(
        op.f("ix_report_snapshots_generated_by"),
        "report_snapshots",
        ["generated_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("report_snapshots")
    op.drop_table("project_documents")
    op.drop_table("milestones")
    op.drop_table("projects")
    op.drop_table("campaign_sequence_steps")
    op.drop_table("campaign_enrollments")
    op.drop_table("tasks")
    op.drop_table("activities")
    op.drop_table("deal_collaborators")
    op.drop_table("deals")
    op.drop_table("pipeline_stages")
    op.drop_table("pipelines")
    op.drop_table("leads")
    op.drop_table("custom_fields")
    op.drop_table("contact_tags")
    op.drop_table("contacts")
    op.drop_table("accounts")
    op.drop_table("campaigns")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in reversed(ENUMS):
        enum_type.drop(bind, checkfirst=True)
