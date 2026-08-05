import json
from types import SimpleNamespace

from scripts import run_evaluation
from src.evaluation.evaluator import JudgeParseError, RAGEvaluator
from src.evaluation.test_set import TestCase as EvaluationTestCase
from src.generation.query_decomposer import DecomposedResponse


def _make_test_case(ground_truth: str = "A1") -> EvaluationTestCase:
    return EvaluationTestCase(
        question="Q1",
        category="fact_lookup",
        ticker="AAPL",
        section=None,
        ground_truth=ground_truth,
        required_keywords=[ground_truth],
        expects_fallback=False,
        expects_decomposition=False,
        priority=1,
    )


def _test_fingerprint(
    test_case: EvaluationTestCase,
    generator_model: str = "model-70b",
    judge_model: str = "model-70b",
) -> str:
    return run_evaluation.evaluation_fingerprint(
        test_case,
        generator_model=generator_model,
        judge_model=judge_model,
    )


def _write_checkpoint(tmp_path, monkeypatch, record: dict) -> None:
    checkpoint = tmp_path / "checkpoint.jsonl"
    checkpoint.write_text(json.dumps(record) + "\n", encoding="utf-8")
    monkeypatch.setattr(run_evaluation, "CHECKPOINT_PATH", checkpoint)


def test_load_checkpoint_only_returns_selected_successes(tmp_path, monkeypatch):
    checkpoint = tmp_path / "checkpoint.jsonl"
    records = [
        {"question": "selected", "status": "OK", "fingerprint": "selected-fp"},
        {"question": "not selected", "status": "OK", "fingerprint": "other-fp"},
        {"question": "failed", "status": "SKIPPED_QUOTA", "fingerprint": "failed-fp"},
    ]
    checkpoint.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    monkeypatch.setattr(run_evaluation, "CHECKPOINT_PATH", checkpoint)

    assert run_evaluation.load_checkpoint(
        {"selected": "selected-fp", "failed": "failed-fp"}
    ) == {
        "selected": records[0]
    }


def test_same_question_same_fingerprint_is_reused(tmp_path, monkeypatch):
    test_case = _make_test_case()
    fingerprint = _test_fingerprint(test_case)
    record = {"question": test_case.question, "status": "OK", "fingerprint": fingerprint}
    _write_checkpoint(tmp_path, monkeypatch, record)

    assert run_evaluation.load_checkpoint({test_case.question: fingerprint}) == {
        test_case.question: record
    }


def test_changed_ground_truth_is_not_reused(tmp_path, monkeypatch):
    old_test_case = _make_test_case(ground_truth="Old answer")
    new_test_case = _make_test_case(ground_truth="New corrected answer")
    record = {
        "question": old_test_case.question,
        "status": "OK",
        "fingerprint": _test_fingerprint(old_test_case),
    }
    _write_checkpoint(tmp_path, monkeypatch, record)

    expected = {new_test_case.question: _test_fingerprint(new_test_case)}

    assert run_evaluation.load_checkpoint(expected) == {}


def test_changed_judge_model_is_not_reused(tmp_path, monkeypatch):
    test_case = _make_test_case()
    record = {
        "question": test_case.question,
        "status": "OK",
        "fingerprint": _test_fingerprint(test_case, judge_model="model-8b"),
    }
    _write_checkpoint(tmp_path, monkeypatch, record)

    expected = {
        test_case.question: _test_fingerprint(test_case, judge_model="model-70b")
    }

    assert run_evaluation.load_checkpoint(expected) == {}


def test_legacy_record_without_fingerprint_is_not_reused(tmp_path, monkeypatch):
    test_case = _make_test_case()
    record = {"question": test_case.question, "status": "OK"}
    _write_checkpoint(tmp_path, monkeypatch, record)

    expected = {test_case.question: _test_fingerprint(test_case)}

    assert run_evaluation.load_checkpoint(expected) == {}


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
        fingerprint="test-fingerprint",
    )

    assert record["status"] == "OK"
    assert record["fingerprint"] == "test-fingerprint"
    assert record["faithfulness"] == 1.0
    assert record["answer_relevancy"] == 0.9
    assert record["context_precision"] == 0.8
