"""Durable, content-free terminal telemetry and sanitized operational projections.

Request terminal facts are immutable rows in the existing workspace database.
DATA-004 jobs remain authoritative in ``jobs`` and are projected at read time;
they are never copied into telemetry rows.
"""

from __future__ import annotations

import base64
import json
import math
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath, PureWindowsPath
from typing import Callable, Iterable, Literal, Mapping, cast

from configs.settings import Settings, settings
from src.workspace.database import WorkspaceDatabase
from src.workspace.repository import utc_timestamp


TelemetrySubsystem = Literal["query", "search", "retrieval"]
TelemetrySeverity = Literal["info", "warning", "error"]
TelemetryOutcome = Literal["succeeded", "rejected", "failed", "cancelled", "interrupted"]
LogCategory = Literal["request", "job"]
AnalyticsRange = Literal["24h", "7d", "30d"]
AnalyticsInterval = Literal["hour", "day"]
AnalyticsMetric = Literal[
    "request_count",
    "request_failure_count",
    "request_duration_p50_ms",
    "request_duration_p95_ms",
    "terminal_job_count",
]

TELEMETRY_RECORD_SCHEMA_VERSION = 1
TELEMETRY_RETENTION_DAYS = 30
LOG_RETENTION_DAYS = 7
MAX_METADATA_BYTES = 2048
MAX_DURATION_MS = 86_400_000.0
MAX_LOG_LIMIT = 100
MAX_CURSOR_CHARS = 512
MAX_TIMESERIES_BUCKETS = 744

_OUTCOMES = frozenset({"succeeded", "rejected", "failed", "cancelled", "interrupted"})
_SEVERITIES = frozenset({"info", "warning", "error"})
_SUBSYSTEMS = frozenset({"query", "search", "retrieval"})
_CAPABILITIES = frozenset({"provider_backed", "public_provider_free"})
_TERMINAL_JOB_STATES = frozenset({"cancelled", "succeeded", "failed", "interrupted"})
_JOB_NAMESPACES = frozenset({"pipeline", "evaluation", "model_test"})
_ROUTE_PROFILES: dict[str, tuple[TelemetrySubsystem, str]] = {
    "/query": ("query", "provider_backed"),
    "/query/decomposed": ("query", "provider_backed"),
    "/query/stream": ("query", "provider_backed"),
    "/query/decomposed/stream": ("query", "provider_backed"),
    "/search": ("search", "public_provider_free"),
    "/retrieval/inspect": ("retrieval", "public_provider_free"),
}
_ALLOWED_METADATA = frozenset({"http_method", "streaming", "decomposed", "status_code"})
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TELEMETRY_ID = re.compile(r"^tel_[A-Za-z0-9][A-Za-z0-9_-]{0,123}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_CREDENTIAL_TEXT = re.compile(
    r"(?:authorization|bearer|api[ _-]?key|password|secret|token)\s*[:=]",
    re.IGNORECASE,
)
_CREDENTIAL_PREFIX = re.compile(
    r"^(?:sk-|ghp_|github_pat_|xox[baprs]-|AIza)",
    re.IGNORECASE,
)


class TelemetryError(RuntimeError):
    """Base error for DATA-005 telemetry operations."""


class TelemetryValidationError(TelemetryError):
    """A record or query does not satisfy the bounded contract."""


class TelemetryConflictError(TelemetryError):
    """An immutable telemetry identity was reused with different facts."""


class TelemetryDataError(TelemetryError):
    """Persisted telemetry is malformed or outside the current contract."""


@dataclass(frozen=True)
class TerminalTelemetryRecord:
    telemetry_id: str
    event_kind: Literal["request_terminal"]
    subsystem: TelemetrySubsystem
    severity: TelemetrySeverity
    outcome: TelemetryOutcome
    route_template: str
    capability: str
    correlation_id: str
    duration_ms: float | None
    error_code: str | None
    metadata: dict[str, object]
    occurred_at: str
    retention_until: str


@dataclass(frozen=True)
class OperationalLogRecord:
    record_id: str
    occurred_at: str
    category: LogCategory
    level: TelemetrySeverity
    kind: str
    subsystem: str
    outcome: str
    correlation_id: str
    domain_id: str | None
    route_template: str | None
    error_code: str | None
    duration_ms: float | None
    metadata: dict[str, object]


@dataclass(frozen=True)
class OperationalLogPage:
    items: tuple[OperationalLogRecord, ...]
    next_cursor: str | None
    has_more: bool
    limit: int


@dataclass(frozen=True)
class TimeSeriesPoint:
    started_at: str
    ended_at: str
    value: float | int | None
    denominator: int


def telemetry_route_profile(route_template: str) -> tuple[TelemetrySubsystem, str] | None:
    """Return the allowlisted subsystem/capability for one exact route template."""
    return _ROUTE_PROFILES.get(route_template)


def safe_request_correlation_id(
    value: str | None,
    configured: Settings,
    *,
    id_factory: Callable[[], str] | None = None,
) -> str:
    """Accept only a safe opaque client request ID; otherwise mint a server ID."""
    forbidden = _configured_secret_values(configured)
    if isinstance(value, str) and _OPAQUE_ID.fullmatch(value):
        try:
            _reject_sensitive_text(value, forbidden, label="request correlation ID")
        except TelemetryValidationError:
            pass
        else:
            return value
    suffix = (id_factory or (lambda: uuid.uuid4().hex))()
    generated = f"req_{suffix}"
    if not _OPAQUE_ID.fullmatch(generated):
        raise TelemetryValidationError("request ID factory returned an invalid identity")
    return generated


def _configured_secret_values(configured: Settings) -> tuple[str, ...]:
    values = (
        configured.local_workspace_token.get_secret_value(),
        configured.groq_api_key,
        configured.groq_api_key2,
        configured.groq_api_key3,
        configured.groq_api_key4,
        configured.groq_api_key5,
        configured.groq_api_key_fall_back,
        configured.groq_api_key_fall_back2,
        configured.qdrant_cloud_api_key,
    )
    return tuple(value for value in values if value)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_utc(value: str, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 40:
        raise TelemetryValidationError(f"{label} must be a bounded UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise TelemetryValidationError(f"{label} must be a valid UTC timestamp") from error
    if parsed.utcoffset() != timedelta(0):
        raise TelemetryValidationError(f"{label} must use UTC")
    return parsed.astimezone(timezone.utc)


def _is_absolute_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _reject_sensitive_text(value: str, forbidden_values: tuple[str, ...], *, label: str) -> None:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise TelemetryValidationError(f"{label} contains control characters")
    if _is_absolute_path(value):
        raise TelemetryValidationError(f"{label} cannot contain an absolute path")
    if _CREDENTIAL_TEXT.search(value) or _CREDENTIAL_PREFIX.search(value):
        raise TelemetryValidationError(f"{label} cannot contain credential-shaped text")
    if any(value == secret or (len(secret) >= 8 and secret in value) for secret in forbidden_values):
        raise TelemetryValidationError(f"{label} cannot contain configured secret values")


def _validate_opaque(value: str, *, label: str, forbidden_values: tuple[str, ...]) -> str:
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        raise TelemetryValidationError(f"{label} must be a bounded opaque identifier")
    _reject_sensitive_text(value, forbidden_values, label=label)
    return value


def _canonical_metadata(
    value: Mapping[str, object] | None,
    forbidden_values: tuple[str, ...],
) -> str:
    metadata = {} if value is None else dict(value)
    unsupported = sorted(set(metadata) - _ALLOWED_METADATA)
    if unsupported:
        raise TelemetryValidationError("telemetry metadata contains unsupported fields")
    for key, item in metadata.items():
        if key == "http_method":
            if item not in {"GET", "POST"}:
                raise TelemetryValidationError("telemetry HTTP method is unsupported")
        elif key in {"streaming", "decomposed"}:
            if not isinstance(item, bool):
                raise TelemetryValidationError(f"telemetry metadata {key} must be boolean")
        elif key == "status_code":
            if isinstance(item, bool) or not isinstance(item, int) or not 100 <= item <= 599:
                raise TelemetryValidationError("telemetry status code is invalid")
        if isinstance(item, str):
            _reject_sensitive_text(item, forbidden_values, label=f"telemetry metadata {key}")
    try:
        encoded = json.dumps(
            metadata,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise TelemetryValidationError("telemetry metadata must be finite JSON") from error
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        raise TelemetryValidationError("telemetry metadata exceeds its UTF-8 byte limit")
    return encoded


def _decode_metadata(raw: object) -> dict[str, object]:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_METADATA_BYTES:
        raise TelemetryDataError("persisted telemetry metadata is malformed")
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as error:
        raise TelemetryDataError("persisted telemetry metadata is malformed") from error
    if not isinstance(value, dict) or set(value) - _ALLOWED_METADATA:
        raise TelemetryDataError("persisted telemetry metadata is malformed")
    return cast(dict[str, object], value)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 3)
    result = ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])
    return round(result, 3)


def _severity_for_job(state: str, failure_code: str | None) -> TelemetrySeverity:
    if state == "failed" and failure_code != "budget_exhausted":
        return "error"
    if state == "interrupted" or failure_code == "budget_exhausted":
        return "warning"
    return "info"


def _encode_cursor(occurred_at: str, record_id: str) -> str:
    payload = json.dumps([occurred_at, record_id], separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or not value or len(value) > MAX_CURSOR_CHARS:
        raise TelemetryValidationError("log cursor is invalid")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        decoded = json.loads(raw)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TelemetryValidationError("log cursor is invalid") from error
    if not isinstance(decoded, list) or len(decoded) != 2 or not all(isinstance(item, str) for item in decoded):
        raise TelemetryValidationError("log cursor is invalid")
    occurred_at, record_id = decoded
    _parse_utc(occurred_at, label="log cursor timestamp")
    if not _OPAQUE_ID.fullmatch(record_id):
        raise TelemetryValidationError("log cursor identity is invalid")
    return occurred_at, record_id


class SQLiteTelemetryRepository:
    """Single SQLite authority for immutable content-free terminal request facts."""

    def __init__(
        self,
        database: WorkspaceDatabase,
        *,
        clock: Callable[[], str] = utc_timestamp,
        id_factory: Callable[[], str] | None = None,
        forbidden_secret_values: Iterable[str] | None = None,
    ) -> None:
        self.database = database
        self._clock = clock
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        configured = _configured_secret_values(settings) if forbidden_secret_values is None else tuple(forbidden_secret_values)
        self._forbidden_secret_values = tuple(value for value in configured if value)

    @classmethod
    def from_settings(cls, configured: Settings, **kwargs: object) -> "SQLiteTelemetryRepository":
        database = WorkspaceDatabase.from_settings(configured)
        database.initialize()
        if "forbidden_secret_values" not in kwargs:
            kwargs["forbidden_secret_values"] = _configured_secret_values(configured)
        return cls(database, **kwargs)

    def now(self) -> datetime:
        return _parse_utc(self._clock(), label="telemetry clock")

    def new_record_id(self) -> str:
        value = f"tel_{self._id_factory()}"
        if not _TELEMETRY_ID.fullmatch(value):
            raise TelemetryValidationError("telemetry ID factory returned an invalid identity")
        return value

    def _record_from_row(self, row: sqlite3.Row) -> TerminalTelemetryRecord:
        if row["record_schema_version"] != TELEMETRY_RECORD_SCHEMA_VERSION:
            raise TelemetryDataError("persisted telemetry schema version is unsupported")
        subsystem = str(row["subsystem"])
        severity = str(row["severity"])
        outcome = str(row["status"])
        if subsystem not in _SUBSYSTEMS or severity not in _SEVERITIES or outcome not in _OUTCOMES:
            raise TelemetryDataError("persisted telemetry enum is invalid")
        route_template = str(row["route_template"])
        profile = telemetry_route_profile(route_template)
        if profile is None or profile != (subsystem, str(row["capability"])):
            raise TelemetryDataError("persisted telemetry source binding is invalid")
        telemetry_id = str(row["telemetry_id"])
        correlation_id = str(row["correlation_id"])
        try:
            if not _TELEMETRY_ID.fullmatch(telemetry_id):
                raise TelemetryValidationError("telemetry ID is invalid")
            _validate_opaque(
                correlation_id,
                label="telemetry correlation ID",
                forbidden_values=self._forbidden_secret_values,
            )
            occurred = _parse_utc(str(row["occurred_at"]), label="telemetry occurrence")
            retained = _parse_utc(str(row["retention_until"]), label="telemetry retention")
            if retained != occurred + timedelta(days=TELEMETRY_RETENTION_DAYS):
                raise TelemetryValidationError("telemetry retention boundary is invalid")
        except TelemetryValidationError as error:
            raise TelemetryDataError("persisted telemetry identity or time is invalid") from error
        duration = float(row["duration_ms"]) if row["duration_ms"] is not None else None
        if duration is not None and (not math.isfinite(duration) or not 0 <= duration <= MAX_DURATION_MS):
            raise TelemetryDataError("persisted telemetry duration is invalid")
        error_code = str(row["error_code"]) if row["error_code"] is not None else None
        if error_code is not None and not _SAFE_CODE.fullmatch(error_code):
            raise TelemetryDataError("persisted telemetry error code is invalid")
        return TerminalTelemetryRecord(
            telemetry_id=telemetry_id,
            event_kind="request_terminal",
            subsystem=cast(TelemetrySubsystem, subsystem),
            severity=cast(TelemetrySeverity, severity),
            outcome=cast(TelemetryOutcome, outcome),
            route_template=route_template,
            capability=str(row["capability"]),
            correlation_id=correlation_id,
            duration_ms=duration,
            error_code=error_code,
            metadata=_decode_metadata(row["metadata_json"]),
            occurred_at=str(row["occurred_at"]),
            retention_until=str(row["retention_until"]),
        )

    def prune_expired(self, *, now: datetime | None = None) -> int:
        current = now or self.now()
        with self.database.transaction(write=True) as connection:
            cursor = connection.execute(
                "DELETE FROM telemetry_events WHERE retention_until <= ?",
                (_format_utc(current),),
            )
        return max(cursor.rowcount, 0)

    def record_request_terminal(
        self,
        *,
        telemetry_id: str,
        subsystem: TelemetrySubsystem,
        route_template: str,
        capability: str,
        severity: TelemetrySeverity,
        outcome: TelemetryOutcome,
        correlation_id: str,
        duration_ms: float | None,
        error_code: str | None,
        metadata: Mapping[str, object] | None = None,
        occurred_at: str | None = None,
    ) -> TerminalTelemetryRecord:
        if not isinstance(telemetry_id, str) or not _TELEMETRY_ID.fullmatch(telemetry_id):
            raise TelemetryValidationError("telemetry ID must be a server terminal identity")
        profile = telemetry_route_profile(route_template)
        if profile is None or profile != (subsystem, capability):
            raise TelemetryValidationError("telemetry route/source binding is unsupported")
        if severity not in _SEVERITIES or outcome not in _OUTCOMES:
            raise TelemetryValidationError("telemetry severity or outcome is unsupported")
        _validate_opaque(
            correlation_id,
            label="telemetry correlation ID",
            forbidden_values=self._forbidden_secret_values,
        )
        if duration_ms is not None and (
            isinstance(duration_ms, bool)
            or not isinstance(duration_ms, (int, float))
            or not math.isfinite(float(duration_ms))
            or not 0 <= float(duration_ms) <= MAX_DURATION_MS
        ):
            raise TelemetryValidationError("telemetry duration is outside its measured bound")
        if error_code is not None:
            if not isinstance(error_code, str) or not _SAFE_CODE.fullmatch(error_code):
                raise TelemetryValidationError("telemetry error code is invalid")
            _reject_sensitive_text(error_code, self._forbidden_secret_values, label="telemetry error code")
        metadata_json = _canonical_metadata(metadata, self._forbidden_secret_values)
        terminal_time = self.now() if occurred_at is None else _parse_utc(occurred_at, label="telemetry occurrence")
        retained_until = terminal_time + timedelta(days=TELEMETRY_RETENTION_DAYS)
        values = (
            telemetry_id,
            "request_terminal",
            route_template,
            capability,
            outcome,
            round(float(duration_ms), 3) if duration_ms is not None else None,
            _format_utc(terminal_time),
            _format_utc(retained_until),
            TELEMETRY_RECORD_SCHEMA_VERSION,
            subsystem,
            severity,
            correlation_id,
            None,
            error_code,
            metadata_json,
        )
        with self.database.transaction(write=True) as connection:
            connection.execute(
                "DELETE FROM telemetry_events WHERE retention_until <= ?",
                (_format_utc(terminal_time),),
            )
            cursor = connection.execute(
                "INSERT OR IGNORE INTO telemetry_events("
                "telemetry_id, event_name, route_template, capability, status, duration_ms, "
                "occurred_at, retention_until, record_schema_version, subsystem, severity, "
                "correlation_id, domain_id, error_code, metadata_json"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values,
            )
            row = connection.execute(
                "SELECT * FROM telemetry_events WHERE telemetry_id = ?",
                (telemetry_id,),
            ).fetchone()
        if row is None:
            raise TelemetryDataError("terminal telemetry insert did not produce a record")
        record = self._record_from_row(row)
        expected = TerminalTelemetryRecord(
            telemetry_id=telemetry_id,
            event_kind="request_terminal",
            subsystem=subsystem,
            severity=severity,
            outcome=outcome,
            route_template=route_template,
            capability=capability,
            correlation_id=correlation_id,
            duration_ms=round(float(duration_ms), 3) if duration_ms is not None else None,
            error_code=error_code,
            metadata=json.loads(metadata_json),
            occurred_at=_format_utc(terminal_time),
            retention_until=_format_utc(retained_until),
        )
        if cursor.rowcount == 0 and record != expected:
            raise TelemetryConflictError("terminal telemetry identity is immutable")
        return record

    def request_records(self, *, started_at: datetime, ended_at: datetime) -> tuple[TerminalTelemetryRecord, ...]:
        if ended_at <= started_at or ended_at - started_at > timedelta(days=TELEMETRY_RETENTION_DAYS):
            raise TelemetryValidationError("telemetry query window is invalid")
        self.prune_expired(now=ended_at)
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM telemetry_events WHERE event_name = 'request_terminal' "
                "AND occurred_at >= ? AND occurred_at < ? AND retention_until > ? "
                "ORDER BY occurred_at, telemetry_id",
                (_format_utc(started_at), _format_utc(ended_at), _format_utc(ended_at)),
            ).fetchall()
        return tuple(self._record_from_row(row) for row in rows)

    def terminal_jobs(self, *, started_at: datetime, ended_at: datetime) -> tuple[OperationalLogRecord, ...]:
        if ended_at <= started_at or ended_at - started_at > timedelta(days=TELEMETRY_RETENTION_DAYS):
            raise TelemetryValidationError("terminal job query window is invalid")
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT job_id, namespace, state, revision, failure_code, finished_at "
                "FROM jobs WHERE state IN ('cancelled', 'succeeded', 'failed', 'interrupted') "
                "AND finished_at IS NOT NULL AND finished_at >= ? AND finished_at < ? "
                "ORDER BY finished_at, job_id",
                (_format_utc(started_at), _format_utc(ended_at)),
            ).fetchall()
        records: list[OperationalLogRecord] = []
        for row in rows:
            job_id = str(row["job_id"])
            namespace = str(row["namespace"])
            state = str(row["state"])
            failure_code = str(row["failure_code"]) if row["failure_code"] is not None else None
            if (
                not _OPAQUE_ID.fullmatch(job_id)
                or namespace not in _JOB_NAMESPACES
                or state not in _TERMINAL_JOB_STATES
                or (failure_code is not None and not _SAFE_CODE.fullmatch(failure_code))
            ):
                raise TelemetryDataError("persisted terminal job projection is invalid")
            revision = int(row["revision"])
            records.append(
                OperationalLogRecord(
                    record_id=f"job:{job_id}:{revision}",
                    occurred_at=str(row["finished_at"]),
                    category="job",
                    level=_severity_for_job(state, failure_code),
                    kind="job_terminal",
                    subsystem=namespace,
                    outcome=state,
                    correlation_id=job_id,
                    domain_id=job_id,
                    route_template=None,
                    error_code=failure_code,
                    duration_ms=None,
                    metadata={},
                )
            )
        return tuple(records)

    def request_log_candidates(
        self,
        *,
        started_at: datetime,
        ended_at: datetime,
        level: TelemetrySeverity | None,
        cursor: tuple[str, str] | None,
        limit: int,
    ) -> tuple[OperationalLogRecord, ...]:
        """Read only one bounded request-log candidate page in final sort order."""
        if not 1 <= limit <= MAX_LOG_LIMIT + 1:
            raise TelemetryValidationError("log candidate limit is out of bounds")
        self.prune_expired(now=ended_at)
        clauses = [
            "event_name = 'request_terminal'",
            "occurred_at >= ?",
            "occurred_at < ?",
            "retention_until > ?",
        ]
        values: list[object] = [
            _format_utc(started_at),
            _format_utc(ended_at),
            _format_utc(ended_at),
        ]
        if level is not None:
            clauses.append("severity = ?")
            values.append(level)
        if cursor is not None:
            clauses.append("(occurred_at < ? OR (occurred_at = ? AND telemetry_id < ?))")
            values.extend((cursor[0], cursor[0], cursor[1]))
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM telemetry_events WHERE "
                + " AND ".join(clauses)
                + " ORDER BY occurred_at DESC, telemetry_id DESC LIMIT ?",
                (*values, limit),
            ).fetchall()
        return tuple(
            OperationalLogRecord(
                record_id=record.telemetry_id,
                occurred_at=record.occurred_at,
                category="request",
                level=record.severity,
                kind=record.event_kind,
                subsystem=record.subsystem,
                outcome=record.outcome,
                correlation_id=record.correlation_id,
                domain_id=None,
                route_template=record.route_template,
                error_code=record.error_code,
                duration_ms=record.duration_ms,
                metadata=record.metadata,
            )
            for record in (self._record_from_row(row) for row in rows)
        )

    def job_log_candidates(
        self,
        *,
        started_at: datetime,
        ended_at: datetime,
        level: TelemetrySeverity | None,
        cursor: tuple[str, str] | None,
        limit: int,
    ) -> tuple[OperationalLogRecord, ...]:
        """Read one bounded DATA-004 terminal-job projection page."""
        if not 1 <= limit <= MAX_LOG_LIMIT + 1:
            raise TelemetryValidationError("log candidate limit is out of bounds")
        severity_sql = (
            "CASE WHEN state = 'failed' AND COALESCE(failure_code, '') != 'budget_exhausted' "
            "THEN 'error' WHEN state = 'interrupted' OR failure_code = 'budget_exhausted' "
            "THEN 'warning' ELSE 'info' END"
        )
        record_id_sql = "('job:' || job_id || ':' || revision)"
        clauses = [
            "state IN ('cancelled', 'succeeded', 'failed', 'interrupted')",
            "finished_at IS NOT NULL",
            "finished_at >= ?",
            "finished_at < ?",
        ]
        values: list[object] = [_format_utc(started_at), _format_utc(ended_at)]
        if level is not None:
            clauses.append(f"{severity_sql} = ?")
            values.append(level)
        if cursor is not None:
            clauses.append(f"(finished_at < ? OR (finished_at = ? AND {record_id_sql} < ?))")
            values.extend((cursor[0], cursor[0], cursor[1]))
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT job_id, namespace, state, revision, failure_code, finished_at FROM jobs WHERE "
                + " AND ".join(clauses)
                + f" ORDER BY finished_at DESC, {record_id_sql} DESC LIMIT ?",
                (*values, limit),
            ).fetchall()
        records: list[OperationalLogRecord] = []
        for row in rows:
            job_id = str(row["job_id"])
            namespace = str(row["namespace"])
            state = str(row["state"])
            failure_code = str(row["failure_code"]) if row["failure_code"] is not None else None
            if (
                not _OPAQUE_ID.fullmatch(job_id)
                or namespace not in _JOB_NAMESPACES
                or state not in _TERMINAL_JOB_STATES
                or (failure_code is not None and not _SAFE_CODE.fullmatch(failure_code))
            ):
                raise TelemetryDataError("persisted terminal job projection is invalid")
            revision = int(row["revision"])
            records.append(
                OperationalLogRecord(
                    record_id=f"job:{job_id}:{revision}",
                    occurred_at=str(row["finished_at"]),
                    category="job",
                    level=_severity_for_job(state, failure_code),
                    kind="job_terminal",
                    subsystem=namespace,
                    outcome=state,
                    correlation_id=job_id,
                    domain_id=job_id,
                    route_template=None,
                    error_code=failure_code,
                    duration_ms=None,
                    metadata={},
                )
            )
        return tuple(records)


class TelemetryService:
    """Bounded aggregates and sanitized log views for the later UI-012 consumer."""

    _RANGES = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
    _INTERVALS = {"hour": timedelta(hours=1), "day": timedelta(days=1)}

    def __init__(self, repository: SQLiteTelemetryRepository) -> None:
        self.repository = repository

    def _bounds(self, range_name: AnalyticsRange) -> tuple[datetime, datetime]:
        if range_name not in self._RANGES:
            raise TelemetryValidationError("analytics range is unsupported")
        ended_at = self.repository.now()
        return ended_at - self._RANGES[range_name], ended_at

    def summary(self, range_name: AnalyticsRange) -> dict[str, object]:
        started_at, ended_at = self._bounds(range_name)
        requests = self.repository.request_records(started_at=started_at, ended_at=ended_at)
        jobs = self.repository.terminal_jobs(started_at=started_at, ended_at=ended_at)
        outcomes = {name: 0 for name in ("succeeded", "rejected", "failed", "cancelled", "interrupted")}
        durations: list[float] = []
        for record in requests:
            outcomes[record.outcome] += 1
            if record.duration_ms is not None:
                durations.append(record.duration_ms)
        total = len(requests)
        job_outcomes = {name: 0 for name in ("succeeded", "failed", "cancelled", "interrupted")}
        job_namespaces = {name: 0 for name in ("pipeline", "evaluation", "model_test")}
        for record in jobs:
            job_outcomes[record.outcome] += 1
            job_namespaces[record.subsystem] += 1
        return {
            "range": range_name,
            "started_at": _format_utc(started_at),
            "ended_at": _format_utc(ended_at),
            "requests": {
                "terminal_count": total,
                "outcomes": outcomes,
                "success_rate": {
                    "value": round(outcomes["succeeded"] / total, 6) if total else None,
                    "numerator": outcomes["succeeded"],
                    "denominator": total,
                },
                "failure_rate": {
                    "value": round(outcomes["failed"] / total, 6) if total else None,
                    "numerator": outcomes["failed"],
                    "denominator": total,
                },
                "duration_ms": {
                    "known_count": len(durations),
                    "unknown_count": total - len(durations),
                    "p50": _percentile(durations, 0.50),
                    "p95": _percentile(durations, 0.95),
                },
            },
            "terminal_jobs": {
                "terminal_count": len(jobs),
                "by_namespace": job_namespaces,
                "by_outcome": job_outcomes,
            },
        }

    def timeseries(
        self,
        range_name: AnalyticsRange,
        interval: AnalyticsInterval,
        metric: AnalyticsMetric,
    ) -> dict[str, object]:
        if interval not in self._INTERVALS:
            raise TelemetryValidationError("analytics interval is unsupported")
        started_at, ended_at = self._bounds(range_name)
        width = self._INTERVALS[interval]
        bucket_count = math.ceil((ended_at - started_at) / width)
        if bucket_count > MAX_TIMESERIES_BUCKETS:
            raise TelemetryValidationError("analytics range and interval exceed the bucket bound")
        requests = self.repository.request_records(started_at=started_at, ended_at=ended_at)
        jobs = self.repository.terminal_jobs(started_at=started_at, ended_at=ended_at)
        request_buckets: list[list[TerminalTelemetryRecord]] = [[] for _ in range(bucket_count)]
        job_buckets: list[list[OperationalLogRecord]] = [[] for _ in range(bucket_count)]
        for record in requests:
            index = int((_parse_utc(record.occurred_at, label="telemetry occurrence") - started_at) // width)
            if 0 <= index < bucket_count:
                request_buckets[index].append(record)
        for record in jobs:
            index = int((_parse_utc(record.occurred_at, label="job completion") - started_at) // width)
            if 0 <= index < bucket_count:
                job_buckets[index].append(record)
        points: list[TimeSeriesPoint] = []
        for index in range(bucket_count):
            bucket_start = started_at + index * width
            bucket_end = min(bucket_start + width, ended_at)
            request_items = request_buckets[index]
            job_items = job_buckets[index]
            if metric == "request_count":
                value: float | int | None = len(request_items)
                denominator = len(request_items)
            elif metric == "request_failure_count":
                value = sum(item.outcome == "failed" for item in request_items)
                denominator = len(request_items)
            elif metric in {"request_duration_p50_ms", "request_duration_p95_ms"}:
                measured = [item.duration_ms for item in request_items if item.duration_ms is not None]
                value = _percentile(cast(list[float], measured), 0.50 if metric.endswith("p50_ms") else 0.95)
                denominator = len(measured)
            else:
                value = len(job_items)
                denominator = len(job_items)
            points.append(
                TimeSeriesPoint(
                    started_at=_format_utc(bucket_start),
                    ended_at=_format_utc(bucket_end),
                    value=value,
                    denominator=denominator,
                )
            )
        return {
            "range": range_name,
            "interval": interval,
            "metric": metric,
            "unit": "milliseconds" if "duration" in metric else "count",
            "started_at": _format_utc(started_at),
            "ended_at": _format_utc(ended_at),
            "points": [point.__dict__ for point in points],
        }

    def logs(
        self,
        *,
        category: LogCategory | None = None,
        level: TelemetrySeverity | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> OperationalLogPage:
        if category is not None and category not in {"request", "job"}:
            raise TelemetryValidationError("log category is unsupported")
        if level is not None and level not in _SEVERITIES:
            raise TelemetryValidationError("log level is unsupported")
        if isinstance(limit, bool) or not 1 <= limit <= MAX_LOG_LIMIT:
            raise TelemetryValidationError("log limit is out of bounds")
        cursor_value = _decode_cursor(cursor) if cursor is not None else None
        ended_at = self.repository.now()
        started_at = ended_at - timedelta(days=LOG_RETENTION_DAYS)
        combined: list[OperationalLogRecord] = []
        if category in {None, "request"}:
            combined.extend(
                self.repository.request_log_candidates(
                    started_at=started_at,
                    ended_at=ended_at,
                    level=level,
                    cursor=cursor_value,
                    limit=limit + 1,
                )
            )
        if category in {None, "job"}:
            combined.extend(
                self.repository.job_log_candidates(
                    started_at=started_at,
                    ended_at=ended_at,
                    level=level,
                    cursor=cursor_value,
                    limit=limit + 1,
                )
            )
        combined.sort(key=lambda record: (record.occurred_at, record.record_id), reverse=True)
        has_more = len(combined) > limit
        items = tuple(combined[:limit])
        next_cursor = _encode_cursor(items[-1].occurred_at, items[-1].record_id) if has_more and items else None
        return OperationalLogPage(items=items, next_cursor=next_cursor, has_more=has_more, limit=limit)
