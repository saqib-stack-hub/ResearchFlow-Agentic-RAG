"""
ResearchFlow AI — Qdrant Vector Store
Persistent vector database wrapper with collection management.
"""
from typing import Any, Dict, List, Optional, Tuple
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue, ScoredPoint
)
from langchain_core.documents import Document
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_async_client: Optional[AsyncQdrantClient] = None
_sync_client: Optional[QdrantClient] = None


def get_sync_client() -> QdrantClient:
    """Get synchronous Qdrant client (for setup/health checks)."""
    global _sync_client
    if _sync_client is None:
        kwargs = {"url": settings.VECTOR_DB_URL}
        if settings.VECTOR_DB_API_KEY:
            kwargs["api_key"] = settings.VECTOR_DB_API_KEY
        _sync_client = QdrantClient(**kwargs)
    return _sync_client


def get_async_client() -> AsyncQdrantClient:
    """Get asynchronous Qdrant client."""
    global _async_client
    if _async_client is None:
        kwargs = {"url": settings.VECTOR_DB_URL}
        if settings.VECTOR_DB_API_KEY:
            kwargs["api_key"] = settings.VECTOR_DB_API_KEY
        _async_client = AsyncQdrantClient(**kwargs)
    return _async_client


async def ensure_collection_exists() -> None:
    """Create the Qdrant collection if it doesn't exist."""
    client = get_async_client()
    collection_name = settings.VECTOR_DB_COLLECTION

    try:
        collections = await client.get_collections()
        existing = [c.name for c in collections.collections]

        if collection_name not in existing:
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("collection_created", collection=collection_name)
        else:
            logger.info("collection_exists", collection=collection_name)
    except Exception as e:
        logger.error("collection_setup_failed", error=str(e))
        raise


async def upsert_chunks(chunks: List[Document], vectors: List[List[float]]) -> int:
    """
    Upsert document chunks with their embeddings into Qdrant.
    Returns the number of points upserted.
    """
    client = get_async_client()
    collection_name = settings.VECTOR_DB_COLLECTION

    points = []
    for chunk, vector in zip(chunks, vectors):
        chunk_id = chunk.metadata.get("chunk_id")
        # Use deterministic ID from chunk_id (convert to int for Qdrant)
        point_id = _chunk_id_to_int(chunk_id)

        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "page_content": chunk.page_content,
                "document_id": chunk.metadata.get("document_id", ""),
                "filename": chunk.metadata.get("filename", ""),
                "file_type": chunk.metadata.get("file_type", ""),
                "page": chunk.metadata.get("page", 0),
                "chunk_id": chunk_id,
                "chunk_index": chunk.metadata.get("chunk_index", 0),
                "char_count": chunk.metadata.get("char_count", 0),
                "upload_timestamp": chunk.metadata.get("upload_timestamp", ""),
            }
        ))

    if not points:
        return 0

    # Batch upsert in groups of 100
    batch_size = 100
    total = 0
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        await client.upsert(collection_name=collection_name, points=batch)
        total += len(batch)

    logger.info("chunks_upserted", count=total, collection=collection_name)
    return total


async def similarity_search(
    query_vector: List[float],
    top_k: int = None,
    score_threshold: float = None,
    document_ids: Optional[List[str]] = None,
) -> List[Tuple[Document, float]]:
    """
    Semantic similarity search in Qdrant.
    Returns list of (Document, score) tuples.
    """
    client = get_async_client()
    top_k = top_k or settings.TOP_K
    score_threshold = score_threshold or settings.SIMILARITY_THRESHOLD

    # Build filter for specific documents if provided
    query_filter = None
    if document_ids:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=doc_id),
                )
                for doc_id in document_ids
            ]
        )

    results: List[ScoredPoint] = await client.search(
        collection_name=settings.VECTOR_DB_COLLECTION,
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
        query_filter=query_filter,
        with_payload=True,
    )

    docs_with_scores = []
    for hit in results:
        payload = hit.payload or {}
        doc = Document(
            page_content=payload.get("page_content", ""),
            metadata={k: v for k, v in payload.items() if k != "page_content"},
        )
        docs_with_scores.append((doc, hit.score))

    return docs_with_scores


async def delete_document_chunks(document_id: str) -> int:
    """Delete all chunks for a specific document from Qdrant."""
    client = get_async_client()
    collection_name = settings.VECTOR_DB_COLLECTION

    result = await client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        ),
    )
    logger.info("chunks_deleted", document_id=document_id)
    return getattr(result, "deleted_count", 0)


async def get_collection_info() -> Dict[str, Any]:
    """Get info about the Qdrant collection."""
    try:
        client = get_async_client()
        info = await client.get_collection(settings.VECTOR_DB_COLLECTION)
        return {
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": str(info.status),
        }
    except Exception as e:
        return {"error": str(e)}


async def check_vector_db_health() -> bool:
    """Check if Qdrant is healthy."""
    try:
        client = get_async_client()
        await client.get_collections()
        return True
    except Exception:
        return False


def _chunk_id_to_int(chunk_id: str) -> int:
    """Convert UUID string to an integer for Qdrant point ID."""
    import hashlib
    h = hashlib.md5(chunk_id.encode()).hexdigest()
    return int(h[:16], 16)  # Use first 16 hex chars as int (fits in uint64)
