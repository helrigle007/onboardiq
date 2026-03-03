import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.schemas import (
    GuideRequest,
    GuideResponse,
    GuideSummary,
)
from app.services.guide_service import GuideService

router = APIRouter()

# In-memory event queues for SSE (production would use Redis pub/sub)
_event_queues: dict[str, asyncio.Queue] = {}


def get_event_queue(guide_id: str) -> asyncio.Queue:
    if guide_id not in _event_queues:
        _event_queues[guide_id] = asyncio.Queue()
    return _event_queues[guide_id]


async def publish_event(guide_id: str, event: dict) -> None:
    """Publish an SSE event for a guide generation."""
    queue = get_event_queue(guide_id)
    await queue.put(event)


@router.post("/generate")
async def generate_guide(
    request: GuideRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start guide generation. Returns guide_id for SSE streaming."""
    service = GuideService(db)
    guide_id = await service.create_guide(request)

    # Launch pipeline in background
    # Phase 2 will implement: background_tasks.add_task(run_pipeline, guide_id, request)
    # For now, publish a placeholder event
    background_tasks.add_task(_placeholder_pipeline, guide_id, request)

    return {"guide_id": guide_id, "status": "generating"}


@router.get("/{guide_id}/stream")
async def stream_guide(guide_id: str, request: Request):
    """SSE endpoint for real-time generation progress."""

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = get_event_queue(guide_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"

                    # If this is the final event, stop
                    if event.get("type") in ("guide_complete", "error"):
                        break
                except TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        finally:
            # Cleanup
            _event_queues.pop(guide_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{guide_id}", response_model=GuideResponse)
async def get_guide(
    guide_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a completed guide by ID."""
    service = GuideService(db)
    guide = await service.get_guide(guide_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    return guide


@router.get("/", response_model=list[GuideSummary])
async def list_guides(
    product: str | None = None,
    role: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List generated guides with optional filters."""
    service = GuideService(db)
    return await service.list_guides(product=product, role=role, limit=limit)


async def _placeholder_pipeline(guide_id: str, request: GuideRequest):
    """Placeholder until Phase 2 implements real pipeline."""
    agents = ["role_profiler", "content_curator", "guide_generator", "quality_evaluator"]
    for agent in agents:
        await publish_event(guide_id, {
            "type": "agent_start",
            "agent": agent,
            "message": f"Starting {agent.replace('_', ' ')}...",
        })
        await asyncio.sleep(0.1)
        await publish_event(guide_id, {
            "type": "agent_complete",
            "agent": agent,
            "duration_ms": 100,
        })

    await publish_event(guide_id, {
        "type": "guide_complete",
        "guide": {
            "id": guide_id,
            "product": request.product.value,
            "role": request.role.value,
            "title": f"Placeholder Guide for {request.role.value}",
            "description": "This is a placeholder. Real pipeline coming in Phase 2.",
            "sections": [],
            "evaluation": {
                "guide_id": guide_id,
                "overall_score": 0.0,
                "section_evaluations": [],
                "generation_metadata": {
                    "model": "placeholder",
                    "total_tokens_used": 0,
                    "total_cost_usd": 0.0,
                    "generation_time_seconds": 0.0,
                    "retrieval_latency_ms": 0.0,
                    "chunks_retrieved": 0,
                    "chunks_after_reranking": 0,
                    "regeneration_count": 0,
                },
            },
            "metadata": {
                "model": "placeholder",
                "total_tokens_used": 0,
                "total_cost_usd": 0.0,
                "generation_time_seconds": 0.0,
                "retrieval_latency_ms": 0.0,
                "chunks_retrieved": 0,
                "chunks_after_reranking": 0,
                "regeneration_count": 0,
            },
            "created_at": datetime.now(UTC).isoformat(),
        },
    })
