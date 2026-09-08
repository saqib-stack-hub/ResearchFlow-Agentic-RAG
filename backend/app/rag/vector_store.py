"""
ResearchFlow AI — Vector Store Interface
Handles Async Qdrant interaction.
"""
from typing import List, Optional, Tuple, Dict, Any
from langchain_core.documents import Document
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Singleton Qdrant Client Instance
_qdrant_client: Optional[AsyncQdrantClient] = None


def get_qdrant_client() -> AsyncQdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        # In-Memory Mode: Docker / External Qdrant Server ki zaroorat nahi hai
        _qdrant_client = AsyncQdrantClient(location=":memory:", check_compatibility=False)
    return _qdrant_client


async def check_vector_db_health() -> bool:
    """Check health status of Qdrant connection."""
    client = get_qdrant_client()
    try:
        await client.get_collections()
        return True
    except Exception as e:
        logger.error("qdrant_health_check_failed", error=str(e))
        return False


async def ensure_collection_exists(collection_name: str = "documents_384_v1", vector_size: int = 384):
    """Ensure that the Qdrant collection exists on server startup."""
    client = get_qdrant_client()
    try:
        collections = await client.get_collections()
        exists = any(c.name == collection_name for c in collections.collections)
        if not exists:
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            logger.info("collection_created", collection=collection_name)
        else:
            logger.info("collection_exists", collection=collection_name)
    except Exception as e:
        logger.error("qdrant_init_failed", error=str(e))


async def upsert_chunks(
    chunks: List[Document],
    vectors: List[List[float]],
    collection_name: str = "documents_384_v1",
) -> bool:
    """Upsert document chunks and vectors into Qdrant."""
    client = get_qdrant_client()
    try:
        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            payload = {
                "page_content": chunk.page_content,
                **chunk.metadata,
            }
            point_id = payload.get("chunk_id", f"{payload.get('document_id', 'doc')}_{idx}")
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        await client.upsert(
            collection_name=collection_name,
            points=points,
        )
        logger.info("chunks_upserted", count=len(points), collection=collection_name)
        return True
    except Exception as e:
        logger.error("qdrant_upsert_error", error=str(e))
        return False


async def delete_document_chunks(
    document_id: str,
    collection_name: str = "documents_384_v1",
) -> bool:
    """Delete all chunks related to a specific document ID."""
    client = get_qdrant_client()
    try:
        await client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
        logger.info("document_chunks_deleted", document_id=document_id)
        return True
    except Exception as e:
        logger.error("qdrant_delete_error", error=str(e))
        return False


async def similarity_search(
    query_vector: List[float],
    top_k: int = 4,
    score_threshold: float = 0.0,
    document_ids: Optional[List[str]] = None,
) -> List[Tuple[Document, float]]:
    """Search vector database using query vector with client compatibility."""
    client = get_qdrant_client()
    collection_name = getattr(settings, "QDRANT_COLLECTION", "documents_384_v1")

    query_filter = None
    if document_ids:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(any=document_ids),
                )
            ]
        )

    try:
        if hasattr(client, "query_points"):
            response = await client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                score_threshold=score_threshold if score_threshold > 0 else None,
                query_filter=query_filter,
                with_payload=True,
            )
            search_results = response.points
        else:
            search_results = await client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold if score_threshold > 0 else None,
                query_filter=query_filter,
                with_payload=True,
            )

        results = []
        for point in search_results:
            payload = point.payload or {}
            page_content = payload.get("page_content", "")
            
            doc = Document(
                page_content=page_content,
                metadata={
                    "document_id": payload.get("document_id"),
                    "chunk_id": payload.get("chunk_id"),
                    "filename": payload.get("filename"),
                    "page_number": payload.get("page_number"),
                }
            )
            results.append((doc, float(point.score)))

        return results

    except Exception as e:
        logger.error("qdrant_search_error", error=str(e))
        return []