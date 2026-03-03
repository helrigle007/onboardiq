"""Tests for the hybrid retriever.

Uses a mock ChromaDB backend and real BM25 index to test retrieval logic
without requiring running infrastructure.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.rag.retriever import HybridRetriever, RetrievedChunk

# ── Fixtures ──────────────────────────────────────────────────────────

MOCK_DOCS = [
    Document(
        page_content="Webhook endpoints receive POST requests from Stripe when events occur. "
        "You must verify the webhook signature using your endpoint secret.",
        metadata={
            "id": "doc_webhook",
            "topic": "webhooks",
            "source_url": "https://docs.stripe.com/webhooks",
            "section_path": "Webhooks > Endpoints",
            "original_content": "Webhook endpoints receive POST requests from Stripe.",
            "complexity": "concept",
        },
    ),
    Document(
        page_content="API keys authenticate your requests to the Stripe API. "
        "Keep your secret key safe and never expose it in client-side code.",
        metadata={
            "id": "doc_auth",
            "topic": "authentication",
            "source_url": "https://docs.stripe.com/authentication",
            "section_path": "Authentication > API Keys",
            "original_content": "API keys authenticate your requests to the Stripe API.",
            "complexity": "concept",
        },
    ),
    Document(
        page_content="Payment Intents represent your intent to collect payment from a customer. "
        "The PaymentIntent transitions through states: requires_payment_method, "
        "requires_confirmation, requires_action, processing, succeeded.",
        metadata={
            "id": "doc_payments",
            "topic": "payments",
            "source_url": "https://docs.stripe.com/payments",
            "section_path": "Payments > Payment Intents",
            "original_content": "Payment Intents represent your intent to collect payment.",
            "complexity": "concept",
        },
    ),
    Document(
        page_content="Error handling is critical for production Stripe integrations. "
        "Stripe uses HTTP status codes and error types including card_error, "
        "api_error, and invalid_request_error.",
        metadata={
            "id": "doc_errors",
            "topic": "errors",
            "source_url": "https://docs.stripe.com/error-handling",
            "section_path": "Error Handling > Error Types",
            "original_content": "Error handling is critical for production integrations.",
            "complexity": "concept",
        },
    ),
    Document(
        page_content="PCI compliance is mandatory for handling card data. "
        "Use Stripe.js and Elements to collect card details securely "
        "without them touching your server.",
        metadata={
            "id": "doc_security",
            "topic": "security",
            "source_url": "https://docs.stripe.com/security",
            "section_path": "Security > PCI Compliance",
            "original_content": "PCI compliance is mandatory for handling card data.",
            "complexity": "detail",
        },
    ),
]


def _mock_collection():
    """Create a mock ChromaDB collection that returns MOCK_DOCS."""
    collection = MagicMock()
    collection.get.return_value = {
        "ids": [doc.metadata["id"] for doc in MOCK_DOCS],
        "documents": [doc.page_content for doc in MOCK_DOCS],
        "metadatas": [doc.metadata for doc in MOCK_DOCS],
    }
    collection.count.return_value = len(MOCK_DOCS)
    return collection


def _mock_vectorstore():
    """Create a mock Chroma vectorstore."""
    vs = MagicMock()
    vs._collection = _mock_collection()
    # Return all docs with fake similarity scores
    vs.similarity_search_with_relevance_scores.return_value = [
        (doc, 0.9 - (i * 0.1)) for i, doc in enumerate(MOCK_DOCS)
    ]
    return vs


@pytest.fixture
def retriever():
    """Create a HybridRetriever with mocked dependencies."""
    with (
        patch("app.rag.retriever.get_vectorstore", return_value=_mock_vectorstore()),
        patch("app.rag.retriever.DocumentReranker") as mock_reranker_cls,
    ):
        # Mock reranker: just pass through with scores
        mock_reranker = MagicMock()

        def rerank_passthrough(query, chunks, top_k):
            for i, chunk in enumerate(chunks[:top_k]):
                chunk.rerank_score = 1.0 - (i * 0.05)
            return chunks[:top_k]

        mock_reranker.rerank.side_effect = rerank_passthrough
        mock_reranker_cls.return_value = mock_reranker

        ret = HybridRetriever(
            product="stripe",
            use_multi_query=False,  # Disable for unit tests (no API calls)
            final_top_k=5,
        )
        yield ret


# ── Tests ─────────────────────────────────────────────────────────────


class TestRetrievedChunk:
    def test_model_serialization(self):
        """RetrievedChunk can be serialized to dict."""
        chunk = RetrievedChunk(
            chunk_id="test_id",
            content="Test content",
            original_content="Test content",
            metadata={"topic": "test"},
            source_url="https://example.com",
            section_path="Test > Path",
            bm25_score=0.5,
            vector_score=0.8,
            rerank_score=0.7,
        )
        data = chunk.model_dump()
        assert data["chunk_id"] == "test_id"
        assert data["bm25_score"] == 0.5
        assert data["rerank_score"] == 0.7

    def test_optional_scores(self):
        """Scores default to None when not provided."""
        chunk = RetrievedChunk(
            chunk_id="test_id",
            content="Test",
            original_content="Test",
            metadata={},
            source_url="",
            section_path="",
        )
        assert chunk.bm25_score is None
        assert chunk.vector_score is None
        assert chunk.rerank_score is None


class TestHybridRetriever:
    @pytest.mark.asyncio
    async def test_bm25_returns_results(self, retriever):
        """BM25 search returns results for known terms."""
        retriever._build_bm25_index()
        results = retriever._bm25_search("webhook signature", top_k=3)
        assert len(results) > 0
        # Webhook doc should score highly
        contents = [doc.page_content for doc, _ in results]
        assert any("webhook" in c.lower() for c in contents)

    @pytest.mark.asyncio
    async def test_vector_retrieval_returns_results(self, retriever):
        """Vector search returns results from the vectorstore."""
        results = await retriever._vector_search("payment processing", top_k=3)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_hybrid_retrieval_combines_both(self, retriever):
        """Full hybrid retrieval returns results with multiple score types."""
        results = await retriever.retrieve("webhook security")
        assert len(results) > 0
        # Results should have rerank scores set
        assert all(c.rerank_score is not None for c in results)

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self, retriever):
        """Empty query returns no results."""
        results = await retriever.retrieve("")
        assert results == []

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty(self, retriever):
        """Whitespace-only query returns no results."""
        results = await retriever.retrieve("   ")
        assert results == []

    @pytest.mark.asyncio
    async def test_results_have_metadata(self, retriever):
        """Retrieved chunks carry source metadata."""
        results = await retriever.retrieve("API authentication")
        assert len(results) > 0
        for chunk in results:
            assert chunk.source_url != "" or chunk.section_path != ""

    @pytest.mark.asyncio
    async def test_final_top_k_respected(self, retriever):
        """Number of results does not exceed final_top_k."""
        retriever.final_top_k = 2
        results = await retriever.retrieve("stripe payments")
        assert len(results) <= 2

    def test_merge_results_deduplicates(self, retriever):
        """Merge combines BM25 and vector results without duplicates."""
        doc = MOCK_DOCS[0]
        bm25_results = [(doc, 0.8)]
        vector_results = [(doc, 0.9)]

        merged = retriever._merge_results(bm25_results, vector_results)
        # Same doc should appear once with both scores
        assert len(merged) == 1
        assert merged[0].bm25_score is not None
        assert merged[0].vector_score is not None

    def test_build_where_filter_single(self, retriever):
        """Single metadata filter produces correct ChromaDB where clause."""
        result = retriever._build_where_filter({"topic": "webhooks"})
        assert result == {"topic": {"$eq": "webhooks"}}

    def test_build_where_filter_multiple(self, retriever):
        """Multiple filters produce $and clause."""
        result = retriever._build_where_filter({"topic": "webhooks", "complexity": "concept"})
        assert "$and" in result

    def test_build_where_filter_none(self, retriever):
        """None filter returns None."""
        assert retriever._build_where_filter(None) is None

    def test_build_where_filter_section_path_prefix(self, retriever):
        """Section path filter uses $contains for prefix matching."""
        result = retriever._build_where_filter({"section_path": "Authentication"})
        assert result == {"section_path": {"$contains": "Authentication"}}
