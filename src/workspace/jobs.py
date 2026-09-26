"""Durable, revisioned job state for later pipeline and evaluation workers.

This module owns persistence and state-machine truth only.  It deliberately
does not start threads, claim leases, execute providers, or expose HTTP routes.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Callable, Iterable, Literal, Mapping, Sequence, cast

from configs.settings import Settings, settings
from src.workspace.database import WorkspaceDatabase
from src.workspace.repository import utc_timestamp


JobNamespace = Literal["pipeline", "evaluation", "model_test"]
JobState = Literal[
    "queued",
    "running",
    "cancelling",
    "cancelled",
    "succeeded",
    "failed",
    "interrupted",
]
JobStepState = Literal[
    "pending",
    "running",
    "cancelled",
    "succeeded",
    "failed",
    "skipped",
    "interrupted",
]

JOB_NAMESPACES = frozenset({"pipeline", "evaluation", "model_test"})
JOB_STATES = frozenset(
    {"queued", "running", "cancelling", "cancelled", "succeeded", "failed", "interrupted"}
)
TERMINAL_JOB_STATES = frozenset({"cancelled", "succeeded", "failed", "interrupted"})
JOB_STEP_STATES = frozenset(
    {"pending", "running", "cancelled", "succeeded", "failed", "skipped", "interrupted"}
)
TERMINAL_STEP_STATES = frozenset({"cancelled", "succeeded", "failed", "skipped", "interrupted"})

MAX_JOB_PAYLOAD_BYTES = 64 * 1024
MAX_JOB_RESULT_BYTES = 256 * 1024
MAX_JOB_STEPS = 64
MAX_ARTIFACT_REFERENCES = 128
MAX_FAILURE_MESSAGE_CHARS = 2048
MAX_LIST_LIMIT = 100
JOB_RECORD_SCHEMA_VERSION = 1

_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_TYPE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_FINGERPRINT = re.compile(r"^[a-f0-9]{64}$")
_FAILURE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ARTIFACT_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "bearer_token",
        "credential",
        "credentials",
        "groq_api_key",
        "local_workspace_token",
        "password",
        "provider_credential",
        "provider_key",
        "secret",
        "token",
    }
)
_COMPACT_FORBIDDEN_KEYS = frozenset(item.replace("_", "") for item in _FORBIDDEN_KEYS)
_CREDENTIAL_TEXT = re.compile(
    r"(?:authorization|bearer|api[ _-]?key|password|secret|token)\s*[:=]",
    re.IGNORECASE,
)

_JOB_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"running", "cancelled"}),
    "running": frozenset({"cancelling", "succeeded", "failed", "interrupted"}),
    "cancelling": frozenset({"cancelled", "interrupted"}),
    "cancelled": frozenset(),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "interrupted": frozenset(),
}
_STEP_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"running", "cancelled", "skipped"}),
    "running": frozenset({"cancelled", "succeeded", "failed", "interrupted"}),
    "cancelled": frozenset(),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "skipped": frozenset(),
    "interrupted": frozenset(),
}


class JobError(RuntimeError):
    """Base error for durable job operations."""


class JobConflictError(JobError):
    """A revision or idempotency precondition did not match."""


class JobNotFoundError(JobError):
    """The requested durable job or step does not exist."""


class JobTransitionError(JobError):
    """The requested state transition is not legal."""


class JobDataError(JobError):
    """Persisted job data is legacy, malformed, or otherwise unsafe."""


class JobLimitError(JobError):
    """A bounded job field or query exceeded its contract."""


@dataclass(frozen=True)
class JobProgress:
    stage: str | None
    current: int | None
    total: int | None


@dataclass(frozen=True)
class JobStep:
    step_id: str
    job_id: str
    ordinal: int
    name: str
    state: JobStepState
    revision: int
    started_at: str | None
    finished_at: str | None


@dataclass(frozen=True)
class DurableJob:
    job_id: str
    namespace: JobNamespace
    job_type: str
    state: JobState
    revision: int
    configuration_fingerprint: str
    payload: dict[str, object]
    artifact_references: tuple[str, ...]
    progress: JobProgress
    result: dict[str, object] | None
    failure_code: str | None
    failure_message: str | None
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None
    cancellation_requested_at: str | None
    steps: tuple[JobStep, ...]


@dataclass(frozen=True)
class JobEvent:
    event_id: str
    job_id: str
    sequence: int
    event_type: str
    state: JobState | None
    reason_code: str | None
    progress: JobProgress
    occurred_at: str


@dataclass(frozen=True)
class JobPage:
    items: tuple[DurableJob, ...]
    total: int
    limit: int
    offset: int


FailureInjector = Callable[[str, str], None]


def validate_job_transition(current: str, target: str) -> None:
    if current not in JOB_STATES or target not in JOB_STATES:
        raise JobTransitionError("unknown durable job state")
    if target not in _JOB_TRANSITIONS[current]:
        raise JobTransitionError(f"job transition {current}->{target} is not allowed")


def validate_step_transition(current: str, target: str) -> None:
    if current not in JOB_STEP_STATES or target not in JOB_STEP_STATES:
        raise JobTransitionError("unknown durable job step state")
    if target not in _STEP_TRANSITIONS[current]:
        raise JobTransitionError(f"job step transition {current}->{target} is not allowed")


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


def _normal_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _looks_absolute_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _validate_safe_tree(value: object, forbidden_values: tuple[str, ...]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("job JSON object keys must be strings")
            normalized = _normal_key(key)
            compact = normalized.replace("_", "")
            if (
                normalized in _FORBIDDEN_KEYS
                or compact in _COMPACT_FORBIDDEN_KEYS
                or normalized.endswith("_api_key")
                or normalized.endswith("_password")
                or normalized.endswith("_secret")
                or normalized.endswith("_token")
                or compact.endswith(("apikey", "credential", "password", "secret", "token"))
            ):
                raise ValueError("job data cannot persist credential fields")
            _validate_safe_tree(child, forbidden_values)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            _validate_safe_tree(child, forbidden_values)
        return
    if isinstance(value, str):
        if _looks_absolute_path(value):
            raise ValueError("job data cannot persist absolute filesystem paths")
        if _CREDENTIAL_TEXT.search(value) or any(
            value == secret or (len(secret) >= 8 and secret in value)
            for secret in forbidden_values
        ):
            raise ValueError("job data cannot persist credential values")


def _canonical_object(
    value: Mapping[str, object],
    *,
    label: str,
    max_bytes: int,
    forbidden_values: tuple[str, ...],
) -> str:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a JSON object")
    _validate_safe_tree(value, forbidden_values)
    try:
        encoded = json.dumps(
            dict(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be finite JSON") from error
    if len(encoded.encode("utf-8")) > max_bytes:
        raise JobLimitError(f"{label} exceeds its UTF-8 byte limit")
    return encoded


def _decode_object(raw: object, *, label: str, max_bytes: int) -> dict[str, object]:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > max_bytes:
        raise JobDataError(f"persisted {label} is malformed")
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as error:
        raise JobDataError(f"persisted {label} is malformed") from error
    if not isinstance(value, dict):
        raise JobDataError(f"persisted {label} is malformed")
    return value


def _validate_opaque(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        raise ValueError(f"{label} must be an opaque identifier")
    return value


def _validate_name(value: str, *, label: str, pattern: re.Pattern[str] = _TYPE_NAME) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _validate_progress(stage: str | None, current: int | None, total: int | None) -> JobProgress:
    if stage is not None:
        _validate_name(stage, label="progress stage")
    if (current is None) != (total is None):
        raise ValueError("progress current and total must both be known or both be unknown")
    if current is not None and total is not None:
        if isinstance(current, bool) or isinstance(total, bool) or total < 1 or current < 0 or current > total:
            raise ValueError("progress counts must satisfy 0 <= current <= total")
    return JobProgress(stage=stage, current=current, total=total)


def _validate_failure(
    code: str | None,
    message: str | None,
    forbidden_values: tuple[str, ...],
) -> tuple[str, str]:
    if code is None or message is None:
        raise ValueError("failed or interrupted jobs require a safe failure code and message")
    _validate_name(code, label="failure code", pattern=_FAILURE_CODE)
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_FAILURE_MESSAGE_CHARS:
        raise JobLimitError("failure message is empty or exceeds its character limit")
    if any(ord(character) < 32 and character not in "\t" for character in message):
        raise ValueError("failure message contains control characters")
    _validate_safe_tree(message, forbidden_values)
    return code, message


class SQLiteJobRepository:
    """One authoritative SQLite owner for durable job state and ordered events."""

    def __init__(
        self,
        database: WorkspaceDatabase,
        *,
        clock: Callable[[], str] = utc_timestamp,
        id_factory: Callable[[], str] | None = None,
        failure_injector: FailureInjector | None = None,
        forbidden_secret_values: Iterable[str] | None = None,
    ) -> None:
        self.database = database
        self._clock = clock
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self._failure_injector = failure_injector
        values = _configured_secret_values() if forbidden_secret_values is None else tuple(forbidden_secret_values)
        self._forbidden_secret_values = tuple(value for value in values if value)

    @classmethod
    def from_settings(cls, configured: Settings, **kwargs: Any) -> "SQLiteJobRepository":
        database = WorkspaceDatabase.from_settings(configured)
        database.initialize()
        return cls(database, **kwargs)

    def _new_id(self, prefix: str) -> str:
        suffix = self._id_factory()
        return _validate_opaque(f"{prefix}_{suffix}", label=f"{prefix} ID")

    def _inject(self, phase: str, job_id: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(phase, job_id)

    @staticmethod
    def _assert_revision(actual: int, expected: int) -> None:
        if isinstance(expected, bool) or expected < 1:
            raise ValueError("expected revision must be a positive integer")
        if actual != expected:
            raise JobConflictError("durable job revision conflict")

    def _steps_in(self, connection: sqlite3.Connection, job_id: str) -> tuple[JobStep, ...]:
        rows = connection.execute(
            "SELECT step_id, job_id, ordinal, step_name, state, revision, started_at, finished_at "
            "FROM job_steps WHERE job_id = ? ORDER BY ordinal, step_id",
            (job_id,),
        ).fetchall()
        steps: list[JobStep] = []
        for row in rows:
            state = str(row["state"])
            if state not in JOB_STEP_STATES:
                raise JobDataError("persisted job step state is invalid")
            step_id = str(row["step_id"])
            step_name = str(row["step_name"])
            ordinal = int(row["ordinal"])
            revision = int(row["revision"])
            try:
                _validate_opaque(step_id, label="step ID")
                _validate_name(step_name, label="job step name")
            except ValueError as error:
                raise JobDataError("persisted job step identity or name is invalid") from error
            if ordinal != len(steps) or revision < 1:
                raise JobDataError("persisted job step ordering or revision is invalid")
            steps.append(
                JobStep(
                    step_id=step_id,
                    job_id=str(row["job_id"]),
                    ordinal=ordinal,
                    name=step_name,
                    state=cast(JobStepState, state),
                    revision=revision,
                    started_at=str(row["started_at"]) if row["started_at"] is not None else None,
                    finished_at=str(row["finished_at"]) if row["finished_at"] is not None else None,
                )
            )
        return tuple(steps)

    def _job_from_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> DurableJob:
        if row["record_schema_version"] != JOB_RECORD_SCHEMA_VERSION:
            raise JobDataError("legacy job row is not compatible with DATA-004")
        state = str(row["state"])
        namespace = str(row["namespace"])
        if state not in JOB_STATES or namespace not in JOB_NAMESPACES:
            raise JobDataError("persisted job state or namespace is invalid")
        job_id = str(row["job_id"])
        job_type = str(row["job_type"])
        fingerprint = str(row["configuration_fingerprint"])
        try:
            _validate_opaque(job_id, label="job ID")
            _validate_name(job_type, label="job type")
        except ValueError as error:
            raise JobDataError("persisted job identity or type is invalid") from error
        if not _FINGERPRINT.fullmatch(fingerprint):
            raise JobDataError("persisted configuration fingerprint is invalid")
        if int(row["revision"]) < 1:
            raise JobDataError("persisted job revision is invalid")
        payload = _decode_object(row["payload_json"], label="job payload", max_bytes=MAX_JOB_PAYLOAD_BYTES)
        try:
            artifacts = json.loads(str(row["artifact_references_json"]))
        except (TypeError, ValueError) as error:
            raise JobDataError("persisted artifact references are malformed") from error
        if (
            not isinstance(artifacts, list)
            or len(artifacts) > MAX_ARTIFACT_REFERENCES
            or any(not isinstance(item, str) or not _ARTIFACT_REFERENCE.fullmatch(item) for item in artifacts)
            or len(set(artifacts)) != len(artifacts)
        ):
            raise JobDataError("persisted artifact references are malformed")
        result = None
        if row["result_json"] is not None:
            result = _decode_object(row["result_json"], label="job result", max_bytes=MAX_JOB_RESULT_BYTES)
        try:
            progress = _validate_progress(
                str(row["progress_stage"]) if row["progress_stage"] is not None else None,
                int(row["progress_current"]) if row["progress_current"] is not None else None,
                int(row["progress_total"]) if row["progress_total"] is not None else None,
            )
            _validate_safe_tree(payload, self._forbidden_secret_values)
            _validate_safe_tree(result, self._forbidden_secret_values)
            if row["failure_code"] is not None or row["failure_message"] is not None:
                _validate_failure(
                    str(row["failure_code"]) if row["failure_code"] is not None else None,
                    str(row["failure_message"]) if row["failure_message"] is not None else None,
                    self._forbidden_secret_values,
                )
        except (JobLimitError, ValueError) as error:
            raise JobDataError("persisted job data violates the durable contract") from error
        if state == "succeeded" and result is None:
            raise JobDataError("persisted successful job has no result")
        if state in {"failed", "interrupted"} and (
            row["failure_code"] is None or row["failure_message"] is None
        ):
            raise JobDataError("persisted failed job has no safe failure detail")
        return DurableJob(
            job_id=job_id,
            namespace=cast(JobNamespace, namespace),
            job_type=job_type,
            state=cast(JobState, state),
            revision=int(row["revision"]),
            configuration_fingerprint=fingerprint,
            payload=payload,
            artifact_references=tuple(artifacts),
            progress=progress,
            result=result,
            failure_code=str(row["failure_code"]) if row["failure_code"] is not None else None,
            failure_message=str(row["failure_message"]) if row["failure_message"] is not None else None,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            started_at=str(row["started_at"]) if row["started_at"] is not None else None,
            finished_at=str(row["finished_at"]) if row["finished_at"] is not None else None,
            cancellation_requested_at=(
                str(row["cancellation_requested_at"])
                if row["cancellation_requested_at"] is not None
                else None
            ),
            steps=self._steps_in(connection, str(row["job_id"])),
        )

    def _job_in(self, connection: sqlite3.Connection, job_id: str) -> DurableJob:
        _validate_opaque(job_id, label="job ID")
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise JobNotFoundError("durable job does not exist")
        return self._job_from_row(connection, row)

    def get_job(self, job_id: str) -> DurableJob:
        with self.database.connection() as connection:
            return self._job_in(connection, job_id)

    def find_idempotent_job(self, namespace: JobNamespace, idempotency_key: str) -> DurableJob | None:
        """Read the existing DATA-004 identity before consulting mutable inputs."""
        if namespace not in JOB_NAMESPACES:
            raise ValueError("unsupported job namespace")
        if (not isinstance(idempotency_key, str) or not idempotency_key.strip()
                or len(idempotency_key) > 256
                or any(ord(character) < 33 or ord(character) == 127 for character in idempotency_key)):
            raise ValueError("idempotency key is invalid")
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE namespace = ? AND idempotency_key_hash = ?",
                (namespace, key_hash),
            ).fetchone()
            return self._job_from_row(connection, row) if row is not None else None

    def list_jobs(
        self,
        *,
        namespace: JobNamespace | None = None,
        state: JobState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> JobPage:
        if namespace is not None and namespace not in JOB_NAMESPACES:
            raise ValueError("unsupported job namespace")
        if state is not None and state not in JOB_STATES:
            raise ValueError("unsupported job state")
        if isinstance(limit, bool) or not 1 <= limit <= MAX_LIST_LIMIT:
            raise JobLimitError("job list limit is out of bounds")
        if isinstance(offset, bool) or offset < 0:
            raise ValueError("job list offset must be non-negative")
        clauses: list[str] = []
        values: list[object] = []
        if namespace is not None:
            clauses.append("namespace = ?")
            values.append(namespace)
        if state is not None:
            clauses.append("state = ?")
            values.append(state)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.database.connection() as connection:
            total = int(connection.execute(f"SELECT COUNT(*) FROM jobs{where}", values).fetchone()[0])
            rows = connection.execute(
                f"SELECT * FROM jobs{where} ORDER BY created_at DESC, job_id DESC LIMIT ? OFFSET ?",
                (*values, limit, offset),
            ).fetchall()
            items = tuple(self._job_from_row(connection, row) for row in rows)
        return JobPage(items=items, total=total, limit=limit, offset=offset)

    def create_job(
        self,
        *,
        namespace: JobNamespace,
        job_type: str,
        idempotency_key: str,
        configuration_fingerprint: str,
        payload: Mapping[str, object],
        artifact_references: Sequence[str] = (),
        steps: Sequence[str] = (),
    ) -> DurableJob:
        if namespace not in JOB_NAMESPACES:
            raise ValueError("unsupported job namespace")
        _validate_name(job_type, label="job type")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 256:
            raise ValueError("idempotency key is empty or too long")
        if any(ord(character) < 33 or ord(character) == 127 for character in idempotency_key):
            raise ValueError("idempotency key contains whitespace or control characters")
        if not _FINGERPRINT.fullmatch(configuration_fingerprint):
            raise ValueError("configuration fingerprint must be lowercase SHA-256")
        payload_json = _canonical_object(
            payload,
            label="job payload",
            max_bytes=MAX_JOB_PAYLOAD_BYTES,
            forbidden_values=self._forbidden_secret_values,
        )
        if len(artifact_references) > MAX_ARTIFACT_REFERENCES:
            raise JobLimitError("too many artifact references")
        artifacts = tuple(artifact_references)
        if any(not isinstance(item, str) or not _ARTIFACT_REFERENCE.fullmatch(item) for item in artifacts):
            raise ValueError("artifact references must be portable opaque identifiers")
        if len(set(artifacts)) != len(artifacts):
            raise ValueError("artifact references must be unique")
        if len(steps) > MAX_JOB_STEPS:
            raise JobLimitError("too many job steps")
        step_names = tuple(steps)
        for name in step_names:
            _validate_name(name, label="job step name")
        if len(set(step_names)) != len(step_names):
            raise ValueError("job step names must be unique")
        artifacts_json = json.dumps(artifacts, separators=(",", ":"))
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        timestamp = self._clock()

        with self.database.transaction(write=True) as connection:
            existing = connection.execute(
                "SELECT * FROM jobs WHERE namespace = ? AND idempotency_key_hash = ?",
                (namespace, key_hash),
            ).fetchone()
            if existing is not None:
                stored = self._job_from_row(connection, existing)
                if (
                    stored.job_type == job_type
                    and stored.configuration_fingerprint == configuration_fingerprint
                    and json.dumps(stored.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == payload_json
                    and stored.artifact_references == artifacts
                    and tuple(step.name for step in stored.steps) == step_names
                ):
                    return stored
                raise JobConflictError("idempotency key was already used for a different job request")

            job_id = self._new_id("job")
            try:
                connection.execute(
                    "INSERT INTO jobs(job_id, namespace, job_type, state, configuration_fingerprint, "
                    "artifact_run_id, failure_code, revision, created_at, updated_at, started_at, "
                    "finished_at, record_schema_version, idempotency_key_hash, payload_json, "
                    "artifact_references_json, progress_stage, progress_current, progress_total, "
                    "result_json, failure_message, cancellation_requested_at) "
                    "VALUES (?, ?, ?, 'queued', ?, NULL, NULL, 1, ?, ?, NULL, NULL, ?, ?, ?, ?, "
                    "NULL, NULL, NULL, NULL, NULL, NULL)",
                    (
                        job_id,
                        namespace,
                        job_type,
                        configuration_fingerprint,
                        timestamp,
                        timestamp,
                        JOB_RECORD_SCHEMA_VERSION,
                        key_hash,
                        payload_json,
                        artifacts_json,
                    ),
                )
                for ordinal, name in enumerate(step_names):
                    connection.execute(
                        "INSERT INTO job_steps(step_id, job_id, ordinal, step_name, state, revision, "
                        "started_at, finished_at) VALUES (?, ?, ?, ?, 'pending', 1, NULL, NULL)",
                        (self._new_id("step"), job_id, ordinal, name),
                    )
            except sqlite3.IntegrityError as error:
                raise JobConflictError("durable job identity already exists") from error
            self._append_event_in(
                connection,
                job_id,
                event_type="created",
                state="queued",
                reason_code=None,
                progress=JobProgress(None, None, None),
                timestamp=timestamp,
            )
            self._inject("after_create", job_id)
            return self._job_in(connection, job_id)

    def transition_job(
        self,
        job_id: str,
        *,
        expected_revision: int,
        target_state: Literal["running", "succeeded", "failed", "interrupted"],
        result: Mapping[str, object] | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> DurableJob:
        if target_state in {"cancelling", "cancelled"}:  # pragma: no cover - typing guard
            raise JobTransitionError("use the explicit cancellation operations")
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            current = self._job_in(connection, job_id)
            self._assert_revision(current.revision, expected_revision)
            validate_job_transition(current.state, target_state)
            if target_state == "succeeded" and any(
                step.state not in {"succeeded", "skipped"} for step in current.steps
            ):
                raise JobTransitionError("a job cannot succeed before every step succeeds or is skipped")
            if target_state == "succeeded":
                result_json = _canonical_object(
                    result or {},
                    label="job result",
                    max_bytes=MAX_JOB_RESULT_BYTES,
                    forbidden_values=self._forbidden_secret_values,
                )
                safe_failure_code = None
                safe_failure_message = None
            elif target_state in {"failed", "interrupted"}:
                safe_failure_code, safe_failure_message = _validate_failure(
                    failure_code, failure_message, self._forbidden_secret_values
                )
                if result is not None:
                    raise ValueError("failed or interrupted jobs cannot persist a success result")
                result_json = None
            else:
                if result is not None or failure_code is not None or failure_message is not None:
                    raise ValueError("running transition cannot persist a result or failure")
                result_json = None
                safe_failure_code = None
                safe_failure_message = None
            started_at = timestamp if target_state == "running" else current.started_at
            finished_at = timestamp if target_state in TERMINAL_JOB_STATES else None
            if target_state in {"failed", "interrupted"}:
                connection.execute(
                    "UPDATE job_steps SET state = ?, revision = revision + 1, finished_at = ? "
                    "WHERE job_id = ? AND state = 'running'",
                    (target_state, timestamp, job_id),
                )
            cursor = connection.execute(
                "UPDATE jobs SET state = ?, revision = revision + 1, updated_at = ?, started_at = ?, "
                "finished_at = ?, result_json = ?, failure_code = ?, failure_message = ? "
                "WHERE job_id = ? AND revision = ?",
                (
                    target_state,
                    timestamp,
                    started_at,
                    finished_at,
                    result_json,
                    safe_failure_code,
                    safe_failure_message,
                    job_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise JobConflictError("durable job revision conflict")
            self._inject("after_job_update", job_id)
            self._append_event_in(
                connection,
                job_id,
                event_type="state_changed",
                state=target_state,
                reason_code=safe_failure_code,
                progress=current.progress,
                timestamp=timestamp,
            )
            return self._job_in(connection, job_id)

    def report_progress(
        self,
        job_id: str,
        *,
        expected_revision: int,
        stage: str | None,
        current: int | None = None,
        total: int | None = None,
    ) -> DurableJob:
        progress = _validate_progress(stage, current, total)
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            job = self._job_in(connection, job_id)
            self._assert_revision(job.revision, expected_revision)
            if job.state != "running":
                raise JobTransitionError("progress can be recorded only while a job is running")
            cursor = connection.execute(
                "UPDATE jobs SET progress_stage = ?, progress_current = ?, progress_total = ?, "
                "revision = revision + 1, updated_at = ? WHERE job_id = ? AND revision = ?",
                (stage, current, total, timestamp, job_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise JobConflictError("durable job revision conflict")
            self._inject("after_progress_update", job_id)
            self._append_event_in(
                connection,
                job_id,
                event_type="progress",
                state="running",
                reason_code=None,
                progress=progress,
                timestamp=timestamp,
            )
            return self._job_in(connection, job_id)

    def transition_step(
        self,
        job_id: str,
        step_id: str,
        *,
        expected_job_revision: int,
        expected_step_revision: int,
        target_state: JobStepState,
    ) -> DurableJob:
        _validate_opaque(step_id, label="step ID")
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            job = self._job_in(connection, job_id)
            self._assert_revision(job.revision, expected_job_revision)
            row = connection.execute(
                "SELECT * FROM job_steps WHERE step_id = ? AND job_id = ?",
                (step_id, job_id),
            ).fetchone()
            if row is None:
                raise JobNotFoundError("durable job step does not exist")
            step_state = str(row["state"])
            step_revision = int(row["revision"])
            if step_revision != expected_step_revision:
                raise JobConflictError("durable job step revision conflict")
            validate_step_transition(step_state, target_state)
            if job.state == "running":
                allowed = {"running", "succeeded", "failed", "skipped", "interrupted"}
            elif job.state == "cancelling":
                allowed = {"cancelled", "interrupted"}
            else:
                allowed = set()
            if target_state not in allowed:
                raise JobTransitionError("job state does not permit that step transition")
            started_at = timestamp if target_state == "running" else row["started_at"]
            finished_at = timestamp if target_state in TERMINAL_STEP_STATES else None
            cursor = connection.execute(
                "UPDATE job_steps SET state = ?, revision = revision + 1, started_at = ?, finished_at = ? "
                "WHERE step_id = ? AND job_id = ? AND revision = ?",
                (target_state, started_at, finished_at, step_id, job_id, expected_step_revision),
            )
            if cursor.rowcount != 1:
                raise JobConflictError("durable job step revision conflict")
            job_cursor = connection.execute(
                "UPDATE jobs SET revision = revision + 1, updated_at = ? "
                "WHERE job_id = ? AND revision = ?",
                (timestamp, job_id, expected_job_revision),
            )
            if job_cursor.rowcount != 1:
                raise JobConflictError("durable job revision conflict")
            self._inject("after_step_update", job_id)
            self._append_event_in(
                connection,
                job_id,
                event_type="step_changed",
                state=job.state,
                reason_code=None,
                progress=job.progress,
                timestamp=timestamp,
            )
            return self._job_in(connection, job_id)

    def request_cancellation(self, job_id: str, *, expected_revision: int) -> DurableJob:
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            job = self._job_in(connection, job_id)
            self._assert_revision(job.revision, expected_revision)
            if job.state == "cancelling" or job.state == "cancelled":
                return job
            if job.state not in {"queued", "running"}:
                raise JobTransitionError("terminal jobs cannot be cancelled")
            target: JobState = "cancelled" if job.state == "queued" else "cancelling"
            validate_job_transition(job.state, target)
            if target == "cancelled":
                connection.execute(
                    "UPDATE job_steps SET state = 'cancelled', revision = revision + 1, finished_at = ? "
                    "WHERE job_id = ? AND state = 'pending'",
                    (timestamp, job_id),
                )
            cursor = connection.execute(
                "UPDATE jobs SET state = ?, revision = revision + 1, updated_at = ?, "
                "finished_at = ?, cancellation_requested_at = ? WHERE job_id = ? AND revision = ?",
                (
                    target,
                    timestamp,
                    timestamp if target == "cancelled" else None,
                    timestamp,
                    job_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise JobConflictError("durable job revision conflict")
            self._inject("after_cancel_request", job_id)
            self._append_event_in(
                connection,
                job_id,
                event_type="cancellation_requested",
                state=target,
                reason_code=None,
                progress=job.progress,
                timestamp=timestamp,
            )
            return self._job_in(connection, job_id)

    def acknowledge_cancellation(self, job_id: str, *, expected_revision: int) -> DurableJob:
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            job = self._job_in(connection, job_id)
            self._assert_revision(job.revision, expected_revision)
            validate_job_transition(job.state, "cancelled")
            connection.execute(
                "UPDATE job_steps SET state = 'cancelled', revision = revision + 1, finished_at = ? "
                "WHERE job_id = ? AND state IN ('pending', 'running')",
                (timestamp, job_id),
            )
            cursor = connection.execute(
                "UPDATE jobs SET state = 'cancelled', revision = revision + 1, updated_at = ?, "
                "finished_at = ? WHERE job_id = ? AND revision = ?",
                (timestamp, timestamp, job_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise JobConflictError("durable job revision conflict")
            self._inject("after_cancel_acknowledgement", job_id)
            self._append_event_in(
                connection,
                job_id,
                event_type="cancelled",
                state="cancelled",
                reason_code=None,
                progress=job.progress,
                timestamp=timestamp,
            )
            return self._job_in(connection, job_id)

    def recover_interrupted_jobs(self, *, limit: int = MAX_LIST_LIMIT) -> tuple[DurableJob, ...]:
        if isinstance(limit, bool) or not 1 <= limit <= MAX_LIST_LIMIT:
            raise JobLimitError("recovery limit is out of bounds")
        timestamp = self._clock()
        with self.database.transaction(write=True) as connection:
            rows = connection.execute(
                "SELECT job_id FROM jobs WHERE state IN ('running', 'cancelling') "
                "ORDER BY updated_at, job_id LIMIT ?",
                (limit,),
            ).fetchall()
            recovered: list[DurableJob] = []
            for row in rows:
                job_id = str(row["job_id"])
                job = self._job_in(connection, job_id)
                validate_job_transition(job.state, "interrupted")
                connection.execute(
                    "UPDATE job_steps SET state = 'interrupted', revision = revision + 1, finished_at = ? "
                    "WHERE job_id = ? AND state = 'running'",
                    (timestamp, job_id),
                )
                cursor = connection.execute(
                    "UPDATE jobs SET state = 'interrupted', revision = revision + 1, updated_at = ?, "
                    "finished_at = ?, failure_code = 'process_interrupted', "
                    "failure_message = 'Execution stopped before the process completed the job.' "
                    "WHERE job_id = ? AND revision = ?",
                    (timestamp, timestamp, job_id, job.revision),
                )
                if cursor.rowcount != 1:
                    raise JobConflictError("durable job revision conflict")
                self._inject("after_recovery_update", job_id)
                self._append_event_in(
                    connection,
                    job_id,
                    event_type="interrupted",
                    state="interrupted",
                    reason_code="process_interrupted",
                    progress=job.progress,
                    timestamp=timestamp,
                )
                recovered.append(self._job_in(connection, job_id))
            return tuple(recovered)

    def list_events(self, job_id: str, *, after_sequence: int = 0, limit: int = 100) -> tuple[JobEvent, ...]:
        _validate_opaque(job_id, label="job ID")
        if isinstance(after_sequence, bool) or after_sequence < 0:
            raise ValueError("event sequence must be non-negative")
        if isinstance(limit, bool) or not 1 <= limit <= MAX_LIST_LIMIT:
            raise JobLimitError("event list limit is out of bounds")
        with self.database.connection() as connection:
            if connection.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone() is None:
                raise JobNotFoundError("durable job does not exist")
            rows = connection.execute(
                "SELECT event_id, job_id, sequence, event_type, state, reason_code, "
                "progress_stage, progress_current, progress_total, occurred_at FROM job_events "
                "WHERE job_id = ? AND sequence > ? ORDER BY sequence LIMIT ?",
                (job_id, after_sequence, limit),
            ).fetchall()
        events: list[JobEvent] = []
        for row in rows:
            state = str(row["state"]) if row["state"] is not None else None
            if state is not None and state not in JOB_STATES:
                raise JobDataError("persisted job event state is invalid")
            try:
                progress = _validate_progress(
                    str(row["progress_stage"]) if row["progress_stage"] is not None else None,
                    int(row["progress_current"]) if row["progress_current"] is not None else None,
                    int(row["progress_total"]) if row["progress_total"] is not None else None,
                )
            except ValueError as error:
                raise JobDataError("persisted job event progress is invalid") from error
            events.append(
                JobEvent(
                    event_id=str(row["event_id"]),
                    job_id=str(row["job_id"]),
                    sequence=int(row["sequence"]),
                    event_type=str(row["event_type"]),
                    state=cast(JobState | None, state),
                    reason_code=str(row["reason_code"]) if row["reason_code"] is not None else None,
                    progress=progress,
                    occurred_at=str(row["occurred_at"]),
                )
            )
        return tuple(events)

    def _append_event_in(
        self,
        connection: sqlite3.Connection,
        job_id: str,
        *,
        event_type: str,
        state: JobState | None,
        reason_code: str | None,
        progress: JobProgress,
        timestamp: str,
    ) -> None:
        row = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM job_events WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        sequence = int(row[0]) if row else 1
        try:
            connection.execute(
                "INSERT INTO job_events(event_id, job_id, sequence, event_type, state, reason_code, "
                "progress_stage, progress_current, progress_total, occurred_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._new_id("event"),
                    job_id,
                    sequence,
                    event_type,
                    state,
                    reason_code,
                    progress.stage,
                    progress.current,
                    progress.total,
                    timestamp,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise JobConflictError("durable job event identity or sequence conflict") from error
