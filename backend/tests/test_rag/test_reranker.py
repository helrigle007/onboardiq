"""Tests for the cross-encoder document reranker."""

import pytest

from app.rag.reranker import DocumentReranker
from app.rag.retriever import RetrievedChunk

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def reranker() -> DocumentReranker:
    """Module-scoped reranker to avoid reloading the model for each test."""
    return DocumentReranker()


def _make_chunk(content: str, chunk_id: str = "") -> RetrievedChunk:
    """Helper to create a RetrievedChunk for testing."""
    return RetrievedChunk(
        chunk_id=chunk_id or content[:16],
        content=content,
        original_content=content,
        metadata={},
        source_url="https://docs.stripe.com/test",
        section_path="Test > Section",
    )


# ── Tests ─────────────────────────────────────────────────────────────


class TestDocumentReranker:
    def test_reranking_changes_order(self, reranker):
        """Reranker produces a different ordering than the input."""
        query = "How to handle Stripe webhook signatures"
        chunks = [
            _make_chunk("The weather is sunny today", "irrelevant"),
            _make_chunk(
                "To verify webhook signatures, use stripe.Webhook.construct_event "
                "with the raw body, signature header, and your endpoint secret.",
                "relevant",
            ),
            _make_chunk(
                "Stripe charges a 2.9% + 30 cent fee per transaction.",
                "semi_relevant",
            ),
        ]

        reranked = reranker.rerank(query, chunks, top_k=3)

        # The webhook chunk should be ranked highest
        assert reranked[0].chunk_id == "relevant"
        # All chunks should have rerank_score set
        assert all(c.rerank_score is not None for c in reranked)

    def test_top_k_respected(self, reranker):
        """Output is truncated to top_k results."""
        query = "payment processing"
        chunks = [_make_chunk(f"Content about topic {i}", f"chunk_{i}") for i in range(10)]

        reranked = reranker.rerank(query, chunks, top_k=3)
        assert len(reranked) == 3

    def test_empty_input(self, reranker):
        """Empty chunk list returns empty result."""
        reranked = reranker.rerank("any query", [], top_k=5)
        assert reranked == []

    def test_single_chunk(self, reranker):
        """Single chunk is returned with score 1.0."""
        chunk = _make_chunk("Some content about payments")
        reranked = reranker.rerank("payments", [chunk], top_k=5)
        assert len(reranked) == 1
        assert reranked[0].rerank_score == 1.0

    def test_scores_are_descending(self, reranker):
        """Results are sorted by descending rerank_score."""
        query = "API authentication with keys"
        chunks = [
            _make_chunk("Use API keys for authentication. Store them securely.", "auth"),
            _make_chunk("Webhooks deliver events to your endpoint.", "webhook"),
            _make_chunk("Error codes indicate specific failure types.", "error"),
            _make_chunk("Set up your Stripe API key for authentication.", "setup"),
        ]

        reranked = reranker.rerank(query, chunks, top_k=4)
        scores = [c.rerank_score for c in reranked]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_larger_than_input(self, reranker):
        """If top_k > len(chunks), all chunks are returned."""
        chunks = [_make_chunk(f"Content {i}", f"c{i}") for i in range(3)]
        reranked = reranker.rerank("test", chunks, top_k=10)
        assert len(reranked) == 3
