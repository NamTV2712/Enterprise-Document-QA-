import pytest

from scripts.diagnostics.context_duplicate_metrics import (
    aggregate_case_diagnostics,
    analyze_context_pairs,
    analyze_metric_association,
    are_exact_duplicates,
    build_case_diagnostic,
    classify_correlation_cohort,
    five_gram_containment,
    is_adjacent_pair,
    is_semantic_only_pair,
    normalize_text,
)


def _chunk(
    chunk_id: str,
    text: str,
    *,
    ticker: str = "AAPL",
    section: str = "risk_factors",
    accession_number: str = "0000320193-25-000079",
    chunk_index: int = 0,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "ticker": ticker,
        "section": section,
        "accession_number": accession_number,
        "chunk_index": chunk_index,
        "text": text,
    }

def test_exact_duplicate_normalization_ignores_case_and_whitespace() -> None:
    first = _chunk("AAPL_0", "  Revenue\n\n growth   was strong. ")
    second = _chunk("AAPL_1", "revenue growth was STRONG.")

    assert normalize_text(first["text"]) == "revenue growth was strong."
    assert are_exact_duplicates(first, second) is True
    assert are_exact_duplicates(first, first) is False


def test_adjacent_pair_requires_same_filing_section_and_neighbor_index() -> None:
    first = _chunk("AAPL_0", "first", chunk_index=4)
    adjacent = _chunk("AAPL_1", "second", chunk_index=5)

    assert is_adjacent_pair(first, adjacent) is True
    assert is_adjacent_pair(
        first,
        _chunk("AAPL_2", "second", chunk_index=6),
    ) is False
    assert is_adjacent_pair(
        first,
        _chunk("AAPL_3", "second", section="mdna", chunk_index=5),
    ) is False
    assert is_adjacent_pair(
        first,
        _chunk(
            "AAPL_4",
            "second",
            accession_number="different-filing",
            chunk_index=5,
        ),
    ) is False


def test_five_gram_containment_measures_contiguous_shared_boundary() -> None:
    first = "one two three four five six seven"
    second = "three four five six seven eight nine"

    assert five_gram_containment(first, second) == 1 / 3
    assert five_gram_containment("one two three", second) == 0.0


def test_semantic_only_pair_excludes_exact_and_adjacent_pairs() -> None:
    first = _chunk("AAPL_0", "alpha evidence", chunk_index=0)
    semantic_match = _chunk("AAPL_4", "different wording", chunk_index=4)
    adjacent = _chunk("AAPL_1", "boundary plus new evidence", chunk_index=1)
    exact = _chunk("AAPL_5", "  ALPHA evidence ", chunk_index=5)

    assert is_semantic_only_pair(
        first,
        semantic_match,
        similarity=0.96,
        threshold=0.95,
    ) is True
    assert is_semantic_only_pair(
        first,
        semantic_match,
        similarity=0.94,
        threshold=0.95,
    ) is False
    assert is_semantic_only_pair(
        first,
        adjacent,
        similarity=0.99,
        threshold=0.95,
    ) is False
    assert is_semantic_only_pair(
        first,
        exact,
        similarity=0.99,
        threshold=0.95,
    ) is False


def test_pairwise_aggregation_counts_each_unordered_pair_once() -> None:
    chunks = [
        _chunk(
            "A",
            "one two three four five six seven",
            chunk_index=0,
        ),
        _chunk(
            "B",
            "three four five six seven eight nine",
            chunk_index=1,
        ),
        _chunk(
            "C",
            " ONE  TWO THREE FOUR FIVE SIX SEVEN ",
            chunk_index=4,
        ),
        _chunk(
            "D",
            "different wording with distinct evidence",
            chunk_index=7,
        ),
    ]
    similarities = {
        ("A", "B"): 0.99,
        ("A", "C"): 1.0,
        ("A", "D"): 0.96,
        ("D", "B"): 0.91,
    }

    metrics = analyze_context_pairs(
        chunks,
        semantic_similarities=similarities,
        semantic_thresholds=(0.90, 0.95, 0.98),
    )

    assert metrics.num_chunks == 4
    assert metrics.num_pairs == 6
    assert metrics.unique_normalized_texts == 3
    assert metrics.exact_duplicate_pairs == 1
    assert metrics.exact_duplicate_pair_rate == 1 / 6
    assert metrics.adjacent_pairs == 1
    assert metrics.adjacent_pair_rate == 1 / 6
    assert metrics.adjacent_containment_mean == 1 / 3
    assert metrics.adjacent_containment_max == 1 / 3
    assert metrics.total_context_tokens == 26
    assert metrics.total_context_5grams == 10
    assert metrics.total_shared_adjacent_5grams == 1
    assert metrics.total_adjacent_shorter_chunk_5grams == 3
    assert metrics.weighted_adjacent_containment == 1 / 3
    assert metrics.pairwise_overlap_mass_rate == 1 / 10
    adjacent_pair = next(pair for pair in metrics.pairs if pair.adjacent)
    assert adjacent_pair.shared_5gram_occurrences == 1
    assert adjacent_pair.shorter_chunk_5gram_count == 3
    assert metrics.semantic_only_pairs_by_threshold == {
        0.90: 2,
        0.95: 1,
        0.98: 0,
    }
    assert metrics.semantic_only_pair_rates_by_threshold == {
        0.90: 2 / 6,
        0.95: 1 / 6,
        0.98: 0.0,
    }


def test_pair_rates_are_zero_when_context_has_no_possible_pairs() -> None:
    metrics = analyze_context_pairs(
        [_chunk("A", "only evidence", chunk_index=0)],
        semantic_thresholds=(0.95,),
    )

    assert metrics.num_pairs == 0
    assert metrics.exact_duplicate_pair_rate == 0.0
    assert metrics.adjacent_pair_rate == 0.0
    assert metrics.semantic_only_pair_rates_by_threshold == {0.95: 0.0}
    assert metrics.total_context_tokens == 2
    assert metrics.total_context_5grams == 0
    assert metrics.total_shared_adjacent_5grams == 0
    assert metrics.total_adjacent_shorter_chunk_5grams == 0
    assert metrics.weighted_adjacent_containment == 0.0
    assert metrics.pairwise_overlap_mass_rate == 0.0


def test_token_weighted_adjacent_burden_uses_shingle_mass() -> None:
    chunks = [
        _chunk("A", "one two three four five six seven", chunk_index=0),
        _chunk("B", "three four five six seven eight nine", chunk_index=1),
        _chunk(
            "C",
            "alpha beta gamma delta epsilon zeta eta theta iota",
            ticker="MSFT",
            chunk_index=0,
        ),
        _chunk(
            "D",
            "alpha beta gamma delta epsilon zeta eta theta iota",
            ticker="MSFT",
            chunk_index=1,
        ),
    ]

    metrics = analyze_context_pairs(chunks)

    assert metrics.adjacent_pairs == 2
    assert metrics.adjacent_containment_mean == (1 / 3 + 1.0) / 2
    assert metrics.total_shared_adjacent_5grams == 6
    assert metrics.total_adjacent_shorter_chunk_5grams == 8
    assert metrics.weighted_adjacent_containment == 6 / 8
    assert metrics.total_context_5grams == 16
    assert metrics.pairwise_overlap_mass_rate == 6 / 16


def test_group_token_weighted_burden_pools_mass_before_division() -> None:
    first_case = build_case_diagnostic(
        question="Short adjacent overlap",
        category="fact_lookup",
        ticker="AAPL",
        section="risk_factors",
        official_context_precision=0.2,
        replay_fidelity="high",
        chunks=[
            _chunk("A", "one two three four five six seven", chunk_index=0),
            _chunk("B", "three four five six seven eight nine", chunk_index=1),
        ],
    )
    second_case = build_case_diagnostic(
        question="Contained adjacent overlap",
        category="fact_lookup",
        ticker="MSFT",
        section="risk_factors",
        official_context_precision=0.8,
        replay_fidelity="high",
        chunks=[
            _chunk(
                "C",
                "alpha beta gamma delta epsilon zeta eta theta iota",
                ticker="MSFT",
                chunk_index=0,
            ),
            _chunk(
                "D",
                "alpha beta gamma delta epsilon zeta eta theta iota",
                ticker="MSFT",
                chunk_index=1,
            ),
        ],
    )

    group = aggregate_case_diagnostics(
        [first_case, second_case],
        group_by="category",
    )[0]

    assert group.context_metrics.total_shared_adjacent_5grams == 6
    assert group.context_metrics.total_adjacent_shorter_chunk_5grams == 8
    assert group.context_metrics.mean_case_weighted_adjacent_containment == (
        1 / 3 + 1.0
    ) / 2
    assert group.context_metrics.pooled_weighted_adjacent_containment == 6 / 8
    assert group.context_metrics.mean_case_pairwise_overlap_mass_rate == (
        1 / 6 + 5 / 10
    ) / 2
    assert group.context_metrics.pooled_pairwise_overlap_mass_rate == 6 / 16


def test_case_diagnostic_keeps_scores_and_replay_fidelity_separate() -> None:
    chunks = [
        _chunk("A", "alpha evidence", chunk_index=0),
        _chunk("B", "different wording", chunk_index=3),
    ]

    diagnostic = build_case_diagnostic(
        question="What evidence is available?",
        category="fact_lookup",
        ticker="AAPL",
        section=None,
        official_context_precision=0.2,
        replay_fidelity="high",
        chunks=chunks,
        semantic_similarities={("A", "B"): 0.96},
        semantic_thresholds=(0.95,),
    )

    assert diagnostic.question == "What evidence is available?"
    assert diagnostic.category == "fact_lookup"
    assert diagnostic.ticker == "AAPL"
    assert diagnostic.section is None
    assert diagnostic.official_context_precision == 0.2
    assert diagnostic.replay_fidelity == "high"
    assert diagnostic.context_metrics.semantic_only_pairs_by_threshold == {
        0.95: 1,
    }


def test_pairwise_aggregation_rejects_conflicting_reverse_similarities() -> None:
    chunks = [
        _chunk("A", "alpha", chunk_index=0),
        _chunk("B", "beta", chunk_index=3),
    ]

    with pytest.raises(ValueError, match="Conflicting similarities"):
        analyze_context_pairs(
            chunks,
            semantic_similarities={
                ("A", "B"): 0.91,
                ("B", "A"): 0.96,
            },
            semantic_thresholds=(0.95,),
        )


def test_group_aggregation_reports_mean_case_and_pooled_pair_rates() -> None:
    small_context = build_case_diagnostic(
        question="Small context",
        category="fact_lookup",
        ticker="AAPL",
        section="risk_factors",
        official_context_precision=0.2,
        replay_fidelity="high",
        chunks=[
            _chunk("A", "duplicate evidence", chunk_index=0),
            _chunk("B", " DUPLICATE  EVIDENCE ", chunk_index=3),
        ],
        semantic_thresholds=(0.95,),
    )
    large_context = build_case_diagnostic(
        question="Large context",
        category="fact_lookup",
        ticker="MSFT",
        section="mdna",
        official_context_precision=0.8,
        replay_fidelity="medium",
        chunks=[
            _chunk("C", "repeated evidence", ticker="MSFT", chunk_index=0),
            _chunk("D", "REPEATED EVIDENCE", ticker="MSFT", chunk_index=3),
            _chunk("E", "unique evidence one", ticker="MSFT", chunk_index=6),
            _chunk("F", "unique evidence two", ticker="MSFT", chunk_index=9),
        ],
        semantic_thresholds=(0.95,),
    )

    groups = aggregate_case_diagnostics(
        [small_context, large_context],
        group_by="category",
    )

    assert len(groups) == 1
    group = groups[0]
    assert group.group_by == "category"
    assert group.group_value == "fact_lookup"
    assert group.num_cases == 2
    assert group.mean_official_context_precision == 0.5
    assert group.replay_fidelity_counts == {"high": 1, "medium": 1}
    assert group.context_metrics.total_possible_pairs == 7
    assert group.context_metrics.exact_duplicate_pairs == 2
    assert group.context_metrics.mean_case_exact_duplicate_pair_rate == (
        1.0 + 1 / 6
    ) / 2
    assert group.context_metrics.pooled_exact_duplicate_pair_rate == 2 / 7
    assert group.context_metrics.total_context_tokens == 14
    assert group.context_metrics.total_context_5grams == 0
    assert group.context_metrics.total_shared_adjacent_5grams == 0
    assert group.context_metrics.pooled_weighted_adjacent_containment == 0.0
    assert group.context_metrics.pooled_pairwise_overlap_mass_rate == 0.0


def test_group_aggregation_keeps_missing_section_as_a_group() -> None:
    diagnostic = build_case_diagnostic(
        question="Mixed-section question",
        category="comparison",
        ticker="AAPL",
        section=None,
        official_context_precision=0.4,
        replay_fidelity="high",
        chunks=[],
        semantic_thresholds=(0.95,),
    )

    groups = aggregate_case_diagnostics([diagnostic], group_by="section")

    assert len(groups) == 1
    assert groups[0].group_value is None
    assert groups[0].context_metrics.pooled_exact_duplicate_pair_rate == 0.0


def test_correlation_cohort_contract_fixes_precision_boundary_and_exclusions() -> None:
    def make_case(
        question: str,
        *,
        category: str = "fact_lookup",
        precision: float,
        fidelity: str = "high",
    ):
        return build_case_diagnostic(
            question=question,
            category=category,
            ticker="AAPL",
            section=None,
            official_context_precision=precision,
            replay_fidelity=fidelity,
            chunks=[],
        )

    assert classify_correlation_cohort(
        make_case("below", precision=0.499),
    ).precision_cohort == "low"
    assert classify_correlation_cohort(
        make_case("boundary", precision=0.5),
    ).precision_cohort == "high"

    out_of_corpus = classify_correlation_cohort(
        make_case(
            "ooc",
            category="out_of_corpus",
            precision=0.0,
            fidelity="low",
        )
    )
    assert out_of_corpus.eligible is False
    assert out_of_corpus.exclusion_reason == "out_of_corpus"

    low_fidelity = classify_correlation_cohort(
        make_case("rewritten", precision=0.2, fidelity="low"),
    )
    assert low_fidelity.eligible is False
    assert low_fidelity.exclusion_reason == "insufficient_replay_fidelity"


def test_metric_association_reports_cohorts_exclusions_and_spearman() -> None:
    def make_case(
        question: str,
        precision: float,
        *,
        category: str = "fact_lookup",
        fidelity: str = "high",
    ):
        return build_case_diagnostic(
            question=question,
            category=category,
            ticker="AAPL",
            section=None,
            official_context_precision=precision,
            replay_fidelity=fidelity,
            chunks=[],
        )

    cases = [
        make_case("first", 0.8),
        make_case("second", 0.6),
        make_case("third", 0.4),
        make_case("fourth", 0.2),
        make_case("ooc", 0.0, category="out_of_corpus"),
        make_case("low-fidelity", 0.3, fidelity="low"),
    ]
    metric_values = {
        "first": 0.1,
        "second": 0.2,
        "third": 0.3,
        "fourth": 0.4,
        "ooc": 1.0,
        "low-fidelity": 1.0,
    }

    association = analyze_metric_association(
        cases,
        metric_name="pairwise_overlap_mass_rate",
        metric_getter=lambda case: metric_values[case.question],
    )

    assert association.total_cases == 6
    assert association.eligible_cases == 4
    assert association.exclusion_counts == {
        "insufficient_replay_fidelity": 1,
        "out_of_corpus": 1,
    }
    assert association.low_precision_cases == 2
    assert association.high_precision_cases == 2
    assert association.low_precision_mean == 0.35
    assert association.high_precision_mean == pytest.approx(0.15)
    assert association.low_minus_high_mean_difference == pytest.approx(0.2)
    assert association.spearman.sample_size == 4
    assert association.spearman.coefficient == pytest.approx(-1.0)
    assert association.spearman.status == "ok"


def test_metric_association_does_not_report_zero_for_constant_metric() -> None:
    cases = [
        build_case_diagnostic(
            question=f"case-{index}",
            category="fact_lookup",
            ticker="AAPL",
            section=None,
            official_context_precision=precision,
            replay_fidelity="high",
            chunks=[],
        )
        for index, precision in enumerate((0.2, 0.5, 0.8))
    ]

    association = analyze_metric_association(
        cases,
        metric_name="constant",
        metric_getter=lambda case: 0.0,
    )

    assert association.spearman.sample_size == 3
    assert association.spearman.coefficient is None
    assert association.spearman.status == "constant_metric"


def test_metric_association_uses_average_ranks_for_ties() -> None:
    precisions = (0.2, 0.4, 0.6, 0.8)
    cases = [
        build_case_diagnostic(
            question=f"case-{index}",
            category="fact_lookup",
            ticker="AAPL",
            section=None,
            official_context_precision=precision,
            replay_fidelity="high",
            chunks=[],
        )
        for index, precision in enumerate(precisions)
    ]
    metric_values = {
        "case-0": 0.1,
        "case-1": 0.1,
        "case-2": 0.2,
        "case-3": 0.3,
    }

    association = analyze_metric_association(
        cases,
        metric_name="tied_metric",
        metric_getter=lambda case: metric_values[case.question],
    )

    assert association.spearman.coefficient == pytest.approx(0.9486832981)
    assert association.spearman.status == "ok"

