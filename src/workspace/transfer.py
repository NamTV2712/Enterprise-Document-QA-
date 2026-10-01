"""Portable browser/workspace backup validation and transactional transfer.

The transfer layer deliberately sits above the DATA-001 generic record tables.
It never reads browser storage and never changes the browser's authority.  A
portable envelope is explicit user data; preview is read-only and import is one
SQLite transaction with a digest-bound, idempotent receipt.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from configs.settings import settings
from src.workspace.database import WorkspaceDatabase


WORKSPACE_BACKUP_FORMAT = "enterprise-document-qa.workspace"
WORKSPACE_BACKUP_VERSION = 1
MAX_BACKUP_BYTES = 25 * 1024 * 1024
MAX_CONVERSATIONS = 100
MAX_COLLECTIONS = 50
MAX_EVIDENCE_ITEMS = 5_000
MAX_FAVORITES = 50
MAX_TOMBSTONES = 1_000
MAX_UNSUPPORTED_DESCRIPTORS = 100
MAX_TEXT_LENGTH = 1_000_000
MAX_JSON_DEPTH = 40
MAX_JSON_NODES = 250_000

_LEGACY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ENTITY_TYPE_BY_KIND = {
    "conversation": "conversation",
    "collection": "collection",
    "evidence_item": "collection_item",
}
_ID_PREFIX_BY_KIND = {
    "conversation": "legacy-conv-",
    "collection": "legacy-col-",
    "evidence_item": "legacy-item-",
}
_SECRET_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "local_workspace_token",
    "groq_api_key",
    "qdrant_api_key",
}


class WorkspaceTransferError(ValueError):
    """A bounded, content-free validation or compatibility error."""


@dataclass(frozen=True)
class ValidatedBackup:
    envelope: dict[str, Any]
    digest: str
    conversations: tuple[dict[str, Any], ...]
    collections: tuple[dict[str, Any], ...]
    evidence_items: tuple[dict[str, Any], ...]
    favorites: tuple[str, ...]
    tombstones: tuple[dict[str, Any], ...]
    unsupported: tuple[dict[str, Any], ...]

    @property
    def records(self) -> tuple[tuple[str, dict[str, Any]], ...]:
        return tuple(
            [("conversation", record) for record in self.conversations]
            + [("collection", record) for record in self.collections]
            + [("evidence_item", record) for record in self.evidence_items]
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _timestamp_ms(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise WorkspaceTransferError("workspace timestamp is invalid") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def _js_number_text(value: float) -> str:
    """Serialize a finite float exactly like ECMAScript ``Number::toString``.

    The portable digest must be byte-identical across the TypeScript and
    Python runtimes, so numbers use the ECMAScript notation (integral values
    without a fractional tail, shortest round-trip digits, and exponents
    without zero padding) instead of Python ``repr`` formatting.
    """
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("backup JSON must contain finite numbers")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    text = repr(abs(value))
    if "e" in text:
        mantissa, _, exponent = text.partition("e")
        n = int(exponent)
    else:
        mantissa, n = text, 0
    whole, _, fraction = mantissa.partition(".")
    if not whole.lstrip("0"):
        # Pure fraction such as 0.001: drop the leading zeros and shift the point.
        stripped = fraction.lstrip("0")
        n = -(len(fraction) - len(stripped))
        digits = stripped
    else:
        digits = whole + fraction
        n = len(whole) + n
    digits = digits.rstrip("0")
    k = len(digits)
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + digits
    exponent = n - 1
    mantissa_text = digits[0] + ("." + digits[1:] if k > 1 else "")
    return f"{sign}{mantissa_text}e{'+' if exponent >= 0 else '-'}{abs(exponent)}"


def _emit_canonical(value: Any, parts: list[str]) -> None:
    if value is None:
        parts.append("null")
    elif value is True:
        parts.append("true")
    elif value is False:
        parts.append("false")
    elif isinstance(value, int):
        parts.append(str(value))
    elif isinstance(value, float):
        parts.append(_js_number_text(value))
    elif isinstance(value, str):
        parts.append(json.dumps(value, ensure_ascii=False))
    elif isinstance(value, list):
        parts.append("[")
        for index, item in enumerate(value):
            if index:
                parts.append(",")
            _emit_canonical(item, parts)
        parts.append("]")
    elif isinstance(value, dict):
        parts.append("{")
        for index, key in enumerate(sorted(value)):
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            if index:
                parts.append(",")
            parts.append(json.dumps(key, ensure_ascii=False))
            parts.append(":")
            _emit_canonical(value[key], parts)
        parts.append("}")
    else:
        raise TypeError("backup JSON must contain only JSON values")


def _canonical_json(value: Any) -> str:
    """Return the cross-runtime canonical form used by the portable digest.

    One canonical representation is shared with the TypeScript serializer:
    object keys sorted by Unicode code point, ECMAScript number notation,
    and raw non-ASCII characters. Unpaired surrogates fail closed at the
    UTF-8 encoding boundary in ``compute_backup_digest``.
    """
    parts: list[str] = []
    _emit_canonical(value, parts)
    return "".join(parts)


def _digest_payload(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in envelope.items()
        if key not in {"digest", "exported_at"}
    }


def compute_backup_digest(envelope: Mapping[str, Any]) -> str:
    try:
        encoded = _canonical_json(_digest_payload(envelope)).encode("utf-8")
    except UnicodeEncodeError as error:
        # JSON escape sequences can carry unpaired surrogates that the
        # TypeScript canonical form cannot represent identically; both
        # runtimes must reject them instead of guessing a digest.
        raise WorkspaceTransferError(
            "backup contains unpaired surrogate code points"
        ) from error
    return hashlib.sha256(encoded).hexdigest()


def stable_legacy_id(kind: str, legacy_id: str) -> str:
    if kind not in _ENTITY_TYPE_BY_KIND:
        raise WorkspaceTransferError("unsupported workspace record kind")
    _validate_legacy_id(legacy_id)
    identity = f"{WORKSPACE_BACKUP_FORMAT}\0{WORKSPACE_BACKUP_VERSION}\0{kind}\0{legacy_id}"
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]
    return f"{_ID_PREFIX_BY_KIND[kind]}{suffix}"


def _validate_legacy_id(value: Any) -> str:
    if not isinstance(value, str) or not _LEGACY_ID.fullmatch(value):
        raise WorkspaceTransferError("backup contains an invalid opaque identifier")
    if ".." in value or "\\" in value or "/" in value or "\0" in value:
        raise WorkspaceTransferError("backup identifiers must not contain paths")
    if len(value) >= 2 and value[1] == ":" and value[0].isalpha():
        raise WorkspaceTransferError("backup identifiers must not contain paths")
    return value


def _require_object(value: Any, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkspaceTransferError(message)
    if not all(isinstance(key, str) for key in value):
        raise WorkspaceTransferError(message)
    return value


def _require_exact_keys(
    value: Mapping[str, Any], required: set[str], *, optional: set[str] | None = None
) -> None:
    optional = optional or set()
    keys = set(value)
    if not required.issubset(keys) or not keys.issubset(required | optional):
        raise WorkspaceTransferError("backup schema contains missing or unknown fields")


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise WorkspaceTransferError(f"backup {field} must be a positive integer")
    return value


def _timestamp(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WorkspaceTransferError(f"backup {field} must be a millisecond timestamp")
    return value


def _configured_secret_values() -> tuple[str, ...]:
    candidates: list[str] = []
    for name in (
        "local_workspace_token",
        "groq_api_key",
        "groq_api_key_fall_back",
        "qdrant_api_key",
    ):
        configured = getattr(settings, name, None)
        if configured is None:
            continue
        reveal = getattr(configured, "get_secret_value", None)
        raw = reveal() if callable(reveal) else str(configured)
        if raw and len(raw) >= 8:
            candidates.append(raw)
    return tuple(candidates)


def _validate_json_tree(value: Any) -> None:
    secret_values = _configured_secret_values()
    nodes = 0

    def visit(current: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise WorkspaceTransferError("backup JSON exceeds structural limits")
        if current is None or isinstance(current, bool):
            return
        if isinstance(current, int):
            # JavaScript numbers cannot represent larger integers exactly, so
            # a portable digest over them could never be cross-runtime equal.
            if abs(current) > 9007199254740991:
                raise WorkspaceTransferError(
                    "backup contains an integer outside the safe cross-runtime range"
                )
            return
        if isinstance(current, float):
            if not math.isfinite(current):
                raise WorkspaceTransferError("backup JSON must contain finite numbers")
            # Every double at or above 2**53 is integral, so the TypeScript
            # validator already rejects it as an unsafe integer; reject it here
            # too so both runtimes accept exactly the same numbers.
            if abs(current) > 9007199254740991:
                raise WorkspaceTransferError(
                    "backup contains an integer outside the safe cross-runtime range"
                )
            return
        if isinstance(current, str):
            if len(current) > MAX_TEXT_LENGTH:
                raise WorkspaceTransferError("backup contains text exceeding the size limit")
            if any(secret in current for secret in secret_values):
                raise WorkspaceTransferError("backup contains a configured credential value")
            try:
                current.encode("utf-8")
            except UnicodeEncodeError as error:
                raise WorkspaceTransferError(
                    "backup contains unpaired surrogate code points"
                ) from error
            return
        if isinstance(current, list):
            for item in current:
                visit(item, depth + 1)
            return
        if isinstance(current, dict):
            for key, item in current.items():
                if not isinstance(key, str) or len(key) > 256:
                    raise WorkspaceTransferError("backup contains an invalid JSON field")
                try:
                    key.encode("utf-8")
                except UnicodeEncodeError as error:
                    raise WorkspaceTransferError(
                        "backup contains unpaired surrogate code points"
                    ) from error
                normalized_key = key.casefold().replace("-", "_")
                if normalized_key in _SECRET_KEYS:
                    raise WorkspaceTransferError("backup contains a credential field")
                visit(item, depth + 1)
            return
        raise WorkspaceTransferError("backup contains a non-JSON value")

    visit(value, 0)


def _validate_record(raw: Any, kind: str) -> dict[str, Any]:
    record = _require_object(raw, "backup record must be an object")
    required = {
        "legacy_id",
        "schema_version",
        "revision",
        "created_at",
        "updated_at",
        "payload",
    }
    if kind == "evidence_item":
        required.add("parent_legacy_id")
    _require_exact_keys(record, required)
    legacy_id = _validate_legacy_id(record["legacy_id"])
    schema_version = _positive_int(record["schema_version"], "schema_version")
    revision = _positive_int(record["revision"], "revision")
    created_at = _timestamp(record["created_at"], "created_at")
    updated_at = _timestamp(record["updated_at"], "updated_at")
    if updated_at < created_at:
        raise WorkspaceTransferError("backup record timestamps are inconsistent")
    payload = _require_object(record["payload"], "backup record payload must be an object")
    _validate_json_tree(payload)
    if payload.get("id") != legacy_id:
        raise WorkspaceTransferError("backup record identity does not match its payload")

    if kind == "conversation":
        if schema_version != 4 or payload.get("schemaVersion") != 4:
            raise WorkspaceTransferError("unsupported conversation schema version")
        if payload.get("revision") != revision:
            raise WorkspaceTransferError("conversation revision does not match its payload")
        if payload.get("createdAt") != created_at or payload.get("updatedAt") != updated_at:
            raise WorkspaceTransferError("conversation timestamps do not match its payload")
        if not isinstance(payload.get("sessionId"), str) or not isinstance(payload.get("title"), str):
            raise WorkspaceTransferError("conversation identity fields are malformed")
        if payload.get("titleMode") not in {"auto", "custom"}:
            raise WorkspaceTransferError("conversation title mode is malformed")
        if not isinstance(payload.get("messages"), list) or len(payload["messages"]) > 5_000:
            raise WorkspaceTransferError("conversation messages are malformed or exceed limits")
        if not isinstance(payload.get("draft"), str) or not isinstance(payload.get("bookmarkedMessageIds"), list):
            raise WorkspaceTransferError("conversation state is malformed")
        notes = payload.get("notes", [])
        variants = payload.get("variants", [])
        if not isinstance(notes, list) or len(notes) > 50:
            raise WorkspaceTransferError("conversation notes are malformed or exceed limits")
        if not isinstance(variants, list) or len(variants) > 100:
            raise WorkspaceTransferError("conversation variants are malformed or exceed limits")
    elif kind == "collection":
        if schema_version not in {1, 2}:
            raise WorkspaceTransferError("unsupported evidence collection schema version")
        payload_schema = payload.get("schemaVersion")
        if schema_version == 1 and payload_schema is not None:
            raise WorkspaceTransferError("legacy collection schema is inconsistent")
        if schema_version == 2 and payload_schema != 2:
            raise WorkspaceTransferError("evidence collection schema is inconsistent")
        if not isinstance(payload.get("name"), str) or not payload["name"].strip():
            raise WorkspaceTransferError("evidence collection name is malformed")
        if "items" in payload:
            raise WorkspaceTransferError("collection items must use evidence_items records")
        if payload.get("createdAt") != created_at or payload.get("updatedAt") != updated_at:
            raise WorkspaceTransferError("collection timestamps do not match its payload")
    else:
        if schema_version not in {1, 2}:
            raise WorkspaceTransferError("unsupported evidence item schema version")
        parent_id = _validate_legacy_id(record["parent_legacy_id"])
        if not isinstance(payload.get("citation"), str) or not isinstance(payload.get("excerpt"), str):
            raise WorkspaceTransferError("evidence item content is malformed")
        if payload.get("savedAt") != created_at or updated_at != created_at:
            raise WorkspaceTransferError("evidence item timestamps are inconsistent")
        record = {**record, "parent_legacy_id": parent_id}

    return {
        **record,
        "legacy_id": legacy_id,
        "schema_version": schema_version,
        "revision": revision,
        "created_at": created_at,
        "updated_at": updated_at,
        "payload": payload,
    }


def _validate_tombstone(raw: Any) -> dict[str, Any]:
    tombstone = _require_object(raw, "backup tombstone must be an object")
    _require_exact_keys(
        tombstone,
        {"kind", "legacy_id", "schema_version", "revision", "deleted_at"},
    )
    if tombstone["kind"] != "conversation":
        raise WorkspaceTransferError("unsupported tombstone kind")
    if _positive_int(tombstone["schema_version"], "tombstone schema_version") != 1:
        raise WorkspaceTransferError("unsupported tombstone schema version")
    return {
        "kind": "conversation",
        "legacy_id": _validate_legacy_id(tombstone["legacy_id"]),
        "schema_version": 1,
        "revision": _positive_int(tombstone["revision"], "tombstone revision"),
        "deleted_at": _timestamp(tombstone["deleted_at"], "deleted_at"),
    }


def _validate_unsupported(raw: Any) -> dict[str, Any]:
    descriptor = _require_object(raw, "unsupported source descriptor must be an object")
    _require_exact_keys(descriptor, {"source", "schema_version", "count", "reason"})
    if not isinstance(descriptor["source"], str) or not descriptor["source"]:
        raise WorkspaceTransferError("unsupported source descriptor is malformed")
    schema_version = descriptor["schema_version"]
    if schema_version is not None and (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version < 1
    ):
        raise WorkspaceTransferError("unsupported source schema version is malformed")
    count = _positive_int(descriptor["count"], "unsupported count")
    if not isinstance(descriptor["reason"], str) or not descriptor["reason"]:
        raise WorkspaceTransferError("unsupported source reason is malformed")
    if len(descriptor["reason"]) > 256 or len(descriptor["source"]) > 128:
        raise WorkspaceTransferError("unsupported source descriptor exceeds limits")
    _validate_json_tree(descriptor)
    return dict(descriptor, count=count)


def validate_workspace_backup(raw: Any) -> ValidatedBackup:
    envelope = _require_object(raw, "workspace backup must be a JSON object")
    required = {
        "format",
        "version",
        "exported_at",
        "source_schemas",
        "source_counts",
        "conversations",
        "collections",
        "evidence_items",
        "favorites",
        "tombstones",
        "unsupported",
        "digest",
    }
    _require_exact_keys(envelope, required)
    try:
        encoded = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except UnicodeEncodeError as error:
        raise WorkspaceTransferError(
            "backup contains unpaired surrogate code points"
        ) from error
    except (TypeError, ValueError) as error:
        raise WorkspaceTransferError("workspace backup contains invalid JSON") from error
    if len(encoded) > MAX_BACKUP_BYTES:
        raise WorkspaceTransferError("workspace backup exceeds the 25 MiB limit")
    if envelope["format"] != WORKSPACE_BACKUP_FORMAT:
        raise WorkspaceTransferError("workspace backup format is not supported")
    if envelope["version"] != WORKSPACE_BACKUP_VERSION:
        raise WorkspaceTransferError("workspace backup version is not supported")
    if not isinstance(envelope["exported_at"], str) or len(envelope["exported_at"]) > 64:
        raise WorkspaceTransferError("workspace backup export timestamp is malformed")
    try:
        datetime.fromisoformat(envelope["exported_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise WorkspaceTransferError("workspace backup export timestamp is malformed") from error
    digest = envelope["digest"]
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise WorkspaceTransferError("workspace backup digest is malformed")

    source_schemas = _require_object(
        envelope["source_schemas"], "workspace source schemas must be an object"
    )
    _require_exact_keys(
        source_schemas,
        {"conversations", "evidence_collections", "favorites", "tombstones"},
    )
    for values in source_schemas.values():
        if not isinstance(values, list) or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1
            for item in values
        ):
            raise WorkspaceTransferError("workspace source schemas are malformed")
        if values != sorted(set(values)):
            raise WorkspaceTransferError("workspace source schemas must be sorted and unique")
    if any(version > 4 for version in source_schemas["conversations"]):
        raise WorkspaceTransferError("unsupported future conversation schema version")
    if any(version > 2 for version in source_schemas["evidence_collections"]):
        raise WorkspaceTransferError("unsupported future evidence collection schema version")
    if any(version > 1 for version in source_schemas["favorites"] + source_schemas["tombstones"]):
        raise WorkspaceTransferError("unsupported future browser storage schema version")

    raw_conversations = envelope["conversations"]
    raw_collections = envelope["collections"]
    raw_items = envelope["evidence_items"]
    raw_favorites = envelope["favorites"]
    raw_tombstones = envelope["tombstones"]
    raw_unsupported = envelope["unsupported"]
    for value, limit, label in (
        (raw_conversations, MAX_CONVERSATIONS, "conversations"),
        (raw_collections, MAX_COLLECTIONS, "collections"),
        (raw_items, MAX_EVIDENCE_ITEMS, "evidence items"),
        (raw_favorites, MAX_FAVORITES, "favorites"),
        (raw_tombstones, MAX_TOMBSTONES, "tombstones"),
        (raw_unsupported, MAX_UNSUPPORTED_DESCRIPTORS, "unsupported sources"),
    ):
        if not isinstance(value, list) or len(value) > limit:
            raise WorkspaceTransferError(f"workspace backup {label} exceed limits")

    conversations = tuple(_validate_record(item, "conversation") for item in raw_conversations)
    collections = tuple(_validate_record(item, "collection") for item in raw_collections)
    evidence_items = tuple(_validate_record(item, "evidence_item") for item in raw_items)
    favorites = tuple(_validate_legacy_id(item) for item in raw_favorites)
    tombstones = tuple(_validate_tombstone(item) for item in raw_tombstones)
    unsupported = tuple(_validate_unsupported(item) for item in raw_unsupported)

    expected_schemas = {
        "conversations": sorted({item["schema_version"] for item in conversations}),
        "evidence_collections": sorted(
            {item["schema_version"] for item in (*collections, *evidence_items)}
        ),
        "favorites": [1] if favorites else [],
        "tombstones": [1] if tombstones else [],
    }
    if source_schemas != expected_schemas:
        raise WorkspaceTransferError("workspace source schemas do not match the payload")

    for records in (conversations, collections, evidence_items):
        ids = [record["legacy_id"] for record in records]
        if len(ids) != len(set(ids)):
            raise WorkspaceTransferError("workspace backup contains duplicate record identities")
    if len(favorites) != len(set(favorites)):
        raise WorkspaceTransferError("workspace backup contains duplicate favorites")
    tombstone_ids = [record["legacy_id"] for record in tombstones]
    if len(tombstone_ids) != len(set(tombstone_ids)):
        raise WorkspaceTransferError("workspace backup contains duplicate tombstones")
    if set(tombstone_ids) & {record["legacy_id"] for record in conversations}:
        raise WorkspaceTransferError("workspace backup contains live and deleted copies of one conversation")
    collection_ids = {record["legacy_id"] for record in collections}
    if any(item["parent_legacy_id"] not in collection_ids for item in evidence_items):
        raise WorkspaceTransferError("evidence item references a missing collection")
    if any(item not in collection_ids for item in favorites):
        raise WorkspaceTransferError("favorite references a missing collection")

    counts = _require_object(envelope["source_counts"], "workspace source counts must be an object")
    _require_exact_keys(
        counts,
        {"conversations", "collections", "evidence_items", "favorites", "tombstones", "unsupported"},
    )
    expected_counts = {
        "conversations": len(conversations),
        "collections": len(collections),
        "evidence_items": len(evidence_items),
        "favorites": len(favorites),
        "tombstones": len(tombstones),
        "unsupported": sum(item["count"] for item in unsupported),
    }
    if counts != expected_counts:
        raise WorkspaceTransferError("workspace source counts do not match the payload")

    calculated = compute_backup_digest(envelope)
    if not hmac.compare_digest(digest, calculated):
        raise WorkspaceTransferError("workspace backup digest does not match its contents")

    return ValidatedBackup(
        envelope=dict(envelope),
        digest=digest,
        conversations=conversations,
        collections=collections,
        evidence_items=evidence_items,
        favorites=favorites,
        tombstones=tombstones,
        unsupported=unsupported,
    )


def build_workspace_backup(
    *,
    conversations: Sequence[dict[str, Any]],
    collections: Sequence[dict[str, Any]],
    evidence_items: Sequence[dict[str, Any]],
    favorites: Sequence[str],
    tombstones: Sequence[dict[str, Any]],
    unsupported: Sequence[dict[str, Any]] = (),
    exported_at: str | None = None,
) -> dict[str, Any]:
    source_schemas = {
        "conversations": sorted({item["schema_version"] for item in conversations}),
        "evidence_collections": sorted(
            {item["schema_version"] for item in [*collections, *evidence_items]}
        ),
        "favorites": [1] if favorites else [],
        "tombstones": [1] if tombstones else [],
    }
    ordered_conversations = sorted(conversations, key=lambda item: item["legacy_id"])
    ordered_collections = sorted(collections, key=lambda item: item["legacy_id"])
    ordered_items = sorted(
        evidence_items,
        key=lambda item: (item["parent_legacy_id"], item["legacy_id"]),
    )
    ordered_favorites = sorted(set(favorites))
    ordered_tombstones = sorted(tombstones, key=lambda item: item["legacy_id"])
    ordered_unsupported = sorted(
        unsupported,
        key=lambda item: (item["source"], item.get("schema_version") or 0, item["reason"]),
    )
    envelope: dict[str, Any] = {
        "format": WORKSPACE_BACKUP_FORMAT,
        "version": WORKSPACE_BACKUP_VERSION,
        "exported_at": exported_at or _utc_now(),
        "source_schemas": source_schemas,
        "source_counts": {
            "conversations": len(ordered_conversations),
            "collections": len(ordered_collections),
            "evidence_items": len(ordered_items),
            "favorites": len(ordered_favorites),
            "tombstones": len(ordered_tombstones),
            "unsupported": sum(item["count"] for item in ordered_unsupported),
        },
        "conversations": ordered_conversations,
        "collections": ordered_collections,
        "evidence_items": ordered_items,
        "favorites": ordered_favorites,
        "tombstones": ordered_tombstones,
        "unsupported": ordered_unsupported,
    }
    envelope["digest"] = compute_backup_digest(envelope)
    validate_workspace_backup(envelope)
    return envelope


class WorkspaceTransferService:
    """Read-only preview/export and transactional idempotent import service."""

    def __init__(
        self,
        database: WorkspaceDatabase,
        *,
        failure_injector: Callable[[str, int], None] | None = None,
    ) -> None:
        self.database = database
        self.failure_injector = failure_injector

    @staticmethod
    def _mapping(kind: str, legacy_id: str) -> dict[str, str]:
        return {
            "kind": kind,
            "legacy_id": legacy_id,
            "workspace_id": stable_legacy_id(kind, legacy_id),
        }

    @staticmethod
    def _wrapped_payload(
        kind: str,
        record: Mapping[str, Any],
        *,
        favorite: bool = False,
    ) -> dict[str, Any]:
        wrapper: dict[str, Any] = {
            "workspace_transfer_version": WORKSPACE_BACKUP_VERSION,
            "source_kind": kind,
            "legacy_id": record["legacy_id"],
            "source_schema_version": record["schema_version"],
            "data": record["payload"],
        }
        if kind == "collection":
            wrapper["favorite"] = favorite
        if kind == "evidence_item":
            wrapper["parent_legacy_id"] = record["parent_legacy_id"]
            wrapper["parent_workspace_id"] = stable_legacy_id(
                "collection", record["parent_legacy_id"]
            )
        return wrapper

    def _plan(self, connection: sqlite3.Connection, backup: ValidatedBackup) -> dict[str, Any]:
        mappings: list[dict[str, str]] = []
        actions: list[dict[str, Any]] = []
        duplicates = 0
        conflicts = 0
        creates = 0
        updates = 0
        skipped = 0
        favorites = set(backup.favorites)

        for kind, record in backup.records:
            workspace_id = stable_legacy_id(kind, record["legacy_id"])
            entity_type = _ENTITY_TYPE_BY_KIND[kind]
            mapping = self._mapping(kind, record["legacy_id"])
            mappings.append(mapping)
            existing_tombstone = connection.execute(
                "SELECT revision FROM tombstones WHERE entity_type = ? AND entity_id = ?",
                (entity_type, workspace_id),
            ).fetchone()
            if existing_tombstone is not None:
                action = "blocked_by_tombstone"
                conflicts += 1
                skipped += 1
            else:
                existing = connection.execute(
                    "SELECT revision, payload_json FROM workspace_records "
                    "WHERE entity_type = ? AND entity_id = ?",
                    (entity_type, workspace_id),
                ).fetchone()
                incoming_payload = self._wrapped_payload(
                    kind,
                    record,
                    favorite=kind == "collection" and record["legacy_id"] in favorites,
                )
                incoming_json = _canonical_json(incoming_payload)
                if existing is None:
                    action = "create"
                    creates += 1
                else:
                    try:
                        existing_payload = json.loads(existing["payload_json"])
                    except (TypeError, json.JSONDecodeError):
                        existing_payload = None
                    owned_existing = (
                        isinstance(existing_payload, dict)
                        and existing_payload.get("workspace_transfer_version") == WORKSPACE_BACKUP_VERSION
                        and existing_payload.get("source_kind") == kind
                        and existing_payload.get("legacy_id") == record["legacy_id"]
                    )
                    if not owned_existing:
                        action = "conflict"
                        conflicts += 1
                        skipped += 1
                    elif int(existing["revision"]) == record["revision"] and existing["payload_json"] == incoming_json:
                        action = "duplicate"
                        duplicates += 1
                        skipped += 1
                    elif int(existing["revision"]) < record["revision"]:
                        action = "replace_older"
                        updates += 1
                    else:
                        action = "conflict"
                        conflicts += 1
                        skipped += 1
            actions.append(
                {
                    "action": action,
                    "kind": kind,
                    "workspace_id": workspace_id,
                    "record": record,
                }
            )

        for tombstone in backup.tombstones:
            kind = tombstone["kind"]
            workspace_id = stable_legacy_id(kind, tombstone["legacy_id"])
            entity_type = _ENTITY_TYPE_BY_KIND[kind]
            mapping = self._mapping(kind, tombstone["legacy_id"])
            if mapping not in mappings:
                mappings.append(mapping)
            existing_tombstone = connection.execute(
                "SELECT revision FROM tombstones WHERE entity_type = ? AND entity_id = ?",
                (entity_type, workspace_id),
            ).fetchone()
            existing_live = connection.execute(
                "SELECT revision, payload_json FROM workspace_records WHERE entity_type = ? AND entity_id = ?",
                (entity_type, workspace_id),
            ).fetchone()
            owned_live = True
            if existing_live is not None:
                try:
                    live_payload = json.loads(existing_live["payload_json"])
                except (TypeError, json.JSONDecodeError):
                    live_payload = None
                owned_live = (
                    isinstance(live_payload, dict)
                    and live_payload.get("workspace_transfer_version") == WORKSPACE_BACKUP_VERSION
                    and live_payload.get("source_kind") == kind
                    and live_payload.get("legacy_id") == tombstone["legacy_id"]
                )
            if existing_live is not None and not owned_live:
                action = "tombstone_conflict"
                conflicts += 1
                skipped += 1
            elif existing_live is not None and int(existing_live["revision"]) > tombstone["revision"]:
                action = "tombstone_conflict"
                conflicts += 1
                skipped += 1
            elif existing_tombstone is None:
                action = "tombstone_create"
            elif int(existing_tombstone["revision"]) == tombstone["revision"]:
                action = "tombstone_duplicate"
                duplicates += 1
                skipped += 1
            elif int(existing_tombstone["revision"]) < tombstone["revision"]:
                action = "tombstone_replace"
            else:
                action = "tombstone_conflict"
                conflicts += 1
                skipped += 1
            actions.append(
                {
                    "action": action,
                    "kind": kind,
                    "workspace_id": workspace_id,
                    "record": tombstone,
                }
            )

        mappings.sort(key=lambda item: (item["kind"], item["legacy_id"]))
        preview = {
            "format": WORKSPACE_BACKUP_FORMAT,
            "version": WORKSPACE_BACKUP_VERSION,
            "digest": backup.digest,
            "compatibility": "partial" if backup.unsupported else "compatible",
            "supported": {
                "conversations": len(backup.conversations),
                "collections": len(backup.collections),
                "evidence_items": len(backup.evidence_items),
                "favorites": len(backup.favorites),
            },
            "unsupported": sum(item["count"] for item in backup.unsupported),
            "unsupported_sources": list(backup.unsupported),
            "duplicates": duplicates,
            "potential_conflicts": conflicts,
            "tombstones": len(backup.tombstones),
            "records_to_create": creates,
            "records_to_update": updates,
            "records_to_skip": skipped,
            "mapping_required": len(mappings),
            "mappings": mappings,
        }
        return {"preview": preview, "actions": actions}

    def preview(self, raw: Any) -> dict[str, Any]:
        backup = validate_workspace_backup(raw)
        with self.database.transaction() as connection:
            return self._plan(connection, backup)["preview"]

    def import_backup(self, raw: Any, preview_digest: str) -> dict[str, Any]:
        backup = validate_workspace_backup(raw)
        if not isinstance(preview_digest, str) or not hmac.compare_digest(
            preview_digest, backup.digest
        ):
            raise WorkspaceTransferError("preview digest does not match the backup")

        with self.database.transaction(write=True) as connection:
            prior = connection.execute(
                "SELECT counts_json FROM workspace_imports WHERE source_digest = ?",
                (backup.digest,),
            ).fetchone()
            if prior is not None:
                try:
                    receipt = json.loads(prior["counts_json"])
                except (TypeError, json.JSONDecodeError) as error:
                    raise WorkspaceTransferError("stored import receipt is invalid") from error
                if not isinstance(receipt, dict):
                    raise WorkspaceTransferError("stored import receipt is invalid")
                return receipt

            plan = self._plan(connection, backup)
            applied = 0
            favorites = set(backup.favorites)
            for operation in plan["actions"]:
                action = operation["action"]
                if action in {"duplicate", "conflict", "blocked_by_tombstone", "tombstone_duplicate", "tombstone_conflict"}:
                    continue
                kind = operation["kind"]
                entity_type = _ENTITY_TYPE_BY_KIND[kind]
                workspace_id = operation["workspace_id"]
                record = operation["record"]
                if action in {"create", "replace_older"}:
                    payload_json = _canonical_json(
                        self._wrapped_payload(
                            kind,
                            record,
                            favorite=kind == "collection" and record["legacy_id"] in favorites,
                        )
                    )
                    if action == "create":
                        connection.execute(
                            "INSERT INTO workspace_records("
                            "entity_type, entity_id, revision, payload_json, created_at, updated_at"
                            ") VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                entity_type,
                                workspace_id,
                                record["revision"],
                                payload_json,
                                datetime.fromtimestamp(record["created_at"] / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
                                datetime.fromtimestamp(record["updated_at"] / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
                            ),
                        )
                    else:
                        connection.execute(
                            "UPDATE workspace_records SET revision = ?, payload_json = ?, created_at = ?, updated_at = ? "
                            "WHERE entity_type = ? AND entity_id = ?",
                            (
                                record["revision"],
                                payload_json,
                                datetime.fromtimestamp(record["created_at"] / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
                                datetime.fromtimestamp(record["updated_at"] / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
                                entity_type,
                                workspace_id,
                            ),
                        )
                else:
                    deleted_at = datetime.fromtimestamp(
                        record["deleted_at"] / 1000, timezone.utc
                    ).isoformat().replace("+00:00", "Z")
                    connection.execute(
                        "DELETE FROM workspace_records WHERE entity_type = ? AND entity_id = ?",
                        (entity_type, workspace_id),
                    )
                    connection.execute(
                        "INSERT INTO tombstones(entity_type, entity_id, revision, deleted_at) "
                        "VALUES (?, ?, ?, ?) ON CONFLICT(entity_type, entity_id) DO UPDATE SET "
                        "revision = excluded.revision, deleted_at = excluded.deleted_at",
                        (entity_type, workspace_id, record["revision"], deleted_at),
                    )
                applied += 1
                if self.failure_injector is not None:
                    self.failure_injector(action, applied)

            now = _utc_now()
            import_id = f"import-{backup.digest[:40]}"
            receipt = {
                "import_id": import_id,
                "status": "committed",
                "digest": backup.digest,
                "completed_at": now,
                **plan["preview"],
            }
            connection.execute(
                "INSERT INTO workspace_imports("
                "import_id, source_digest, source_schema_version, status, counts_json, created_at, completed_at"
                ") VALUES (?, ?, ?, 'committed', ?, ?, ?)",
                (
                    import_id,
                    backup.digest,
                    WORKSPACE_BACKUP_VERSION,
                    _canonical_json(receipt),
                    now,
                    now,
                ),
            )
            return receipt

    def export_backup(self) -> dict[str, Any]:
        conversations: list[dict[str, Any]] = []
        collections: list[dict[str, Any]] = []
        evidence_items: list[dict[str, Any]] = []
        favorites: list[str] = []
        tombstones: list[dict[str, Any]] = []
        unsupported_count = 0

        with self.database.transaction() as connection:
            rows = list(
                connection.execute(
                    "SELECT entity_type, entity_id, revision, payload_json, created_at, updated_at "
                    "FROM workspace_records ORDER BY entity_type, entity_id"
                )
            )
            reverse_mappings: dict[tuple[str, str], tuple[str, str]] = {}
            receipt_rows = connection.execute(
                "SELECT counts_json FROM workspace_imports WHERE status = 'committed' ORDER BY import_id"
            )
            for receipt_row in receipt_rows:
                try:
                    receipt = json.loads(receipt_row["counts_json"])
                except (TypeError, json.JSONDecodeError):
                    unsupported_count += 1
                    continue
                for mapping in receipt.get("mappings", []) if isinstance(receipt, dict) else []:
                    if not isinstance(mapping, dict):
                        continue
                    kind = mapping.get("kind")
                    legacy_id = mapping.get("legacy_id")
                    workspace_id = mapping.get("workspace_id")
                    if kind in _ENTITY_TYPE_BY_KIND and isinstance(legacy_id, str) and isinstance(workspace_id, str):
                        reverse_mappings[(_ENTITY_TYPE_BY_KIND[kind], workspace_id)] = (kind, legacy_id)

            for row in rows:
                try:
                    wrapper = json.loads(row["payload_json"])
                except (TypeError, json.JSONDecodeError):
                    unsupported_count += 1
                    continue
                if not isinstance(wrapper, dict) or wrapper.get("workspace_transfer_version") != 1:
                    unsupported_count += 1
                    continue
                kind = wrapper.get("source_kind")
                legacy_id = wrapper.get("legacy_id")
                schema_version = wrapper.get("source_schema_version")
                payload = wrapper.get("data")
                if kind not in _ENTITY_TYPE_BY_KIND or not isinstance(payload, dict):
                    unsupported_count += 1
                    continue
                record: dict[str, Any] = {
                    "legacy_id": legacy_id,
                    "schema_version": schema_version,
                    "revision": int(row["revision"]),
                    "created_at": _timestamp_ms(row["created_at"]),
                    "updated_at": _timestamp_ms(row["updated_at"]),
                    "payload": payload,
                }
                if kind == "conversation":
                    conversations.append(record)
                elif kind == "collection":
                    collections.append(record)
                    if wrapper.get("favorite") is True:
                        favorites.append(legacy_id)
                else:
                    record["parent_legacy_id"] = wrapper.get("parent_legacy_id")
                    evidence_items.append(record)

            for row in connection.execute(
                "SELECT entity_type, entity_id, revision, deleted_at FROM tombstones "
                "ORDER BY entity_type, entity_id"
            ):
                mapping = reverse_mappings.get((row["entity_type"], row["entity_id"]))
                if mapping is None:
                    unsupported_count += 1
                    continue
                kind, legacy_id = mapping
                if kind != "conversation":
                    unsupported_count += 1
                    continue
                tombstones.append(
                    {
                        "kind": kind,
                        "legacy_id": legacy_id,
                        "schema_version": 1,
                        "revision": int(row["revision"]),
                        "deleted_at": _timestamp_ms(row["deleted_at"]),
                    }
                )

        unsupported = (
            [
                {
                    "source": "workspace_records",
                    "schema_version": None,
                    "count": unsupported_count,
                    "reason": "record is not part of the portable DATA-002 transfer contract",
                }
            ]
            if unsupported_count
            else []
        )
        return build_workspace_backup(
            conversations=conversations,
            collections=collections,
            evidence_items=evidence_items,
            favorites=favorites,
            tombstones=tombstones,
            unsupported=unsupported,
        )
