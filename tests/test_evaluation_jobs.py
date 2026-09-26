"""Hermetic frozen EVAL-003 lifecycle, budget, and recovery checks."""

from __future__ import annotations

import hashlib
import asyncio
import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
import httpx
from fastapi import FastAPI
from pydantic import SecretStr

from src.api import access
from src.api.routers.evaluation_jobs import create_evaluation_job_router

from src.evaluation.frozen_job_plan import FrozenPlanError, assert_runtime_binding, freeze_plan, registered_artifact_bytes
from src.evaluation import frozen_job_plan
from src.evaluation.job_service import EvaluationJobService
from src.evaluation import job_service as job_service_module
from src.evaluation.native_protocol import NativeProtocolError
from src.evaluation.job_store import EvaluationBudgetExhausted, EvaluationStoreError
from src.evaluation.retrieval_artifact import canonical_json
from src.evaluation.test_set import TEST_SET
from src.workspace.database import WorkspaceDatabase
from src.workspace.jobs import SQLiteJobRepository
from src.workspace.jobs import JobConflictError


METRICS = [
    "native.faithfulness", "native.answer_relevancy", "native.context_precision",
    "native.citation_index_validity", "native.keyword_recall_proxy", "native.fallback_correctness",
]


def _artifact() -> bytes:
    source = TEST_SET[0]
    payload = {
        "schema_version": 2,
        "plans": [],
        "cases": [{
            "question": source.question, "category": source.category, "route": "direct",
            "expects_fallback": source.expects_fallback,
            "required_keywords": source.required_keywords,
            "ground_truth": source.ground_truth,
            "queries": [{"query": {"text": source.question}, "chunks": [{
                "chunk_id": "synthetic-1", "citation": "Synthetic filing",
                "text": "Apple total net sales fiscal 2024 were 391,035 million.",
            }]}],
            "final_chunk_ids": ["synthetic-1"],
        }],
        "fingerprints": {
            "retrieval_config": "sha256:" + "1" * 64,
            "embedding": "sha256:" + "2" * 64,
            "reranker": "sha256:" + "3" * 64,
        },
    }
    payload["fingerprints"]["artifact"] = "sha256:" + hashlib.sha256(canonical_json(payload)).hexdigest()
    return canonical_json(payload)


def _service(tmp_path, *, generate=None, judge=None):
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    database.initialize()
    repo = SQLiteJobRepository(database)
    calls = {"generation": 0, "judging": 0}

    def gen(_prompt):
        calls["generation"] += 1
        return (generate(_prompt) if generate else
                "Apple's total net sales in fiscal 2024 were 391,035 million [Source 1].")

    def jdg(_prompt):
        calls["judging"] += 1
        return judge(_prompt) if judge else {
            "faithfulness": 0.0, "answer_relevancy": 1.0, "context_precision": 0.5,
        }

    service = EvaluationJobService(
        repo, artifact_loader=lambda _id: _artifact(),
        provider_factory=lambda _model: (gen, jdg),
    )
    return service, calls


def _create(service, *, key="same", budget=3):
    return service.create(
        artifact_id="synthetic", engine="native", metrics=METRICS,
        mode="provider_backed", budget=budget, idempotency_key=key,
    )


def test_frozen_plan_and_preflight(tmp_path):
    content = _artifact()
    first = freeze_plan("synthetic", content, 3)
    assert first == freeze_plan("synthetic", content, 3)
    assert first["budget_unit"] == "provider_attempt_slot"
    assert first["maximum_required_attempts"] == 3
    assert first["binding"]["dataset_revision"].startswith("sha256:")
    assert first["metric_versions"] == {item: 1 for item in METRICS}
    assert "api_key" not in str(first).lower()
    assert_runtime_binding(first)
    with pytest.raises(FrozenPlanError):
        freeze_plan("synthetic", content, 2)
    modified = dict(first, judge_max_tokens=1)
    with pytest.raises(FrozenPlanError):
        assert_runtime_binding(modified)


def test_dataset_change_after_freeze_does_not_change_execution(tmp_path, monkeypatch):
    service, _ = _service(tmp_path)
    job = _create(service)
    original_revision = job.payload["binding"]["dataset_revision"]
    monkeypatch.setattr(frozen_job_plan, "TEST_SET", [])
    service.run(job.job_id)
    ended = service.get(job.job_id)
    assert ended["state"] == "succeeded"
    assert ended["frozen"]["binding"]["dataset_revision"] == original_revision


def test_idempotent_replay_uses_original_snapshot_after_source_change(tmp_path, monkeypatch):
    service, _ = _service(tmp_path)
    job = _create(service)
    service.artifact_loader = lambda _id: pytest.fail("re-read mutable artifact")
    monkeypatch.setattr(frozen_job_plan, "TEST_SET", [])
    replay = service.create(
        artifact_id="synthetic", engine="native", metrics=list(reversed(METRICS)),
        mode="provider_backed", budget=3, idempotency_key="same",
    )
    assert replay.job_id == job.job_id and replay.payload == job.payload


def test_conflicting_idempotency_reuse_and_queued_cancel(tmp_path):
    service, _ = _service(tmp_path)
    job = _create(service, key="shared")
    with pytest.raises(JobConflictError):
        _create(service, key="shared", budget=4)
    cancelled = service.cancel(job.job_id, expected_revision=job.revision)
    assert cancelled["state"] == "cancelled"
    service.run(job.job_id)
    assert service.store.attempted_count(job.job_id) == 0


def test_concurrent_equivalent_creation_has_one_durable_identity(tmp_path):
    service, _ = _service(tmp_path)
    barrier = threading.Barrier(3)

    def create():
        barrier.wait()
        return _create(service).job_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
        barrier.wait()
        assert len({future.result() for future in futures}) == 1
    assert service.list(state=None, page=1, page_size=50)["total"] == 1


def test_private_artifact_rejects_credentials_and_paths(tmp_path, monkeypatch):
    service, _ = _service(tmp_path)
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr("escaped-secret-token-0123456789"))
    with pytest.raises(EvaluationStoreError):
        service.store.register_artifact(b'{"value":"escaped-secret-\\u0074oken-0123456789"}')
    with pytest.raises(EvaluationStoreError):
        service.store.register_artifact(b'{"api_key":"unknown-credential"}')
    with pytest.raises(EvaluationStoreError):
        service.store.register_artifact(b'{"metadata":{"api_key":"hidden"},"metadata":{}}')
    with pytest.raises(FrozenPlanError):
        registered_artifact_bytes("../outside", directory=tmp_path)
    with pytest.raises(FrozenPlanError):
        registered_artifact_bytes("C:\\private", directory=tmp_path)


def test_duplicate_phase_and_unknown_case_cannot_spend(tmp_path):
    service, _ = _service(tmp_path)
    job = _create(service)
    service.repository.transition_job(job.job_id, expected_revision=job.revision, target_state="running")
    identifier = job.payload["case_ids"][0]
    service.store.reserve_attempt(job.job_id, identifier, "generation")
    with pytest.raises(EvaluationStoreError):
        service.store.reserve_attempt(job.job_id, identifier, "generation")
    with pytest.raises(EvaluationStoreError):
        service.store.reserve_attempt(job.job_id, "unknown", "judging")
    assert service.store.attempted_count(job.job_id) == 1


def test_native_job_success_and_idempotency(tmp_path):
    service, calls = _service(tmp_path)
    queued = _create(service)
    assert queued.state == "queued"
    assert _create(service).job_id == queued.job_id
    service.run(queued.job_id)
    completed = service.get(queued.job_id)
    assert completed["state"] == "succeeded", completed
    assert completed["progress"]["current"] == 1
    assert completed["budget_consumed"] <= 3
    assert calls["generation"] + calls["judging"] == completed["budget_consumed"]
    assert completed["report_digest"].startswith("sha256:")
    page = service.results(queued.job_id, page=1, page_size=50)
    assert page["total"] == 1
    assert page["items"][0]["metrics"][0]["value"] == 0.0
    assert service.store.report(queued.job_id).status == "complete"
    service.run(queued.job_id)
    assert calls["generation"] + calls["judging"] == completed["budget_consumed"]


def test_frozen_multi_case_order_and_partial_failure_preserve_completed_case(tmp_path):
    payload = json.loads(_artifact())
    second = copy.deepcopy(payload["cases"][0])
    source = TEST_SET[1]
    second.update(
        question=source.question, category=source.category, ground_truth=source.ground_truth,
        required_keywords=source.required_keywords, expects_fallback=source.expects_fallback,
    )
    second["queries"][0]["chunks"][0].update(chunk_id="synthetic-2", text=source.ground_truth)
    second["final_chunk_ids"] = ["synthetic-2"]
    payload["cases"] = [second, payload["cases"][0]]
    del payload["fingerprints"]["artifact"]
    payload["fingerprints"]["artifact"] = "sha256:" + hashlib.sha256(canonical_json(payload)).hexdigest()
    seen = []

    def judge(prompt):
        seen.append(next(case["question"] for case in payload["cases"] if case["question"] in prompt))
        if len(seen) == 2:
            raise RuntimeError("second case provider failure")
        return {"faithfulness": 0.0, "answer_relevancy": 1.0, "context_precision": 0.5}

    service, calls = _service(tmp_path, judge=judge)
    service.artifact_loader = lambda _id: canonical_json(payload)
    job = _create(service, budget=6)
    service.run(job.job_id)
    assert seen == [case["question"] for case in payload["cases"]]
    assert service.get(job.job_id)["state"] == "failed"
    results = service.results(job.job_id, page=1, page_size=50)
    assert results["total"] == 1 and results["items"][0]["case_id"] == job.payload["case_ids"][0]
    assert service.store.report(job.job_id) is None
    used = sum(calls.values())
    service.run(job.job_id)
    assert sum(calls.values()) == used == service.store.attempted_count(job.job_id)


def test_budget_reservation_is_atomic_and_restart_safe(tmp_path):
    service, _ = _service(tmp_path)
    queued = _create(service)
    running = service.repository.transition_job(
        queued.job_id, expected_revision=queued.revision, target_state="running",
    )
    identifier = running.payload["case_ids"][0]
    service.store.reserve_attempt(running.job_id, identifier, "generation")
    service.store.reserve_attempt(running.job_id, identifier, "correction")
    barrier = threading.Barrier(3)

    def spend():
        barrier.wait()
        try:
            return service.store.reserve_attempt(running.job_id, identifier, "judging")
        except EvaluationBudgetExhausted:
            return "exhausted"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(spend) for _ in range(2)]
        barrier.wait()
        results = [future.result() for future in futures]
    assert sorted(map(str, results)) == ["3", "exhausted"]
    assert service.store.attempted_count(running.job_id) == 3
    reopened = SQLiteJobRepository(WorkspaceDatabase(tmp_path / "workspace.sqlite3"))
    recovered = reopened.recover_interrupted_jobs()
    assert len(recovered) == 1 and recovered[0].state == "interrupted"
    assert EvaluationJobService(reopened).store.attempted_count(running.job_id) == 3
    assert EvaluationJobService(reopened).get(running.job_id)["frozen"] == running.payload


def test_cancel_after_inflight_attempt_preserves_receipt(tmp_path):
    entered = threading.Event()
    release = threading.Event()

    def generate(_prompt):
        entered.set()
        assert release.wait(10)
        return "Apple's total net sales in fiscal 2024 were 391,035 million [Source 1]."

    service, calls = _service(tmp_path, generate=generate)
    queued = _create(service)
    with ThreadPoolExecutor(max_workers=1) as pool:
        worker = pool.submit(service.run, queued.job_id)
        assert entered.wait(10)
        current = service.get(queued.job_id)
        cancelling = service.cancel(queued.job_id, expected_revision=current["revision"])
        assert cancelling["state"] == "cancelling"
        release.set()
        worker.result(timeout=10)
    ended = service.get(queued.job_id)
    assert ended["state"] == "cancelled"
    assert ended["budget_consumed"] == 1
    assert calls["judging"] == 0


def test_provider_failure_is_sanitized_and_consumed(tmp_path):
    def fail(_prompt):
        raise RuntimeError("Authorization: Bearer secret-provider-reply")

    service, _ = _service(tmp_path, generate=fail)
    job = _create(service)
    service.run(job.job_id)
    ended = service.get(job.job_id)
    assert ended["state"] == "failed"
    assert ended["failure"]["code"] == "provider_failure"
    assert "secret-provider" not in str(ended)
    assert ended["budget_consumed"] == 1
    assert service.results(job.job_id, page=1, page_size=50)["total"] == 0


def test_cancellation_wins_terminal_failure_revision_race(tmp_path, monkeypatch):
    def fail(_prompt):
        raise RuntimeError("synthetic provider failure")

    service, _ = _service(tmp_path, generate=fail)
    job = _create(service)
    original = service.repository.transition_job
    raced = False

    def transition(job_id, **kwargs):
        nonlocal raced
        if kwargs["target_state"] == "failed" and not raced:
            raced = True
            current = service.repository.get_job(job_id)
            service.repository.request_cancellation(job_id, expected_revision=current.revision)
        return original(job_id, **kwargs)

    monkeypatch.setattr(service.repository, "transition_job", transition)
    service.run(job.job_id)
    assert raced and service.get(job.job_id)["state"] == "cancelled"
    assert service.store.attempted_count(job.job_id) == 1


def test_false_native_value_is_computed_not_missing(tmp_path):
    service, _ = _service(tmp_path, generate=lambda _prompt: "I could not find sufficient information in the filings.")
    job = _create(service)
    service.run(job.job_id)
    assert service.get(job.job_id)["state"] == "succeeded"
    metrics = service.results(job.job_id, page=1, page_size=50)["items"][0]["metrics"]
    fallback = next(row for row in metrics if row["metric_id"] == "native.fallback_correctness")
    assert fallback["status"] == "computed" and fallback["value"] is False


def test_invalid_judge_scores_fail_without_fabricated_metrics(tmp_path):
    service, _ = _service(tmp_path, judge=lambda _prompt: {
        "faithfulness": 99, "answer_relevancy": 1, "context_precision": 1,
    })
    job = _create(service)
    service.run(job.job_id)
    assert service.get(job.job_id)["failure"]["code"] == "case_failure"
    assert service.results(job.job_id, page=1, page_size=50)["total"] == 0


def test_report_validation_failure_is_explicit(tmp_path, monkeypatch):
    service, _ = _service(tmp_path)
    job = _create(service)

    def reject(*_args):
        raise NativeProtocolError("synthetic report rejection")

    monkeypatch.setattr(job_service_module, "build_native_report", reject)
    service.run(job.job_id)
    assert service.get(job.job_id)["failure"]["code"] == "report_validation_failure"
    assert service.results(job.job_id, page=1, page_size=50)["total"] == 1
    assert service.store.report(job.job_id) is None


def test_budget_exhaustion_is_distinct_from_provider_failure(tmp_path):
    service, _ = _service(tmp_path)
    job = _create(service)

    def exhausted_factory(_model):
        for phase in ("generation", "correction", "judging"):
            service.store.reserve_attempt(job.job_id, job.payload["case_ids"][0], phase)
        return (lambda _prompt: pytest.fail("unbudgeted provider call"),
                lambda _prompt: pytest.fail("unbudgeted judge call"))

    service.provider_factory = exhausted_factory
    service.run(job.job_id)
    ended = service.get(job.job_id)
    assert ended["state"] == "failed"
    assert ended["failure"]["code"] == "budget_exhausted"
    assert ended["budget_consumed"] == 3


def test_aggregate_failure_preserves_case_and_no_partial_report(tmp_path, monkeypatch):
    service, _ = _service(tmp_path)
    job = _create(service)

    def fail_report(_job_id, _report):
        raise OSError("private database unavailable")

    monkeypatch.setattr(service.store, "commit_report", fail_report)
    service.run(job.job_id)
    ended = service.get(job.job_id)
    assert ended["state"] == "failed"
    assert ended["failure"]["code"] == "infrastructure_failure"
    assert service.results(job.job_id, page=1, page_size=50)["total"] == 1
    assert service.store.report(job.job_id) is None


@pytest.mark.parametrize("boundary", ["case", "report"])
def test_crash_after_durable_result_recovers_without_replay(tmp_path, monkeypatch, boundary):
    class SimulatedCrash(BaseException):
        pass

    service, calls = _service(tmp_path)
    job = _create(service)
    operation = service.store.commit_case if boundary == "case" else service.store.commit_report

    def crash(*args):
        operation(*args)
        raise SimulatedCrash

    monkeypatch.setattr(service.store, "commit_case" if boundary == "case" else "commit_report", crash)
    with pytest.raises(SimulatedCrash):
        service.run(job.job_id)
    spent = service.store.attempted_count(job.job_id)
    assert service.repository.get_job(job.job_id).state == "running"
    reopened = SQLiteJobRepository(WorkspaceDatabase(tmp_path / "workspace.sqlite3"))
    reopened.recover_interrupted_jobs()
    recovered = EvaluationJobService(reopened)
    assert recovered.get(job.job_id)["state"] == "interrupted"
    assert recovered.results(job.job_id, page=1, page_size=50)["total"] == 1
    assert recovered.store.attempted_count(job.job_id) == spent
    assert (recovered.store.report(job.job_id) is not None) == (boundary == "report")
    service.run(job.job_id)
    assert sum(calls.values()) == spent


def test_only_one_worker_claims_and_calls_provider(tmp_path):
    service, calls = _service(tmp_path)
    job = _create(service)
    barrier = threading.Barrier(3)

    def run():
        barrier.wait()
        service.run(job.job_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run) for _ in range(2)]
        barrier.wait()
        for future in futures:
            future.result()
    assert service.get(job.job_id)["state"] == "succeeded"
    assert calls["generation"] + calls["judging"] == service.store.attempted_count(job.job_id)
    assert calls["judging"] == 1


def test_private_http_access_creation_results_and_events(tmp_path, monkeypatch):
    service, _ = _service(tmp_path)
    app = FastAPI()
    app.include_router(create_evaluation_job_router(lambda: service))
    token = "evaluation-local-token-0123456789"
    monkeypatch.setattr(access.settings, "workspace_mode", "local")
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr(token))
    monkeypatch.setattr(access.settings, "local_workspace_allowed_origins", "http://localhost:3000")
    monkeypatch.setattr(access.settings, "local_workspace_allowed_hosts", "localhost:8000")
    monkeypatch.setattr(access.settings, "enable_workspace_execution", True)
    body = {
        "artifact_id": "synthetic", "engine": "native", "metrics": METRICS,
        "mode": "provider_backed", "budget": 3,
    }
    headers = {
        "Host": "localhost:8000", "Origin": "http://localhost:3000",
        "Authorization": f"Bearer {token}", "Idempotency-Key": "http-test",
    }

    async def request(method, path, *, headers_override=None, peer="127.0.0.1", json_body=None):
        transport = httpx.ASGITransport(app=app, client=(peer, 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
            return await client.request(method, path, headers=headers_override or headers, json=json_body)

    def call(method, path, **kwargs):
        return asyncio.run(request(method, path, **kwargs))

    assert call("GET", "/evaluation/jobs", headers_override={"Host": "localhost:8000"}).status_code == 401
    assert call("POST", "/evaluation/jobs", json_body=body, headers_override={**headers, "Host": "localhost:8001"}).status_code == 403
    assert call("POST", "/evaluation/jobs", json_body=body, headers_override={**headers, "Origin": "http://evil"}).status_code == 403
    assert call("POST", "/evaluation/jobs", json_body=body, peer="203.0.113.9").status_code == 403
    created = call("POST", "/evaluation/jobs", json_body=body)
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    detail = call("GET", f"/evaluation/jobs/{job_id}")
    assert detail.status_code == 200 and detail.json()["state"] == "succeeded"
    assert detail.json()["budget_consumed"] <= 3
    results = call("GET", f"/evaluation/jobs/{job_id}/results")
    assert results.status_code == 200 and results.json()["total"] == 1
    events = call("GET", f"/evaluation/jobs/{job_id}/events")
    assert events.status_code == 200 and "event: created" in events.text
    resumed = call("GET", f"/evaluation/jobs/{job_id}/events", headers_override={**headers, "Last-Event-ID": "1"})
    assert "id: 1\n" not in resumed.text
    assert call("POST", f"/evaluation/jobs/{job_id}/cancel", headers_override=headers).status_code == 428
    monkeypatch.setattr(access.settings, "enable_workspace_execution", False)
    assert call("POST", "/evaluation/jobs", json_body=body).status_code == 403
