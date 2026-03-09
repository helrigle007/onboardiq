"""Quality Evaluator agent node — runs LLM-as-judge on each section."""

from __future__ import annotations

import logging
import time

from app.agents.state import PipelineState
from app.evaluation.llm_judge import LLMJudge
from app.models.schemas import SectionEvaluation

logger = logging.getLogger(__name__)


async def quality_evaluator_node(state: PipelineState) -> dict:
    """LangGraph node: evaluate all sections via the LLM judge."""
    publish = state["publish_event"]
    role_profile = state["role_profile"]
    sections = state["sections"]

    await publish({
        "type": "agent_start",
        "agent": "quality_evaluator",
        "message": "Evaluating guide quality across 5 dimensions...",
    })

    start = time.perf_counter()
    judge = LLMJudge()

    evaluations: list[SectionEvaluation] = []
    sections_to_regenerate: list[int] = []
    acc_tokens = 0
    acc_cost = 0.0

    for section in sections:
        evaluation, tokens, cost = await judge.evaluate_section(
            section=section,
            role_profile=role_profile,
            all_sections=sections,
        )
        evaluations.append(evaluation)
        acc_tokens += tokens
        acc_cost += cost

        if evaluation.needs_regeneration:
            sections_to_regenerate.append(section.section_number)

        await publish({
            "type": "section_evaluated",
            "evaluation": evaluation.model_dump(),
            "index": section.section_number - 1,
        })

        logger.info(
            "Section %d: %.3f (%s)",
            section.section_number,
            evaluation.overall_score,
            "PASS" if evaluation.pass_threshold else "FAIL",
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    await publish({
        "type": "agent_complete",
        "agent": "quality_evaluator",
        "duration_ms": round(elapsed_ms, 1),
    })

    return {
        "section_evaluations": evaluations,
        "sections_to_regenerate": sections_to_regenerate,
        "total_tokens": acc_tokens,
        "total_cost_usd": acc_cost,
    }
