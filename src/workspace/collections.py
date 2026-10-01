"""Typed collections over the local workspace record store.

A collection is a named, taggable, favoritable, private-by-default container of
typed items. Item kinds are exactly the ones the rebuild plan defines —
``document``, ``evidence``, ``answer`` and ``note`` — and each kind states which
identity its reference must carry, so a member is never silently coerced into
another kind. Notes are editable and may be bound to an evidence reference;
items are immutable references or snapshots, which is why the plan gives them
only create and delete.

Persistence deliberately reuses the DATA-001 versioned-record store
(``workspace_records`` and ``tombstones``) instead of the unused foundation
tables: revisions, revision preconditions, tombstones, no-resurrection,
canonical payloads and secret-field rejection all come from that layer, and the
records keep the DATA-002 transfer wrapper, so the existing workspace backup
already round-trips typed collections and their items with no format change.

Reads go straight to the store through the database transaction helper; writes
go through ``SQLiteVersionedRecordRepository`` so conflict and tombstone
semantics stay in one place. Every timestamp the payload exposes is the very
instant the record was written, and every identifier comes from the caller or is
generated once here — never from list position.
"""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.workspace.database import WorkspaceDatabase
from src.workspace.repository import (
    RecordConflictError,
    RecordDeletedError,
    RecordNotFoundError,
    SQLiteVersionedRecordRepository,
    utc_timestamp,
)
from src.workspace.transfer import stable_legacy_id

# Entity types in the shared record store.
COLLECTION_ENTITY_TYPE = "collection"
ITEM_ENTITY_TYPE = "collection_item"
# ``note`` is the entity type the workspace foundation already provisions for
# editable collection notes; it is not a transfer kind, so notes stay outside
# the portable backup format.
NOTE_ENTITY_TYPE = "note"
ACTIVITY_ENTITY_TYPE = "collection_activity"

# The transfer record kinds these entities ride in. Items keep the
# ``evidence_item`` kind because that is the envelope record that carries a
# collection member; the typed truth lives in the payload's ``item_kind``.
_COLLECTION_SOURCE_KIND = "collection"
_ITEM_SOURCE_KIND = "evidence_item"
_SCHEMA_VERSION = 2

COLLECTION_ITEM_KINDS: tuple[str, ...] = ("document", "evidence", "answer", "note")
REFERENCE_ITEM_KINDS: tuple[str, ...] = ("document", "evidence", "answer")

# Bounds. Every one is enforced here, not by a client convention.
MAX_COLLECTIONS = 50
MAX_ITEMS_PER_COLLECTION = 100
MAX_NOTES_PER_COLLECTION = 50
MAX_ACTIVITY_PER_COLLECTION = 500
MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2_000
MAX_TAGS = 20
MAX_TAG_LENGTH = 64
MAX_CITATION_LENGTH = 500
MAX_EXCERPT_LENGTH = 10_000
MAX_NOTE_LENGTH = 10_000
MAX_REFERENCE_DEPTH = 12
MAX_REFERENCE_NODES = 500
MAX_ACTIVITY_EVENT_LENGTH = 64

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_ACTIVITY_EVENT = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

ACTIVITY_EVENTS: tuple[str, ...] = (
    "collection_created",
    "collection_updated",
    "collection_deleted",
    "item_added",
    "item_removed",
    "note_added",
    "note_updated",
    "note_removed",
)

COLLECTION_SORT_FIELDS: tuple[str, ...] = ("name", "updated_at", "created_at", "item_count")
DEFAULT_SORT = "updated_at"


class CollectionError(ValueError):
    """A bounded, content-free domain error."""


class CollectionNotFoundError(CollectionError):
    """The collection, item or note does not exist in this workspace."""


class CollectionConflictError(CollectionError):
    """A revision precondition failed, so the caller's view is stale."""


class CollectionDeletedError(CollectionError):
    """The record is tombstoned and must not be recreated by this operation."""


class CollectionLimitError(CollectionError):
    """A bound was exceeded."""


@dataclass(frozen=True)
class Collection:
    collection_id: str
    name: str
    description: str
    tags: tuple[str, ...]
    favorite: bool
    private: bool
    revision: int
    created_at: str
    updated_at: str
    item_count: int


@dataclass(frozen=True)
class CollectionItem:
    item_id: str
    collection_id: str
    item_kind: str
    citation: str
    excerpt: str
    reference: Mapping[str, Any]
    snapshot: Mapping[str, Any] | None
    revision: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CollectionNote:
    note_id: str
    collection_id: str
    text: str
    evidence_ref: Mapping[str, Any] | None
    revision: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CollectionActivity:
    activity_id: str
    collection_id: str | None
    entity_type: str
    entity_id: str
    event_type: str
    occurred_at: str


@dataclass(frozen=True)
class Receipt:
    """A committed operation: what changed, at which revision, when."""

    operation: str
    entity_type: str
    entity_id: str
    revision: int
    deleted_at: str | None


def generate_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(16)}"


def collection_entity_id(collection_id: str) -> str:
    """The store key for a collection: the transfer's own deterministic mapping.

    Using the mapping the import/export path already applies means a typed
    collection keeps one storage key through create, restart, export, import and
    repeated import, so importing a backup into the workspace that produced it
    cannot duplicate the collection under a second identity.
    """
    return stable_legacy_id("collection", collection_id)


def item_entity_id(item_id: str) -> str:
    """The store key for an item, mapped exactly like an exported member."""
    return stable_legacy_id("evidence_item", item_id)


# --- validation ------------------------------------------------------------


def _require_text(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise CollectionError(f"{label} must be a string")
    if not allow_empty and not value.strip():
        raise CollectionError(f"{label} must not be empty")
    if len(value) > maximum:
        raise CollectionLimitError(f"{label} exceeds {maximum} characters")
    return value


def validate_identifier(value: Any, *, label: str) -> str:
    """Opaque identifiers only: never a filesystem path, never a URL."""
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise CollectionError(f"{label} is malformed")
    if ".." in value or "/" in value or "\\" in value or "\0" in value:
        raise CollectionError(f"{label} is malformed")
    return value


def _validate_tags(tags: Any) -> tuple[str, ...]:
    if tags is None:
        return ()
    if isinstance(tags, (str, bytes)) or not isinstance(tags, Iterable):
        raise CollectionError("tags must be a list of strings")
    values = list(tags)
    if len(values) > MAX_TAGS:
        raise CollectionLimitError(f"a collection may carry at most {MAX_TAGS} tags")
    normalized: list[str] = []
    for tag in values:
        text = _require_text(tag, label="tag", maximum=MAX_TAG_LENGTH)
        text = text.strip()
        if text not in normalized:
            normalized.append(text)
    return tuple(sorted(normalized))


def _validate_reference_tree(value: Any, *, label: str) -> Mapping[str, Any]:
    """Bound a reference/snapshot tree without accepting anything executable."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise CollectionError(f"{label} must be an object")
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_REFERENCE_DEPTH:
            raise CollectionLimitError(f"{label} is nested too deeply")
        if isinstance(current, Mapping):
            for key, entry in current.items():
                if not isinstance(key, str):
                    raise CollectionError(f"{label} contains a non-string key")
                nodes += 1
                stack.append((entry, depth + 1))
        elif isinstance(current, (list, tuple)):
            for entry in current:
                nodes += 1
                stack.append((entry, depth + 1))
        elif isinstance(current, (str, int, float, bool)) or current is None:
            nodes += 1
        else:
            raise CollectionError(f"{label} contains an unsupported value")
        if nodes > MAX_REFERENCE_NODES:
            raise CollectionLimitError(f"{label} exceeds {MAX_REFERENCE_NODES} values")
    try:
        json.dumps(dict(value), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise CollectionError(f"{label} is not JSON-serializable") from error
    return dict(value)


def validate_evidence_reference(value: Any, *, label: str = "evidence reference") -> Mapping[str, Any]:
    """An ``EvidenceRef``: at least one identity, plus optional provenance."""
    reference = _validate_reference_tree(value, label=label)
    identity_keys = (
        "document_id",
        "chunk_id",
        "source_document_id",
        "conversation_id",
        "message_id",
    )
    if not any(isinstance(reference.get(key), str) and reference[key] for key in identity_keys):
        raise CollectionError(
            f"{label} must carry at least one identity "
            f"({', '.join(identity_keys)})"
        )
    for key in (*identity_keys, "document_revision", "source_set_revision", "chunk_text_hash", "representation", "location_status", "coverage_status"):
        if key in reference and reference[key] is not None and not isinstance(reference[key], str):
            raise CollectionError(f"{label} field {key} must be a string")
    return reference


def validate_item_reference(item_kind: str, value: Any) -> Mapping[str, Any]:
    """Membership rule: what identity each item kind must carry."""
    if item_kind not in COLLECTION_ITEM_KINDS:
        raise CollectionError(
            f"unsupported collection item kind; expected one of {', '.join(COLLECTION_ITEM_KINDS)}"
        )
    if item_kind == "note":
        reference = _validate_reference_tree(value, label="note reference")
        if reference:
            validate_evidence_reference(reference, label="note reference")
        return reference
    if item_kind == "document":
        reference = _validate_reference_tree(value, label="document reference")
        document_id = reference.get("document_id")
        if not isinstance(document_id, str) or not document_id:
            raise CollectionError("a document item must reference a document_id")
        return reference
    if item_kind == "answer":
        reference = _validate_reference_tree(value, label="answer reference")
        if not any(
            isinstance(reference.get(key), str) and reference[key]
            for key in ("conversation_id", "message_id", "answer_id")
        ):
            raise CollectionError("an answer item must reference a conversation, message or answer identity")
        return reference
    # evidence
    return validate_evidence_reference(value)


def validate_collection_fields(
    *,
    name: Any,
    description: Any = "",
    tags: Any = None,
    favorite: Any = False,
    private: Any = True,
) -> dict[str, Any]:
    """Normalize the mutable fields of one collection and enforce their bounds."""
    if not isinstance(favorite, bool):
        raise CollectionError("favorite must be a boolean")
    if not isinstance(private, bool):
        raise CollectionError("private must be a boolean")
    return {
        "name": _require_text(name, label="name", maximum=MAX_NAME_LENGTH).strip(),
        "description": _require_text(
            description if description is not None else "",
            label="description",
            maximum=MAX_DESCRIPTION_LENGTH,
            allow_empty=True,
        ),
        "tags": list(_validate_tags(tags)),
        "favorite": favorite,
        "private": private,
    }


def validate_snapshot(value: Any) -> Mapping[str, Any] | None:
    if value is None:
        return None
    return _validate_reference_tree(value, label="item snapshot")


# --- record payloads -------------------------------------------------------


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _iso_from_ms(value: int) -> str:
    return (
        datetime.fromtimestamp(value / 1000, timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _ms_from_iso(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def _wrap(
    *,
    source_kind: str,
    legacy_id: str,
    data: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The store's transfer wrapper plus the typed payload in ``data``."""
    wrapper: dict[str, Any] = {
        "workspace_transfer_version": 1,
        "source_kind": source_kind,
        "legacy_id": legacy_id,
        "source_schema_version": _SCHEMA_VERSION,
        "data": dict(data),
    }
    if extra:
        wrapper.update(extra)
    return wrapper


def unwrap_payload(payload: Mapping[str, Any], *, label: str) -> Mapping[str, Any]:
    """Return the typed payload, or fail closed on a foreign record.

    A record this domain did not write is never guessed at: it is reported as
    unsupported so a caller cannot act on a shape it does not understand.
    Collections and items carry the transfer wrapper; notes carry their own
    workspace marker because the backup format has no note record type.
    """
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise CollectionError(f"{label} is not a typed record this workspace understands")
    if payload.get("workspace_transfer_version") == 1 or payload.get("workspace_collection_note") == 1:
        return data
    raise CollectionError(f"{label} is not a typed record this workspace understands")


def activity_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the data of one recorded activity row, or fail closed."""
    data = payload.get("data")
    if payload.get("workspace_collection_activity") != 1 or not isinstance(data, Mapping):
        raise CollectionError("activity record is not a typed record this workspace understands")
    return data


def collection_payload(
    *,
    collection_id: str,
    fields: Mapping[str, Any],
    created_at_ms: int,
    updated_at_ms: int,
) -> dict[str, Any]:
    data = {
        "id": collection_id,
        "schemaVersion": _SCHEMA_VERSION,
        "name": fields["name"],
        "description": fields["description"],
        "tags": list(fields["tags"]),
        "favorite": bool(fields["favorite"]),
        "private": bool(fields["private"]),
        "createdAt": created_at_ms,
        "updatedAt": updated_at_ms,
    }
    return _wrap(
        source_kind=_COLLECTION_SOURCE_KIND,
        legacy_id=collection_id,
        data=data,
        extra={"favorite": bool(fields["favorite"])},
    )


def item_payload(
    *,
    item_id: str,
    collection_id: str,
    item_kind: str,
    citation: str,
    excerpt: str,
    reference: Mapping[str, Any],
    snapshot: Mapping[str, Any] | None,
    saved_at_ms: int,
) -> dict[str, Any]:
    data = {
        "id": item_id,
        "schemaVersion": _SCHEMA_VERSION,
        "itemKind": item_kind,
        "citation": citation,
        "excerpt": excerpt,
        "savedAt": saved_at_ms,
        "collectionId": collection_id,
        "reference": dict(reference),
        "createdAt": saved_at_ms,
        "updatedAt": saved_at_ms,
    }
    if snapshot is not None:
        data["snapshot"] = dict(snapshot)
    return _wrap(
        source_kind=_ITEM_SOURCE_KIND,
        legacy_id=item_id,
        data=data,
        extra={"parent_legacy_id": collection_id},
    )


def note_payload(
    *,
    note_id: str,
    collection_id: str,
    text: str,
    evidence_ref: Mapping[str, Any] | None,
    created_at_ms: int,
    updated_at_ms: int,
) -> dict[str, Any]:
    data = {
        "id": note_id,
        "schemaVersion": _SCHEMA_VERSION,
        "collectionId": collection_id,
        "text": text,
        "createdAt": created_at_ms,
        "updatedAt": updated_at_ms,
    }
    if evidence_ref is not None:
        data["evidenceRef"] = dict(evidence_ref)
    # Notes live outside the portable transfer kinds on purpose: the envelope
    # has no note record type, and this task does not change the backup format.
    return {"workspace_collection_note": 1, "legacy_id": note_id, "data": data}


def activity_payload(*, activity_id: str, collection_id: str | None, entity_type: str, entity_id: str, event_type: str, occurred_at: str) -> dict[str, Any]:
    return {
        "workspace_collection_activity": 1,
        "legacy_id": activity_id,
        "data": {
            "id": activity_id,
            "collectionId": collection_id,
            "entityType": entity_type,
            "entityId": entity_id,
            "eventType": event_type,
            "occurredAt": occurred_at,
        },
    }


# --- repository ------------------------------------------------------------


class SQLiteCollectionRepository:
    """Typed collection repository over one workspace database."""

    def __init__(self, database: WorkspaceDatabase, *, clock: Callable[[], str] = utc_timestamp) -> None:
        self.database = database
        self._clock = clock
        self._store_instance = SQLiteVersionedRecordRepository(database, clock=clock)

    # -- helpers

    def _records(self, *, clock: Callable[[], str] | None = None) -> SQLiteVersionedRecordRepository:
        return SQLiteVersionedRecordRepository(self.database, clock=clock or self._clock)

    @property
    def _store(self) -> SQLiteVersionedRecordRepository:
        """One record repository per collection repository, for the write path."""
        return self._store_instance

    # Every write helper below operates on a caller-owned connection and never
    # commits: a logical collection mutation is exactly one transaction, so its
    # preconditions and its writes can never be separated by another writer.

    def _create_in(
        self,
        connection: Any,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, Any],
        *,
        timestamp_ms: int,
    ) -> Any:
        # The payload states the instant, and the record is written at exactly
        # that instant, so the exported spine and the stored timestamps agree.
        try:
            return self._store.create_in(
                connection,
                entity_type,
                entity_id,
                payload,
                timestamp=_iso_from_ms(timestamp_ms),
            )
        except RecordConflictError as error:
            raise CollectionConflictError(str(error)) from error
        except RecordDeletedError as error:
            raise CollectionDeletedError(str(error)) from error

    def _replace_in(
        self,
        connection: Any,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, Any],
        *,
        expected_revision: int,
        timestamp_ms: int,
    ) -> Any:
        try:
            return self._store.replace_in(
                connection,
                entity_type,
                entity_id,
                payload,
                expected_revision=expected_revision,
                timestamp=_iso_from_ms(timestamp_ms),
            )
        except RecordConflictError as error:
            raise CollectionConflictError(str(error)) from error
        except RecordDeletedError as error:
            raise CollectionDeletedError(str(error)) from error
        except RecordNotFoundError as error:
            raise CollectionNotFoundError(str(error)) from error

    def _delete_in(
        self,
        connection: Any,
        entity_type: str,
        entity_id: str,
        *,
        expected_revision: int,
        timestamp_ms: int,
    ) -> Any:
        try:
            return self._store.delete_in(
                connection,
                entity_type,
                entity_id,
                expected_revision=expected_revision,
                timestamp=_iso_from_ms(timestamp_ms),
            )
        except RecordConflictError as error:
            raise CollectionConflictError(str(error)) from error
        except RecordNotFoundError as error:
            raise CollectionNotFoundError(str(error)) from error
        except RecordDeletedError as error:
            # A second delete of the same record is not a conflict: the record
            # is already gone, and saying so is the honest answer.
            raise CollectionDeletedError(str(error)) from error

    @staticmethod
    def _scan_in(connection: Any, entity_type: str) -> list[tuple[str, int, Mapping[str, Any], str, str]]:
        rows = list(
            connection.execute(
                "SELECT entity_id, revision, payload_json, created_at, updated_at "
                "FROM workspace_records WHERE entity_type = ? ORDER BY entity_id",
                (entity_type,),
            )
        )
        scanned: list[tuple[str, int, Mapping[str, Any], str, str]] = []
        for row in rows:
            try:
                payload = json.loads(str(row["payload_json"]))
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, Mapping):
                continue
            scanned.append(
                (
                    str(row["entity_id"]),
                    int(row["revision"]),
                    payload,
                    str(row["created_at"]),
                    str(row["updated_at"]),
                )
            )
        return scanned

    def _scan(self, entity_type: str) -> list[tuple[str, int, Mapping[str, Any], str, str]]:
        with self.database.transaction() as connection:
            return self._scan_in(connection, entity_type)

    @staticmethod
    def _one_in(connection: Any, entity_type: str, entity_id: str, *, label: str) -> tuple[int, Mapping[str, Any], str, str]:
        row = connection.execute(
            "SELECT entity_id, revision, payload_json, created_at, updated_at "
            "FROM workspace_records WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        if row is not None:
            payload = json.loads(str(row["payload_json"]))
            if not isinstance(payload, Mapping):
                raise CollectionNotFoundError(f"{label} payload is malformed")
            return int(row["revision"]), payload, str(row["created_at"]), str(row["updated_at"])
        tombstone = connection.execute(
            "SELECT 1 FROM tombstones WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        if tombstone is not None:
            raise CollectionDeletedError(f"{label} has been deleted")
        raise CollectionNotFoundError(f"{label} does not exist")

    def _one(self, entity_type: str, entity_id: str, *, label: str) -> tuple[int, Mapping[str, Any], str, str]:
        with self.database.transaction() as connection:
            return self._one_in(connection, entity_type, entity_id, label=label)

    @classmethod
    def _children_in(cls, connection: Any, entity_type: str, collection_id: str) -> list[tuple[str, int, Mapping[str, Any]]]:
        children: list[tuple[str, int, Mapping[str, Any]]] = []
        for entity_id, revision, payload, _created, _updated in cls._scan_in(connection, entity_type):
            try:
                data = unwrap_payload(payload, label="child record")
            except CollectionError:
                continue
            if data.get("collectionId") == collection_id:
                children.append((entity_id, revision, payload))
        return children

    @classmethod
    def _member_count_in(cls, connection: Any, collection_id: str) -> int:
        """Live members of one collection, read inside the caller's transaction."""
        count = 0
        for entity_type in (ITEM_ENTITY_TYPE, NOTE_ENTITY_TYPE):
            for _entity_id, _revision, payload, _created, _updated in cls._scan_in(connection, entity_type):
                try:
                    data = unwrap_payload(payload, label="member record")
                except CollectionError:
                    continue
                if data.get("collectionId") == collection_id:
                    count += 1
        return count

    @staticmethod
    def _live_count_in(connection: Any, entity_type: str) -> int:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM workspace_records WHERE entity_type = ?",
            (entity_type,),
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    def _record_activity_in(
        self,
        connection: Any,
        *,
        collection_id: str | None,
        event_type: str,
        entity_type: str,
        entity_id: str,
        occurred_at: str,
    ) -> CollectionActivity:
        activity_id = generate_id("act")
        timestamp_ms = _ms_from_iso(occurred_at)
        self._prune_activity_in(connection, collection_id, timestamp_ms=timestamp_ms)
        self._create_in(
            connection,
            ACTIVITY_ENTITY_TYPE,
            activity_id,
            activity_payload(
                activity_id=activity_id,
                collection_id=collection_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                occurred_at=occurred_at,
            ),
            timestamp_ms=timestamp_ms,
        )
        return CollectionActivity(
            activity_id=activity_id,
            collection_id=collection_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            occurred_at=occurred_at,
        )

    def _prune_activity_in(self, connection: Any, collection_id: str | None, *, timestamp_ms: int) -> None:
        if collection_id is None:
            return
        rows = []
        for row in self._scan_in(connection, ACTIVITY_ENTITY_TYPE):
            try:
                data = activity_data(row[2])
            except CollectionError:
                continue
            if data.get("collectionId") == collection_id:
                rows.append(row)
        if len(rows) < MAX_ACTIVITY_PER_COLLECTION:
            return
        rows.sort(key=lambda row: (row[4], row[0]))
        for entity_id, revision, _payload, _created, _updated in rows[: len(rows) - MAX_ACTIVITY_PER_COLLECTION + 1]:
            try:
                self._delete_in(
                    connection,
                    ACTIVITY_ENTITY_TYPE,
                    entity_id,
                    expected_revision=revision,
                    timestamp_ms=timestamp_ms,
                )
            except CollectionError:
                continue

    # -- collection readers

    @staticmethod
    def _collection_of(collection_id: str, revision: int, payload: Mapping[str, Any], created_at: str, updated_at: str, item_count: int) -> Collection:
        data = unwrap_payload(payload, label="collection record")
        return Collection(
            collection_id=str(data.get("id") or collection_id),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            tags=tuple(str(tag) for tag in (data.get("tags") or [])),
            favorite=bool(data.get("favorite")),
            private=bool(data.get("private", True)),
            revision=revision,
            created_at=created_at,
            updated_at=updated_at,
            item_count=item_count,
        )

    def _item_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _item_id, _revision, payload, _created, _updated in self._scan(ITEM_ENTITY_TYPE):
            try:
                data = unwrap_payload(payload, label="item record")
            except CollectionError:
                continue
            collection_id = data.get("collectionId")
            if isinstance(collection_id, str):
                counts[collection_id] = counts.get(collection_id, 0) + 1
        return counts

    def list_collections(
        self,
        *,
        search: str | None = None,
        tags: Sequence[str] | None = None,
        favorite: bool | None = None,
        sort: str = DEFAULT_SORT,
        direction: str = "desc",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Collection], int]:
        if sort not in COLLECTION_SORT_FIELDS:
            raise CollectionError(f"unsupported sort field; expected one of {', '.join(COLLECTION_SORT_FIELDS)}")
        if direction not in ("asc", "desc"):
            raise CollectionError("direction must be asc or desc")
        page, page_size = _bounded_page(page, page_size)
        wanted_tags = {tag.strip().lower() for tag in (tags or []) if isinstance(tag, str) and tag.strip()}
        needle = (search or "").strip().lower()
        counts = self._item_counts()

        collections: list[Collection] = []
        for storage_id, revision, payload, created_at, updated_at in self._scan(COLLECTION_ENTITY_TYPE):
            try:
                data = unwrap_payload(payload, label="collection record")
            except CollectionError:
                continue
            logical_id = str(data.get("id") or storage_id)
            collection = self._collection_of(storage_id, revision, payload, created_at, updated_at, counts.get(logical_id, 0))
            # ``None`` means "either"; both True and False are real filters, so
            # a caller can ask for the unfavorited collections specifically.
            if favorite is not None and collection.favorite is not favorite:
                continue
            if wanted_tags and not wanted_tags.issubset({tag.lower() for tag in collection.tags}):
                continue
            if needle and needle not in collection.name.lower() and needle not in collection.description.lower():
                continue
            collections.append(collection)

        key = {
            "name": lambda item: item.name.lower(),
            "updated_at": lambda item: item.updated_at,
            "created_at": lambda item: item.created_at,
            "item_count": lambda item: item.item_count,
        }[sort]
        collections.sort(key=lambda item: (key(item), item.collection_id), reverse=(direction == "desc"))
        total = len(collections)
        start = (page - 1) * page_size
        return collections[start : start + page_size], total

    def get_collection(self, collection_id: str) -> Collection:
        validate_identifier(collection_id, label="collection_id")
        revision, payload, created_at, updated_at = self._one(COLLECTION_ENTITY_TYPE, collection_entity_id(collection_id), label="collection")
        counts = self._item_counts()
        return self._collection_of(collection_entity_id(collection_id), revision, payload, created_at, updated_at, counts.get(collection_id, 0))

    # -- collection writes

    def create_collection(
        self,
        *,
        name: Any,
        description: Any = "",
        tags: Any = None,
        favorite: Any = False,
        private: Any = True,
        collection_id: str | None = None,
    ) -> Collection:
        fields = validate_collection_fields(name=name, description=description, tags=tags, favorite=favorite, private=private)
        identifier = validate_identifier(collection_id, label="collection_id") if collection_id else generate_id("col")
        timestamp_ms = _now_ms()
        payload = collection_payload(
            collection_id=identifier,
            fields=fields,
            created_at_ms=timestamp_ms,
            updated_at_ms=timestamp_ms,
        )
        # The duplicate check, the capacity count, the insert and the recorded
        # activity are one transaction, so two concurrent creators cannot both
        # pass the count and exceed the workspace bound.
        with self.database.transaction(write=True) as connection:
            if self._has_record_in(connection, COLLECTION_ENTITY_TYPE, collection_entity_id(identifier)):
                raise CollectionConflictError("collection already exists")
            if self._live_count_in(connection, COLLECTION_ENTITY_TYPE) >= MAX_COLLECTIONS:
                raise CollectionLimitError(f"a workspace holds at most {MAX_COLLECTIONS} collections")
            record = self._create_in(connection, COLLECTION_ENTITY_TYPE, collection_entity_id(identifier), payload, timestamp_ms=timestamp_ms)
            self._record_activity_in(
                connection,
                collection_id=identifier,
                event_type="collection_created",
                entity_type=COLLECTION_ENTITY_TYPE,
                entity_id=identifier,
                occurred_at=self._clock(),
            )
        return self._collection_of(identifier, record.revision, record.payload, record.created_at, record.updated_at, 0)

    @staticmethod
    def _has_record_in(connection: Any, entity_type: str, entity_id: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM workspace_records WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        return row is not None

    def update_collection(
        self,
        collection_id: str,
        *,
        expected_revision: int,
        name: Any = None,
        description: Any = None,
        tags: Any = None,
        favorite: Any = None,
        private: Any = None,
    ) -> Collection:
        validate_identifier(collection_id, label="collection_id")
        _validate_revision(expected_revision)
        storage_id = collection_entity_id(collection_id)
        timestamp_ms = _now_ms()
        # One transaction: the read the fields are derived from, the revision
        # precondition, the write and the recorded activity.
        with self.database.transaction(write=True) as connection:
            revision, payload, created_at, record_updated_at = self._one_in(
                connection, COLLECTION_ENTITY_TYPE, storage_id, label="collection"
            )
            if revision != expected_revision:
                raise CollectionConflictError("workspace record revision conflict")
            current = self._collection_of(
                collection_id,
                revision,
                payload,
                created_at,
                record_updated_at,
                self._member_count_in(connection, collection_id),
            )
            fields = validate_collection_fields(
                name=current.name if name is None else name,
                description=current.description if description is None else description,
                tags=list(current.tags) if tags is None else tags,
                favorite=current.favorite if favorite is None else favorite,
                private=current.private if private is None else private,
            )
            updated_payload = collection_payload(
                collection_id=collection_id,
                fields=fields,
                created_at_ms=_ms_from_iso(current.created_at),
                updated_at_ms=timestamp_ms,
            )
            record = self._replace_in(
                connection,
                COLLECTION_ENTITY_TYPE,
                storage_id,
                updated_payload,
                expected_revision=expected_revision,
                timestamp_ms=timestamp_ms,
            )
            self._record_activity_in(
                connection,
                collection_id=collection_id,
                event_type="collection_updated",
                entity_type=COLLECTION_ENTITY_TYPE,
                entity_id=collection_id,
                occurred_at=self._clock(),
            )
        return self._collection_of(collection_id, record.revision, record.payload, record.created_at, record.updated_at, current.item_count)

    def delete_collection(self, collection_id: str, *, expected_revision: int) -> Receipt:
        validate_identifier(collection_id, label="collection_id")
        _validate_revision(expected_revision)
        storage_id = collection_entity_id(collection_id)
        timestamp_ms = _now_ms()
        # The parent is validated FIRST, inside the same transaction that then
        # tombstones it and every member it holds: a stale revision cannot
        # remove children, and a failure anywhere rolls the whole operation
        # back instead of leaving a half-deleted collection.
        with self.database.transaction(write=True) as connection:
            revision, _payload, _created, _updated = self._one_in(
                connection, COLLECTION_ENTITY_TYPE, storage_id, label="collection"
            )
            if revision != expected_revision:
                raise CollectionConflictError("workspace record revision conflict")
            # Deleting a collection tombstones its items and notes too, so an
            # item can never outlive the container it was listed in.
            for item_id, item_revision, _item_payload in self._children_in(connection, ITEM_ENTITY_TYPE, collection_id):
                self._delete_in(
                    connection,
                    ITEM_ENTITY_TYPE,
                    item_id,
                    expected_revision=item_revision,
                    timestamp_ms=timestamp_ms,
                )
            for note_id, note_revision, _note_payload in self._children_in(connection, NOTE_ENTITY_TYPE, collection_id):
                self._delete_in(
                    connection,
                    NOTE_ENTITY_TYPE,
                    note_id,
                    expected_revision=note_revision,
                    timestamp_ms=timestamp_ms,
                )
            tombstone = self._delete_in(
                connection,
                COLLECTION_ENTITY_TYPE,
                storage_id,
                expected_revision=expected_revision,
                timestamp_ms=timestamp_ms,
            )
            self._record_activity_in(
                connection,
                collection_id=collection_id,
                event_type="collection_deleted",
                entity_type=COLLECTION_ENTITY_TYPE,
                entity_id=collection_id,
                occurred_at=self._clock(),
            )
        return Receipt(
            operation="delete_collection",
            entity_type=COLLECTION_ENTITY_TYPE,
            entity_id=collection_id,
            revision=tombstone.revision,
            deleted_at=tombstone.deleted_at,
        )

    def _children(self, entity_type: str, collection_id: str) -> list[tuple[str, int, Mapping[str, Any]]]:
        with self.database.transaction() as connection:
            return self._children_in(connection, entity_type, collection_id)

    # -- items

    @staticmethod
    def _item_of(item_id: str, revision: int, payload: Mapping[str, Any], created_at: str, updated_at: str) -> CollectionItem:
        data = unwrap_payload(payload, label="item record")
        is_note = payload.get("workspace_collection_note") == 1
        return CollectionItem(
            item_id=str(data.get("id") or item_id),
            collection_id=str(data.get("collectionId") or ""),
            item_kind="note" if is_note else str(data.get("itemKind") or ""),
            citation=str(data.get("citation") or ""),
            excerpt=str(data.get("text") if is_note else data.get("excerpt") or ""),
            reference=dict(data.get("evidenceRef") or {}) if is_note else dict(data.get("reference") or {}),
            snapshot=dict(data["snapshot"]) if isinstance(data.get("snapshot"), Mapping) else None,
            revision=revision,
            created_at=created_at,
            updated_at=updated_at,
        )

    def list_items(
        self,
        collection_id: str,
        *,
        kind: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[CollectionItem], int]:
        self.get_collection(collection_id)
        if kind is not None and kind not in COLLECTION_ITEM_KINDS:
            raise CollectionError(f"unsupported item kind; expected one of {', '.join(COLLECTION_ITEM_KINDS)}")
        page, page_size = _bounded_page(page, page_size)
        items: list[CollectionItem] = []
        for entity_type in (ITEM_ENTITY_TYPE, NOTE_ENTITY_TYPE):
            for item_id, revision, payload, created_at, updated_at in self._scan(entity_type):
                try:
                    item = self._item_of(item_id, revision, payload, created_at, updated_at)
                except CollectionError:
                    continue
                if item.collection_id != collection_id:
                    continue
                if kind is not None and item.item_kind != kind:
                    continue
                items.append(item)
        items.sort(key=lambda item: (item.created_at, item.item_id))
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def get_item(self, item_id: str) -> CollectionItem:
        validate_identifier(item_id, label="item_id")
        candidates = (
            (ITEM_ENTITY_TYPE, item_entity_id(item_id)),
            (NOTE_ENTITY_TYPE, item_id),
        )
        for entity_type, storage_id in candidates:
            try:
                revision, payload, created_at, updated_at = self._one(entity_type, storage_id, label="item")
            except CollectionNotFoundError:
                continue
            return self._item_of(item_id, revision, payload, created_at, updated_at)
        raise CollectionNotFoundError("item does not exist")

    def add_item(
        self,
        collection_id: str,
        *,
        item_kind: Any,
        citation: Any,
        excerpt: Any,
        reference: Any = None,
        snapshot: Any = None,
        item_id: str | None = None,
    ) -> CollectionItem:
        validate_identifier(collection_id, label="collection_id")
        if item_kind not in COLLECTION_ITEM_KINDS:
            raise CollectionError(f"unsupported collection item kind; expected one of {', '.join(COLLECTION_ITEM_KINDS)}")
        if not isinstance(item_kind, str):
            raise CollectionError("item_kind must be a string")
        validated_reference = validate_item_reference(item_kind, reference)
        validated_snapshot = validate_snapshot(snapshot)
        # A document/evidence/answer item states its own citation and excerpt;
        # the server never invents one. A note carries its text instead.
        if item_kind in REFERENCE_ITEM_KINDS:
            citation_text = _require_text(citation, label="citation", maximum=MAX_CITATION_LENGTH)
            excerpt_text = _require_text(excerpt, label="excerpt", maximum=MAX_EXCERPT_LENGTH)
        else:
            citation_text = _require_text(citation, label="citation", maximum=MAX_CITATION_LENGTH, allow_empty=True)
            excerpt_text = _require_text(excerpt, label="excerpt", maximum=MAX_EXCERPT_LENGTH)
        identifier = validate_identifier(item_id, label="item_id") if item_id else generate_id("itm")
        if item_kind == "note":
            note = self.add_note(collection_id, text=excerpt_text, evidence_ref=validated_reference or None, note_id=identifier)
            revision, payload, created_at, updated_at = self._one(NOTE_ENTITY_TYPE, note.note_id, label="note")
            return self._item_of(note.note_id, revision, payload, created_at, updated_at)
        timestamp_ms = _now_ms()
        payload = item_payload(
            item_id=identifier,
            collection_id=collection_id,
            item_kind=item_kind,
            citation=citation_text,
            excerpt=excerpt_text,
            reference=validated_reference,
            snapshot=validated_snapshot,
            saved_at_ms=timestamp_ms,
        )
        # The parent's liveness and the capacity count are read inside the same
        # transaction as the insert, so a member can never become live under a
        # tombstoned parent and a capacity race cannot exceed the bound.
        with self.database.transaction(write=True) as connection:
            self._one_in(connection, COLLECTION_ENTITY_TYPE, collection_entity_id(collection_id), label="collection")
            if self._member_count_in(connection, collection_id) >= MAX_ITEMS_PER_COLLECTION:
                raise CollectionLimitError(f"a collection holds at most {MAX_ITEMS_PER_COLLECTION} items")
            record = self._create_in(connection, ITEM_ENTITY_TYPE, item_entity_id(identifier), payload, timestamp_ms=timestamp_ms)
            self._record_activity_in(
                connection,
                collection_id=collection_id,
                event_type="item_added",
                entity_type=ITEM_ENTITY_TYPE,
                entity_id=identifier,
                occurred_at=self._clock(),
            )
        return self._item_of(identifier, record.revision, record.payload, record.created_at, record.updated_at)

    def delete_item(self, collection_id: str, item_id: str, *, expected_revision: int) -> Receipt:
        validate_identifier(collection_id, label="collection_id")
        validate_identifier(item_id, label="item_id")
        _validate_revision(expected_revision)
        timestamp_ms = _now_ms()
        with self.database.transaction(write=True) as connection:
            item = self._item_in(connection, item_id)
            # Parent ownership: an item is only removable through the collection
            # that actually holds it.
            if item.collection_id != collection_id:
                raise CollectionNotFoundError("item does not belong to this collection")
            entity_type = NOTE_ENTITY_TYPE if item.item_kind == "note" else ITEM_ENTITY_TYPE
            storage_id = item_id if item.item_kind == "note" else item_entity_id(item_id)
            tombstone = self._delete_in(
                connection,
                entity_type,
                storage_id,
                expected_revision=expected_revision,
                timestamp_ms=timestamp_ms,
            )
            self._record_activity_in(
                connection,
                collection_id=collection_id,
                event_type="note_removed" if item.item_kind == "note" else "item_removed",
                entity_type=entity_type,
                entity_id=item_id,
                occurred_at=self._clock(),
            )
        return Receipt(
            operation="delete_item",
            entity_type=entity_type,
            entity_id=item_id,
            revision=tombstone.revision,
            deleted_at=tombstone.deleted_at,
        )

    def _item_in(self, connection: Any, item_id: str) -> CollectionItem:
        """One member read inside a caller-owned transaction."""
        for entity_type in (ITEM_ENTITY_TYPE, NOTE_ENTITY_TYPE):
            for entity_id, revision, payload, created_at, updated_at in self._scan_in(connection, entity_type):
                try:
                    item = self._item_of(entity_id, revision, payload, created_at, updated_at)
                except CollectionError:
                    continue
                if item.item_id == item_id:
                    return item
        tombstone = connection.execute(
            "SELECT 1 FROM tombstones WHERE entity_type = ? AND entity_id IN (?, ?)",
            (ITEM_ENTITY_TYPE, item_entity_id(item_id), item_id),
        ).fetchone()
        if tombstone is not None:
            raise CollectionDeletedError("item has been deleted")
        if connection.execute(
            "SELECT 1 FROM tombstones WHERE entity_type = ? AND entity_id = ?",
            (NOTE_ENTITY_TYPE, item_id),
        ).fetchone() is not None:
            raise CollectionDeletedError("item has been deleted")
        raise CollectionNotFoundError("item does not exist")

    # -- notes

    def list_notes(self, collection_id: str, *, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> tuple[list[CollectionNote], int]:
        self.get_collection(collection_id)
        page, page_size = _bounded_page(page, page_size)
        notes: list[CollectionNote] = []
        for note_id, revision, payload, created_at, updated_at in self._scan(NOTE_ENTITY_TYPE):
            try:
                data = unwrap_payload(payload, label="note record")
            except CollectionError:
                continue
            if data.get("collectionId") != collection_id:
                continue
            notes.append(
                CollectionNote(
                    note_id=note_id,
                    collection_id=collection_id,
                    text=str(data.get("text") or ""),
                    evidence_ref=dict(data["evidenceRef"]) if isinstance(data.get("evidenceRef"), Mapping) else None,
                    revision=revision,
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )
        notes.sort(key=lambda note: (note.created_at, note.note_id))
        total = len(notes)
        start = (page - 1) * page_size
        return notes[start : start + page_size], total

    def add_note(
        self,
        collection_id: str,
        *,
        text: Any,
        evidence_ref: Any = None,
        note_id: str | None = None,
    ) -> CollectionNote:
        validate_identifier(collection_id, label="collection_id")
        note_text = _require_text(text, label="note text", maximum=MAX_NOTE_LENGTH)
        validated_ref = None if evidence_ref is None else validate_evidence_reference(evidence_ref)
        identifier = validate_identifier(note_id, label="note_id") if note_id else generate_id("note")
        timestamp_ms = _now_ms()
        payload = note_payload(
            note_id=identifier,
            collection_id=collection_id,
            text=note_text,
            evidence_ref=validated_ref,
            created_at_ms=timestamp_ms,
            updated_at_ms=timestamp_ms,
        )
        # Parent liveness, the note bound, the duplicate check and the insert
        # share one transaction.
        with self.database.transaction(write=True) as connection:
            self._one_in(connection, COLLECTION_ENTITY_TYPE, collection_entity_id(collection_id), label="collection")
            if self._note_count_in(connection, collection_id) >= MAX_NOTES_PER_COLLECTION:
                raise CollectionLimitError(f"a collection holds at most {MAX_NOTES_PER_COLLECTION} notes")
            if self._member_count_in(connection, collection_id) >= MAX_ITEMS_PER_COLLECTION:
                raise CollectionLimitError(f"a collection holds at most {MAX_ITEMS_PER_COLLECTION} items")
            if self._has_record_in(connection, NOTE_ENTITY_TYPE, identifier):
                raise CollectionConflictError("note already exists")
            record = self._create_in(connection, NOTE_ENTITY_TYPE, identifier, payload, timestamp_ms=timestamp_ms)
            self._record_activity_in(
                connection,
                collection_id=collection_id,
                event_type="note_added",
                entity_type=NOTE_ENTITY_TYPE,
                entity_id=identifier,
                occurred_at=self._clock(),
            )
        return CollectionNote(
            note_id=identifier,
            collection_id=collection_id,
            text=note_text,
            evidence_ref=validated_ref,
            revision=record.revision,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @classmethod
    def _note_count_in(cls, connection: Any, collection_id: str) -> int:
        count = 0
        for _entity_id, _revision, payload, _created, _updated in cls._scan_in(connection, NOTE_ENTITY_TYPE):
            try:
                data = unwrap_payload(payload, label="note record")
            except CollectionError:
                continue
            if data.get("collectionId") == collection_id:
                count += 1
        return count

    def update_note(self, collection_id: str, note_id: str, *, expected_revision: int, text: Any) -> CollectionNote:
        validate_identifier(collection_id, label="collection_id")
        validate_identifier(note_id, label="note_id")
        _validate_revision(expected_revision)
        note_text = _require_text(text, label="note text", maximum=MAX_NOTE_LENGTH)
        timestamp_ms = _now_ms()
        with self.database.transaction(write=True) as connection:
            _revision, payload, created_at, _updated = self._one_in(
                connection, NOTE_ENTITY_TYPE, note_id, label="note"
            )
            data = unwrap_payload(payload, label="note record")
            if data.get("collectionId") != collection_id:
                raise CollectionNotFoundError("note does not belong to this collection")
            updated = note_payload(
                note_id=note_id,
                collection_id=collection_id,
                text=note_text,
                evidence_ref=dict(data["evidenceRef"]) if isinstance(data.get("evidenceRef"), Mapping) else None,
                created_at_ms=_ms_from_iso(created_at),
                updated_at_ms=timestamp_ms,
            )
            record = self._replace_in(
                connection,
                NOTE_ENTITY_TYPE,
                note_id,
                updated,
                expected_revision=expected_revision,
                timestamp_ms=timestamp_ms,
            )
            self._record_activity_in(
                connection,
                collection_id=collection_id,
                event_type="note_updated",
                entity_type=NOTE_ENTITY_TYPE,
                entity_id=note_id,
                occurred_at=self._clock(),
            )
        return CollectionNote(
            note_id=note_id,
            collection_id=collection_id,
            text=str(record.payload["data"].get("text") or ""),
            evidence_ref=dict(record.payload["data"]["evidenceRef"]) if isinstance(record.payload["data"].get("evidenceRef"), Mapping) else None,
            revision=record.revision,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def delete_note(self, collection_id: str, note_id: str, *, expected_revision: int) -> Receipt:
        return self.delete_item(collection_id, note_id, expected_revision=expected_revision)

    # -- activity

    def record_activity(self, *, collection_id: str | None, event_type: str, entity_type: str, entity_id: str) -> CollectionActivity:
        """Record one operation that actually happened.

        Activity is history, not a mutation guard: writing it must never fail a
        collection write that already committed, so the row is bounded and the
        oldest rows are pruned instead of the write being refused.
        """
        if not _ACTIVITY_EVENT.fullmatch(event_type) or event_type not in ACTIVITY_EVENTS:
            raise CollectionError("unsupported activity event")
        validate_identifier(entity_id, label="entity_id")
        occurred_at = self._clock()
        with self.database.transaction(write=True) as connection:
            return self._record_activity_in(
                connection,
                collection_id=collection_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                occurred_at=occurred_at,
            )

    def list_activity(self, collection_id: str, *, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> tuple[list[CollectionActivity], int]:
        page, page_size = _bounded_page(page, page_size)
        events: list[CollectionActivity] = []
        for activity_id, _revision, payload, created_at, _updated in self._scan(ACTIVITY_ENTITY_TYPE):
            try:
                data = activity_data(payload)
            except CollectionError:
                continue
            if data.get("collectionId") != collection_id:
                continue
            events.append(
                CollectionActivity(
                    activity_id=activity_id,
                    collection_id=collection_id,
                    entity_type=str(data.get("entityType") or ""),
                    entity_id=str(data.get("entityId") or ""),
                    event_type=str(data.get("eventType") or ""),
                    occurred_at=str(data.get("occurredAt") or created_at),
                )
            )
        events.sort(key=lambda event: (event.occurred_at, event.activity_id), reverse=True)
        total = len(events)
        start = (page - 1) * page_size
        return events[start : start + page_size], total

    # -- export

    def export_collection(self, collection_id: str, *, format: str = "json") -> dict[str, Any] | str:
        """Portable per-collection export: the truth, none of it reinterpreted."""
        if format not in ("json", "markdown"):
            raise CollectionError("export format must be json or markdown")
        collection = self.get_collection(collection_id)
        # Notes are exported in their own section rather than twice, so the item
        # list carries the immutable members only.
        listed, _total = self.list_items(collection_id, page=1, page_size=MAX_ITEMS_PER_COLLECTION)
        items = [item for item in listed if item.item_kind != "note"]
        notes, _note_total = self.list_notes(collection_id, page=1, page_size=MAX_NOTES_PER_COLLECTION)
        if format == "json":
            return {
                "id": collection.collection_id,
                "name": collection.name,
                "description": collection.description,
                "tags": list(collection.tags),
                "favorite": collection.favorite,
                "private": collection.private,
                "revision": collection.revision,
                "created_at": collection.created_at,
                "updated_at": collection.updated_at,
                "items": [
                    {
                        "id": item.item_id,
                        "kind": item.item_kind,
                        "citation": item.citation,
                        "excerpt": item.excerpt,
                        "reference": dict(item.reference),
                        **({"snapshot": dict(item.snapshot)} if item.snapshot is not None else {}),
                        "created_at": item.created_at,
                    }
                    for item in items
                ],
                "notes": [
                    {
                        "id": note.note_id,
                        "text": note.text,
                        **({"evidence_ref": dict(note.evidence_ref)} if note.evidence_ref is not None else {}),
                        "revision": note.revision,
                        "created_at": note.created_at,
                        "updated_at": note.updated_at,
                    }
                    for note in notes
                ],
            }
        lines = [f"# {collection.name}", ""]
        if collection.description:
            lines += [collection.description, ""]
        if collection.tags:
            lines += [f"Tags: {', '.join(collection.tags)}", ""]
        lines += [f"Revision {collection.revision} · updated {collection.updated_at}", ""]
        for item in items:
            lines += [f"## {item.citation or item.item_kind}", "", item.excerpt, "", f"_{item.item_kind} · {item.item_id}_", ""]
        for note in notes:
            lines += [f"### Note {note.note_id}", "", note.text, ""]
        return "\n".join(lines).rstrip() + "\n"


def _validate_revision(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CollectionError("expected_revision must be a positive integer")
    return value


def _bounded_page(page: Any, page_size: Any) -> tuple[int, int]:
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise CollectionError("page must be a positive integer")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
        raise CollectionError("page_size must be a positive integer")
    if page_size > MAX_PAGE_SIZE:
        raise CollectionLimitError(f"page_size must not exceed {MAX_PAGE_SIZE}")
    return page, page_size
