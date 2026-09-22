"""Existing semantic-cache controls and content-free metrics route."""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from slowapi import Limiter

from configs.settings import settings
from src.api.schemas import CacheTestRequest


def create_cache_router(
    limiter: Limiter,
    get_pipeline: Callable[[], Any],
    get_telemetry: Callable[[], Any],
    embed_query_pair: Callable[[Any, str, str], tuple[list[float], list[float]]],
) -> APIRouter:
    router = APIRouter()

    @router.get("/cache/stats")
    async def cache_stats() -> dict:
        """Return semantic cache metrics."""
        return get_pipeline().cache.get_stats()

    @router.get("/metrics")
    async def metrics() -> dict:
        """Expose aggregate request, error, and latency counters when enabled."""
        if not settings.enable_metrics_endpoint:
            raise HTTPException(status_code=403, detail="Metrics endpoint is disabled")
        return get_telemetry().snapshot()

    @router.post("/cache/clear")
    async def cache_clear() -> dict:
        """Clear semantic cache entries and reset cache metrics."""
        if not settings.enable_cache_clear:
            raise HTTPException(
                status_code=403,
                detail="Cache clearing is disabled on this deployment",
            )
        count = get_pipeline().cache.clear()
        return {"cleared_entries": count}

    @router.post("/cache/test")
    @limiter.limit(settings.cache_test_rate_limit)
    async def cache_test_similarity(
        request: Request, body: CacheTestRequest
    ) -> dict:
        """Compare two query embeddings to tune the semantic cache threshold."""
        pipeline = get_pipeline()
        emb_a, emb_b = await run_in_threadpool(
            embed_query_pair,
            pipeline,
            body.query_a,
            body.query_b,
        )
        similarity = pipeline.cache.test_similarity(emb_a, emb_b)
        return {
            "query_a": body.query_a,
            "query_b": body.query_b,
            "similarity": round(similarity, 6),
            "threshold": pipeline.cache.threshold,
            "would_cache_hit": similarity >= pipeline.cache.threshold,
        }

    return router
