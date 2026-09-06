"""
ResearchFlow AI — Document Cleaner
Preprocessing pipeline: remove empty pages, normalize whitespace,
deduplicate content, repair broken text, strip headers/footers.
"""
import re
import unicodedata
from hashlib import md5
from typing import List, Set

from langchain_core.documents import Document

from app.core.logging_config import get_logger

logger = get_logger(__name__)


def clean_documents(docs: List[Document]) -> List[Document]:
    """
    Full cleaning pipeline applied to a list of raw LangChain Documents.
    Returns cleaned documents preserving original metadata for citations.
    """
    if not docs:
        return []

    original_count = len(docs)
    pipeline = [
        _normalize_unicode,
        _fix_broken_text,
        _normalize_whitespace,
        _remove_empty_pages,
        _remove_duplicate_pages,
    ]

    cleaned = docs
    for step in pipeline:
        cleaned = step(cleaned)

    logger.info(
        "cleaning_complete",
        original_pages=original_count,
        cleaned_pages=len(cleaned),
        removed=original_count - len(cleaned),
    )
    return cleaned


# ── Cleaning Steps ────────────────────────────────────────────

def _normalize_unicode(docs: List[Document]) -> List[Document]:
    """Normalize unicode characters to NFC form."""
    result = []
    for doc in docs:
        text = unicodedata.normalize("NFC", doc.page_content)
        # Replace common problematic unicode chars
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2013", "-").replace("\u2014", "--")
        text = text.replace("\u00a0", " ")  # non-breaking space
        result.append(Document(page_content=text, metadata=doc.metadata.copy()))
    return result


def _fix_broken_text(docs: List[Document]) -> List[Document]:
    """
    Repair common PDF text extraction artifacts:
    - Rejoin hyphenated line breaks
    - Fix word-boundary issues from PDF extraction
    """
    result = []
    for doc in docs:
        text = doc.page_content
        # Rejoin hyphenated words split across lines (e.g., "configu-\nration")
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        # Collapse single newlines that don't indicate paragraph breaks
        text = re.sub(r"(?<!\n)\n(?!\n)(?![A-Z•\-\d])", " ", text)
        result.append(Document(page_content=text, metadata=doc.metadata.copy()))
    return result


def _normalize_whitespace(docs: List[Document]) -> List[Document]:
    """
    Normalize excessive whitespace:
    - Collapse multiple spaces to one
    - Collapse 3+ newlines to 2
    - Strip leading/trailing whitespace
    """
    result = []
    for doc in docs:
        text = doc.page_content
        # Replace tabs with spaces
        text = text.replace("\t", " ")
        # Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text)
        # Collapse 3+ newlines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip
        text = text.strip()
        result.append(Document(page_content=text, metadata=doc.metadata.copy()))
    return result


def _remove_empty_pages(docs: List[Document]) -> List[Document]:
    """Remove pages with no meaningful content."""
    MIN_CONTENT_LENGTH = 20  # Minimum chars to consider a page non-empty

    result = []
    for doc in docs:
        # Strip whitespace and control characters
        stripped = re.sub(r"[\s\x00-\x1f\x7f-\x9f]+", "", doc.page_content)
        if len(stripped) >= MIN_CONTENT_LENGTH:
            result.append(doc)
    return result


def _remove_duplicate_pages(docs: List[Document]) -> List[Document]:
    """Remove pages with identical or near-identical content (exact hash dedup)."""
    seen_hashes: Set[str] = set()
    result = []

    for doc in docs:
        # Normalize for comparison (lowercase, strip whitespace)
        normalized = re.sub(r"\s+", " ", doc.page_content.lower().strip())
        content_hash = md5(normalized.encode()).hexdigest()

        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            result.append(doc)

    return result


def deduplicate_chunks(chunks: List[Document]) -> List[Document]:
    """Remove duplicate chunks after splitting (used in chunker pipeline)."""
    seen: Set[str] = set()
    result = []
    for chunk in chunks:
        normalized = re.sub(r"\s+", " ", chunk.page_content.lower().strip())
        h = md5(normalized.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            result.append(chunk)
    return result
