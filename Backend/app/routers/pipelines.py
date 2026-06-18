from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import PIPELINE_ADMIN_ROLES
from app.dependencies import get_current_user, get_db, require_role
from app.models import User
from app.schemas.pipelines import (
    PipelineCreate,
    PipelineResponse,
    PipelineStageCreate,
    PipelineStageResponse,
    PipelineStageUpdate,
    PipelineUpdate,
)
from app.services import pipeline as pipeline_service

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.get("/", response_model=list[PipelineResponse])
async def list_pipelines(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PipelineResponse]:
    return await pipeline_service.list_pipelines(db)


@router.post("/", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    pipeline_in: PipelineCreate,
    current_user: Annotated[User, Depends(require_role(*PIPELINE_ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PipelineResponse:
    return await pipeline_service.create_pipeline(db, pipeline_in)


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PipelineResponse:
    return await pipeline_service.get_pipeline(db, pipeline_id)


@router.patch("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: UUID,
    pipeline_in: PipelineUpdate,
    current_user: Annotated[User, Depends(require_role(*PIPELINE_ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PipelineResponse:
    return await pipeline_service.update_pipeline(db, pipeline_id, pipeline_in)


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: UUID,
    current_user: Annotated[User, Depends(require_role(*PIPELINE_ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await pipeline_service.delete_pipeline(db, pipeline_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{pipeline_id}/stages", response_model=list[PipelineStageResponse])
async def list_pipeline_stages(
    pipeline_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PipelineStageResponse]:
    return await pipeline_service.list_pipeline_stages(db, pipeline_id)


@router.post("/{pipeline_id}/stages", response_model=PipelineStageResponse, status_code=status.HTTP_201_CREATED)
async def add_pipeline_stage(
    pipeline_id: UUID,
    stage_in: PipelineStageCreate,
    current_user: Annotated[User, Depends(require_role(*PIPELINE_ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PipelineStageResponse:
    return await pipeline_service.add_pipeline_stage(db, pipeline_id, stage_in)


@router.patch("/{pipeline_id}/stages/{stage_id}", response_model=PipelineStageResponse)
async def update_pipeline_stage(
    pipeline_id: UUID,
    stage_id: UUID,
    stage_in: PipelineStageUpdate,
    current_user: Annotated[User, Depends(require_role(*PIPELINE_ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PipelineStageResponse:
    return await pipeline_service.update_pipeline_stage(db, pipeline_id, stage_id, stage_in)


@router.delete("/{pipeline_id}/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_stage(
    pipeline_id: UUID,
    stage_id: UUID,
    current_user: Annotated[User, Depends(require_role(*PIPELINE_ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await pipeline_service.delete_pipeline_stage(db, pipeline_id, stage_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
