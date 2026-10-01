"""Read explicitly published native reports from the existing public directory.

This module never publishes or modifies a report. A publication envelope adds
an ordering timestamp that the private EVAL-001 report intentionally lacks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.evaluation.native_protocol import (
    MAX_REPORT_BYTES,
    NativeProtocolError,
    NativeReport,
    UnsupportedNativeProtocolVersion,
    parse_native_report,
)

PUBLICATION_VERSION = 1
MAX_PUBLICATIONS = 1000
MAX_ENVELOPE_BYTES = MAX_REPORT_BYTES + 4096
MAX_TOTAL_ENVELOPE_BYTES = 50_000_000
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SUFFIX = ".native.json"


class NativePublicationError(ValueError):
    """A selected or discovered public native artifact is unsafe or invalid."""


class InvalidPublishedRunId(NativePublicationError):
    """A caller-supplied report identity is not a safe publication key."""


class UnsupportedNativePublicationVersion(NativePublicationError):
    """The publication envelope or contained native protocol is unsupported."""


@dataclass(frozen=True)
class PublishedNativeReport:
    published_at: datetime
    report: NativeReport


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise NativePublicationError("duplicate publication JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise NativePublicationError("non-finite publication JSON value")


def _path(run_id: str, root: Path) -> Path:
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id) or ".." in run_id:
        raise InvalidPublishedRunId("invalid published run ID")
    base = root.resolve()
    target = base / f"{run_id}{_SUFFIX}"
    if target.parent != base or target.is_symlink():
        raise NativePublicationError("invalid native publication path")
    return target


def _load(path: Path, root: Path) -> PublishedNativeReport:
    if path.is_symlink() or path.parent.resolve() != root.resolve():
        raise NativePublicationError("invalid native publication path")
    try:
        if path.stat().st_size > MAX_ENVELOPE_BYTES:
            raise NativePublicationError("native publication exceeds size limit")
        with path.open("rb") as file:
            encoded = file.read(MAX_ENVELOPE_BYTES + 1)
        if len(encoded) > MAX_ENVELOPE_BYTES:
            raise NativePublicationError("native publication exceeds size limit")
        payload = json.loads(
            encoded, object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(payload, dict) or set(payload) != {"schema_version", "published_at", "report"}:
            raise NativePublicationError("invalid native publication fields")
        if type(payload["schema_version"]) is not int or payload["schema_version"] != PUBLICATION_VERSION:
            raise UnsupportedNativePublicationVersion("unsupported native publication version")
        if not isinstance(payload["published_at"], str):
            raise NativePublicationError("publication timestamp is required")
        timestamp = datetime.fromisoformat(payload["published_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise NativePublicationError("publication timestamp needs a timezone")
        report = parse_native_report(payload["report"])
        expected = _path(report.run_id, root)
        if path.name != expected.name:
            raise NativePublicationError("published run ID does not match filename")
        return PublishedNativeReport(timestamp.astimezone(timezone.utc), report)
    except (OSError, UnicodeError, json.JSONDecodeError, NativeProtocolError, TypeError, ValueError, RecursionError, OverflowError) as error:
        if isinstance(error, InvalidPublishedRunId):
            raise NativePublicationError("invalid published report identity") from error
        if isinstance(error, UnsupportedNativeProtocolVersion):
            raise UnsupportedNativePublicationVersion("unsupported native report protocol version") from error
        if isinstance(error, NativePublicationError):
            raise
        raise NativePublicationError("invalid native publication artifact") from error


def get_published_native_report(run_id: str, *, root: Path) -> PublishedNativeReport | None:
    """Return one validated native publication, or None only when absent."""
    if root.is_symlink():
        raise NativePublicationError("invalid native publication directory")
    path = _path(run_id, root)
    if not path.exists():
        return None
    return _load(path, root)


def list_published_native_reports(*, root: Path) -> tuple[PublishedNativeReport, ...]:
    """Discover only fixed-directory native envelopes; malformed data fails closed."""
    if not root.exists():
        return ()
    if not root.is_dir() or root.is_symlink():
        raise NativePublicationError("invalid native publication directory")
    paths = sorted(root.glob(f"*{_SUFFIX}"), key=lambda item: item.name)
    if len(paths) > MAX_PUBLICATIONS:
        raise NativePublicationError("too many native publications")
    try:
        if sum(path.stat().st_size for path in paths) > MAX_TOTAL_ENVELOPE_BYTES:
            raise NativePublicationError("native publication history exceeds size limit")
    except OSError as error:
        raise NativePublicationError("cannot inspect native publication history") from error
    reports = tuple(_load(path, root) for path in paths)
    ids = [item.report.run_id for item in reports]
    if len(ids) != len(set(ids)):
        raise NativePublicationError("duplicate published run ID")
    return tuple(sorted(reports, key=lambda item: (item.published_at, item.report.run_id, item.report.digest)))
