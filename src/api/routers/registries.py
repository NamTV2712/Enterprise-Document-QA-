"""Thin API-006 transport for public registries and bounded local tests."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.access import (
    AccessGrant,
    require_execution_access,
    require_public_provider_free_access,
)
from src.api.registry import RegistryService
from src.api.registry_models import (
    DatasetDetail,
    DatasetKind,
    DatasetRegistryResponse,
    ModelRegistryResponse,
    ModelRole,
    ModelTestRequest,
    ModelTestResponse,
)


def create_registry_router(service: RegistryService) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/models",
        response_model=ModelRegistryResponse,
        dependencies=[Depends(require_public_provider_free_access)],
    )
    async def models(
        role: ModelRole | None = Query(default=None),
    ) -> ModelRegistryResponse:
        items = service.list_models(role=role)
        return ModelRegistryResponse(items=items, total=len(items))

    @router.post("/models/{model_id}/tests", response_model=ModelTestResponse)
    async def model_test(
        model_id: str,
        body: ModelTestRequest,
        _grant: AccessGrant = Depends(require_execution_access),
    ) -> ModelTestResponse:
        result = service.run_model_test(model_id, body.test_type)
        if result is None:
            raise HTTPException(status_code=404, detail="Model registry entry not found")
        return result

    @router.get(
        "/datasets",
        response_model=DatasetRegistryResponse,
        dependencies=[Depends(require_public_provider_free_access)],
    )
    async def datasets(
        kind: DatasetKind | None = Query(default=None),
    ) -> DatasetRegistryResponse:
        items = service.list_datasets(kind=kind)
        return DatasetRegistryResponse(items=items, total=len(items))

    @router.get(
        "/datasets/{dataset_id}",
        response_model=DatasetDetail,
        dependencies=[Depends(require_public_provider_free_access)],
    )
    async def dataset(dataset_id: str) -> DatasetDetail:
        result = service.get_dataset(dataset_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Dataset registry entry not found")
        return result

    return router
