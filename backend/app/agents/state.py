"""LangGraph pipeline state definition with reducer annotations."""

from __future__ import annotations

import operator
from collections.abc import Awaitable, Callable
from typing import Annotated

from typing_extensions import TypedDict

from app.models.schemas import (
    GuideRequest,
    GuideSection,
    RoleProfile,
    SectionEvaluation,
)
from app.rag.retriever import RetrievedChunk

# ── Price table (per 1M tokens) ─────────────────────────────────────
_PRICING: dict[str, tuple[float, float]] = {
    # model-prefix: (input_$/1M, output_$/1M)
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-4": (0.80, 4.00),
}


def calculate_cost(
    input_tokens: int, output_tokens: int, model: str
) -> tuple[int, float]:
    """Return (total_tokens, cost_usd) for a single LLM call."""
    total = input_tokens + output_tokens
    # Match the longest prefix
    rate = (3.00, 15.00)  # default to sonnet pricing
    for prefix, prices in _PRICING.items():
        if model.startswith(prefix):
            rate = prices
            break
    cost = (input_tokens * rate[0] + output_tokens * rate[1]) / 1_000_000
    return total, cost


class PipelineState(TypedDict, total=False):
    """Full state flowing through the LangGraph pipeline."""

    guide_id: str
    request: GuideRequest
    role_profile: RoleProfile | None
    retrieved_chunks: list[RetrievedChunk]
    sections: list[GuideSection]
    section_evaluations: list[SectionEvaluation]
    regeneration_count: int
    sections_to_regenerate: list[int]
    total_tokens: Annotated[int, operator.add]
    total_cost_usd: Annotated[float, operator.add]
    retrieval_latency_ms: float
    chunks_retrieved: int
    chunks_after_reranking: int
    pipeline_start_time: float
    publish_event: Callable[[dict], Awaitable[None]]
