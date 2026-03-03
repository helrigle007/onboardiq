from fastapi import APIRouter
from app.api import guides, products, evaluations, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(guides.router, prefix="/api/guides", tags=["guides"])
api_router.include_router(products.router, prefix="/api/products", tags=["products"])
api_router.include_router(evaluations.router, prefix="/api/evaluations", tags=["evaluations"])
