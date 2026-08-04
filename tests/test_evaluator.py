import json
from types import SimpleNamespace

import pytest

from src.evaluation.evaluator import (
    JUDGE_CONTEXT_CHARS_PER_CHUNK,
    JudgeParseError,
    RAGEvaluator,
    compute_recall_proxy,
    _extract_relevant_window,
    _parse_judge_response,
)


def test_malformed_judge_json_raises_instead_of_returning_zero_scores() -> None:
    evaluator = RAGEvaluator(SimpleNamespace())
    evaluator._call_judge = lambda prompt: "I cannot evaluate this properly."

    with pytest.raises(JudgeParseError):
        evaluator.evaluate_one(
            question="test question",
            answer="test answer",
            chunks=[],
            ground_truth="test ground truth",
        )


@pytest.mark.parametrize(
    "case",
    [
        "missing_field",
        "unexpected_field",
        "string_score",
        "null_score",
        "out_of_range_score",
        "non_finite_score",
        "null_reason",
        "non_object",
    ],
)
def test_invalid_judge_schema_raises_parse_error(case: str) -> None:
    payload = {
        "faithfulness": 1.0,
        "faithfulness_reason": "grounded",
        "answer_relevancy": 0.9,
        "relevancy_reason": "relevant",
        "context_precision": 0.8,
        "precision_reason": "precise",
    }
    if case == "missing_field":
        payload.pop("context_precision")
    elif case == "unexpected_field":
        payload["extra"] = "unexpected"
    elif case == "string_score":
        payload["faithfulness"] = "1.0"
    elif case == "null_score":
        payload["answer_relevancy"] = None
    elif case == "out_of_range_score":
        payload["context_precision"] = 1.1
    elif case == "non_finite_score":
        payload["faithfulness"] = float("nan")
    elif case == "null_reason":
        payload["precision_reason"] = None

    raw = "[]" if case == "non_object" else json.dumps(payload)

    with pytest.raises(JudgeParseError):
        _parse_judge_response(raw)


def test_judge_prompt_includes_evidence_beyond_old_250_character_preview() -> None:
    captured = {}
    evaluator = RAGEvaluator(SimpleNamespace())

    def fake_call_judge(prompt: str) -> str:
        captured["prompt"] = prompt
        return '{"faithfulness": 1, "faithfulness_reason": "ok", "answer_relevancy": 1, "relevancy_reason": "ok", "context_precision": 1, "precision_reason": "ok"}'

    evaluator._call_judge = fake_call_judge
    context = "x" * 300 + "North America, International, and Amazon Web Services"

    evaluator._judge_all(
        question="What are Amazon's business segments?",
        answer="Amazon operates North America, International, and AWS.",
        context_texts=[context],
        ground_truth="North America, International, and Amazon Web Services.",
    )

    assert JUDGE_CONTEXT_CHARS_PER_CHUNK == 1000
    assert "North America, International" in captured["prompt"]


def test_relevant_window_finds_evidence_beyond_first_1000_chars() -> None:
    """Regression guard for auditor evidence that appears after char 1000."""
    padding = "Some unrelated text about tax positions. " * 40
    evidence = (
        "Ernst & Young LLP audited the financial statements. "
        "Report signed October 31, 2025."
    )
    text = padding + evidence

    result = _extract_relevant_window(
        text,
        query="Who audited Apple's financial statements and when was the report signed?",
        window_chars=1000,
    )

    assert "Ernst & Young" in result
    assert "October 31" in result


def test_relevant_window_falls_back_to_start_when_no_overlap() -> None:
    """If no relevant window is found, preserve the old prefix behavior."""
    text = "Random unrelated content. " * 100

    result = _extract_relevant_window(text, query="Apple revenue 2024", window_chars=1000)

    assert len(result) == 1000
    assert result == text[:1000]


def test_recall_proxy_handles_split_character_artifact() -> None:
    """SEC text may split auditor names across lines, e.g. D\nELOITTE."""
    fake_chunk = SimpleNamespace(
        text="/s/ \nD\nELOITTE\n & T\nOUCHE\n LLP\n\nSeattle, Washington"
    )

    result = compute_recall_proxy(["Deloitte"], [fake_chunk])

    assert result == 1.0


def test_recall_proxy_still_fails_on_truly_missing_keyword() -> None:
    """Compact matching should not make unrelated chunks pass recall checks."""
    fake_chunk = SimpleNamespace(text="This chunk talks about revenue only.")

    result = compute_recall_proxy(["Deloitte"], [fake_chunk])

    assert result == 0.0
