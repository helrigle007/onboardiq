from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str
    voyage_api_key: str = ""
    langsmith_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://onboardiq:onboardiq@localhost:5432/onboardiq"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # LangSmith
    langsmith_project: str = "onboardiq"
    langsmith_tracing: bool = True

    # Generation tuning
    eval_threshold: float = 0.7
    max_regenerations: int = 2
    guide_sections_count: int = 6
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 20

    # Models
    generation_model: str = "claude-sonnet-4-20250514"
    evaluation_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "voyage-3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
