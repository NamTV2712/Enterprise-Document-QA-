"""Pure metrics for diagnosing duplicate evidence in retrieved contexts."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import combinations
from math import isfinite, sqrt
from statistics import fmean, median
from typing import Any, Callable, Literal

ChunkRecord = Mapping[str, Any]
SimilarityMap = Mapping[tuple[str, str], float]
LOW_CONTEXT_PRECISION_THRESHOLD = 0.50
ELIGIBLE_REPLAY_FIDELITIES = frozenset({"high"})


@dataclass(frozen=True)
class PairDiagnostic:
    first_chunk_id: str
    second_chunk_id: str
    exact_duplicate: bool
    adjacent: bool
    adjacent_containment: float
    shared_5gram_occurrences: int
    shorter_chunk_5gram_count: int
    semantic_similarity: float | None
    semantic_only_thresholds: tuple[float, ...]


@dataclass(frozen=True)
class ContextDuplicateMetrics:
    """Case metrics using normalized whitespace tokens as a budget proxy.

    Pairwise overlap mass can count the same text region more than once when a
    chunk overlaps multiple neighbors. It is not a unique wasted-token rate.
    """

    num_chunks: int
    num_pairs: int
    unique_normalized_texts: int
    exact_duplicate_pairs: int
    exact_duplicate_pair_rate: float
    adjacent_pairs: int
    adjacent_pair_rate: float
    adjacent_containment_mean: float
    adjacent_containment_max: float
    total_context_tokens: int
    total_context_5grams: int
    total_shared_adjacent_5grams: int
    total_adjacent_shorter_chunk_5grams: int
    weighted_adjacent_containment: float
    pairwise_overlap_mass_rate: float
    semantic_only_pairs_by_threshold: dict[float, int]
    semantic_only_pair_rates_by_threshold: dict[float, float]
    pairs: tuple[PairDiagnostic, ...]


@dataclass(frozen=True)
class CaseDiagnostic:
    question: str
    category: str
    ticker: str | None
    section: str | None
    official_context_precision: float
    replay_fidelity: str
    context_metrics: ContextDuplicateMetrics


@dataclass(frozen=True)
class GroupDuplicateMetrics:
    """Group totals plus equally weighted case means and pooled mass ratios."""

    total_possible_pairs: int
    total_context_tokens: int
    total_context_5grams: int
    exact_duplicate_pairs: int
    mean_case_exact_duplicate_pair_rate: float
    pooled_exact_duplicate_pair_rate: float
    adjacent_pairs: int
    mean_case_adjacent_pair_rate: float
    pooled_adjacent_pair_rate: float
    total_shared_adjacent_5grams: int
    total_adjacent_shorter_chunk_5grams: int
    mean_case_weighted_adjacent_containment: float
    pooled_weighted_adjacent_containment: float
    mean_case_pairwise_overlap_mass_rate: float
    pooled_pairwise_overlap_mass_rate: float
    semantic_only_pairs_by_threshold: dict[float, int]
    mean_case_semantic_only_pair_rates_by_threshold: dict[float, float]
    pooled_semantic_only_pair_rates_by_threshold: dict[float, float]


@dataclass(frozen=True)
class GroupDiagnostic:
    group_by: Literal["category", "ticker", "section"]
    group_value: str | None
    num_cases: int
    mean_official_context_precision: float
    replay_fidelity_counts: dict[str, int]
    context_metrics: GroupDuplicateMetrics


@dataclass(frozen=True)
class CorrelationCohortAssignment:
    eligible: bool
    precision_cohort: Literal["low", "high"] | None
    exclusion_reason: Literal[
        "out_of_corpus",
        "insufficient_replay_fidelity",
    ] | None


@dataclass(frozen=True)
class RankCorrelation:
    sample_size: int
    coefficient: float | None
    status: Literal[
        "ok",
        "insufficient_cases",
        "constant_metric",
        "constant_context_precision",
    ]


@dataclass(frozen=True)
class MetricAssociationDiagnostic:
    metric_name: str
    total_cases: int
    eligible_cases: int
    exclusion_counts: dict[str, int]
    low_precision_threshold: float
    low_precision_cases: int
    high_precision_cases: int
    low_precision_mean: float | None
    high_precision_mean: float | None
    low_precision_median: float | None
    high_precision_median: float | None
    low_minus_high_mean_difference: float | None
    spearman: RankCorrelation

def normalize_text(text: str) -> str:
    """Normalize case and whitespace without changing punctuation or numbers."""
    return re.sub(r"\s+", " ", text).strip().lower()


def are_exact_duplicates(first: ChunkRecord, second: ChunkRecord) -> bool:
    """Return whether distinct logical chunks contain the same normalized text."""
    if first.get("chunk_id") == second.get("chunk_id"):
        return False

    first_text = normalize_text(str(first.get("text", "")))
    second_text = normalize_text(str(second.get("text", "")))
    return bool(first_text) and first_text == second_text


def is_adjacent_pair(first: ChunkRecord, second: ChunkRecord) -> bool:
    """Return whether chunks are neighbors in the same filing section."""
    if first.get("chunk_id") == second.get("chunk_id"):
        return False

    identity_fields = ("ticker", "accession_number", "section")
    if any(first.get(field) != second.get(field) for field in identity_fields):
        return False

    first_index = first.get("chunk_index")
    second_index = second.get("chunk_index")
    if not isinstance(first_index, int) or not isinstance(second_index, int):
        return False
    return abs(first_index - second_index) == 1


def _token_shingles(text: str, size: int) -> Counter[tuple[str, ...]]:
    tokens = normalize_text(text).split()
    if size <= 0 or len(tokens) < size:
        return Counter()
    return Counter(
        tuple(tokens[start:start + size])
        for start in range(len(tokens) - size + 1)
    )


def _shingle_overlap_counts(
    first_shingles: Counter[tuple[str, ...]],
    second_shingles: Counter[tuple[str, ...]],
) -> tuple[int, int]:
    shared_occurrences = sum((first_shingles & second_shingles).values())
    shorter_count = min(
        sum(first_shingles.values()),
        sum(second_shingles.values()),
    )
    return shared_occurrences, shorter_count


def five_gram_containment(first_text: str, second_text: str) -> float:
    """Measure shared contiguous five-token content relative to the shorter text."""
    first_shingles = _token_shingles(first_text, size=5)
    second_shingles = _token_shingles(second_text, size=5)
    shared, shorter_count = _shingle_overlap_counts(
        first_shingles,
        second_shingles,
    )
    return _safe_rate(shared, shorter_count)


def is_semantic_only_pair(
    first: ChunkRecord,
    second: ChunkRecord,
    *,
    similarity: float,
    threshold: float,
) -> bool:
    """Classify a high-similarity pair not explained by identity or adjacency."""
    if first.get("chunk_id") == second.get("chunk_id"):
        return False
    if similarity < threshold:
        return False
    if are_exact_duplicates(first, second):
        return False
    return not is_adjacent_pair(first, second)


def pair_key(first_chunk_id: str, second_chunk_id: str) -> tuple[str, str]:
    """Return one deterministic identity for an unordered chunk pair."""
    return tuple(sorted((first_chunk_id, second_chunk_id)))


def _safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _canonicalize_similarities(
    semantic_similarities: SimilarityMap | None,
) -> dict[tuple[str, str], float]:
    canonical: dict[tuple[str, str], float] = {}
    for (first_chunk_id, second_chunk_id), raw_similarity in (
        semantic_similarities or {}
    ).items():
        key = pair_key(first_chunk_id, second_chunk_id)
        similarity = float(raw_similarity)
        if key in canonical and canonical[key] != similarity:
            raise ValueError(
                "Conflicting similarities for unordered pair "
                f"{key}: {canonical[key]} != {similarity}"
            )
        canonical[key] = similarity
    return canonical


def analyze_context_pairs(
    chunks: list[ChunkRecord],
    *,
    semantic_similarities: SimilarityMap | None = None,
    semantic_thresholds: tuple[float, ...] = (0.90, 0.95, 0.98),
) -> ContextDuplicateMetrics:
    """Aggregate mutually classified duplicate signals for one final context."""
    chunk_ids = [str(chunk.get("chunk_id", "")) for chunk in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("Final context contains duplicate chunk IDs")

    thresholds = tuple(sorted(set(semantic_thresholds)))
    canonical_similarities = _canonicalize_similarities(semantic_similarities)
    pair_diagnostics: list[PairDiagnostic] = []
    exact_duplicate_pairs = 0
    adjacent_containments: list[float] = []
    semantic_counts = {threshold: 0 for threshold in thresholds}
    chunk_tokens = {
        chunk_id: normalize_text(str(chunk.get("text", ""))).split()
        for chunk_id, chunk in zip(chunk_ids, chunks, strict=True)
    }
    chunk_fivegrams = {
        chunk_id: _token_shingles(str(chunk.get("text", "")), size=5)
        for chunk_id, chunk in zip(chunk_ids, chunks, strict=True)
    }
    total_context_tokens = sum(len(tokens) for tokens in chunk_tokens.values())
    total_context_5grams = sum(
        sum(shingles.values())
        for shingles in chunk_fivegrams.values()
    )
    total_shared_adjacent_5grams = 0
    total_adjacent_shorter_chunk_5grams = 0

    for first, second in combinations(chunks, 2):
        first_chunk_id = str(first.get("chunk_id", ""))
        second_chunk_id = str(second.get("chunk_id", ""))
        exact_duplicate = are_exact_duplicates(first, second)
        adjacent = is_adjacent_pair(first, second)
        shared_5gram_occurrences = 0
        shorter_chunk_5gram_count = 0
        if adjacent:
            (
                shared_5gram_occurrences,
                shorter_chunk_5gram_count,
            ) = _shingle_overlap_counts(
                chunk_fivegrams[first_chunk_id],
                chunk_fivegrams[second_chunk_id],
            )
        adjacent_containment = _safe_rate(
            shared_5gram_occurrences,
            shorter_chunk_5gram_count,
        )
        similarity = canonical_similarities.get(
            pair_key(first_chunk_id, second_chunk_id)
        )
        semantic_only_thresholds = tuple(
            threshold
            for threshold in thresholds
            if similarity is not None
            and is_semantic_only_pair(
                first,
                second,
                similarity=similarity,
                threshold=threshold,
            )
        )

        if exact_duplicate:
            exact_duplicate_pairs += 1
        if adjacent:
            adjacent_containments.append(adjacent_containment)
            total_shared_adjacent_5grams += shared_5gram_occurrences
            total_adjacent_shorter_chunk_5grams += shorter_chunk_5gram_count
        for threshold in semantic_only_thresholds:
            semantic_counts[threshold] += 1

        pair_diagnostics.append(
            PairDiagnostic(
                first_chunk_id=first_chunk_id,
                second_chunk_id=second_chunk_id,
                exact_duplicate=exact_duplicate,
                adjacent=adjacent,
                adjacent_containment=adjacent_containment,
                shared_5gram_occurrences=shared_5gram_occurrences,
                shorter_chunk_5gram_count=shorter_chunk_5gram_count,
                semantic_similarity=similarity,
                semantic_only_thresholds=semantic_only_thresholds,
            )
        )

    adjacent_containment_mean = (
        sum(adjacent_containments) / len(adjacent_containments)
        if adjacent_containments
        else 0.0
    )
    return ContextDuplicateMetrics(
        num_chunks=len(chunks),
        num_pairs=len(pair_diagnostics),
        unique_normalized_texts=len(
            {normalize_text(str(chunk.get("text", ""))) for chunk in chunks}
        ),
        exact_duplicate_pairs=exact_duplicate_pairs,
        exact_duplicate_pair_rate=_safe_rate(
            exact_duplicate_pairs,
            len(pair_diagnostics),
        ),
        adjacent_pairs=len(adjacent_containments),
        adjacent_pair_rate=_safe_rate(
            len(adjacent_containments),
            len(pair_diagnostics),
        ),
        adjacent_containment_mean=adjacent_containment_mean,
        adjacent_containment_max=max(adjacent_containments, default=0.0),
        total_context_tokens=total_context_tokens,
        total_context_5grams=total_context_5grams,
        total_shared_adjacent_5grams=total_shared_adjacent_5grams,
        total_adjacent_shorter_chunk_5grams=(
            total_adjacent_shorter_chunk_5grams
        ),
        weighted_adjacent_containment=_safe_rate(
            total_shared_adjacent_5grams,
            total_adjacent_shorter_chunk_5grams,
        ),
        pairwise_overlap_mass_rate=_safe_rate(
            total_shared_adjacent_5grams,
            total_context_5grams,
        ),
        semantic_only_pairs_by_threshold=semantic_counts,
        semantic_only_pair_rates_by_threshold={
            threshold: _safe_rate(count, len(pair_diagnostics))
            for threshold, count in semantic_counts.items()
        },
        pairs=tuple(pair_diagnostics),
    )


def build_case_diagnostic(
    *,
    question: str,
    category: str,
    ticker: str | None,
    section: str | None,
    official_context_precision: float,
    replay_fidelity: str,
    chunks: list[ChunkRecord],
    semantic_similarities: SimilarityMap | None = None,
    semantic_thresholds: tuple[float, ...] = (0.90, 0.95, 0.98),
) -> CaseDiagnostic:
    """Attach replay metadata to pure duplicate metrics for one evaluation case."""
    return CaseDiagnostic(
        question=question,
        category=category,
        ticker=ticker,
        section=section,
        official_context_precision=official_context_precision,
        replay_fidelity=replay_fidelity,
        context_metrics=analyze_context_pairs(
            chunks,
            semantic_similarities=semantic_similarities,
            semantic_thresholds=semantic_thresholds,
        ),
    )

def _aggregate_duplicate_metrics(
    cases: list[CaseDiagnostic],
) -> GroupDuplicateMetrics:
    total_possible_pairs = sum(
        case.context_metrics.num_pairs
        for case in cases
    )
    exact_duplicate_pairs = sum(
        case.context_metrics.exact_duplicate_pairs
        for case in cases
    )
    adjacent_pairs = sum(
        case.context_metrics.adjacent_pairs
        for case in cases
    )
    total_context_tokens = sum(
        case.context_metrics.total_context_tokens
        for case in cases
    )
    total_context_5grams = sum(
        case.context_metrics.total_context_5grams
        for case in cases
    )
    total_shared_adjacent_5grams = sum(
        case.context_metrics.total_shared_adjacent_5grams
        for case in cases
    )
    total_adjacent_shorter_chunk_5grams = sum(
        case.context_metrics.total_adjacent_shorter_chunk_5grams
        for case in cases
    )

    threshold_sets = {
        tuple(case.context_metrics.semantic_only_pairs_by_threshold)
        for case in cases
    }
    if len(threshold_sets) > 1:
        raise ValueError(
            "Cannot aggregate cases computed with different semantic thresholds"
        )
    thresholds = next(iter(threshold_sets), ())
    semantic_counts = {
        threshold: sum(
            case.context_metrics.semantic_only_pairs_by_threshold[threshold]
            for case in cases
        )
        for threshold in thresholds
    }

    num_cases = len(cases)
    return GroupDuplicateMetrics(
        total_possible_pairs=total_possible_pairs,
        total_context_tokens=total_context_tokens,
        total_context_5grams=total_context_5grams,
        exact_duplicate_pairs=exact_duplicate_pairs,
        mean_case_exact_duplicate_pair_rate=sum(
            case.context_metrics.exact_duplicate_pair_rate
            for case in cases
        ) / num_cases,
        pooled_exact_duplicate_pair_rate=_safe_rate(
            exact_duplicate_pairs,
            total_possible_pairs,
        ),
        adjacent_pairs=adjacent_pairs,
        mean_case_adjacent_pair_rate=sum(
            case.context_metrics.adjacent_pair_rate
            for case in cases
        ) / num_cases,
        pooled_adjacent_pair_rate=_safe_rate(
            adjacent_pairs,
            total_possible_pairs,
        ),
        total_shared_adjacent_5grams=total_shared_adjacent_5grams,
        total_adjacent_shorter_chunk_5grams=(
            total_adjacent_shorter_chunk_5grams
        ),
        mean_case_weighted_adjacent_containment=sum(
            case.context_metrics.weighted_adjacent_containment
            for case in cases
        ) / num_cases,
        pooled_weighted_adjacent_containment=_safe_rate(
            total_shared_adjacent_5grams,
            total_adjacent_shorter_chunk_5grams,
        ),
        mean_case_pairwise_overlap_mass_rate=sum(
            case.context_metrics.pairwise_overlap_mass_rate
            for case in cases
        ) / num_cases,
        pooled_pairwise_overlap_mass_rate=_safe_rate(
            total_shared_adjacent_5grams,
            total_context_5grams,
        ),
        semantic_only_pairs_by_threshold=semantic_counts,
        mean_case_semantic_only_pair_rates_by_threshold={
            threshold: sum(
                case.context_metrics.semantic_only_pair_rates_by_threshold[
                    threshold
                ]
                for case in cases
            ) / num_cases
            for threshold in thresholds
        },
        pooled_semantic_only_pair_rates_by_threshold={
            threshold: _safe_rate(count, total_possible_pairs)
            for threshold, count in semantic_counts.items()
        },
    )


def aggregate_case_diagnostics(
    cases: list[CaseDiagnostic],
    *,
    group_by: Literal["category", "ticker", "section"],
) -> tuple[GroupDiagnostic, ...]:
    """Aggregate case-level duplicate burden without changing official scores."""
    if group_by not in {"category", "ticker", "section"}:
        raise ValueError(f"Unsupported diagnostic grouping: {group_by}")

    grouped: dict[str | None, list[CaseDiagnostic]] = {}
    for case in cases:
        group_value = getattr(case, group_by)
        grouped.setdefault(group_value, []).append(case)

    diagnostics = []
    for group_value, group_cases in sorted(
        grouped.items(),
        key=lambda item: (item[0] is None, str(item[0])),
    ):
        diagnostics.append(
            GroupDiagnostic(
                group_by=group_by,
                group_value=group_value,
                num_cases=len(group_cases),
                mean_official_context_precision=sum(
                    case.official_context_precision
                    for case in group_cases
                ) / len(group_cases),
                replay_fidelity_counts=dict(
                    sorted(
                        Counter(
                            case.replay_fidelity
                            for case in group_cases
                        ).items()
                    )
                ),
                context_metrics=_aggregate_duplicate_metrics(group_cases),
            )
        )
    return tuple(diagnostics)


def classify_correlation_cohort(
    case: CaseDiagnostic,
) -> CorrelationCohortAssignment:
    """Apply the pre-registered eligibility and precision cohort contract."""
    precision = case.official_context_precision
    if not isfinite(precision) or not 0.0 <= precision <= 1.0:
        raise ValueError(
            "official_context_precision must be a finite value between 0 and 1"
        )

    if case.category == "out_of_corpus":
        return CorrelationCohortAssignment(
            eligible=False,
            precision_cohort=None,
            exclusion_reason="out_of_corpus",
        )
    if case.replay_fidelity not in ELIGIBLE_REPLAY_FIDELITIES:
        return CorrelationCohortAssignment(
            eligible=False,
            precision_cohort=None,
            exclusion_reason="insufficient_replay_fidelity",
        )
    return CorrelationCohortAssignment(
        eligible=True,
        precision_cohort=(
            "low"
            if precision < LOW_CONTEXT_PRECISION_THRESHOLD
            else "high"
        ),
        exclusion_reason=None,
    )


def _average_ranks(values: list[float]) -> list[float]:
    indexed_values = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(indexed_values):
        end = start + 1
        while (
            end < len(indexed_values)
            and indexed_values[end][1] == indexed_values[start][1]
        ):
            end += 1
        average_rank = ((start + 1) + end) / 2
        for position in range(start, end):
            original_index = indexed_values[position][0]
            ranks[original_index] = average_rank
        start = end
    return ranks


def _spearman_rank_correlation(
    metric_values: list[float],
    precision_values: list[float],
) -> RankCorrelation:
    sample_size = len(metric_values)
    if sample_size < 3:
        return RankCorrelation(sample_size, None, "insufficient_cases")
    if len(set(metric_values)) == 1:
        return RankCorrelation(sample_size, None, "constant_metric")
    if len(set(precision_values)) == 1:
        return RankCorrelation(
            sample_size,
            None,
            "constant_context_precision",
        )

    metric_ranks = _average_ranks(metric_values)
    precision_ranks = _average_ranks(precision_values)
    metric_mean = fmean(metric_ranks)
    precision_mean = fmean(precision_ranks)
    covariance = sum(
        (metric_rank - metric_mean) * (precision_rank - precision_mean)
        for metric_rank, precision_rank in zip(
            metric_ranks,
            precision_ranks,
            strict=True,
        )
    )
    metric_variance = sum(
        (rank - metric_mean) ** 2
        for rank in metric_ranks
    )
    precision_variance = sum(
        (rank - precision_mean) ** 2
        for rank in precision_ranks
    )
    coefficient = covariance / sqrt(metric_variance * precision_variance)
    return RankCorrelation(sample_size, coefficient, "ok")


def analyze_metric_association(
    cases: list[CaseDiagnostic],
    *,
    metric_name: str,
    metric_getter: Callable[[CaseDiagnostic], float],
) -> MetricAssociationDiagnostic:
    """Compare pre-registered precision cohorts and compute rank correlation."""
    eligible: list[tuple[CaseDiagnostic, str, float]] = []
    exclusion_counts: Counter[str] = Counter()
    for case in cases:
        assignment = classify_correlation_cohort(case)
        if not assignment.eligible:
            assert assignment.exclusion_reason is not None
            exclusion_counts[assignment.exclusion_reason] += 1
            continue

        metric_value = float(metric_getter(case))
        if not isfinite(metric_value):
            raise ValueError(f"Metric {metric_name!r} contains a non-finite value")
        assert assignment.precision_cohort is not None
        eligible.append((case, assignment.precision_cohort, metric_value))

    low_values = [
        metric_value
        for _, cohort, metric_value in eligible
        if cohort == "low"
    ]
    high_values = [
        metric_value
        for _, cohort, metric_value in eligible
        if cohort == "high"
    ]
    low_mean = fmean(low_values) if low_values else None
    high_mean = fmean(high_values) if high_values else None
    mean_difference = (
        low_mean - high_mean
        if low_mean is not None and high_mean is not None
        else None
    )
    metric_values = [metric_value for _, _, metric_value in eligible]
    precision_values = [
        case.official_context_precision
        for case, _, _ in eligible
    ]

    return MetricAssociationDiagnostic(
        metric_name=metric_name,
        total_cases=len(cases),
        eligible_cases=len(eligible),
        exclusion_counts=dict(sorted(exclusion_counts.items())),
        low_precision_threshold=LOW_CONTEXT_PRECISION_THRESHOLD,
        low_precision_cases=len(low_values),
        high_precision_cases=len(high_values),
        low_precision_mean=low_mean,
        high_precision_mean=high_mean,
        low_precision_median=median(low_values) if low_values else None,
        high_precision_median=median(high_values) if high_values else None,
        low_minus_high_mean_difference=mean_difference,
        spearman=_spearman_rank_correlation(
            metric_values,
            precision_values,
        ),
    )
