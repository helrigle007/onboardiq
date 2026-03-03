# ADR-002: Two-Stage Semantic Chunking with Contextual Enrichment

## Status
Accepted

## Context
Naive fixed-size text splitting loses document structure and context boundaries. A 1000-character chunk that splits mid-paragraph about "API Key Rotation" might end up without any reference to what API or what rotation pattern is being discussed. This causes retrieval failures where semantically relevant chunks are missed because their embeddings lack sufficient context to match the user's query.

Stripe's documentation is structured with clear Markdown headers (h1 for product areas, h2 for features, h3 for implementation details). This hierarchy carries meaningful information: a chunk under "Authentication > API Keys > Restricted Keys" has a very different audience and complexity level than one under "Getting Started > Your First Charge." Losing this hierarchy during chunking means losing a powerful signal for role-based filtering and progressive complexity ordering.

Additionally, individual chunks often assume knowledge from their surrounding sections. A paragraph explaining "use `sk_test_` keys in development" makes sense under the "Test Mode" heading, but as an isolated chunk, the embedding may not capture that this is about testing environments. This is the classic "lost in the middle" problem applied to chunking rather than retrieval.

## Decision
Implement a two-stage chunking strategy with contextual enrichment:

1. **First pass — Structural splitting:** `MarkdownHeaderTextSplitter` splits on h1, h2, and h3 headers, preserving the document hierarchy. Each resulting chunk carries metadata including its full `section_path` (e.g., "Authentication > API Keys > Restricted Keys"), the document source, and the header level.

2. **Second pass — Size-constrained splitting:** `RecursiveCharacterTextSplitter` with a 1000-character chunk size and 200-character overlap splits large sections while respecting sentence boundaries. The recursive strategy tries paragraph breaks first, then sentence breaks, then word breaks, minimizing mid-thought splits. The 200-character overlap ensures that context at chunk boundaries is not lost entirely.

3. **Contextual enrichment:** Each chunk is enriched via Claude Haiku with a 2-3 sentence contextual prefix that situates the chunk within its parent section. This follows Anthropic's Contextual Retrieval technique. The enrichment prompt receives the full parent section and the specific chunk, and produces a brief preamble like: "This chunk is from the Stripe Authentication documentation, specifically the section on restricted API keys. It explains how to create keys with limited permissions for specific API resources." This prefix is prepended to the chunk text before embedding.

Metadata attached to each chunk includes: `source` (document filename), `section_path` (header hierarchy), `topic` (extracted during enrichment), `complexity_level` (basic/intermediate/advanced, inferred from section depth and content), and `chunk_index` (position within the parent section).

## Consequences

### Positive
- **Header hierarchy preserved in metadata:** The `section_path` field enables agents to filter chunks by topic area and complexity. The content curator agent uses this to select chunks appropriate for the user's role and experience level.
- **Contextual enrichment reduces retrieval failures:** Anthropic's research shows that contextual retrieval reduces top-20 chunk retrieval failure rates by 35% on its own and by 49% when combined with BM25 hybrid search. The enriched prefix gives the embedding model explicit context that would otherwise be implicit.
- **Rich metadata for agent filtering:** Chunks carry enough structured metadata (topic, complexity, section_path) for the content curator agent to make informed decisions about which chunks to include in each guide section, supporting the progressive complexity requirement.
- **Sentence-boundary respect:** The recursive splitting strategy avoids mid-sentence breaks in the vast majority of cases, producing chunks that are coherent when read in isolation.

### Negative
- **Enrichment cost:** Contextual enrichment requires one Claude Haiku API call per chunk, costing approximately $0.002 per chunk. For a typical Stripe documentation set of 100-200 chunks, this adds $0.20-$0.40 per full document ingestion. This is a one-time cost at ingestion, not per-query.
- **Small boundary chunks:** The two-pass approach can occasionally create small chunks (under 200 characters) at section boundaries where the structural split produces a section that is just barely over the size threshold. These small chunks tend to have lower-quality embeddings.
- **Ingestion latency:** The enrichment step adds approximately 0.5-1 second per chunk due to the LLM call, making full ingestion take 1-3 minutes for the Stripe documentation set. This is acceptable for a curated, infrequently-updated documentation source.

### Trade-offs
The enrichment cost is a one-time expense at ingestion, not a per-query cost. For a curated documentation set like Stripe's, ingestion happens rarely (when documentation is updated), making the cost negligible relative to the per-query generation costs. The retrieval quality improvement directly impacts guide quality, which is the core value proposition of the product.
