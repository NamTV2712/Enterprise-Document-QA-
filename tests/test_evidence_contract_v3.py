from src.generation.comparative_answerability import assess_comparative_answerability_v3
from src.generation.comparative_answer_renderer import (
    COMPARATIVE_ANSWER_RENDERER_FINGERPRINT,
    COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT,
    render_dependency_comparison_v3,
)
from src.generation.comparative_evidence import (
    COMPARATIVE_EVIDENCE_V3_FINGERPRINT,
    extract_comparative_facts_v3,
    select_dependency_evidence_v3,
)


QUESTION = "Which company depends more on cloud/subscription revenue, Microsoft or Apple?"


def test_v3_binds_table_values_to_year_columns_and_ignores_change_column() -> None:
    context = """[Source 1] MSFT 10-K, revenue table
Units: USD in millions
| Metric | 2024 | 2025 | Change |
|---|---:|---:|---:|
| Cloud revenue | 900 | 100 | 800% |

[Source 2] AAPL 10-K, revenue table
Units: USD in millions
| Metric | 2024 | 2025 | Change |
|---|---:|---:|---:|
| Cloud revenue | 80 | 90 | 12% |
"""

    facts = extract_comparative_facts_v3(QUESTION, context)
    msft = [fact for fact in facts["MSFT"] if fact.metric == "Cloud revenue"]
    assert {(fact.period, fact.value, fact.kind) for fact in msft} == {
        ("2024", "900", "amount"), ("2025", "100", "amount")
    }
    assert all(fact.location.endswith(":column:1") or fact.location.endswith(":column:2") for fact in msft)
    selected = select_dependency_evidence_v3(QUESTION, context)
    assert selected.selected_by_ticker["MSFT"].period == "2025"
    assert selected.selected_by_ticker["AAPL"].period == "2025"


def test_v3_does_not_turn_footnotes_or_neighbor_lines_into_facts() -> None:
    context = """[Source 1] MSFT 10-K, MD&A
Microsoft Cloud discussion for fiscal year 2025.
Services revenue
(1)
The next paragraph discusses a different segment.

[Source 2] AAPL 10-K, MD&A
Apple Services discussion for fiscal year 2025.
Services revenue
*"""

    facts = extract_comparative_facts_v3(QUESTION, context)
    assert facts == {"MSFT": (), "AAPL": ()}


def test_v3_keeps_ambiguous_period_unknown_and_requires_requested_period() -> None:
    ambiguous = """[Source 1] MSFT 10-K, MD&A
Cloud revenue was $10 billion in 2024 compared with $9 billion in 2023.

[Source 2] AAPL 10-K, MD&A
Cloud revenue was $8 billion in 2024 compared with $7 billion in 2023.
"""
    facts = extract_comparative_facts_v3(QUESTION, ambiguous)
    assert facts["MSFT"]
    assert all(fact.period is None for fact in facts["MSFT"])
    assert select_dependency_evidence_v3(QUESTION, ambiguous).selected_by_ticker["MSFT"] is None

    requested = QUESTION + " for fiscal year 2025"
    selection = select_dependency_evidence_v3(requested, ambiguous)
    assert selection.evidence_sufficient is False
    assert selection.selected_by_ticker == {"MSFT": None, "AAPL": None}


def test_v3_compatible_share_ranks_using_normalized_values_and_renderer() -> None:
    context = """[Source 1] AAPL 10-K, MD&A
Cloud revenue was 20% of total revenue in fiscal year 2025.

[Source 2] MSFT 10-K, MD&A
Cloud revenue was 30% of total revenue in fiscal year 2025.
"""
    selection = select_dependency_evidence_v3(QUESTION, context)
    assert selection.compatible is True
    assert selection.winners == ("MSFT",)
    answer = render_dependency_comparison_v3(QUESTION, context)
    assert answer is not None
    assert "Microsoft is higher" in answer
    assert "[Source 1]" in answer and "[Source 2]" in answer
    assessment = assess_comparative_answerability_v3(QUESTION, context, answer)
    assert assessment.status == "sufficient"
    assert assessment.passed is True


def test_v3_rejects_ranking_claim_when_only_absolute_amounts_exist() -> None:
    context = """[Source 1] MSFT 10-K, MD&A
Microsoft Cloud revenue was $168.9 billion.

[Source 2] AAPL 10-K, MD&A
Services net sales were 109,158 million.
"""
    answer = "Microsoft depends more because its amount is larger [Source 1] [Source 2]."
    assessment = assess_comparative_answerability_v3(QUESTION, context, answer)
    assert assessment.status == "qualified"
    assert assessment.unsupported_ranking is True
    assert assessment.passed is False
    bounded = render_dependency_comparison_v3(QUESTION, context)
    assert bounded is not None
    assert "bounded conclusion" in bounded


def test_v3_fingerprints_are_opt_in_and_v2_default_is_unchanged() -> None:
    assert COMPARATIVE_EVIDENCE_V3_FINGERPRINT.startswith("sha256:")
    assert COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT.startswith("sha256:")
    assert COMPARATIVE_ANSWER_RENDERER_FINGERPRINT != COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT
