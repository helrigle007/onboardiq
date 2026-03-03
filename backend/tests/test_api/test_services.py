"""Tests for the GuideService business logic layer."""

from sqlalchemy import select

from app.models.database import Guide
from app.models.schemas import GuideRequest
from app.services.guide_service import GuideService


async def test_create_guide_returns_uuid(db_session):
    """create_guide returns a valid UUID string."""
    service = GuideService(db_session)
    guide_id = await service.create_guide(
        GuideRequest(product="stripe", role="backend_developer")
    )
    assert len(guide_id) == 36  # UUID format
    assert "-" in guide_id


async def test_create_guide_title_format(db_session):
    """Guide title follows 'Product Onboarding: Role' format."""
    service = GuideService(db_session)
    guide_id = await service.create_guide(
        GuideRequest(product="stripe", role="security_engineer")
    )
    result = await db_session.execute(select(Guide).where(Guide.id == guide_id))
    guide = result.scalar_one()
    assert guide.title == "Stripe Onboarding: Security Engineer"


async def test_create_guide_default_status_pending(db_session):
    """New guides start with status 'pending'."""
    service = GuideService(db_session)
    guide_id = await service.create_guide(
        GuideRequest(product="stripe", role="backend_developer")
    )
    result = await db_session.execute(select(Guide).where(Guide.id == guide_id))
    guide = result.scalar_one()
    assert guide.status == "pending"


async def test_get_guide_none_for_missing(db_session):
    """get_guide returns None for non-existent ID."""
    service = GuideService(db_session)
    assert await service.get_guide("does-not-exist") is None


async def test_list_guides_returns_all(db_session):
    """list_guides returns all created guides."""
    service = GuideService(db_session)

    ids = set()
    for role in ["backend_developer", "frontend_developer", "security_engineer"]:
        gid = await service.create_guide(
            GuideRequest(product="stripe", role=role)
        )
        ids.add(gid)

    results = await service.list_guides()
    assert len(results) == 3
    assert {r.id for r in results} == ids


async def test_save_guide_result_updates_status(db_session):
    """save_guide_result sets status to 'complete'."""
    service = GuideService(db_session)
    guide_id = await service.create_guide(
        GuideRequest(product="stripe", role="backend_developer")
    )

    await service.save_guide_result(
        guide_id=guide_id,
        sections=[{"section_number": 1, "title": "Test"}],
        evaluation={"overall_score": 0.8},
        metadata={"model": "test"},
    )

    result = await db_session.execute(select(Guide).where(Guide.id == guide_id))
    guide = result.scalar_one()
    assert guide.status == "complete"
    assert guide.sections == [{"section_number": 1, "title": "Test"}]


async def test_save_guide_result_nonexistent_guide(db_session):
    """save_guide_result on non-existent guide is a no-op."""
    service = GuideService(db_session)
    # Should not raise
    await service.save_guide_result(
        guide_id="nonexistent",
        sections=[],
        evaluation={},
        metadata={},
    )


async def test_save_evaluation_run_returns_id(db_session):
    """save_evaluation_run returns the evaluation run ID."""
    service = GuideService(db_session)
    guide_id = await service.create_guide(
        GuideRequest(product="stripe", role="backend_developer")
    )

    eval_id = await service.save_evaluation_run(
        guide_id=guide_id,
        overall_score=0.9,
        dimension_scores={"completeness": 0.9},
        section_scores=[],
        tokens_used=1000,
        cost_usd=0.01,
        latency_seconds=3.0,
    )
    assert len(eval_id) == 36  # UUID


async def test_to_summary_default_score(db_session):
    """Guide summary defaults to 0.0 score when no evaluation exists."""
    service = GuideService(db_session)
    await service.create_guide(
        GuideRequest(product="stripe", role="backend_developer")
    )

    summaries = await service.list_guides()
    assert summaries[0].overall_score == 0.0
    assert summaries[0].sections_count == 0
