"""
ResearchFlow AI — Free Local Embedding Provider
Uses HuggingFace HuggingFaceEmbeddings (all-MiniLM-L6-v2) for zero-cost local embeddings.
"""
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_community.embeddings import HuggingFaceEmbeddings
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
    """Create local HuggingFace embedding model."""
    logger.info("initializing_embedder", provider="huggingface", model="all-MiniLM-L6-v2")
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts locally with retry logic.
    Returns list of embedding vectors.
    """
    embedder = get_embedder()
    with LatencyTracker("embed_texts", logger) as tracker:
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
    """Embed a single query string locally."""
    embedder = get_embedder()
    with LatencyTracker("embed_query", logger) as tracker:
        vector = await embedder.aembed_query(text)
    return vector