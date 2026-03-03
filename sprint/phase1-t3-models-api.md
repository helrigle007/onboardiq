# Phase 1 — Terminal 3: Data Models + API Layer

## Overview
You are building the complete Pydantic schema layer, SQLAlchemy database models, and all FastAPI endpoints including SSE streaming. This is the contract layer — everything the frontend calls and everything the agents produce flows through your schemas.

## Pre-flight
```bash
cd ~/onboardiq
git checkout infra/scaffolding   # wait for T1 to finish
git checkout -b feat/models-api
```

## Task 1: Pydantic Schemas (Complete)

### File: `backend/app/models/schemas.py`

This is the single source of truth for all data shapes. Implement every model below exactly — other terminals depend on these types.

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime


# ━━━ Enums ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SupportedProduct(str, Enum):
    STRIPE = "stripe"
    TWILIO = "twilio"
    SENDGRID = "sendgrid"


class UserRole(str, Enum):
    FRONTEND_DEVELOPER = "frontend_developer"
    BACKEND_DEVELOPER = "backend_developer"
    SECURITY_ENGINEER = "security_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    PRODUCT_MANAGER = "product_manager"
    TEAM_LEAD = "team_lead"


class ExperienceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class GuideStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    EVALUATING = "evaluating"
    REGENERATING = "regenerating"
    COMPLETE = "complete"
    FAILED = "failed"


# ━━━ Request Models ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class GuideRequest(BaseModel):
    product: SupportedProduct
    role: UserRole
    experience_level: ExperienceLevel = ExperienceLevel.INTERMEDIATE
    focus_areas: list[str] = Field(
        default=[],
        max_length=5,
        description="Specific topics: 'webhooks', 'authentication', etc.",
    )
    tech_stack: list[str] = Field(
        default=[],
        description="User's tech stack for tailored code examples",
    )


# ━━━ Role Profile (Role Profiler Agent Output) ━━━━━━━━━━━━━━━━━━━

class RoleProfile(BaseModel):
    role: UserRole
    experience_level: ExperienceLevel
    primary_concerns: list[str] = Field(
        description="Top 5 concerns for this role when onboarding to this product",
    )
    relevant_doc_topics: list[str] = Field(
        description="8-12 documentation topic areas to prioritize in retrieval",
    )
    excluded_topics: list[str] = Field(
        description="Topics irrelevant to this role, to filter out",
    )
    learning_objectives: list[str] = Field(
        description="4-6 concrete skills. Each starts with action verb.",
    )
    complexity_ceiling: str = Field(
        description="'conceptual' | 'hands-on' | 'deep-dive'",
    )


# ━━━ Guide Section (Generator Agent Output) ━━━━━━━━━━━━━━━━━━━━━━

class CodeExample(BaseModel):
    language: str
    code: str
    description: str


class Citation(BaseModel):
    source_url: str
    source_title: str
    chunk_id: str
    relevance_score: float


class GuideSection(BaseModel):
    section_number: int
    title: str
    summary: str = Field(description="2-3 sentence overview of this section")
    content: str = Field(description="Full markdown content with steps and explanations")
    key_takeaways: list[str] = Field(max_length=5)
    code_examples: list[CodeExample] = Field(default=[])
    warnings: list[str] = Field(
        default=[],
        description="Common pitfalls and gotchas for this section",
    )
    citations: list[Citation] = Field(default=[])
    estimated_time_minutes: int = Field(ge=1, le=120)
    prerequisites: list[str] = Field(default=[])


# ━━━ Evaluation (Quality Evaluator Agent Output) ━━━━━━━━━━━━━━━━━

class DimensionScore(BaseModel):
    dimension: str  # completeness|role_relevance|actionability|clarity|progressive_complexity
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    suggestions: list[str] = Field(default=[])


class SectionEvaluation(BaseModel):
    section_number: int
    overall_score: float = Field(ge=0.0, le=1.0)
    dimensions: list[DimensionScore]
    pass_threshold: bool
    needs_regeneration: bool


class GenerationMetadata(BaseModel):
    model: str
    total_tokens_used: int
    total_cost_usd: float
    generation_time_seconds: float
    retrieval_latency_ms: float
    chunks_retrieved: int
    chunks_after_reranking: int
    regeneration_count: int
    langsmith_trace_url: Optional[str] = None


class GuideEvaluation(BaseModel):
    guide_id: str
    overall_score: float = Field(ge=0.0, le=1.0)
    section_evaluations: list[SectionEvaluation]
    generation_metadata: GenerationMetadata


# ━━━ Full Guide Response ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class GuideResponse(BaseModel):
    id: str
    product: SupportedProduct
    role: UserRole
    title: str
    description: str
    sections: list[GuideSection]
    evaluation: GuideEvaluation
    metadata: GenerationMetadata
    created_at: datetime


class GuideSummary(BaseModel):
    """Lightweight guide listing (for index endpoints)."""
    id: str
    product: SupportedProduct
    role: UserRole
    title: str
    overall_score: float
    sections_count: int
    created_at: datetime


# ━━━ SSE Event Types ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SSEAgentStart(BaseModel):
    type: str = "agent_start"
    agent: str
    message: str


class SSEAgentComplete(BaseModel):
    type: str = "agent_complete"
    agent: str
    duration_ms: float


class SSESectionGenerated(BaseModel):
    type: str = "section_generated"
    section: GuideSection
    index: int


class SSESectionEvaluated(BaseModel):
    type: str = "section_evaluated"
    evaluation: SectionEvaluation
    index: int


class SSERegenerationTriggered(BaseModel):
    type: str = "regeneration_triggered"
    sections: list[int]
    attempt: int


class SSEGuideComplete(BaseModel):
    type: str = "guide_complete"
    guide: GuideResponse


class SSEError(BaseModel):
    type: str = "error"
    message: str
    recoverable: bool


# ━━━ Product/Config Responses ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProductInfo(BaseModel):
    id: str
    name: str
    description: str
    doc_count: int
    chunk_count: int
    available_roles: list[UserRole]


class ProductListResponse(BaseModel):
    products: list[ProductInfo]
```

## Task 2: SQLAlchemy Database Models

### File: `backend/app/models/database.py`

```python
from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()


class Guide(Base):
    __tablename__ = "guides"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product = Column(String, nullable=False)
    role = Column(String, nullable=False)
    experience_level = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    sections = Column(JSON, nullable=False, default=list)
    evaluation = Column(JSON, default=dict)
    generation_metadata = Column(JSON, default=dict)
    focus_areas = Column(JSON, default=list)
    tech_stack = Column(JSON, default=list)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_guides_product_role", "product", "role"),
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    guide_id = Column(String, nullable=False, index=True)
    run_type = Column(String, default="generation")  # generation | regression
    overall_score = Column(Float)
    dimension_scores = Column(JSON, default=dict)
    section_scores = Column(JSON, default=list)
    ragas_metrics = Column(JSON, default=dict)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

Update the Alembic migration (that T1 created) if needed to match these models exactly.

## Task 3: Guide Service (Business Logic)

### File: `backend/app/services/guide_service.py`

This orchestrates guide generation and persistence. It will be called by the API layer and will call the LangGraph pipeline (implemented in Phase 2). For now, implement everything EXCEPT the actual agent invocation — stub that part.

```python
import uuid
import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.schemas import (
    GuideRequest, GuideResponse, GuideSummary, GuideStatus,
    GenerationMetadata,
)
from app.models.database import Guide, EvaluationRun


class GuideService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_guide(self, request: GuideRequest) -> str:
        """Create a guide record and return its ID. Pipeline runs async."""
        guide_id = str(uuid.uuid4())
        guide = Guide(
            id=guide_id,
            product=request.product.value,
            role=request.role.value,
            experience_level=request.experience_level.value,
            title=f"{request.product.value.title()} Onboarding: {request.role.value.replace('_', ' ').title()}",
            description="",
            status=GuideStatus.PENDING.value,
            focus_areas=[a for a in request.focus_areas],
            tech_stack=[t for t in request.tech_stack],
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
        sections: list[dict],
        evaluation: dict,
        metadata: dict,
    ) -> None:
        """Save completed guide data."""
        result = await self.db.execute(select(Guide).where(Guide.id == guide_id))
        guide = result.scalar_one_or_none()
        if guide:
            guide.sections = sections
            guide.evaluation = evaluation
            guide.generation_metadata = metadata
            guide.status = GuideStatus.COMPLETE.value
            await self.db.commit()

    async def save_evaluation_run(
        self,
        guide_id: str,
        overall_score: float,
        dimension_scores: dict,
        section_scores: list,
        tokens_used: int,
        cost_usd: float,
        latency_seconds: float,
    ) -> str:
        eval_run = EvaluationRun(
            guide_id=guide_id,
            run_type="generation",
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            section_scores=section_scores,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            latency_seconds=latency_seconds,
        )
        self.db.add(eval_run)
        await self.db.commit()
        return eval_run.id

    def _to_response(self, guide: Guide) -> GuideResponse:
        eval_data = guide.evaluation or {}
        meta_data = guide.generation_metadata or {}
        return GuideResponse(
            id=guide.id,
            product=guide.product,
            role=guide.role,
            title=guide.title,
            description=guide.description or "",
            sections=guide.sections or [],
            evaluation=eval_data,
            metadata=meta_data,
            created_at=guide.created_at,
        )

    def _to_summary(self, guide: Guide) -> GuideSummary:
        eval_data = guide.evaluation or {}
        return GuideSummary(
            id=guide.id,
            product=guide.product,
            role=guide.role,
            title=guide.title,
            overall_score=eval_data.get("overall_score", 0.0),
            sections_count=len(guide.sections or []),
            created_at=guide.created_at,
        )
```

## Task 4: API Endpoints

### File: `backend/app/api/guides.py`

```python
import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.schemas import (
    GuideRequest, GuideResponse, GuideSummary, GuideStatus,
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
                except asyncio.TimeoutError:
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
    import time

    agents = ["role_profiler", "content_curator", "guide_generator", "quality_evaluator"]
    for agent in agents:
        await publish_event(guide_id, {
            "type": "agent_start",
            "agent": agent,
            "message": f"Starting {agent.replace('_', ' ')}...",
        })
        await asyncio.sleep(1)
        await publish_event(guide_id, {
            "type": "agent_complete",
            "agent": agent,
            "duration_ms": 1000,
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
            "evaluation": {"overall_score": 0.0, "section_evaluations": [], "generation_metadata": {}},
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    })
```

### File: `backend/app/api/evaluations.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
```

### File: `backend/app/api/products.py`

```python
from fastapi import APIRouter
from app.models.schemas import ProductListResponse, ProductInfo, UserRole

router = APIRouter()

# Static product registry for MVP
PRODUCTS = {
    "stripe": ProductInfo(
        id="stripe",
        name="Stripe",
        description="Payment processing platform for internet businesses",
        doc_count=6,
        chunk_count=0,  # Updated at runtime after ingestion
        available_roles=[
            UserRole.FRONTEND_DEVELOPER,
            UserRole.BACKEND_DEVELOPER,
            UserRole.SECURITY_ENGINEER,
            UserRole.DEVOPS_ENGINEER,
            UserRole.PRODUCT_MANAGER,
            UserRole.TEAM_LEAD,
        ],
    ),
}


@router.get("/", response_model=ProductListResponse)
async def list_products():
    return ProductListResponse(products=list(PRODUCTS.values()))


@router.get("/{product_id}", response_model=ProductInfo)
async def get_product(product_id: str):
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    return PRODUCTS[product_id]
```

## Task 5: Tests

### File: `backend/tests/test_api/test_guides.py`
- Test POST /api/guides/generate returns guide_id
- Test GET /api/guides/{id} returns 404 for unknown ID
- Test GET /api/guides/ returns empty list initially
- Test SSE endpoint sends events and terminates

### File: `backend/tests/test_api/test_products.py`
- Test GET /api/products/ returns Stripe
- Test GET /api/products/stripe returns product info
- Test GET /api/products/unknown returns 404

### File: `backend/tests/test_api/test_health.py`
- Test GET /api/health returns 200
- Test response includes model names

### File: `backend/tests/conftest.py`
Set up test fixtures:
- Test database (SQLite in-memory for speed)
- Test client (httpx AsyncClient with app)
- Override get_db dependency for tests

## Completion Criteria
- [ ] All Pydantic schemas defined with proper validation (Field constraints, enums)
- [ ] SQLAlchemy models match Pydantic schemas
- [ ] All API endpoints return correct status codes and response shapes
- [ ] SSE streaming works (test with `curl -N http://localhost:8000/api/guides/{id}/stream`)
- [ ] Placeholder pipeline sends mock SSE events through the full flow
- [ ] Guide CRUD operations work (create, get, list with filters)
- [ ] Evaluation endpoints work
- [ ] All tests pass
- [ ] FastAPI auto-docs at /docs show all endpoints with correct schemas

## Final Steps
```bash
# Add the missing import at top of guides.py
from datetime import datetime, timezone

git add -A
git commit -m "feat: complete data models, API endpoints, and SSE streaming

- Pydantic schemas for all entities (guides, evaluations, SSE events)
- SQLAlchemy models with indexes
- Full CRUD for guides and evaluations
- SSE streaming with event queue system
- Placeholder pipeline for end-to-end SSE testing
- Product registry endpoint
- API tests with async test client
- All endpoints documented in Swagger UI"
```
