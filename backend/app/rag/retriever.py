"""
Hybrid retriever combining BM25 keyword search with ChromaDB vector search.

Two-stage retrieval:
  Stage 1: BM25 (keyword, 30%) + ChromaDB (semantic, 70%)
  Stage 2: Cross-encoder reranking for precision

Also supports MultiQuery expansion via Claude Haiku for improved recall.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from pydantic import BaseModel
from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.rag.reranker import DocumentReranker
from app.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


class RetrievedChunk(BaseModel):
    """A chunk returned from the hybrid retriever."""

    chunk_id: str
    content: str
    original_content: str
    metadata: dict[str, Any]
    bm25_score: float | None = None
    vector_score: float | None = None
    rerank_score: float | None = None
    source_url: str
    section_path: str


class HybridRetriever:
    """Two-stage hybrid retrieval with cross-encoder reranking."""

    def __init__(
        self,
        product: str,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
        initial_top_k: int = 50,
        final_top_k: int = 20,
        use_multi_query: bool = True,
    ) -> None:
        self.product = product
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.initial_top_k = initial_top_k
        self.final_top_k = final_top_k
        self.use_multi_query = use_multi_query

        self._vectorstore = get_vectorstore(product)
        self._reranker = DocumentReranker()

        # BM25 index: built lazily on first retrieve call
        self._bm25: BM25Okapi | None = None
        self._bm25_docs: list[Document] = []

    def _build_bm25_index(self) -> None:
        """Build BM25 index from documents in ChromaDB."""
        start = time.perf_counter()

        collection = self._vectorstore._collection
        result = collection.get(include=["documents", "metadatas"])

        if not result["documents"]:
            logger.warning("No documents in collection for BM25 index")
            self._bm25_docs = []
            self._bm25 = None
            return

        self._bm25_docs = []
        for doc_text, meta, doc_id in zip(
            result["documents"], result["metadatas"], result["ids"]
        ):
            self._bm25_docs.append(
                Document(
                    page_content=doc_text or "",
                    metadata={**(meta or {}), "id": doc_id},
                )
            )

        tokenized = [
            doc.page_content.lower().split()
            for doc in self._bm25_docs
        ]
        self._bm25 = BM25Okapi(tokenized)

        elapsed = time.perf_counter() - start
        logger.info(
            "Built BM25 index over %d documents in %.2fs",
            len(self._bm25_docs), elapsed,
        )

    def _bm25_search(
        self, query: str, top_k: int
    ) -> list[tuple[Document, float]]:
        """Search with BM25 and return (document, score) pairs."""
        if self._bm25 is None or not self._bm25_docs:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25.get_scores(tokenized_query)

        scored = list(zip(self._bm25_docs, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        """Search ChromaDB and return (document, score) pairs."""
        where_filter = self._build_where_filter(metadata_filter)
        results = self._vectorstore.similarity_search_with_relevance_scores(
            query=query,
            k=top_k,
            **({"filter": where_filter} if where_filter else {}),
        )
        return results

    @staticmethod
    def _build_where_filter(
        metadata_filter: dict[str, Any] | None,
    ) -> dict | None:
        """Build ChromaDB where filter from metadata filter dict."""
        if not metadata_filter:
            return None

        conditions: list[dict] = []
        for key, value in metadata_filter.items():
            if key == "section_path" and isinstance(value, str):
                conditions.append({key: {"$contains": value}})
            else:
                conditions.append({key: {"$eq": value}})

        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    async def _generate_multi_queries(self, query: str) -> list[str]:
        """Use Claude Haiku to generate query variations."""
        if not self.use_multi_query:
            return [query]

        try:
            settings = get_settings()
            llm = ChatAnthropic(
                model=settings.fast_model,
                api_key=settings.anthropic_api_key,
                max_tokens=200,
                temperature=0.3,
            )

            prompt = (
                "Generate 2 alternative search queries for the following "
                "query. The first should rephrase using different "
                "terminology. The second should rephrase as a how-to "
                "question.\n\n"
                f"Original query: {query}\n\n"
                "Return ONLY the 2 queries, one per line, no numbering."
            )

            response = await llm.ainvoke(prompt)
            lines = [
                line.strip()
                for line in response.content.strip().splitlines()
                if line.strip()
            ]
            queries = [query] + lines[:2]
            logger.info(
                "MultiQuery expansion: %s → %s", query, queries
            )
            return queries

        except Exception as e:
            logger.warning(
                "MultiQuery expansion failed: %s. Using original.",
                str(e),
            )
            return [query]

    def _merge_results(
        self,
        bm25_results: list[tuple[Document, float]],
        vector_results: list[tuple[Document, float]],
    ) -> list[RetrievedChunk]:
        """Merge BM25 and vector results with weighted scoring."""
        bm25_max = max(
            (s for _, s in bm25_results), default=1.0
        ) or 1.0
        vector_max = max(
            (s for _, s in vector_results), default=1.0
        ) or 1.0

        seen: dict[str, RetrievedChunk] = {}

        for doc, score in bm25_results:
            norm_score = score / bm25_max
            chunk_id = doc.metadata.get(
                "id", str(hash(doc.page_content))
            )
            if chunk_id not in seen:
                seen[chunk_id] = RetrievedChunk(
                    chunk_id=chunk_id,
                    content=doc.page_content,
                    original_content=doc.metadata.get(
                        "original_content", doc.page_content
                    ),
                    metadata=doc.metadata,
                    bm25_score=norm_score,
                    source_url=doc.metadata.get("source_url", ""),
                    section_path=doc.metadata.get("section_path", ""),
                )
            else:
                seen[chunk_id].bm25_score = norm_score

        for doc, score in vector_results:
            chunk_id = doc.metadata.get(
                "id", str(hash(doc.page_content))
            )
            norm_score = score / vector_max if vector_max else 0.0
            if chunk_id not in seen:
                seen[chunk_id] = RetrievedChunk(
                    chunk_id=chunk_id,
                    content=doc.page_content,
                    original_content=doc.metadata.get(
                        "original_content", doc.page_content
                    ),
                    metadata=doc.metadata,
                    vector_score=norm_score,
                    source_url=doc.metadata.get("source_url", ""),
                    section_path=doc.metadata.get("section_path", ""),
                )
            else:
                seen[chunk_id].vector_score = norm_score

        results = list(seen.values())
        for chunk in results:
            bm25_s = chunk.bm25_score or 0.0
            vector_s = chunk.vector_score or 0.0
            chunk.rerank_score = (
                self.bm25_weight * bm25_s
                + self.vector_weight * vector_s
            )

        results.sort(
            key=lambda c: c.rerank_score or 0.0, reverse=True
        )
        return results

    async def retrieve(
        self,
        query: str,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Run the full hybrid retrieval pipeline.

        1. (Optional) MultiQuery expansion
        2. BM25 keyword + ChromaDB vector search
        3. Merge and weight results
        4. Cross-encoder reranking
        """
        if not query.strip():
            return []

        start = time.perf_counter()

        if self._bm25 is None:
            self._build_bm25_index()

        # Stage 0: MultiQuery expansion
        queries = await self._generate_multi_queries(query)

        # Stage 1: BM25 + Vector search across all queries
        all_bm25: list[tuple[Document, float]] = []
        all_vector: list[tuple[Document, float]] = []

        for q in queries:
            bm25_results = self._bm25_search(q, self.initial_top_k)
            vector_results = await self._vector_search(
                q, self.initial_top_k, metadata_filter
            )
            all_bm25.extend(bm25_results)
            all_vector.extend(vector_results)

        # Stage 2: Merge with weighted scoring
        merged = self._merge_results(all_bm25, all_vector)
        candidates = merged[: self.initial_top_k]

        logger.info(
            "Stage 1: %d BM25 + %d vector → %d candidates",
            len(all_bm25), len(all_vector), len(candidates),
        )

        # Stage 3: Cross-encoder reranking
        if candidates:
            for c in candidates:
                c.rerank_score = None
            reranked = self._reranker.rerank(
                query, candidates, self.final_top_k
            )
        else:
            reranked = []

        elapsed = time.perf_counter() - start
        logger.info(
            "Retrieval complete: query=%r → %d results in %.2fs",
            query[:50], len(reranked), elapsed,
        )

        return reranked
