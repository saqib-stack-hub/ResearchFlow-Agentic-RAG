"""
ResearchFlow AI — Document Chunker
Configurable text splitting with metadata preservation.

Default config (from environment):
  CHUNK_SIZE    = 1000 chars
  CHUNK_OVERLAP = 200  chars

Chunk size experiment:
  Small  (500/100):  Higher recall, more noise, more chunks
  Medium (1000/200): Good balance — DEFAULT
  Large  (2000/400): Better context, lower recall, fewer chunks
"""
import uuid
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.logging_config import get_logger
from app.rag.cleaner import deduplicate_chunks

logger = get_logger(__name__)


def chunk_documents(
    docs: List[Document],
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> List[Document]:
    """
    Split documents into overlapping chunks using RecursiveCharacterTextSplitter.

    Args:
        docs: List of cleaned LangChain Documents
        chunk_size: Override default CHUNK_SIZE from config
        chunk_overlap: Override default CHUNK_OVERLAP from config

    Returns:
        List of Document chunks with enriched metadata
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    logger.info(
        "chunking_start",
        num_docs=len(docs),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=False,
    )

    chunks = splitter.split_documents(docs)

    # Enrich metadata
    chunks = _enrich_chunk_metadata(chunks)

    # Remove duplicate chunks
    chunks = deduplicate_chunks(chunks)

    logger.info(
        "chunking_complete",
        num_chunks=len(chunks),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return chunks


def _enrich_chunk_metadata(chunks: List[Document]) -> List[Document]:
    """Add chunk_id, char_count, and upload_timestamp to each chunk."""
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).isoformat()

    for i, chunk in enumerate(chunks):
        # Generate a unique chunk ID
        chunk_id = str(uuid.uuid4())
        chunk.metadata["chunk_id"] = chunk_id
        chunk.metadata["chunk_index"] = i
        chunk.metadata["char_count"] = len(chunk.page_content)
        chunk.metadata["upload_timestamp"] = chunk.metadata.get("upload_timestamp", timestamp)

        # Ensure page is an integer
        page = chunk.metadata.get("page", 0)
        chunk.metadata["page"] = int(page) if page is not None else 0

    return chunks
