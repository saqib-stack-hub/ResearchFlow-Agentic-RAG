"""
ResearchFlow AI — Retriever Node
Executes hybrid retrieval + reranking and updates graph state.
"""
import time
from typing import Any, Dict, List
from langchain_core.documents import Document
from app.core.config import settings
from app.core.logging_config import get_logger
from app.graph.state import GraphState
from app.rag.retriever import hybrid_retrieve
from app.rag.reranker import rerank_documents, normalize_rerank_scores
from app.rag.context_builder import build_context

logger = get_logger(__name__)


async def retriever_node(state: GraphState) -> Dict[str, Any]:
    """
    LangGraph node: Retrieve relevant document chunks.
    Uses rewritten_query if available (after retry), else original query.
    Updates: retrieved_docs, reranked_docs, context_str, retrieval_score, citations
    """
    # Use rewritten query if this is a retry
    query = state.get("rewritten_query") or state["query"]
    document_ids = state.get("document_ids")

    logger.info(
        "retriever_start",
        query_preview=query[:80],
        retry_count=state.get("retry_count", 0),
    )

    try:
        # Step 1: Hybrid retrieval (vector + BM25 + MMR)
        t0 = time.perf_counter()
        candidates = await hybrid_retrieve(
            query=query,
            top_k=settings.TOP_K,
            similarity_threshold=settings.SIMILARITY_THRESHOLD,
            document_ids=[str(d) for d in document_ids] if document_ids else None,
        )
        retrieval_latency = (time.perf_counter() - t0) * 1000

        # Step 2: Rerank candidates
        t1 = time.perf_counter()
        reranked = rerank_documents(query, candidates, top_k=settings.RERANK_TOP_K)
        reranked = normalize_rerank_scores(reranked)
        reranking_latency = (time.perf_counter() - t1) * 1000

        # Step 3: Build context
        context_result = build_context(reranked, min_relevance=0.0, max_tokens=settings.MAX_CONTEXT_TOKENS)

        # Serialize docs for state (LangGraph state must be JSON-serializable)
        retrieved_docs_serialized = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in candidates
        ]

        reranked_docs_serialized = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in reranked
        ]

        retrieval_score = reranked[0][1] if reranked else 0.0
        citations_serialized = [c.model_dump() for c in context_result["citations"]]

        logger.info(
            "retriever_complete",
            candidates=len(candidates),
            reranked=len(reranked),
            retrieval_score=round(retrieval_score, 3),
            retrieval_latency_ms=round(retrieval_latency, 2),
            reranking_latency_ms=round(reranking_latency, 2),
        )

    except Exception as e:
        logger.error("retriever_failed", error=str(e))
        retrieved_docs_serialized = []
        reranked_docs_serialized = []
        context_result = {"context_str": "", "citations": [], "num_chunks": 0, "total_tokens": 0}
        retrieval_score = 0.0
        citations_serialized = []

    graph_path = state.get("graph_path", []) + ["retriever"]
    processing_steps = state.get("processing_steps", []) + ["Searching your documents..."]

    return {
        "retrieved_docs": retrieved_docs_serialized,
        "reranked_docs": reranked_docs_serialized,
        "context_str": context_result["context_str"],
        "retrieval_score": retrieval_score,
        "citations": citations_serialized,
        "graph_path": graph_path,
        "processing_steps": processing_steps,
    }
