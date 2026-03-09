"""Integration test: SSE infrastructure and event publishing.

Tests the SSE event queue system that underlies the pipeline.
The real LangGraph pipeline requires LLM API keys and ChromaDB,
so these tests focus on the event infrastructure.
"""

from app.api.guides import get_event_queue, publish_event


async def test_publish_event_creates_queue():
    """Publishing an event auto-creates a queue for the guide."""
    guide_id = "test-publish-001"
    await publish_event(guide_id, {"type": "test", "data": "hello"})

    queue = get_event_queue(guide_id)
    event = await queue.get()
    assert event["type"] == "test"
    assert event["data"] == "hello"


async def test_multiple_events_ordered():
    """Events are received in the order they were published."""
    guide_id = "test-ordering-001"
    await publish_event(guide_id, {"type": "agent_start", "agent": "a"})
    await publish_event(guide_id, {"type": "agent_complete", "agent": "a"})
    await publish_event(guide_id, {"type": "guide_complete"})

    queue = get_event_queue(guide_id)
    events = []
    while not queue.empty():
        events.append(await queue.get())

    assert [e["type"] for e in events] == [
        "agent_start", "agent_complete", "guide_complete",
    ]


async def test_separate_guide_queues():
    """Each guide_id gets its own independent queue."""
    await publish_event("guide-a", {"type": "a"})
    await publish_event("guide-b", {"type": "b"})

    qa = get_event_queue("guide-a")
    qb = get_event_queue("guide-b")

    ea = await qa.get()
    eb = await qb.get()
    assert ea["type"] == "a"
    assert eb["type"] == "b"
