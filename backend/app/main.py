"""
ResearchFlow AI — FastAPI Application Entry Point
Production-ready FastAPI setup with CORS, middleware, error handling, and OpenAPI docs.
"""
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import create_tables
from app.core.logging_config import configure_logging, get_logger, request_id_var
from app.core.redis_client import close_redis
from app.rag.vector_store import ensure_collection_exists
from app.api import documents, chat, health

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info(
        "application_starting",
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )

    # Initialize database tables
    try:
        await create_tables()
        logger.info("database_tables_created")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))

    # Initialize Qdrant collection
    try:
        await ensure_collection_exists()
        logger.info("vector_db_initialized")
    except Exception as e:
        logger.warning("vector_db_init_failed", error=str(e))

    logger.info("application_ready")
    yield

    # Shutdown
    logger.info("application_shutting_down")
    await close_redis()
    logger.info("application_stopped")


app = FastAPI(
    title="ResearchFlow AI API",
    description="""
## ResearchFlow AI — AI-Powered Document Research Assistant

Upload documents, ask questions, and get evidence-backed answers with citations.

### Features
- **Document Management**: Upload PDF, DOCX, TXT documents
- **LangGraph RAG Pipeline**: Intelligent query analysis, retrieval, and generation
- **Hybrid Retrieval**: Vector + BM25 + MMR for best results
- **Cross-Encoder Reranking**: Precision document ranking
- **Citation System**: Every answer backed by sources
- **Hallucination Protection**: Citation verification before response
""",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],  # In production, remove "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


# ── Request ID & Timing Middleware ─────────────────────────────
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Add request ID and timing to every request."""
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(
            "unhandled_exception",
            request_id=request_id,
            path=request.url.path,
            error=str(e),
        )
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )

    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

    logger.info(
        "request_complete",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=round(process_time, 2),
    )

    return response


# ── Exception Handlers ─────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "body": str(exc.body) if hasattr(exc, "body") else None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler — never expose internals."""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


# ── Routers ────────────────────────────────────────────────────
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(health.router)


# ── Root Endpoint ──────────────────────────────────────────────
@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
