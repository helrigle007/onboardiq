# Phase 2 — Terminal 1: LangGraph Agents (Role Profiler + Content Curator)

## Overview
You are building the first half of the LangGraph agent pipeline: the state schema, graph definition, Role Profiler agent, and Content Curator agent. Terminal 2 builds the second half (Generator + Evaluator). Your graph definition must include ALL 4 nodes — stub the ones T2 implements.

## Pre-flight
```bash
cd ~/onboardiq
git checkout main              # should have all Phase 1 merged
git pull
git checkout -b agents/role-profiler-curator
```

## Context
- Models/schemas are in `backend/app/models/schemas.py` — use RoleProfile, GuideSection, etc. from there
- RAG retriever is in `backend/app/rag/retriever.py` — import HybridRetriever
- Config is in `backend/app/config.py` — use get_settings()
- Claude models: generation=claude-sonnet-4-20250514, fast=claude-haiku-4-5-20251001
- Use XML-structured prompts (Claude was trained on them)
- All prompts live in `backend/app/agents/prompts/` as .xml files

## Task 1: LangGraph State Schema

### File: `backend/app/agents/state.py`

```python
"""
OnboardIQ LangGraph state schema.

This TypedDict defines the complete state that flows through the agent pipeline.
Each agent node reads from and writes to specific fields.

Data flow:
  Input → Role Profiler → Content Curator → Guide Generator → Quality Evaluator → (loop or done)
"""

from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class OnboardIQState(TypedDict):
    # ── Input (set once at pipeline start) ──────────────────────
    product: str
    role: str
    experience_level: str
    focus_areas: list[str]
    tech_stack: list[str]
    guide_id: str

    # ── Role Profiler output ────────────────────────────────────
    role_profile: Optional[dict]            # RoleProfile.model_dump()

    # ── Content Curator output ──────────────────────────────────
    retrieved_chunks: list[dict]            # All chunks from hybrid retrieval
    reranked_chunks: list[dict]             # After reranking + filtering
    section_outlines: list[dict]            # Planned sections with assigned chunks

    # ── Guide Generator output ──────────────────────────────────
    guide_sections: list[dict]              # List of GuideSection.model_dump()

    # ── Quality Evaluator output ────────────────────────────────
    section_evaluations: list[dict]         # List of SectionEvaluation.model_dump()
    overall_score: float

    # ── Control flow ────────────────────────────────────────────
    current_section_index: int
    regeneration_count: int
    max_regenerations: int                  # From settings, default 2
    sections_needing_regen: list[int]       # Section numbers that failed eval

    # ── Metrics tracking ────────────────────────────────────────
    total_tokens: int
    total_cost: float
    retrieval_latency_ms: float
    generation_start_time: float
    step_timings: dict                      # {agent_name: duration_ms}

    # ── SSE callback ────────────────────────────────────────────
    event_callback: Optional[object]        # Callable for SSE events (not serialized)

    # ── Messages (for LangGraph internals) ──────────────────────
    messages: Annotated[list, add_messages]
```

## Task 2: Graph Definition

### File: `backend/app/agents/graph.py`

```python
"""
OnboardIQ LangGraph pipeline.

Graph structure:
  START → role_profiler → content_curator → guide_generator → quality_evaluator
                                    ↑                                    │
                                    └────── regenerate (if score < 0.7) ─┘
                                                                         │
                                                                    END (if pass)
"""

import time
from langgraph.graph import StateGraph, END
from app.agents.state import OnboardIQState
from app.agents.role_profiler import role_profiler_node
from app.agents.content_curator import content_curator_node
from app.agents.guide_generator import guide_generator_node
from app.agents.quality_evaluator import quality_evaluator_node
from app.config import get_settings


def should_regenerate(state: OnboardIQState) -> str:
    """
    Conditional edge after quality_evaluator.
    Routes to 'regenerate' if any sections scored below threshold
    and we haven't hit max regeneration attempts.
    Routes to 'done' otherwise.
    """
    sections_to_redo = state.get("sections_needing_regen", [])
    regen_count = state.get("regeneration_count", 0)
    max_regen = state.get("max_regenerations", 2)

    if not sections_to_redo:
        return "done"
    if regen_count >= max_regen:
        return "done"  # Accept what we have
    return "regenerate"


def build_graph() -> StateGraph:
    """Build and compile the OnboardIQ agent graph."""
    graph = StateGraph(OnboardIQState)

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

    # Conditional: evaluate → done or → re-curate for failed sections
    graph.add_conditional_edges(
        "quality_evaluator",
        should_regenerate,
        {
            "done": END,
            "regenerate": "content_curator",
        },
    )

    return graph.compile()


async def run_pipeline(guide_id: str, request_dict: dict, event_callback=None) -> OnboardIQState:
    """
    Execute the full pipeline for a guide generation request.
    
    Args:
        guide_id: Unique guide identifier
        request_dict: GuideRequest as dict
        event_callback: async callable for SSE events
    
    Returns:
        Final state with all agent outputs
    """
    settings = get_settings()
    
    initial_state: OnboardIQState = {
        "product": request_dict["product"],
        "role": request_dict["role"],
        "experience_level": request_dict.get("experience_level", "intermediate"),
        "focus_areas": request_dict.get("focus_areas", []),
        "tech_stack": request_dict.get("tech_stack", []),
        "guide_id": guide_id,
        "role_profile": None,
        "retrieved_chunks": [],
        "reranked_chunks": [],
        "section_outlines": [],
        "guide_sections": [],
        "section_evaluations": [],
        "overall_score": 0.0,
        "current_section_index": 0,
        "regeneration_count": 0,
        "max_regenerations": settings.max_regenerations,
        "sections_needing_regen": [],
        "total_tokens": 0,
        "total_cost": 0.0,
        "retrieval_latency_ms": 0.0,
        "generation_start_time": time.time(),
        "step_timings": {},
        "event_callback": event_callback,
        "messages": [],
    }

    graph = build_graph()
    final_state = await graph.ainvoke(initial_state)
    return final_state
```

## Task 3: Role Profiler Agent

### File: `backend/app/agents/prompts/role_profiler.xml`

```xml
<system>
You are an expert SaaS onboarding strategist. You analyze a user's role,
experience level, and target product to create a detailed profile that
drives personalized onboarding guide generation.

You must respond with ONLY valid JSON matching the RoleProfile schema.
No markdown, no explanation, no preamble — just the JSON object.
</system>

<task>
Create a RoleProfile for the following user:

Product: {product}
Role: {role}
Experience Level: {experience_level}
Focus Areas: {focus_areas}
Tech Stack: {tech_stack}
</task>

<schema>
{{
  "role": "{role}",
  "experience_level": "{experience_level}",
  "primary_concerns": ["string", "...5 items, specific to this product+role"],
  "relevant_doc_topics": ["string", "...8-12 items, terms that appear in actual docs"],
  "excluded_topics": ["string", "...3-5 topics irrelevant to this role"],
  "learning_objectives": ["string", "...4-6 items, each starts with action verb"],
  "complexity_ceiling": "conceptual|hands-on|deep-dive"
}}
</schema>

<rules>
1. primary_concerns must be specific to {product}, not generic.
   BAD: "security" GOOD: "Stripe API key rotation and restricted key scoping"
2. relevant_doc_topics should use terminology from {product}'s actual documentation.
3. excluded_topics prevents retrieval of irrelevant content.
   Example: Security Engineer excludes "marketing integrations", "UI customization"
4. learning_objectives start with action verbs: "Configure...", "Implement...", "Audit..."
5. complexity_ceiling maps from experience_level:
   beginner → "conceptual", intermediate → "hands-on", advanced → "deep-dive"
</rules>
```

### File: `backend/app/agents/role_profiler.py`

```python
"""
Role Profiler Agent — first node in the OnboardIQ pipeline.

Analyzes user context (role, experience, product) and generates a structured
RoleProfile that drives all downstream retrieval and generation decisions.

This is the "intelligence" that makes outputs role-adaptive rather than generic.
"""

import time
import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from app.agents.state import OnboardIQState
from app.models.schemas import RoleProfile
from app.config import get_settings


PROMPT_PATH = Path(__file__).parent / "prompts" / "role_profiler.xml"


async def _emit_event(state: OnboardIQState, event: dict):
    """Emit SSE event if callback is available."""
    callback = state.get("event_callback")
    if callback and callable(callback):
        await callback(state["guide_id"], event)


async def role_profiler_node(state: OnboardIQState) -> dict:
    """
    Generate a RoleProfile from user input.
    
    Reads: product, role, experience_level, focus_areas, tech_stack
    Writes: role_profile, total_tokens, total_cost, step_timings
    """
    settings = get_settings()
    start = time.time()

    await _emit_event(state, {
        "type": "agent_start",
        "agent": "role_profiler",
        "message": f"Analyzing {state['role'].replace('_', ' ')} role for {state['product']}...",
    })

    # Load and format prompt
    prompt_template = PROMPT_PATH.read_text()
    prompt = prompt_template.format(
        product=state["product"],
        role=state["role"],
        experience_level=state["experience_level"],
        focus_areas=", ".join(state.get("focus_areas", [])) or "None specified",
        tech_stack=", ".join(state.get("tech_stack", [])) or "Not specified",
    )

    # Call Claude
    llm = ChatAnthropic(
        model=settings.generation_model,
        temperature=0,
        max_tokens=2000,
        api_key=settings.anthropic_api_key,
    )

    response = await llm.ainvoke(prompt)

    # Parse and validate
    content = response.content
    # Handle potential markdown code fences
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    
    profile = RoleProfile.model_validate_json(content)

    # Track metrics
    tokens_used = response.usage_metadata.get("total_tokens", 0) if hasattr(response, 'usage_metadata') and response.usage_metadata else 0
    duration_ms = (time.time() - start) * 1000

    await _emit_event(state, {
        "type": "agent_complete",
        "agent": "role_profiler",
        "duration_ms": duration_ms,
    })

    return {
        "role_profile": profile.model_dump(),
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
        "step_timings": {**state.get("step_timings", {}), "role_profiler": duration_ms},
    }
```

## Task 4: Content Curator Agent

### File: `backend/app/agents/prompts/content_curator.xml`

```xml
<system>
You are a documentation content curator. Given a role profile and product,
you plan the optimal section structure for an onboarding guide, then assign
the most relevant documentation chunks to each section.

Respond with ONLY valid JSON. No markdown, no explanation.
</system>

<task>
Plan a {sections_count}-section onboarding guide for:

Product: {product}
Role: {role}
Experience Level: {experience_level}
Learning Objectives: {learning_objectives}
Primary Concerns: {primary_concerns}
Complexity Ceiling: {complexity_ceiling}
</task>

<schema>
{{
  "sections": [
    {{
      "section_number": 1,
      "title": "Section title",
      "focus": "What this section should cover",
      "retrieval_queries": ["query1", "query2", "query3"],
      "target_complexity": "conceptual|hands-on|deep-dive",
      "prerequisites": ["section titles this depends on"]
    }}
  ]
}}
</schema>

<rules>
1. Order sections by progressive complexity — start simple, build up.
2. Section 1 is always a platform overview tailored to this role's perspective.
3. Each section's retrieval_queries should be 3-5 specific search terms
   that will find the right documentation chunks.
4. Avoid overlap between sections — each section covers distinct ground.
5. The final section should cover monitoring, troubleshooting, or next steps.
6. For {experience_level}:
   - beginner: more conceptual sections, fewer deep-dive
   - intermediate: balanced mix
   - advanced: skip basics, focus on edge cases, optimization, best practices
</rules>
```

### File: `backend/app/agents/content_curator.py`

```python
"""
Content Curator Agent — second node in the OnboardIQ pipeline.

Uses the RoleProfile to:
1. Plan guide section structure (via Claude)
2. Execute targeted hybrid retrieval per section
3. Rerank and filter chunks by role relevance
4. Assign chunks to sections

On regeneration loops, only re-retrieves for sections that failed evaluation.
"""

import time
import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from app.agents.state import OnboardIQState
from app.rag.retriever import HybridRetriever
from app.config import get_settings


PROMPT_PATH = Path(__file__).parent / "prompts" / "content_curator.xml"


async def _emit_event(state: OnboardIQState, event: dict):
    callback = state.get("event_callback")
    if callback and callable(callback):
        await callback(state["guide_id"], event)


async def content_curator_node(state: OnboardIQState) -> dict:
    """
    Plan sections and retrieve relevant documentation.
    
    On first run: plan all sections, retrieve for all.
    On regeneration: only re-retrieve for failed sections.
    
    Reads: role_profile, product, sections_needing_regen
    Writes: reranked_chunks, section_outlines, retrieval_latency_ms
    """
    settings = get_settings()
    start = time.time()
    profile = state["role_profile"]
    is_regen = bool(state.get("sections_needing_regen"))

    await _emit_event(state, {
        "type": "agent_start",
        "agent": "content_curator",
        "message": "Re-retrieving for failed sections..." if is_regen
                   else "Planning guide structure and retrieving documentation...",
    })

    # Step 1: Plan sections (skip on regeneration — reuse existing outlines)
    if not is_regen:
        section_outlines = await _plan_sections(state, settings)
    else:
        section_outlines = state.get("section_outlines", [])

    # Step 2: Determine which sections need retrieval
    if is_regen:
        sections_to_retrieve = [
            s for s in section_outlines
            if s["section_number"] in state["sections_needing_regen"]
        ]
    else:
        sections_to_retrieve = section_outlines

    # Step 3: Retrieve chunks for each section
    retriever = HybridRetriever(
        product=state["product"],
        final_top_k=settings.retrieval_top_k,
    )

    all_chunks = state.get("reranked_chunks", []) if is_regen else []
    retrieval_start = time.time()

    for section in sections_to_retrieve:
        section_chunks = []
        for query in section.get("retrieval_queries", []):
            chunks = await retriever.retrieve(query)
            section_chunks.extend([c.model_dump() if hasattr(c, 'model_dump') else c for c in chunks])

        # Deduplicate
        seen_ids = set()
        unique = []
        for chunk in section_chunks:
            cid = chunk.get("chunk_id", chunk.get("content", "")[:50])
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique.append(chunk)

        # Tag chunks with their target section
        for chunk in unique:
            chunk["assigned_section"] = section["section_number"]

        # Replace chunks for regen sections, append for new
        if is_regen:
            all_chunks = [
                c for c in all_chunks
                if c.get("assigned_section") != section["section_number"]
            ] + unique
        else:
            all_chunks.extend(unique)

    retrieval_latency = (time.time() - retrieval_start) * 1000
    duration_ms = (time.time() - start) * 1000

    await _emit_event(state, {
        "type": "agent_complete",
        "agent": "content_curator",
        "duration_ms": duration_ms,
    })

    return {
        "section_outlines": section_outlines,
        "reranked_chunks": all_chunks,
        "retrieval_latency_ms": retrieval_latency,
        "step_timings": {**state.get("step_timings", {}), "content_curator": duration_ms},
    }


async def _plan_sections(state: OnboardIQState, settings) -> list[dict]:
    """Use Claude to plan the guide section structure."""
    profile = state["role_profile"]

    prompt_template = PROMPT_PATH.read_text()
    prompt = prompt_template.format(
        product=state["product"],
        role=state["role"],
        experience_level=state["experience_level"],
        sections_count=settings.guide_sections_count,
        learning_objectives="\n".join(f"- {obj}" for obj in profile.get("learning_objectives", [])),
        primary_concerns="\n".join(f"- {c}" for c in profile.get("primary_concerns", [])),
        complexity_ceiling=profile.get("complexity_ceiling", "hands-on"),
    )

    llm = ChatAnthropic(
        model=settings.fast_model,  # Use Haiku for planning (fast + cheap)
        temperature=0,
        max_tokens=2000,
        api_key=settings.anthropic_api_key,
    )

    response = await llm.ainvoke(prompt)
    content = response.content
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]

    plan = json.loads(content)
    return plan.get("sections", plan) if isinstance(plan, dict) else plan
```

## Task 5: Integration with API Layer

### File: Update `backend/app/api/guides.py`

Replace the `_placeholder_pipeline` function with a real pipeline invocation:

```python
from app.agents.graph import run_pipeline
from app.services.guide_service import GuideService

async def _run_guide_pipeline(guide_id: str, request_dict: dict):
    """Run the LangGraph pipeline and save results."""
    from app.infrastructure.database import async_session_factory
    
    async def event_callback(gid: str, event: dict):
        await publish_event(gid, event)
    
    try:
        # Run pipeline
        final_state = await run_pipeline(guide_id, request_dict, event_callback)
        
        # Save to database
        async with async_session_factory() as db:
            service = GuideService(db)
            await service.save_guide_result(
                guide_id=guide_id,
                sections=final_state.get("guide_sections", []),
                evaluation={
                    "guide_id": guide_id,
                    "overall_score": final_state.get("overall_score", 0.0),
                    "section_evaluations": final_state.get("section_evaluations", []),
                    "generation_metadata": _build_metadata(final_state),
                },
                metadata=_build_metadata(final_state),
            )
        
        # Emit completion
        # (The quality_evaluator node should emit guide_complete,
        #  but this is a safety net)
    except Exception as e:
        await publish_event(guide_id, {
            "type": "error",
            "message": str(e),
            "recoverable": False,
        })


def _build_metadata(state: dict) -> dict:
    import time
    return {
        "model": get_settings().generation_model,
        "total_tokens_used": state.get("total_tokens", 0),
        "total_cost_usd": state.get("total_cost", 0.0),
        "generation_time_seconds": time.time() - state.get("generation_start_time", time.time()),
        "retrieval_latency_ms": state.get("retrieval_latency_ms", 0.0),
        "chunks_retrieved": len(state.get("retrieved_chunks", [])),
        "chunks_after_reranking": len(state.get("reranked_chunks", [])),
        "regeneration_count": state.get("regeneration_count", 0),
        "langsmith_trace_url": None,
    }
```

Update the `generate_guide` endpoint to call `_run_guide_pipeline` instead of `_placeholder_pipeline`.

## Task 6: Tests

### File: `backend/tests/test_agents/test_role_profiler.py`
- Test that role_profiler_node produces a valid RoleProfile
- Test that different roles produce different profiles (security vs frontend)
- Test that experience_level affects complexity_ceiling
- Mock the Claude API call with a fixture

### File: `backend/tests/test_agents/test_graph.py`
- Test that the graph compiles without errors
- Test should_regenerate routing logic
- Test initial state setup in run_pipeline

## Completion Criteria
- [ ] LangGraph state schema covers all fields needed by all 4 agents
- [ ] Graph compiles and routes correctly (linear + conditional regeneration)
- [ ] Role Profiler generates valid, role-specific RoleProfile JSON
- [ ] Content Curator plans sections and retrieves relevant chunks per section
- [ ] On regeneration, only failed sections are re-retrieved
- [ ] SSE events fire for agent_start and agent_complete
- [ ] API integration calls real pipeline (replacing placeholder)
- [ ] Tests pass

## Final Steps
```bash
git add -A
git commit -m "feat: LangGraph pipeline with Role Profiler and Content Curator agents

- OnboardIQState TypedDict with full field schema
- StateGraph with 4 nodes and conditional regeneration routing
- Role Profiler: XML prompt → Claude → validated RoleProfile
- Content Curator: section planning + targeted hybrid retrieval
- SSE event emission from agent nodes
- API integration replacing placeholder pipeline
- Unit tests for profiler and graph routing"
```
