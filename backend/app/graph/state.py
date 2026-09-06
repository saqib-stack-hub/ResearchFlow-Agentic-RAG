"""
ResearchFlow AI — LangGraph State Definition
Typed state dictionary shared across all graph nodes.
"""
from typing import Any, Dict, List, Optional, TypedDict
from langchain_core.documents import Document
from app.models.schemas import Citation


class GraphState(TypedDict):
    """
    Shared state for the ResearchFlow LangGraph workflow.
    Each node reads from and writes to this state.
    """

    # ── Input ─────────────────────────────────────────────────
    query: str                                  # Original user query
    session_id: str                             # Chat session ID
    document_ids: Optional[List[str]]          # Restrict to specific docs

    # ── Query Analysis ────────────────────────────────────────
    query_analysis: Optional[Dict[str, Any]]   # Output from QueryAnalyzer
    rewritten_query: Optional[str]             # Query after rewriting

    # ── Retrieval ─────────────────────────────────────────────
    retrieved_docs: List[Dict[str, Any]]        # Raw retrieved chunks with scores
    reranked_docs: List[Dict[str, Any]]         # After reranking
    context_str: str                            # Formatted context for LLM
    retrieval_score: float                      # Best retrieval score

    # ── Relevance Grading ─────────────────────────────────────
    relevance_grades: List[Dict[str, Any]]      # Per-chunk relevance judgments
    has_relevant_docs: bool                     # Whether any docs are relevant

    # ── Generation ────────────────────────────────────────────
    answer: str                                 # LLM-generated answer
    citations: List[Dict[str, Any]]             # Extracted citations

    # ── Citation Check ────────────────────────────────────────
    citation_check: Optional[Dict[str, Any]]    # Citation verification result
    is_hallucination: bool                      # Whether answer is hallucinated

    # ── Routing / Control ─────────────────────────────────────
    retry_count: int                            # Number of retries so far
    graph_path: List[str]                       # Nodes traversed (for logging)
    processing_steps: List[str]                 # Human-readable progress steps
    error: Optional[str]                        # Error message if any
