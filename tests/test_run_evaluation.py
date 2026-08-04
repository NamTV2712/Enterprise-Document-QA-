import json
from types import SimpleNamespace

from scripts import run_evaluation
from src.evaluation.evaluator import JudgeParseError, RAGEvaluator
from src.evaluation.test_set import TestCase as EvaluationTestCase
from src.generation.query_decomposer import DecomposedResponse


def test_load_checkpoint_only_returns_selected_successes(tmp_path, monkeypatch):
    checkpoint = tmp_path / "checkpoint.jsonl"
    records = [
        {"question": "selected", "status": "OK"},
        {"question": "not selected", "status": "OK"},
        {"question": "failed", "status": "SKIPPED_QUOTA"},
    ]
    checkpoint.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    monkeypatch.setattr(run_evaluation, "CHECKPOINT_PATH", checkpoint)

    assert run_evaluation.load_checkpoint({"selected", "failed"}) == {
        "selected": records[0]
    }


def test_network_error_still_retries_and_returns_failure_for_quota_skip(monkeypatch):
    attempts = 0

    def fail_with_network_error():
        nonlocal attempts
        attempts += 1
        raise ConnectionError("provider unavailable")

    monkeypatch.setattr(run_evaluation, "RETRY_BACKOFF_SECONDS", [0, 0])

    result, error = run_evaluation.call_with_capped_retry(fail_with_network_error)

    assert result is None
    assert error == "provider unavailable"
    assert attempts == run_evaluation.MAX_RETRIES + 1
    assert run_evaluation._judge_failure_status(error) == "JUDGE_SKIPPED_QUOTA"


def test_judge_parse_error_does_not_retry_and_reports_invalid(monkeypatch):
    attempts = 0

    def fail_with_parse_error():
        nonlocal attempts
        attempts += 1
        raise JudgeParseError("invalid schema")

    monkeypatch.setattr(run_evaluation, "RETRY_BACKOFF_SECONDS", [0, 0])

    result, error = run_evaluation.call_with_capped_retry(fail_with_parse_error)

    assert result is None
    assert attempts == 1
    assert run_evaluation._judge_failure_status(error) == "JUDGE_PARSE_INVALID"


def test_valid_judge_json_still_produces_ok_status():
    evaluator = RAGEvaluator(SimpleNamespace())
    evaluator._call_judge = lambda prompt: json.dumps(
        {
            "faithfulness": 1.0,
            "faithfulness_reason": "grounded",
            "answer_relevancy": 0.9,
            "relevancy_reason": "relevant",
            "context_precision": 0.8,
            "precision_reason": "precise",
        }
    )
    judge_scores = evaluator.evaluate_one(
        question="test question",
        answer="test answer",
        chunks=[],
        ground_truth="test ground truth",
    )
    test_case = EvaluationTestCase(
        question="test question",
        category="fact_lookup",
        ticker=None,
        section=None,
        ground_truth="test ground truth",
    )
    response = DecomposedResponse(
        answer="test answer",
        sub_queries=[],
        all_chunks=[],
        model_used="fake-model",
        was_decomposed=False,
    )

    record = run_evaluation._record_success(
        test_case,
        response,
        judge_scores,
        latency=0.1,
    )

    assert record["status"] == "OK"
    assert record["faithfulness"] == 1.0
    assert record["answer_relevancy"] == 0.9
    assert record["context_precision"] == 0.8
