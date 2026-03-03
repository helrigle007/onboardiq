"""Tests for evaluation API endpoints."""


from app.models.schemas import GuideRequest
from app.services.guide_service import GuideService


async def test_get_evaluation_returns_404_for_unknown(client):
    """GET /api/evaluations/{guide_id} returns 404 when no evaluations exist."""
    response = await client.get("/api/evaluations/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "No evaluations found"


async def test_get_evaluation_after_save(client, db_session):
    """GET /api/evaluations/{guide_id} returns saved evaluation data."""
    # Create a guide and save an evaluation
    service = GuideService(db_session)
    guide_id = await service.create_guide(
        GuideRequest(product="stripe", role="backend_developer")
    )
    await service.save_evaluation_run(
        guide_id=guide_id,
        overall_score=0.82,
        dimension_scores={"completeness": 0.9, "clarity": 0.75},
        section_scores=[{"section": 1, "score": 0.82}],
        tokens_used=2500,
        cost_usd=0.025,
        latency_seconds=6.0,
    )

    response = await client.get(f"/api/evaluations/{guide_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["guide_id"] == guide_id
    assert len(data["evaluations"]) == 1
    assert data["evaluations"][0]["overall_score"] == 0.82
    assert data["evaluations"][0]["tokens_used"] == 2500


async def test_evaluation_history_empty(client):
    """GET /api/evaluations/history/ returns empty list initially."""
    response = await client.get("/api/evaluations/history/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] == 0
    assert data["evaluations"] == []


async def test_evaluation_history_with_data(client, db_session):
    """GET /api/evaluations/history/ returns evaluation history."""
    service = GuideService(db_session)
    guide_id = await service.create_guide(
        GuideRequest(product="stripe", role="security_engineer")
    )

    # Save multiple evaluation runs
    for score in [0.7, 0.8, 0.85]:
        await service.save_evaluation_run(
            guide_id=guide_id,
            overall_score=score,
            dimension_scores={},
            section_scores=[],
            tokens_used=1000,
            cost_usd=0.01,
            latency_seconds=5.0,
        )

    response = await client.get("/api/evaluations/history/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] == 3


async def test_evaluation_history_limit(client, db_session):
    """GET /api/evaluations/history/ respects limit parameter."""
    service = GuideService(db_session)
    guide_id = await service.create_guide(
        GuideRequest(product="stripe", role="backend_developer")
    )

    for i in range(5):
        await service.save_evaluation_run(
            guide_id=guide_id,
            overall_score=0.8,
            dimension_scores={},
            section_scores=[],
            tokens_used=1000,
            cost_usd=0.01,
            latency_seconds=5.0,
        )

    response = await client.get("/api/evaluations/history/?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] == 3
