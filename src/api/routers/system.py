"""Allowlisted public system-information routes."""

import os
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import APIRouter

from src.api.original_normalizer import NORMALIZER_VERSION
from src.api.registry import _public_identifier


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
        # Runtime model names can be local directories. Apply the same public
        # identifier boundary as the registry rather than exposing raw values.
        build = {}
        for key in ("GIT_REVISION", "BUILD_VERSION"):
            value = _public_identifier(os.environ.get(key))
            if value is not None:
                build[key] = value
        return {
            "api_version": get_api_version(),
            "corpus": dict(get_state().get("corpus") or {}),
            "retrieval": {
                "embedding_model": _public_identifier(getattr(
                    getattr(retriever, "embedder", None), "model_name", None
                )),
                "reranker_model": _public_identifier(getattr(retriever, "cross_encoder_model", None)),
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
            "build": build,
        }

    return router
