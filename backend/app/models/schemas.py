"""
ResearchFlow AI — Pydantic Schemas (Request / Response models)
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ══════════════════════════════════════════════════════════════
# Document Schemas
# ══════════════════════════════════════════════════════════════

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    word_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime] = None
    doc_metadata: Dict[str, Any] = {}


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: uuid.UUID


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    progress_step: Optional[str] = None
    error_message: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# Citation Schemas
# ══════════════════════════════════════════════════════════════

class Citation(BaseModel):
    document_id: Optional[str] = None
    document: str  # filename
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    excerpt: str
    score: float = 0.0


# ══════════════════════════════════════════════════════════════
# Chat Schemas
# ══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    session_id: Optional[uuid.UUID] = Field(None, description="Existing session ID (optional)")
    document_ids: Optional[List[uuid.UUID]] = Field(None, description="Limit search to specific documents")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What is the refund policy mentioned in the uploaded documents?",
                "session_id": None,
            }
        }
    )


class QueryAnalysis(BaseModel):
    is_document_related: bool
    intent: str
    needs_retrieval: bool
    retrieval_strategy: str = "hybrid"
    confidence: float = 1.0


class ChatResponse(BaseModel):
    answer: str
    session_id: uuid.UUID
    message_id: uuid.UUID
    is_document_grounded: bool
    citations: List[Citation] = []
    retrieval_score: Optional[float] = None
    num_sources: int = 0
    query_analysis: Optional[QueryAnalysis] = None
    graph_path: List[str] = []
    processing_steps: List[str] = []


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    retrieval_score: Optional[float] = None
    num_sources: Optional[int] = None
    is_document_grounded: bool = False
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: uuid.UUID
    title: Optional[str] = None
    messages: List[ChatMessageResponse]
    created_at: datetime
    updated_at: datetime


class ChatSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionSummary]
    total: int


# ══════════════════════════════════════════════════════════════
# Health Schemas
# ══════════════════════════════════════════════════════════════

class ServiceHealth(BaseModel):
    status: str  # "operational" | "degraded" | "down"
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: Dict[str, ServiceHealth]
    timestamp: datetime


# ══════════════════════════════════════════════════════════════
# Stats Schemas
# ══════════════════════════════════════════════════════════════

class DashboardStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_sessions: int
    indexed_documents: int
    processing_documents: int
    failed_documents: int
