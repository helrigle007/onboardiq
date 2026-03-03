"""
Embedding configuration for OnboardIQ.

Primary: Voyage AI (voyage-3) — recommended by Anthropic for Claude-based RAG.
Fallback: sentence-transformers/all-MiniLM-L6-v2 (local, free, for dev without API key)

The embedding function is used by both the ingestion pipeline and the retriever.
"""

import asyncio
import logging
import time

from langchain_core.embeddings import Embeddings

from app.config import get_settings

logger = logging.getLogger(__name__)

# Embedding dimensions by model
EMBEDDING_DIMENSIONS: dict[str, int] = {
    "voyage-3": 1024,
    "all-MiniLM-L6-v2": 384,
}


def get_embedding_function() -> Embeddings:
    """Return a LangChain-compatible embedding function.

    Uses Voyage AI if VOYAGE_API_KEY is set, otherwise falls back to
    a local HuggingFace model (all-MiniLM-L6-v2).
    """
    settings = get_settings()

    if settings.voyage_api_key:
        from langchain_voyageai import VoyageAIEmbeddings

        logger.info(
            "Using Voyage AI embeddings (model=%s)",
            settings.embedding_model,
        )
        return VoyageAIEmbeddings(
            model=settings.embedding_model,
            voyage_api_key=settings.voyage_api_key,
        )

    logger.warning(
        "VOYAGE_API_KEY not set — falling back to local HuggingFace "
        "embeddings (all-MiniLM-L6-v2). Embedding quality will be lower."
    )
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def get_embedding_dimension() -> int:
    """Return the embedding dimension for the active model."""
    settings = get_settings()
    if settings.voyage_api_key:
        return EMBEDDING_DIMENSIONS.get(settings.embedding_model, 1024)
    return EMBEDDING_DIMENSIONS["all-MiniLM-L6-v2"]


async def embed_with_retry(
    embedding_fn: Embeddings,
    texts: list[str],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> list[list[float]]:
    """Embed texts with exponential backoff retry.

    Args:
        embedding_fn: LangChain embedding function.
        texts: Texts to embed.
        max_retries: Maximum number of retries.
        base_delay: Base delay in seconds (doubled each retry).

    Returns:
        List of embedding vectors.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            start = time.perf_counter()
            if hasattr(embedding_fn, "aembed_documents"):
                embeddings = await embedding_fn.aembed_documents(texts)
            else:
                embeddings = await asyncio.to_thread(
                    embedding_fn.embed_documents, texts
                )
            elapsed = time.perf_counter() - start
            logger.debug(
                "Embedded %d texts in %.2fs (attempt %d)",
                len(texts), elapsed, attempt + 1,
            )
            return embeddings
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Embedding attempt %d/%d failed: %s. "
                    "Retrying in %.1fs...",
                    attempt + 1, max_retries + 1, str(e), delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Embedding failed after %d attempts: %s",
                    max_retries + 1, str(e),
                )

    raise last_error  # type: ignore[misc]
