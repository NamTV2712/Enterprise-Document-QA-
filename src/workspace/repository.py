"""Versioned repository primitives for later workspace domain repositories."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping, Protocol

from configs.settings import settings
from src.workspace.database import WorkspaceDatabase


class WorkspaceRecordError(RuntimeError):
    """Base error for deterministic workspace record operations."""


class RecordConflictError(WorkspaceRecordError):
    """Raised when an ID exists or an expected revision is stale."""


class RecordNotFoundError(WorkspaceRecordError):
    """Raised when the requested live record does not exist."""


class RecordDeletedError(WorkspaceRecordError):
    """Raised when a tombstone prevents silent record resurrection."""


@dataclass(frozen=True)
class VersionedRecord:
    entity_type: str
    entity_id: str
    revision: int
    payload: dict[str, object]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Tombstone:
    entity_type: str
    entity_id: str
    revision: int
    deleted_at: str


class VersionedRecordRepository(Protocol):
    def get(self, entity_type: str, entity_id: str) -> VersionedRecord | None: ...

    def create(
        self,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, object],
    ) -> VersionedRecord: ...

    def replace(
        self,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
    ) -> VersionedRecord: ...

    def delete(
        self,
        entity_type: str,
        entity_id: str,
        *,
        expected_revision: int,
    ) -> Tombstone: ...


_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_ENTITY_TYPES = frozenset(
    {
        "conversation",
        "collection",
        "collection_item",
        "note",
        "job",
        "job_step",
        # Recorded collection operations (DATA-003). Activity is append-only
        # history, never a mutation guard, and it stays outside the portable
        # transfer kinds on purpose.
        "collection_activity",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "bearer_token",
        "groq_api_key",
        "local_workspace_token",
        "password",
        "provider_credential",
        "provider_key",
        "secret",
    }
)
_FORBIDDEN_COMPACT_KEYS = frozenset(key.replace("_", "") for key in _FORBIDDEN_KEYS)


def utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _validate_entity(entity_type: str, entity_id: str) -> None:
    if entity_type not in _ENTITY_TYPES:
        raise ValueError("unsupported workspace entity type")
    if not _OPAQUE_ID.fullmatch(entity_id):
        raise ValueError("workspace entity IDs must be opaque identifiers")


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")


def _configured_secret_values() -> tuple[str, ...]:
    values = (
        settings.local_workspace_token.get_secret_value(),
        settings.groq_api_key,
        settings.groq_api_key2,
        settings.groq_api_key3,
        settings.groq_api_key4,
        settings.groq_api_key5,
        settings.groq_api_key_fall_back,
        settings.groq_api_key_fall_back2,
        settings.qdrant_cloud_api_key,
    )
    return tuple(value for value in values if value)


def _reject_secret_fields(value: object, forbidden_values: tuple[str, ...]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = _normalized_key(str(key))
            compact = normalized.replace("_", "")
            if (
                normalized in _FORBIDDEN_KEYS
                or compact in _FORBIDDEN_COMPACT_KEYS
                or normalized.endswith("_api_key")
                or normalized.endswith("_password")
                or normalized.endswith("_secret")
                or normalized.endswith("_token")
            ):
                raise ValueError("workspace records cannot persist credential fields")
            _reject_secret_fields(child, forbidden_values)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_secret_fields(child, forbidden_values)
    elif isinstance(value, str):
        if any(
            value == secret or (len(secret) >= 8 and secret in value)
            for secret in forbidden_values
        ):
            raise ValueError("workspace records cannot persist credential values")


def _canonical_payload(
    payload: Mapping[str, object],
    forbidden_values: tuple[str, ...],
) -> str:
    if not isinstance(payload, Mapping):
        raise TypeError("workspace record payload must be an object")
    _reject_secret_fields(payload, forbidden_values)
    try:
        return json.dumps(
            dict(payload),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise ValueError("workspace record payload must be finite JSON") from error


class SQLiteVersionedRecordRepository:
    """Atomic revision/conflict/tombstone primitives without product workflows.

    Every public method is one write transaction. The ``*_in`` variants apply the
    exact same rules on a caller-supplied connection and never commit, so a
    domain repository can compose several record operations into one logical
    mutation without inventing a second set of revision or tombstone semantics.
    """

    def __init__(
        self,
        database: WorkspaceDatabase,
        *,
        clock: Callable[[], str] = utc_timestamp,
        forbidden_secret_values: Iterable[str] | None = None,
    ) -> None:
        self.database = database
        self._clock = clock
        values = (
            _configured_secret_values()
            if forbidden_secret_values is None
            else tuple(forbidden_secret_values)
        )
        self._forbidden_secret_values = tuple(value for value in values if value)

    @staticmethod
    def _record(row: sqlite3.Row) -> VersionedRecord:
        payload = json.loads(str(row["payload_json"]))
        if not isinstance(payload, dict):
            raise ValueError("workspace record payload is malformed")
        return VersionedRecord(
            entity_type=str(row["entity_type"]),
            entity_id=str(row["entity_id"]),
            revision=int(row["revision"]),
            payload=payload,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _tombstone(row: sqlite3.Row) -> Tombstone:
        return Tombstone(
            entity_type=str(row["entity_type"]),
            entity_id=str(row["entity_id"]),
            revision=int(row["revision"]),
            deleted_at=str(row["deleted_at"]),
        )

    # -- connection-scoped operations (never commit on their own) ----------

    def get_in(
        self,
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
    ) -> VersionedRecord | None:
        _validate_entity(entity_type, entity_id)
        row = connection.execute(
            "SELECT entity_type, entity_id, revision, payload_json, created_at, updated_at "
            "FROM workspace_records WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        return self._record(row) if row else None

    def get_tombstone_in(
        self,
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
    ) -> Tombstone | None:
        _validate_entity(entity_type, entity_id)
        row = connection.execute(
            "SELECT entity_type, entity_id, revision, deleted_at "
            "FROM tombstones WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        return self._tombstone(row) if row else None

    def create_in(
        self,
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, object],
        *,
        timestamp: str,
    ) -> VersionedRecord:
        _validate_entity(entity_type, entity_id)
        payload_json = _canonical_payload(payload, self._forbidden_secret_values)
        try:
            deleted = connection.execute(
                "SELECT 1 FROM tombstones WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
            if deleted:
                raise RecordDeletedError("workspace record has been deleted")
            connection.execute(
                "INSERT INTO workspace_records("
                "entity_type, entity_id, revision, payload_json, created_at, updated_at"
                ") VALUES (?, ?, 1, ?, ?, ?)",
                (entity_type, entity_id, payload_json, timestamp, timestamp),
            )
        except sqlite3.IntegrityError as error:
            raise RecordConflictError("workspace record already exists") from error
        return VersionedRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            revision=1,
            payload=json.loads(payload_json),
            created_at=timestamp,
            updated_at=timestamp,
        )

    def replace_in(
        self,
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
        timestamp: str,
    ) -> VersionedRecord:
        _validate_entity(entity_type, entity_id)
        if expected_revision < 1:
            raise ValueError("expected revision must be positive")
        payload_json = _canonical_payload(payload, self._forbidden_secret_values)
        cursor = connection.execute(
            "UPDATE workspace_records SET payload_json = ?, revision = revision + 1, "
            "updated_at = ? WHERE entity_type = ? AND entity_id = ? AND revision = ?",
            (payload_json, timestamp, entity_type, entity_id, expected_revision),
        )
        if cursor.rowcount != 1:
            self._raise_missing_or_conflict(connection, entity_type, entity_id)
        row = connection.execute(
            "SELECT entity_type, entity_id, revision, payload_json, created_at, updated_at "
            "FROM workspace_records WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        if row is None:
            raise RecordNotFoundError("workspace record does not exist")
        return self._record(row)

    def delete_in(
        self,
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
        *,
        expected_revision: int,
        timestamp: str,
    ) -> Tombstone:
        _validate_entity(entity_type, entity_id)
        if expected_revision < 1:
            raise ValueError("expected revision must be positive")
        row = connection.execute(
            "SELECT revision FROM workspace_records "
            "WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        if row is None:
            self._raise_missing_or_conflict(connection, entity_type, entity_id)
        current_revision = int(row["revision"])
        if current_revision != expected_revision:
            raise RecordConflictError("workspace record revision conflict")
        tombstone_revision = current_revision + 1
        connection.execute(
            "DELETE FROM workspace_records WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        )
        connection.execute(
            "INSERT INTO tombstones(entity_type, entity_id, revision, deleted_at) "
            "VALUES (?, ?, ?, ?)",
            (entity_type, entity_id, tombstone_revision, timestamp),
        )
        return Tombstone(
            entity_type=entity_type,
            entity_id=entity_id,
            revision=tombstone_revision,
            deleted_at=timestamp,
        )

    # -- public operations: one call, one transaction ----------------------

    def get(self, entity_type: str, entity_id: str) -> VersionedRecord | None:
        with self.database.connection() as connection:
            return self.get_in(connection, entity_type, entity_id)

    def get_tombstone(self, entity_type: str, entity_id: str) -> Tombstone | None:
        with self.database.connection() as connection:
            return self.get_tombstone_in(connection, entity_type, entity_id)

    def create(
        self,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, object],
    ) -> VersionedRecord:
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            return self.create_in(connection, entity_type, entity_id, payload, timestamp=timestamp)

    def replace(
        self,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, object],
        *,
        expected_revision: int,
    ) -> VersionedRecord:
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            return self.replace_in(
                connection,
                entity_type,
                entity_id,
                payload,
                expected_revision=expected_revision,
                timestamp=timestamp,
            )

    def delete(
        self,
        entity_type: str,
        entity_id: str,
        *,
        expected_revision: int,
    ) -> Tombstone:
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            return self.delete_in(
                connection,
                entity_type,
                entity_id,
                expected_revision=expected_revision,
                timestamp=timestamp,
            )

    @staticmethod
    def _raise_missing_or_conflict(
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
    ) -> None:
        deleted = connection.execute(
            "SELECT 1 FROM tombstones WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        if deleted:
            raise RecordDeletedError("workspace record has been deleted")
        exists = connection.execute(
            "SELECT 1 FROM workspace_records WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchone()
        if exists:
            raise RecordConflictError("workspace record revision conflict")
        raise RecordNotFoundError("workspace record does not exist")
