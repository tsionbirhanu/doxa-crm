from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Deal,
    DealStageHistory,
    DealStatus,
    Pipeline,
    PipelineStage,
    User,
)
from app.schemas.pipelines import (
    PipelineCreate,
    PipelineResponse,
    PipelineStageCreate,
    PipelineStageResponse,
    PipelineStageUpdate,
    PipelineUpdate,
)

FOLLOW_UP_STAGE_NAMES = {"proposal sent", "negotiation"}


def _not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found")


def _is_won_stage(stage: PipelineStage) -> bool:
    return "won" in stage.name.lower()


def _is_lost_stage(stage: PipelineStage) -> bool:
    return "lost" in stage.name.lower()


async def build_pipeline_response(db: AsyncSession, pipeline: Pipeline) -> PipelineResponse:
    stages = await list_pipeline_stages(db, pipeline.id)
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        is_default=pipeline.is_default,
        stages=stages,
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at,
    )


async def list_pipelines(db: AsyncSession) -> list[PipelineResponse]:
    result = await db.execute(select(Pipeline).order_by(Pipeline.created_at.desc()))
    return [await build_pipeline_response(db, pipeline) for pipeline in result.scalars().all()]


async def get_pipeline_model(db: AsyncSession, pipeline_id: UUID) -> Pipeline:
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        raise _not_found("Pipeline")
    return pipeline


async def get_pipeline(db: AsyncSession, pipeline_id: UUID) -> PipelineResponse:
    return await build_pipeline_response(db, await get_pipeline_model(db, pipeline_id))


async def create_pipeline(db: AsyncSession, pipeline_in: PipelineCreate) -> PipelineResponse:
    pipeline = Pipeline(name=pipeline_in.name, is_default=pipeline_in.is_default)
    db.add(pipeline)
    await db.flush()

    for stage_in in pipeline_in.stages:
        db.add(
            PipelineStage(
                pipeline_id=pipeline.id,
                name=stage_in.name,
                probability=stage_in.probability,
                order_index=stage_in.order_index,
            )
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pipeline could not be created") from exc

    await db.refresh(pipeline)
    return await build_pipeline_response(db, pipeline)


async def update_pipeline(
    db: AsyncSession,
    pipeline_id: UUID,
    pipeline_in: PipelineUpdate,
) -> PipelineResponse:
    pipeline = await get_pipeline_model(db, pipeline_id)
    for field_name, value in pipeline_in.model_dump(exclude_unset=True).items():
        setattr(pipeline, field_name, value)
    await db.commit()
    await db.refresh(pipeline)
    return await build_pipeline_response(db, pipeline)


async def delete_pipeline(db: AsyncSession, pipeline_id: UUID) -> None:
    pipeline = await get_pipeline_model(db, pipeline_id)
    deal_count_result = await db.execute(select(func.count(Deal.id)).where(Deal.pipeline_id == pipeline_id))
    if int(deal_count_result.scalar_one() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline cannot be deleted while deals reference it",
        )
    await db.delete(pipeline)
    await db.commit()


async def list_pipeline_stages(db: AsyncSession, pipeline_id: UUID) -> list[PipelineStageResponse]:
    result = await db.execute(
        select(PipelineStage)
        .where(PipelineStage.pipeline_id == pipeline_id)
        .order_by(PipelineStage.order_index.asc())
    )
    return [PipelineStageResponse.model_validate(stage) for stage in result.scalars().all()]


async def get_stage_model(db: AsyncSession, pipeline_id: UUID, stage_id: UUID) -> PipelineStage:
    result = await db.execute(
        select(PipelineStage).where(
            PipelineStage.id == stage_id,
            PipelineStage.pipeline_id == pipeline_id,
        )
    )
    stage = result.scalar_one_or_none()
    if stage is None:
        raise _not_found("Pipeline stage")
    return stage


async def add_pipeline_stage(
    db: AsyncSession,
    pipeline_id: UUID,
    stage_in: PipelineStageCreate,
) -> PipelineStageResponse:
    await get_pipeline_model(db, pipeline_id)
    stage = PipelineStage(
        pipeline_id=pipeline_id,
        name=stage_in.name,
        probability=stage_in.probability,
        order_index=stage_in.order_index,
    )
    db.add(stage)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pipeline stage could not be created") from exc
    await db.refresh(stage)
    return PipelineStageResponse.model_validate(stage)


async def update_pipeline_stage(
    db: AsyncSession,
    pipeline_id: UUID,
    stage_id: UUID,
    stage_in: PipelineStageUpdate,
) -> PipelineStageResponse:
    stage = await get_stage_model(db, pipeline_id, stage_id)
    for field_name, value in stage_in.model_dump(exclude_unset=True).items():
        setattr(stage, field_name, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pipeline stage update conflicts") from exc
    await db.refresh(stage)
    return PipelineStageResponse.model_validate(stage)


async def delete_pipeline_stage(db: AsyncSession, pipeline_id: UUID, stage_id: UUID) -> None:
    stage = await get_stage_model(db, pipeline_id, stage_id)
    deal_count_result = await db.execute(select(func.count(Deal.id)).where(Deal.stage_id == stage_id))
    if int(deal_count_result.scalar_one() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline stage cannot be deleted while deals reference it",
        )
    await db.delete(stage)
    await db.commit()


async def move_deal_to_stage(
    db: AsyncSession,
    deal: Deal,
    to_stage_id: UUID,
    current_user: User,
    *,
    lost_reason: str | None = None,
) -> Deal:
    stage_result = await db.execute(select(PipelineStage).where(PipelineStage.id == to_stage_id))
    to_stage = stage_result.scalar_one_or_none()
    if to_stage is None:
        raise _not_found("Pipeline stage")

    if to_stage.pipeline_id != deal.pipeline_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deal can only move to stages within the same pipeline",
        )

    if _is_lost_stage(to_stage) and not lost_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lost_reason is required when moving a deal to a lost stage",
        )

    from_stage_id = deal.stage_id
    deal.stage_id = to_stage.id
    deal.probability = to_stage.probability

    if _is_won_stage(to_stage):
        deal.status = DealStatus.won
        deal.closed_at = datetime.now(timezone.utc)
        deal.lost_reason = None
    elif _is_lost_stage(to_stage):
        deal.status = DealStatus.lost
        deal.closed_at = datetime.now(timezone.utc)
        deal.lost_reason = lost_reason
    else:
        deal.status = DealStatus.open
        deal.closed_at = None
        deal.lost_reason = None

    if from_stage_id != to_stage.id:
        db.add(
            DealStageHistory(
                deal_id=deal.id,
                from_stage_id=from_stage_id,
                to_stage_id=to_stage.id,
                changed_by=current_user.id,
                note=f"Moved to {to_stage.name}",
            )
        )
        await _create_follow_up_task_if_needed(db, deal, to_stage)

    return deal


async def _create_follow_up_task_if_needed(
    db: AsyncSession,
    deal: Deal,
    stage: PipelineStage,
) -> None:
    if stage.name.lower() not in FOLLOW_UP_STAGE_NAMES:
        return

    from app.services.task_automation import create_tasks_for_stage_transition

    await create_tasks_for_stage_transition(db, deal.id, stage.id)
