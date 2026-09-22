"""Allowlisted public system-information routes."""

import os
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import APIRouter

from src.api.original_normalizer import NORMALIZER_VERSION


def create_system_router(
    get_pipeline: Callable[[], Any],
    get_state: Callable[[], Mapping[str, Any]],
    get_api_version: Callable[[], str],
) -> APIRouter:
    router = APIRouter()

    @router.get("/system/info")
    async def system_info() -> dict:
        """Expose allowlisted build, model and corpus metadata for the workspace."""
        pipeline = get_pipeline()
        retriever = pipeline.retriever
        return {
            "api_version": get_api_version(),
            "corpus": dict(get_state().get("corpus") or {}),
            "retrieval": {
                "embedding_model": getattr(
                    getattr(retriever, "embedder", None), "model_name", None
                ),
                "reranker_model": getattr(retriever, "cross_encoder_model", None),
                "presets": ["bm25", "dense", "hybrid", "hybrid_rerank"],
                "default": "hybrid_rerank",
            },
            "capabilities": {
                "stage_events": True,
                "comparative_stream": True,
                "document_indexed_viewer": True,
                "original_document_viewer": {
                    "enabled": True,
                    "representation": "normalized_text",
                    "normalizer_version": NORMALIZER_VERSION,
                },
            },
            "build": {
                key: os.environ[key]
                for key in ("GIT_REVISION", "BUILD_VERSION")
                if os.environ.get(key)
            },
        }

    return router
