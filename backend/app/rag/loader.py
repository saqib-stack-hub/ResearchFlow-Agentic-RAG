"""
ResearchFlow AI — Document Loader
Auto-detects file type and uses the appropriate LangChain loader.
"""
import os
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".text": "txt",
}


def detect_file_type(file_path: str) -> str:
    """Auto-detect file type from extension."""
    ext = Path(file_path).suffix.lower()
    file_type = SUPPORTED_EXTENSIONS.get(ext)
    if not file_type:
        raise ValueError(
            f"Unsupported file type: '{ext}'. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )
    return file_type


def load_document(file_path: str, document_id: str, filename: str) -> List[Document]:
    """
    Load a document using the appropriate LangChain loader.
    Returns a list of LangChain Document objects.
    """
    file_type = detect_file_type(file_path)
    logger.info("loading_document", file_type=file_type, filename=filename)

    try:
        if file_type == "pdf":
            docs = _load_pdf(file_path)
        elif file_type == "docx":
            docs = _load_docx(file_path)
        elif file_type == "txt":
            docs = _load_txt(file_path)
        else:
            raise ValueError(f"Unknown file type: {file_type}")
    except Exception as e:
        logger.error("document_load_failed", filename=filename, error=str(e))
        raise

    # Normalize metadata for all pages
    for i, doc in enumerate(docs):
        doc.metadata.update({
            "document_id": document_id,
            "filename": filename,
            "file_type": file_type,
            "source": filename,
        })
        # Ensure page number is set
        if "page" not in doc.metadata:
            doc.metadata["page"] = i

    logger.info("document_loaded", filename=filename, page_count=len(docs))
    return docs


def _load_pdf(file_path: str) -> List[Document]:
    """Load PDF using PyPDFLoader (per-page loading)."""
    loader = PyPDFLoader(file_path)
    return loader.load()


def _load_docx(file_path: str) -> List[Document]:
    """Load DOCX using Docx2txtLoader."""
    loader = Docx2txtLoader(file_path)
    docs = loader.load()
    # DOCX loads as single doc — add page metadata
    for doc in docs:
        if "page" not in doc.metadata:
            doc.metadata["page"] = 0
    return docs


def _load_txt(file_path: str) -> List[Document]:
    """Load TXT using TextLoader with encoding detection."""
    # Try UTF-8 first, then fall back to detected encoding
    try:
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
    except UnicodeDecodeError:
        try:
            import chardet
            with open(file_path, "rb") as f:
                raw = f.read()
            detected = chardet.detect(raw)
            encoding = detected.get("encoding", "latin-1") or "latin-1"
            loader = TextLoader(file_path, encoding=encoding)
            docs = loader.load()
        except Exception:
            loader = TextLoader(file_path, encoding="latin-1")
            docs = loader.load()

    for doc in docs:
        if "page" not in doc.metadata:
            doc.metadata["page"] = 0
    return docs


def get_page_count(file_path: str) -> Optional[int]:
    """Get page count for a document (best effort)."""
    try:
        file_type = detect_file_type(file_path)
        if file_type == "pdf":
            import pypdf
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                return len(reader.pages)
        return None
    except Exception:
        return None
