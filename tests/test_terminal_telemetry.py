"""Focused DATA-005 domain, persistence, projection, retention, and query tests."""

from __future__ import annotations

import itertools
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.workspace.database import WorkspaceDatabase
from src.workspace.jobs import SQLiteJobRepository
from src.workspace.migrations import MIGRATIONS
from src.workspace.telemetry import (
    LOG_RETENTION_DAYS,
    TELEMETRY_RETENTION_DAYS,
    SQLiteTelemetryRepository,
    TelemetryConflictError,
    TelemetryService,
    TelemetryValidationError,
    safe_request_correlation_id,
)
from src.workspace.transfer import WorkspaceTransferService
from configs.settings import Settings


NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
NOW_TEXT = "2026-09-27T12:00:00.000000Z"
FINGERPRINT = "a" * 64


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


class MutableClock:
    def __init__(self, value: datetime = NOW) -> None:
        self.value = value

    def __call__(self) -> str:
        return _timestamp(self.value)


def _repository(
    tmp_path: Path,
    *,
    clock: MutableClock | None = None,
    secrets: tuple[str, ...] = (),
) -> SQLiteTelemetryRepository:
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    assert database.initialize() == 6
    counter = itertools.count(1)
    return SQLiteTelemetryRepository(
        database,
        clock=clock or MutableClock(),
        id_factory=lambda: f"record-{next(counter):04d}",
        forbidden_secret_values=secrets,
    )


def _record(
    repository: SQLiteTelemetryRepository,
    *,
    telemetry_id: str = "tel_request_0001",
    route: str = "/query",
    subsystem: str = "query",
    capability: str = "provider_backed",
    outcome: str = "succeeded",
    severity: str = "info",
    duration_ms: float | None = 125.25,
    correlation_id: str = "request-0001",
    error_code: str | None = None,
    occurred_at: str = NOW_TEXT,
):
    return repository.record_request_terminal(
        telemetry_id=telemetry_id,
        subsystem=subsystem,
        route_template=route,
        capability=capability,
        severity=severity,
        outcome=outcome,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
        error_code=error_code,
        metadata={
            "http_method": "POST",
            "streaming": route.endswith("/stream"),
            "decomposed": route.startswith("/query/decomposed"),
            "status_code": 200 if outcome == "succeeded" else 500,
        },
        occurred_at=occurred_at,
    )


def test_terminal_record_has_stable_identity_exact_kind_utc_and_deterministic_metadata(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    record = _record(repository)

    assert record.telemetry_id == "tel_request_0001"
    assert record.event_kind == "request_terminal"
    assert record.subsystem == "query"
    assert record.outcome == "succeeded" and record.severity == "info"
    assert record.correlation_id == "request-0001"
    assert record.occurred_at == NOW_TEXT
    assert record.retention_until == _timestamp(NOW + timedelta(days=TELEMETRY_RETENTION_DAYS))
    with repository.database.connection() as connection:
        raw = connection.execute(
            "SELECT metadata_json FROM telemetry_events WHERE telemetry_id = ?",
            (record.telemetry_id,),
        ).fetchone()[0]
    assert raw == json.dumps(record.metadata, sort_keys=True, separators=(",", ":"))


def test_computed_zero_duration_and_unknown_duration_remain_distinct(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    zero = _record(repository, telemetry_id="tel_zero", duration_ms=0)
    unknown = _record(repository, telemetry_id="tel_unknown", duration_ms=None)

    assert zero.duration_ms == 0.0
    assert unknown.duration_ms is None


def test_same_terminal_identity_is_idempotent_but_cannot_rewrite_history(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    first = _record(repository)

    assert _record(repository) == first
    with pytest.raises(TelemetryConflictError, match="immutable"):
        _record(repository, outcome="failed", severity="error", error_code="provider_error")
    with repository.database.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0] == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("correlation_id", "Bearer=synthetic-secret"),
        ("correlation_id", "sk-synthetic0123456789012345"),
        ("correlation_id", "D:\\Project\\private\\file.txt"),
        ("correlation_id", "/home/example/private.txt"),
        ("correlation_id", "forged\nrecord"),
        ("error_code", "token=synthetic"),
    ],
)
def test_sensitive_path_control_and_credential_shaped_values_never_persist(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    repository = _repository(tmp_path)
    kwargs = {field: value}

    with pytest.raises(TelemetryValidationError):
        _record(repository, **kwargs)
    with repository.database.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0] == 0


def test_configured_secret_and_oversized_arbitrary_metadata_are_rejected(tmp_path: Path) -> None:
    secret = "workspace-secret-value-0123456789"
    repository = _repository(tmp_path, secrets=(secret,))

    with pytest.raises(TelemetryValidationError, match="secret"):
        _record(repository, correlation_id=secret)
    with pytest.raises(TelemetryValidationError, match="unsupported"):
        repository.record_request_terminal(
            telemetry_id="tel_large",
            subsystem="query",
            route_template="/query",
            capability="provider_backed",
            severity="info",
            outcome="succeeded",
            correlation_id="request-large",
            duration_ms=None,
            error_code=None,
            metadata={"authorization": "x" * 10_000},
            occurred_at=NOW_TEXT,
        )


def test_route_subsystem_and_capability_are_one_allowlisted_binding(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    with pytest.raises(TelemetryValidationError, match="binding"):
        _record(repository, route="/query", subsystem="search", capability="public_provider_free")
    with pytest.raises(TelemetryValidationError, match="binding"):
        _record(repository, route="/documents")


def test_reopen_preserves_terminal_records_and_migration_v6_is_idempotent(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    expected = _record(repository)

    reopened_database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    assert reopened_database.initialize() == 6
    reopened = SQLiteTelemetryRepository(reopened_database, clock=MutableClock(), forbidden_secret_values=())

    assert reopened.request_records(started_at=NOW - timedelta(hours=1), ended_at=NOW + timedelta(seconds=1)) == (expected,)


def test_v5_upgrade_adds_terminal_columns_without_rewriting_historical_migration(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    old = WorkspaceDatabase(path, migrations=MIGRATIONS[:5])
    assert old.initialize() == 5
    with old.transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO telemetry_events(telemetry_id, event_name, route_template, capability, status, duration_ms, occurred_at, retention_until) "
            "VALUES ('legacy_1', 'legacy_counter', NULL, NULL, 'complete', NULL, ?, ?)",
            (NOW_TEXT, _timestamp(NOW + timedelta(days=30))),
        )

    upgraded = WorkspaceDatabase(path)
    assert upgraded.initialize() == 6
    with upgraded.connection() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(telemetry_events)")}
        receipt = connection.execute(
            "SELECT name FROM schema_migrations WHERE version = 6"
        ).fetchone()[0]
    assert {"record_schema_version", "subsystem", "severity", "correlation_id", "metadata_json"}.issubset(columns)
    assert receipt == "terminal_telemetry_contract"
    repository = SQLiteTelemetryRepository(upgraded, clock=MutableClock(), forbidden_secret_values=())
    assert repository.request_records(started_at=NOW - timedelta(hours=1), ended_at=NOW + timedelta(seconds=1)) == ()


def test_retention_hides_and_prunes_expired_rows_on_reopen(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    old_time = NOW - timedelta(days=TELEMETRY_RETENTION_DAYS, seconds=1)
    _record(repository, occurred_at=_timestamp(old_time))

    reopened = SQLiteTelemetryRepository(
        WorkspaceDatabase(tmp_path / "workspace.sqlite3"),
        clock=MutableClock(),
        forbidden_secret_values=(),
    )
    assert reopened.database.initialize() == 6
    assert reopened.request_records(started_at=NOW - timedelta(days=30), ended_at=NOW) == ()
    with reopened.database.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0] == 0


def test_summary_defines_rates_denominators_and_duration_population(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    occurred_at = _timestamp(NOW - timedelta(seconds=1))
    _record(repository, telemetry_id="tel_ok", duration_ms=0, occurred_at=occurred_at)
    _record(
        repository,
        telemetry_id="tel_fail",
        outcome="failed",
        severity="error",
        duration_ms=100,
        error_code="provider_error",
        occurred_at=occurred_at,
    )
    _record(
        repository,
        telemetry_id="tel_reject",
        outcome="rejected",
        severity="warning",
        duration_ms=None,
        error_code="http_422",
        occurred_at=occurred_at,
    )

    summary = TelemetryService(repository).summary("24h")

    requests = summary["requests"]
    assert requests["terminal_count"] == 3
    assert requests["success_rate"] == {"value": 0.333333, "numerator": 1, "denominator": 3}
    assert requests["failure_rate"] == {"value": 0.333333, "numerator": 1, "denominator": 3}
    assert requests["duration_ms"] == {"known_count": 2, "unknown_count": 1, "p50": 50.0, "p95": 95.0}


def test_empty_summary_uses_null_rates_and_percentiles_not_zero(tmp_path: Path) -> None:
    summary = TelemetryService(_repository(tmp_path)).summary("24h")

    assert summary["requests"]["success_rate"]["value"] is None
    assert summary["requests"]["failure_rate"]["value"] is None
    assert summary["requests"]["duration_ms"]["p50"] is None
    assert summary["requests"]["duration_ms"]["p95"] is None


def test_timeseries_keeps_empty_duration_null_but_count_zero(tmp_path: Path) -> None:
    service = TelemetryService(_repository(tmp_path))

    counts = service.timeseries("24h", "hour", "request_count")
    durations = service.timeseries("24h", "hour", "request_duration_p95_ms")

    assert len(counts["points"]) == 24
    assert {point["value"] for point in counts["points"]} == {0}
    assert {point["value"] for point in durations["points"]} == {None}
    assert {point["denominator"] for point in durations["points"]} == {0}


def test_timeseries_largest_range_remains_bounded(tmp_path: Path) -> None:
    result = TelemetryService(_repository(tmp_path)).timeseries("30d", "hour", "request_count")

    assert len(result["points"]) == 720


def _terminal_jobs(database: WorkspaceDatabase) -> None:
    clock = MutableClock(NOW - timedelta(hours=2))
    counter = itertools.count(1)
    jobs = SQLiteJobRepository(
        database,
        clock=clock,
        id_factory=lambda: f"job-record-{next(counter):04d}",
        forbidden_secret_values=(),
    )

    succeeded = jobs.create_job(
        namespace="pipeline",
        job_type="pipeline_run",
        idempotency_key="success",
        configuration_fingerprint=FINGERPRINT,
        payload={},
    )
    clock.value += timedelta(minutes=1)
    succeeded = jobs.transition_job(succeeded.job_id, expected_revision=succeeded.revision, target_state="running")
    clock.value += timedelta(minutes=1)
    jobs.transition_job(succeeded.job_id, expected_revision=succeeded.revision, target_state="succeeded", result={})

    cancelled = jobs.create_job(
        namespace="pipeline",
        job_type="pipeline_run",
        idempotency_key="cancelled",
        configuration_fingerprint=FINGERPRINT,
        payload={},
    )
    clock.value += timedelta(minutes=1)
    jobs.request_cancellation(cancelled.job_id, expected_revision=cancelled.revision)

    interrupted = jobs.create_job(
        namespace="evaluation",
        job_type="native_evaluation",
        idempotency_key="interrupted",
        configuration_fingerprint=FINGERPRINT,
        payload={},
    )
    clock.value += timedelta(minutes=1)
    interrupted = jobs.transition_job(interrupted.job_id, expected_revision=interrupted.revision, target_state="running")
    clock.value += timedelta(minutes=1)
    jobs.transition_job(
        interrupted.job_id,
        expected_revision=interrupted.revision,
        target_state="interrupted",
        failure_code="process_interrupted",
        failure_message="Execution stopped before completion.",
    )

    exhausted = jobs.create_job(
        namespace="evaluation",
        job_type="native_evaluation",
        idempotency_key="budget",
        configuration_fingerprint=FINGERPRINT,
        payload={},
    )
    clock.value += timedelta(minutes=1)
    exhausted = jobs.transition_job(exhausted.job_id, expected_revision=exhausted.revision, target_state="running")
    clock.value += timedelta(minutes=1)
    jobs.transition_job(
        exhausted.job_id,
        expected_revision=exhausted.revision,
        target_state="failed",
        failure_code="budget_exhausted",
        failure_message="The provider attempt slot budget was exhausted.",
    )

    failed = jobs.create_job(
        namespace="evaluation",
        job_type="native_evaluation",
        idempotency_key="failed",
        configuration_fingerprint=FINGERPRINT,
        payload={},
    )
    clock.value += timedelta(minutes=1)
    failed = jobs.transition_job(failed.job_id, expected_revision=failed.revision, target_state="running")
    clock.value += timedelta(minutes=1)
    jobs.transition_job(
        failed.job_id,
        expected_revision=failed.revision,
        target_state="failed",
        failure_code="provider_error",
        failure_message="The provider operation failed.",
    )


def test_terminal_jobs_are_read_only_projections_with_distinct_severity_and_no_fake_duration(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _terminal_jobs(repository.database)

    jobs = repository.terminal_jobs(started_at=NOW - timedelta(days=1), ended_at=NOW)
    summary = TelemetryService(repository).summary("24h")["terminal_jobs"]

    assert {item.outcome for item in jobs} == {"succeeded", "cancelled", "interrupted", "failed"}
    assert next(item for item in jobs if item.outcome == "cancelled").level == "info"
    assert next(item for item in jobs if item.outcome == "interrupted").level == "warning"
    budget = next(item for item in jobs if item.error_code == "budget_exhausted")
    assert budget.outcome == "failed" and budget.level == "warning"
    provider_failure = next(item for item in jobs if item.error_code == "provider_error")
    assert provider_failure.outcome == "failed" and provider_failure.level == "error"
    assert all(item.duration_ms is None and item.domain_id == item.correlation_id for item in jobs)
    assert summary["terminal_count"] == 5
    assert summary["by_namespace"] == {"pipeline": 2, "evaluation": 3, "model_test": 0}
    assert summary["by_outcome"] == {"succeeded": 1, "failed": 2, "cancelled": 1, "interrupted": 1}
    with repository.database.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 5


def test_logs_merge_request_and_job_truth_with_stable_cursor_pagination_and_filters(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _record(repository, telemetry_id="tel_a", occurred_at=_timestamp(NOW - timedelta(minutes=2)))
    _record(
        repository,
        telemetry_id="tel_b",
        outcome="failed",
        severity="error",
        error_code="provider_error",
        occurred_at=_timestamp(NOW - timedelta(minutes=1)),
    )
    _terminal_jobs(repository.database)
    service = TelemetryService(repository)

    first = service.logs(limit=2)
    second = service.logs(limit=2, cursor=first.next_cursor)
    errors = service.logs(level="error")
    requests = service.logs(category="request")

    assert first.has_more and first.next_cursor
    assert not {item.record_id for item in first.items}.intersection(item.record_id for item in second.items)
    assert all(item.level == "error" for item in errors.items)
    assert all(item.category == "request" for item in requests.items)
    combined = list(first.items + second.items)
    assert combined == sorted(combined, key=lambda item: (item.occurred_at, item.record_id), reverse=True)


def test_logs_enforce_seven_day_view_even_while_telemetry_is_retained_for_thirty(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _record(
        repository,
        occurred_at=_timestamp(NOW - timedelta(days=LOG_RETENTION_DAYS, seconds=1)),
    )

    assert TelemetryService(repository).logs().items == ()
    retained = repository.request_records(started_at=NOW - timedelta(days=30), ended_at=NOW)
    assert len(retained) == 1


def test_invalid_cursor_filter_limit_and_wrong_identity_do_not_match(tmp_path: Path) -> None:
    service = TelemetryService(_repository(tmp_path))

    with pytest.raises(TelemetryValidationError, match="cursor"):
        service.logs(cursor="not-base64")
    with pytest.raises(TelemetryValidationError, match="category"):
        service.logs(category="debug")
    with pytest.raises(TelemetryValidationError, match="limit"):
        service.logs(limit=101)
    assert service.logs().items == ()


def test_safe_request_identity_replaces_secrets_paths_controls_and_oversized_values() -> None:
    configured = Settings(
        _env_file=None,
        workspace_mode="local",
        local_workspace_token="workspace-secret-0123456789-abcdef",
    )
    values = [
        configured.local_workspace_token.get_secret_value(),
        "Bearer=synthetic",
        "C:\\Users\\Example\\secret.txt",
        "/home/example/secret.txt",
        "forged\nrequest",
        "x" * 200,
    ]

    assert safe_request_correlation_id("trace-123", configured) == "trace-123"
    for value in values:
        safe = safe_request_correlation_id(value, configured, id_factory=lambda: "safe-id")
        assert safe == "req_safe-id"
        assert value not in safe


def test_workspace_transfer_excludes_telemetry_and_job_operational_history(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _record(repository)
    _terminal_jobs(repository.database)

    backup = WorkspaceTransferService(repository.database).export_backup()
    encoded = json.dumps(backup)

    assert "telemetry_events" not in encoded
    assert "job_events" not in encoded
    assert "tel_request_0001" not in encoded
