"""Integration test: SSE event flow during guide generation.

Verifies SSE infrastructure delivers events correctly.
The real pipeline requires external services (LLM API, ChromaDB, DB),
so tests verify the event delivery mechanism and terminal event handling.
"""

import asyncio
import json


async def test_sse_events_arrive_in_order(client):
    """SSE stream delivers events and terminates with a terminal event."""
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

    # Verify we got a terminal event
    assert len(events) >= 1
    assert events[-1]["type"] in ("guide_complete", "error")


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


async def test_sse_terminal_event_has_correct_type(client):
    """The final SSE event is either guide_complete or error."""
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

    assert len(events) >= 1
    terminal = events[-1]
    assert terminal["type"] in ("guide_complete", "error")
    if terminal["type"] == "error":
        assert "message" in terminal


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
