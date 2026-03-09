"""Guide Generator agent node — sequentially generates guide sections via Claude."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from langchain_anthropic import ChatAnthropic

from app.agents.state import PipelineState, calculate_cost
from app.config import get_settings
from app.models.schemas import GuideSection

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "guide_generator.xml"


def _format_chunks_xml(state: PipelineState) -> str:
    """Format retrieved chunks as XML elements for the prompt."""
    lines: list[str] = []
    for chunk in state["retrieved_chunks"]:
        lines.append(
            f'<chunk id="{chunk.chunk_id}" source="{chunk.source_url}" '
            f'path="{chunk.section_path}">\n{chunk.content}\n</chunk>'
        )
    return "\n".join(lines)


def _format_previous_sections_xml(sections: list[GuideSection]) -> str:
    """Format previously generated sections for progressive complexity context."""
    if not sections:
        return "<none>This is the first section.</none>"
    lines: list[str] = []
    for s in sections:
        lines.append(
            f'<section number="{s.section_number}" title="{s.title}">\n'
            f"  <summary>{s.summary}</summary>\n"
            f"  <key_takeaways>{', '.join(s.key_takeaways)}</key_takeaways>\n"
            f"</section>"
        )
    return "\n".join(lines)


async def guide_generator_node(state: PipelineState) -> dict:
    """LangGraph node: generate guide sections sequentially (ADR-004)."""
    settings = get_settings()
    publish = state["publish_event"]
    role_profile = state["role_profile"]
    total_sections = settings.guide_sections_count

    await publish({
        "type": "agent_start",
        "agent": "guide_generator",
        "message": "Generating guide sections...",
    })

    start = time.perf_counter()
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    chunks_xml = _format_chunks_xml(state)

    llm = ChatAnthropic(
        model=settings.generation_model,
        api_key=settings.anthropic_api_key,
        max_tokens=4000,
        temperature=0.3,
    )
    llm_with_output = llm.with_structured_output(GuideSection, include_raw=True)

    # Determine which sections to generate
    sections_to_regen = state.get("sections_to_regenerate", [])
    existing_sections = list(state.get("sections", []))
    regen_count = state.get("regeneration_count", 0)

    if sections_to_regen:
        # Regeneration mode: only regenerate failing sections
        regen_count += 1
        await publish({
            "type": "regeneration_triggered",
            "sections": sections_to_regen,
            "attempt": regen_count,
        })
        section_numbers = sections_to_regen
    else:
        # Initial generation: all sections
        section_numbers = list(range(1, total_sections + 1))

    acc_tokens = 0
    acc_cost = 0.0

    for section_num in section_numbers:
        # Build context: previous sections are all sections before this one
        if sections_to_regen:
            # During regeneration, use all other existing sections as context
            previous = [s for s in existing_sections if s.section_number < section_num]
        else:
            previous = existing_sections[:section_num - 1] if existing_sections else []

        # Build regeneration feedback if applicable
        regen_feedback = ""
        if sections_to_regen:
            evals = state.get("section_evaluations", [])
            for ev in evals:
                if ev.section_number == section_num and ev.needs_regeneration:
                    suggestions = []
                    for dim in ev.dimensions:
                        if dim.score < settings.eval_threshold:
                            suggestions.extend(dim.suggestions)
                    if suggestions:
                        regen_feedback = (
                            "<regeneration_feedback>\n"
                            "This section previously failed quality evaluation. "
                            "Address these improvements:\n"
                            + "\n".join(f"- {s}" for s in suggestions)
                            + "\n</regeneration_feedback>"
                        )
                    break

        prompt = template.format(
            section_number=section_num,
            total_sections=total_sections,
            role=role_profile.role.value,
            experience_level=role_profile.experience_level.value,
            primary_concerns=", ".join(role_profile.primary_concerns),
            learning_objectives=", ".join(role_profile.learning_objectives),
            complexity_ceiling=role_profile.complexity_ceiling,
            chunks_xml=chunks_xml,
            previous_sections_xml=_format_previous_sections_xml(previous),
            regeneration_feedback=regen_feedback,
        )

        result = await llm_with_output.ainvoke(prompt)
        section: GuideSection = result["parsed"]
        raw = result["raw"]

        # Ensure section_number is correct
        section.section_number = section_num

        input_tokens = raw.usage_metadata.get("input_tokens", 0)
        output_tokens = raw.usage_metadata.get("output_tokens", 0)
        tokens, cost = calculate_cost(input_tokens, output_tokens, settings.generation_model)
        acc_tokens += tokens
        acc_cost += cost

        # Update or append section
        if sections_to_regen:
            # Replace the existing section
            replaced = False
            for i, s in enumerate(existing_sections):
                if s.section_number == section_num:
                    existing_sections[i] = section
                    replaced = True
                    break
            if not replaced:
                existing_sections.append(section)
        else:
            existing_sections.append(section)

        await publish({
            "type": "section_generated",
            "section": section.model_dump(),
            "index": section_num - 1,
        })

        logger.info("Generated section %d/%d (%d tokens)", section_num, total_sections, tokens)

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Sort sections by number
    existing_sections.sort(key=lambda s: s.section_number)

    await publish({
        "type": "agent_complete",
        "agent": "guide_generator",
        "duration_ms": round(elapsed_ms, 1),
    })

    return {
        "sections": existing_sections,
        "sections_to_regenerate": [],
        "total_tokens": acc_tokens,
        "total_cost_usd": acc_cost,
        "regeneration_count": regen_count,
    }
