"""
ResearchFlow AI — Structured Logging Configuration
JSON-formatted logs with request_id, latency, and component tracking.
"""
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional
import structlog
from app.core.config import settings

# Context variable for request-scoped request_id
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get() or str(uuid.uuid4())


def configure_logging() -> None:
    """Configure structlog for JSON output."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LatencyTracker:
    """Context manager for tracking operation latency."""

    def __init__(self, operation: str, logger: Optional[structlog.BoundLogger] = None):
        self.operation = operation
        self.logger = logger or get_logger()
        self.start_time: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000
        level = "error" if exc_type else "info"
        log_fn = getattr(self.logger, level)
        log_fn(
            f"{self.operation}_completed",
            operation=self.operation,
            latency_ms=round(self.elapsed_ms, 2),
            success=exc_type is None,
        )
        return False  # Don't suppress exceptions


def log_retrieval_metrics(
    logger: structlog.BoundLogger,
    query: str,
    num_retrieved: int,
    num_reranked: int,
    retrieval_latency_ms: float,
    reranking_latency_ms: float,
) -> None:
    """Log standardized retrieval metrics."""
    logger.info(
        "retrieval_metrics",
        query_preview=query[:100],
        num_retrieved=num_retrieved,
        num_reranked=num_reranked,
        retrieval_latency_ms=round(retrieval_latency_ms, 2),
        reranking_latency_ms=round(reranking_latency_ms, 2),
    )


def log_llm_metrics(
    logger: structlog.BoundLogger,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
) -> None:
    """Log standardized LLM usage metrics."""
    logger.info(
        "llm_metrics",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=round(latency_ms, 2),
    )
