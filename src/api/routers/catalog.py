"""Provider-free public catalog facets and statistics routes.

These routes read the startup catalog callback only: they never construct a
model, provider, store, or reader, and never mutate corpus, index, evaluation,
or workspace state. They are registered before the dynamic document routes so
``/documents/facets`` and ``/documents/stats`` cannot be matched as a
``document_id``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Query

from src.api.catalog import build_facets, build_stats
from src.api.schemas import DocumentFacetsResponse, DocumentStatsResponse


def create_catalog_router(get_rows: Callable[[], list[dict[str, Any]]]) -> APIRouter:
    """Build the catalog router over an application-owned metadata callback.

    ``get_rows`` raises the boundary's own not-ready error, so these routes
    never report an empty corpus for a server that simply has not loaded one.
    """
    router = APIRouter()

    @router.get("/documents/facets", response_model=DocumentFacetsResponse)
    async def document_facets(
        ticker: str | None = Query(default=None, pattern=r"^[A-Z]{1,5}(-[A-Z])?$"),
        section: str | None = Query(default=None, max_length=64),
        year: int | None = Query(default=None, ge=1900, le=2200),
        filing_date: str | None = Query(default=None, max_length=32),
        search: str | None = Query(default=None, max_length=100),
    ) -> dict[str, Any]:
        """Return recorded facet values and counts for the applied scope."""
        return build_facets(
            get_rows(),
            ticker=ticker,
            section=section,
            year=year,
            filing_date=filing_date,
            search=search,
        )

    @router.get("/documents/stats", response_model=DocumentStatsResponse)
    async def document_stats() -> dict[str, Any]:
        """Return truthful catalog totals and per-dimension availability."""
        return build_stats(get_rows())

    return router
