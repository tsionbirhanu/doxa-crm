from __future__ import annotations

import asyncio
import calendar
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import AsyncSessionLocal, close_database_connections
from app.models import (
    Account,
    AccountTier,
    Activity,
    ActivityType,
    AuditLog,
    Campaign,
    CampaignEnrollment,
    CampaignEnrollmentStatus,
    CampaignMetric,
    CampaignMetricEventType,
    CampaignSequenceChannel,
    CampaignSequenceStep,
    CampaignStatus,
    CampaignType,
    Contact,
    ContactTag,
    CustomField,
    CustomFieldEntityType,
    CustomFieldType,
    Deal,
    DealCollaborator,
    DealStageHistory,
    DealStatus,
    Lead,
    LeadSource,
    LeadStatus,
    Milestone,
    Pipeline,
    PipelineStage,
    Project,
    ProjectDocument,
    ProjectHealth,
    ReportSnapshot,
    Role,
    SalesQuota,
    Task,
    TaskLog,
    TaskPriority,
    TaskStatus,
    User,
    UserRole,
    UserRoleName,
    WebhookLog,
    WebhookSubscription,
)

ModelT = TypeVar("ModelT")


@dataclass
class SeedStats:
    created: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)

    def add_created(self, name: str) -> None:
        self.created[name] = self.created.get(name, 0) + 1

    def add_updated(self, name: str) -> None:
        self.updated[name] = self.updated.get(name, 0) + 1


DEFAULT_PIPELINE_STAGES = (
    ("Prospecting", 10.0),
    ("Qualification", 25.0),
    ("Proposal Sent", 50.0),
    ("Negotiation", 75.0),
    ("Closed Won", 100.0),
    ("Closed Lost", 0.0),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_datetime(day: date, hour: int = 9) -> datetime:
    return datetime.combine(day, time(hour=hour), tzinfo=timezone.utc)


def month_window(day: date) -> tuple[date, date]:
    start = day.replace(day=1)
    end = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    return start, end


async def one_or_none(db: AsyncSession, statement: Select[tuple[ModelT]]) -> ModelT | None:
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def upsert_one(
    db: AsyncSession,
    stats: SeedStats,
    model_name: str,
    statement: Select[tuple[ModelT]],
    create_kwargs: dict[str, Any],
    update_kwargs: dict[str, Any] | None = None,
) -> ModelT:
    existing = await one_or_none(db, statement)
    if existing is None:
        model_type = statement.column_descriptions[0]["type"]
        created = model_type(**create_kwargs)
        db.add(created)
        await db.flush()
        stats.add_created(model_name)
        return created

    for key, value in (update_kwargs or {}).items():
        setattr(existing, key, value)
    if update_kwargs:
        stats.add_updated(model_name)
    return existing


async def seed_roles_and_users(db: AsyncSession, stats: SeedStats) -> dict[str, User]:
    roles: dict[UserRoleName, Role] = {}
    for role_name in UserRoleName:
        role = await upsert_one(
            db,
            stats,
            "roles",
            select(Role).where(Role.name == role_name),
            {
                "name": role_name,
                "description": role_name.value.replace("_", " ").title(),
            },
            {"description": role_name.value.replace("_", " ").title()},
        )
        roles[role_name] = role

    users_data = (
        ("admin", "admin@doxa.local", "Amina Reed", UserRoleName.super_admin),
        ("sales_manager", "sales.manager@doxa.local", "Priya Shah", UserRoleName.sales_manager),
        ("sales_rep_alex", "alex.rep@doxa.local", "Alex Morgan", UserRoleName.sales_rep),
        ("sales_rep_maya", "maya.rep@doxa.local", "Maya Chen", UserRoleName.sales_rep),
        ("marketing_manager", "marketing.manager@doxa.local", "Noah Reed", UserRoleName.marketing_manager),
        ("marketing_rep", "marketing.rep@doxa.local", "Zoe Park", UserRoleName.marketing_rep),
        ("customer_success", "success@doxa.local", "Lina Gomez", UserRoleName.customer_success),
        ("read_only", "readonly@doxa.local", "Omar Ali", UserRoleName.read_only),
    )

    users: dict[str, User] = {}
    for key, email, full_name, role_name in users_data:
        user = await upsert_one(
            db,
            stats,
            "users",
            select(User).where(User.email == email),
            {
                "email": email,
                "full_name": full_name,
                "role": role_name,
                "is_active": True,
            },
            {
                "full_name": full_name,
                "role": role_name,
                "is_active": True,
            },
        )
        users[key] = user

        role = roles[role_name]
        await upsert_one(
            db,
            stats,
            "user_roles",
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id),
            {"user_id": user.id, "role_id": role.id},
        )

    return users


async def seed_foundation(db: AsyncSession, stats: SeedStats, users: dict[str, User]) -> tuple[dict[str, Account], dict[str, Contact]]:
    for tag_name, color, description in (
        ("vip", "#2563EB", "High-value customer or prospect"),
        ("decision-maker", "#16A34A", "Executive buyer or signer"),
        ("technical", "#9333EA", "Technical evaluator"),
        ("renewal", "#F59E0B", "Renewal or expansion conversation"),
    ):
        await upsert_one(
            db,
            stats,
            "contact_tags",
            select(ContactTag).where(ContactTag.name == tag_name),
            {"name": tag_name, "color": color, "description": description},
            {"color": color, "description": description},
        )

    custom_fields = (
        (CustomFieldEntityType.contact, "preferred_channel", "Preferred Channel", CustomFieldType.text, {}),
        (CustomFieldEntityType.contact, "lifecycle_score", "Lifecycle Score", CustomFieldType.number, {}),
        (CustomFieldEntityType.account, "renewal_month", "Renewal Month", CustomFieldType.text, {}),
        (CustomFieldEntityType.account, "strategic_account", "Strategic Account", CustomFieldType.boolean, {}),
        (CustomFieldEntityType.deal, "procurement_risk", "Procurement Risk", CustomFieldType.select, {"options": ["low", "medium", "high"]}),
        (CustomFieldEntityType.project, "implementation_tier", "Implementation Tier", CustomFieldType.select, {"options": ["standard", "premium"]}),
    )

    for entity_type, name, label, field_type, options in custom_fields:
        await upsert_one(
            db,
            stats,
            "custom_fields",
            select(CustomField).where(CustomField.entity_type == entity_type, CustomField.name == name),
            {
                "entity_type": entity_type,
                "name": name,
                "label": label,
                "field_type": field_type,
                "options": options,
                "is_required": False,
            },
            {"label": label, "field_type": field_type, "options": options, "is_required": False},
        )

    accounts_data = (
        (
            "acme",
            {
                "name": "Acme Robotics",
                "industry": "Manufacturing",
                "size": "1,001-5,000",
                "website": "https://acme-robotics.example",
                "address": {"city": "Austin", "state": "TX", "country": "US"},
                "tier": AccountTier.enterprise,
                "owner_id": users["sales_manager"].id,
                "custom_fields": {"renewal_month": "November", "strategic_account": True},
                "is_active": True,
            },
        ),
        (
            "brightpath",
            {
                "name": "BrightPath SaaS",
                "industry": "Software",
                "size": "201-500",
                "website": "https://brightpath.example",
                "address": {"city": "Seattle", "state": "WA", "country": "US"},
                "tier": AccountTier.smb,
                "owner_id": users["sales_rep_alex"].id,
                "custom_fields": {"renewal_month": "August", "strategic_account": False},
                "is_active": True,
            },
        ),
        (
            "nova",
            {
                "name": "Nova Health",
                "industry": "Healthcare",
                "size": "51-200",
                "website": "https://nova-health.example",
                "address": {"city": "Denver", "state": "CO", "country": "US"},
                "tier": AccountTier.startup,
                "owner_id": users["sales_rep_maya"].id,
                "custom_fields": {"renewal_month": "January", "strategic_account": False},
                "is_active": True,
            },
        ),
        (
            "greenfield",
            {
                "name": "GreenField Energy",
                "industry": "Energy",
                "size": "501-1,000",
                "website": "https://greenfield-energy.example",
                "address": {"city": "Phoenix", "state": "AZ", "country": "US"},
                "tier": AccountTier.enterprise,
                "owner_id": users["sales_manager"].id,
                "custom_fields": {"renewal_month": "June", "strategic_account": True},
                "is_active": True,
            },
        ),
    )

    accounts: dict[str, Account] = {}
    for key, payload in accounts_data:
        account = await upsert_one(
            db,
            stats,
            "accounts",
            select(Account).where(Account.name == payload["name"]),
            payload,
            payload,
        )
        accounts[key] = account

    contacts_data = (
        (
            "ava",
            {
                "first_name": "Ava",
                "last_name": "Stone",
                "email": "ava.stone@acme-robotics.example",
                "phone": "+1-555-0101",
                "title": "VP Operations",
                "account_id": accounts["acme"].id,
                "owner_id": users["sales_rep_alex"].id,
                "tags": ["vip", "decision-maker"],
                "custom_fields": {"preferred_channel": "email", "lifecycle_score": 92},
                "is_active": True,
            },
        ),
        (
            "ben",
            {
                "first_name": "Ben",
                "last_name": "Carter",
                "email": "ben.carter@acme-robotics.example",
                "phone": "+1-555-0102",
                "title": "Director of IT",
                "account_id": accounts["acme"].id,
                "owner_id": users["sales_rep_alex"].id,
                "tags": ["technical"],
                "custom_fields": {"preferred_channel": "meeting", "lifecycle_score": 81},
                "is_active": True,
            },
        ),
        (
            "clara",
            {
                "first_name": "Clara",
                "last_name": "Nguyen",
                "email": "clara.nguyen@brightpath.example",
                "phone": "+1-555-0103",
                "title": "CEO",
                "account_id": accounts["brightpath"].id,
                "owner_id": users["sales_rep_alex"].id,
                "tags": ["decision-maker"],
                "custom_fields": {"preferred_channel": "phone", "lifecycle_score": 77},
                "is_active": True,
            },
        ),
        (
            "dev",
            {
                "first_name": "Dev",
                "last_name": "Patel",
                "email": "dev.patel@nova-health.example",
                "phone": "+1-555-0104",
                "title": "COO",
                "account_id": accounts["nova"].id,
                "owner_id": users["sales_rep_maya"].id,
                "tags": ["vip"],
                "custom_fields": {"preferred_channel": "email", "lifecycle_score": 88},
                "is_active": True,
            },
        ),
        (
            "emma",
            {
                "first_name": "Emma",
                "last_name": "Brooks",
                "email": "emma.brooks@greenfield-energy.example",
                "phone": "+1-555-0105",
                "title": "Head of Revenue",
                "account_id": accounts["greenfield"].id,
                "owner_id": users["sales_manager"].id,
                "tags": ["renewal", "decision-maker"],
                "custom_fields": {"preferred_channel": "email", "lifecycle_score": 84},
                "is_active": True,
            },
        ),
    )

    contacts: dict[str, Contact] = {}
    for key, payload in contacts_data:
        contact = await upsert_one(
            db,
            stats,
            "contacts",
            select(Contact).where(Contact.email == payload["email"]),
            payload,
            payload,
        )
        contacts[key] = contact

    return accounts, contacts


async def seed_pipelines(db: AsyncSession, stats: SeedStats) -> tuple[Pipeline, dict[str, PipelineStage]]:
    pipeline = await upsert_one(
        db,
        stats,
        "pipelines",
        select(Pipeline).where(Pipeline.name == "New Business"),
        {"name": "New Business", "is_default": True},
        {"is_default": True},
    )

    stages: dict[str, PipelineStage] = {}
    for index, (name, probability) in enumerate(DEFAULT_PIPELINE_STAGES):
        stage = await upsert_one(
            db,
            stats,
            "pipeline_stages",
            select(PipelineStage).where(PipelineStage.pipeline_id == pipeline.id, PipelineStage.order_index == index),
            {
                "pipeline_id": pipeline.id,
                "name": name,
                "probability": probability,
                "order_index": index,
            },
            {"name": name, "probability": probability},
        )
        stages[name] = stage

    return pipeline, stages


async def seed_campaigns(
    db: AsyncSession,
    stats: SeedStats,
    users: dict[str, User],
    contacts: dict[str, Contact],
) -> dict[str, Campaign]:
    today = date.today()
    campaigns_data = (
        (
            "product_launch",
            {
                "name": "Q3 Product Launch Nurture",
                "type": CampaignType.email,
                "status": CampaignStatus.active,
                "start_date": today - timedelta(days=10),
                "end_date": today + timedelta(days=35),
                "target_segment": {"tier": ["enterprise", "smb"], "persona": "operations"},
                "budget": Decimal("18000.00"),
                "owner_id": users["marketing_manager"].id,
            },
        ),
        (
            "renewal_readiness",
            {
                "name": "Renewal Readiness Outreach",
                "type": CampaignType.email,
                "status": CampaignStatus.draft,
                "start_date": today + timedelta(days=7),
                "end_date": today + timedelta(days=60),
                "target_segment": {"tag": "renewal"},
                "budget": Decimal("7500.00"),
                "owner_id": users["marketing_rep"].id,
            },
        ),
    )

    campaigns: dict[str, Campaign] = {}
    for key, payload in campaigns_data:
        campaign = await upsert_one(
            db,
            stats,
            "campaigns",
            select(Campaign).where(Campaign.name == payload["name"]),
            payload,
            payload,
        )
        campaigns[key] = campaign

    launch_steps = (
        (0, CampaignSequenceChannel.email, "See what Doxa CRM can automate this quarter", "Hi {{first_name}}, here are three CRM workflows we can automate for your team.", 0, "A"),
        (1, CampaignSequenceChannel.email, "A quick workflow audit for your team", "Want us to map your current lead-to-close process?", 3, "A"),
        (2, CampaignSequenceChannel.task, "Call warm launch responders", "Call contacts who opened or clicked the first two launch emails.", 5, None),
    )
    for step_index, channel, subject, body, delay_days, variant in launch_steps:
        await upsert_one(
            db,
            stats,
            "campaign_sequence_steps",
            select(CampaignSequenceStep).where(
                CampaignSequenceStep.campaign_id == campaigns["product_launch"].id,
                CampaignSequenceStep.step_index == step_index,
            ),
            {
                "campaign_id": campaigns["product_launch"].id,
                "step_index": step_index,
                "channel": channel,
                "subject": subject,
                "body": body,
                "delay_days": delay_days,
                "variant": variant,
            },
            {"channel": channel, "subject": subject, "body": body, "delay_days": delay_days, "variant": variant},
        )

    renewal_steps = (
        (0, CampaignSequenceChannel.email, "Planning ahead for your renewal", "Let's review usage, goals, and support needs before renewal season.", 0, None),
        (1, CampaignSequenceChannel.call, "Schedule renewal planning call", "Book a planning call with the account owner.", 2, None),
    )
    for step_index, channel, subject, body, delay_days, variant in renewal_steps:
        await upsert_one(
            db,
            stats,
            "campaign_sequence_steps",
            select(CampaignSequenceStep).where(
                CampaignSequenceStep.campaign_id == campaigns["renewal_readiness"].id,
                CampaignSequenceStep.step_index == step_index,
            ),
            {
                "campaign_id": campaigns["renewal_readiness"].id,
                "step_index": step_index,
                "channel": channel,
                "subject": subject,
                "body": body,
                "delay_days": delay_days,
                "variant": variant,
            },
            {"channel": channel, "subject": subject, "body": body, "delay_days": delay_days, "variant": variant},
        )

    for contact in (contacts["ava"], contacts["clara"], contacts["dev"]):
        await upsert_one(
            db,
            stats,
            "campaign_enrollments",
            select(CampaignEnrollment).where(
                CampaignEnrollment.campaign_id == campaigns["product_launch"].id,
                CampaignEnrollment.contact_id == contact.id,
            ),
            {
                "campaign_id": campaigns["product_launch"].id,
                "contact_id": contact.id,
                "step_index": 1,
                "status": CampaignEnrollmentStatus.active,
            },
            {"step_index": 1, "status": CampaignEnrollmentStatus.active},
        )

    first_step = await one_or_none(
        db,
        select(CampaignSequenceStep).where(
            CampaignSequenceStep.campaign_id == campaigns["product_launch"].id,
            CampaignSequenceStep.step_index == 0,
        ),
    )
    if first_step is not None:
        metric_events = (
            (contacts["ava"], CampaignMetricEventType.sent),
            (contacts["ava"], CampaignMetricEventType.opened),
            (contacts["ava"], CampaignMetricEventType.clicked),
            (contacts["clara"], CampaignMetricEventType.sent),
            (contacts["clara"], CampaignMetricEventType.opened),
            (contacts["dev"], CampaignMetricEventType.sent),
        )
        for contact, event_type in metric_events:
            await upsert_one(
                db,
                stats,
                "campaign_metrics",
                select(CampaignMetric).where(
                    CampaignMetric.campaign_id == campaigns["product_launch"].id,
                    CampaignMetric.contact_id == contact.id,
                    CampaignMetric.step_id == first_step.id,
                    CampaignMetric.event_type == event_type,
                ),
                {
                    "campaign_id": campaigns["product_launch"].id,
                    "contact_id": contact.id,
                    "step_id": first_step.id,
                    "event_type": event_type,
                },
            )

    return campaigns


async def seed_leads(
    db: AsyncSession,
    stats: SeedStats,
    users: dict[str, User],
    campaigns: dict[str, Campaign],
) -> dict[str, Lead]:
    leads_data = (
        (
            "olivia",
            {
                "full_name": "Olivia Fox",
                "email": "olivia.fox@northstar.example",
                "phone": "+1-555-0201",
                "company": "Northstar Logistics",
                "source": LeadSource.website,
                "score": 72,
                "status": LeadStatus.qualified,
                "assigned_to": users["sales_rep_alex"].id,
                "campaign_id": campaigns["product_launch"].id,
                "utm_source": "linkedin",
                "utm_campaign": "q3-product-launch",
                "utm_medium": "paid-social",
                "converted_at": None,
                "is_active": True,
            },
        ),
        (
            "peter",
            {
                "full_name": "Peter Lang",
                "email": "peter.lang@blueharbor.example",
                "phone": "+1-555-0202",
                "company": "Blue Harbor Finance",
                "source": LeadSource.referral,
                "score": 84,
                "status": LeadStatus.contacted,
                "assigned_to": users["sales_rep_maya"].id,
                "campaign_id": None,
                "utm_source": None,
                "utm_campaign": None,
                "utm_medium": None,
                "converted_at": None,
                "is_active": True,
            },
        ),
        (
            "quinn",
            {
                "full_name": "Quinn Rivera",
                "email": "quinn.rivera@gmail.com",
                "phone": "+1-555-0203",
                "company": "Independent Consultant",
                "source": LeadSource.social,
                "score": 31,
                "status": LeadStatus.new,
                "assigned_to": users["sales_rep_alex"].id,
                "campaign_id": campaigns["product_launch"].id,
                "utm_source": "x",
                "utm_campaign": "q3-product-launch",
                "utm_medium": "organic-social",
                "converted_at": None,
                "is_active": True,
            },
        ),
        (
            "riley",
            {
                "full_name": "Riley Adams",
                "email": "riley.adams@matrixlabs.example",
                "phone": "+1-555-0204",
                "company": "Matrix Labs",
                "source": LeadSource.event,
                "score": 64,
                "status": LeadStatus.disqualified,
                "assigned_to": users["sales_rep_maya"].id,
                "campaign_id": None,
                "utm_source": "conference",
                "utm_campaign": "saas-summit",
                "utm_medium": "event",
                "converted_at": None,
                "is_active": True,
            },
        ),
        (
            "sam",
            {
                "full_name": "Sam Novak",
                "email": "sam.novak@pilotworks.example",
                "phone": "+1-555-0205",
                "company": "PilotWorks",
                "source": LeadSource.cold_outreach,
                "score": 55,
                "status": LeadStatus.converted,
                "assigned_to": users["sales_rep_alex"].id,
                "campaign_id": None,
                "utm_source": None,
                "utm_campaign": None,
                "utm_medium": None,
                "converted_at": utc_now() - timedelta(days=4),
                "is_active": True,
            },
        ),
    )

    leads: dict[str, Lead] = {}
    for key, payload in leads_data:
        lead = await upsert_one(
            db,
            stats,
            "leads",
            select(Lead).where(Lead.email == payload["email"]),
            payload,
            payload,
        )
        leads[key] = lead

    return leads


async def seed_deals(
    db: AsyncSession,
    stats: SeedStats,
    users: dict[str, User],
    accounts: dict[str, Account],
    contacts: dict[str, Contact],
    pipeline: Pipeline,
    stages: dict[str, PipelineStage],
) -> dict[str, Deal]:
    today = date.today()
    deals_data = (
        (
            "acme_expansion",
            {
                "title": "Acme Robotics Expansion",
                "type": "new_business",
                "value": Decimal("125000.00"),
                "currency": "USD",
                "pipeline_id": pipeline.id,
                "stage_id": stages["Proposal Sent"].id,
                "probability": 50.0,
                "expected_close": today + timedelta(days=28),
                "contact_id": contacts["ava"].id,
                "account_id": accounts["acme"].id,
                "owner_id": users["sales_rep_alex"].id,
                "status": DealStatus.open,
                "lost_reason": None,
                "closed_at": None,
                "is_active": True,
            },
        ),
        (
            "brightpath_pilot",
            {
                "title": "BrightPath Pilot",
                "type": "new_business",
                "value": Decimal("42000.00"),
                "currency": "USD",
                "pipeline_id": pipeline.id,
                "stage_id": stages["Qualification"].id,
                "probability": 25.0,
                "expected_close": today + timedelta(days=42),
                "contact_id": contacts["clara"].id,
                "account_id": accounts["brightpath"].id,
                "owner_id": users["sales_rep_alex"].id,
                "status": DealStatus.open,
                "lost_reason": None,
                "closed_at": None,
                "is_active": True,
            },
        ),
        (
            "nova_onboarding",
            {
                "title": "Nova Health Onboarding",
                "type": "new_business",
                "value": Decimal("68000.00"),
                "currency": "USD",
                "pipeline_id": pipeline.id,
                "stage_id": stages["Closed Won"].id,
                "probability": 100.0,
                "expected_close": today - timedelta(days=5),
                "contact_id": contacts["dev"].id,
                "account_id": accounts["nova"].id,
                "owner_id": users["sales_rep_maya"].id,
                "status": DealStatus.won,
                "lost_reason": None,
                "closed_at": utc_now() - timedelta(days=5),
                "is_active": True,
            },
        ),
        (
            "greenfield_renewal",
            {
                "title": "GreenField Renewal",
                "type": "renewal",
                "value": Decimal("97000.00"),
                "currency": "USD",
                "pipeline_id": pipeline.id,
                "stage_id": stages["Negotiation"].id,
                "probability": 75.0,
                "expected_close": today + timedelta(days=18),
                "contact_id": contacts["emma"].id,
                "account_id": accounts["greenfield"].id,
                "owner_id": users["sales_manager"].id,
                "status": DealStatus.open,
                "lost_reason": None,
                "closed_at": None,
                "is_active": True,
            },
        ),
        (
            "acme_legacy",
            {
                "title": "Acme Legacy Replacement",
                "type": "new_business",
                "value": Decimal("54000.00"),
                "currency": "USD",
                "pipeline_id": pipeline.id,
                "stage_id": stages["Closed Lost"].id,
                "probability": 0.0,
                "expected_close": today - timedelta(days=12),
                "contact_id": contacts["ben"].id,
                "account_id": accounts["acme"].id,
                "owner_id": users["sales_rep_alex"].id,
                "status": DealStatus.lost,
                "lost_reason": "Customer postponed modernization budget.",
                "closed_at": utc_now() - timedelta(days=12),
                "is_active": True,
            },
        ),
    )

    deals: dict[str, Deal] = {}
    for key, payload in deals_data:
        deal = await upsert_one(
            db,
            stats,
            "deals",
            select(Deal).where(Deal.title == payload["title"]),
            payload,
            payload,
        )
        deals[key] = deal

        await upsert_one(
            db,
            stats,
            "deal_stage_history",
            select(DealStageHistory).where(
                DealStageHistory.deal_id == deal.id,
                DealStageHistory.to_stage_id == payload["stage_id"],
                DealStageHistory.note == "Seeded current stage",
            ),
            {
                "deal_id": deal.id,
                "from_stage_id": None,
                "to_stage_id": payload["stage_id"],
                "changed_by": payload["owner_id"],
                "note": "Seeded current stage",
            },
        )

    for deal_key, collaborator_key in (
        ("acme_expansion", "sales_manager"),
        ("greenfield_renewal", "customer_success"),
        ("nova_onboarding", "customer_success"),
    ):
        await upsert_one(
            db,
            stats,
            "deal_collaborators",
            select(DealCollaborator).where(
                DealCollaborator.deal_id == deals[deal_key].id,
                DealCollaborator.user_id == users[collaborator_key].id,
            ),
            {
                "deal_id": deals[deal_key].id,
                "user_id": users[collaborator_key].id,
                "role": "collaborator",
            },
            {"role": "collaborator"},
        )

    return deals


async def seed_activities_and_tasks(
    db: AsyncSession,
    stats: SeedStats,
    users: dict[str, User],
    accounts: dict[str, Account],
    contacts: dict[str, Contact],
    leads: dict[str, Lead],
    deals: dict[str, Deal],
) -> None:
    now = utc_now()
    activity_data = (
        {
            "type": ActivityType.call,
            "subject": "Discovery call with Acme operations",
            "body": "Reviewed automation goals and procurement timeline.",
            "outcome": "Next step: proposal review",
            "duration_minutes": 35,
            "lead_id": None,
            "contact_id": contacts["ava"].id,
            "deal_id": deals["acme_expansion"].id,
            "account_id": accounts["acme"].id,
            "owner_id": users["sales_rep_alex"].id,
            "scheduled_at": now - timedelta(days=8, hours=2),
            "completed_at": now - timedelta(days=8, hours=1, minutes=25),
        },
        {
            "type": ActivityType.email,
            "subject": "Sent BrightPath pilot proposal",
            "body": "Shared pilot scope, technical checklist, and implementation timeline.",
            "outcome": "Waiting for technical feedback",
            "duration_minutes": None,
            "lead_id": None,
            "contact_id": contacts["clara"].id,
            "deal_id": deals["brightpath_pilot"].id,
            "account_id": accounts["brightpath"].id,
            "owner_id": users["sales_rep_alex"].id,
            "scheduled_at": None,
            "completed_at": now - timedelta(days=3),
        },
        {
            "type": ActivityType.meeting,
            "subject": "Nova implementation kickoff",
            "body": "Aligned project milestones and customer success ownership.",
            "outcome": "Kickoff complete",
            "duration_minutes": 60,
            "lead_id": None,
            "contact_id": contacts["dev"].id,
            "deal_id": deals["nova_onboarding"].id,
            "account_id": accounts["nova"].id,
            "owner_id": users["customer_success"].id,
            "scheduled_at": now - timedelta(days=2),
            "completed_at": now - timedelta(days=2) + timedelta(hours=1),
        },
        {
            "type": ActivityType.note,
            "subject": "GreenField renewal risk note",
            "body": "Executive sponsor wants a security review before signature.",
            "outcome": None,
            "duration_minutes": None,
            "lead_id": None,
            "contact_id": contacts["emma"].id,
            "deal_id": deals["greenfield_renewal"].id,
            "account_id": accounts["greenfield"].id,
            "owner_id": users["sales_manager"].id,
            "scheduled_at": None,
            "completed_at": now - timedelta(days=1),
        },
        {
            "type": ActivityType.call,
            "subject": "Qualified Northstar inbound lead",
            "body": "Lead has strong fit and requested pricing guidance.",
            "outcome": "Create opportunity after demo",
            "duration_minutes": 22,
            "lead_id": leads["olivia"].id,
            "contact_id": None,
            "deal_id": None,
            "account_id": None,
            "owner_id": users["sales_rep_alex"].id,
            "scheduled_at": now - timedelta(days=1, hours=3),
            "completed_at": now - timedelta(days=1, hours=2, minutes=38),
        },
    )

    activities_by_subject: dict[str, Activity] = {}
    for payload in activity_data:
        activity = await upsert_one(
            db,
            stats,
            "activities",
            select(Activity).where(Activity.subject == payload["subject"]),
            payload,
            payload,
        )
        activities_by_subject[payload["subject"]] = activity

    task_data = (
        {
            "title": "Follow up on Acme legal review",
            "description": "Send redlines to operations and legal stakeholders.",
            "status": TaskStatus.pending,
            "priority": TaskPriority.high,
            "due_at": now - timedelta(days=1),
            "completed_at": None,
            "activity_id": activities_by_subject["Discovery call with Acme operations"].id,
            "lead_id": None,
            "contact_id": contacts["ava"].id,
            "deal_id": deals["acme_expansion"].id,
            "account_id": accounts["acme"].id,
            "owner_id": users["sales_rep_alex"].id,
        },
        {
            "title": "Schedule BrightPath technical validation",
            "description": "Coordinate with Ben and the solution engineer.",
            "status": TaskStatus.in_progress,
            "priority": TaskPriority.medium,
            "due_at": now + timedelta(days=2),
            "completed_at": None,
            "activity_id": None,
            "lead_id": None,
            "contact_id": contacts["clara"].id,
            "deal_id": deals["brightpath_pilot"].id,
            "account_id": accounts["brightpath"].id,
            "owner_id": users["sales_rep_alex"].id,
        },
        {
            "title": "Send Nova onboarding recap",
            "description": "Send milestone summary and project portal link.",
            "status": TaskStatus.completed,
            "priority": TaskPriority.medium,
            "due_at": now - timedelta(days=2),
            "completed_at": now - timedelta(days=2, hours=-2),
            "activity_id": activities_by_subject["Nova implementation kickoff"].id,
            "lead_id": None,
            "contact_id": contacts["dev"].id,
            "deal_id": deals["nova_onboarding"].id,
            "account_id": accounts["nova"].id,
            "owner_id": users["customer_success"].id,
        },
        {
            "title": "Prepare GreenField renewal deck",
            "description": "Highlight ROI, adoption, and security posture.",
            "status": TaskStatus.pending,
            "priority": TaskPriority.high,
            "due_at": now + timedelta(days=4),
            "completed_at": None,
            "activity_id": None,
            "lead_id": None,
            "contact_id": contacts["emma"].id,
            "deal_id": deals["greenfield_renewal"].id,
            "account_id": accounts["greenfield"].id,
            "owner_id": users["sales_manager"].id,
        },
        {
            "title": "Book Northstar pricing demo",
            "description": "Confirm attendees and demo use case.",
            "status": TaskStatus.pending,
            "priority": TaskPriority.medium,
            "due_at": now + timedelta(days=1),
            "completed_at": None,
            "activity_id": activities_by_subject["Qualified Northstar inbound lead"].id,
            "lead_id": leads["olivia"].id,
            "contact_id": None,
            "deal_id": None,
            "account_id": None,
            "owner_id": users["sales_rep_alex"].id,
        },
    )

    for payload in task_data:
        await upsert_one(
            db,
            stats,
            "tasks",
            select(Task).where(Task.title == payload["title"]),
            payload,
            payload,
        )


async def seed_projects(
    db: AsyncSession,
    stats: SeedStats,
    users: dict[str, User],
    accounts: dict[str, Account],
    deals: dict[str, Deal],
) -> dict[str, Project]:
    today = date.today()
    projects_data = (
        (
            "nova_onboarding",
            {
                "name": "Nova Health Onboarding",
                "account_id": accounts["nova"].id,
                "deal_id": deals["nova_onboarding"].id,
                "status": "active",
                "start_date": today - timedelta(days=5),
                "end_date": today + timedelta(days=35),
                "health": ProjectHealth.green,
                "owner_id": users["customer_success"].id,
                "portal_token": "00000000-0000-4000-8000-000000000101",
                "is_active": True,
            },
        ),
        (
            "acme_success",
            {
                "name": "Acme Robotics Success Plan",
                "account_id": accounts["acme"].id,
                "deal_id": deals["acme_expansion"].id,
                "status": "planning",
                "start_date": today + timedelta(days=7),
                "end_date": today + timedelta(days=67),
                "health": ProjectHealth.yellow,
                "owner_id": users["customer_success"].id,
                "portal_token": "00000000-0000-4000-8000-000000000102",
                "is_active": True,
            },
        ),
    )

    projects: dict[str, Project] = {}
    for key, payload in projects_data:
        project = await upsert_one(
            db,
            stats,
            "projects",
            select(Project).where(Project.name == payload["name"]),
            payload,
            payload,
        )
        projects[key] = project

    milestones_data = (
        (projects["nova_onboarding"], "Kickoff complete", today - timedelta(days=2), utc_now() - timedelta(days=2)),
        (projects["nova_onboarding"], "Data import", today + timedelta(days=7), None),
        (projects["nova_onboarding"], "Admin training", today + timedelta(days=18), None),
        (projects["acme_success"], "Implementation plan approved", today + timedelta(days=9), None),
        (projects["acme_success"], "Security review", today + timedelta(days=14), None),
    )

    for project, title, due_date, completed_at in milestones_data:
        await upsert_one(
            db,
            stats,
            "milestones",
            select(Milestone).where(Milestone.project_id == project.id, Milestone.title == title),
            {"project_id": project.id, "title": title, "due_date": due_date, "completed_at": completed_at},
            {"due_date": due_date, "completed_at": completed_at},
        )

    documents_data = (
        (
            projects["nova_onboarding"],
            {
                "name": "Nova Kickoff Notes",
                "file_url": "https://storage.example.local/doxa-demo/nova-kickoff-notes.pdf",
                "content_type": "application/pdf",
                "description": "Seeded kickoff notes document.",
                "filename": "nova-kickoff-notes.pdf",
                "file_size": 248320,
                "mime_type": "application/pdf",
                "storage_key": "demo/projects/nova-kickoff-notes.pdf",
                "uploaded_by": users["customer_success"].id,
            },
        ),
        (
            projects["acme_success"],
            {
                "name": "Acme Success Plan",
                "file_url": "https://storage.example.local/doxa-demo/acme-success-plan.pdf",
                "content_type": "application/pdf",
                "description": "Seeded success plan document.",
                "filename": "acme-success-plan.pdf",
                "file_size": 184512,
                "mime_type": "application/pdf",
                "storage_key": "demo/projects/acme-success-plan.pdf",
                "uploaded_by": users["customer_success"].id,
            },
        ),
    )

    for project, payload in documents_data:
        await upsert_one(
            db,
            stats,
            "project_documents",
            select(ProjectDocument).where(ProjectDocument.project_id == project.id, ProjectDocument.filename == payload["filename"]),
            {"project_id": project.id, **payload},
            payload,
        )

    return projects


async def seed_reports_and_ops(
    db: AsyncSession,
    stats: SeedStats,
    users: dict[str, User],
    accounts: dict[str, Account],
    deals: dict[str, Deal],
) -> None:
    today = date.today()
    period_start, period_end = month_window(today)

    for user_key, quota in (
        ("sales_rep_alex", Decimal("150000.00")),
        ("sales_rep_maya", Decimal("125000.00")),
        ("sales_manager", Decimal("300000.00")),
    ):
        await upsert_one(
            db,
            stats,
            "sales_quotas",
            select(SalesQuota).where(
                SalesQuota.user_id == users[user_key].id,
                SalesQuota.period_start == period_start,
                SalesQuota.period_end == period_end,
            ),
            {
                "user_id": users[user_key].id,
                "period_start": period_start,
                "period_end": period_end,
                "quota_amount": quota,
                "currency": "USD",
            },
            {"quota_amount": quota, "currency": "USD"},
        )

    snapshots = (
        (
            "pipeline_summary",
            "Pipeline Summary",
            {
                "stages": [
                    {"stage": "Qualification", "count": 1, "total_value": 42000, "weighted_value": 10500},
                    {"stage": "Proposal Sent", "count": 1, "total_value": 125000, "weighted_value": 62500},
                    {"stage": "Negotiation", "count": 1, "total_value": 97000, "weighted_value": 72750},
                ]
            },
        ),
        (
            "lead_volume",
            "Lead Volume",
            {"groups": [{"group": "website", "count": 1}, {"group": "referral", "count": 1}, {"group": "social", "count": 1}]},
        ),
        (
            "activity_volume",
            "Activity Volume",
            {"activities": [{"type": "call", "count": 2}, {"type": "email", "count": 1}, {"type": "meeting", "count": 1}, {"type": "note", "count": 1}]},
        ),
    )
    for report_type, name, data in snapshots:
        await upsert_one(
            db,
            stats,
            "report_snapshots",
            select(ReportSnapshot).where(ReportSnapshot.report_type == report_type, ReportSnapshot.date == today),
            {
                "name": name,
                "report_type": report_type,
                "date": today,
                "filters": {},
                "data": data,
                "generated_by": users["admin"].id,
            },
            {"name": name, "filters": {}, "data": data, "generated_by": users["admin"].id},
        )

    subscription = await upsert_one(
        db,
        stats,
        "webhook_subscriptions",
        select(WebhookSubscription).where(WebhookSubscription.url == "https://example.com/doxa-crm-webhook"),
        {
            "url": "https://example.com/doxa-crm-webhook",
            "events": ["lead.created", "deal.won", "project.health_changed"],
            "secret": "demo-webhook-secret-change-me",
            "is_active": True,
        },
        {"events": ["lead.created", "deal.won", "project.health_changed"], "is_active": True},
    )

    await upsert_one(
        db,
        stats,
        "webhook_logs",
        select(WebhookLog).where(WebhookLog.direction == "outbound", WebhookLog.event_type == "deal.won", WebhookLog.url == subscription.url),
        {
            "direction": "outbound",
            "event_type": "deal.won",
            "status": "success",
            "url": subscription.url,
            "status_code": 200,
            "signature": "seed-demo-signature",
            "payload": {"deal_id": str(deals["nova_onboarding"].id), "value": "68000.00"},
            "response_body": '{"ok":true}',
            "error": None,
            "subscription_id": subscription.id,
        },
        {"status": "success", "status_code": 200, "subscription_id": subscription.id},
    )

    started_at = utc_now() - timedelta(minutes=15)
    await upsert_one(
        db,
        stats,
        "task_logs",
        select(TaskLog).where(TaskLog.task_id == "seed-demo-reindex-all"),
        {
            "task_id": "seed-demo-reindex-all",
            "task_name": "app.workers.search_tasks.reindex_all",
            "status": "success",
            "started_at": started_at,
            "finished_at": started_at + timedelta(minutes=2),
            "error": None,
            "details": {"source": "seed_demo_data"},
        },
        {"status": "success", "finished_at": started_at + timedelta(minutes=2), "details": {"source": "seed_demo_data"}},
    )

    await upsert_one(
        db,
        stats,
        "audit_logs",
        select(AuditLog).where(AuditLog.action == "seed", AuditLog.entity_type == "account", AuditLog.entity_id == accounts["acme"].id),
        {
            "user_id": users["admin"].id,
            "action": "seed",
            "entity_type": "account",
            "entity_id": accounts["acme"].id,
            "old_value": None,
            "new_value": {"name": accounts["acme"].name},
            "ip_address": "127.0.0.1",
        },
        {"new_value": {"name": accounts["acme"].name}, "ip_address": "127.0.0.1"},
    )


async def table_counts(db: AsyncSession, models: Iterable[type[Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in models:
        counts[model.__tablename__] = int(await db.scalar(select(func.count()).select_from(model)) or 0)
    return counts


async def seed_demo_data() -> None:
    stats = SeedStats()

    async with AsyncSessionLocal() as db:
        users = await seed_roles_and_users(db, stats)
        accounts, contacts = await seed_foundation(db, stats, users)
        pipeline, stages = await seed_pipelines(db, stats)
        campaigns = await seed_campaigns(db, stats, users, contacts)
        leads = await seed_leads(db, stats, users, campaigns)
        deals = await seed_deals(db, stats, users, accounts, contacts, pipeline, stages)
        await seed_activities_and_tasks(db, stats, users, accounts, contacts, leads, deals)
        await seed_projects(db, stats, users, accounts, deals)
        await seed_reports_and_ops(db, stats, users, accounts, deals)

        await db.commit()

        counts = await table_counts(
            db,
            (
                User,
                Account,
                Contact,
                Lead,
                Pipeline,
                PipelineStage,
                Deal,
                Activity,
                Task,
                Campaign,
                CampaignSequenceStep,
                CampaignEnrollment,
                CampaignMetric,
                Project,
                Milestone,
                ProjectDocument,
                SalesQuota,
                ReportSnapshot,
                WebhookSubscription,
                WebhookLog,
                TaskLog,
                AuditLog,
            ),
        )

    print("Seed data complete.")
    print("Created:", stats.created)
    print("Updated:", stats.updated)
    print("Current counts:", counts)
    print("Backend demo users:")
    print("  admin@doxa.local / super_admin")
    print("  sales.manager@doxa.local / sales_manager")
    print("  alex.rep@doxa.local / sales_rep")
    print("  maya.rep@doxa.local / sales_rep")
    print("  marketing.manager@doxa.local / marketing_manager")
    print("  marketing.rep@doxa.local / marketing_rep")
    print("  success@doxa.local / customer_success")
    print("  readonly@doxa.local / read_only")


async def main() -> None:
    try:
        await seed_demo_data()
    finally:
        await close_database_connections()


if __name__ == "__main__":
    asyncio.run(main())
