"""
ResearchFlow AI — Health Check API Router
Real health checks for all system components.
"""
import time
from datetime import datetime, timezone
from fastapi import APIRouter

from app.core.config import settings
from app.core.database import check_db_health
from app.core.redis_client import check_redis_health
from app.core.logging_config import get_logger
from app.models.schemas import HealthResponse, ServiceHealth
from app.rag.vector_store import check_vector_db_health

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger(__name__)


async def _check_llm_health() -> ServiceHealth:
    """Check LLM provider availability."""
    t0 = time.perf_counter()
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            max_tokens=5,
        )
        await llm.ainvoke([HumanMessage(content="ping")])
        latency = (time.perf_counter() - t0) * 1000
        return ServiceHealth(status="operational", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(status="down", detail=str(e)[:100])


@router.get("", response_model=HealthResponse)
async def health_check():
    """Overall system health check."""
    t0 = time.perf_counter()

    # Check all services concurrently
    import asyncio
    db_task = asyncio.create_task(_check_db())
    redis_task = asyncio.create_task(_check_redis())
    vector_task = asyncio.create_task(_check_vector_db())

    db_health, redis_health, vector_health = await asyncio.gather(
        db_task, redis_task, vector_task
    )

    services = {
        "database": db_health,
        "redis": redis_health,
        "vector_db": vector_health,
    }

    # Determine overall status
    statuses = [s.status for s in services.values()]
    if all(s == "operational" for s in statuses):
        overall = "healthy"
    elif any(s == "down" for s in statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        services=services,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/chat", response_model=HealthResponse)
async def chat_health():
    """Chat-specific health check including LLM."""
    import asyncio

    db_task = asyncio.create_task(_check_db())
    vector_task = asyncio.create_task(_check_vector_db())
    llm_task = asyncio.create_task(_check_llm_health())

    db_health, vector_health, llm_health = await asyncio.gather(
        db_task, vector_task, llm_task
    )

    services = {
        "database": db_health,
        "vector_db": vector_health,
        "llm": llm_health,
    }

    statuses = [s.status for s in services.values()]
    overall = "healthy" if all(s == "operational" for s in statuses) else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        services=services,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/ping")
async def ping():
    """Simple liveness probe."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Helpers ────────────────────────────────────────────────────

async def _check_db() -> ServiceHealth:
    t0 = time.perf_counter()
    healthy = await check_db_health()
    latency = (time.perf_counter() - t0) * 1000
    return ServiceHealth(
        status="operational" if healthy else "down",
        latency_ms=round(latency, 2),
    )


async def _check_redis() -> ServiceHealth:
    t0 = time.perf_counter()
    healthy = await check_redis_health()
    latency = (time.perf_counter() - t0) * 1000
    return ServiceHealth(
        status="operational" if healthy else "down",
        latency_ms=round(latency, 2),
    )


async def _check_vector_db() -> ServiceHealth:
    t0 = time.perf_counter()
    healthy = await check_vector_db_health()
    latency = (time.perf_counter() - t0) * 1000
    return ServiceHealth(
        status="operational" if healthy else "down",
        latency_ms=round(latency, 2),
    )
