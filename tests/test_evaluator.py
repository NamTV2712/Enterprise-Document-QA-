from types import SimpleNamespace

from src.evaluation.evaluator import (
    JUDGE_CONTEXT_CHARS_PER_CHUNK,
    RAGEvaluator,
    compute_recall_proxy,
    _extract_relevant_window,
)


def test_judge_prompt_includes_evidence_beyond_old_250_character_preview() -> None:
    captured = {}
    evaluator = RAGEvaluator(SimpleNamespace(provider="fake"))

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
