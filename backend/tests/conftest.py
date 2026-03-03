"""Shared test fixtures — SQLite in-memory DB, mock Claude, sample data."""

import os

# Set required env vars before any app imports that trigger Settings()
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database import get_db
from app.models.database import Base
from app.models.schemas import (
    Citation,
    CodeExample,
    DimensionScore,
    GenerationMetadata,
    GuideEvaluation,
    GuideResponse,
    GuideSection,
    SectionEvaluation,
)

# SQLite in-memory async engine for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# ── 5 evaluation dimensions ──────────────────────────────────────────
EVAL_DIMENSIONS = [
    "completeness",
    "role_relevance",
    "actionability",
    "clarity",
    "progressive_complexity",
]


# ── Database fixtures ────────────────────────────────────────────────


@pytest.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(engine, db_session) -> AsyncGenerator[AsyncClient, None]:
    from app.main import create_app

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Sample data fixtures ─────────────────────────────────────────────


def _make_guide_section(section_number: int) -> dict:
    """Build a sample GuideSection dict for testing."""
    return GuideSection(
        section_number=section_number,
        title=f"Section {section_number}: Test Topic",
        summary=f"This section covers topic {section_number}.",
        content=f"# Section {section_number}\n\nDetailed content here.",
        key_takeaways=[f"Takeaway {i}" for i in range(1, 4)],
        code_examples=[
            CodeExample(
                language="python",
                code=f"print('section {section_number}')",
                description="Example code",
            )
        ],
        warnings=["Watch out for rate limits"],
        citations=[
            Citation(
                source_url="https://docs.stripe.com/test",
                source_title="Test Doc",
                chunk_id=f"chunk-{section_number}",
                relevance_score=0.9,
            )
        ],
        estimated_time_minutes=15,
        prerequisites=[],
    ).model_dump()


def _make_section_evaluation(section_number: int, score: float = 0.85) -> dict:
    """Build a sample SectionEvaluation dict."""
    return SectionEvaluation(
        section_number=section_number,
        overall_score=score,
        dimensions=[
            DimensionScore(
                dimension=dim,
                score=score,
                reasoning=f"Good {dim}",
                suggestions=[],
            )
            for dim in EVAL_DIMENSIONS
        ],
        pass_threshold=score >= 0.7,
        needs_regeneration=score < 0.7,
    ).model_dump()


@pytest.fixture
def sample_sections() -> list[dict]:
    """6 sample guide sections as dicts."""
    return [_make_guide_section(i) for i in range(1, 7)]


@pytest.fixture
def sample_evaluation(sample_sections: list[dict]) -> dict:
    """Sample GuideEvaluation dict with 6 section evaluations."""
    section_evals = [_make_section_evaluation(i) for i in range(1, 7)]
    return GuideEvaluation(
        guide_id="test-guide-id",
        overall_score=0.85,
        section_evaluations=section_evals,
        generation_metadata=GenerationMetadata(
            model="claude-sonnet-4-20250514",
            total_tokens_used=5000,
            total_cost_usd=0.05,
            generation_time_seconds=12.5,
            retrieval_latency_ms=350.0,
            chunks_retrieved=20,
            chunks_after_reranking=10,
            regeneration_count=0,
        ),
    ).model_dump()


@pytest.fixture
def sample_metadata() -> dict:
    """Sample GenerationMetadata dict."""
    return GenerationMetadata(
        model="claude-sonnet-4-20250514",
        total_tokens_used=5000,
        total_cost_usd=0.05,
        generation_time_seconds=12.5,
        retrieval_latency_ms=350.0,
        chunks_retrieved=20,
        chunks_after_reranking=10,
        regeneration_count=0,
    ).model_dump()


@pytest.fixture
def sample_guide_response(
    sample_sections: list[dict],
    sample_evaluation: dict,
    sample_metadata: dict,
) -> dict:
    """Complete GuideResponse dict with 6 sections and evaluation."""
    return GuideResponse(
        id="test-guide-id",
        product="stripe",
        role="security_engineer",
        title="Stripe Onboarding: Security Engineer",
        description="Complete onboarding guide for security engineers.",
        sections=sample_sections,
        evaluation=sample_evaluation,
        metadata=sample_metadata,
        created_at=datetime.now(UTC),
    ).model_dump()
