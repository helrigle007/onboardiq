import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from statistics import mean

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_pipeline
from app.config import get_settings
from app.infrastructure.database import async_session_factory, get_db
from app.models.schemas import (
    GenerationMetadata,
    GuideEvaluation,
    GuideRequest,
    GuideResponse,
    GuideStatus,
    GuideSummary,
)
from app.services.guide_service import GuideService

logger = logging.getLogger(__name__)

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

    # Launch real pipeline in background
    background_tasks.add_task(_run_generation_pipeline, guide_id, request)

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


async def _run_generation_pipeline(guide_id: str, request: GuideRequest) -> None:
    """Run the full LangGraph pipeline in a background task."""
    settings = get_settings()

    # Create SSE publish closure bound to guide_id
    async def emit(event: dict) -> None:
        await publish_event(guide_id, event)

    try:
        # Use async_session_factory directly (not Depends — we're in a background task)
        assert async_session_factory is not None, "Database not initialized"

        # Update status to generating
        async with async_session_factory() as db:
            service = GuideService(db)
            await service.update_guide_status(guide_id, GuideStatus.GENERATING)

        # Run the pipeline
        pipeline_start = time.time()
        final_state = await run_pipeline(guide_id, request, emit)

        generation_time = time.time() - pipeline_start

        # Build metadata
        metadata = GenerationMetadata(
            model=settings.generation_model,
            total_tokens_used=final_state.get("total_tokens", 0),
            total_cost_usd=final_state.get("total_cost_usd", 0.0),
            generation_time_seconds=round(generation_time, 2),
            retrieval_latency_ms=final_state.get("retrieval_latency_ms", 0.0),
            chunks_retrieved=final_state.get("chunks_retrieved", 0),
            chunks_after_reranking=final_state.get("chunks_after_reranking", 0),
            regeneration_count=final_state.get("regeneration_count", 0),
        )

        # Build evaluation
        section_evals = final_state.get("section_evaluations", [])
        overall_score = (
            round(mean(e.overall_score for e in section_evals), 4)
            if section_evals
            else 0.0
        )

        evaluation = GuideEvaluation(
            guide_id=guide_id,
            overall_score=overall_score,
            section_evaluations=section_evals,
            generation_metadata=metadata,
        )

        # Build guide response
        sections = final_state.get("sections", [])
        guide_response = GuideResponse(
            id=guide_id,
            product=request.product,
            role=request.role,
            title=(
                f"{request.product.value.title()} Onboarding: "
                f"{request.role.value.replace('_', ' ').title()}"
            ),
            description=(
                f"A personalized {request.experience_level.value}-level "
                f"onboarding guide for "
                f"{request.role.value.replace('_', ' ')}s integrating "
                f"{request.product.value.title()}."
            ),
            sections=sections,
            evaluation=evaluation,
            metadata=metadata,
            created_at=datetime.now(UTC),
        )

        # Persist results
        async with async_session_factory() as db:
            service = GuideService(db)
            await service.save_guide_result(
                guide_id=guide_id,
                sections=[s.model_dump() for s in sections],
                evaluation=evaluation.model_dump(),
                metadata=metadata.model_dump(),
            )

            # Save evaluation run
            dim_scores = {}
            for ev in section_evals:
                for dim in ev.dimensions:
                    if dim.dimension not in dim_scores:
                        dim_scores[dim.dimension] = []
                    dim_scores[dim.dimension].append(dim.score)
            avg_dim_scores = {k: round(mean(v), 4) for k, v in dim_scores.items()}

            await service.save_evaluation_run(
                guide_id=guide_id,
                overall_score=overall_score,
                dimension_scores=avg_dim_scores,
                section_scores=[e.model_dump() for e in section_evals],
                tokens_used=metadata.total_tokens_used,
                cost_usd=metadata.total_cost_usd,
                latency_seconds=generation_time,
            )

        # Emit guide_complete SSE
        await emit({
            "type": "guide_complete",
            "guide": guide_response.model_dump(mode="json"),
        })

        logger.info(
            "Guide %s complete: %.3f score, %d tokens, $%.4f, %.1fs",
            guide_id,
            overall_score,
            metadata.total_tokens_used,
            metadata.total_cost_usd,
            generation_time,
        )

    except Exception:
        logger.exception("Pipeline failed for guide %s", guide_id)

        # Update status to failed
        try:
            async with async_session_factory() as db:
                service = GuideService(db)
                await service.update_guide_status(guide_id, GuideStatus.FAILED)
        except Exception:
            logger.exception("Failed to update guide status to FAILED")

        await emit({
            "type": "error",
            "message": "Guide generation failed. Please try again.",
            "recoverable": False,
        })
