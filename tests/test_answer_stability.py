from src.generation.answer_stability import (
    ANSWER_STABILITY_FINGERPRINT,
    assess_answer_stability,
)


CONTEXT = """[Source 1] MSFT 10-K, MD&A
Server products and cloud services revenue increased 23% driven by Azure and other cloud services revenue growth of 34%.
Microsoft Cloud revenue increased 23% to $168.9 billion.
"""
QUESTION = "How does Microsoft describe its Azure and cloud services growth?"


def test_prose_numeric_stability_derives_relevant_exact_facts() -> None:
    result = assess_answer_stability(
        QUESTION,
        CONTEXT,
        "Azure and cloud services revenue grew 23% and 34% [Source 1].",
    )

    assert result.applicable is True
    assert result.kind == "query_anchored_numeric_summary"
    assert [fact.value for fact in result.expected_facts] == [
        "23%",
        "34%",
        "$168.9 billion",
    ]
    assert [fact.value for fact in result.missing_facts] == ["$168.9 billion"]
    assert result.correction_required is True


def test_prose_numeric_stability_accepts_all_exact_facts() -> None:
    result = assess_answer_stability(
        QUESTION,
        CONTEXT,
        "Revenue increased 23% and Azure growth was 34%; Microsoft Cloud "
        "revenue reached $168.9 billion [Source 1].",
    )

    assert result.applicable is True
    assert result.passed is True
    assert result.missing_facts == ()


def test_stability_does_not_treat_years_as_numeric_answer_facts() -> None:
    result = assess_answer_stability(
        "How did AWS sales change from 2024 to 2025?",
        """[Source 1] AMZN 10-K, MD&A
AWS sales increased 20% in 2025, compared to the prior year.
""",
        "AWS sales increased 20% in 2025 [Source 1].",
    )

    assert result.applicable is False


def test_fingerprint_is_content_addressed() -> None:
    assert ANSWER_STABILITY_FINGERPRINT.startswith("sha256:")
    assert len(ANSWER_STABILITY_FINGERPRINT) == 71
