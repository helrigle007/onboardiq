# Phase 2 — Terminal 3: Evaluation Pipeline

## Overview
You are building the offline evaluation layer: RAGAS integration for RAG-specific metrics, the golden evaluation dataset, metrics logging, and the evaluation script that runs in CI. This complements the real-time LLM-as-judge (built by T2) with rigorous, reproducible offline metrics.

## Pre-flight
```bash
cd ~/onboardiq
git checkout main && git pull
git checkout -b feat/evaluation-pipeline
```

## Task 1: Golden Dataset

### File: `backend/app/evaluation/golden_dataset.json`

Create 50+ evaluation entries for Stripe across multiple roles. Each entry tests whether the RAG pipeline retrieves the right content and the generator produces faithful, role-appropriate output.

Structure:
```json
{
  "version": "1.0",
  "product": "stripe",
  "created_at": "2025-01-01",
  "entries": [
    {
      "id": "stripe-sec-001",
      "role": "security_engineer",
      "experience_level": "intermediate",
      "query": "How should I configure API key rotation for production?",
      "expected_topics": ["restricted keys", "key rotation", "webhook signing secrets"],
      "expected_source_files": ["authentication.md", "security.md"],
      "ground_truth": "Stripe supports restricted API keys with granular permissions scoped to specific API resources. Production deployments should use restricted keys with minimum necessary permissions. Keys should be rotated regularly. Webhook signing secrets should be rotated independently using the rolling secret feature.",
      "role_specific_requirements": [
        "Must mention least-privilege principle for key scoping",
        "Must include key permission configuration",
        "Should NOT include basic SDK installation steps"
      ],
      "difficulty": "medium"
    }
  ]
}
```

Create entries across these categories (aim for ~10 per category):

**Security Engineer (12 entries):**
- API key management and rotation
- PCI compliance requirements
- Webhook signature verification
- Fraud prevention configuration
- Audit logging and monitoring
- Data encryption and TLS

**Backend Developer (12 entries):**
- Payment intent creation flow
- Error handling and retry strategies
- Webhook endpoint implementation
- Idempotency key usage
- SDK initialization and configuration
- Rate limiting and pagination

**Frontend Developer (8 entries):**
- Stripe.js integration
- Elements UI component setup
- Client-side error handling
- PCI compliance for client-side
- Payment form implementation

**DevOps Engineer (8 entries):**
- Webhook endpoint scaling
- API key secret management
- Monitoring and alerting setup
- Deployment best practices

**Product Manager (5 entries):**
- Payment flow overview
- Feature comparison and selection
- Pricing and billing concepts

**Team Lead (5 entries):**
- Team access management
- Integration planning overview
- Security review checklist

Each entry should have a well-written `ground_truth` of 2-4 sentences that captures the key information a correct answer should contain.

## Task 2: RAGAS Evaluation Runner

### File: `backend/app/evaluation/ragas_eval.py`

```python
"""
RAGAS evaluation runner for OnboardIQ.

Measures four key RAG metrics:
- Faithfulness: Is the answer grounded in retrieved context?
- Answer Relevancy: Does the answer address the question?
- Context Precision: Are the retrieved chunks relevant to the question?
- Context Recall: Did retrieval find all necessary information?

Usage:
  python -m app.evaluation.ragas_eval --product stripe --role security_engineer
  python -m app.evaluation.ragas_eval --all  # Run full dataset
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset

from app.rag.retriever import HybridRetriever
from app.config import get_settings


GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


def load_golden_dataset(
    role: str | None = None,
    difficulty: str | None = None,
) -> list[dict]:
    """Load and optionally filter the golden dataset."""
    with open(GOLDEN_DATASET_PATH) as f:
        data = json.load(f)

    entries = data["entries"]
    if role:
        entries = [e for e in entries if e["role"] == role]
    if difficulty:
        entries = [e for e in entries if e.get("difficulty") == difficulty]
    return entries


async def generate_answers_for_dataset(
    entries: list[dict],
    product: str = "stripe",
) -> tuple[list[str], list[str], list[list[str]], list[str]]:
    """
    Run retrieval + generation for each golden dataset entry.
    Returns (questions, answers, contexts, ground_truths) for RAGAS.
    """
    retriever = HybridRetriever(product=product, final_top_k=10)
    settings = get_settings()
    
    from langchain_anthropic import ChatAnthropic
    llm = ChatAnthropic(
        model=settings.generation_model,
        temperature=0,
        max_tokens=1000,
        api_key=settings.anthropic_api_key,
    )

    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for entry in entries:
        query = entry["query"]
        
        # Retrieve
        chunks = await retriever.retrieve(query)
        context_texts = [c.content if hasattr(c, 'content') else c.get("content", "") for c in chunks]
        
        # Generate answer
        context_str = "\n---\n".join(context_texts[:5])
        prompt = f"""Based on the following documentation, answer this question for a {entry['role']}:

Question: {query}

Documentation:
{context_str}

Provide a concise, accurate answer grounded in the documentation."""

        response = await llm.ainvoke(prompt)
        
        questions.append(query)
        answers.append(response.content)
        contexts.append(context_texts[:5])
        ground_truths.append(entry["ground_truth"])

    return questions, answers, contexts, ground_truths


async def run_ragas_evaluation(
    role: str | None = None,
    product: str = "stripe",
) -> dict:
    """
    Run full RAGAS evaluation.
    
    Returns dict with metric scores and per-entry details.
    """
    entries = load_golden_dataset(role=role)
    if not entries:
        return {"error": "No entries found for filter criteria"}

    questions, answers, contexts, ground_truths = await generate_answers_for_dataset(
        entries, product
    )

    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )

    # Convert to serializable dict
    scores = {
        "faithfulness": float(result["faithfulness"]),
        "answer_relevancy": float(result["answer_relevancy"]),
        "context_precision": float(result["context_precision"]),
        "context_recall": float(result["context_recall"]),
    }

    return {
        "product": product,
        "role": role or "all",
        "num_entries": len(entries),
        "scores": scores,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation")
    parser.add_argument("--product", default="stripe")
    parser.add_argument("--role", default=None)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(run_ragas_evaluation(
        role=None if args.all else args.role,
        product=args.product,
    ))
    
    print(json.dumps(result, indent=2))
```

## Task 3: Custom Metrics Module

### File: `backend/app/evaluation/metrics.py`

```python
"""
Custom evaluation metrics beyond RAGAS.

Tracks:
- Role specificity score (% of content tailored vs generic)
- Citation coverage (% of claims with citations)
- Code example quality (parseable, uses correct language)
- Progressive complexity score (section-over-section difficulty increase)
- Cost efficiency (quality per dollar spent)
"""

from app.models.schemas import GuideResponse, SectionEvaluation


def calculate_role_specificity(evaluation: dict) -> float:
    """Average role_relevance score across all sections."""
    section_evals = evaluation.get("section_evaluations", [])
    if not section_evals:
        return 0.0
    
    scores = []
    for se in section_evals:
        for dim in se.get("dimensions", []):
            if dim["dimension"] == "role_relevance":
                scores.append(dim["score"])
    
    return sum(scores) / len(scores) if scores else 0.0


def calculate_citation_coverage(sections: list[dict]) -> float:
    """Ratio of sections with at least one citation."""
    if not sections:
        return 0.0
    cited = sum(1 for s in sections if s.get("citations"))
    return cited / len(sections)


def calculate_cost_efficiency(overall_score: float, cost_usd: float) -> float:
    """Quality points per dollar (higher is better)."""
    if cost_usd <= 0:
        return 0.0
    return overall_score / cost_usd


def generate_metrics_report(guide_response: dict) -> dict:
    """Generate a comprehensive metrics report for a completed guide."""
    sections = guide_response.get("sections", [])
    evaluation = guide_response.get("evaluation", {})
    metadata = guide_response.get("metadata", {})

    overall = evaluation.get("overall_score", 0.0)
    cost = metadata.get("total_cost_usd", 0.0)

    return {
        "overall_score": overall,
        "role_specificity": calculate_role_specificity(evaluation),
        "citation_coverage": calculate_citation_coverage(sections),
        "cost_efficiency": calculate_cost_efficiency(overall, cost),
        "total_tokens": metadata.get("total_tokens_used", 0),
        "total_cost_usd": cost,
        "generation_time_seconds": metadata.get("generation_time_seconds", 0),
        "retrieval_latency_ms": metadata.get("retrieval_latency_ms", 0),
        "regeneration_count": metadata.get("regeneration_count", 0),
        "sections_count": len(sections),
        "avg_section_score": overall,
        "dimension_averages": _average_dimensions(evaluation),
    }


def _average_dimensions(evaluation: dict) -> dict:
    """Average score per dimension across all sections."""
    dim_totals: dict[str, list[float]] = {}
    for se in evaluation.get("section_evaluations", []):
        for dim in se.get("dimensions", []):
            name = dim["dimension"]
            if name not in dim_totals:
                dim_totals[name] = []
            dim_totals[name].append(dim["score"])

    return {
        name: round(sum(scores) / len(scores), 3)
        for name, scores in dim_totals.items()
    }
```

## Task 4: LLM-as-Judge Standalone Module

### File: `backend/app/evaluation/llm_judge.py`

A standalone evaluation function that can be used outside the LangGraph pipeline (for batch evaluation, CI runs, A/B testing prompts):

```python
"""
Standalone LLM-as-Judge evaluation.

Can be used:
1. Inside the LangGraph pipeline (via quality_evaluator agent)
2. In CI/CD for regression testing
3. For batch evaluation of existing guides
4. For A/B testing different generation prompts
"""

import json
from langchain_anthropic import ChatAnthropic
from app.models.schemas import SectionEvaluation
from app.config import get_settings


EVAL_DIMENSIONS = [
    "completeness",
    "role_relevance",
    "actionability",
    "clarity",
    "progressive_complexity",
]


async def evaluate_section(
    section: dict,
    role: str,
    experience_level: str,
    product: str,
    source_chunks: list[dict],
    previous_sections: list[dict] | None = None,
    model: str | None = None,
) -> SectionEvaluation:
    """
    Evaluate a single guide section using LLM-as-judge.
    
    Returns a SectionEvaluation with scores for all 5 dimensions.
    """
    settings = get_settings()
    llm = ChatAnthropic(
        model=model or settings.evaluation_model,
        temperature=0,
        max_tokens=3000,
        api_key=settings.anthropic_api_key,
    )

    # Build evaluation prompt (reuse the same prompt template as the agent)
    from pathlib import Path
    prompt_path = Path(__file__).parent.parent / "agents" / "prompts" / "quality_evaluator.xml"
    
    if prompt_path.exists():
        prompt_template = prompt_path.read_text()
    else:
        # Inline fallback
        prompt_template = _fallback_eval_prompt()

    prev_summaries = ""
    if previous_sections:
        prev_summaries = "\n".join(
            f"Section {s['section_number']}: {s['title']} — {s.get('summary', '')}"
            for s in previous_sections
        )

    chunk_text = "\n---\n".join(
        c.get("content", "")[:300] for c in (source_chunks or [])[:10]
    )

    prompt = prompt_template.format(
        product=product,
        role=role,
        experience_level=experience_level,
        section_number=section.get("section_number", 0),
        section_title=section.get("title", "Unknown"),
        section_content=json.dumps(section, indent=2)[:4000],
        source_chunks=chunk_text or "No source chunks available.",
        previous_section_summaries=prev_summaries or "None",
        eval_threshold=settings.eval_threshold,
    )

    response = await llm.ainvoke(prompt)
    content = response.content
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]

    return SectionEvaluation.model_validate_json(content)


async def evaluate_guide(
    guide: dict,
    source_chunks: list[dict] | None = None,
) -> dict:
    """Evaluate all sections in a guide. Returns full evaluation results."""
    sections = guide.get("sections", [])
    results = []
    
    for i, section in enumerate(sections):
        prev = sections[:i]
        sec_chunks = [
            c for c in (source_chunks or [])
            if c.get("assigned_section") == section.get("section_number")
        ]
        
        evaluation = await evaluate_section(
            section=section,
            role=guide.get("role", ""),
            experience_level=guide.get("experience_level", "intermediate"),
            product=guide.get("product", ""),
            source_chunks=sec_chunks,
            previous_sections=prev,
        )
        results.append(evaluation.model_dump())
    
    overall = sum(r["overall_score"] for r in results) / len(results) if results else 0
    
    return {
        "overall_score": round(overall, 3),
        "section_evaluations": results,
        "dimensions_avg": _avg_dims(results),
    }


def _avg_dims(results: list[dict]) -> dict:
    totals: dict[str, list] = {}
    for r in results:
        for d in r.get("dimensions", []):
            totals.setdefault(d["dimension"], []).append(d["score"])
    return {k: round(sum(v)/len(v), 3) for k, v in totals.items()}


def _fallback_eval_prompt():
    """Inline eval prompt as fallback if file not found."""
    return """Evaluate this guide section for a {role} ({experience_level}) learning {product}.
Section {section_number}: {section_title}

Content: {section_content}
Sources: {source_chunks}
Previous sections: {previous_section_summaries}

Score each dimension (0.0, 0.25, 0.5, 0.75, 1.0):
completeness, role_relevance, actionability, clarity, progressive_complexity

needs_regeneration = true if overall < {eval_threshold}

Respond with JSON matching SectionEvaluation schema."""
```

## Task 5: Evaluation API Endpoint Enhancement

Update `backend/app/api/evaluations.py` to add a batch evaluation trigger:

```python
@router.post("/run")
async def trigger_evaluation(
    product: str = "stripe",
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an offline RAGAS evaluation run."""
    # This would normally be a background task
    from app.evaluation.ragas_eval import run_ragas_evaluation
    result = await run_ragas_evaluation(role=role, product=product)
    return result


@router.get("/metrics/{guide_id}")
async def get_guide_metrics(guide_id: str, db: AsyncSession = Depends(get_db)):
    """Get comprehensive metrics for a specific guide."""
    from app.evaluation.metrics import generate_metrics_report
    from app.services.guide_service import GuideService
    
    service = GuideService(db)
    guide = await service.get_guide(guide_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    
    return generate_metrics_report(guide.model_dump())
```

## Task 6: Tests

### File: `backend/tests/test_evaluation/test_golden_dataset.py`
- Test dataset loads correctly
- Test filtering by role works
- Test all entries have required fields
- Test ground_truth is non-empty for all entries

### File: `backend/tests/test_evaluation/test_metrics.py`
- Test calculate_role_specificity with mock data
- Test calculate_citation_coverage
- Test calculate_cost_efficiency edge cases (zero cost)
- Test generate_metrics_report produces valid structure

## Completion Criteria
- [ ] Golden dataset has 50+ entries across 6 roles
- [ ] RAGAS runner executes and produces 4 metric scores
- [ ] Custom metrics module calculates role_specificity, citation_coverage, cost_efficiency
- [ ] LLM judge module works standalone (outside LangGraph)
- [ ] Evaluation API endpoints work
- [ ] All tests pass

## Final Steps
```bash
git add -A
git commit -m "feat: evaluation pipeline with RAGAS, golden dataset, and custom metrics

- 50+ golden evaluation entries across 6 roles for Stripe
- RAGAS integration (faithfulness, relevancy, precision, recall)
- Standalone LLM-as-judge module for batch evaluation
- Custom metrics: role_specificity, citation_coverage, cost_efficiency
- Evaluation API endpoints (trigger runs, get metrics)
- CLI runner for CI/CD integration
- Unit tests for dataset, metrics, and evaluation logic"
```
