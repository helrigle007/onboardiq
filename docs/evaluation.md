# Evaluation Methodology

OnboardIQ uses a two-layer evaluation strategy to ensure that every generated onboarding guide is high-quality, role-appropriate, and factually grounded in real product documentation. This document describes both layers, the scoring rubrics, the golden dataset, and how to run and interpret evaluation results.

---

## 1. Two-Layer Evaluation Strategy

Guide quality is validated at two distinct stages, each catching a different class of failure.

### Real-Time: LLM-as-Judge

During every generation run, each section of the onboarding guide passes through a 5-dimension quality evaluator before the guide is finalized and returned to the user. The evaluator is an LLM (Claude) prompted with a structured rubric that scores each section on five dimensions (described in Section 2). Any section that receives an overall score below **0.7** is automatically regenerated, up to a maximum of **2 retry attempts**. If a section still fails after retries, it is included with a quality warning flag so the user is aware of potential issues.

This layer runs synchronously within the LangGraph pipeline. The `quality_evaluator` agent node emits SSE events (`evaluation_start`, `evaluation_complete`) so the frontend can display evaluation progress in real time. Token usage for evaluation calls is tracked alongside generation costs.

### Offline: RAGAS

In CI (or on-demand via CLI), the RAGAS framework computes four retrieval-augmented generation metrics against a golden dataset:

- Faithfulness
- Answer Relevancy
- Context Precision
- Context Recall

These metrics are described in detail in Section 3. RAGAS evaluation runs end-to-end: it feeds golden dataset queries through the full pipeline (retrieval, reranking, generation) and compares the outputs against expected topics and citations.

### Why Both Layers Are Needed

The LLM-as-judge catches **output quality** problems before the user ever sees them: incoherent structure, missing information, wrong audience targeting, lack of actionable content. However, the judge operates on the generated text alone and cannot directly measure whether the retriever found the right source documents or whether the generated content is factually grounded in those documents.

RAGAS fills that gap. It validates **retrieval fidelity** (did we find the right chunks?) and **factual grounding** (does the output actually come from the source material, or did the model hallucinate?). These are failure modes that a quality judge reading only the output text would miss entirely, since hallucinated content can be fluent, well-structured, and appear perfectly reasonable.

Together, the two layers provide defense in depth: real-time quality gating for every user request, and offline retrieval validation to catch systemic pipeline regressions.

---

## 2. 5-Dimension Rubric

Every section is scored on five dimensions, each ranging from **0.0 to 1.0**. The overall section score is the unweighted mean of all five dimensions.

### Completeness (0.0 - 1.0)

Does the section cover all essential concepts for the topic?

| Score | Meaning |
|-------|---------|
| 1.0 | No key information is missing. All essential concepts, edge cases, and prerequisites are addressed. |
| 0.7 | Minor gaps. Core concepts present but some secondary details omitted. |
| 0.5 | Significant gaps. Several important concepts are missing or only superficially mentioned. |
| 0.3 | Majority of expected content is absent. |
| 0.0 | The section is empty, irrelevant to the topic, or fundamentally wrong. |

### Role Relevance (0.0 - 1.0)

Is the content tailored to the reader's specific role and experience level?

| Score | Meaning |
|-------|---------|
| 1.0 | Every example, explanation, and recommendation is appropriate for the target role. A backend engineer sees API integration patterns and server-side code; a security engineer sees compliance frameworks and threat models. |
| 0.7 | Mostly role-appropriate with minor generic sections. |
| 0.5 | Generic content that could apply to any role. Not wrong, but not targeted. |
| 0.3 | Partially targeted at the wrong audience. |
| 0.0 | Entirely targeted at the wrong audience or role is ignored completely. |

### Actionability (0.0 - 1.0)

Can the reader take concrete action after reading this section?

| Score | Meaning |
|-------|---------|
| 1.0 | Specific code examples, step-by-step instructions, copy-pasteable commands, and clear next steps. The reader can immediately start implementing. |
| 0.7 | Mostly actionable with some gaps in specificity. |
| 0.5 | Conceptual understanding conveyed but not practical. Reader knows "what" but not "how." |
| 0.3 | Vague suggestions without concrete guidance. |
| 0.0 | Purely theoretical. No actionable guidance whatsoever. |

### Clarity (0.0 - 1.0)

Is the content well-organized and easy to understand?

| Score | Meaning |
|-------|---------|
| 1.0 | Logical flow, clear headings, concise explanations, appropriate use of lists and code blocks. No ambiguity. |
| 0.7 | Well-organized with minor structural issues. |
| 0.5 | Some confusion in organization. Reader has to re-read sections to understand the flow. |
| 0.3 | Disorganized. Key information is buried or presented out of order. |
| 0.0 | Incoherent or so poorly structured that the content is effectively unusable. |

### Progressive Complexity (0.0 - 1.0)

Does the guide build from basics to advanced topics appropriately?

| Score | Meaning |
|-------|---------|
| 1.0 | Smooth progression. Prerequisites are introduced before they are needed. Foundational concepts lead naturally into advanced material. |
| 0.7 | Generally good progression with minor jumps in difficulty. |
| 0.5 | Noticeable jumps. Some advanced concepts appear before their prerequisites. |
| 0.3 | Largely random ordering of difficulty. |
| 0.0 | No discernible progression. Advanced topics mixed arbitrarily with basics throughout. |

### Why These 5 Dimensions

The five dimensions were chosen to answer three stakeholder questions that collectively define onboarding guide quality:

1. **"Did it cover everything?"** -- Completeness directly measures information coverage. A guide that misses critical setup steps or key concepts fails its primary purpose.

2. **"Is it for me?"** -- Role Relevance ensures personalization is working. The entire value proposition of OnboardIQ is that a backend engineer gets a different guide than a product manager. If this dimension scores low, the role profiler and content curator agents are not doing their jobs.

3. **"Can I act on it?"** -- This is the combined concern of Actionability, Clarity, and Progressive Complexity. Content can be complete and role-relevant but still unusable if it is poorly organized (Clarity), lacks concrete steps (Actionability), or drops the reader into advanced material without context (Progressive Complexity).

---

## 3. RAGAS Metrics

RAGAS (Retrieval-Augmented Generation Assessment) provides four metrics that evaluate the retrieval and grounding layers of the pipeline.

### Faithfulness

Measures whether the generated answer is factually grounded in the retrieved source documents. RAGAS decomposes the generated text into individual claims and checks each claim against the provided context. A faithfulness score of 1.0 means every claim in the output can be traced back to a source chunk. This is the primary **hallucination detection** metric.

### Answer Relevancy

Measures whether the generated content is relevant to the original query and role. RAGAS generates synthetic questions from the answer and checks whether they align with the original input. A low score indicates that the generator produced tangential or off-topic content, even if the content itself is factually correct.

### Context Precision

Measures whether the retrieved chunks are actually relevant to the query. A high context precision means the retriever is not polluting the context window with irrelevant documents. This directly evaluates the quality of hybrid retrieval (vector + BM25) and cross-encoder reranking.

### Context Recall

Measures whether the retriever found all the relevant chunks available in the corpus. A low context recall means relevant documentation exists but was not retrieved, leading to incomplete answers. This metric requires the golden dataset to specify expected citations so that recall can be computed.

### How RAGAS Complements the LLM Judge

The LLM judge evaluates **output quality**: is the text complete, clear, actionable, and role-appropriate? It reads only the generated content. RAGAS evaluates **retrieval quality and grounding**: did we find the right source documents, and does the output actually come from them? The judge cannot detect a fluent hallucination that sounds plausible but has no basis in the documentation. RAGAS can. Conversely, RAGAS does not evaluate whether the output is well-structured or role-appropriate. The two systems cover complementary failure modes.

---

## 4. Golden Dataset

The golden dataset is the ground truth used by RAGAS evaluation and is stored at `backend/app/evaluation/golden_dataset.json`.

### Schema

Each entry in the JSON array follows this structure:

```json
{
  "id": "stripe-payments-backend-001",
  "product": "stripe",
  "role": "backend_developer",
  "experience_level": "intermediate",
  "query": "How do I integrate Stripe payment intents for a subscription billing system?",
  "expected_topics": [
    "PaymentIntent API",
    "Customer objects",
    "Subscription lifecycle",
    "Webhook handling",
    "Idempotency keys",
    "Error handling"
  ],
  "expected_citations": [
    "stripe-docs/payments/payment-intents",
    "stripe-docs/billing/subscriptions/overview"
  ],
  "quality_threshold": 0.85
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the entry. Convention: `{product}-{topic}-{role}-{number}`. |
| `product` | string | The product documentation corpus (e.g., `"stripe"`). |
| `role` | string | One of: `frontend_developer`, `backend_developer`, `security_engineer`, `devops_engineer`, `product_manager`, `team_lead`. |
| `experience_level` | string | One of: `beginner`, `intermediate`, `senior`. |
| `query` | string | The natural-language query or onboarding scenario. |
| `expected_topics` | string[] | Topics that a correct answer must address. Used to compute completeness and recall. |
| `expected_citations` | string[] | Source document paths that a correct answer should reference. Used by RAGAS context recall. |
| `quality_threshold` | float | Minimum acceptable overall score for this entry. Defaults to 0.85 if omitted. |

### Coverage

The golden dataset targets coverage across:

- **6 roles**: frontend_developer, backend_developer, security_engineer, devops_engineer, product_manager, team_lead
- **Multiple topics per role**: payments, subscriptions, webhooks, authentication, compliance, deployment, and more
- **3 experience levels**: beginner, intermediate, senior

### How to Add Entries

1. Identify a query-role-experience combination not yet covered.
2. Manually determine the expected topics by reading the relevant source documentation.
3. Identify the specific source document paths that should be retrieved.
4. Set a quality threshold (0.85 is the default; use 0.9 for critical paths, 0.8 for edge cases).
5. Add the entry to `backend/app/evaluation/golden_dataset.json`.
6. Run the RAGAS evaluation to verify the entry is well-formed and produces meaningful scores.

### Target Size

The dataset should contain **50+ entries** for meaningful statistical significance. At 6 roles with 3 experience levels each, this means roughly 3 queries per role-experience combination. Prioritize high-traffic role-topic pairs first.

---

## 5. Running Evaluations

### LLM-as-Judge (Unit and Integration Tests)

```bash
# Run all evaluation tests
python -m pytest tests/test_evaluation/ -v

# Run a specific test file
python -m pytest tests/test_evaluation/test_quality_evaluator.py -v

# Run with detailed output for debugging
python -m pytest tests/test_evaluation/ -v -s
```

### RAGAS Evaluation (Against Golden Dataset)

```bash
# Run RAGAS evaluation against the full golden dataset
python -m app.evaluation.ragas_eval --dataset golden_dataset.json

# Run against a subset (e.g., only backend_developer entries)
python -m app.evaluation.ragas_eval --dataset golden_dataset.json --role backend_developer

# Output results as JSON for CI parsing
python -m app.evaluation.ragas_eval --dataset golden_dataset.json --output results.json
```

### Full Evaluation Suite with Coverage

```bash
# Run all tests with coverage reporting
python -m pytest tests/ --cov=app/evaluation --cov-report=html

# View the HTML coverage report
open htmlcov/index.html
```

### Environment Requirements

Both evaluation layers require the following environment variables:

- `ANTHROPIC_API_KEY` -- Used by the LLM judge and by the generator during RAGAS end-to-end evaluation.
- `VOYAGE_API_KEY` -- Used by the embedding model during retrieval in RAGAS evaluation.

Ensure Docker services (PostgreSQL, Redis, ChromaDB) are running via `docker compose up` before executing RAGAS evaluation, as it exercises the full pipeline.

---

## 6. Interpreting Results

### Score Thresholds

| Level | Overall Score | Per-Dimension | Faithfulness |
|-------|--------------|---------------|--------------|
| **Good** | >= 0.85 | All >= 0.7 | >= 0.9 |
| **Acceptable** | >= 0.75 | All >= 0.6 | >= 0.85 |
| **Warning** | < 0.75 | Any < 0.6 | < 0.8 |
| **Failing** | < 0.6 | Any < 0.4 | < 0.7 |

### Common Failure Modes and Debugging

**Low Completeness (< 0.6)**
- Likely cause: The retriever is missing relevant chunks from the corpus.
- Debug: Check chunk coverage in ChromaDB. Verify that the ingestion pipeline processed all relevant documentation pages. Use LangSmith traces to inspect what chunks the retriever returned for the query.
- Fix: Re-ingest missing documentation. Adjust chunk size or overlap. Verify BM25 index is up to date.

**Low Role Relevance (< 0.6)**
- Likely cause: The role profiler agent is not producing sufficiently differentiated role profiles, or the content curator is not using the role profile to filter content.
- Debug: Inspect the role profiler output in LangSmith traces. Compare profiles generated for different roles on the same topic.
- Fix: Strengthen the role profiler prompt in `backend/app/agents/prompts/`. Add more explicit role-differentiation instructions. Include few-shot examples of role-specific content.

**Low Actionability (< 0.6)**
- Likely cause: The guide generator is producing conceptual explanations without concrete code examples or step-by-step instructions.
- Debug: Read the generated sections and check for the presence of code blocks, numbered steps, and specific API calls.
- Fix: Update the generator prompt to explicitly require code examples and implementation steps. Add examples of high-actionability content to the prompt.

**Low Progressive Complexity (< 0.6)**
- Likely cause: Sections are generated in the wrong order, or the sequential generation pipeline is not passing sufficient context about what has already been covered.
- Debug: Review the section ordering logic and the context passed between sequential generation steps.
- Fix: Ensure the section planner produces a logical ordering. Pass summaries of previously generated sections to the generator so it can calibrate difficulty.

**Low Faithfulness (< 0.8)**
- Likely cause: The model is hallucinating content not present in the retrieved chunks. This is the most critical failure mode.
- Debug: Use LangSmith traces to compare the retrieved context against the generated claims. RAGAS faithfulness scoring will identify specific unfaithful claims.
- Fix: Improve chunk quality via contextual retrieval enrichment. Strengthen the reranker to surface more relevant chunks. Add explicit grounding instructions to the generator prompt (e.g., "Only include information that appears in the provided context").

**Low Context Precision (< 0.7)**
- Likely cause: The retriever is returning irrelevant chunks that dilute the context window.
- Debug: Inspect retrieved chunks for a sample of queries. Check the cross-encoder reranker scores.
- Fix: Tune the hybrid retrieval weights (currently 70% vector / 30% BM25). Adjust the reranker score threshold. Reduce the number of chunks passed to the generator.

**Low Context Recall (< 0.7)**
- Likely cause: Relevant chunks exist in the corpus but are not being retrieved.
- Debug: Manually query ChromaDB and BM25 for expected citations from the golden dataset. Check if the embedding model is producing good representations for the query type.
- Fix: Improve query expansion. Adjust chunk overlap to reduce information loss at chunk boundaries. Consider adding metadata filters to improve retrieval targeting.

### Using LangSmith for Debugging

All pipeline runs are traced in LangSmith. To debug a specific evaluation failure:

1. Find the run in the LangSmith dashboard by timestamp or run ID.
2. Inspect the `role_profiler` node output to verify the role profile.
3. Inspect the `content_curator` node to see which chunks were retrieved and how they were ranked.
4. Inspect the `guide_generator` node to see the prompt and generated output.
5. Inspect the `quality_evaluator` node to see per-dimension scores and the judge's reasoning.

The judge's reasoning field is particularly valuable: it explains why each dimension received its score, which directly points to what needs improvement.

---

## Appendix: Evaluation Architecture Diagram

```
User Request
     |
     v
[Role Profiler] --> [Content Curator] --> [Guide Generator] --+--> [Quality Evaluator]
                                                               |         |
                                                               |    score < 0.7?
                                                               |     yes  |  no
                                                               |      |   |
                                                               |      v   v
                                                               +-- Retry  Finalize
                                                              (max 2x)    |
                                                                          v
                                                                   Guide Output
                                                                          |
                                              (offline, CI)               |
                                                   |                      |
                                                   v                      |
                                             [RAGAS Eval] <--- Golden Dataset
                                                   |
                                                   v
                                           Retrieval Metrics
```
