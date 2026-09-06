"""
ResearchFlow AI — Relevance Grader Agent
Grades each retrieved chunk for relevance to the query using LLM.
"""
import json
from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.core.logging_config import get_logger
from app.graph.state import GraphState

logger = get_logger(__name__)

RELEVANCE_GRADER_SYSTEM = """You are a relevance grader for a RAG system.
Given a user question and a document chunk, determine if the chunk is relevant to answering the question.

Return ONLY JSON:
{
  "is_relevant": true/false,
  "relevance_score": 0.0-1.0,
  "reason": "brief reason"
}

A chunk is relevant if it contains information that would help answer the question.
Be strict — if the chunk doesn't contain useful information for the question, mark it as not relevant."""


async def relevance_grader_node(state: GraphState) -> Dict[str, Any]:
    """
    LangGraph node: Grade each retrieved document for relevance.
    Updates: relevance_grades, has_relevant_docs
    """
    query = state.get("rewritten_query") or state["query"]
    reranked_docs = state.get("reranked_docs", [])

    if not reranked_docs:
        logger.info("relevance_grader_no_docs")
        graph_path = state.get("graph_path", []) + ["relevance_grader"]
        processing_steps = state.get("processing_steps", []) + ["Checking relevance..."]
        return {
            "relevance_grades": [],
            "has_relevant_docs": False,
            "graph_path": graph_path,
            "processing_steps": processing_steps,
        }

    logger.info(
        "relevance_grader_start",
        num_docs=len(reranked_docs),
        query_preview=query[:80],
    )

    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.0,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        grades = []
        # Grade top 3 docs (to save API calls; reranker already ordered by relevance)
        docs_to_grade = reranked_docs[:3]

        for doc_data in docs_to_grade:
            try:
                content = doc_data.get("page_content", "")[:800]  # Limit for efficiency
                prompt = f"Question: {query}\n\nDocument chunk:\n{content}"

                messages = [
                    SystemMessage(content=RELEVANCE_GRADER_SYSTEM),
                    HumanMessage(content=prompt),
                ]
                response = await llm.ainvoke(messages)
                resp_content = response.content.strip()

                # Parse JSON
                if "```json" in resp_content:
                    resp_content = resp_content.split("```json")[1].split("```")[0].strip()
                elif "```" in resp_content:
                    resp_content = resp_content.split("```")[1].split("```")[0].strip()

                grade = json.loads(resp_content)
                grades.append({
                    "is_relevant": bool(grade.get("is_relevant", True)),
                    "relevance_score": float(grade.get("relevance_score", 0.5)),
                    "reason": str(grade.get("reason", "")),
                    "chunk_id": doc_data.get("metadata", {}).get("chunk_id", ""),
                })
            except Exception as e:
                logger.warning("grade_parse_failed", error=str(e))
                # Default to relevant if grading fails
                grades.append({
                    "is_relevant": True,
                    "relevance_score": doc_data.get("score", 0.5),
                    "reason": "grading_failed_assumed_relevant",
                    "chunk_id": doc_data.get("metadata", {}).get("chunk_id", ""),
                })

        # Determine if we have any relevant documents
        has_relevant = any(g["is_relevant"] for g in grades)
        # Also consider rerank scores — if any are above threshold, consider relevant
        if not has_relevant and reranked_docs:
            top_score = reranked_docs[0].get("score", 0.0)
            has_relevant = top_score > 0.4

        logger.info(
            "relevance_grader_complete",
            num_graded=len(grades),
            has_relevant=has_relevant,
            relevant_count=sum(1 for g in grades if g["is_relevant"]),
        )

    except Exception as e:
        logger.error("relevance_grader_failed", error=str(e))
        # Fail open — assume relevant
        grades = []
        has_relevant = bool(reranked_docs)

    graph_path = state.get("graph_path", []) + ["relevance_grader"]
    processing_steps = state.get("processing_steps", []) + ["Checking relevance..."]

    return {
        "relevance_grades": grades,
        "has_relevant_docs": has_relevant,
        "graph_path": graph_path,
        "processing_steps": processing_steps,
    }


def route_after_grading(state: GraphState) -> str:
    """
    Conditional edge: Route based on relevance grading.
    Returns node name to route to.
    """
    has_relevant = state.get("has_relevant_docs", False)
    retry_count = state.get("retry_count", 0)
    max_retries = settings.MAX_RETRIES

    # Check if query needs retrieval at all
    query_analysis = state.get("query_analysis", {})
    if not query_analysis.get("needs_retrieval", True):
        return "answer_generator"

    if has_relevant:
        return "answer_generator"
    elif retry_count < max_retries:
        return "query_rewriter"
    else:
        # Max retries reached — generate a "no answer" response
        return "answer_generator"
