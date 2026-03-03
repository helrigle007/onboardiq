# How to Run the OnboardIQ Parallel Sprint

## Setup (One Time)

```bash
# Create project directory
mkdir -p ~/onboardiq
cd ~/onboardiq

# Copy CLAUDE.md to project root (all terminals will read this)
cp /sprint/CLAUDE.md ./CLAUDE.md
```

## Phase 1 — Foundation

### Step 1: Terminal 1 (Infrastructure) — STARTS FIRST

Open Terminal 1 and paste:
```
cd ~/onboardiq && cat /sprint/phase1-t1-infrastructure.md | head -5
```

Then tell Claude Code:
```
Read the file /sprint/phase1-t1-infrastructure.md and execute every task in it.
This is a project scaffold task. Create the full project structure, all configuration
files, Docker Compose, FastAPI app factory, infrastructure layer, and Alembic setup
exactly as specified. Commit to branch infra/scaffolding when done.
```

**Wait for T1 to commit.** (~5-10 minutes)

### Step 2: Terminals 2, 3, 4 — START AFTER T1 COMMITS

Once T1 has committed its scaffold, open 3 more terminals.

**Terminal 2 (RAG Pipeline):**
```
Read /sprint/phase1-t2-rag-pipeline.md and execute every task.
Checkout from infra/scaffolding branch. Create the complete RAG pipeline:
Stripe documentation files, ingestion pipeline, semantic chunking with contextual
enrichment, Voyage AI embeddings, ChromaDB vector store, hybrid BM25+vector retriever,
cross-encoder reranker, and debug endpoint. Write all unit tests. Commit to
branch feat/rag-pipeline.
```

**Terminal 3 (Models + API):**
```
Read /sprint/phase1-t3-models-api.md and execute every task.
Checkout from infra/scaffolding branch. Create all Pydantic schemas, SQLAlchemy
models, FastAPI endpoints with SSE streaming, guide service layer, and placeholder
pipeline. Write all unit tests. Commit to branch feat/models-api.
```

**Terminal 4 (Frontend):**
```
Read /sprint/phase1-t4-frontend.md and execute every task.
Checkout from infra/scaffolding branch. Scaffold the React app with Vite +
TypeScript + Tailwind. Build all components: ProductSelector, RoleConfigurator,
GenerationView, GuideViewer, EvalRadarChart, QualityBadge, CitationTooltip.
Create comprehensive mock data. Wire up the full mock flow.
Commit to branch feat/frontend.
```

### Step 3: Merge Phase 1

When all 4 terminals complete:
```bash
cd ~/onboardiq
git checkout main

# Merge in order
git merge infra/scaffolding
git merge feat/models-api    # schemas everything depends on
git merge feat/rag-pipeline  # may have minor merge conflicts in products.py
git merge feat/frontend      # independent, clean merge
```

Resolve any merge conflicts (likely minimal — each touched different files).

---

## Phase 2 — Agent Pipeline + Integration

### All 4 terminals start simultaneously after Phase 1 merge.

**Terminal 1 (LangGraph + Agents A):**
```
Read /sprint/phase2-t1-agents-a.md and execute every task.
Build the LangGraph state schema, graph definition, Role Profiler agent, and
Content Curator agent. Wire the pipeline to the API layer. Commit to
branch agents/role-profiler-curator.
```

**Terminal 2 (Agents B):**
```
Read /sprint/phase2-t2-agents-b.md and execute every task.
Build the Guide Generator agent and Quality Evaluator agent. These are the
guide_generator_node and quality_evaluator_node in the LangGraph pipeline.
The Quality Evaluator implements the 5-dimension LLM-as-judge. Commit to
branch agents/generator-evaluator.
```

**Terminal 3 (Evaluation Pipeline):**
```
Read /sprint/phase2-t3-evaluation.md and execute every task.
Build the golden evaluation dataset (50+ entries), RAGAS integration,
standalone LLM-as-judge module, custom metrics, and evaluation API endpoints.
Commit to branch feat/evaluation-pipeline.
```

**Terminal 4 (Frontend Integration):**
```
Read /sprint/phase2-t4-frontend-integration.md and execute every task.
Wire the React frontend to real API endpoints and SSE streaming. Remove mock data.
Add guide history page, metadata panel, loading/error states, and animations.
Commit to branch feat/frontend-integration.
```

### Merge Phase 2
```bash
git checkout main
git merge agents/role-profiler-curator    # State + graph + 2 agents
git merge agents/generator-evaluator      # 2 more agents (will need graph.py merge)
git merge feat/evaluation-pipeline        # Eval layer
git merge feat/frontend-integration       # UI wiring
```

---

## Phase 3 — Polish

See `/sprint/phase3-all-terminals.md` for all 4 terminal tasks.
These are shorter tasks focused on CI/CD, documentation, testing, and UI polish.

---

## After All Phases

```bash
git tag -a v1.0.0 -m "OnboardIQ v1.0.0 — MVP release"
docker compose up
# Visit http://localhost:3000
```

## Tips
- If a terminal gets stuck, check that its branch was based on the right commit
- T1 must finish Phase 1 before any other terminal starts
- Within each phase (after T1), all terminals are independent
- Merge conflicts should be minimal since each terminal owns different files
- If Claude Code asks questions, it's usually about ambiguity — answer briefly and let it continue
