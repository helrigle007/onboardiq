# Phase 2 — Terminal 2: Agents (Guide Generator + Quality Evaluator)

## Overview
You are building the second half of the LangGraph pipeline: the Guide Generator agent (produces structured guide sections from retrieved chunks) and the Quality Evaluator agent (LLM-as-judge that scores sections and triggers regeneration). The Quality Evaluator is the **portfolio centerpiece**.

## Pre-flight
```bash
cd ~/onboardiq
git checkout main
git pull
git checkout -b agents/generator-evaluator
```

## Context
- State schema is in `backend/app/agents/state.py` (built by T1)
- Graph definition is in `backend/app/agents/graph.py` (built by T1)
- Schemas: `GuideSection`, `SectionEvaluation`, `DimensionScore` in `backend/app/models/schemas.py`
- Chunks arrive in `state["reranked_chunks"]` tagged with `assigned_section`
- Section outlines are in `state["section_outlines"]` with title, focus, prerequisites
- Use XML prompts in `backend/app/agents/prompts/`
- Claude model: `settings.generation_model` (claude-sonnet-4-20250514)

## Task 1: Guide Generator Agent

### File: `backend/app/agents/prompts/guide_generator.xml`

```xml
<s>
You are a technical writer creating a personalized SaaS onboarding guide section.
You write clear, actionable content grounded EXCLUSIVELY in the provided
documentation chunks. Never fabricate information not present in the sources.
Every claim must be traceable to a source chunk.

Respond with ONLY valid JSON matching the GuideSection schema.
No markdown wrapping, no preamble.
</s>

<context>
Product: {product}
User Role: {role} ({experience_level})
Tech Stack: {tech_stack}
</context>

<section_spec>
Section {section_number} of {total_sections}
Title: {section_title}
Focus: {section_focus}
Previous sections covered: {previous_sections}
Prerequisites: {prerequisites}
Target complexity: {target_complexity}
</section_spec>

<source_documentation>
{relevant_chunks}
</source_documentation>

<schema>
{{
  "section_number": {section_number},
  "title": "{section_title}",
  "summary": "2-3 sentence overview of this section",
  "content": "Full markdown content. Use ## for sub-headings, ```language for code blocks, > for callouts.",
  "key_takeaways": ["3-5 actionable takeaways"],
  "code_examples": [
    {{
      "language": "python",
      "code": "# Actual working code snippet",
      "description": "What this code demonstrates"
    }}
  ],
  "warnings": ["Common pitfalls specific to this role"],
  "citations": [
    {{
      "source_url": "URL from chunk metadata",
      "source_title": "Document title",
      "chunk_id": "chunk identifier",
      "relevance_score": 0.95
    }}
  ],
  "estimated_time_minutes": 15,
  "prerequisites": ["What the reader should know first"]
}}
</schema>

<rules>
1. Write for a {experience_level} {role}. Adjust jargon and depth accordingly.
2. Code examples MUST use {tech_stack} when specified. Default to Python if unspecified.
3. Every factual statement must come from the source chunks. Add citations.
4. Include at least 1 code example and 1 warning per section.
5. The "content" field uses markdown. Structure with sub-headings (##).
6. Build on concepts from previous sections. Don't repeat what was covered.
7. Estimated time: beginner=20-30min, intermediate=10-20min, advanced=5-15min per section.
8. Warnings should be role-specific:
   - Security Engineer: security implications, compliance risks
   - Backend Developer: error handling, rate limits, idempotency
   - Frontend Developer: client-side pitfalls, UX considerations
   - DevOps: deployment concerns, scaling, monitoring gaps
</rules>
```

### File: `backend/app/agents/guide_generator.py`

```python
"""
Guide Generator Agent — third node in the OnboardIQ pipeline.

Generates structured guide sections one at a time, sequentially, so each
section can reference and build on previous ones (progressive complexity).

Design decision (ADR-004): Sequential over parallel generation.
Parallel would be ~3x faster but can't enforce progressive complexity.
SSE streaming mitigates perceived latency — users see sections as they complete.
"""

import time
import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from app.agents.state import OnboardIQState
from app.models.schemas import GuideSection
from app.config import get_settings


PROMPT_PATH = Path(__file__).parent / "prompts" / "guide_generator.xml"


async def _emit_event(state: OnboardIQState, event: dict):
    callback = state.get("event_callback")
    if callback and callable(callback):
        await callback(state["guide_id"], event)


async def guide_generator_node(state: OnboardIQState) -> dict:
    """
    Generate guide sections sequentially with progressive context.
    
    On first run: generate all sections.
    On regeneration: only regenerate sections in sections_needing_regen.
    
    Reads: section_outlines, reranked_chunks, role_profile, sections_needing_regen
    Writes: guide_sections, total_tokens, total_cost
    """
    settings = get_settings()
    start = time.time()
    is_regen = bool(state.get("sections_needing_regen"))

    await _emit_event(state, {
        "type": "agent_start",
        "agent": "guide_generator",
        "message": "Regenerating failed sections..." if is_regen
                   else "Generating personalized guide sections...",
    })

    prompt_template = PROMPT_PATH.read_text()
    llm = ChatAnthropic(
        model=settings.generation_model,
        temperature=0.3,  # Slightly creative for prose quality
        max_tokens=4000,
        api_key=settings.anthropic_api_key,
    )

    outlines = state.get("section_outlines", [])
    chunks = state.get("reranked_chunks", [])
    profile = state.get("role_profile", {})

    # Start with existing sections (for regen, keep the ones that passed)
    existing_sections = state.get("guide_sections", [])
    if is_regen:
        sections_to_generate = state["sections_needing_regen"]
        guide_sections = [
            s for s in existing_sections
            if s["section_number"] not in sections_to_generate
        ]
    else:
        sections_to_generate = [o["section_number"] for o in outlines]
        guide_sections = []

    total_tokens = state.get("total_tokens", 0)
    total_cost = state.get("total_cost", 0.0)

    for outline in outlines:
        sec_num = outline["section_number"]
        if sec_num not in sections_to_generate:
            continue

        # Gather chunks assigned to this section
        section_chunks = [
            c for c in chunks
            if c.get("assigned_section") == sec_num
        ]

        # Format chunks for prompt
        formatted_chunks = _format_chunks(section_chunks)

        # Get summaries of previous sections for progressive context
        previous = [
            f"- Section {s['section_number']}: {s['title']} — {s.get('summary', '')}"
            for s in sorted(guide_sections, key=lambda x: x["section_number"])
            if s["section_number"] < sec_num
        ]

        prompt = prompt_template.format(
            product=state["product"],
            role=state["role"],
            experience_level=state["experience_level"],
            tech_stack=", ".join(state.get("tech_stack", [])) or "Python",
            section_number=sec_num,
            total_sections=len(outlines),
            section_title=outline["title"],
            section_focus=outline.get("focus", ""),
            previous_sections="\n".join(previous) if previous else "None (this is the first section)",
            prerequisites=", ".join(outline.get("prerequisites", [])) or "None",
            target_complexity=outline.get("target_complexity", "hands-on"),
            relevant_chunks=formatted_chunks,
        )

        response = await llm.ainvoke(prompt)
        content = response.content
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            section = GuideSection.model_validate_json(content)
        except Exception as e:
            # Fallback: create minimal section on parse failure
            section = GuideSection(
                section_number=sec_num,
                title=outline["title"],
                summary=f"Failed to generate: {str(e)[:100]}",
                content="Generation error — see evaluation for details.",
                key_takeaways=[],
                estimated_time_minutes=10,
            )

        guide_sections.append(section.model_dump())

        # Track tokens
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens = response.usage_metadata.get("total_tokens", 0)
            total_tokens += tokens
            # Approximate cost: Sonnet input=$3/MTok, output=$15/MTok
            input_tok = response.usage_metadata.get("input_tokens", 0)
            output_tok = response.usage_metadata.get("output_tokens", 0)
            total_cost += (input_tok * 3 + output_tok * 15) / 1_000_000

        # Emit section as it's generated
        await _emit_event(state, {
            "type": "section_generated",
            "section": section.model_dump(),
            "index": sec_num - 1,
        })

    # Sort sections by number
    guide_sections.sort(key=lambda s: s["section_number"])

    duration_ms = (time.time() - start) * 1000

    await _emit_event(state, {
        "type": "agent_complete",
        "agent": "guide_generator",
        "duration_ms": duration_ms,
    })

    return {
        "guide_sections": guide_sections,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "step_timings": {**state.get("step_timings", {}), "guide_generator": duration_ms},
    }


def _format_chunks(chunks: list[dict]) -> str:
    """Format chunks for inclusion in the generation prompt."""
    formatted = []
    for i, chunk in enumerate(chunks[:15]):  # Limit to 15 chunks per section
        source = chunk.get("source_url", "unknown")
        section = chunk.get("section_path", "")
        content = chunk.get("content", chunk.get("original_content", ""))
        score = chunk.get("rerank_score", chunk.get("vector_score", 0))
        formatted.append(
            f"<chunk id=\"{chunk.get('chunk_id', i)}\" source=\"{source}\" "
            f"section=\"{section}\" relevance=\"{score:.2f}\">\n"
            f"{content}\n</chunk>"
        )
    return "\n\n".join(formatted)
```

## Task 2: Quality Evaluator Agent (Portfolio Centerpiece)

### File: `backend/app/agents/prompts/quality_evaluator.xml`

```xml
<s>
You are a rigorous quality evaluator for technical onboarding guides.
You score each guide section across 5 dimensions using structured rubrics.
Be critical but fair — a score of 0.75+ should indicate genuinely good content.

Respond with ONLY valid JSON matching the SectionEvaluation schema.
No markdown, no preamble.
</s>

<evaluation_context>
Product: {product}
Target Role: {role} ({experience_level})
This is Section {section_number}: "{section_title}"
</evaluation_context>

<section_content>
{section_content}
</section_content>

<source_chunks>
{source_chunks}
</source_chunks>

<previous_sections>
{previous_section_summaries}
</previous_sections>

<rubrics>
COMPLETENESS (Does the section cover all necessary sub-topics?):
  1.0: Covers all expected sub-topics with appropriate depth
  0.75: Covers most sub-topics, minor gaps
  0.5: Missing significant sub-topics
  0.25: Major gaps in coverage
  0.0: Fails to address the topic meaningfully

ROLE_RELEVANCE (Is content tailored to {role}, not generic?):
  1.0: Deeply role-specific examples, concerns, and language
  0.75: Mostly role-relevant with minor generic content
  0.5: Mix of role-specific and generic content
  0.25: Mostly generic, could apply to any role
  0.0: Completely generic, no role adaptation

ACTIONABILITY (Can the user take concrete action?):
  1.0: Clear step-by-step actions, runnable code, specific configurations
  0.75: Mostly actionable with some vague steps
  0.5: Mix of actionable and conceptual-only content
  0.25: Mostly conceptual, few concrete actions
  0.0: Purely theoretical, no actionable guidance

CLARITY (Is writing clear and experience-level-appropriate?):
  1.0: Exceptionally clear, well-organized, appropriate complexity
  0.75: Clear with minor organizational issues
  0.5: Some confusing passages or poor structure
  0.25: Frequently unclear or poorly organized
  0.0: Incomprehensible or completely mismatched complexity

PROGRESSIVE_COMPLEXITY (Does it build on previous sections?):
  1.0: Perfectly scaffolded, builds naturally on prior knowledge
  0.75: Good progression with minor jumps
  0.5: Some concepts introduced without adequate foundation
  0.25: Poor scaffolding, assumes knowledge not yet covered
  0.0: No relationship to learning progression
</rubrics>

<schema>
{{
  "section_number": {section_number},
  "overall_score": 0.85,
  "dimensions": [
    {{
      "dimension": "completeness",
      "score": 0.75,
      "reasoning": "Quote specific passages. Explain score.",
      "suggestions": ["1-2 specific improvements"]
    }},
    {{
      "dimension": "role_relevance",
      "score": 0.9,
      "reasoning": "...",
      "suggestions": ["..."]
    }},
    {{
      "dimension": "actionability",
      "score": 0.85,
      "reasoning": "...",
      "suggestions": ["..."]
    }},
    {{
      "dimension": "clarity",
      "score": 0.8,
      "reasoning": "...",
      "suggestions": ["..."]
    }},
    {{
      "dimension": "progressive_complexity",
      "score": 0.85,
      "reasoning": "...",
      "suggestions": ["..."]
    }}
  ],
  "pass_threshold": true,
  "needs_regeneration": false
}}
</schema>

<rules>
1. Use the EXACT rubric values: 0.0, 0.25, 0.5, 0.75, 1.0 for each dimension.
2. overall_score = mean of all 5 dimension scores.
3. needs_regeneration = true if overall_score < {eval_threshold}.
4. pass_threshold = overall_score >= {eval_threshold}.
5. Be especially critical of role_relevance. Generic content MUST score ≤0.5.
6. Check citations — content not supported by source chunks is a faithfulness issue.
7. For progressive_complexity on Section 1, score based on appropriate starting point.
8. reasoning must quote or reference specific parts of the section content.
</rules>
```

### File: `backend/app/agents/quality_evaluator.py`

```python
"""
Quality Evaluator Agent — fourth node in the OnboardIQ pipeline.
This is the PORTFOLIO CENTERPIECE.

Implements a 5-dimension LLM-as-judge evaluation:
  1. Completeness
  2. Role Relevance
  3. Actionability
  4. Clarity
  5. Progressive Complexity

Sections scoring below threshold trigger regeneration via the conditional
edge in the LangGraph. Max regeneration attempts bounded by settings.

This pattern mirrors production evaluation systems at DoorDash (guardrails +
LLM judge) and Uber (multi-dimension quality scoring).
"""

import time
import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from app.agents.state import OnboardIQState
from app.models.schemas import SectionEvaluation, DimensionScore, GuideResponse, GenerationMetadata
from app.config import get_settings


PROMPT_PATH = Path(__file__).parent / "prompts" / "quality_evaluator.xml"


async def _emit_event(state: OnboardIQState, event: dict):
    callback = state.get("event_callback")
    if callback and callable(callback):
        await callback(state["guide_id"], event)


async def quality_evaluator_node(state: OnboardIQState) -> dict:
    """
    Evaluate each guide section across 5 dimensions.
    
    After evaluation:
    - If all sections pass → emit guide_complete, return with empty sections_needing_regen
    - If some fail → emit regeneration_triggered, return with failed section numbers
    
    Reads: guide_sections, reranked_chunks, role_profile
    Writes: section_evaluations, overall_score, sections_needing_regen, regeneration_count
    """
    settings = get_settings()
    start = time.time()

    await _emit_event(state, {
        "type": "agent_start",
        "agent": "quality_evaluator",
        "message": "Evaluating guide quality across 5 dimensions...",
    })

    prompt_template = PROMPT_PATH.read_text()
    llm = ChatAnthropic(
        model=settings.evaluation_model,
        temperature=0,  # Deterministic evaluation
        max_tokens=3000,
        api_key=settings.anthropic_api_key,
    )

    sections = state.get("guide_sections", [])
    chunks = state.get("reranked_chunks", [])
    evaluations = []
    total_tokens = state.get("total_tokens", 0)
    total_cost = state.get("total_cost", 0.0)

    for section in sections:
        sec_num = section["section_number"]

        # Get source chunks for this section
        section_chunks = [
            c for c in chunks
            if c.get("assigned_section") == sec_num
        ]

        # Get previous section summaries
        prev_summaries = [
            f"Section {s['section_number']}: {s['title']} — {s.get('summary', '')}"
            for s in sections
            if s["section_number"] < sec_num
        ]

        prompt = prompt_template.format(
            product=state["product"],
            role=state["role"],
            experience_level=state["experience_level"],
            section_number=sec_num,
            section_title=section["title"],
            section_content=json.dumps(section, indent=2)[:4000],  # Truncate if huge
            source_chunks=_format_chunks_for_eval(section_chunks),
            previous_section_summaries="\n".join(prev_summaries) or "None (first section)",
            eval_threshold=settings.eval_threshold,
        )

        response = await llm.ainvoke(prompt)
        content = response.content
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            evaluation = SectionEvaluation.model_validate_json(content)
        except Exception as e:
            # Fallback: mark as needing regeneration on parse failure
            evaluation = SectionEvaluation(
                section_number=sec_num,
                overall_score=0.0,
                dimensions=[
                    DimensionScore(
                        dimension="evaluation_error",
                        score=0.0,
                        reasoning=f"Evaluation parse failed: {str(e)[:200]}",
                        suggestions=["Regenerate this section"],
                    )
                ],
                pass_threshold=False,
                needs_regeneration=True,
            )

        evaluations.append(evaluation.model_dump())

        # Track tokens
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens = response.usage_metadata.get("total_tokens", 0)
            total_tokens += tokens
            input_tok = response.usage_metadata.get("input_tokens", 0)
            output_tok = response.usage_metadata.get("output_tokens", 0)
            total_cost += (input_tok * 3 + output_tok * 15) / 1_000_000

        # Emit per-section evaluation
        await _emit_event(state, {
            "type": "section_evaluated",
            "evaluation": evaluation.model_dump(),
            "index": sec_num - 1,
        })

    # Calculate overall score
    if evaluations:
        overall_score = sum(e["overall_score"] for e in evaluations) / len(evaluations)
    else:
        overall_score = 0.0

    # Determine which sections need regeneration
    failed_sections = [
        e["section_number"]
        for e in evaluations
        if e.get("needs_regeneration", False)
    ]

    regen_count = state.get("regeneration_count", 0)
    if failed_sections:
        regen_count += 1

    duration_ms = (time.time() - start) * 1000

    await _emit_event(state, {
        "type": "agent_complete",
        "agent": "quality_evaluator",
        "duration_ms": duration_ms,
    })

    # If sections failed and we can still regen, emit regen event
    if failed_sections and regen_count <= state.get("max_regenerations", 2):
        await _emit_event(state, {
            "type": "regeneration_triggered",
            "sections": failed_sections,
            "attempt": regen_count,
        })
    else:
        # Build and emit final guide
        guide_response = _build_guide_response(state, sections, evaluations, overall_score, total_tokens, total_cost)
        await _emit_event(state, {
            "type": "guide_complete",
            "guide": guide_response,
        })

    return {
        "section_evaluations": evaluations,
        "overall_score": overall_score,
        "sections_needing_regen": failed_sections if regen_count <= state.get("max_regenerations", 2) else [],
        "regeneration_count": regen_count,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "step_timings": {**state.get("step_timings", {}), "quality_evaluator": duration_ms},
    }


def _format_chunks_for_eval(chunks: list[dict]) -> str:
    """Format source chunks for the evaluation prompt."""
    formatted = []
    for chunk in chunks[:10]:
        formatted.append(
            f"[Source: {chunk.get('source_url', 'unknown')}] "
            f"{chunk.get('content', '')[:500]}"
        )
    return "\n---\n".join(formatted) if formatted else "No source chunks available."


def _build_guide_response(
    state: dict,
    sections: list[dict],
    evaluations: list[dict],
    overall_score: float,
    total_tokens: int,
    total_cost: float,
) -> dict:
    """Build the final GuideResponse dict for the SSE event."""
    import time
    from datetime import datetime, timezone

    metadata = {
        "model": get_settings().generation_model,
        "total_tokens_used": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "generation_time_seconds": round(time.time() - state.get("generation_start_time", time.time()), 2),
        "retrieval_latency_ms": round(state.get("retrieval_latency_ms", 0), 2),
        "chunks_retrieved": len(state.get("retrieved_chunks", [])),
        "chunks_after_reranking": len(state.get("reranked_chunks", [])),
        "regeneration_count": state.get("regeneration_count", 0),
        "langsmith_trace_url": None,
    }

    return {
        "id": state["guide_id"],
        "product": state["product"],
        "role": state["role"],
        "title": f"{state['product'].title()} Onboarding: {state['role'].replace('_', ' ').title()}",
        "description": f"Personalized {state['experience_level']} guide for {state['role'].replace('_', ' ')}s",
        "sections": sections,
        "evaluation": {
            "guide_id": state["guide_id"],
            "overall_score": round(overall_score, 3),
            "section_evaluations": evaluations,
            "generation_metadata": metadata,
        },
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
```

## Task 3: Tests

### File: `backend/tests/test_agents/test_guide_generator.py`
- Test _format_chunks produces valid XML chunk format
- Test section generation with mocked Claude response
- Test fallback on JSON parse failure
- Test regeneration only generates failed sections

### File: `backend/tests/test_agents/test_quality_evaluator.py`
- Test evaluation produces valid SectionEvaluation
- Test overall_score is mean of dimensions
- Test needs_regeneration triggers when score < threshold
- Test sections_needing_regen correctly identified
- Test _build_guide_response produces valid structure

## Completion Criteria
- [ ] Guide Generator produces valid GuideSection JSON for each section
- [ ] Sections are generated sequentially with progressive context
- [ ] Code examples use the user's tech stack
- [ ] Quality Evaluator scores all 5 dimensions per section
- [ ] Sections below threshold are flagged for regeneration
- [ ] SSE events fire: section_generated, section_evaluated, regeneration_triggered, guide_complete
- [ ] Full pipeline runs end-to-end: request → profile → curate → generate → evaluate → (regen?) → complete
- [ ] Tests pass

## Final Steps
```bash
git add -A
git commit -m "feat: Guide Generator and Quality Evaluator agents

- Guide Generator: sequential section generation with progressive context
- Quality Evaluator: 5-dimension LLM-as-judge (completeness, role_relevance,
  actionability, clarity, progressive_complexity)
- Structured rubrics with threshold-based regeneration routing
- SSE events for section_generated, section_evaluated, guide_complete
- Token and cost tracking across all agent calls
- Fallback handling for JSON parse failures
- Unit tests for both agents"
```
