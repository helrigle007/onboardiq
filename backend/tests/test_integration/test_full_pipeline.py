"""Integration test: Full placeholder pipeline from request to completed guide.

Tests the placeholder pipeline end-to-end. The real LangGraph pipeline
(Phase 2) is not yet implemented, so this tests the placeholder flow
which verifies the SSE infrastructure and guide creation work together.
"""

import asyncio
import json

from app.api.guides import _placeholder_pipeline, get_event_queue, publish_event
from app.models.schemas import GuideRequest


async def test_placeholder_pipeline_emits_all_agents():
    """Placeholder pipeline emits start+complete for all 4 agents."""
    guide_id = "test-pipeline-001"
    request = GuideRequest(
        product="stripe",
        role="security_engineer",
        experience_level="intermediate",
        focus_areas=["API security"],
        tech_stack=["Python"],
    )

    queue = get_event_queue(guide_id)
    await _placeholder_pipeline(guide_id, request)

    events = []
    while not queue.empty():
        events.append(await queue.get())

    event_types = [e["type"] for e in events]
    agents_started = [e["agent"] for e in events if e["type"] == "agent_start"]
    agents_completed = [e["agent"] for e in events if e["type"] == "agent_complete"]

    expected_agents = ["role_profiler", "content_curator", "guide_generator", "quality_evaluator"]
    assert agents_started == expected_agents
    assert agents_completed == expected_agents
    assert event_types[-1] == "guide_complete"


async def test_placeholder_pipeline_guide_complete_has_correct_data():
    """The guide_complete event has correct product, role, and structure."""
    guide_id = "test-pipeline-002"
    request = GuideRequest(
        product="stripe",
        role="backend_developer",
        experience_level="beginner",
    )

    queue = get_event_queue(guide_id)
    await _placeholder_pipeline(guide_id, request)

    events = []
    while not queue.empty():
        events.append(await queue.get())

    final = next(e for e in events if e["type"] == "guide_complete")
    guide = final["guide"]
    assert guide["id"] == guide_id
    assert guide["product"] == "stripe"
    assert guide["role"] == "backend_developer"
    assert "evaluation" in guide
    assert "metadata" in guide
    assert "created_at" in guide


async def test_placeholder_pipeline_event_count():
    """Placeholder pipeline emits exactly 9 events (4 start + 4 complete + 1 guide_complete)."""
    guide_id = "test-pipeline-003"
    request = GuideRequest(product="stripe", role="devops_engineer")

    queue = get_event_queue(guide_id)
    await _placeholder_pipeline(guide_id, request)

    events = []
    while not queue.empty():
        events.append(await queue.get())

    assert len(events) == 9


async def test_publish_event_creates_queue():
    """Publishing an event auto-creates a queue for the guide."""
    guide_id = "test-publish-001"
    await publish_event(guide_id, {"type": "test", "data": "hello"})

    queue = get_event_queue(guide_id)
    event = await queue.get()
    assert event["type"] == "test"
    assert event["data"] == "hello"


async def test_full_api_pipeline_flow(client):
    """POST /generate → GET /stream captures all events end-to-end."""
    # Start generation
    response = await client.post("/api/guides/generate", json={
        "product": "stripe",
        "role": "frontend_developer",
        "experience_level": "intermediate",
        "focus_areas": [],
        "tech_stack": ["React"],
    })
    assert response.status_code == 200
    guide_id = response.json()["guide_id"]

    # Wait for background task
    await asyncio.sleep(0.5)

    # Collect events
    events = []
    async with client.stream("GET", f"/api/guides/{guide_id}/stream") as stream:
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                events.append(event)
                if event["type"] in ("guide_complete", "error"):
                    break

    # 4 agent_start + 4 agent_complete + 1 guide_complete = 9
    non_keepalive = [e for e in events if e["type"] != "keepalive"]
    assert len(non_keepalive) == 9

    # Guide data in the final event
    final = non_keepalive[-1]
    assert final["type"] == "guide_complete"
    assert final["guide"]["id"] == guide_id
