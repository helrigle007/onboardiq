"""LangGraph pipeline assembly — wires the 4 agent nodes into a state graph."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from langgraph.graph import END, StateGraph

from app.agents.content_curator import content_curator_node
from app.agents.guide_generator import guide_generator_node
from app.agents.quality_evaluator import quality_evaluator_node
from app.agents.role_profiler import role_profiler_node
from app.agents.state import PipelineState
from app.config import get_settings
from app.models.schemas import GuideRequest

logger = logging.getLogger(__name__)


def _should_regenerate(state: PipelineState) -> str:
    """Conditional edge: regenerate failing sections or finish."""
    settings = get_settings()
    to_regen = state.get("sections_to_regenerate", [])
    regen_count = state.get("regeneration_count", 0)

    if to_regen and regen_count < settings.max_regenerations:
        logger.info(
            "Regeneration triggered: sections %s (attempt %d/%d)",
            to_regen,
            regen_count + 1,
            settings.max_regenerations,
        )
        return "guide_generator"
    return END


def build_graph() -> StateGraph:
    """Build the LangGraph state graph for the pipeline."""
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("role_profiler", role_profiler_node)
    graph.add_node("content_curator", content_curator_node)
    graph.add_node("guide_generator", guide_generator_node)
    graph.add_node("quality_evaluator", quality_evaluator_node)

    # Linear flow
    graph.set_entry_point("role_profiler")
    graph.add_edge("role_profiler", "content_curator")
    graph.add_edge("content_curator", "guide_generator")
    graph.add_edge("guide_generator", "quality_evaluator")

    # Conditional: regenerate or finish
    graph.add_conditional_edges(
        "quality_evaluator",
        _should_regenerate,
        {"guide_generator": "guide_generator", END: END},
    )

    return graph


# Compile once at module level
_compiled_graph = build_graph().compile()


async def run_pipeline(
    guide_id: str,
    request: GuideRequest,
    publish_event_fn: Callable[[dict], Awaitable[None]],
) -> PipelineState:
    """Execute the full generation pipeline and return final state."""
    initial_state: PipelineState = {
        "guide_id": guide_id,
        "request": request,
        "role_profile": None,
        "retrieved_chunks": [],
        "sections": [],
        "section_evaluations": [],
        "regeneration_count": 0,
        "sections_to_regenerate": [],
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "retrieval_latency_ms": 0.0,
        "chunks_retrieved": 0,
        "chunks_after_reranking": 0,
        "pipeline_start_time": time.time(),
        "publish_event": publish_event_fn,
    }

    logger.info("Starting pipeline for guide %s", guide_id)
    final_state = await _compiled_graph.ainvoke(initial_state)
    logger.info(
        "Pipeline complete for guide %s: %d tokens, $%.4f",
        guide_id,
        final_state.get("total_tokens", 0),
        final_state.get("total_cost_usd", 0.0),
    )

    return final_state
