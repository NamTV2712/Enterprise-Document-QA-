import copy
import json

from scripts import run_evidence_contract_v3_campaign as campaign
from scripts.diagnostics.answerability_stability_v1_reproducibility import (
    build_report,
    validate_report,
)
from src.evaluation.request_ledger import RequestLedger


def test_fake_replicate_produces_a_receipt_the_verifier_can_recompute(tmp_path, monkeypatch) -> None:
    artifact = json.loads(campaign.ARTIFACT_PATH.read_text(encoding="utf-8"))
    config = {
        "run_id": "evidence-contract-v3-test",
        "generation": tmp_path / "generation.jsonl",
        "judge": tmp_path / "judge.jsonl",
        "report": tmp_path / "report.json",
    }
    monkeypatch.setitem(campaign.RUN_CONFIG, "r1", config)
    monkeypatch.setattr(campaign, "ARTIFACT_PATH", campaign.ARTIFACT_PATH)
    ledger = RequestLedger(tmp_path / "ledger.jsonl", campaign.CAMPAIGN_ID, 60)

    def fake_generate(question_prompt: str) -> str:
        if "Disney" in question_prompt:
            return "I could not find sufficient information in the available documents to answer this question with confidence."
        return "The supplied evidence is reported above [Source 1]."

    def fake_score(_prompt: str) -> dict[str, float]:
        return {"faithfulness": 1.0, "answer_relevancy": 1.0, "context_precision": 1.0}

    def generate(run_id: str, operation: str, prompt: str) -> str:
        return ledger.call(operation, run_id, campaign.sha256_text(prompt), lambda: {"content": fake_generate(prompt)})["content"]

    def score(run_id: str, operation: str, prompt: str) -> dict[str, float]:
        return ledger.call(operation, run_id, campaign.sha256_text(prompt), lambda: {"scores": fake_score(prompt)})["scores"]

    report = campaign._run_replicate("r1", artifact, ledger, generate, score)

    assert report["passed"] is True
    assert validate_report(report, config["report"]) == ()
    assert ledger.used == 12


def test_v3_verifier_rejects_tampered_answer_score_and_aggregate(tmp_path, monkeypatch) -> None:
    artifact = json.loads(campaign.ARTIFACT_PATH.read_text(encoding="utf-8"))
    config = {
        "run_id": "evidence-contract-v3-test-tamper",
        "generation": tmp_path / "generation.jsonl",
        "judge": tmp_path / "judge.jsonl",
        "report": tmp_path / "report.json",
    }
    monkeypatch.setitem(campaign.RUN_CONFIG, "r1", config)
    ledger = RequestLedger(tmp_path / "ledger.jsonl", campaign.CAMPAIGN_ID, 60)

    def generate(_run_id: str, _operation: str, prompt: str) -> str:
        if "Disney" in prompt:
            return "I could not find sufficient information in the available documents to answer this question with confidence."
        return "Evidence [Source 1]."

    def score(run_id: str, operation: str, prompt: str) -> dict[str, float]:
        return ledger.call(
            operation, run_id, campaign.sha256_text(prompt),
            lambda: {"scores": {"faithfulness": 1.0, "answer_relevancy": 1.0, "context_precision": 1.0}},
        )["scores"]

    def generate_with_ledger(run_id: str, operation: str, prompt: str) -> str:
        return ledger.call(
            operation, run_id, campaign.sha256_text(prompt),
            lambda: {"content": generate(run_id, operation, prompt)},
        )["content"]

    report = campaign._run_replicate("r1", artifact, ledger, generate_with_ledger, score)
    answer_tampered = copy.deepcopy(report)
    answer_tampered["cases"][0]["answer"] += " forged"
    assert any("differs from generation" in error for error in validate_report(answer_tampered, config["report"]))
    score_tampered = copy.deepcopy(report)
    score_tampered["cases"][0]["scores"]["faithfulness"] = 0.5
    assert any("differs from judge" in error for error in validate_report(score_tampered, config["report"]))
    aggregate_tampered = copy.deepcopy(report)
    aggregate_tampered["metrics"]["context_precision"] = 0.5
    assert any("aggregate metrics" in error for error in validate_report(aggregate_tampered, config["report"]))

    duplicate_run = copy.deepcopy(report)
    audit = build_report(report, duplicate_run, config["report"], config["report"])
    assert audit["gates"]["distinct_replicates"] is False
    assert audit["passed"] is False
