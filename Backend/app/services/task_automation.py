from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deal, PipelineStage, Task, TaskPriority, TaskStatus

RULES_FILE = Path(__file__).with_name("task_automation_rules.json")


def load_automation_rules() -> list[dict[str, Any]]:
    if not RULES_FILE.exists():
        return []

    with RULES_FILE.open("r", encoding="utf-8") as rules_file:
        data = json.load(rules_file)

    rules = data.get("stage_rules", [])
    return rules if isinstance(rules, list) else []


async def create_tasks_for_stage_transition(
    db: AsyncSession,
    deal_id: UUID,
    new_stage_id: UUID,
) -> list[Task]:
    deal_result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = deal_result.scalar_one_or_none()
    stage_result = await db.execute(select(PipelineStage).where(PipelineStage.id == new_stage_id))
    stage = stage_result.scalar_one_or_none()

    if deal is None or stage is None:
        return []

    created_tasks: list[Task] = []
    for rule in load_automation_rules():
        if not _rule_matches_stage(rule, stage):
            continue

        task = Task(
            title=rule.get("title", f"Follow up on {deal.title}"),
            description=rule.get("description"),
            status=TaskStatus.pending,
            priority=_parse_priority(rule.get("priority")),
            due_at=datetime.now(timezone.utc) + timedelta(days=int(rule.get("due_in_days", 3))),
            deal_id=deal.id,
            contact_id=deal.contact_id,
            account_id=deal.account_id,
            owner_id=deal.owner_id,
        )
        db.add(task)
        created_tasks.append(task)

    return created_tasks


def _rule_matches_stage(rule: dict[str, Any], stage: PipelineStage) -> bool:
    stage_names = {str(name).lower() for name in rule.get("stage_names", [])}
    stage_ids = {str(stage_id) for stage_id in rule.get("stage_ids", [])}
    return stage.name.lower() in stage_names or str(stage.id) in stage_ids


def _parse_priority(value: Any) -> TaskPriority:
    try:
        return TaskPriority(value)
    except (TypeError, ValueError):
        return TaskPriority.medium
