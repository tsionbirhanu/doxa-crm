from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Pipeline, PipelineStage

DEFAULT_PIPELINE_NAME = "New Business"
DEFAULT_STAGES = (
    ("Prospecting", 10.0),
    ("Qualification", 25.0),
    ("Proposal Sent", 50.0),
    ("Negotiation", 75.0),
    ("Closed Won", 100.0),
    ("Closed Lost", 0.0),
)


async def seed_default_pipeline() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Pipeline).where(Pipeline.name == DEFAULT_PIPELINE_NAME))
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f'Pipeline "{DEFAULT_PIPELINE_NAME}" already exists.')
            return

        pipeline = Pipeline(name=DEFAULT_PIPELINE_NAME, is_default=True)
        db.add(pipeline)
        await db.flush()

        for index, (name, probability) in enumerate(DEFAULT_STAGES):
            db.add(
                PipelineStage(
                    pipeline_id=pipeline.id,
                    name=name,
                    probability=probability,
                    order_index=index,
                )
            )

        await db.commit()
        print(f'Created pipeline "{DEFAULT_PIPELINE_NAME}" with {len(DEFAULT_STAGES)} stages.')


if __name__ == "__main__":
    asyncio.run(seed_default_pipeline())
