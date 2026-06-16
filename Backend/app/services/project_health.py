from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Milestone, Project, ProjectHealth


def calculate_project_health(
    milestones: list[Milestone],
    *,
    today: date | None = None,
) -> ProjectHealth:
    today = today or date.today()
    warning_date = today + timedelta(days=3)

    open_milestones = [milestone for milestone in milestones if milestone.completed_at is None]
    if any(milestone.due_date < today for milestone in open_milestones):
        return ProjectHealth.red
    if any(today <= milestone.due_date <= warning_date for milestone in open_milestones):
        return ProjectHealth.yellow
    return ProjectHealth.green


async def update_single_project_health(db: AsyncSession, project: Project) -> ProjectHealth:
    result = await db.execute(
        select(Milestone).where(Milestone.project_id == project.id).order_by(Milestone.due_date.asc())
    )
    project.health = calculate_project_health(list(result.scalars().all()))
    return project.health


async def update_project_health(db: AsyncSession) -> int:
    result = await db.execute(select(Project).where(Project.is_active.is_(True)))
    projects = list(result.scalars().all())

    for project in projects:
        await update_single_project_health(db, project)

    await db.commit()
    return len(projects)
