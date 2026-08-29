from src.evaluation.answer_contract import audit_answer


def test_canonical_citations_and_numeric_support() -> None:
    result = audit_answer(
        "Revenue was $391,035 million [Source 1].",
        ["Total net sales were $391,035 million in 2024."],
    )
    assert result.canonical_citations == (1,)
    assert result.unsupported_numeric_claims == ()
    assert not result.uncited_answer


def test_line_citation_is_reported_as_malformed_and_missing_canonical() -> None:
    result = audit_answer("Revenue was $10 【1†L1-L3】.", ["Revenue was $10."])
    assert result.malformed_line_citations == 1
    assert result.uncited_answer


def test_out_of_range_and_derived_numbers_are_reviewable() -> None:
    result = audit_answer(
        "It increased by $5 from $10 to $15 [Source 2].",
        ["Revenue was $10 and $15."] ,
    )
    assert result.out_of_range_citations == (2,)
    assert "$5" in result.unsupported_numeric_claims


def test_fallback_does_not_require_citations() -> None:
    result = audit_answer(
        "I could not find sufficient information in the filings.",
        ["Unrelated evidence."],
    )
    assert result.fallback_answer
    assert not result.uncited_answer
