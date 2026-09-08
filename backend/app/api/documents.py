"""
ResearchFlow AI — Documents API Router
Endpoints: upload, list, delete
"""
import os
import uuid
from typing import List, Optional
from datetime import datetime, timezone
import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.config import settings
from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.schemas import (
    DocumentResponse, DocumentListResponse, DocumentDeleteResponse,
    DocumentStatusResponse, DashboardStats
)
from app.services.document_service import save_upload, process_document, delete_document, get_total_chunks

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)


def get_file_type(filename: str) -> DocumentType:
    """Determine document type from filename extension."""
    ext = os.path.splitext(filename.lower())[1].strip(".")
    mapping = {"pdf": DocumentType.PDF, "docx": DocumentType.DOCX, "txt": DocumentType.TXT}
    if ext not in mapping:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(mapping.keys())}",
        )
    return mapping[ext]


@router.post("/upload", response_model=DocumentResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF, DOCX, or TXT document.
    Processing runs in the background via FastAPI BackgroundTasks.
    """
    # Validate file type
    file_type = get_file_type(file.filename or "unknown.txt")

    # Read file bytes and validate size
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB",
        )
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    document_id = uuid.uuid4()

    # Save to disk
    try:
        file_path = await save_upload(file_bytes, file.filename)
    except Exception as e:
        logger.error("file_save_failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Create DB record
    doc = Document(
        id=document_id,
        filename=os.path.basename(file_path),
        original_filename=file.filename,
        file_type=file_type,
        file_size=len(file_bytes),
        file_path=file_path,
        status=DocumentStatus.PROCESSING,
        doc_metadata={
            "content_type": file.content_type,
            "original_name": file.filename,
        },
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Queue background processing (Redis-Bypassed Direct Task)
    background_tasks.add_task(
        process_document,
        str(document_id),
        file_path,
        file.filename,
        db,
    )

    logger.info(
        "document_upload_accepted",
        document_id=str(document_id),
        filename=file.filename,
        file_type=file_type.value,
        size_bytes=len(file_bytes),
    )

    return DocumentResponse.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded documents with optional status filter."""
    query = select(Document).order_by(desc(Document.created_at))

    if status:
        try:
            status_enum = DocumentStatus(status)
            query = query.where(Document.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Get total count
    count_query = select(func.count()).select_from(Document)
    if status:
        count_query = count_query.where(Document.status == DocumentStatus(status))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated documents
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
    )


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get real dashboard statistics from the database."""
    status_counts = {}
    for status in DocumentStatus:
        result = await db.execute(
            select(func.count()).select_from(Document).where(Document.status == status)
        )
        status_counts[status.value] = result.scalar() or 0

    total_docs = sum(status_counts.values())
    total_chunks = await get_total_chunks(db)

    from app.models.chat import ChatSession
    sessions_result = await db.execute(select(func.count()).select_from(ChatSession))
    total_sessions = sessions_result.scalar() or 0

    return DashboardStats(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_sessions=total_sessions,
        indexed_documents=status_counts.get("indexed", 0),
        processing_documents=status_counts.get("processing", 0) + status_counts.get("embedding", 0) + status_counts.get("chunking", 0) + status_counts.get("cleaning", 0) + status_counts.get("indexing", 0),
        failed_documents=status_counts.get("failed", 0),
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status_endpoint(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get document status directly from the Database (Redis-Safe fallback)."""
    # Safe Redis lookup with immediate Database fallback
    try:
        from app.core.redis_client import get_document_status
        redis_status = await get_document_status(str(document_id))
        if redis_status:
            return DocumentStatusResponse(
                document_id=document_id,
                status=redis_status.get("status", "unknown"),
                progress_step=redis_status.get("step"),
                error_message=redis_status.get("error") or None,
            )
    except Exception as e:
        logger.warning("redis_status_check_failed_fallback_to_db", error=str(e))

    # Always fallback to direct DB lookup
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentStatusResponse(
        document_id=document_id,
        status=doc.status.value,
        error_message=doc.error_message,
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document_endpoint(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a document from PostgreSQL, Qdrant, and local Disk.
    """
    deleted = await delete_document(str(document_id), db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDeleteResponse(
        message="Document deleted successfully",
        document_id=document_id,
    )