"""
ResearchFlow AI — Advanced Retrieval
Hybrid BM25 + Vector search with MMR diversity filtering.
"""
import math
from hashlib import md5
from typing import List, Optional, Tuple

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.logging_config import get_logger, LatencyTracker
from app.rag.embedder import embed_query
from app.rag.vector_store import similarity_search

logger = get_logger(__name__)

# In-memory BM25 index per document corpus
_bm25_corpus: List[Document] = []
_bm25_index: Optional[BM25Okapi] = None


def update_bm25_index(documents: List[Document]) -> None:
    """Update the in-memory BM25 index with new documents."""
    global _bm25_corpus, _bm25_index
    _bm25_corpus.extend(documents)
    tokenized = [_tokenize(doc.page_content) for doc in _bm25_corpus]
    if tokenized:
        _bm25_index = BM25Okapi(tokenized)
        logger.info("bm25_index_updated", corpus_size=len(_bm25_corpus))


def _tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer for BM25."""
    return text.lower().split()


async def hybrid_retrieve(
    query: str,
    top_k: int = None,
    similarity_threshold: float = None,
    document_ids: Optional[List[str]] = None,
) -> List[Tuple[Document, float]]:
    """
    Hybrid retrieval: combines vector search + BM25 via Reciprocal Rank Fusion (RRF).
    Falls back gracefully to pure vector search if BM25 index is empty.
    """
    top_k = top_k or getattr(settings, "TOP_K", 4)
    similarity_threshold = similarity_threshold or getattr(settings, "SIMILARITY_THRESHOLD", 0.2)

    with LatencyTracker("hybrid_retrieve", logger) as tracker:
        # 1. Vector (semantic) search
        query_vector = await embed_query(query)
        vector_results = await similarity_search(
            query_vector=query_vector,
            top_k=top_k * 2,  # Over-retrieve for fusion
            score_threshold=0.0,  # Fetch raw results first for RRF
            document_ids=document_ids,
        )

        # 2. BM25 keyword search (if index available)
        bm25_results = _bm25_search(query, top_k * 2) if _bm25_index else []

        # 3. Reciprocal Rank Fusion
        if bm25_results and vector_results:
            fused = _reciprocal_rank_fusion(vector_results, bm25_results, k=60)
        else:
            fused = vector_results

        # 4. Safe Filtering (Do not drop all documents if RRF score is low)
        filtered = [(doc, score) for doc, score in fused if score >= (similarity_threshold * 0.5)]
        if not filtered and fused:
            filtered = fused[:top_k]  # Fallback to top fused candidates

        # 5. MMR for diversity
        diverse = mmr_rerank(query_vector, filtered, top_k=top_k, lambda_mult=0.7)

    logger.info(
        "hybrid_retrieval_complete",
        query_preview=query[:80],
        vector_results=len(vector_results),
        bm25_results=len(bm25_results),
        fused_results=len(fused),
        after_mmr=len(diverse),
        latency_ms=tracker.elapsed_ms,
    )

    return diverse


def _bm25_search(query: str, top_k: int) -> List[Tuple[Document, float]]:
    """Search BM25 index and return ranked results."""
    if not _bm25_index or not _bm25_corpus:
        return []

    tokens = _tokenize(query)
    scores = _bm25_index.get_scores(tokens)

    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for idx in ranked_indices:
        if scores[idx] > 0:
            results.append((_bm25_corpus[idx], float(scores[idx])))

    if results:
        max_score = results[0][1]
        if max_score > 0:
            results = [(doc, score / max_score) for doc, score in results]

    return results


def _reciprocal_rank_fusion(
    list1: List[Tuple[Document, float]],
    list2: List[Tuple[Document, float]],
    k: int = 60,
) -> List[Tuple[Document, float]]:
    """
    Reciprocal Rank Fusion (RRF) to merge two ranked lists.
    """
    scores: dict = {}
    doc_map: dict = {}

    def get_doc_key(doc: Document) -> str:
        return doc.metadata.get("chunk_id") or md5(doc.page_content[:100].encode()).hexdigest()

    for rank, (doc, _) in enumerate(list1):
        key = get_doc_key(doc)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        doc_map[key] = doc

    for rank, (doc, _) in enumerate(list2):
        key = get_doc_key(doc)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        doc_map[key] = doc

    sorted_keys = sorted(scores, key=scores.get, reverse=True)

    max_score = scores[sorted_keys[0]] if sorted_keys else 1.0
    return [(doc_map[k], scores[k] / max_score) for k in sorted_keys]


def mmr_rerank(
    query_vector: List[float],
    candidates: List[Tuple[Document, float]],
    top_k: int,
    lambda_mult: float = 0.7,
) -> List[Tuple[Document, float]]:
    """
    Maximum Marginal Relevance (MMR) for diversity.
    """
    if not candidates or top_k <= 0:
        return candidates

    if len(candidates) <= top_k:
        return candidates

    selected = []
    remaining = list(candidates)

    while len(selected) < top_k and remaining:
        if not selected:
            best = max(remaining, key=lambda x: x[1])
        else:
            def mmr_score(candidate: Tuple[Document, float]) -> float:
                doc, rel_score = candidate
                max_sim = max(
                    _text_overlap(doc.page_content, sel_doc.page_content)
                    for sel_doc, _ in selected
                )
                return lambda_mult * rel_score - (1 - lambda_mult) * max_sim

            best = max(remaining, key=mmr_score)

        selected.append(best)
        remaining.remove(best)

    return selected


def _text_overlap(text1: str, text2: str) -> float:
    """Approximate text overlap using Jaccard similarity of words."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)