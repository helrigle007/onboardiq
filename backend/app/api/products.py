"""Product endpoints with debug retrieval for the RAG pipeline."""

from fastapi import APIRouter, Query

from app.rag.retriever import HybridRetriever

router = APIRouter()


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
