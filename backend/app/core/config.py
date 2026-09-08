"""
ResearchFlow AI — Application Configuration
All settings loaded from environment variables with sensible defaults.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "ResearchFlow AI"
    APP_VERSION: str = "1.0.0"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False

    # ── Server ──────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # ── CORS ────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://researchflow:researchflow_pass@localhost:5432/researchflow_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL: int = 3600

    # ── Vector Database (Qdrant) ─────────────────────────────────
    VECTOR_DB_URL: str = "http://localhost:6333"
    VECTOR_DB_COLLECTION: str = "researchflow_docs_v3"
    VECTOR_DB_API_KEY: Optional[str] = None

    # ── LLM ──────────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2000
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # ── Embeddings ───────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "huggingface"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    HUGGINGFACE_API_KEY: Optional[str] = None

    # ── RAG Configuration ─────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 10
    SIMILARITY_THRESHOLD: float = 0.3
    RERANK_TOP_K: int = 5
    MAX_CONTEXT_TOKENS: int = 4000
    MAX_RETRIES: int = 2

    # ── Reranker ──────────────────────────────────────────────────
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_ENABLED: bool = True

    # ── Document Upload ───────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt"
    UPLOAD_DIR: str = "/app/data/uploads"

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [e.strip().lower() for e in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    # ── Rate Limiting ─────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # ── Logging ───────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — call once, reuse everywhere."""
    return Settings()


settings = get_settings()