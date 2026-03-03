"""
Usage: python -m scripts.ingest_stripe_docs

Downloads and ingests Stripe documentation into ChromaDB.
Run this once before starting the application.

Options:
    --skip-enrichment   Skip Claude Haiku contextual enrichment (faster, no API calls)
"""

import asyncio
import logging
import sys

from app.rag.ingestion import run_ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    skip_enrichment = "--skip-enrichment" in sys.argv

    logger.info("Starting Stripe documentation ingestion...")
    if skip_enrichment:
        logger.info("Contextual enrichment DISABLED (--skip-enrichment flag)")

    stats = await run_ingestion(product="stripe", skip_enrichment=skip_enrichment)

    logger.info("=" * 60)
    logger.info("Ingestion Summary")
    logger.info("=" * 60)
    for key, value in stats.items():
        logger.info("  %-20s %s", key, value)
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
