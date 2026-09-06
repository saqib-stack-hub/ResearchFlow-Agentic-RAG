"""
ResearchFlow AI — Document Service
Orchestrates the full document ingestion pipeline:
Upload → Load → Clean → Chunk → Embed → Index (Qdrant) → Store (PostgreSQL)
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.core.config import settings
from app.core.logging_config import get_logger, LatencyTracker
from app.core.redis_client import set_document_status, get_document_status
from app.models.document import Document, DocumentStatus, DocumentType
from app.rag.loader import load_document, get_page_count
from app.rag.cleaner import clean_documents
from app.rag.chunker import chunk_documents
from app.rag.embedder import embed_texts
from app.rag.vector_store import upsert_chunks, delete_document_chunks, ensure_collection_exists
from app.rag.retriever import update_bm25_index

logger = get_logger(__name__)


async def save_upload(file_bytes: bytes, filename: str) -> str:
    """Save uploaded file to disk and return the file path."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)
    return file_path


async def process_document(
    document_id: str,
    file_path: str,
    filename: str,
    db: AsyncSession,
) -> None:
    """
    Full document processing pipeline (runs as background task).
    Updates document status in both Redis (real-time) and PostgreSQL (persistent).
    """
    async def update_status(status: DocumentStatus, step: str = "", error: str = ""):
        """Update status in both DB and Redis."""
        await _update_document_status_db(db, document_id, status, error)
        await set_document_status(document_id, {
            "status": status.value,
            "step": step,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("document_status_update", document_id=document_id, status=status.value, step=step)

    try:
        # Step 1: Ensure Qdrant collection exists
        await ensure_collection_exists()

        # ── CLEANING ─────────────────────────────────────────────
        await update_status(DocumentStatus.CLEANING, "Cleaning document...")
        raw_docs = load_document(file_path, document_id, filename)
        cleaned_docs = clean_documents(raw_docs)

        # ── CHUNKING ─────────────────────────────────────────────
        await update_status(DocumentStatus.CHUNKING, "Chunking text...")
        chunks = chunk_documents(cleaned_docs)

        if not chunks:
            raise ValueError("Document produced no content after cleaning/chunking")

        # ── EMBEDDING ─────────────────────────────────────────────
        await update_status(DocumentStatus.EMBEDDING, "Generating embeddings...")
        texts = [chunk.page_content for chunk in chunks]
        with LatencyTracker("embedding_batch", logger):
            vectors = await embed_texts(texts)

        # ── INDEXING ──────────────────────────────────────────────
        await update_status(DocumentStatus.INDEXING, "Indexing into vector database...")
        upserted = await upsert_chunks(chunks, vectors)

        # Update BM25 index (for hybrid search)
        update_bm25_index(chunks)

        # ── FINALIZE ──────────────────────────────────────────────
        page_count = get_page_count(file_path) or len(cleaned_docs)
        word_count = sum(len(chunk.page_content.split()) for chunk in chunks)

        # Mark as indexed in DB with final stats
        await _finalize_document(db, document_id, page_count, len(chunks), word_count)
        await update_status(DocumentStatus.INDEXED, "Complete")

        logger.info(
            "document_processing_complete",
            document_id=document_id,
            filename=filename,
            chunks=len(chunks),
            pages=page_count,
        )

    except Exception as e:
        error_msg = str(e)[:500]
        logger.error(
            "document_processing_failed",
            document_id=document_id,
            filename=filename,
            error=error_msg,
        )
        await update_status(DocumentStatus.FAILED, "Failed", error_msg)


async def _update_document_status_db(
    db: AsyncSession,
    document_id: str,
    status: DocumentStatus,
    error: str = "",
) -> None:
    """Update document status in PostgreSQL."""
    await db.execute(
        update(Document)
        .where(Document.id == uuid.UUID(document_id))
        .values(
            status=status,
            error_message=error if error else None,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


async def _finalize_document(
    db: AsyncSession,
    document_id: str,
    page_count: int,
    chunk_count: int,
    word_count: int,
) -> None:
    """Update document with final processing stats."""
    await db.execute(
        update(Document)
        .where(Document.id == uuid.UUID(document_id))
        .values(
            status=DocumentStatus.INDEXED,
            page_count=page_count,
            chunk_count=chunk_count,
            word_count=word_count,
            indexed_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


async def delete_document(document_id: str, db: AsyncSession) -> bool:
    """
    Delete document from:
    1. Qdrant (vector chunks)
    2. PostgreSQL (document record)
    3. Disk (uploaded file)
    Returns True if deleted, False if not found.
    """
    # Get document record
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return False

    # Delete from vector DB
    try:
        await delete_document_chunks(document_id)
    except Exception as e:
        logger.warning("vector_delete_failed", document_id=document_id, error=str(e))

    # Delete from disk
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception as e:
        logger.warning("file_delete_failed", file_path=doc.file_path, error=str(e))

    # Delete from database
    await db.delete(doc)
    await db.commit()

    logger.info("document_deleted", document_id=document_id, filename=doc.filename)
    return True


async def get_total_chunks(db: AsyncSession) -> int:
    """Get total indexed chunks across all documents."""
    result = await db.execute(
        select(func.sum(Document.chunk_count)).where(
            Document.status == DocumentStatus.INDEXED
        )
    )
    total = result.scalar()
    return int(total or 0)
