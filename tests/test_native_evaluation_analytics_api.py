"""Public EVAL-002 routes expose safe native facts, not private case text."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest

from src.api.routers import evaluations as router_module
from src.evaluation.dataset_binding import evaluation_dataset_revision
from src.evaluation.native_protocol import NativeCaseInput, NativeReportBinding, build_native_report
from src.evaluation.public_report import example_report, publish_public_report
from src.evaluation.test_set import TEST_SET
from src.retrieval.canonical_json import canonical_json_bytes


CONTEXT = "[Source 1] Synthetic evidence\nRevenue was 10.\n"
CONTEXT_HASH = "sha256:" + hashlib.sha256(CONTEXT.encode()).hexdigest()


def _binding(dataset_revision=None):
    return NativeReportBinding(
        "native", 1, "evaluation-test-set", "evaluation-test-set-v1",
        dataset_revision or evaluation_dataset_revision(TEST_SET),
        "synthetic-model", "sha256:" + "a" * 64, "sha256:" + "b" * 64,
        "sha256:" + "c" * 64, "sha256:" + "d" * 64,
        "sha256:" + "e" * 64, "sha256:" + "f" * 64,
        "sha256:" + "1" * 64, "sha256:" + "2" * 64,
        "synthetic-judge", "sha256:" + "3" * 64,
        "sha256:" + "4" * 64,
    )


def _case(case_id="case-a", faith=0.5, *, answer="Revenue was 10 [Source 1].", judge=True):
    return NativeCaseInput(
        case_id, answer, CONTEXT, "Revenue was 10.", ("10",), False,
        {"native.faithfulness": faith, "native.answer_relevancy": 0.5,
         "native.context_precision": 0.5} if judge else None,
        CONTEXT_HASH, CONTEXT_HASH if judge else None,
        "sha256:" + "c" * 64, "sha256:" + "4" * 64 if judge else None,
    )


def _publish(root: Path, run_id: str, faith=0.5, *, at="2026-01-01T00:00:00Z", cases=None, bind=None):
    report = build_native_report(run_id, cases or [_case(faith=faith)], bind or _binding())
    path = root / f"{run_id}.native.json"
    path.write_bytes(canonical_json_bytes({
        "schema_version": 1, "published_at": at, "report": asdict(report),
    }))
    return path, report


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(router_module.settings, "data_public_evaluations_dir", tmp_path)
    app = FastAPI()
    app.include_router(router_module.create_evaluation_router())
    return TestClient(app)


def test_public_native_list_detail_results_compare_trends_failures_are_safe(client, tmp_path):
    baseline_path, _ = _publish(tmp_path, "baseline", 0.5)
    candidate_path, _ = _publish(tmp_path, "candidate", 0.75, at="2026-02-01T00:00:00Z",
             cases=[_case(faith=0.75, answer="could not find sufficient information [Source 9]")])
    source_bytes = baseline_path.read_bytes(), candidate_path.read_bytes()
    listing = client.get("/evaluation/runs")
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert [item["run_id"] for item in listing.json()["items"]] == ["baseline", "candidate"]
    assert all(item["protocol"] == "native-evaluation" for item in listing.json()["items"])

    detail = client.get("/evaluation/runs/baseline")
    results = client.get("/evaluation/runs/baseline/results", params={"case_id": "case-a"})
    comparison = client.post("/evaluation/compare", json={
        "baseline_run_id": "baseline", "candidate_run_id": "candidate",
        "metric_ids": ["native.faithfulness"],
    })
    trend = client.get("/evaluation/metrics/trends", params={"metric_id": "native.faithfulness"})
    failures = client.get("/evaluation/failures", params={"run_id": "candidate"})
    assert all(response.status_code == 200 for response in (detail, results, comparison, trend, failures))
    assert detail.json()["protocol_version"] == 1
    assert detail.json()["case_count"] == 1
    assert "cases" not in detail.json()
    candidate_case = client.get("/evaluation/runs/candidate/results").json()["items"][0]
    assert candidate_case["metrics"][-1]["value"] is False
    assert results.json()["total"] == 1
    assert results.json()["items"][0]["case_id"] == "case-a"
    assert comparison.json()["metrics"][0]["candidate_minus_baseline"] == 0.25
    assert comparison.json()["eligible_for_complete_comparison"] is True
    assert comparison.json()["metrics"][0]["baseline"]["denominator"] == 1
    assert comparison.json()["total_cases"] == 1
    assert comparison.json()["cases"][0]["metrics"][0]["baseline"]["value"] == 0.5
    assert comparison.json()["cases"][0]["metrics"][0]["candidate"]["value"] == 0.75
    assert next(item for item in comparison.json()["cases"][0]["metrics"] if item["metric_id"] == "native.faithfulness")["status"] == "comparable"
    assert [point["run_id"] for point in trend.json()["groups"][0]["points"]] == ["baseline", "candidate"]
    assert failures.json()["total"] >= 2
    assert (baseline_path.read_bytes(), candidate_path.read_bytes()) == source_bytes
    for response in (listing, detail, results, comparison, trend, failures):
        encoded = response.text
        assert "Revenue was 10" not in encoded
        assert "Synthetic evidence" not in encoded
        assert "[Source" not in encoded
        assert "Authorization" not in response.request.headers


def test_empty_history_and_legacy_are_not_silently_native(client, tmp_path):
    empty = client.get("/evaluation/metrics/trends", params={"metric_id": "native.faithfulness"})
    assert empty.status_code == 200
    assert empty.json()["total_points"] == 0
    publish_public_report(example_report("legacy"), root=tmp_path)
    assert client.get("/evaluation/runs/legacy").json()["schema_version"] == 1
    assert client.get("/evaluation/runs/legacy/results").status_code == 409
    assert client.post("/evaluation/compare", json={
        "baseline_run_id": "legacy", "candidate_run_id": "legacy",
    }).status_code == 409
    assert client.get("/evaluation/failures", params={"run_id": "missing"}).status_code == 404
    assert client.get("/evaluation/runs/../private/results").status_code in {404, 422}


def test_incompatible_corrupt_unknown_filters_and_pagination(client, tmp_path):
    _publish(tmp_path, "baseline")
    path, _ = _publish(tmp_path, "candidate", bind=_binding("sha256:" + "9" * 64))
    mismatch = client.post("/evaluation/compare", json={
        "baseline_run_id": "baseline", "candidate_run_id": "candidate",
    })
    assert mismatch.status_code == 409
    unknown_metric = client.get("/evaluation/metrics/trends", params={"metric_id": "native.missing"})
    assert unknown_metric.status_code == 422
    assert client.get("/evaluation/failures", params={"run_id": "baseline", "category": "hallucination"}).status_code == 422
    assert client.get("/evaluation/runs/baseline/results", params={"page_size": 101}).status_code == 422
    assert client.get("/evaluation/runs/baseline/results", params={"page": 0}).status_code == 422
    assert client.get("/evaluation/runs/baseline/results", params={"sort": "score_desc"}).status_code == 422
    assert client.get("/evaluation/runs/baseline/results", params={"unknown_filter": "x"}).status_code == 422
    assert client.get("/evaluation/failures", params={"run_id": "baseline", "sort": "score_desc"}).status_code == 422
    assert client.get("/evaluation/metrics/trends", params={"metric_id": "native.faithfulness", "sort": "newest"}).status_code == 422
    assert client.post("/evaluation/compare", json={
        "baseline_run_id": "baseline", "candidate_run_id": "candidate", "sort": "score_desc",
    }).status_code == 422
    assert client.get("/evaluation/metrics/trends", params={
        "metric_id": "native.faithfulness", "start_at": "2026-01-01T00:00:00",
    }).status_code == 422
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["report"]["digest"] = "sha256:" + "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert client.get("/evaluation/runs/candidate").status_code == 409
    assert client.get("/evaluation/metrics/trends", params={"metric_id": "native.faithfulness"}).status_code == 409


def test_case_and_failure_pages_preserve_order_and_counts(client, tmp_path):
    _publish(tmp_path, "ordered", cases=[
        _case("case-b", answer="could not find sufficient information [Source 9]"),
        _case("case-a", answer="could not find sufficient information [Source 9]"),
    ])
    first = client.get("/evaluation/runs/ordered/results", params={"page_size": 1, "page": 1})
    second = client.get("/evaluation/runs/ordered/results", params={"page_size": 1, "page": 2})
    assert first.json()["total"] == second.json()["total"] == 2
    assert [first.json()["items"][0]["case_id"], second.json()["items"][0]["case_id"]] == ["case-a", "case-b"]
    findings = client.get("/evaluation/failures", params={
        "run_id": "ordered", "category": "fallback_expectation_mismatch", "page_size": 1,
    })
    assert findings.status_code == 200
    assert findings.json()["total"] == 2
    assert len(findings.json()["items"]) == 1


def test_native_and_legacy_same_id_fail_closed_even_when_filtered(client, tmp_path):
    _publish(tmp_path, "collision")
    publish_public_report(example_report("collision"), root=tmp_path)
    assert client.get("/evaluation/runs", params={"status": "official"}).status_code == 409
    assert client.get("/evaluation/runs/collision").status_code == 409


def test_added_routes_are_public_reads_with_explicit_models_and_names():
    routes = {route.path: route for route in router_module.create_evaluation_router().routes if isinstance(route, APIRoute)}
    expected = {
        "/evaluation/runs/{run_id}/results": "evaluation_run_results",
        "/evaluation/compare": "evaluation_compare",
        "/evaluation/metrics/trends": "evaluation_metric_trends",
        "/evaluation/failures": "evaluation_failures",
    }
    for path, name in expected.items():
        route = routes[path]
        assert route.name == name
        assert route.response_model is not None
        assert route.dependant.dependencies == []
    assert routes["/evaluation/compare"].methods == {"POST"}
    assert all(routes[path].methods == {"GET"} for path in expected if path != "/evaluation/compare")
