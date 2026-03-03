from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/api/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "models": {
            "generation": settings.generation_model,
            "evaluation": settings.evaluation_model,
            "fast": settings.fast_model,
        },
    }
