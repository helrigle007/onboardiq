"""Product endpoints with debug retrieval and ingestion trigger."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ProductInfo, ProductListResponse, UserRole
from app.rag.ingestion import run_ingestion
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)

router = APIRouter()

# Static product registry for MVP
PRODUCTS = {
    "stripe": ProductInfo(
        id="stripe",
        name="Stripe",
        description="Payment processing platform for internet businesses",
        doc_count=6,
        chunk_count=0,  # Updated at runtime after ingestion
        available_roles=[
            UserRole.FRONTEND_DEVELOPER,
            UserRole.BACKEND_DEVELOPER,
            UserRole.SECURITY_ENGINEER,
            UserRole.DEVOPS_ENGINEER,
            UserRole.PRODUCT_MANAGER,
            UserRole.TEAM_LEAD,
        ],
    ),
}


@router.get("/", response_model=ProductListResponse)
async def list_products():
    return ProductListResponse(products=list(PRODUCTS.values()))


@router.post("/{product_id}/ingest")
async def ingest_product_docs(
    product_id: str,
    skip_enrichment: bool = Query(True, description="Skip contextual enrichment to save costs"),
):
    """Trigger document ingestion for a product. Populates ChromaDB."""
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")

    logger.info("Starting ingestion for product: %s", product_id)
    stats = await run_ingestion(product=product_id, skip_enrichment=skip_enrichment)
    logger.info("Ingestion complete: %s", stats)
    return {"status": "complete", "stats": stats}


@router.get("/debug/retrieve")
async def debug_retrieve(
    query: str = Query(..., description="Search query"),
    product: str = Query("stripe", description="Product to search"),
    top_k: int = Query(5, ge=1, le=50, description="Number of results"),
):
    """Debug endpoint: test retrieval pipeline end-to-end."""
    retriever = HybridRetriever(product=product, final_top_k=top_k)
    chunks = await retriever.retrieve(query)
    return {
        "query": query,
        "product": product,
        "num_results": len(chunks),
        "results": [c.model_dump() for c in chunks],
    }


@router.get("/{product_id}", response_model=ProductInfo)
async def get_product(product_id: str):
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    return PRODUCTS[product_id]
