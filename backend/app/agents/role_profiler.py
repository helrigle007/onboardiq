"""Role Profiler agent node — analyzes the user's role to create a tailored profile."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from langchain_anthropic import ChatAnthropic

from app.agents.state import PipelineState, calculate_cost
from app.config import get_settings
from app.models.schemas import RoleProfile

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "role_profiler.xml"


async def role_profiler_node(state: PipelineState) -> dict:
    """LangGraph node: profile the user's role for tailored content."""
    settings = get_settings()
    publish = state["publish_event"]
    request = state["request"]

    await publish({
        "type": "agent_start",
        "agent": "role_profiler",
        "message": "Analyzing role and creating learning profile...",
    })

    start = time.perf_counter()

    # Format prompt
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.format(
        product=request.product.value,
        role=request.role.value,
        experience_level=request.experience_level.value,
        focus_areas=", ".join(request.focus_areas) if request.focus_areas else "none specified",
        tech_stack=", ".join(request.tech_stack) if request.tech_stack else "not specified",
    )

    # Call LLM with structured output
    llm = ChatAnthropic(
        model=settings.fast_model,
        api_key=settings.anthropic_api_key,
        max_tokens=1000,
        temperature=0.0,
    )
    llm_with_output = llm.with_structured_output(RoleProfile, include_raw=True)
    result = await llm_with_output.ainvoke(prompt)

    profile: RoleProfile = result["parsed"]
    raw = result["raw"]

    # Track tokens
    input_tokens = raw.usage_metadata.get("input_tokens", 0)
    output_tokens = raw.usage_metadata.get("output_tokens", 0)
    tokens, cost = calculate_cost(input_tokens, output_tokens, settings.fast_model)

    elapsed_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "Role profiler complete: %s/%s — %d topics, %d tokens",
        profile.role.value,
        profile.experience_level.value,
        len(profile.relevant_doc_topics),
        tokens,
    )

    await publish({
        "type": "agent_complete",
        "agent": "role_profiler",
        "duration_ms": round(elapsed_ms, 1),
    })

    return {
        "role_profile": profile,
        "total_tokens": tokens,
        "total_cost_usd": cost,
    }
