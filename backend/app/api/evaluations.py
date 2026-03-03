from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.database import EvaluationRun

router = APIRouter()


@router.get("/{guide_id}")
async def get_evaluation(
    guide_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get evaluation details for a guide."""
    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.guide_id == guide_id)
        .order_by(EvaluationRun.created_at.desc())
    )
    runs = result.scalars().all()
    if not runs:
        raise HTTPException(status_code=404, detail="No evaluations found")
    return {
        "guide_id": guide_id,
        "evaluations": [
            {
                "id": run.id,
                "run_type": run.run_type,
                "overall_score": run.overall_score,
                "dimension_scores": run.dimension_scores,
                "section_scores": run.section_scores,
                "tokens_used": run.tokens_used,
                "cost_usd": run.cost_usd,
                "latency_seconds": run.latency_seconds,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ],
    }


@router.get("/history/")
async def evaluation_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Evaluation trends over time."""
    result = await db.execute(
        select(EvaluationRun)
        .order_by(EvaluationRun.created_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()
    return {
        "total_runs": len(runs),
        "evaluations": [
            {
                "id": run.id,
                "guide_id": run.guide_id,
                "overall_score": run.overall_score,
                "tokens_used": run.tokens_used,
                "cost_usd": run.cost_usd,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ],
    }
