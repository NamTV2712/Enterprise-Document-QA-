"""AGENT-003 durable lifecycle, events and crash boundaries without network."""

from __future__ import annotations

import asyncio
import hashlib
import threading
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.agent.durable import AgentDurableService
from src.agent.durable_models import AgentRunCreateRequest
from src.agent.registry import build_tool_registry
from src.workspace.database import WorkspaceDatabase, WorkspaceMigrationError
from src.workspace.jobs import (
    JobConflictError, JobTransitionError, SQLiteJobRepository,
)
from src.workspace.migrations import MIGRATIONS, Migration
from tests.test_agent_orchestration import (
    ATTACK, CHUNK, DOC, ScriptedDecisionModel, _final, _services, _tool,
)


def _service(tmp_path: Path, decisions=(), *, limits=None, text="Safe evidence 🚀",
             model_factory=None, repository=None):
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    database.initialize()
    repo = repository or SQLiteJobRepository(database)
    calls: list[str] = []
    model = ScriptedDecisionModel(*decisions)
    factory = model_factory if model_factory is not None else lambda _identity: model
    service = AgentDurableService(
        repo, lambda: build_tool_registry(_services(calls, text=text)),
        decision_model_factory=factory, decision_model_id="scripted_test",
    )
    body = AgentRunCreateRequest(goal="Find relevant risk evidence.", **({"limits": limits} if limits else {}))
    return service, repo, calls, model, body


def _create(service, body=None, key="agent-key-1"):
    return service.create(body or AgentRunCreateRequest(goal="Find relevant risk evidence."),
                          idempotency_key=key)


def _run(service, run_id):
    return asyncio.run(service.run(run_id))


def test_v7_fresh_and_v6_upgrade_preserve_existing_jobs_evaluation_rows_and_receipts(tmp_path):
    path = tmp_path / "workspace.sqlite3"
    old = WorkspaceDatabase(path, migrations=MIGRATIONS[:6])
    assert old.initialize() == 6
    repo = SQLiteJobRepository(old)
    job = repo.create_job(
        namespace="evaluation", job_type="frozen_native_evaluation",
        idempotency_key="legacy-eval", configuration_fingerprint="a" * 64,
        payload={"safe": "value"}, steps=("execute_cases", "aggregate_report"),
    )
    with old.transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO evaluation_attempts(job_id, ordinal, case_id, phase, attempted_at) "
            "VALUES (?, 1, 'case_1', 'generation', '2026-01-01T00:00:00Z')", (job.job_id,),
        )
        connection.execute(
            "INSERT INTO evaluation_case_results(job_id, ordinal, case_id, result_json, committed_at) "
            "VALUES (?, 0, 'case_1', '{}', '2026-01-01T00:00:00Z')", (job.job_id,),
        )
        connection.execute(
            "INSERT INTO evaluation_reports(job_id, report_json, committed_at) "
            "VALUES (?, ?, '2026-01-01T00:00:00Z')", (job.job_id, b"{}"),
        )
    current = WorkspaceDatabase(path)
    assert current.initialize() == 7
    assert current.initialize() == 7
    reopened = SQLiteJobRepository(current).get_job(job.job_id)
    assert reopened.namespace == "evaluation" and reopened.revision == 1
    assert len(reopened.steps) == 2
    assert len(SQLiteJobRepository(current).list_events(job.job_id)) == 1
    with current.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM evaluation_attempts").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM evaluation_case_results").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM evaluation_reports").fetchone()[0] == 1
        assert list(connection.execute("PRAGMA foreign_key_check")) == []
        receipts = list(connection.execute("SELECT version, checksum FROM schema_migrations ORDER BY version"))
    assert [row["version"] for row in receipts] == list(range(1, 8))
    assert [row["checksum"] for row in receipts] == [migration.checksum for migration in MIGRATIONS]


def test_v7_migration_failure_rolls_back_without_losing_v6_jobs(tmp_path):
    path = tmp_path / "workspace.sqlite3"
    old = WorkspaceDatabase(path, migrations=MIGRATIONS[:6])
    old.initialize()
    job = SQLiteJobRepository(old).create_job(
        namespace="pipeline", job_type="safe_stage", idempotency_key="before-v7",
        configuration_fingerprint="a" * 64, payload={}, steps=("stage",),
    )
    broken = Migration(7, "agent_durable_jobs", MIGRATIONS[6].statements + ("INVALID SQL",))
    with pytest.raises(WorkspaceMigrationError):
        WorkspaceDatabase(path, migrations=MIGRATIONS[:6] + (broken,)).initialize()
    assert old.current_schema_version() == 6
    assert SQLiteJobRepository(old).get_job(job.job_id).steps[0].name == "stage"
    assert WorkspaceDatabase(path).initialize() == 7


def test_queued_plan_is_frozen_reopenable_idempotent_and_secret_free(tmp_path):
    service, repo, _, _, body = _service(tmp_path)
    created = _create(service, body)
    replay = _create(service, body)
    assert replay.run_id == created.run_id and replay.revision == 1
    assert created.run_id.startswith("agent_") and created.run_id != "job_" + created.run_id[6:]
    assert created.state == "queued" and created.step.state == "pending"
    assert created.frozen.limits.max_steps == 8 and created.frozen.locale == "en"
    reopened = AgentDurableService(
        SQLiteJobRepository(WorkspaceDatabase(repo.database.path)), service.registry_factory,
        decision_model_factory=service.decision_model_factory, decision_model_id="changed_default",
    )
    assert reopened.get(created.run_id).frozen == created.frozen
    with pytest.raises(JobConflictError):
        reopened.create(body.model_copy(update={"goal": "A different safe goal."}),
                        idempotency_key="agent-key-1")
    with pytest.raises(ValidationError):
        AgentRunCreateRequest(goal="Authorization: Bearer synthetic-secret")
    with repo.database.connection() as connection:
        raw = connection.execute("SELECT payload_json, idempotency_key_hash FROM jobs").fetchone()
    assert raw["idempotency_key_hash"] == hashlib.sha256(b"agent-key-1").hexdigest()
    assert "agent-key-1" not in raw["payload_json"]
    assert "Bearer" not in raw["payload_json"]


def test_scripted_execution_events_result_and_frozen_limits(tmp_path):
    service, repo, calls, model, body = _service(tmp_path, (
        _tool("search_documents", query="risk evidence", group_by="chunk"),
        _tool("read_document", document_id=DOC),
        _final("Risk evidence summarized.", ("document_id", DOC), ("chunk_id", CHUNK)),
    ))
    created = _create(service, body)
    service.decision_model_id = "changed_default"
    final = _run(service, created.run_id)
    assert final.state == "succeeded" and final.result.agent_status == "completed"
    assert final.result.answer == "Risk evidence summarized."
    assert final.result.step_count == 3 and final.result.tool_call_count == 2
    assert final.result.per_tool_calls["read_document"] == 1
    assert calls == ["search_documents", "read_document"] and len(model.requests) == 3
    assert final.frozen.decision_model_id == "scripted_test"
    assert final.frozen.limits.max_steps == 8
    assert final.result.evidence_refs[0].value == DOC
    events = service.events(created.run_id, after_sequence=0)
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert [event.summary.tool_name for event in events if event.summary and event.summary.tool_name] == calls
    assert service.events(created.run_id, after_sequence=events[3].sequence) == events[4:]
    assert len(events) <= 8 + 6
    assert _run(service, created.run_id).revision == final.revision
    assert service.result(created.run_id).result == final.result


def test_frozen_tool_policy_and_budget_ignore_later_mutation(tmp_path):
    service, _, calls, _, _ = _service(tmp_path, (
        _tool("read_document", document_id=DOC, page=1),
        _tool("read_document", document_id=DOC, page=2),
    ))
    body = AgentRunCreateRequest(
        goal="Find relevant risk evidence.", allowed_tools=["read_document"],
        limits={"max_steps": 4, "max_tool_calls": 1,
                "per_tool_calls": {"search_documents": 0, "inspect_retrieval": 0,
                                   "read_document": 1, "ask_rag": 0},
                "max_observations": 1, "max_evidence_per_observation": 1,
                "max_excerpt_chars": 20, "max_observation_bytes": 256,
                "max_total_observation_bytes": 256},
    )
    created = _create(service, body)
    body.allowed_tools.append("ask_rag")
    body.limits.per_tool_calls["read_document"] = 10
    result = _run(service, created.run_id)
    assert result.frozen.allowed_tools == ("read_document",)
    assert result.frozen.limits.max_tool_calls == 1
    assert result.frozen.limits.per_tool_calls["read_document"] == 1
    assert result.frozen.limits.max_observation_bytes == 256
    assert result.state == "failed" and result.result.agent_status == "budget_exhausted"
    assert calls == ["read_document"]


def test_agent_event_key_dedup_and_hard_count_bound(tmp_path):
    service, repo, _, _, _ = _service(tmp_path)
    created = _create(service)
    job = repo.get_job("job_" + created.run_id[6:])
    repo.transition_job(job.job_id, expected_revision=job.revision, target_state="running")
    payload = {"decision_index": 1, "decision_kind": "tool", "tool_name": "read_document",
               "argument_names": [], "outcome": "observed", "evidence_count": 0,
               "evidence_refs": [], "step_count": 1, "tool_call_count": 1,
               "failure_code": None}
    first = repo.append_agent_decision_event(
        job.job_id, event_key="decision_1", payload=payload, step_count=1, max_steps=20,
    )
    revision = repo.get_job(job.job_id).revision
    replay = repo.append_agent_decision_event(
        job.job_id, event_key="decision_1", payload=payload, step_count=1, max_steps=20,
    )
    assert replay.event_id == first.event_id and repo.get_job(job.job_id).revision == revision
    with pytest.raises(JobConflictError):
        repo.append_agent_decision_event(
            job.job_id, event_key="decision_1", payload={**payload, "tool_name": "ask_rag"},
            step_count=1, max_steps=20,
        )
    with pytest.raises(ValueError):
        repo.append_agent_decision_event(
            job.job_id, event_key="decision_2", payload={**payload, "decision_index": 2},
            step_count=1, max_steps=1,
        )
    for index in range(2, 21):
        repo.append_agent_decision_event(
            job.job_id, event_key=f"decision_{index}",
            payload={**payload, "decision_index": index, "step_count": index},
            step_count=index, max_steps=20,
        )
    with pytest.raises(ValueError):
        repo.append_agent_decision_event(
            job.job_id, event_key="decision_21", payload={**payload, "decision_index": 21},
            step_count=20, max_steps=20,
        )
    assert len(repo.list_agent_events(job.job_id)) == 22  # created, running, 20 decisions


def test_unavailable_model_and_invalid_or_exhausted_decisions_are_terminal_failures(tmp_path):
    service, _, calls, _, body = _service(tmp_path, model_factory=lambda _identity: None)
    service.decision_model_factory = None
    created = _create(service, body)
    unavailable = _run(service, created.run_id)
    assert unavailable.state == "failed" and unavailable.result.agent_status == "unavailable"
    assert unavailable.failure.code == "decision_provider_unavailable" and calls == []

    service, _, calls, _, _ = _service(tmp_path / "missing_factory", model_factory=lambda _identity: None)
    missing = _run(service, _create(service).run_id)
    assert missing.state == "failed" and missing.result.agent_status == "unavailable" and calls == []

    service, _, calls, _, _ = _service(tmp_path / "invalid", (
        {"kind": "final", "answer": "Bad", "reasoning": "hidden reasoning sentinel"},
    ))
    invalid = _run(service, _create(service).run_id)
    assert invalid.state == "failed" and invalid.result.agent_status == "invalid_decision"
    assert invalid.failure.code == "malformed_decision" and calls == []
    assert "hidden reasoning sentinel" not in service.repository.database.path.read_bytes().decode("utf-8", "ignore")

    service, _, calls, _, body = _service(tmp_path / "exhausted", (
        _tool("read_document", document_id=DOC, page=1),
        _tool("read_document", document_id=DOC, page=2),
    ), limits={"max_steps": 2})
    exhausted = _run(service, _create(service, body).run_id)
    assert exhausted.state == "failed" and exhausted.result.agent_status == "budget_exhausted"
    assert exhausted.failure.code == "max_steps" and calls == ["read_document", "read_document"]


def test_decision_and_rag_provider_permissions_stay_independent_when_frozen(tmp_path):
    decisions = (
        _tool("ask_rag", question="What did the filing say?"),
        _final("Grounded result [Source 1].", ("chunk_id", CHUNK)),
    )
    service, _, calls, model, _ = _service(tmp_path / "denied", decisions)
    model.requires_provider = True
    body = AgentRunCreateRequest(
        goal="Summarize the relevant filing evidence.", allowed_tools=["ask_rag"],
        allow_decision_provider_execution=True, allow_provider_tool_execution=False,
    )
    denied = _run(service, _create(service, body).run_id)
    assert denied.state == "failed" and denied.result.agent_status == "policy_denied"
    assert denied.failure.code == "tool_provider_required" and calls == []

    service, _, calls, model, _ = _service(tmp_path / "allowed", decisions)
    model.requires_provider = True
    allowed = _run(service, _create(service, body.model_copy(
        update={"allow_provider_tool_execution": True})).run_id)
    assert allowed.state == "succeeded" and allowed.result.agent_status == "completed"
    assert calls == ["ask_rag"] and allowed.result.evidence_refs[0].value == CHUNK


def test_tool_unavailable_and_unknown_action_keep_distinct_durable_causes(tmp_path):
    service, _, calls, _, _ = _service(tmp_path / "unavailable", (
        _tool("read_document", document_id=DOC),
    ))
    service.registry_factory = lambda: build_tool_registry(_services(
        calls, failure=HTTPException(status_code=503, detail="synthetic provider secret"),
    ))
    unavailable = _run(service, _create(service).run_id)
    assert unavailable.state == "failed" and unavailable.result.agent_status == "unavailable"
    assert unavailable.failure.code == "tool_unavailable"
    assert "synthetic provider secret" not in unavailable.model_dump_json()

    service, _, calls, _, _ = _service(tmp_path / "unknown", (_tool("delete_database"),))
    invalid = _run(service, _create(service).run_id)
    assert invalid.state == "failed" and invalid.result.agent_status == "invalid_decision"
    assert invalid.failure.code == "unknown_tool" and calls == []


def test_claim_race_runs_one_model_and_one_tool(tmp_path):
    entered = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    class SlowModel:
        requires_provider = False

        async def decide(self, _request):
            entered.set()
            await asyncio.to_thread(release.wait)
            return _tool("read_document", document_id=DOC)

    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    database.initialize()
    repo = SQLiteJobRepository(database)
    made = []

    def factory(_identity):
        made.append(1)
        return SlowModel()

    service = AgentDurableService(
        repo, lambda: build_tool_registry(_services(calls)),
        decision_model_factory=factory, decision_model_id="scripted_test",
    )
    created = _create(service)
    outcome = []
    thread = threading.Thread(target=lambda: outcome.append(_run(service, created.run_id)))
    thread.start()
    assert entered.wait(5)
    contender = _run(service, created.run_id)
    assert contender.state == "running" and made == [1]
    release.set()
    thread.join(5)
    assert not thread.is_alive()
    assert calls == ["read_document"] and len(made) == 1
    assert outcome[0].state == "failed"  # fake exhausts on its next decision


def test_queued_and_running_cancellation_are_revision_safe(tmp_path):
    service, _, _, _, _ = _service(tmp_path / "queued")
    queued = _create(service)
    cancelled = service.cancel(queued.run_id, expected_revision=queued.revision)
    assert cancelled.state == "cancelled" and cancelled.step.state == "cancelled"
    assert _run(service, queued.run_id).state == "cancelled"
    with pytest.raises(JobConflictError):
        service.cancel(queued.run_id, expected_revision=queued.revision)
    assert service.cancel(queued.run_id, expected_revision=cancelled.revision).revision == cancelled.revision

    entered = threading.Event()
    release = threading.Event()

    class WaitingModel:
        requires_provider = True

        async def decide(self, _request):
            entered.set()
            await asyncio.to_thread(release.wait)
            return _tool("read_document", document_id=DOC)

    service, _, calls, _, body = _service(
        tmp_path / "running", model_factory=lambda _identity: WaitingModel(),
    )
    body.allow_decision_provider_execution = True
    active = _create(service, body)
    done = []
    thread = threading.Thread(target=lambda: done.append(_run(service, active.run_id)))
    thread.start()
    assert entered.wait(5)
    current = service.get(active.run_id)
    requested = service.cancel(active.run_id, expected_revision=current.revision)
    assert requested.state == "cancelling" and requested.finished_at is None
    assert calls == []
    with pytest.raises(JobConflictError):
        service.cancel(active.run_id, expected_revision=current.revision)
    repeated = service.cancel(active.run_id, expected_revision=requested.revision)
    assert repeated.revision == requested.revision
    release.set()
    thread.join(5)
    assert not thread.is_alive()
    assert done[0].state == "cancelled" and done[0].result.agent_status == "cancelled"
    assert calls == []


def test_restart_marks_active_run_interrupted_without_replay(tmp_path):
    service, repo, calls, model, _ = _service(tmp_path)
    created = _create(service)
    job = repo.get_job("job_" + created.run_id[6:])
    running = repo.transition_job(job.job_id, expected_revision=job.revision, target_state="running")
    repo.transition_step(job.job_id, running.steps[0].step_id,
                         expected_job_revision=running.revision,
                         expected_step_revision=running.steps[0].revision, target_state="running")
    reopened = SQLiteJobRepository(WorkspaceDatabase(repo.database.path))
    recovered = reopened.recover_interrupted_jobs()
    assert len(recovered) == 1 and recovered[0].state == "interrupted"
    assert recovered[0].steps[0].state == "interrupted"
    assert service.get(created.run_id).frozen.goal == "Find relevant risk evidence."
    assert _run(service, created.run_id).state == "interrupted"
    assert calls == [] and model.requests == []
    assert service.events(created.run_id, after_sequence=0)[-1].event_type == "interrupted"


class SimulatedProcessCrash(BaseException):
    pass


def test_crash_after_claim_before_orchestrator_has_no_replay(tmp_path):
    service, repo, calls, model, _ = _service(tmp_path)
    created = _create(service)
    service.registry_factory = lambda: (_ for _ in ()).throw(SimulatedProcessCrash())
    with pytest.raises(SimulatedProcessCrash):
        _run(service, created.run_id)
    assert service.get(created.run_id).state == "running"
    assert calls == [] and model.requests == []
    assert repo.recover_interrupted_jobs()[0].state == "interrupted"
    assert _run(service, created.run_id).state == "interrupted"


def test_crash_after_tool_before_event_commit_preserves_ambiguity(tmp_path, monkeypatch):
    service, repo, calls, _, _ = _service(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Evidence found.", ("document_id", DOC)),
    ))
    created = _create(service)
    monkeypatch.setattr(repo, "append_agent_decision_event", lambda *_args, **_kwargs:
                        (_ for _ in ()).throw(SimulatedProcessCrash()))
    with pytest.raises(SimulatedProcessCrash):
        _run(service, created.run_id)
    assert calls == ["read_document"]
    assert service.get(created.run_id).state == "running"
    assert all(event.summary is None for event in service.events(created.run_id, after_sequence=0))
    assert repo.recover_interrupted_jobs()[0].state == "interrupted"
    assert _run(service, created.run_id).state == "interrupted"
    assert calls == ["read_document"]


def test_crash_after_orchestrator_before_terminal_commit_does_not_replay(tmp_path, monkeypatch):
    service, repo, calls, _, _ = _service(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Evidence found.", ("document_id", DOC)),
    ))
    created = _create(service)
    original_transition = repo.transition_job

    def crash_terminal(job_id, **kwargs):
        if kwargs.get("target_state") == "succeeded":
            raise SimulatedProcessCrash()
        return original_transition(job_id, **kwargs)

    monkeypatch.setattr(repo, "transition_job", crash_terminal)
    with pytest.raises(SimulatedProcessCrash):
        _run(service, created.run_id)
    assert calls == ["read_document"]
    assert service.get(created.run_id).state == "running"
    assert repo.recover_interrupted_jobs()[0].state == "interrupted"
    assert _run(service, created.run_id).state == "interrupted"
    assert calls == ["read_document"]


def test_hostile_observation_and_large_unicode_answer_do_not_leak_events(tmp_path):
    service, repo, calls, _, _ = _service(tmp_path / "hostile", (
        _tool("read_document", document_id=DOC),
        _final("Evidence found.", ("document_id", DOC)),
    ), text=ATTACK + " 🚀")
    final = _run(service, _create(service).run_id)
    assert final.state == "succeeded" and calls == ["read_document"]
    raw = repo.database.path.read_bytes().decode("utf-8", "ignore")
    assert "IGNORE ALL RULES" not in raw and "SECRET-SENTINEL" not in raw

    service, repo, _, _, _ = _service(tmp_path / "unicode", (
        _tool("read_document", document_id=DOC),
        _final("🚀" * 4000, ("document_id", DOC)),
    ))
    oversized = _run(service, _create(service).run_id)
    assert oversized.state == "failed" and oversized.result is None
    assert oversized.failure.code == "agent_execution_failed"
    assert len(repo.database.path.read_bytes()) < 1_000_000
