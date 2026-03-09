"""Content Curator agent node — retrieves and deduplicates documentation chunks."""

from __future__ import annotations

import asyncio
import logging
import time

from app.agents.state import PipelineState
from app.config import get_settings
from app.rag.retriever import HybridRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


async def content_curator_node(state: PipelineState) -> dict:
    """LangGraph node: retrieve relevant documentation via hybrid search."""
    settings = get_settings()
    publish = state["publish_event"]
    role_profile = state["role_profile"]

    await publish({
        "type": "agent_start",
        "agent": "content_curator",
        "message": "Retrieving relevant documentation...",
    })

    start = time.perf_counter()

    retriever = HybridRetriever(
        product=state["request"].product.value,
        final_top_k=settings.retrieval_top_k,
    )

    # Build queries from role profile topics
    queries = role_profile.relevant_doc_topics

    # Run retrievals concurrently
    tasks = [retriever.retrieve(q) for q in queries]
    results = await asyncio.gather(*tasks)

    # Deduplicate by chunk_id, keeping highest rerank_score
    seen: dict[str, RetrievedChunk] = {}
    total_raw = 0
    for chunk_list in results:
        total_raw += len(chunk_list)
        for chunk in chunk_list:
            existing = seen.get(chunk.chunk_id)
            if existing is None or (chunk.rerank_score or 0) > (existing.rerank_score or 0):
                seen[chunk.chunk_id] = chunk

    # Sort by rerank score, take top_k
    deduped = sorted(
        seen.values(),
        key=lambda c: c.rerank_score or 0.0,
        reverse=True,
    )[:settings.retrieval_top_k]

    elapsed_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "Content curator complete: %d queries → %d raw → %d deduped in %.0fms",
        len(queries),
        total_raw,
        len(deduped),
        elapsed_ms,
    )

    await publish({
        "type": "agent_complete",
        "agent": "content_curator",
        "duration_ms": round(elapsed_ms, 1),
    })

    return {
        "retrieved_chunks": deduped,
        "retrieval_latency_ms": round(elapsed_ms, 1),
        "chunks_retrieved": total_raw,
        "chunks_after_reranking": len(deduped),
    }
