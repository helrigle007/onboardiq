# ADR-001: ChromaDB for Vector Storage

## Status
Accepted

## Context
OnboardIQ needs a vector database for storing document embeddings and performing similarity search as part of its hybrid RAG retrieval pipeline. The system ingests Stripe product documentation, chunks and embeds it, and retrieves relevant passages at generation time to ground the onboarding guides in accurate, up-to-date content.

Options considered:
- **ChromaDB** — Open-source, Python-native, runs as a Docker service or embedded
- **pgvector** — PostgreSQL extension, consolidates vector and relational storage
- **Pinecone** — Managed cloud service, excellent scaling, proprietary
- **Qdrant** — Open-source, Rust-based, strong filtering support
- **Weaviate** — Open-source, GraphQL API, module ecosystem

The primary selection criteria were: ease of local development, Docker Compose compatibility, LangChain integration quality, and the ability to iterate quickly on retrieval strategies without infrastructure overhead. Production scaling is a secondary concern for the portfolio stage, but a clear migration path is required.

## Decision
Use ChromaDB for development and the portfolio demo, with a documented migration path to pgvector for production.

ChromaDB runs as a standalone service in the Docker Compose stack with persistent storage via a named Docker volume. The retriever layer accesses ChromaDB through an abstraction (`get_vectorstore()`) that returns a LangChain-compatible vectorstore interface, decoupling the retrieval logic from the specific vector database implementation.

The LangChain integration (`langchain-chroma`) is first-class and well-maintained, supporting metadata filtering, MMR search, and similarity score thresholds out of the box. This allows the hybrid retrieval pipeline (70% vector / 30% BM25 with cross-encoder reranking) to be developed and tested without fighting infrastructure issues.

## Consequences

### Positive
- **Zero-config Docker setup:** A single `docker compose up` brings ChromaDB online alongside PostgreSQL and Redis. No manual index creation, no extension installation, no schema migrations for vector tables.
- **Python-native API:** ChromaDB's client library feels natural in the async Python codebase. Collection management, upserts, and queries use idiomatic Python patterns.
- **Fast iteration:** Changing embedding dimensions, switching distance metrics, or rebuilding the entire collection takes seconds, not minutes. This is critical during the chunking and retrieval experimentation phase.
- **No external service dependencies:** Everything runs locally. No API keys, no cloud accounts, no network latency for vector operations.
- **First-class LangChain integration:** The `langchain-chroma` package supports all retriever features used by the hybrid pipeline, including metadata filtering for role-based chunk selection.

### Negative
- **No built-in backup or replication:** ChromaDB is single-node only. Data durability depends entirely on the Docker volume. A volume corruption event means re-ingesting all documents.
- **Limited production scaling:** ChromaDB does not support horizontal scaling, sharding, or multi-tenant isolation. For a production deployment with multiple concurrent users and large document sets, this becomes a bottleneck.
- **Separate service to manage:** Unlike pgvector, ChromaDB is an additional service in the Docker Compose stack. This means another container to monitor, another port to expose, and another failure point in the infrastructure.

### Migration Path
The retriever abstraction (`get_vectorstore()`) allows swapping ChromaDB for pgvector by changing only the vectorstore module. pgvector consolidates vector and relational data in a single PostgreSQL instance, reducing operational complexity from three data services (PostgreSQL + Redis + ChromaDB) to two (PostgreSQL + Redis). The migration involves: (1) installing the pgvector extension, (2) creating an Alembic migration for the embeddings table with a vector column, (3) implementing a new `PgVectorStore` class behind the same `get_vectorstore()` interface, and (4) re-ingesting documents. No changes to the retriever, reranker, or agent layers are required.
