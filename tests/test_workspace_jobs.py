"""Hermetic DATA-004 durable-job contract and SQLite persistence tests."""

from __future__ import annotations

import itertools
import sqlite3
import threading
from pathlib import Path

import pytest

from configs.settings import Settings
from src.workspace.database import WorkspaceDatabase, WorkspaceDisabledError
from src.workspace.jobs import (
    JOB_STATES,
    TERMINAL_JOB_STATES,
    JobConflictError,
    JobDataError,
    JobLimitError,
    JobTransitionError,
    SQLiteJobRepository,
    validate_job_transition,
    validate_step_transition,
)
from src.workspace.migrations import MIGRATIONS
from src.workspace.transfer import WorkspaceTransferService


FINGERPRINT = "a" * 64


def _ids(prefix: str = "fixed"):
    counter = itertools.count(1)
    return lambda: f"{prefix}{next(counter):04d}"


def _repository(
    tmp_path: Path,
    *,
    name: str = "workspace.sqlite3",
    failure_injector=None,
) -> SQLiteJobRepository:
    database = WorkspaceDatabase(tmp_path / name)
    assert database.initialize() == 4
    return SQLiteJobRepository(
        database,
        clock=lambda: "2026-09-22T10:00:00.000000Z",
        id_factory=_ids(name.replace(".", "")),
        failure_injector=failure_injector,
        forbidden_secret_values=("configured-secret-value",),
    )


def _create(repository: SQLiteJobRepository, *, key: str = "request-1", steps=("fetch", "index")):
    return repository.create_job(
        namespace="pipeline",
        job_type="ingest_filings",
        idempotency_key=key,
        configuration_fingerprint=FINGERPRINT,
        payload={"tickers": ["AAPL"], "year": 2025},
        artifact_references=("run_2025_aapl",),
        steps=steps,
    )


def _running(repository: SQLiteJobRepository, *, key: str = "request-1", steps=("fetch", "index")):
    created = _create(repository, key=key, steps=steps)
    return repository.transition_job(
        created.job_id,
        expected_revision=created.revision,
        target_state="running",
    )


def test_transition_contract_is_explicit_and_terminal_states_are_absorbing() -> None:
    allowed = {
        ("queued", "running"),
        ("queued", "cancelled"),
        ("running", "cancelling"),
        ("running", "succeeded"),
        ("running", "failed"),
        ("running", "interrupted"),
        ("cancelling", "cancelled"),
        ("cancelling", "interrupted"),
    }
    for current in JOB_STATES:
        for target in JOB_STATES:
            if (current, target) in allowed:
                validate_job_transition(current, target)
            else:
                with pytest.raises(JobTransitionError):
                    validate_job_transition(current, target)
    for state in TERMINAL_JOB_STATES:
        with pytest.raises(JobTransitionError):
            validate_job_transition(state, "running")


def test_step_transition_contract_rejects_restarts_and_terminal_mutations() -> None:
    for target in ("running", "cancelled", "skipped"):
        validate_step_transition("pending", target)
    for target in ("cancelled", "succeeded", "failed", "interrupted"):
        validate_step_transition("running", target)
    for state in ("cancelled", "succeeded", "failed", "skipped", "interrupted"):
        with pytest.raises(JobTransitionError):
            validate_step_transition(state, "running")


def test_create_is_durable_idempotent_and_never_persists_raw_key(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    created = _create(repository)
    repeated = _create(repository)

    assert repeated == created
    assert created.job_id.startswith("job_")
    assert created.revision == 1
    assert [step.name for step in created.steps] == ["fetch", "index"]
    with repository.database.connection() as connection:
        row = connection.execute(
            "SELECT idempotency_key_hash, payload_json FROM jobs WHERE job_id = ?",
            (created.job_id,),
        ).fetchone()
    assert row["idempotency_key_hash"] != "request-1"
    assert len(row["idempotency_key_hash"]) == 64
    assert "request-1" not in row["payload_json"]

    reopened = SQLiteJobRepository(repository.database)
    assert reopened.get_job(created.job_id).payload == created.payload


def test_idempotency_key_reuse_with_different_request_conflicts(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _create(repository)
    with pytest.raises(JobConflictError, match="different job request"):
        repository.create_job(
            namespace="pipeline",
            job_type="different_type",
            idempotency_key="request-1",
            configuration_fingerprint=FINGERPRINT,
            payload={},
        )


def test_job_step_progress_and_event_revisions_are_atomic(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    running = _running(repository)
    first_step = running.steps[0]
    with pytest.raises(JobConflictError):
        repository.report_progress(
            running.job_id,
            expected_revision=1,
            stage="fetching",
            current=1,
            total=3,
        )

    progressed = repository.report_progress(
        running.job_id,
        expected_revision=running.revision,
        stage="fetching",
        current=1,
        total=3,
    )
    stepped = repository.transition_step(
        progressed.job_id,
        first_step.step_id,
        expected_job_revision=progressed.revision,
        expected_step_revision=first_step.revision,
        target_state="running",
    )
    assert progressed.revision == running.revision + 1
    assert stepped.revision == progressed.revision + 1
    assert stepped.steps[0].revision == first_step.revision + 1
    events = repository.list_events(stepped.job_id)
    assert [event.sequence for event in events] == [1, 2, 3, 4]
    assert events[2].progress.stage == "fetching"
    assert events[2].progress.current == 1


def test_success_requires_completed_steps_and_result_is_durable(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    job = _running(repository, steps=("fetch",))
    with pytest.raises(JobTransitionError, match="every step"):
        repository.transition_job(job.job_id, expected_revision=job.revision, target_state="succeeded")
    job = repository.transition_step(
        job.job_id,
        job.steps[0].step_id,
        expected_job_revision=job.revision,
        expected_step_revision=1,
        target_state="running",
    )
    job = repository.transition_step(
        job.job_id,
        job.steps[0].step_id,
        expected_job_revision=job.revision,
        expected_step_revision=2,
        target_state="succeeded",
    )
    job = repository.transition_job(
        job.job_id,
        expected_revision=job.revision,
        target_state="succeeded",
        result={"artifact": "run_2025_aapl"},
    )
    assert job.state == "succeeded"
    assert job.result == {"artifact": "run_2025_aapl"}
    assert job.finished_at is not None


def test_running_cancellation_requires_acknowledgement_but_queued_cancels_immediately(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    queued = _create(repository, key="queued")
    cancelled = repository.request_cancellation(queued.job_id, expected_revision=queued.revision)
    assert cancelled.state == "cancelled"
    assert all(step.state == "cancelled" for step in cancelled.steps)

    running = _running(repository, key="running")
    cancelling = repository.request_cancellation(running.job_id, expected_revision=running.revision)
    assert cancelling.state == "cancelling"
    assert cancelling.finished_at is None
    acknowledged = repository.acknowledge_cancellation(
        cancelling.job_id, expected_revision=cancelling.revision
    )
    assert acknowledged.state == "cancelled"
    assert acknowledged.finished_at is not None
    assert repository.request_cancellation(
        acknowledged.job_id, expected_revision=acknowledged.revision
    ) == acknowledged


def test_restart_recovery_interrupts_only_active_work(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    queued = _create(repository, key="queued")
    running = _running(repository, key="running")
    running = repository.transition_step(
        running.job_id,
        running.steps[0].step_id,
        expected_job_revision=running.revision,
        expected_step_revision=1,
        target_state="running",
    )
    cancelling = _running(repository, key="cancelling")
    cancelling = repository.request_cancellation(
        cancelling.job_id, expected_revision=cancelling.revision
    )

    reopened = SQLiteJobRepository(repository.database)
    assert reopened.get_job(queued.job_id).state == "queued"
    assert reopened.get_job(running.job_id).state == "running"
    recovered = reopened.recover_interrupted_jobs()

    assert {job.job_id for job in recovered} == {running.job_id, cancelling.job_id}
    recovered_running = reopened.get_job(running.job_id)
    assert recovered_running.state == "interrupted"
    assert [step.state for step in recovered_running.steps] == ["interrupted", "pending"]
    assert reopened.get_job(queued.job_id).state == "queued"
    assert reopened.recover_interrupted_jobs() == ()


def test_two_contenders_cannot_both_start_the_same_job(tmp_path: Path) -> None:
    first = _repository(tmp_path)
    created = _create(first)
    second = SQLiteJobRepository(WorkspaceDatabase(first.database.path))
    barrier = threading.Barrier(3)
    outcomes: list[str] = []

    def start(repository: SQLiteJobRepository) -> None:
        barrier.wait()
        try:
            repository.transition_job(
                created.job_id,
                expected_revision=created.revision,
                target_state="running",
            )
            outcomes.append("started")
        except JobConflictError:
            outcomes.append("conflict")

    threads = [threading.Thread(target=start, args=(repository,)) for repository in (first, second)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=3)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(outcomes) == ["conflict", "started"]
    assert first.get_job(created.job_id).state == "running"


@pytest.mark.parametrize(
    ("phase", "operation"),
    [
        ("after_create", "create"),
        ("after_job_update", "transition"),
        ("after_progress_update", "progress"),
        ("after_step_update", "step"),
        ("after_cancel_request", "cancel"),
        ("after_recovery_update", "recover"),
    ],
)
def test_injected_failures_roll_back_each_logical_operation(
    tmp_path: Path, phase: str, operation: str
) -> None:
    repository = _repository(tmp_path, name=f"{operation}.sqlite3")
    job = None
    if operation != "create":
        job = _running(repository, steps=("fetch",))
    before = repository.get_job(job.job_id) if job is not None else None
    before_events = repository.list_events(job.job_id) if job is not None else ()

    def fail(current_phase: str, _job_id: str) -> None:
        if current_phase == phase:
            raise RuntimeError("injected")

    repository._failure_injector = fail
    with pytest.raises(RuntimeError, match="injected"):
        if operation == "create":
            _create(repository)
        elif operation == "transition":
            repository.transition_job(
                job.job_id,
                expected_revision=job.revision,
                target_state="failed",
                failure_code="provider_error",
                failure_message="Provider failed safely.",
            )
        elif operation == "progress":
            repository.report_progress(
                job.job_id, expected_revision=job.revision, stage="fetching"
            )
        elif operation == "step":
            repository.transition_step(
                job.job_id,
                job.steps[0].step_id,
                expected_job_revision=job.revision,
                expected_step_revision=1,
                target_state="running",
            )
        elif operation == "cancel":
            repository.request_cancellation(job.job_id, expected_revision=job.revision)
        else:
            repository.recover_interrupted_jobs()

    if operation == "create":
        assert repository.list_jobs().total == 0
    else:
        assert repository.get_job(job.job_id) == before
        assert repository.list_events(job.job_id) == before_events


@pytest.mark.parametrize(
    "payload",
    [
        {"api_key": "value"},
        {"nested": {"providerToken": "value"}},
        {"path": "C:\\private\\artifact.bin"},
        {"message": "authorization: Bearer value"},
        {"value": "configured-secret-value"},
        {"nan": float("nan")},
    ],
)
def test_payload_rejects_credentials_paths_and_non_finite_json(tmp_path: Path, payload) -> None:
    repository = _repository(tmp_path)
    with pytest.raises((ValueError, JobLimitError)):
        repository.create_job(
            namespace="pipeline",
            job_type="ingest_filings",
            idempotency_key="safe-key",
            configuration_fingerprint=FINGERPRINT,
            payload=payload,
        )


def test_bounds_progress_failure_and_artifact_validation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    with pytest.raises(JobLimitError):
        repository.create_job(
            namespace="pipeline",
            job_type="ingest_filings",
            idempotency_key="large",
            configuration_fingerprint=FINGERPRINT,
            payload={"value": "x" * (64 * 1024)},
        )
    with pytest.raises(ValueError, match="portable opaque"):
        repository.create_job(
            namespace="pipeline",
            job_type="ingest_filings",
            idempotency_key="path-ref",
            configuration_fingerprint=FINGERPRINT,
            payload={},
            artifact_references=("runs/output.json",),
        )
    running = _running(repository)
    with pytest.raises(ValueError, match="both be known"):
        repository.report_progress(
            running.job_id, expected_revision=running.revision, stage="fetching", current=1
        )
    with pytest.raises(ValueError, match="credential"):
        repository.transition_job(
            running.job_id,
            expected_revision=running.revision,
            target_state="failed",
            failure_code="provider_error",
            failure_message="token=configured-secret-value",
        )


def test_listing_and_event_pagination_are_deterministic(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    first = _create(repository, key="one")
    second = _create(repository, key="two")
    page = repository.list_jobs(namespace="pipeline", state="queued", limit=1)
    expected_first = max(first.job_id, second.job_id)
    assert page.total == 2
    assert page.items[0].job_id == expected_first
    events = repository.list_events(first.job_id, after_sequence=0, limit=1)
    assert len(events) == 1 and events[0].sequence == 1
    with pytest.raises(JobLimitError):
        repository.list_jobs(limit=101)


def test_v3_upgrade_is_additive_and_legacy_job_rows_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    old = WorkspaceDatabase(path, migrations=MIGRATIONS[:3])
    assert old.initialize() == 3
    with old.transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO jobs(job_id, namespace, job_type, state, configuration_fingerprint, "
            "revision, created_at, updated_at) VALUES (?, 'pipeline', 'legacy_job', 'queued', ?, 1, ?, ?)",
            ("job_legacy", FINGERPRINT, "2026-09-22T00:00:00Z", "2026-09-22T00:00:00Z"),
        )

    upgraded = WorkspaceDatabase(path)
    assert upgraded.initialize() == 4
    with upgraded.connection() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(jobs)")}
        event_columns = {row["name"] for row in connection.execute("PRAGMA table_info(job_events)")}
        indexes = {row["name"] for row in connection.execute("PRAGMA index_list(jobs)")}
        assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    assert {"record_schema_version", "payload_json", "result_json"}.issubset(columns)
    assert "progress_stage" in event_columns
    assert {"jobs_idempotency_idx", "jobs_listing_idx"}.issubset(indexes)
    with pytest.raises(JobDataError, match="legacy job row"):
        SQLiteJobRepository(upgraded).get_job("job_legacy")


def test_public_settings_never_construct_job_storage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    configured = Settings(_env_file=None)
    with pytest.raises(WorkspaceDisabledError):
        SQLiteJobRepository.from_settings(configured)
    assert not (tmp_path / ".local").exists()


def test_job_repository_exposes_no_delete_retry_or_lease_surface() -> None:
    for method in ("delete_job", "retry_job", "claim_lease", "heartbeat", "requeue_job"):
        assert not hasattr(SQLiteJobRepository, method)


def test_workspace_transfer_excludes_private_job_history_without_mutating_it(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    created = _create(repository)

    backup = WorkspaceTransferService(repository.database).export_backup()

    assert "jobs" not in backup
    assert "job_events" not in backup
    assert repository.get_job(created.job_id) == created
