# Phase 3 — Polish, Documentation, Testing, DevOps

**All 4 terminals. Start after Phase 2 merges.**

---

## Terminal 1: DevOps & CI/CD

Branch: `devops/ci-cd`

### Tasks
1. **GitHub Actions CI** (`/.github/workflows/ci.yml`):
   - Trigger on push to main and PRs
   - Backend job: install deps, ruff lint, mypy type-check, pytest with coverage
   - Frontend job: npm ci, lint, type-check, build
   - Upload coverage to codecov (or just output coverage report)

2. **GitHub Actions Eval** (`/.github/workflows/eval.yml`):
   - Weekly cron schedule (or manual trigger)
   - Run RAGAS evaluation against golden dataset
   - Output results as a GitHub Actions artifact
   - Update a `docs/eval-results.md` with latest scores

3. **Production Dockerfiles**:
   - Backend: multi-stage build (builder + runtime), non-root user, health check
   - Frontend: multi-stage (build + nginx), small final image

4. **Makefile enhancements**:
   - `make eval` — run evaluation locally
   - `make ingest` — run doc ingestion
   - `make clean` — remove volumes and data

5. **`.env.example`** — ensure all variables documented with inline comments

6. **PR template** (`.github/pull_request_template.md`):
   ```markdown
   ## What
   [Brief description]
   
   ## Type
   - [ ] Feature
   - [ ] Bug fix
   - [ ] Documentation
   - [ ] Refactor
   
   ## Checklist
   - [ ] Tests pass
   - [ ] Lint passes
   - [ ] Types check
   - [ ] Updated docs if needed
   ```

---

## Terminal 2: Documentation

Branch: `docs/readme`

### Tasks
1. **README.md** — Full professional README:
   - Project logo placeholder (just use a styled text header for now)
   - shields.io badges: CI status, coverage, license, Docker, RAG Faithfulness score
   - One-liner description + 2-sentence explanation
   - Animated GIF placeholder (`docs/assets/demo.gif` — add a TODO note)
   - "What is OnboardIQ?" section (3-4 sentences)
   - "Quick Start" section (3 commands: clone, env, docker compose up)
   - "Architecture" section with Mermaid diagram (renders natively in GitHub):
     ```mermaid
     graph TD
       A[React Frontend] -->|REST + SSE| B[FastAPI Backend]
       B --> C[LangGraph Orchestrator]
       C --> D[Role Profiler]
       C --> E[Content Curator]
       C --> F[Guide Generator]
       C --> G[Quality Evaluator]
       E --> H[Hybrid Retriever]
       H --> I[BM25 Index]
       H --> J[ChromaDB]
       H --> K[Cross-Encoder Reranker]
       D & E & F & G -->|Claude API| L[Anthropic]
       B --> M[(PostgreSQL)]
       B --> N[(Redis)]
       G -->|Score < 0.7| E
     ```
   - "Evaluation Results" section with markdown table of latest RAGAS + LLM judge scores
   - "Tech Stack" section (brief, with "why" for each choice)
   - "Project Structure" (abbreviated tree)
   - Links to docs/ files
   - License (MIT)

2. **docs/architecture.md** — Detailed architecture doc:
   - System overview with Mermaid sequence diagram (request flow)
   - Component descriptions (each agent, RAG pipeline, evaluation)
   - Data flow explanation
   - Technology choices with reasoning

3. **docs/evaluation.md** — Evaluation methodology:
   - 5-dimension rubric explanations
   - RAGAS metrics explanations
   - How to run evaluations
   - How to add golden dataset entries
   - Interpreting results

4. **docs/development.md** — Developer setup guide:
   - Prerequisites (Docker, Python 3.12, Node 20, API keys)
   - Setup steps
   - Running tests
   - Adding new products
   - Adding new roles

5. **ADRs** (docs/adr/):
   - `001-vector-db-choice.md` — ChromaDB over pgvector
   - `002-chunking-strategy.md` — Semantic + fixed hybrid
   - `003-eval-dimensions.md` — Why these 5 dimensions
   - `004-sequential-generation.md` — Sequential over parallel

   Each ADR follows the format: Status, Context, Decision, Consequences.

---

## Terminal 3: Testing & Quality

Branch: `test/e2e`

### Tasks
1. **Integration tests** (`backend/tests/test_integration/`):
   - `test_full_pipeline.py` — Mock Claude API, run entire LangGraph pipeline, verify output structure
   - `test_sse_flow.py` — Start generation, connect to SSE, verify all event types arrive in order
   - `test_guide_persistence.py` — Generate → save → fetch → verify data integrity

2. **Expand golden dataset** — add any missing entries to reach 50+

3. **Add test fixtures** (`backend/tests/conftest.py`):
   - Mock Claude responses for each agent (deterministic test data)
   - Test ChromaDB collection with sample data
   - Async test client setup

4. **Coverage report** — Aim for 70%+ coverage on `app/agents/`, `app/rag/`, `app/evaluation/`

5. **Type checking** — Fix any mypy issues across the backend

---

## Terminal 4: UI Polish & Demo Prep

Branch: `feat/ui-polish`

### Tasks
1. **Responsive layout fixes** — Ensure nothing breaks at 1024px and 1280px
2. **Dark mode** (optional stretch) — Add toggle using Tailwind's `dark:` classes
3. **Empty states** — Nice illustrations/messages when no guides exist yet
4. **Favicon** — Simple favicon for the app
5. **Page title** — Dynamic document.title based on current page
6. **Console cleanup** — Remove console.logs, fix any warnings
7. **Performance** — Lazy load GuideViewer and EvalRadarChart (React.lazy)
8. **Demo script** — Create `docs/DEMO-SCRIPT.md`:
   - Step-by-step walkthrough for recording a demo GIF
   - Suggested product/role/experience combinations that produce best results
   - Talking points for each screen

---

## Merge Order (Phase 3)
1. T3 (tests) — ensures everything works
2. T1 (devops) — CI validates tests
3. T2 (docs) — README and documentation
4. T4 (polish) — final visual touches
5. Tag `v1.0.0`
