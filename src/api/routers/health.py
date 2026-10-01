"""Health and local-workspace configuration status routes."""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.access import (
    AccessGrant,
    configuration_status as workspace_configuration_status,
    require_local_workspace_access,
    require_public_provider_free_access,
)


def create_health_router(health_payload: Callable[[], dict[str, Any]], *,
                         agent_decision_capability: Callable[[], dict[str, object]] | None = None) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/health/live",
        dependencies=[Depends(require_public_provider_free_access)],
    )
    async def health_live() -> dict:
        """Report whether the API process can serve HTTP requests."""
        return {"status": "ok"}

    @router.get("/system/configuration-status")
    async def system_configuration_status(
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, object]:
        """Return only allowlisted local workspace capability flags."""
        payload = workspace_configuration_status()
        if agent_decision_capability is not None:
            payload["agent_decision_provider"] = agent_decision_capability()
        return payload

    @router.get("/health/ready")
    async def health_ready() -> dict:
        """Report whether the RAG pipeline is ready to accept query traffic."""
        payload = health_payload()
        if not payload["pipeline_ready"] or payload.get("worker_ready") is False:
            raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
        return payload

    @router.get("/health")
    async def health() -> dict:
        """Return the legacy health payload used by the current frontend."""
        return health_payload()

    return router
