"""
ResearchFlow AI — Query Analyzer Agent
Analyzes user query to determine intent, retrieval strategy, and routing.
"""
import json
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.core.logging_config import get_logger
from app.graph.state import GraphState

logger = get_logger(__name__)

QUERY_ANALYZER_SYSTEM = """You are a query analyzer for an AI Research Assistant.
Analyze the user's question and return a structured JSON response.

Determine:
1. is_document_related: Is this question about uploaded research documents?
2. intent: Brief description of what the user wants (e.g., "policy_lookup", "definition", "comparison", "general_knowledge")
3. needs_retrieval: Should we search the document database?
4. retrieval_strategy: "hybrid" (default), "semantic", or "keyword"
5. confidence: Your confidence in this analysis (0.0 to 1.0)

Rules:
- Questions about specific facts, policies, data, or content → is_document_related: true
- General knowledge questions (math, history, definitions) → is_document_related: false
- Greetings, meta-questions → is_document_related: false, needs_retrieval: false
- When uncertain → default to is_document_related: true, needs_retrieval: true

Return ONLY valid JSON, no explanation:
{
  "is_document_related": true/false,
  "intent": "string",
  "needs_retrieval": true/false,
  "retrieval_strategy": "hybrid",
  "confidence": 0.95
}"""


def get_llm() -> ChatOpenAI:
    """Get LLM instance."""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.0,  # Deterministic for analysis
        openai_api_key=settings.OPENAI_API_KEY,
    )


async def query_analyzer_node(state: GraphState) -> Dict[str, Any]:
    """
    LangGraph node: Analyze the user query.
    Updates: query_analysis, graph_path, processing_steps
    """
    query = state["query"]
    logger.info("query_analyzer_start", query_preview=query[:80])

    try:
        llm = get_llm()
        messages = [
            SystemMessage(content=QUERY_ANALYZER_SYSTEM),
            HumanMessage(content=f"Analyze this query: {query}"),
        ]
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        analysis = json.loads(content)

        # Validate required fields with defaults
        query_analysis = {
            "is_document_related": bool(analysis.get("is_document_related", True)),
            "intent": str(analysis.get("intent", "information_lookup")),
            "needs_retrieval": bool(analysis.get("needs_retrieval", True)),
            "retrieval_strategy": str(analysis.get("retrieval_strategy", "hybrid")),
            "confidence": float(analysis.get("confidence", 0.9)),
        }

    except (json.JSONDecodeError, Exception) as e:
        logger.warning("query_analyzer_parse_failed", error=str(e), query=query[:80])
        # Fallback: assume document-related
        query_analysis = {
            "is_document_related": True,
            "intent": "information_lookup",
            "needs_retrieval": True,
            "retrieval_strategy": "hybrid",
            "confidence": 0.5,
        }

    logger.info(
        "query_analyzer_complete",
        is_document_related=query_analysis["is_document_related"],
        needs_retrieval=query_analysis["needs_retrieval"],
        intent=query_analysis["intent"],
    )

    graph_path = state.get("graph_path", []) + ["query_analyzer"]
    processing_steps = state.get("processing_steps", []) + ["Analyzing your question..."]

    return {
        "query_analysis": query_analysis,
        "graph_path": graph_path,
        "processing_steps": processing_steps,
        "retry_count": state.get("retry_count", 0),
        "is_hallucination": False,
    }
