from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PipelineStageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    probability: float = Field(ge=0, le=100)
    order_index: int = Field(ge=0)


class PipelineStageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    probability: float | None = Field(default=None, ge=0, le=100)
    order_index: int | None = Field(default=None, ge=0)


class PipelineStageResponse(BaseModel):
    id: UUID
    pipeline_id: UUID
    name: str
    probability: float
    order_index: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_default: bool = False
    stages: list[PipelineStageCreate] = Field(default_factory=list)


class PipelineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_default: bool | None = None


class PipelineResponse(BaseModel):
    id: UUID
    name: str
    is_default: bool
    stages: list[PipelineStageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
