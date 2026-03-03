from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.infrastructure.database import close_db, init_db
from app.infrastructure.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()
    setup_tracing(settings)
    yield
    await close_db()


def create_app() -> FastAPI:
    get_settings()

    app = FastAPI(
        title="OnboardIQ",
        description="Role-adaptive SaaS onboarding guide generator",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()
