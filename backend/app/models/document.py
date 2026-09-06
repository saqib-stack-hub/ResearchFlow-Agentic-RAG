"""
ResearchFlow AI — Document Database Model
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Enum,
    Text, BigInteger, JSON
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DocumentStatus(str, PyEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentType(str, PyEnum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_type = Column(Enum(DocumentType), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_path = Column(String(1000), nullable=False)

    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Processing metadata
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    indexed_at = Column(DateTime(timezone=True), nullable=True)

    # Extra metadata stored as JSON
    doc_metadata = Column(JSON, default=dict, nullable=False, server_default='{}')

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"
