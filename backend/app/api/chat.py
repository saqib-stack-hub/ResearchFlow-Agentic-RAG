"""
ResearchFlow AI — Chat API Router
Endpoints: POST /chat, GET /chat/history/{session_id}, GET /chat/sessions
"""
import uuid
import time
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.schemas import (
    ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessageResponse,
    ChatSessionListResponse, ChatSessionSummary, Citation, QueryAnalysis
)
from app.graph.workflow import run_workflow

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a chat query through the LangGraph RAG pipeline.
    Creates or continues a chat session.
    """
    t0 = time.perf_counter()
    logger.info(
        "chat_request",
        query_preview=request.query[:80],
        session_id=str(request.session_id) if request.session_id else "new",
    )

    # Get or create session
    session = await _get_or_create_session(db, request.session_id, request.query)

    # Save user message
    user_message = ChatMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content=request.query,
    )
    db.add(user_message)
    await db.commit()

    # Run LangGraph workflow
    try:
        document_ids = [str(d) for d in request.document_ids] if request.document_ids else None
        final_state = await run_workflow(
            query=request.query,
            session_id=str(session.id),
            document_ids=document_ids,
        )
    except Exception as e:
        logger.error("workflow_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")

    latency_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "chat_complete",
        session_id=str(session.id),
        latency_ms=round(latency_ms, 2),
        graph_path=final_state.get("graph_path", []),
    )

    # Parse citations
    raw_citations = final_state.get("citations", [])
    citations = [Citation(**c) for c in raw_citations if isinstance(c, dict)]

    # Parse query analysis
    raw_qa = final_state.get("query_analysis")
    query_analysis = QueryAnalysis(**raw_qa) if raw_qa else None

    is_doc_grounded = (
        final_state.get("is_document_grounded", False)
        or bool(citations)
    )

    # Save assistant message
    assistant_message = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=final_state.get("answer", ""),
        citations=[c.model_dump() for c in citations],
        retrieval_score=final_state.get("retrieval_score"),
        num_sources=len(citations),
        is_document_grounded=is_doc_grounded,
        query_analysis=final_state.get("query_analysis"),
        graph_path=final_state.get("graph_path", []),
    )
    db.add(assistant_message)

    # Update session title if first message
    if not session.title:
        session.title = _generate_session_title(request.query)
    session.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(assistant_message)

    return ChatResponse(
        answer=final_state.get("answer", ""),
        session_id=session.id,
        message_id=assistant_message.id,
        is_document_grounded=is_doc_grounded,
        citations=citations,
        retrieval_score=final_state.get("retrieval_score"),
        num_sources=len(citations),
        query_analysis=query_analysis,
        graph_path=final_state.get("graph_path", []),
        processing_steps=final_state.get("processing_steps", []),
    )


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions ordered by most recent."""
    # Count total
    total_result = await db.execute(select(func.count()).select_from(ChatSession))
    total = total_result.scalar() or 0

    # Get sessions with message counts
    result = await db.execute(
        select(ChatSession)
        .order_by(desc(ChatSession.updated_at))
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()

    session_summaries = []
    for session in sessions:
        count_result = await db.execute(
            select(func.count()).select_from(ChatMessage).where(
                ChatMessage.session_id == session.id
            )
        )
        msg_count = count_result.scalar() or 0
        session_summaries.append(
            ChatSessionSummary(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=msg_count,
            )
        )

    return ChatSessionListResponse(sessions=session_summaries, total=total)


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full chat history for a session."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = [
        ChatMessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role.value,
            content=msg.content,
            citations=[Citation(**c) for c in (msg.citations or [])] if msg.citations else None,
            retrieval_score=msg.retrieval_score,
            num_sources=msg.num_sources,
            is_document_grounded=msg.is_document_grounded,
            created_at=msg.created_at,
        )
        for msg in (session.messages or [])
    ]

    return ChatHistoryResponse(
        session_id=session.id,
        title=session.title,
        messages=messages,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()


# ── Helpers ────────────────────────────────────────────────────

async def _get_or_create_session(
    db: AsyncSession,
    session_id: Optional[uuid.UUID],
    query: str,
) -> ChatSession:
    """Get existing session or create new one."""
    if session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            return session

    # Create new session
    session = ChatSession(title=None)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


def _generate_session_title(query: str, max_length: int = 50) -> str:
    """Generate a title from the first query."""
    title = query.strip()
    if len(title) > max_length:
        title = title[:max_length - 3] + "..."
    return title
