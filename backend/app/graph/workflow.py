"""
ResearchFlow AI — LangGraph Workflow Definition

Graph structure:
  START
    ↓
  QueryAnalyzer
    ↓
  [if needs_retrieval] → Retriever → RelevanceGrader
                                         ↓
                               ┌──────────────────────┐
                               │ has_relevant_docs?    │
                               └──────────────────────┘
                              YES ↓              ↓ NO (retry < max)
                          AnswerGenerator    QueryRewriter
                                ↓                 ↓
                          CitationChecker    Retriever (retry)
                                ↓
                          FinalResponse
    ↓
  [if not needs_retrieval] → AnswerGenerator → FinalResponse
"""
from langgraph.graph import StateGraph, END
from app.graph.state import GraphState
from app.agents.query_analyzer import query_analyzer_node
from app.agents.retriever_node import retriever_node
from app.agents.relevance_grader import relevance_grader_node, route_after_grading
from app.agents.query_rewriter import query_rewriter_node
from app.agents.answer_generator import answer_generator_node
from app.agents.citation_checker import citation_checker_node, final_response_node
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def route_after_analysis(state: GraphState) -> str:
    """Route after query analysis — skip retrieval for general questions."""
    query_analysis = state.get("query_analysis", {})
    if not query_analysis.get("needs_retrieval", True):
        return "answer_generator"
    return "retriever"


def build_workflow() -> StateGraph:
    """Build and compile the LangGraph workflow."""

    workflow = StateGraph(GraphState)

    # ── Add Nodes ────────────────────────────────────────────────
    workflow.add_node("query_analyzer", query_analyzer_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("relevance_grader", relevance_grader_node)
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("answer_generator", answer_generator_node)
    workflow.add_node("citation_checker", citation_checker_node)
    workflow.add_node("final_response", final_response_node)

    # ── Set Entry Point ────────────────────────────────────────────
    workflow.set_entry_point("query_analyzer")

    # ── Conditional Edge: After Query Analyzer ─────────────────────
    workflow.add_conditional_edges(
        "query_analyzer",
        route_after_analysis,
        {
            "retriever": "retriever",
            "answer_generator": "answer_generator",
        },
    )

    # ── Linear Edge: Retriever → Relevance Grader ──────────────────
    workflow.add_edge("retriever", "relevance_grader")

    # ── Conditional Edge: After Relevance Grader ───────────────────
    workflow.add_conditional_edges(
        "relevance_grader",
        route_after_grading,
        {
            "answer_generator": "answer_generator",
            "query_rewriter": "query_rewriter",
        },
    )

    # ── Linear Edge: Query Rewriter → Retriever (retry) ───────────
    workflow.add_edge("query_rewriter", "retriever")

    # ── Linear Edges: Generation → Verification → Final ───────────
    workflow.add_edge("answer_generator", "citation_checker")
    workflow.add_edge("citation_checker", "final_response")
    workflow.add_edge("final_response", END)

    logger.info("langgraph_workflow_built")
    return workflow.compile()


# Compile the workflow at import time (singleton)
_compiled_workflow = None


def get_workflow():
    """Get or create the compiled LangGraph workflow."""
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = build_workflow()
    return _compiled_workflow


async def run_workflow(
    query: str,
    session_id: str,
    document_ids=None,
) -> GraphState:
    """
    Execute the full LangGraph workflow for a given query.

    Args:
        query: User question
        session_id: Chat session ID
        document_ids: Optional list of document IDs to restrict search

    Returns:
        Final GraphState with answer, citations, and graph_path
    """
    workflow = get_workflow()

    initial_state: GraphState = {
        "query": query,
        "session_id": session_id,
        "document_ids": document_ids,
        "query_analysis": None,
        "rewritten_query": None,
        "retrieved_docs": [],
        "reranked_docs": [],
        "context_str": "",
        "retrieval_score": 0.0,
        "relevance_grades": [],
        "has_relevant_docs": False,
        "answer": "",
        "citations": [],
        "citation_check": None,
        "is_hallucination": False,
        "retry_count": 0,
        "graph_path": [],
        "processing_steps": [],
        "error": None,
    }

    logger.info("workflow_start", query_preview=query[:80], session_id=session_id)

    try:
        final_state = await workflow.ainvoke(initial_state)
        logger.info(
            "workflow_complete",
            graph_path=final_state.get("graph_path", []),
            retry_count=final_state.get("retry_count", 0),
            num_citations=len(final_state.get("citations", [])),
        )
        return final_state
    except Exception as e:
        logger.error("workflow_failed", error=str(e))
        # Return error state
        initial_state["answer"] = "I encountered an error processing your request. Please try again."
        initial_state["error"] = str(e)
        return initial_state
