# Phase 1 — Terminal 2: RAG Pipeline

## Overview
You are building the complete RAG pipeline for OnboardIQ: document ingestion, semantic chunking, contextual embedding enrichment, ChromaDB vector storage, BM25 keyword index, hybrid retrieval, and cross-encoder reranking. This is the retrieval backbone that all agents depend on.

## Pre-flight
```bash
cd ~/onboardiq
git checkout infra/scaffolding   # wait for T1 to finish this branch
git checkout -b feat/rag-pipeline
```

## Context
- Product docs target: **Stripe** (stripe.com/docs)
- Embedding provider: **Voyage AI** (model: voyage-3)
- Vector store: **ChromaDB** (running in Docker on port 8001)
- Reranker: **cross-encoder/ms-marco-MiniLM-L-6-v2** (local, via sentence-transformers)
- Key Anthropic technique to implement: **Contextual Retrieval** — use Claude Haiku to prepend a 2-3 sentence contextual description to each chunk before embedding

## Task 1: Stripe Documentation Ingestion

Create a script that downloads/processes Stripe documentation for the MVP demo. Since we can't scrape live at runtime reliably, we'll create a curated dataset.

### File: `backend/app/rag/ingestion.py`

Implement:

1. **`StripeDocLoader`** class that:
   - Reads markdown files from `backend/data/docs/stripe/`
   - Extracts metadata: title, URL path, section hierarchy, topic tags
   - Returns `list[Document]` with content + metadata

2. **`SemanticChunker`** class that:
   - First pass: `MarkdownHeaderTextSplitter` to split on h1/h2/h3 headers
   - Second pass: `RecursiveCharacterTextSplitter` with chunk_size=1000, overlap=200
   - Preserves header hierarchy in chunk metadata as `section_path` (e.g., "Authentication > API Keys > Restricted Keys")
   - Adds metadata fields: `product`, `topic`, `chunk_index`, `source_url`, `section_path`, `complexity` (inferred from header depth: h1=overview, h2=concept, h3=detail)

3. **`ContextualEnricher`** class that:
   - Takes each chunk + its parent document excerpt (the full h2 section it came from)
   - Calls Claude Haiku with this prompt to generate a contextual prefix:
   ```
   <document>
   {parent_section_text}
   </document>

   <chunk>
   {chunk_text}
   </chunk>

   Provide a concise 2-3 sentence contextual description that situates this chunk
   within the broader document. What product feature, API, or concept does it cover?
   How does it relate to its parent section? Start with "This chunk..."
   ```
   - Prepends the contextual description to the chunk content before embedding
   - Stores original content AND enriched content separately in metadata

4. **`run_ingestion`** async function that orchestrates the full pipeline:
   - Load → Chunk → Enrich → Embed → Store in ChromaDB
   - Log progress: chunks created, enriched, embedded
   - Return stats dict

### File: `backend/scripts/ingest_stripe_docs.py`

A runnable script:
```python
"""
Usage: python -m scripts.ingest_stripe_docs

Downloads and ingests Stripe documentation into ChromaDB.
Run this once before starting the application.
"""
```

### Stripe Doc Dataset

Create **at minimum** these curated markdown files in `backend/data/docs/stripe/` covering the key areas a demo needs. These should be realistic representations of Stripe's actual documentation structure and content. Each file should be 2000-5000 words covering the topic thoroughly:

1. `authentication.md` — API keys, restricted keys, key rotation, authentication methods
2. `payments-overview.md` — Payment intents, charges, payment methods, payment flow
3. `webhooks.md` — Webhook endpoints, event types, signatures, retry logic, testing
4. `error-handling.md` — Error types, error codes, idempotency, retry strategies
5. `security.md` — PCI compliance, data security, TLS, fraud prevention, audit logging
6. `sdks-quickstart.md` — SDK installation, basic usage for Python/Node/Ruby, first charge

Write these as realistic SaaS documentation. Use proper markdown headers (h1/h2/h3), code blocks, tables, callout-style warnings. Include realistic API endpoint references, parameter names, and code snippets. These docs will be chunked and retrieved, so quality matters for the demo.

Each file should have a YAML-style frontmatter comment at the top:
```markdown
<!-- 
title: Authentication
url: https://docs.stripe.com/authentication
topic: authentication
complexity: intermediate
-->

# Authentication

## API Keys
...
```

## Task 2: Embedding Configuration

### File: `backend/app/rag/embeddings.py`

```python
"""
Embedding configuration for OnboardIQ.

Primary: Voyage AI (voyage-3) — recommended by Anthropic for Claude-based RAG.
Fallback: sentence-transformers/all-MiniLM-L6-v2 (local, free, for dev without API key)

The embedding function is used by both the ingestion pipeline and the retriever.
"""
```

Implement:
1. **`get_embedding_function()`** — returns a LangChain-compatible embedding function
   - If `VOYAGE_API_KEY` is set → use `VoyageAIEmbeddings(model="voyage-3")`
   - Else → fall back to `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")` with a warning log
2. Configure embedding dimension (Voyage-3 = 1024 dims, MiniLM = 384 dims)
3. Add a `embed_with_retry()` wrapper with exponential backoff (3 retries, base delay 1s)

## Task 3: Vector Store Setup

### File: `backend/app/rag/vectorstore.py`

Implement:
1. **`get_vectorstore(product: str)`** — returns a ChromaDB collection for the given product
   - Collection name: `{product}_docs` (e.g., `stripe_docs`)
   - Uses the embedding function from `embeddings.py`
   - Connects to ChromaDB via HTTP client (host from settings)
2. **`add_documents(product: str, documents: list[Document])`** — batch upsert with deduplication
   - Generate deterministic IDs from content hash to prevent duplicates
   - Batch size: 100 documents per upsert call
3. **`get_collection_stats(product: str)`** — return count, metadata summary

## Task 4: Hybrid Retriever

### File: `backend/app/rag/retriever.py`

This is the core retrieval component. Implement:

1. **`HybridRetriever`** class:
   ```python
   class HybridRetriever:
       """
       Two-stage hybrid retrieval:
       Stage 1: BM25 (keyword) + ChromaDB (semantic) via EnsembleRetriever
       Stage 2: Cross-encoder reranking
       
       Also supports MultiQuery expansion for improved recall.
       """
       
       def __init__(
           self,
           product: str,
           bm25_weight: float = 0.3,
           vector_weight: float = 0.7,
           initial_top_k: int = 50,  # candidates before reranking
           final_top_k: int = 20,     # results after reranking
           use_multi_query: bool = True,
       ): ...
       
       async def retrieve(
           self,
           query: str,
           metadata_filter: dict | None = None,
       ) -> list[RetrievedChunk]: ...
   ```

2. **`RetrievedChunk`** Pydantic model:
   ```python
   class RetrievedChunk(BaseModel):
       chunk_id: str
       content: str                    # The enriched chunk text
       original_content: str           # Pre-enrichment text
       metadata: dict                  # All chunk metadata
       bm25_score: float | None = None
       vector_score: float | None = None
       rerank_score: float | None = None
       source_url: str
       section_path: str
   ```

3. **MultiQuery generation**: Use Claude Haiku to generate 3 query variations:
   - Original query
   - Rephrased for different terminology
   - Rephrased as a how-to question
   
   Example: "Stripe API key security" →
   - "Stripe API key security"
   - "Stripe authentication best practices secret key protection"  
   - "How to secure and rotate Stripe API keys in production"

4. **Metadata filtering**: Support filtering by `topic`, `complexity`, `section_path` prefix

5. **BM25 Index**: Build from the same document set stored in ChromaDB. Use `rank_bm25.BM25Okapi`. The BM25 index should be built once during initialization and cached.

## Task 5: Cross-Encoder Reranker

### File: `backend/app/rag/reranker.py`

```python
"""
Cross-encoder reranker using ms-marco-MiniLM-L-6-v2.

Why two-stage retrieval matters (architecture note):
- Bi-encoders (embedding models) encode query and document independently.
  Fast but approximate — they can't capture fine-grained query-document interaction.
- Cross-encoders see query+document together as a single input.
  Much more accurate but too slow for initial retrieval (O(n) vs O(1)).
- Solution: Use bi-encoders for broad recall (top-50), then cross-encoders
  for precision (top-20). This is the pattern used at Uber, DoorDash, LinkedIn.
"""
```

Implement:
1. **`DocumentReranker`** class:
   - Loads `cross-encoder/ms-marco-MiniLM-L-6-v2` on init
   - `rerank(query, chunks, top_k)` method
   - Returns chunks sorted by rerank_score with score attached
   - Handles edge cases: empty chunks list, single chunk, chunks shorter than query

2. Add timing instrumentation: log reranking latency

## Task 6: Debug/Test Endpoint

Add a temporary debug endpoint to verify the pipeline works end-to-end:

### File: Update `backend/app/api/products.py`

```python
@router.get("/")
async def list_products():
    """List supported products with doc stats."""
    return {
        "products": [
            {
                "id": "stripe",
                "name": "Stripe",
                "description": "Payment processing platform",
                "doc_stats": await get_collection_stats("stripe"),
                "available_roles": [...],
            }
        ]
    }

@router.get("/debug/retrieve")
async def debug_retrieve(query: str, product: str = "stripe", top_k: int = 5):
    """Debug endpoint: test retrieval pipeline."""
    retriever = HybridRetriever(product=product, final_top_k=top_k)
    chunks = await retriever.retrieve(query)
    return {
        "query": query,
        "num_results": len(chunks),
        "results": [c.model_dump() for c in chunks],
    }
```

## Task 7: Unit Tests

### File: `backend/tests/test_rag/test_chunking.py`
- Test MarkdownHeaderTextSplitter preserves header hierarchy
- Test chunk sizes are within bounds (800-1200 chars)
- Test metadata is correctly populated
- Test duplicate content doesn't create duplicate chunks

### File: `backend/tests/test_rag/test_retriever.py`
- Test BM25 retrieval returns results for known terms (e.g., "webhook")
- Test vector retrieval returns semantically similar results
- Test hybrid retrieval combines both
- Test metadata filtering works
- Test empty query handling

### File: `backend/tests/test_rag/test_reranker.py`
- Test reranking changes order (not just pass-through)
- Test top_k is respected
- Test empty input handling

Use pytest fixtures for a small test document set (3-5 short docs).

## Completion Criteria
- [ ] 6 Stripe doc files in `backend/data/docs/stripe/` (2000-5000 words each, realistic content)
- [ ] `python -m scripts.ingest_stripe_docs` runs successfully, ingests all docs into ChromaDB
- [ ] `GET /api/products/debug/retrieve?query=webhook+security` returns relevant ranked chunks
- [ ] Hybrid retrieval combines BM25 + vector scores
- [ ] Reranker reorders results by cross-encoder score
- [ ] Contextual enrichment adds meaningful context prefixes to chunks
- [ ] All unit tests pass
- [ ] Voyage AI embeddings work (with fallback to local if no API key)

## Architecture Notes for Context
- ChromaDB runs in Docker on port 8001 (internal port 8000)
- The retriever will be called by the Content Curator agent (Phase 2)
- Chunks need to carry enough metadata for the agents to filter by role relevance
- The `section_path` metadata is critical — agents use it to avoid duplicate coverage across guide sections
- Keep the BM25 index in memory — it's small enough for our doc set

## Final Steps
```bash
git add -A
git commit -m "feat: complete RAG pipeline with hybrid retrieval and reranking

- Stripe documentation dataset (6 curated doc files)
- Semantic chunking with header-aware splitting
- Contextual embedding enrichment via Claude Haiku
- Voyage AI embeddings with local fallback
- ChromaDB vector store with batch upsert
- BM25 keyword index
- Hybrid retriever (EnsembleRetriever pattern)
- Cross-encoder reranking (ms-marco-MiniLM)
- MultiQuery expansion for improved recall
- Debug retrieval endpoint
- Unit tests for chunking, retrieval, reranking"
```
