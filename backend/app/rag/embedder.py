"""
ResearchFlow AI — Embedding Provider
Supports OpenAI embeddings (default) with configurable model.
Designed to be provider-swappable via environment config.
"""
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.logging_config import get_logger, LatencyTracker

logger = get_logger(__name__)

_embedder = None


def get_embedder():
    """Get or create the embedding model (singleton)."""
    global _embedder
    if _embedder is None:
        _embedder = _create_embedder()
    return _embedder


def _create_embedder():
    """Create the appropriate embedding model based on configuration."""
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "openai":
        logger.info("initializing_embedder", provider="openai", model=settings.EMBEDDING_MODEL)
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    else:
        # Default fallback to OpenAI
        logger.warning("unknown_embedding_provider", provider=provider, fallback="openai")
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts with retry logic.
    Returns list of embedding vectors.
    """
    embedder = get_embedder()
    with LatencyTracker("embed_texts", logger) as tracker:
        # OpenAI embeddings support async via aembed_documents
        vectors = await embedder.aembed_documents(texts)
    logger.info(
        "embeddings_generated",
        num_texts=len(texts),
        dimension=len(vectors[0]) if vectors else 0,
        latency_ms=tracker.elapsed_ms,
    )
    return vectors


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    embedder = get_embedder()
    with LatencyTracker("embed_query", logger) as tracker:
        vector = await embedder.aembed_query(text)
    return vector
