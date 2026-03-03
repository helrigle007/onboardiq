# OnboardIQ — Parallel Sprint Plan

**4 Terminals | 3 Phases | Target: Full MVP**

## Dependency Graph

```
PHASE 1 (All Independent — Start Simultaneously)
═══════════════════════════════════════════════════
T1: Infrastructure     T2: RAG Pipeline      T3: Models + API      T4: Frontend
├─ Docker Compose      ├─ Doc ingestion       ├─ Pydantic schemas   ├─ React scaffold
├─ Config system       ├─ Chunking pipeline   ├─ SQLAlchemy models  ├─ All components
├─ DB + migrations     ├─ Embeddings (Voyage) ├─ FastAPI endpoints  ├─ SSE hook
├─ Redis setup         ├─ ChromaDB setup      ├─ SSE streaming      ├─ Types
└─ LangSmith config    ├─ Hybrid retriever    └─ Health/debug       └─ Mock data flow
                       └─ Reranker

PHASE 2 (Builds on Phase 1)
═══════════════════════════════════════════════════
T1: Agents A           T2: Agents B           T3: Evaluation        T4: Integration
├─ LangGraph state     ├─ Guide Generator     ├─ LLM-as-Judge       ├─ Wire API→UI
├─ Graph definition    ├─ Quality Evaluator   ├─ RAGAS integration  ├─ Real SSE events
├─ Role Profiler       ├─ Regen routing       ├─ Golden dataset     ├─ Eval radar chart
└─ Content Curator     └─ Prompt templates    └─ Metrics logging    └─ Citation tooltips

PHASE 3 (Polish)
═══════════════════════════════════════════════════
T1: DevOps             T2: Documentation      T3: Testing           T4: UI Polish
├─ GitHub Actions CI   ├─ README (full)       ├─ E2E test suite     ├─ Loading states
├─ Dockerfiles (prod)  ├─ Architecture.md     ├─ Golden dataset     ├─ Error handling
├─ .env.example        ├─ ADRs (4)           ├─ Eval regression    ├─ Demo GIF
└─ Makefile            └─ Mermaid diagrams    └─ Coverage reports   └─ Dark mode
```

## User Workflow Per Phase

### Phase 1 Start
1. Open 4 terminals, all cd to ~/onboardiq
2. Run T1 spec FIRST (creates repo + base structure, ~2 min)
3. After T1 scaffolding commit: start T2, T3, T4 in parallel
4. Each terminal works on its own branch
5. When all 4 complete → merge all branches → Phase 2

### Branch Strategy
- T1: `infra/scaffolding` → `agents/role-profiler-curator` → `devops/ci-cd`
- T2: `feat/rag-pipeline` → `agents/generator-evaluator` → `docs/readme`
- T3: `feat/models-api` → `feat/evaluation-pipeline` → `test/e2e`
- T4: `feat/frontend` → `feat/frontend-integration` → `feat/ui-polish`

### Merge Order (Phase 1)
1. T1 (infra) first — base structure
2. T3 (models) second — schemas everything depends on
3. T2 (RAG) third — retrieval pipeline
4. T4 (frontend) last — UI layer
