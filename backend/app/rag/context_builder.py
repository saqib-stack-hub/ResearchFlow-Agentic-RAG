"""
ResearchFlow AI — Context Builder
Assembles the final context for LLM generation from reranked chunks.
Handles: deduplication, relevance filtering, token-length control,
metadata preservation, and citation preparation.
"""
import re
from hashlib import md5
from typing import Any, Dict, List, Optional, Tuple

import tiktoken
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import Citation

logger = get_logger(__name__)

# Use cl100k_base encoder (GPT-3.5/4 compatible)
_encoder = None


def get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """Count tokens in a text string."""
    try:
        return len(get_encoder().encode(text))
    except Exception:
        return len(text) // 4  # Rough approximation


def build_context(
    reranked: List[Tuple[Document, float]],
    min_relevance: float = 0.0,
    max_tokens: int = None,
) -> Dict[str, Any]:
    """
    Build LLM context from reranked document chunks.

    Steps:
      1. Remove low-relevance chunks
      2. Remove near-duplicate chunks
      3. Control total context length (token budget)
      4. Build context string with numbered citations
      5. Extract citation metadata

    Returns:
      context_str: Formatted context string for LLM
      citations: List of Citation objects
      num_chunks: Number of chunks included
      total_tokens: Estimated token count
    """
    max_tokens = max_tokens or settings.MAX_CONTEXT_TOKENS

    if not reranked:
        return {
            "context_str": "",
            "citations": [],
            "num_chunks": 0,
            "total_tokens": 0,
        }

    # Step 1: Filter low-relevance chunks
    relevant = [(doc, score) for doc, score in reranked if score >= min_relevance]

    # Step 2: Remove near-duplicates
    deduplicated = _deduplicate_by_content(relevant)

    # Step 3: Token budget control
    selected, total_tokens = _apply_token_budget(deduplicated, max_tokens)

    # Step 4 & 5: Build context string and citations
    context_parts = []
    citations = []

    for i, (doc, score) in enumerate(selected, start=1):
        filename = doc.metadata.get("filename", "unknown")
        page = doc.metadata.get("page", 0)
        chunk_id = doc.metadata.get("chunk_id", "")
        document_id = doc.metadata.get("document_id", "")

        # Format context block
        context_parts.append(
            f"[Source {i}] {filename} (Page {page + 1}):\n{doc.page_content}"
        )

        # Build citation
        citations.append(Citation(
            document_id=document_id,
            document=filename,
            page=int(page) + 1,  # Convert to 1-indexed for display
            chunk_id=chunk_id,
            excerpt=doc.page_content[:300].strip(),
            score=round(float(score), 4),
        ))

    context_str = "\n\n---\n\n".join(context_parts)

    logger.info(
        "context_built",
        input_chunks=len(reranked),
        relevant_chunks=len(relevant),
        deduplicated_chunks=len(deduplicated),
        selected_chunks=len(selected),
        total_tokens=total_tokens,
    )

    return {
        "context_str": context_str,
        "citations": citations,
        "num_chunks": len(selected),
        "total_tokens": total_tokens,
    }


def _deduplicate_by_content(
    chunks: List[Tuple[Document, float]],
    similarity_threshold: float = 0.85,
) -> List[Tuple[Document, float]]:
    """Remove near-duplicate chunks using Jaccard similarity."""
    if not chunks:
        return []

    result = [chunks[0]]

    for doc, score in chunks[1:]:
        words_new = set(doc.page_content.lower().split())
        is_duplicate = False

        for existing_doc, _ in result:
            words_existing = set(existing_doc.page_content.lower().split())
            if words_new and words_existing:
                intersection = words_new & words_existing
                union = words_new | words_existing
                jaccard = len(intersection) / len(union)
                if jaccard >= similarity_threshold:
                    is_duplicate = True
                    break

        if not is_duplicate:
            result.append((doc, score))

    return result


def _apply_token_budget(
    chunks: List[Tuple[Document, float]],
    max_tokens: int,
) -> Tuple[List[Tuple[Document, float]], int]:
    """
    Select chunks within token budget.
    Higher-scored chunks are already at the top (from reranking).
    """
    selected = []
    total = 0

    for doc, score in chunks:
        chunk_tokens = count_tokens(doc.page_content)
        if total + chunk_tokens <= max_tokens:
            selected.append((doc, score))
            total += chunk_tokens
        else:
            # Stop adding when budget exhausted
            if not selected:
                # Always include at least one chunk
                selected.append((doc, score))
                total += chunk_tokens
            break

    return selected, total
