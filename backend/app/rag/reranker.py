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

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from sentence_transformers import CrossEncoder

if TYPE_CHECKING:
    from app.rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class DocumentReranker:
    """Reranks retrieved chunks using a cross-encoder model."""

    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        logger.info("Loading cross-encoder model: %s", model_name)
        start = time.perf_counter()
        self._model = CrossEncoder(model_name)
        elapsed = time.perf_counter() - start
        logger.info("Cross-encoder loaded in %.2fs", elapsed)

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 20,
    ) -> list[RetrievedChunk]:
        """Rerank chunks by cross-encoder relevance score.

        Args:
            query: The search query.
            chunks: Candidate chunks from first-stage retrieval.
            top_k: Number of top results to return.

        Returns:
            Reranked chunks sorted by descending rerank_score, truncated to top_k.
        """
        if not chunks:
            return []

        if len(chunks) == 1:
            chunks[0].rerank_score = 1.0
            return chunks

        start = time.perf_counter()

        # Build query-document pairs for the cross-encoder
        pairs = [[query, chunk.content] for chunk in chunks]

        # Score all pairs
        scores = self._model.predict(pairs)

        # Attach scores and sort
        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)

        reranked = sorted(
            chunks, key=lambda c: c.rerank_score or 0.0, reverse=True
        )

        elapsed = time.perf_counter() - start
        logger.info(
            "Reranked %d chunks in %.3fs (top=%.4f, bottom=%.4f)",
            len(chunks), elapsed,
            reranked[0].rerank_score or 0.0,
            reranked[-1].rerank_score or 0.0,
        )

        return reranked[:top_k]
