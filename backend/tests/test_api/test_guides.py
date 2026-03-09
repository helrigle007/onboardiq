"""Tests for guide API endpoints."""

import json

import pytest


@pytest.mark.asyncio
async def test_generate_guide_returns_guide_id(client):
    """POST /api/guides/generate returns guide_id and status."""
    response = await client.post(
        "/api/guides/generate",
        json={
            "product": "stripe",
            "role": "backend_developer",
            "experience_level": "intermediate",
            "focus_areas": ["webhooks"],
            "tech_stack": ["python", "fastapi"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "guide_id" in data
    assert data["status"] == "generating"
    assert len(data["guide_id"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_get_guide_returns_404_for_unknown_id(client):
    """GET /api/guides/{id} returns 404 for unknown ID."""
    response = await client.get("/api/guides/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Guide not found"


@pytest.mark.asyncio
async def test_list_guides_returns_empty_initially(client):
    """GET /api/guides/ returns empty list initially."""
    response = await client.get("/api/guides/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_guides_after_creation(client):
    """GET /api/guides/ returns guides after creation."""
    await client.post(
        "/api/guides/generate",
        json={"product": "stripe", "role": "frontend_developer"},
    )
    response = await client.get("/api/guides/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["product"] == "stripe"
    assert data[0]["role"] == "frontend_developer"


@pytest.mark.asyncio
async def test_list_guides_filter_by_product(client):
    """GET /api/guides/?product=stripe filters correctly."""
    await client.post(
        "/api/guides/generate",
        json={"product": "stripe", "role": "backend_developer"},
    )
    response = await client.get("/api/guides/?product=stripe")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(g["product"] == "stripe" for g in data)


@pytest.mark.asyncio
async def test_sse_stream_sends_events(client):
    """SSE endpoint sends agent events and terminates on guide_complete."""
    # Start generation
    gen_response = await client.post(
        "/api/guides/generate",
        json={"product": "stripe", "role": "security_engineer"},
    )
    guide_id = gen_response.json()["guide_id"]

    # Stream events — collect all SSE data lines
    import asyncio

    # Give the background task time to start producing events
    await asyncio.sleep(0.5)

    events = []
    async with client.stream("GET", f"/api/guides/{guide_id}/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event_data = json.loads(line[6:])
                events.append(event_data)
                if event_data.get("type") in ("guide_complete", "error"):
                    break

    # Verify we got a terminal event (error is expected without LLM/DB services)
    event_types = [e["type"] for e in events]
    assert event_types[-1] in ("guide_complete", "error")


@pytest.mark.asyncio
async def test_generate_guide_validates_product(client):
    """POST /api/guides/generate rejects invalid product."""
    response = await client.post(
        "/api/guides/generate",
        json={"product": "invalid_product", "role": "backend_developer"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_guide_validates_role(client):
    """POST /api/guides/generate rejects invalid role."""
    response = await client.post(
        "/api/guides/generate",
        json={"product": "stripe", "role": "invalid_role"},
    )
    assert response.status_code == 422
