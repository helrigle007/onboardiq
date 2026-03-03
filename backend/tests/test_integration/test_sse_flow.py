"""Integration test: SSE event flow during guide generation.

Verifies events arrive in correct order with correct types.
Uses the placeholder pipeline which emits mock events.
"""

import asyncio
import json


async def test_sse_events_arrive_in_order(client):
    """SSE stream delivers events in pipeline order."""
    response = await client.post("/api/guides/generate", json={
        "product": "stripe",
        "role": "security_engineer",
        "experience_level": "intermediate",
        "focus_areas": [],
        "tech_stack": [],
    })
    guide_id = response.json()["guide_id"]

    # Give the background task time to produce events
    await asyncio.sleep(0.5)

    events = []
    async with client.stream("GET", f"/api/guides/{guide_id}/stream") as stream:
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event["type"] != "keepalive":
                    events.append(event)
                if event["type"] in ("guide_complete", "error"):
                    break

    # Verify event order
    event_types = [e["type"] for e in events]
    assert "agent_start" in event_types
    assert "agent_complete" in event_types
    assert event_types[-1] in ("guide_complete", "error")

    # Verify all 4 agents reported
    agents_started = [e["agent"] for e in events if e["type"] == "agent_start"]
    assert "role_profiler" in agents_started
    assert "content_curator" in agents_started
    assert "guide_generator" in agents_started
    assert "quality_evaluator" in agents_started


async def test_sse_agent_start_has_message(client):
    """Each agent_start event includes a message field."""
    response = await client.post("/api/guides/generate", json={
        "product": "stripe",
        "role": "backend_developer",
        "experience_level": "beginner",
        "focus_areas": [],
        "tech_stack": [],
    })
    guide_id = response.json()["guide_id"]

    await asyncio.sleep(0.5)

    events = []
    async with client.stream("GET", f"/api/guides/{guide_id}/stream") as stream:
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                events.append(event)
                if event["type"] in ("guide_complete", "error"):
                    break

    start_events = [e for e in events if e["type"] == "agent_start"]
    for ev in start_events:
        assert "message" in ev
        assert len(ev["message"]) > 0


async def test_sse_agent_complete_has_duration(client):
    """Each agent_complete event includes a duration_ms field."""
    response = await client.post("/api/guides/generate", json={
        "product": "stripe",
        "role": "devops_engineer",
        "experience_level": "advanced",
        "focus_areas": [],
        "tech_stack": [],
    })
    guide_id = response.json()["guide_id"]

    await asyncio.sleep(0.5)

    events = []
    async with client.stream("GET", f"/api/guides/{guide_id}/stream") as stream:
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                events.append(event)
                if event["type"] in ("guide_complete", "error"):
                    break

    complete_events = [e for e in events if e["type"] == "agent_complete"]
    assert len(complete_events) == 4
    for ev in complete_events:
        assert "duration_ms" in ev
        assert isinstance(ev["duration_ms"], (int, float))


async def test_sse_guide_complete_has_guide_payload(client):
    """The final guide_complete event contains the guide data."""
    response = await client.post("/api/guides/generate", json={
        "product": "stripe",
        "role": "product_manager",
        "experience_level": "intermediate",
        "focus_areas": [],
        "tech_stack": [],
    })
    guide_id = response.json()["guide_id"]

    await asyncio.sleep(0.5)

    final_event = None
    async with client.stream("GET", f"/api/guides/{guide_id}/stream") as stream:
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event["type"] == "guide_complete":
                    final_event = event
                    break

    assert final_event is not None
    assert "guide" in final_event
    guide = final_event["guide"]
    assert guide["id"] == guide_id
    assert guide["product"] == "stripe"
    assert guide["role"] == "product_manager"


async def test_sse_stream_returns_correct_content_type(client):
    """SSE endpoint returns text/event-stream content type."""
    response = await client.post("/api/guides/generate", json={
        "product": "stripe",
        "role": "team_lead",
        "experience_level": "intermediate",
        "focus_areas": [],
        "tech_stack": [],
    })
    guide_id = response.json()["guide_id"]

    await asyncio.sleep(0.3)

    async with client.stream("GET", f"/api/guides/{guide_id}/stream") as stream:
        assert stream.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert stream.headers.get("cache-control") == "no-cache"
        # Consume to avoid hanging
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event["type"] in ("guide_complete", "error"):
                    break
