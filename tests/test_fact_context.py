from __future__ import annotations

from src.generation.fact_context import (
    FACT_CONTEXT_SELECTOR_FINGERPRINT,
    FACT_CONTEXT_SELECTOR_FINGERPRINT_V2,
    select_fact_context,
    select_fact_context_v2,
    selected_fact_entries,
)


def _chunk(
    chunk_id: str,
    text: str,
    score: float,
    *,
    section: str = "financial_statements",
    ticker: str | None = None,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "citation": f"{chunk_id} citation",
        "text": text,
        "score": score,
        "section": section,
        "ticker": ticker or chunk_id.split("_", 1)[0],
    }


def _case(
    question: str,
    chunks: list[dict],
    *,
    section: str | None = None,
    ticker: str | None = None,
) -> dict:
    return {
        "question": question,
        "category": "fact_lookup",
        "queries": [
            {
                "query": {
                    "effective_query": question,
                    "ticker": ticker or chunks[0]["ticker"],
                    "section": section,
                },
                "chunks": chunks,
            }
        ],
    }


def test_structured_exact_keeps_one_self_contained_chunk() -> None:
    case = _case(
        "What was Microsoft's total assets as of fiscal year 2025?",
        [
            _chunk(
                "MSFT_structured",
                "| Assets - Total assets | 619,003 | 512,163 | 2025 | 2024 |",
                10.0,
                section="financial_table",
                ticker="MSFT",
            ),
            _chunk("MSFT_backup", "Operating income and revenue 2025 2024", 5.0),
        ],
    )

    selection = select_fact_context(case)

    assert selection.tier == "structured_exact"
    assert selection.safe is True
    assert selection.kept_ids == ("MSFT_structured",)
    assert [entry["chunk_id"] for entry in selected_fact_entries(case)] == [
        "MSFT_structured"
    ]


def test_full_terms_finds_lower_ranked_aws_donor() -> None:
    case = _case(
        "What was Amazon's AWS net sales in 2025?",
        [
            _chunk(
                "AMZN_noise",
                "AWS technology and infrastructure costs in 2025",
                4.5,
                section="mdna",
                ticker="AMZN",
            ),
            _chunk(
                "AMZN_donor",
                "Year ended 2024 2025 Net Sales: AWS 107,556 128,725",
                4.0,
                section="mdna",
                ticker="AMZN",
            ),
        ],
        section="mdna",
        ticker="AMZN",
    )

    selection = select_fact_context(case)

    assert selection.tier in {"exact_phrase", "full_terms"}
    assert selection.safe is True
    assert selection.kept_ids == ("AMZN_donor",)


def test_partial_and_fuzzy_matches_never_remove_context() -> None:
    case = _case(
        "What was Microsoft's total assets as of fiscal year 2025?",
        [
            _chunk("MSFT_partial", "assets and 2025 discussion", 4.0),
            _chunk("MSFT_other", "asset commentary", 3.0),
        ],
    )

    selection = select_fact_context(case)

    assert selection.safe is False
    assert selection.kept_ids == selection.all_ids
    assert selection.tier in {
        "partial_terms_support_only",
        "fuzzy_diagnostic_only",
        "no_safe_candidate",
    }


def test_entity_and_section_scope_are_required() -> None:
    case = _case(
        "What was Amazon's AWS net sales in 2025?",
        [
            _chunk(
                "MSFT_wrong",
                "AWS net sales 2025 128,725",
                10.0,
                section="mdna",
                ticker="MSFT",
            ),
            _chunk(
                "AMZN_wrong_section",
                "AWS net sales 2025 128,725",
                9.0,
                section="financial_statements",
                ticker="AMZN",
            ),
        ],
        section="mdna",
        ticker="AMZN",
    )

    selection = select_fact_context(case)

    assert selection.safe is False
    assert selection.kept_ids == selection.all_ids


def test_v2_ignores_possessive_owner_and_plural_year_scaffolding() -> None:
    case = _case(
        "What were Chevron's total assets in fiscal years 2025 and 2024?",
        [
            _chunk(
                "CVX_exact",
                "| Assets - Total Assets | 324,012 | 256,938 | 2025 | 2024 |",
                10.0,
                section="financial_table",
                ticker="CVX",
            ),
            _chunk(
                "CVX_backup",
                "Capital employed 2025 2024 2023",
                4.0,
                section="financial_table",
                ticker="CVX",
            ),
        ],
        section="financial_table",
        ticker="CVX",
    )

    v1 = select_fact_context(case)
    v2 = select_fact_context_v2(case)

    assert v1.safe is False
    assert v2.tier == "structured_exact"
    assert v2.safe is True
    assert v2.kept_ids == ("CVX_exact",)


def test_v2_recognizes_compound_net_income_metric() -> None:
    case = _case(
        "What was IBM's net income in fiscal year 2025?",
        [
            _chunk(
                "IBM_exact",
                "| Net income | 13,011 | 2025 |",
                10.0,
                section="financial_table",
                ticker="IBM",
            ),
            _chunk(
                "IBM_backup",
                "Net cash provided by operating activities 2025",
                4.0,
                section="financial_table",
                ticker="IBM",
            ),
        ],
        section="financial_table",
        ticker="IBM",
    )

    selection = select_fact_context_v2(case)

    assert selection.tier == "structured_exact"
    assert selection.kept_ids == ("IBM_exact",)
    assert selection.profile.metric_groups == (("net_income", ("net income",)),)


def test_v2_preserves_aws_residual_metric_term() -> None:
    case = _case(
        "What was Amazon's AWS net sales in 2025?",
        [
            _chunk(
                "AMZN_noise",
                "AWS technology and infrastructure costs in 2025",
                4.5,
                section="mdna",
                ticker="AMZN",
            ),
            _chunk(
                "AMZN_donor",
                "Year ended 2024 2025 Net Sales: AWS 107,556 128,725",
                4.0,
                section="mdna",
                ticker="AMZN",
            ),
        ],
        section="mdna",
        ticker="AMZN",
    )

    selection = select_fact_context_v2(case)

    assert selection.safe is True
    assert selection.kept_ids == ("AMZN_donor",)


def test_v2_selector_has_a_distinct_fingerprint() -> None:
    assert FACT_CONTEXT_SELECTOR_FINGERPRINT.startswith("sha256:")
    assert FACT_CONTEXT_SELECTOR_FINGERPRINT_V2.startswith("sha256:")
    assert FACT_CONTEXT_SELECTOR_FINGERPRINT_V2 != FACT_CONTEXT_SELECTOR_FINGERPRINT
