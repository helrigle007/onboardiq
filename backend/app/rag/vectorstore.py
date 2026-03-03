"""
ChromaDB vector store wrapper for OnboardIQ.

Manages per-product document collections with batch upsert,
deduplication via content hashing, and collection statistics.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.rag.embeddings import get_embedding_function

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


def _get_chroma_client() -> chromadb.HttpClient:
    """Return a ChromaDB HTTP client connected to the configured host."""
    settings = get_settings()
    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )


def _collection_name(product: str) -> str:
    """Derive collection name from product identifier."""
    return f"{product}_docs"


def _content_hash(text: str) -> str:
    """Generate a deterministic ID from content to prevent duplicates."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def get_vectorstore(product: str) -> Chroma:
    """Return a LangChain Chroma vectorstore for the given product.

    Args:
        product: Product identifier (e.g., "stripe").

    Returns:
        A Chroma vectorstore backed by the HTTP client.
    """
    return Chroma(
        collection_name=_collection_name(product),
        embedding_function=get_embedding_function(),
        client=_get_chroma_client(),
    )


def add_documents(product: str, documents: list[Document]) -> int:
    """Batch upsert documents into the product's ChromaDB collection.

    Generates deterministic IDs from content hashes to prevent duplicates.
    Processes in batches of 100.

    Args:
        product: Product identifier (e.g., "stripe").
        documents: LangChain Document objects to store.

    Returns:
        Number of documents upserted.
    """
    if not documents:
        return 0

    vectorstore = get_vectorstore(product)
    total = len(documents)

    for batch_start in range(0, total, _BATCH_SIZE):
        batch = documents[batch_start : batch_start + _BATCH_SIZE]
        ids = [_content_hash(doc.page_content) for doc in batch]

        vectorstore.add_documents(documents=batch, ids=ids)
        logger.info(
            "Upserted batch %d-%d of %d documents into %s",
            batch_start + 1,
            min(batch_start + len(batch), total),
            total,
            _collection_name(product),
        )

    logger.info(
        "Completed upsert: %d documents into %s",
        total, _collection_name(product),
    )
    return total


def get_collection_stats(product: str) -> dict[str, Any]:
    """Return statistics for a product's document collection.

    Args:
        product: Product identifier (e.g., "stripe").

    Returns:
        Dict with count and metadata summary.
    """
    try:
        client = _get_chroma_client()
        name = _collection_name(product)
        collection = client.get_or_create_collection(name)
        count = collection.count()

        # Sample metadata from first few docs for summary
        topics: set[str] = set()
        if count > 0:
            peek = collection.peek(limit=min(count, 50))
            if peek and peek.get("metadatas"):
                for meta in peek["metadatas"]:
                    if meta and "topic" in meta:
                        topics.add(meta["topic"])

        return {
            "collection": name,
            "document_count": count,
            "topics": sorted(topics),
        }
    except Exception as e:
        logger.warning(
            "Failed to get collection stats for %s: %s", product, str(e),
        )
        return {
            "collection": _collection_name(product),
            "document_count": 0,
            "topics": [],
            "error": str(e),
        }
