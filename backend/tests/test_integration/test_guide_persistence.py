"""Integration test: Guide data persistence through the full lifecycle."""


from sqlalchemy import select

from app.models.database import EvaluationRun, Guide
from app.models.schemas import GuideRequest, GuideStatus
from app.services.guide_service import GuideService


async def test_guide_created_with_correct_fields(db_session):
    """Guide record is created with all expected fields."""
    service = GuideService(db_session)
    request = GuideRequest(
        product="stripe",
        role="security_engineer",
        experience_level="intermediate",
        focus_areas=["API security"],
        tech_stack=["Python"],
    )
    guide_id = await service.create_guide(request)

    result = await db_session.execute(select(Guide).where(Guide.id == guide_id))
    guide = result.scalar_one()

    assert guide.product == "stripe"
    assert guide.role == "security_engineer"
    assert guide.experience_level == "intermediate"
    assert guide.status == "pending"
    assert guide.focus_areas == ["API security"]
    assert guide.tech_stack == ["Python"]
    assert "Security Engineer" in guide.title


async def test_guide_status_update(db_session):
    """Guide status can be updated through the lifecycle."""
    service = GuideService(db_session)
    request = GuideRequest(product="stripe", role="backend_developer")
    guide_id = await service.create_guide(request)

    # Transition through statuses
    for status in [GuideStatus.GENERATING, GuideStatus.EVALUATING, GuideStatus.COMPLETE]:
        await service.update_guide_status(guide_id, status)
        result = await db_session.execute(select(Guide).where(Guide.id == guide_id))
        guide = result.scalar_one()
        assert guide.status == status.value


async def test_guide_result_saved(db_session, sample_sections, sample_evaluation, sample_metadata):
    """Completed guide data is persisted correctly."""
    service = GuideService(db_session)
    request = GuideRequest(product="stripe", role="frontend_developer")
    guide_id = await service.create_guide(request)

    await service.save_guide_result(
        guide_id=guide_id,
        sections=sample_sections,
        evaluation=sample_evaluation,
        metadata=sample_metadata,
    )

    result = await db_session.execute(select(Guide).where(Guide.id == guide_id))
    guide = result.scalar_one()

    assert guide.status == "complete"
    assert len(guide.sections) == 6
    assert guide.evaluation["overall_score"] == 0.85
    assert guide.generation_metadata["total_tokens_used"] == 5000


async def test_guide_list_with_filters(db_session):
    """Guide listing supports product and role filters."""
    service = GuideService(db_session)

    # Create guides with different roles
    await service.create_guide(GuideRequest(product="stripe", role="security_engineer"))
    await service.create_guide(GuideRequest(product="stripe", role="backend_developer"))
    await service.create_guide(GuideRequest(product="stripe", role="frontend_developer"))

    # Filter by role
    results = await service.list_guides(role="security_engineer")
    assert len(results) == 1
    assert results[0].role == "security_engineer"

    # Filter by product
    results = await service.list_guides(product="stripe")
    assert len(results) == 3

    # No filter — returns all
    results = await service.list_guides()
    assert len(results) == 3


async def test_guide_list_respects_limit(db_session):
    """Guide listing respects the limit parameter."""
    service = GuideService(db_session)
    for _ in range(5):
        await service.create_guide(GuideRequest(product="stripe", role="backend_developer"))

    results = await service.list_guides(limit=3)
    assert len(results) == 3


async def test_evaluation_run_saved(db_session):
    """Evaluation run is persisted with all metrics."""
    service = GuideService(db_session)
    request = GuideRequest(product="stripe", role="backend_developer")
    guide_id = await service.create_guide(request)

    eval_id = await service.save_evaluation_run(
        guide_id=guide_id,
        overall_score=0.85,
        dimension_scores={"completeness": 0.9, "clarity": 0.8},
        section_scores=[{"section": 1, "score": 0.85}],
        tokens_used=3000,
        cost_usd=0.03,
        latency_seconds=8.5,
    )

    result = await db_session.execute(
        select(EvaluationRun).where(EvaluationRun.id == eval_id)
    )
    run = result.scalar_one()

    assert run.guide_id == guide_id
    assert run.overall_score == 0.85
    assert run.tokens_used == 3000
    assert run.cost_usd == 0.03
    assert run.run_type == "generation"


async def test_get_guide_returns_none_for_missing(db_session):
    """Getting a non-existent guide returns None."""
    service = GuideService(db_session)
    result = await service.get_guide("nonexistent-id")
    assert result is None


async def test_update_status_nonexistent_guide(db_session):
    """Updating status of non-existent guide is a no-op."""
    service = GuideService(db_session)
    # Should not raise
    await service.update_guide_status("nonexistent-id", GuideStatus.COMPLETE)


async def test_guide_roundtrip_via_api(
    client, db_session, sample_sections, sample_evaluation, sample_metadata,
):
    """Guide can be created via API and retrieved with full data."""
    # Create via API
    response = await client.post("/api/guides/generate", json={
        "product": "stripe",
        "role": "security_engineer",
        "experience_level": "advanced",
        "focus_areas": ["webhooks"],
        "tech_stack": ["Python", "FastAPI"],
    })
    assert response.status_code == 200
    guide_id = response.json()["guide_id"]

    # Save result directly via service
    service = GuideService(db_session)
    await service.save_guide_result(
        guide_id=guide_id,
        sections=sample_sections,
        evaluation=sample_evaluation,
        metadata=sample_metadata,
    )

    # Retrieve via API
    response = await client.get(f"/api/guides/{guide_id}")
    assert response.status_code == 200
    guide = response.json()
    assert guide["id"] == guide_id
    assert guide["product"] == "stripe"
    assert guide["role"] == "security_engineer"
    assert len(guide["sections"]) == 6


async def test_guide_list_via_api_with_filters(client):
    """API list endpoint supports query parameter filters."""
    # Create two guides with different roles
    await client.post("/api/guides/generate", json={
        "product": "stripe", "role": "security_engineer",
    })
    await client.post("/api/guides/generate", json={
        "product": "stripe", "role": "backend_developer",
    })

    # Filter by role
    response = await client.get("/api/guides/?role=security_engineer")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["role"] == "security_engineer"
