"""
ResearchFlow AI — Answer Generator Agent
Generates evidence-backed answers with inline citations.
"""
import time
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.core.logging_config import get_logger, log_llm_metrics
from app.graph.state import GraphState

logger = get_logger(__name__)

ANSWER_GENERATOR_SYSTEM = """You are an AI Research Assistant that answers questions based on provided document context.

Instructions:
1. Answer ONLY based on the provided document context
2. If the context contains the answer, provide it clearly and accurately
3. Use inline citations like [1], [2] referring to the source numbers in the context
4. If the context does NOT contain enough information to answer, say so clearly
5. Do not make up or infer information not present in the context
6. Be concise but comprehensive
7. Format your response in clear, readable prose

IMPORTANT: If the documents don't contain the answer, respond with:
"I couldn't find enough evidence in your uploaded documents to answer this confidently."
Then optionally mention what you searched for."""

GENERAL_ANSWER_SYSTEM = """You are a helpful AI assistant. Answer the user's question clearly and accurately.
This question does not require document search — answer from your general knowledge.
Be concise, accurate, and helpful."""

NO_ANSWER_RESPONSE = """I couldn't find enough evidence in your uploaded documents to answer this confidently.

**What I searched for:** {query}

**What I found:** {found_summary}

**Suggestions:**
- Try rephrasing your question with different keywords
- Make sure the relevant document has been uploaded
- Ask a more specific question about a particular topic"""


async def answer_generator_node(state: GraphState) -> Dict[str, Any]:
    """
    LangGraph node: Generate the final answer.
    Handles both document-grounded and general knowledge answers.
    Updates: answer
    """
    query = state["query"]
    context_str = state.get("context_str", "")
    citations = state.get("citations", [])
    has_relevant = state.get("has_relevant_docs", False)
    query_analysis = state.get("query_analysis", {})
    needs_retrieval = query_analysis.get("needs_retrieval", True)

    logger.info(
        "answer_generator_start",
        has_context=bool(context_str),
        has_relevant_docs=has_relevant,
        needs_retrieval=needs_retrieval,
    )

    t0 = time.perf_counter()

    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        if not needs_retrieval:
            # General knowledge question — no document context needed
            messages = [
                SystemMessage(content=GENERAL_ANSWER_SYSTEM),
                HumanMessage(content=query),
            ]
            response = await llm.ainvoke(messages)
            answer = response.content.strip()
            is_document_grounded = False

        elif not context_str or not has_relevant:
            # No relevant documents found
            retry_count = state.get("retry_count", 0)
            found_summary = f"{len(state.get('retrieved_docs', []))} chunks retrieved but none were sufficiently relevant" if state.get('retrieved_docs') else "No documents found"
            answer = NO_ANSWER_RESPONSE.format(
                query=query,
                found_summary=found_summary,
            )
            is_document_grounded = False

        else:
            # Document-grounded answer
            prompt = f"""Based on the following document context, answer the question.

Question: {query}

Document Context:
{context_str}

Provide a comprehensive answer with inline citations [1], [2], etc. referring to the sources above."""

            messages = [
                SystemMessage(content=ANSWER_GENERATOR_SYSTEM),
                HumanMessage(content=prompt),
            ]
            response = await llm.ainvoke(messages)
            answer = response.content.strip()
            is_document_grounded = True

        latency_ms = (time.perf_counter() - t0) * 1000

        # Try to extract token usage
        usage = getattr(response, "usage_metadata", None) or {}
        prompt_tokens = usage.get("input_tokens", 0) if usage else 0
        completion_tokens = usage.get("output_tokens", 0) if usage else 0

        log_llm_metrics(
            logger,
            model=settings.LLM_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )

    except Exception as e:
        logger.error("answer_generator_failed", error=str(e))
        answer = "I encountered an error while generating your answer. Please try again."
        is_document_grounded = False

    logger.info(
        "answer_generator_complete",
        answer_length=len(answer),
        is_document_grounded=is_document_grounded,
    )

    graph_path = state.get("graph_path", []) + ["answer_generator"]
    processing_steps = state.get("processing_steps", []) + ["Generating answer..."]

    return {
        "answer": answer,
        "is_document_grounded": is_document_grounded if "is_document_grounded" not in state else state.get("is_document_grounded", is_document_grounded),
        "graph_path": graph_path,
        "processing_steps": processing_steps,
    }
