import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import EvaluationRun, Guide
from app.models.schemas import (
    GuideRequest,
    GuideResponse,
    GuideStatus,
    GuideSummary,
)


class GuideService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_guide(self, request: GuideRequest) -> str:
        """Create a guide record and return its ID. Pipeline runs async."""
        guide_id = str(uuid.uuid4())
        guide = Guide(
            id=guide_id,
            product=request.product.value,
            role=request.role.value,
            experience_level=request.experience_level.value,
            title=(
                f"{request.product.value.title()} Onboarding: "
                f"{request.role.value.replace('_', ' ').title()}"
            ),
            description="",
            status=GuideStatus.PENDING.value,
            focus_areas=list(request.focus_areas),
            tech_stack=list(request.tech_stack),
        )
        self.db.add(guide)
        await self.db.commit()
        return guide_id

    async def get_guide(self, guide_id: str) -> GuideResponse | None:
        """Fetch a completed guide by ID."""
        result = await self.db.execute(select(Guide).where(Guide.id == guide_id))
        guide = result.scalar_one_or_none()
        if not guide:
            return None
        return self._to_response(guide)

    async def list_guides(
        self,
        product: str | None = None,
        role: str | None = None,
        limit: int = 20,
    ) -> list[GuideSummary]:
        """List guides with optional filtering."""
        query = select(Guide).order_by(Guide.created_at.desc()).limit(limit)
        if product:
            query = query.where(Guide.product == product)
        if role:
            query = query.where(Guide.role == role)
        result = await self.db.execute(query)
        guides = result.scalars().all()
        return [self._to_summary(g) for g in guides]

    async def update_guide_status(self, guide_id: str, status: GuideStatus) -> None:
        result = await self.db.execute(select(Guide).where(Guide.id == guide_id))
        guide = result.scalar_one_or_none()
        if guide:
            guide.status = status.value
            await self.db.commit()

    async def save_guide_result(
        self,
        guide_id: str,
        sections: list[dict[str, Any]],
        evaluation: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        """Save completed guide data."""
        result = await self.db.execute(select(Guide).where(Guide.id == guide_id))
        guide = result.scalar_one_or_none()
        if guide:
            guide.sections = sections  # type: ignore[assignment]
            guide.evaluation = evaluation
            guide.generation_metadata = metadata
            guide.status = GuideStatus.COMPLETE.value
            await self.db.commit()

    async def save_evaluation_run(
        self,
        guide_id: str,
        overall_score: float,
        dimension_scores: dict[str, Any],
        section_scores: list[Any],
        tokens_used: int,
        cost_usd: float,
        latency_seconds: float,
    ) -> str:
        eval_run = EvaluationRun(
            id=str(uuid.uuid4()),
            guide_id=guide_id,
            run_type="generation",
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            section_scores=section_scores,  # type: ignore[arg-type]
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            latency_seconds=latency_seconds,
        )
        self.db.add(eval_run)
        await self.db.commit()
        return eval_run.id

    def _to_response(self, guide: Guide) -> GuideResponse:
        eval_data: dict[str, Any] = guide.evaluation or {}
        meta_data: dict[str, Any] = guide.generation_metadata or {}
        sections_data: list[Any] = guide.sections if isinstance(guide.sections, list) else []
        return GuideResponse(
            id=guide.id,
            product=guide.product,  # type: ignore[arg-type]
            role=guide.role,  # type: ignore[arg-type]
            title=guide.title,
            description=guide.description or "",
            sections=sections_data,
            evaluation=eval_data,  # type: ignore[arg-type]
            metadata=meta_data,  # type: ignore[arg-type]
            created_at=guide.created_at,
        )

    def _to_summary(self, guide: Guide) -> GuideSummary:
        eval_data: dict[str, Any] = guide.evaluation or {}
        sections_list: list[Any] = guide.sections if isinstance(guide.sections, list) else []
        return GuideSummary(
            id=guide.id,
            product=guide.product,  # type: ignore[arg-type]
            role=guide.role,  # type: ignore[arg-type]
            title=guide.title,
            overall_score=eval_data.get("overall_score", 0.0),
            sections_count=len(sections_list),
            created_at=guide.created_at,
        )
