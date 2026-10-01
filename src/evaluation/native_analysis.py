"""Read-only comparison, trend, and failure facts over EVAL-001 reports."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Sequence

from src.evaluation.native_protocol import (
    METRIC_DEFINITIONS,
    AggregateMetricResult,
    CaseMetricResult,
    MetricDefinition,
    NativeReport,
    NativeReportBinding,
    canonical_report_bytes,
    parse_native_report,
)
from src.evaluation.native_publication import PublishedNativeReport
from src.retrieval.canonical_json import canonical_json_bytes

METRIC_IDS = tuple(item.metric_id for item in METRIC_DEFINITIONS)
_JUDGE_METRICS = frozenset(item.metric_id for item in METRIC_DEFINITIONS if item.source == "precomputed_native_judge")
FAILURE_CATEGORIES = (
    "fallback_expectation_mismatch",
    "invalid_citation_index",
    "missing_required_keyword",
    "unavailable_prerequisite",
)


class NativeAnalysisError(ValueError):
    """A requested native analysis cannot be performed truthfully."""


class UnknownNativeMetric(NativeAnalysisError):
    """A requested metric ID does not exist in the EVAL-001 registry."""


class IncompatibleNativeReports(NativeAnalysisError):
    """Two reports have a global protocol/dataset/context mismatch."""


@dataclass(frozen=True)
class MetricComparison:
    metric_id: str
    metric_version: int
    direction: str
    baseline: AggregateMetricResult
    candidate: AggregateMetricResult
    same_computed_case_coverage: bool
    status: Literal["comparable", "unavailable", "not_applicable", "incompatible"]
    candidate_minus_baseline: float | None
    reason_code: str | None


@dataclass(frozen=True)
class CaseMetricComparison:
    metric_id: str
    metric_version: int
    baseline: CaseMetricResult | None
    candidate: CaseMetricResult | None
    status: Literal["comparable", "unavailable", "not_applicable", "incompatible", "unpaired"]
    candidate_minus_baseline: float | None
    reason_code: str | None


@dataclass(frozen=True)
class CaseComparison:
    case_id: str
    pairing: Literal["paired", "baseline_only", "candidate_only"]
    baseline_context_sha256: str | None
    candidate_context_sha256: str | None
    metrics: tuple[CaseMetricComparison, ...]


@dataclass(frozen=True)
class NativeComparison:
    baseline_run_id: str
    candidate_run_id: str
    baseline_digest: str
    candidate_digest: str
    baseline_status: str
    candidate_status: str
    baseline_binding: NativeReportBinding
    candidate_binding: NativeReportBinding
    same_case_universe: bool
    eligible_for_complete_comparison: bool
    eligibility_reasons: tuple[str, ...]
    metrics: tuple[MetricComparison, ...]
    cases: tuple[CaseComparison, ...]


@dataclass(frozen=True)
class TrendPoint:
    run_id: str
    report_digest: str
    published_at: str
    report_status: str
    aggregate: AggregateMetricResult
    generator_model_id: str
    generation_binding: str
    retrieval_binding: str
    judge_binding: str | None


@dataclass(frozen=True)
class TrendGroup:
    binding_group: str
    metric_id: str
    metric_version: int
    points: tuple[TrendPoint, ...]


@dataclass(frozen=True)
class FailureFinding:
    category_id: str
    case_id: str
    context_sha256: str | None
    metric_id: str
    metric_version: int
    metric_status: str
    value: float | bool | None
    reason_code: str | None


@dataclass(frozen=True)
class FailureAnalysis:
    run_id: str
    report_digest: str
    report_status: str
    category_counts: tuple[tuple[str, int], ...]
    findings: tuple[FailureFinding, ...]


def _validated(report: NativeReport) -> NativeReport:
    # Never trust a constructed/modified dataclass solely because its type matches.
    return parse_native_report(canonical_report_bytes(report))


def _definitions(metric_ids: Sequence[str] | None) -> tuple[MetricDefinition, ...]:
    if metric_ids is None:
        return METRIC_DEFINITIONS
    if not metric_ids or len(metric_ids) != len(set(metric_ids)):
        raise UnknownNativeMetric("metric selection must be nonempty and unique")
    unknown = set(metric_ids) - set(METRIC_IDS)
    if unknown:
        raise UnknownNativeMetric("unknown native metric ID")
    return tuple(item for item in METRIC_DEFINITIONS if item.metric_id in metric_ids)


def _delta(baseline: float | bool, candidate: float | bool) -> float:
    return float(Decimal(str(float(candidate))) - Decimal(str(float(baseline))))


def _status(baseline: str, candidate: str) -> tuple[str, str | None]:
    if baseline == candidate == "computed":
        return "comparable", None
    if "unavailable" in (baseline, candidate):
        return "unavailable", "metric_unavailable"
    return "not_applicable", "metric_not_applicable"


def _metric_compatible(definition: MetricDefinition, baseline: NativeReport, candidate: NativeReport) -> bool:
    if definition.metric_id not in _JUDGE_METRICS:
        return True
    return (
        baseline.binding.judge_model_id == candidate.binding.judge_model_id
        and baseline.binding.judge_prompt_sha256 == candidate.binding.judge_prompt_sha256
    )


def compare_native_reports(
    baseline: NativeReport,
    candidate: NativeReport,
    metric_ids: Sequence[str] | None = None,
) -> NativeComparison:
    """Compare values without changing EVAL-001 aggregates or source reports."""
    baseline = _validated(baseline)
    candidate = _validated(candidate)
    definitions = _definitions(metric_ids)
    left_binding, right_binding = baseline.binding, candidate.binding
    if (left_binding.dataset_id, left_binding.dataset_version, left_binding.dataset_revision) != (
        right_binding.dataset_id, right_binding.dataset_version, right_binding.dataset_revision
    ):
        raise IncompatibleNativeReports("dataset identity or revision differs")
    if left_binding.context_binding != right_binding.context_binding:
        raise IncompatibleNativeReports("rendered-context binding differs")
    left_cases = {item.case_id: item for item in baseline.cases}
    right_cases = {item.case_id: item for item in candidate.cases}
    same_universe = left_cases.keys() == right_cases.keys()
    aggregate_rows: list[MetricComparison] = []
    for definition in definitions:
        left = next(item for item in baseline.aggregates if item.metric_id == definition.metric_id)
        right = next(item for item in candidate.aggregates if item.metric_id == definition.metric_id)
        left_coverage = {case.case_id for case in baseline.cases if
                         next(metric for metric in case.metrics if metric.metric_id == definition.metric_id).status == "computed"}
        right_coverage = {case.case_id for case in candidate.cases if
                          next(metric for metric in case.metrics if metric.metric_id == definition.metric_id).status == "computed"}
        same_coverage = left_coverage == right_coverage
        if left.metric_version != right.metric_version or not _metric_compatible(definition, baseline, candidate):
            status, reason = "incompatible", "metric_or_judge_definition_changed"
        elif not same_universe:
            status, reason = "incompatible", "case_universe_changed"
        else:
            status, reason = _status(left.status, right.status)
            if status == "comparable" and not same_coverage:
                status, reason = "incompatible", "computed_case_coverage_changed"
        aggregate_rows.append(MetricComparison(
            definition.metric_id, definition.metric_version, definition.direction,
            left, right, same_coverage, status,
            _delta(left.value, right.value) if status == "comparable" else None,
            reason,
        ))
    case_rows: list[CaseComparison] = []
    for case_id in sorted(left_cases.keys() | right_cases.keys()):
        left, right = left_cases.get(case_id), right_cases.get(case_id)
        pairing = "paired" if left and right else ("baseline_only" if left else "candidate_only")
        metric_rows: list[CaseMetricComparison] = []
        for definition in definitions:
            left_metric = next((item for item in left.metrics if item.metric_id == definition.metric_id), None) if left else None
            right_metric = next((item for item in right.metrics if item.metric_id == definition.metric_id), None) if right else None
            if left_metric is None or right_metric is None:
                status, reason = "unpaired", "case_missing_from_one_report"
            elif left_metric.metric_version != right_metric.metric_version or not _metric_compatible(definition, baseline, candidate):
                status, reason = "incompatible", "metric_or_judge_definition_changed"
            else:
                status, reason = _status(left_metric.status, right_metric.status)
            metric_rows.append(CaseMetricComparison(
                definition.metric_id, definition.metric_version, left_metric, right_metric,
                status,
                _delta(left_metric.value, right_metric.value) if status == "comparable" else None,
                reason,
            ))
        case_rows.append(CaseComparison(
            case_id, pairing, left.context_sha256 if left else None,
            right.context_sha256 if right else None, tuple(metric_rows),
        ))
    reasons = set(item.reason_code for item in aggregate_rows if item.reason_code is not None)
    if baseline.status != "complete" or candidate.status != "complete":
        reasons.add("incomplete_report")
    return NativeComparison(
        baseline.run_id, candidate.run_id, baseline.digest, candidate.digest,
        baseline.status, candidate.status, left_binding, right_binding,
        same_universe, not reasons, tuple(sorted(reasons)),
        tuple(aggregate_rows), tuple(case_rows),
    )


def metric_binding_group(report: NativeReport, metric_id: str) -> str:
    """Fingerprint exactly the dimensions held equal in a comparable series."""
    report = _validated(report)
    definition = _definitions((metric_id,))[0]
    binding = report.binding
    payload = {
        "dataset_id": binding.dataset_id,
        "dataset_version": binding.dataset_version,
        "dataset_revision": binding.dataset_revision,
        "case_ids": [case.case_id for case in report.cases],
        "computed_case_ids": [
            case.case_id for case in report.cases
            if next(metric for metric in case.metrics if metric.metric_id == metric_id).status == "computed"
        ],
        "context_binding": binding.context_binding,
        "metric_id": definition.metric_id,
        "metric_version": definition.metric_version,
        "judge_model_id": binding.judge_model_id if metric_id in _JUDGE_METRICS else None,
        "judge_prompt_sha256": binding.judge_prompt_sha256 if metric_id in _JUDGE_METRICS else None,
    }
    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def native_trends(publications: Sequence[PublishedNativeReport], metric_id: str) -> tuple[TrendGroup, ...]:
    """Group observations without interpolating, smoothing, or ordering by mtime."""
    _definitions((metric_id,))
    groups: dict[str, list[TrendPoint]] = {}
    for published in publications:
        report = _validated(published.report)
        group_id = metric_binding_group(report, metric_id)
        aggregate = next(item for item in report.aggregates if item.metric_id == metric_id)
        groups.setdefault(group_id, []).append(TrendPoint(
            report.run_id, report.digest, published.published_at.isoformat(),
            report.status, aggregate, report.binding.generator_model_id,
            report.binding.generation_binding, report.binding.retrieval_binding,
            report.binding.judge_binding,
        ))
    definition = _definitions((metric_id,))[0]
    return tuple(TrendGroup(group_id, metric_id, definition.metric_version, tuple(sorted(
        points, key=lambda item: (item.published_at, item.run_id, item.report_digest),
    ))) for group_id, points in sorted(groups.items()))


def native_failures(report: NativeReport) -> FailureAnalysis:
    """Classify only explicit deterministic failures and missing prerequisites."""
    report = _validated(report)
    findings: list[FailureFinding] = []
    for case in report.cases:
        for metric in case.metrics:
            category: str | None = None
            if metric.status == "unavailable":
                category = "unavailable_prerequisite"
            elif metric.status == "computed":
                if metric.metric_id == "native.fallback_correctness" and metric.value is False:
                    category = "fallback_expectation_mismatch"
                elif metric.metric_id == "native.citation_index_validity" and metric.value < 1.0:
                    category = "invalid_citation_index"
                elif metric.metric_id == "native.keyword_recall_proxy" and metric.value < 1.0:
                    category = "missing_required_keyword"
            if category:
                findings.append(FailureFinding(
                    category, case.case_id, case.context_sha256,
                    metric.metric_id, metric.metric_version, metric.status,
                    metric.value, metric.reason_code,
                ))
    order = {category: index for index, category in enumerate(FAILURE_CATEGORIES)}
    findings.sort(key=lambda item: (order[item.category_id], item.case_id, item.metric_id))
    counts = tuple((category, sum(item.category_id == category for item in findings)) for category in FAILURE_CATEGORIES)
    return FailureAnalysis(report.run_id, report.digest, report.status, counts, tuple(findings))
