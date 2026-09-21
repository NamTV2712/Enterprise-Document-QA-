"""Provider-free public discovery search routes.

``POST /search`` runs one keyword discovery pass over the already-loaded
serving corpus and stores a bounded snapshot; ``GET /search/{search_id}`` pages
that snapshot without re-running the search, so the result set cannot change
under a reader. Both routes are public (plan access class ``P``) and never
construct a model, provider, store, or reader.

Note: this module must not use postponed annotations. The route decorator is
applied under the slowapi limiter wrapper, whose module globals cannot resolve
a string annotation, so FastAPI would degrade the typed request body into a
required query parameter.
"""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from slowapi import Limiter

from src.api.discovery import (
    DEFAULT_PAGE_SIZE,
    DiscoveryError,
    DiscoveryService,
    MAX_PAGE_SIZE,
)
from src.api.schemas import DiscoverySnapshotResponse, SearchRequest


def create_search_router(
    get_service: Callable[[], DiscoveryService],
    *,
    limiter: Limiter,
    rate_limit: str,
) -> APIRouter:
    router = APIRouter()

    @router.post("/search", response_model=DiscoverySnapshotResponse)
    @limiter.limit(rate_limit)
    async def create_discovery_search(
        request: Request,
        body: SearchRequest,
    ) -> dict[str, Any]:
        """Run one provider-free keyword discovery pass and store its snapshot."""
        try:
            snapshot = get_service().search(
                query=body.query,
                mode=body.mode,
                group_by=body.group_by,
                ticker=body.ticker,
                section=body.section,
                year=body.year,
                filing_date=body.filing_date,
                page=body.page,
                page_size=body.page_size,
            )
        except DiscoveryError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return snapshot.as_payload(body.page, body.page_size)

    @router.get("/search/{search_id}", response_model=DiscoverySnapshotResponse)
    async def read_discovery_snapshot(
        search_id: str,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ) -> dict[str, Any]:
        """Return one page of a stored snapshot.

        An expired snapshot is reported as gone (410) and an unknown id as
        missing (404), so a reader can tell "search again" from "no such id".
        """
        status = get_service().snapshots.status(search_id)
        if status == "unknown":
            raise HTTPException(status_code=404, detail="Discovery snapshot not found")
        if status == "expired":
            raise HTTPException(
                status_code=410,
                detail="Discovery snapshot expired; run the search again",
            )
        snapshot = get_service().snapshots.get(search_id)
        if snapshot is None:  # pragma: no cover - defensive, status was live
            raise HTTPException(status_code=404, detail="Discovery snapshot not found")
        return snapshot.as_payload(page, page_size)

    return router
