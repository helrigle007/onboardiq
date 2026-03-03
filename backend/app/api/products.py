"""Product endpoints with debug retrieval for the RAG pipeline."""

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ProductInfo, ProductListResponse, UserRole
from app.rag.retriever import HybridRetriever

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
