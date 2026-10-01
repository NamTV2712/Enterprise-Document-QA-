"""Protected local-workspace routes for typed collections.

Every route here needs the API-001 local workspace grant, including reads: a
collection holds private research, so the access class is ``L``. The handlers
stay thin — validation, bounds and conflict semantics live in
``src.workspace.collections`` — and each error the domain raises maps to one
honest HTTP status: not found, tombstoned, conflict, or a bounded validation
problem.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.api.access import AccessGrant, require_local_workspace_access
from src.api.schemas import (
    CollectionCreateRequest,
    CollectionItemRequest,
    CollectionNoteRequest,
    CollectionNoteUpdateRequest,
    CollectionUpdateRequest,
)
from src.workspace.collections import (
    COLLECTION_ITEM_KINDS,
    COLLECTION_SORT_FIELDS,
    CollectionConflictError,
    CollectionDeletedError,
    CollectionError,
    CollectionLimitError,
    CollectionNotFoundError,
    SQLiteCollectionRepository,
)


def _status_for(error: CollectionError) -> int:
    if isinstance(error, CollectionNotFoundError):
        return 404
    if isinstance(error, CollectionDeletedError):
        return 410
    if isinstance(error, CollectionConflictError):
        return 409
    if isinstance(error, CollectionLimitError):
        return 422
    return 422


def _raise(error: CollectionError) -> None:
    raise HTTPException(status_code=_status_for(error), detail=str(error)) from error


def _collection_payload(collection: Any) -> dict[str, Any]:
    return {
        "collection_id": collection.collection_id,
        "name": collection.name,
        "description": collection.description,
        "tags": list(collection.tags),
        "favorite": collection.favorite,
        "private": collection.private,
        "revision": collection.revision,
        "created_at": collection.created_at,
        "updated_at": collection.updated_at,
        "item_count": collection.item_count,
    }


def _item_payload(item: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "item_id": item.item_id,
        "collection_id": item.collection_id,
        "item_kind": item.item_kind,
        "citation": item.citation,
        "excerpt": item.excerpt,
        "reference": dict(item.reference),
        "revision": item.revision,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }
    if item.snapshot is not None:
        payload["snapshot"] = dict(item.snapshot)
    return payload


def _note_payload(note: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "note_id": note.note_id,
        "collection_id": note.collection_id,
        "text": note.text,
        "revision": note.revision,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
    }
    if note.evidence_ref is not None:
        payload["evidence_ref"] = dict(note.evidence_ref)
    return payload


def _receipt_payload(receipt: Any) -> dict[str, Any]:
    return {
        "operation": receipt.operation,
        "entity_type": receipt.entity_type,
        "entity_id": receipt.entity_id,
        "revision": receipt.revision,
        "deleted_at": receipt.deleted_at,
    }


def create_collections_router(
    get_repository: Callable[[], SQLiteCollectionRepository],
) -> APIRouter:
    """Build the collections router over an application-owned repository."""
    router = APIRouter()

    @router.get("/collections")
    async def list_collections(
        _grant: AccessGrant = Depends(require_local_workspace_access),
        search: str | None = Query(default=None, max_length=200),
        tags: list[str] | None = Query(default=None),
        favorite: bool | None = Query(default=None),
        sort: str = Query(default="updated_at"),
        direction: str = Query(default="desc", pattern=r"^(asc|desc)$"),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
    ) -> dict[str, Any]:
        """List collections with the filters this workspace can actually apply."""
        if sort not in COLLECTION_SORT_FIELDS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported sort field. Supported fields: {', '.join(COLLECTION_SORT_FIELDS)}",
            )
        try:
            items, total = await run_in_threadpool(
                get_repository().list_collections,
                search=search,
                tags=tags,
                favorite=favorite,
                sort=sort,
                direction=direction,
                page=page,
                page_size=page_size,
            )
        except CollectionError as error:
            _raise(error)
        return {"items": [_collection_payload(item) for item in items], "total": total, "page": page, "page_size": page_size}

    @router.post("/collections")
    async def create_collection(
        body: CollectionCreateRequest,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Create one collection, returning its committed revision."""
        try:
            collection = await run_in_threadpool(
                get_repository().create_collection,
                name=body.name,
                description=body.description,
                tags=body.tags,
                favorite=body.favorite,
                private=body.private,
                collection_id=body.collection_id,
            )
        except CollectionError as error:
            _raise(error)
        return _collection_payload(collection)

    @router.get("/collections/{collection_id}")
    async def get_collection(
        collection_id: str,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        try:
            collection = await run_in_threadpool(get_repository().get_collection, collection_id)
        except CollectionError as error:
            _raise(error)
        return _collection_payload(collection)

    @router.patch("/collections/{collection_id}")
    async def update_collection(
        collection_id: str,
        body: CollectionUpdateRequest,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Update with a revision precondition: a stale view is a conflict."""
        try:
            collection = await run_in_threadpool(
                get_repository().update_collection,
                collection_id,
                expected_revision=body.revision,
                name=body.name,
                description=body.description,
                tags=body.tags,
                favorite=body.favorite,
                private=body.private,
            )
        except CollectionError as error:
            _raise(error)
        return _collection_payload(collection)

    @router.delete("/collections/{collection_id}")
    async def delete_collection(
        collection_id: str,
        revision: int = Query(ge=1),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Atomically tombstone a collection and every member it holds."""
        try:
            receipt = await run_in_threadpool(get_repository().delete_collection, collection_id, expected_revision=revision)
        except CollectionError as error:
            _raise(error)
        return _receipt_payload(receipt)

    @router.get("/collections/{collection_id}/items")
    async def list_items(
        collection_id: str,
        _grant: AccessGrant = Depends(require_local_workspace_access),
        kind: str | None = Query(default=None),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
    ) -> dict[str, Any]:
        if kind is not None and kind not in COLLECTION_ITEM_KINDS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported item kind. Supported kinds: {', '.join(COLLECTION_ITEM_KINDS)}",
            )
        try:
            items, total = await run_in_threadpool(
                get_repository().list_items,
                collection_id,
                kind=kind,
                page=page,
                page_size=page_size,
            )
        except CollectionError as error:
            _raise(error)
        return {"items": [_item_payload(item) for item in items], "total": total, "page": page, "page_size": page_size}

    @router.post("/collections/{collection_id}/items")
    async def add_item(
        collection_id: str,
        body: CollectionItemRequest,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Add one typed member; an incompatible reference is refused, not coerced."""
        try:
            item = await run_in_threadpool(
                get_repository().add_item,
                collection_id,
                item_kind=body.item_kind,
                citation=body.citation,
                excerpt=body.excerpt,
                reference=body.reference,
                snapshot=body.snapshot,
                item_id=body.item_id,
            )
        except CollectionError as error:
            _raise(error)
        return _item_payload(item)

    @router.delete("/collections/{collection_id}/items/{item_id}")
    async def delete_item(
        collection_id: str,
        item_id: str,
        revision: int = Query(ge=1),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Remove a member through the collection that owns it."""
        try:
            receipt = await run_in_threadpool(
                get_repository().delete_item,
                collection_id,
                item_id,
                expected_revision=revision,
            )
        except CollectionError as error:
            _raise(error)
        return _receipt_payload(receipt)

    @router.get("/collections/{collection_id}/notes")
    async def list_notes(
        collection_id: str,
        _grant: AccessGrant = Depends(require_local_workspace_access),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
    ) -> dict[str, Any]:
        try:
            notes, total = await run_in_threadpool(get_repository().list_notes, collection_id, page=page, page_size=page_size)
        except CollectionError as error:
            _raise(error)
        return {"items": [_note_payload(note) for note in notes], "total": total, "page": page, "page_size": page_size}

    @router.post("/collections/{collection_id}/notes")
    async def add_note(
        collection_id: str,
        body: CollectionNoteRequest,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        """Add a note, bound to an evidence reference when one is supplied."""
        try:
            note = await run_in_threadpool(
                get_repository().add_note,
                collection_id,
                text=body.text,
                evidence_ref=body.evidence_ref,
                note_id=body.note_id,
            )
        except CollectionError as error:
            _raise(error)
        return _note_payload(note)

    @router.patch("/collections/{collection_id}/notes/{note_id}")
    async def update_note(
        collection_id: str,
        note_id: str,
        body: CollectionNoteUpdateRequest,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        try:
            note = await run_in_threadpool(
                get_repository().update_note,
                collection_id,
                note_id,
                expected_revision=body.revision,
                text=body.text,
            )
        except CollectionError as error:
            _raise(error)
        return _note_payload(note)

    @router.delete("/collections/{collection_id}/notes/{note_id}")
    async def delete_note(
        collection_id: str,
        note_id: str,
        revision: int = Query(ge=1),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> dict[str, Any]:
        try:
            receipt = await run_in_threadpool(
                get_repository().delete_note,
                collection_id,
                note_id,
                expected_revision=revision,
            )
        except CollectionError as error:
            _raise(error)
        return _receipt_payload(receipt)

    @router.get("/collections/{collection_id}/activity")
    async def list_activity(
        collection_id: str,
        _grant: AccessGrant = Depends(require_local_workspace_access),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
    ) -> dict[str, Any]:
        """The operations this workspace actually recorded, newest first."""
        try:
            events, total = await run_in_threadpool(get_repository().list_activity, collection_id, page=page, page_size=page_size)
        except CollectionError as error:
            _raise(error)
        return {
            "items": [
                {
                    "activity_id": event.activity_id,
                    "collection_id": event.collection_id,
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at,
                }
                for event in events
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @router.get("/collections/{collection_id}/export")
    async def export_collection(
        collection_id: str,
        _grant: AccessGrant = Depends(require_local_workspace_access),
        format: str = Query(default="json", pattern=r"^(json|markdown)$"),
    ) -> Any:
        """Portable per-collection export; a read, so it mutates nothing."""
        try:
            payload = await run_in_threadpool(get_repository().export_collection, collection_id, format=format)
        except CollectionError as error:
            _raise(error)
        if isinstance(payload, str):
            return {"format": "markdown", "content": payload}
        return payload

    return router
