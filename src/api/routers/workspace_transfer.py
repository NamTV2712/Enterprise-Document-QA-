"""Protected local workspace import preview, commit, and export routes."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from src.api.access import AccessGrant, require_local_workspace_access
from src.workspace.transfer import (
    MAX_BACKUP_BYTES,
    WorkspaceTransferError,
    WorkspaceTransferService,
)


def _safe_json(raw: bytes) -> Any:
    if len(raw) > MAX_BACKUP_BYTES:
        raise HTTPException(status_code=413, detail="Workspace backup exceeds the 25 MiB limit")
    try:
        return json.loads(
            raw,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite number")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Workspace backup is not valid JSON") from error


async def _read_bounded_body(request: Request) -> bytes:
    """Read a request body incrementally and stop once it exceeds the import limit."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_BACKUP_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Workspace backup exceeds the 25 MiB limit",
                )
        except ValueError:
            # Content-Length is only an early-rejection hint. The streamed byte
            # count below remains authoritative for missing, malformed, or
            # under-reported lengths.
            pass

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BACKUP_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Workspace backup exceeds the 25 MiB limit",
            )
        body.extend(chunk)
    return bytes(body)


def _safe_transfer_error(error: WorkspaceTransferError) -> HTTPException:
    # Transfer errors are deliberately structural and never include source content.
    return HTTPException(status_code=400, detail=str(error))


def create_workspace_transfer_router(
    get_service: Callable[[], WorkspaceTransferService],
) -> APIRouter:
    router = APIRouter()

    @router.post("/workspace/imports/preview")
    async def preview_workspace_import(
        request: Request,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Validate and compare a portable backup without writing workspace state."""
        raw = _safe_json(await _read_bounded_body(request))
        try:
            return await run_in_threadpool(get_service().preview, raw)
        except WorkspaceTransferError as error:
            raise _safe_transfer_error(error) from error

    @router.post("/workspace/imports")
    async def import_workspace_backup(
        request: Request,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Commit a digest-bound portable backup as one idempotent transaction."""
        body = _safe_json(await _read_bounded_body(request))
        if not isinstance(body, dict) or set(body) != {"backup", "preview_digest"}:
            raise HTTPException(status_code=400, detail="Workspace import request is malformed")
        try:
            return await run_in_threadpool(
                get_service().import_backup,
                body["backup"],
                body["preview_digest"],
            )
        except WorkspaceTransferError as error:
            raise _safe_transfer_error(error) from error

    @router.get("/workspace/export")
    async def export_workspace_backup(
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Export portable research records from the private SQLite workspace."""
        try:
            return await run_in_threadpool(get_service().export_backup)
        except WorkspaceTransferError as error:
            raise _safe_transfer_error(error) from error

    return router
