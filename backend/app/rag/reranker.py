"""
ResearchFlow AI — Cross-Encoder Reranker
Uses sentence-transformers cross-encoder for precision reranking.
Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (fast, production-appropriate)
"""
from typing import List, Optional, Tuple
from langchain_core.documents import Document
from app.core.config import settings
from app.core.logging_config import get_logger, LatencyTracker

logger = get_logger(__name__)

_reranker = None


def get_reranker():
    """Load cross-encoder model (singleton, lazy-loaded)."""
    global _reranker
    if _reranker is None and settings.RERANKER_ENABLED:
        try:
            from sentence_transformers import CrossEncoder
            logger.info("loading_reranker", model=settings.RERANKER_MODEL)
            _reranker = CrossEncoder(settings.RERANKER_MODEL)
            logger.info("reranker_loaded", model=settings.RERANKER_MODEL)
        except Exception as e:
            logger.warning("reranker_load_failed", error=str(e), fallback="score_passthrough")
    return _reranker


def rerank_documents(
    query: str,
    candidates: List[Tuple[Document, float]],
    top_k: int = None,
) -> List[Tuple[Document, float]]:
    """
    Rerank candidate documents using cross-encoder.

    Pipeline:
      candidates (from vector/hybrid search)
        → cross-encoder scoring
        → sorted by rerank score
        → top_k returned

    Falls back to original scores if reranker unavailable.
    """
    if not candidates:
        return []

    top_k = top_k or settings.RERANK_TOP_K
    reranker = get_reranker()

    if not reranker or not settings.RERANKER_ENABLED:
        # Graceful fallback: just return top_k by original score
        logger.info("reranker_disabled_fallback", top_k=top_k)
        return sorted(candidates, key=lambda x: x[1], reverse=True)[:top_k]

    with LatencyTracker("reranking", logger) as tracker:
        # Prepare query-document pairs
        pairs = [(query, doc.page_content) for doc, _ in candidates]

        # Score all pairs
        scores = reranker.predict(pairs)

        # Combine with documents
        reranked = [(doc, float(score)) for (doc, _), score in zip(candidates, scores)]

        # Sort by rerank score (descending)
        reranked.sort(key=lambda x: x[1], reverse=True)

        # Take top_k
        result = reranked[:top_k]

    logger.info(
        "reranking_complete",
        input_candidates=len(candidates),
        output_candidates=len(result),
        top_score=result[0][1] if result else 0.0,
        latency_ms=tracker.elapsed_ms,
    )

    return result


def normalize_rerank_scores(
    reranked: List[Tuple[Document, float]],
) -> List[Tuple[Document, float]]:
    """
    Normalize cross-encoder scores to [0, 1] using sigmoid.
    Cross-encoder outputs raw logits — sigmoid maps them to probabilities.
    """
    import math

    def sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    return [(doc, sigmoid(score)) for doc, score in reranked]
