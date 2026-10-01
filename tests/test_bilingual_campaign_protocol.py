from __future__ import annotations

import json
from pathlib import Path

from scripts.diagnostics.bilingual_evaluation_manifest import (
    BILINGUAL_CASES,
    MAX_REQUESTS,
    RESERVED_RETRY_BUDGET,
    SENTINEL_REQUESTS,
    build_manifest,
    campaign_output_paths,
    case_records,
    verify_manifest,
)
from scripts.run_bilingual_evaluation_campaign import BASE_REQUESTS, _bounded_call
from src.evaluation.request_ledger import RequestLedger


def test_bilingual_manifest_freezes_ten_language_cases_and_budget() -> None:
    artifact = Path("tests/fixtures/bilingual_artifact_identity.json")
    manifest = build_manifest(artifact, "bilingual_test")
    assert manifest["passed"] is True
    assert len(BILINGUAL_CASES) == 5
    assert len(case_records()) == 10
    assert manifest["provider_protocol"] == {
        "max_requests": 60,
        "calibration_requests": 12,
        "sentinel_requests": SENTINEL_REQUESTS,
        "reserved_retry_budget": RESERVED_RETRY_BUDGET,
        "sdk_retries": 0,
        "explicit_retries_per_logical_operation": 1,
        "unknown_outcome_policy": "INCOMPLETE; start a new campaign after provider authorization",
    }
    assert len(set(campaign_output_paths("bilingual_test"))) == 8


def test_bilingual_manifest_detects_changed_case(tmp_path: Path) -> None:
    artifact = Path("tests/fixtures/bilingual_artifact_identity.json")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(build_manifest(artifact, "bilingual_test")), encoding="utf-8")
    assert verify_manifest(manifest_path, artifact, "bilingual_test") == ()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["cases"][0]["question"] = "tampered"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    assert "manifest field changed: cases" in verify_manifest(manifest_path, artifact, "bilingual_test")


def test_bilingual_retry_reserve_caps_provider_slots(tmp_path: Path) -> None:
    ledger = RequestLedger(tmp_path / "ledger.jsonl", "bilingual_test", MAX_REQUESTS)
    for index in range(BASE_REQUESTS + RESERVED_RETRY_BUDGET):
        ledger.call(f"op-{index}", "run", f"hash-{index}", lambda: {"ok": True})
    try:
        _bounded_call(ledger, lambda: {"ok": True})
    except Exception as error:
        assert "reserved retry budget exhausted" in str(error)
    else:
        raise AssertionError("the 61st request should be rejected")
