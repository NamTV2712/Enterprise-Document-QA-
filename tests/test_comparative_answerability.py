from src.generation.answer_completion import (
    answer_completion_requires_buffering,
    correct_answer_once,
)
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_FINGERPRINT,
    assess_comparative_answerability,
)
from src.retrieval.query_normalizer import detect_ticker, detect_tickers


QUESTION = "Which company depends more on cloud/subscription revenue, Microsoft or Apple?"
CONTEXT = """[Source 1] MSFT 10-K, MD&A
Microsoft Cloud revenue increased 23% to $168.9 billion. Microsoft generates revenue from cloud-based solutions and services.

[Source 2] AAPL 10-K, MD&A
Services net sales were 109,158 million. Services net sales include higher net sales from advertising, the App Store and cloud services.
"""
FALLBACK = (
    "I could not find sufficient information in the available documents "
    "to answer this question with confidence."
)


def test_detect_tickers_preserves_question_order() -> None:
    assert detect_tickers(QUESTION) == ("MSFT", "AAPL")
    assert detect_ticker(QUESTION) is None


def test_balanced_comparative_evidence_is_answerable() -> None:
    assessment = assess_comparative_answerability(QUESTION, CONTEXT, FALLBACK)

    assert assessment.applicable is True
    assert assessment.expected_tickers == ("MSFT", "AAPL")
    assert assessment.evidenced_tickers == ("MSFT", "AAPL")
    assert assessment.missing_tickers == ()
    assert assessment.evidence_sufficient is True
    assert assessment.draft_is_fallback is True
    assert assessment.retry_required is True
    assert assessment.numeric_evidence_by_ticker == {"MSFT": True, "AAPL": True}
    assert assessment.requires_buffering is True
    assert COMPARATIVE_ANSWERABILITY_FINGERPRINT.startswith("sha256:")


def test_one_sided_comparative_evidence_stays_safe_fallback() -> None:
    context = """[Source 1] MSFT 10-K, MD&A
Microsoft Cloud revenue increased 23% to $168.9 billion.
"""

    assessment = assess_comparative_answerability(QUESTION, context, FALLBACK)

    assert assessment.applicable is True
    assert assessment.evidence_sufficient is False
    assert assessment.missing_tickers == ("AAPL",)
    assert assessment.retry_required is False
    assert assessment.passed is True
    assert answer_completion_requires_buffering(QUESTION, context) is False


def test_unknown_companies_do_not_trigger_comparative_retry() -> None:
    question = "Which company depends more on streaming revenue, Netflix or Disney?"
    assessment = assess_comparative_answerability(question, CONTEXT, FALLBACK)

    assert assessment.applicable is False
    assert assessment.retry_required is False
    assert answer_completion_requires_buffering(question, CONTEXT) is False


def test_answerable_fallback_gets_one_grounded_correction() -> None:
    calls: list[str] = []
    corrected = (
        "Microsoft Cloud revenue increased 23% to $168.9 billion [Source 1]. "
        "Apple Services net sales were 109,158 million and include cloud "
        "services [Source 2]. Microsoft depends more on cloud revenue as a "
        "core business driver than Apple depends on Services."
    )

    result = correct_answer_once(
        QUESTION,
        CONTEXT,
        FALLBACK,
        lambda prompt: calls.append(prompt) or corrected,
    )

    assert len(calls) == 1
    assert "balanced" in calls[0]
    assert result.initial.answerability.retry_required is True
    assert result.correction_attempted is True
    assert result.correction_accepted is True
    assert result.final.answerability.passed is True
    assert result.final.grounding_passed is True
    assert result.answer == corrected


def test_answerable_fallback_with_invalid_correction_remains_fallback() -> None:
    result = correct_answer_once(
        QUESTION,
        CONTEXT,
        FALLBACK,
        lambda _prompt: "Microsoft depends more on cloud revenue.",
    )

    assert result.correction_attempted is True
    assert result.correction_accepted is False
    assert result.answer == FALLBACK
