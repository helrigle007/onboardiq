import os

from app.config import Settings


def setup_tracing(settings: Settings) -> None:
    """Configure LangSmith tracing via environment variables."""
    if settings.langsmith_api_key and settings.langsmith_tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
