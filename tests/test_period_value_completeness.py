from src.generation.period_value_completeness import (
    FALLBACK_ANSWER,
    assess_period_value_completeness,
    correct_period_value_once,
)


AWS_CONTEXT = """[Source 1] AMZN 10-K
Year Ended December 31,

2024
2025
Net Sales:
North America
387,497
426,305
AWS
107,556
128,725
Consolidated
637,959
716,924

[Source 2] MSFT 10-K
Microsoft Cloud revenue increased 23% to $168.9 billion in fiscal 2025.
"""
AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)


def test_extracts_question_matched_table_period_value_pairs() -> None:
    result = assess_period_value_completeness(
        AWS_QUESTION, AWS_CONTEXT, "AWS grew 20% in 2025 [Source 1]."
    )

    assert result.applicable is True
    assert [(pair.period, pair.value) for pair in result.evidence_pairs] == [
        ("2024", "107,556"),
        ("2025", "128,725"),
    ]
    assert result.missing_pairs == result.evidence_pairs
    assert result.passed is False


def test_qualitative_approach_question_is_not_applicable() -> None:
    result = assess_period_value_completeness(
        "Compare Apple and Microsoft's approach to cloud/services revenue.",
        AWS_CONTEXT,
        "A concise qualitative answer.",
    )

    assert result.applicable is False
    assert result.passed is True


def test_correct_answer_does_not_make_correction_call() -> None:
    calls: list[str] = []
    result = correct_period_value_once(
        AWS_QUESTION,
        AWS_CONTEXT,
        "AWS net sales were 107,556 in 2024 and 128,725 in 2025 [Source 1].",
        lambda prompt: calls.append(prompt) or "unused",
    )

    assert result.correction_attempted is False
    assert result.answer.startswith("AWS net sales")
    assert calls == []


def test_complete_pairs_still_correct_unsupported_derived_numeric_claim() -> None:
    calls: list[str] = []

    def generate(prompt: str) -> str:
        calls.append(prompt)
        return (
            "AWS net sales were 107,556 in 2024 and 128,725 in 2025 "
            "[Source 1]."
        )

    result = correct_period_value_once(
        AWS_QUESTION,
        AWS_CONTEXT,
        (
            "AWS net sales were 107,556 in 2024 and 128,725 in 2025. "
            "The increase was $21,169 [Source 1]."
        ),
        generate,
    )

    assert len(calls) == 1
    assert "$21,169" in calls[0]
    assert result.initial.passed is True
    assert result.initial_grounding_passed is False
    assert result.initial_unsupported_numeric_claims == ("$21,169",)
    assert result.correction_reason == "grounding_violation"
    assert result.correction_accepted is True
    assert "$21,169" not in result.answer


def test_unsupported_numeric_claim_surviving_correction_returns_fallback() -> None:
    calls: list[str] = []
    result = correct_period_value_once(
        AWS_QUESTION,
        AWS_CONTEXT,
        (
            "AWS net sales were 107,556 in 2024 and 128,725 in 2025. "
            "The increase was $21,169 [Source 1]."
        ),
        lambda prompt: calls.append(prompt) or (
            "AWS net sales were 107,556 in 2024 and 128,725 in 2025. "
            "The increase was $21,169 [Source 1]."
        ),
    )

    assert len(calls) == 1
    assert result.answer == FALLBACK_ANSWER
    assert result.correction_accepted is False
    assert result.final_grounding_passed is False
    assert result.final_unsupported_numeric_claims == ("$21,169",)


def test_invalid_draft_gets_exactly_one_grounded_correction() -> None:
    calls: list[str] = []

    def generate(prompt: str) -> str:
        calls.append(prompt)
        return (
            "AWS net sales were 107,556 in 2024 and 128,725 in 2025 "
            "[Source 1]."
        )

    result = correct_period_value_once(
        AWS_QUESTION,
        AWS_CONTEXT,
        "AWS grew 20% [Source 1].",
        generate,
        validate_answer=lambda answer: "[Source 1]" in answer,
    )

    assert len(calls) == 1
    assert "107,556" in calls[0]
    assert result.correction_attempted is True
    assert result.correction_accepted is True
    assert result.final.passed is True


def test_failed_correction_returns_safe_fallback_without_second_call() -> None:
    calls: list[str] = []
    result = correct_period_value_once(
        AWS_QUESTION,
        AWS_CONTEXT,
        "AWS grew 20% [Source 1].",
        lambda prompt: calls.append(prompt) or "AWS grew 20% [Source 1].",
    )

    assert len(calls) == 1
    assert result.answer == FALLBACK_ANSWER
    assert result.correction_accepted is False


def test_generic_total_row_cannot_trigger_period_value_completion() -> None:
    context = """[Source 1] MSFT 10-K
2025
2024
2023
Total
281,724
245,122
211,915
"""

    result = assess_period_value_completeness(
        "How did Microsoft's total assets change year over year?",
        context,
        "",
    )

    assert result.applicable is False
    assert result.evidence_pairs == ()


def test_year_header_is_not_reprocessed_with_shifted_periods() -> None:
    context = """[Source 1] AAPL 10-K
2025
2024
2023
Total net sales
416,161
391,035
383,285
"""

    result = assess_period_value_completeness(
        "How did Apple's total net sales trend from 2023 to 2025?",
        context,
        "",
    )

    assert [(pair.period, pair.value) for pair in result.evidence_pairs] == [
        ("2025", "416,161"),
        ("2024", "391,035"),
        ("2023", "383,285"),
    ]


def test_later_same_label_source_does_not_expand_first_source_contract() -> None:
    context = AWS_CONTEXT + """

[Source 3] AMZN 10-K, operating income
2024
2025
AWS
39,834
45,606
"""

    result = assess_period_value_completeness(AWS_QUESTION, context, "")

    assert [(pair.period, pair.value) for pair in result.evidence_pairs] == [
        ("2024", "107,556"),
        ("2025", "128,725"),
    ]
