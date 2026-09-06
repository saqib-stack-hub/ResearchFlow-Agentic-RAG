"""
ResearchFlow AI — Citation Checker Agent
Verifies that generated answers are supported by retrieved context.
Hallucination detection and citation validation.
"""
import json
import re
from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.core.logging_config import get_logger
from app.graph.state import GraphState

logger = get_logger(__name__)

CITATION_CHECKER_SYSTEM = """You are a hallucination detector and citation verifier for an AI Research Assistant.

Given:
1. A user question
2. The retrieved document context
3. The generated answer

Verify:
1. Is the answer supported by the provided context? (is_supported)
2. Does the answer contain any claims NOT found in the context? (has_hallucinations)
3. Are the citation references ([1], [2], etc.) present and used correctly?

Return ONLY JSON:
{
  "is_supported": true/false,
  "has_hallucinations": false/true,
  "unsupported_claims": ["claim 1", "claim 2"],
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}

Be strict: if the answer makes specific factual claims not present in the context, flag them."""


async def citation_checker_node(state: GraphState) -> Dict[str, Any]:
    """
    LangGraph node: Verify answer is grounded in retrieved context.
    Updates: citation_check, is_hallucination
    """
    query = state["query"]
    answer = state.get("answer", "")
    context_str = state.get("context_str", "")
    citations = state.get("citations", [])
    is_document_grounded = state.get("is_document_grounded", False)

    graph_path = state.get("graph_path", []) + ["citation_checker"]
    processing_steps = state.get("processing_steps", []) + ["Verifying sources..."]

    # Skip verification for non-document answers
    if not is_document_grounded or not context_str:
        return {
            "citation_check": {
                "is_supported": True,
                "has_hallucinations": False,
                "unsupported_claims": [],
                "confidence": 1.0,
                "reason": "general_knowledge_answer_no_verification_needed",
            },
            "is_hallucination": False,
            "graph_path": graph_path,
            "processing_steps": processing_steps,
        }

    logger.info(
        "citation_checker_start",
        answer_length=len(answer),
        context_length=len(context_str),
        num_citations=len(citations),
    )

    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.0,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # Limit context length for checker
        context_preview = context_str[:2000] if len(context_str) > 2000 else context_str

        prompt = f"""Question: {query}

Retrieved Context:
{context_preview}

Generated Answer:
{answer}

Verify that the answer is grounded in the context."""

        messages = [
            SystemMessage(content=CITATION_CHECKER_SYSTEM),
            HumanMessage(content=prompt),
        ]
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        check_result = json.loads(content)

        citation_check = {
            "is_supported": bool(check_result.get("is_supported", True)),
            "has_hallucinations": bool(check_result.get("has_hallucinations", False)),
            "unsupported_claims": list(check_result.get("unsupported_claims", [])),
            "confidence": float(check_result.get("confidence", 0.9)),
            "reason": str(check_result.get("reason", "")),
        }

        # Determine if this is a hallucination
        is_hallucination = (
            not citation_check["is_supported"]
            and citation_check["has_hallucinations"]
            and citation_check["confidence"] > 0.8
        )

        # If hallucination detected, modify answer to add disclaimer
        if is_hallucination and citation_check["unsupported_claims"]:
            logger.warning(
                "hallucination_detected",
                unsupported_claims=citation_check["unsupported_claims"][:3],
            )

    except (json.JSONDecodeError, Exception) as e:
        logger.warning("citation_checker_parse_failed", error=str(e))
        citation_check = {
            "is_supported": True,
            "has_hallucinations": False,
            "unsupported_claims": [],
            "confidence": 0.7,
            "reason": "verification_failed_assumed_valid",
        }
        is_hallucination = False

    logger.info(
        "citation_checker_complete",
        is_supported=citation_check["is_supported"],
        has_hallucinations=citation_check["has_hallucinations"],
        is_hallucination=is_hallucination,
    )

    return {
        "citation_check": citation_check,
        "is_hallucination": is_hallucination,
        "graph_path": graph_path,
        "processing_steps": processing_steps,
    }


async def final_response_node(state: GraphState) -> Dict[str, Any]:
    """
    LangGraph node: Final response assembly.
    If hallucination detected, modify answer with safety disclaimer.
    """
    answer = state.get("answer", "")
    is_hallucination = state.get("is_hallucination", False)
    citation_check = state.get("citation_check", {})

    if is_hallucination:
        # Add hallucination warning
        unsupported = citation_check.get("unsupported_claims", [])
        disclaimer = "\n\n> ⚠️ **Note:** Some parts of this answer may not be fully supported by the retrieved documents. Please verify the information against the source documents."
        answer = answer + disclaimer

    graph_path = state.get("graph_path", []) + ["final_response"]
    processing_steps = state.get("processing_steps", []) + ["Response ready ✓"]

    return {
        "answer": answer,
        "graph_path": graph_path,
        "processing_steps": processing_steps,
    }
