"""
ResearchFlow AI — Query Rewriter Agent
Rewrites poor queries to improve retrieval on retry.
"""
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.core.logging_config import get_logger
from app.graph.state import GraphState

logger = get_logger(__name__)

QUERY_REWRITER_SYSTEM = """You are a query rewriting specialist for a document retrieval system.
When an initial query fails to retrieve relevant documents, rewrite it to be more effective.

Strategies:
1. Add specific keywords likely to appear in documents
2. Break complex questions into simpler retrieval-friendly forms
3. Use synonyms and alternative phrasings
4. Make implicit concepts explicit
5. Remove irrelevant words that could confuse retrieval

Return ONLY the rewritten query — no explanation, no quotes."""


async def query_rewriter_node(state: GraphState) -> Dict[str, Any]:
    """
    LangGraph node: Rewrite the query for better retrieval.
    Updates: rewritten_query, retry_count
    """
    original_query = state["query"]
    current_rewritten = state.get("rewritten_query") or original_query
    retry_count = state.get("retry_count", 0)

    logger.info(
        "query_rewriter_start",
        original_query=original_query[:80],
        retry_count=retry_count,
    )

    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # Include context about why retrieval failed
        relevance_grades = state.get("relevance_grades", [])
        grade_context = ""
        if relevance_grades:
            reasons = [g.get("reason", "") for g in relevance_grades if not g.get("is_relevant")]
            if reasons:
                grade_context = f"\n\nPrevious retrieval failed because: {'; '.join(reasons[:2])}"

        prompt = f"""Original query: "{current_rewritten}"{grade_context}

Rewrite this query to find better results in the document database.
Use different keywords and phrasing to maximize retrieval success."""

        messages = [
            SystemMessage(content=QUERY_REWRITER_SYSTEM),
            HumanMessage(content=prompt),
        ]
        response = await llm.ainvoke(messages)
        rewritten = response.content.strip().strip('"').strip("'")

        # Ensure rewritten query is different from original
        if rewritten.lower() == current_rewritten.lower():
            # Force a variation
            rewritten = f"{current_rewritten} key concepts main points"

    except Exception as e:
        logger.error("query_rewriter_failed", error=str(e))
        rewritten = f"{original_query} detailed information"

    new_retry_count = retry_count + 1

    logger.info(
        "query_rewriter_complete",
        original=original_query[:60],
        rewritten=rewritten[:60],
        new_retry_count=new_retry_count,
    )

    graph_path = state.get("graph_path", []) + ["query_rewriter"]
    processing_steps = state.get("processing_steps", []) + [f"Refining search (attempt {new_retry_count + 1})..."]

    return {
        "rewritten_query": rewritten,
        "retry_count": new_retry_count,
        "graph_path": graph_path,
        "processing_steps": processing_steps,
    }
