"""Provider-free, versioned native metric and report contract.

This module records existing judge scores; it never invokes a judge. It uses
the exact evidence string rendered for generation and judging for the three
deterministic checks. Native reports are private domain artifacts, not legacy
public-report-v1 payloads or a publication decision.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, replace
from types import SimpleNamespace
from typing import Any, Literal, Mapping, Sequence

from src.evaluation.dataset_binding import EVALUATION_DATASET_ID, EVALUATION_DATASET_VERSION
from src.evaluation.evaluator import (
    check_fallback_correctness,
    compute_citation_correctness,
    compute_recall_proxy,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.retrieval.canonical_json import canonical_json_bytes

PROTOCOL_NAME = "native-evaluation"
PROTOCOL_VERSION = 1
METRIC_VERSION = 1
MAX_CASES = 5000
MAX_REPORT_BYTES = 2_000_000
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,255}$")
_CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_JUDGE_IDS = (
    "native.faithfulness",
    "native.answer_relevancy",
    "native.context_precision",
)
_REASONS = frozenset({
    "missing_generation", "missing_context", "missing_ground_truth",
    "judge_not_run", "judge_not_configured", "no_citations",
    "no_required_keywords", "missing_fallback_expectation",
})
_ALLOWED_REASONS = {
    "native.faithfulness": {
        "unavailable": {"missing_generation", "missing_context", "missing_ground_truth", "judge_not_run", "judge_not_configured"},
        "not_applicable": set(),
    },
    "native.answer_relevancy": {
        "unavailable": {"missing_generation", "missing_context", "missing_ground_truth", "judge_not_run", "judge_not_configured"},
        "not_applicable": set(),
    },
    "native.context_precision": {
        "unavailable": {"missing_generation", "missing_context", "missing_ground_truth", "judge_not_run", "judge_not_configured"},
        "not_applicable": set(),
    },
    "native.citation_index_validity": {
        "unavailable": {"missing_generation", "missing_context"},
        "not_applicable": {"no_citations"},
    },
    "native.keyword_recall_proxy": {
        "unavailable": {"missing_context"},
        "not_applicable": {"no_required_keywords"},
    },
    "native.fallback_correctness": {
        "unavailable": {"missing_generation"},
        "not_applicable": {"missing_fallback_expectation"},
    },
}


class NativeProtocolError(ValueError):
    """Invalid input, unsupported version, or inconsistent native report."""


class InvalidNativeInput(NativeProtocolError):
    """A frozen case or its binding is invalid before report construction."""


class MissingGroundTruth(InvalidNativeInput):
    """Bound judge scores were supplied without their required reference."""


class EmptyEvaluationSet(InvalidNativeInput):
    """A report cannot be created from zero selected cases."""


class CorruptNativeReport(NativeProtocolError):
    """A serialized report is malformed or internally inconsistent."""


class UnsupportedNativeProtocolVersion(CorruptNativeReport):
    """The report is not the exact native protocol/version supported here."""


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    metric_version: int
    label: str
    meaning: str
    value_kind: Literal["ratio", "boolean"]
    aggregate_kind: Literal["mean", "success_rate"]
    direction: Literal["higher_is_better"]
    source: Literal["precomputed_native_judge", "deterministic"]
    minimum: float
    maximum: float
    required_inputs: tuple[str, ...]


METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        "native.faithfulness", 1, "Faithfulness",
        "Existing native judge estimate of answer claims supported by the same rendered evidence; not deterministic claim verification.",
        "ratio", "mean", "higher_is_better", "precomputed_native_judge", 0.0, 1.0,
        ("answer", "rendered_context", "ground_truth", "bound_judge_score"),
    ),
    MetricDefinition(
        "native.answer_relevancy", 1, "Answer relevancy",
        "Existing native judge estimate of how well the answer addresses the question against ground truth.",
        "ratio", "mean", "higher_is_better", "precomputed_native_judge", 0.0, 1.0,
        ("answer", "rendered_context", "ground_truth", "bound_judge_score"),
    ),
    MetricDefinition(
        "native.context_precision", 1, "Context precision",
        "Existing native judge estimate of the fraction of retrieved chunks useful for the answer.",
        "ratio", "mean", "higher_is_better", "precomputed_native_judge", 0.0, 1.0,
        ("answer", "rendered_context", "ground_truth", "bound_judge_score"),
    ),
    MetricDefinition(
        "native.citation_index_validity", 1, "Citation index validity",
        "Fraction of Source N references whose indices exist in the rendered evidence; not claim support.",
        "ratio", "mean", "higher_is_better", "deterministic", 0.0, 1.0,
        ("answer", "rendered_context"),
    ),
    MetricDefinition(
        "native.keyword_recall_proxy", 1, "Keyword recall proxy",
        "Fraction of explicit required keywords found in rendered evidence; not Recall@K or semantic relevance.",
        "ratio", "mean", "higher_is_better", "deterministic", 0.0, 1.0,
        ("rendered_context", "required_keywords"),
    ),
    MetricDefinition(
        "native.fallback_correctness", 1, "Fallback correctness",
        "Whether the answer's existing insufficient-information fallback phrase matches the case expectation.",
        "boolean", "success_rate", "higher_is_better", "deterministic", 0.0, 1.0,
        ("answer", "expects_fallback"),
    ),
)


def validate_metric_definitions(definitions: Sequence[MetricDefinition]) -> None:
    """Reject ambiguous metric IDs or invalid semantic-version declarations."""
    ids: set[str] = set()
    if not definitions:
        raise NativeProtocolError("native metric registry is empty")
    for definition in definitions:
        if definition.metric_id in ids:
            raise NativeProtocolError(f"duplicate metric ID: {definition.metric_id}")
        ids.add(definition.metric_id)
        if not re.fullmatch(r"native\.[a-z][a-z0-9_]*", definition.metric_id):
            raise NativeProtocolError("metric ID is not canonical")
        if type(definition.metric_version) is not int or definition.metric_version < 1:
            raise NativeProtocolError("metric version must be a positive integer")
        if definition.minimum != 0.0 or definition.maximum != 1.0:
            raise NativeProtocolError("native metric range must be explicitly [0, 1]")


validate_metric_definitions(METRIC_DEFINITIONS)


@dataclass(frozen=True)
class NativeEngineCapabilities:
    provider_free: Literal[True] = True
    computes_judge_scores: Literal[False] = False
    requires_bound_judge_scores: Literal[True] = True


NATIVE_CAPABILITIES = NativeEngineCapabilities()


@dataclass(frozen=True)
class NativePreflight:
    total_cases: int
    bound_judge_cases: int
    cases_requiring_external_judging: int
    core_provider_calls: Literal[0] = 0


@dataclass(frozen=True)
class NativeCaseInput:
    case_id: str
    answer: str | None
    rendered_context: str | None
    ground_truth: str | None
    required_keywords: tuple[str, ...] | None
    expects_fallback: bool | None
    judge_scores: Mapping[str, float] | None
    generation_context_sha256: str | None = None
    judge_context_sha256: str | None = None
    generation_binding: str | None = None
    judge_binding: str | None = None


@dataclass(frozen=True)
class NativeReportBinding:
    engine_id: Literal["native"]
    engine_version: int
    dataset_id: str
    dataset_version: str
    dataset_revision: str
    generator_model_id: str
    generator_model_fingerprint: str
    generation_prompt_sha256: str
    generation_binding: str
    retrieval_binding: str
    retrieval_config_fingerprint: str
    embedding_fingerprint: str
    reranker_fingerprint: str
    context_binding: str
    judge_model_id: str | None
    judge_prompt_sha256: str | None
    judge_binding: str | None


@dataclass(frozen=True)
class CaseMetricResult:
    metric_id: str
    metric_version: int
    status: Literal["computed", "unavailable", "not_applicable"]
    value: float | bool | None
    reason_code: str | None


@dataclass(frozen=True)
class NativeCaseResult:
    case_id: str
    context_sha256: str | None
    metrics: tuple[CaseMetricResult, ...]


@dataclass(frozen=True)
class AggregateMetricResult:
    metric_id: str
    metric_version: int
    status: Literal["computed", "unavailable", "not_applicable"]
    value: float | None
    total_cases: int
    denominator: int
    unavailable_count: int
    not_applicable_count: int


@dataclass(frozen=True)
class NativeReport:
    protocol: str
    protocol_version: int
    run_id: str
    status: Literal["complete", "incomplete"]
    binding: NativeReportBinding
    metric_definitions: tuple[MetricDefinition, ...]
    cases: tuple[NativeCaseResult, ...]
    aggregates: tuple[AggregateMetricResult, ...]
    digest: str


def _safe_identifier(value: Any, label: str, *, case_id: bool = False) -> str:
    pattern = _CASE_ID if case_id else _IDENTIFIER
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise NativeProtocolError(f"{label} is not a bounded identifier")
    folded = value.casefold()
    if (
        folded.startswith(("sk-", "gsk_", "ghp_", "bearer ", "file:"))
        or value.startswith(("/", "\\", "~"))
        or re.match(r"^[A-Za-z]:[/\\]", value)
        or "://" in value
        or "\\" in value
        or ".." in value.split("/")
    ):
        raise NativeProtocolError(f"{label} contains a path or credential")
    return value


def _fingerprint(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise NativeProtocolError(f"{label} must be a sha256 fingerprint")
    return value


def _validate_binding(binding: NativeReportBinding) -> None:
    if binding.engine_id != "native" or type(binding.engine_version) is not int or binding.engine_version != 1:
        raise NativeProtocolError("unsupported native engine identity/version")
    if binding.dataset_id != EVALUATION_DATASET_ID or binding.dataset_version != EVALUATION_DATASET_VERSION:
        raise NativeProtocolError("dataset identity/version does not match API-006")
    _fingerprint(binding.dataset_revision, "dataset_revision")
    _safe_identifier(binding.generator_model_id, "generator_model_id")
    for name in (
        "generator_model_fingerprint", "generation_prompt_sha256",
        "generation_binding", "retrieval_binding", "retrieval_config_fingerprint",
        "embedding_fingerprint", "reranker_fingerprint", "context_binding",
    ):
        _fingerprint(getattr(binding, name), name)
    if len({binding.judge_model_id is None, binding.judge_prompt_sha256 is None, binding.judge_binding is None}) != 1:
        raise NativeProtocolError("judge model, prompt, and judge binding must all be present or absent")
    if binding.judge_model_id is not None:
        _safe_identifier(binding.judge_model_id, "judge_model_id")
        _fingerprint(binding.judge_prompt_sha256, "judge_prompt_sha256")
        _fingerprint(binding.judge_binding, "judge_binding")


def _ratio(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise NativeProtocolError(f"{label} must be a finite ratio in [0, 1]")
    return float(value)


def _metric(metric_id: str, status: str, value: float | bool | None, reason: str | None = None) -> CaseMetricResult:
    return CaseMetricResult(metric_id, METRIC_VERSION, status, value, reason)


def _validate_case_input(case: NativeCaseInput, binding: NativeReportBinding) -> None:
    _safe_identifier(case.case_id, "case_id", case_id=True)
    for name, maximum in (("answer", 100_000), ("rendered_context", 1_000_000), ("ground_truth", 20_000)):
        value = getattr(case, name)
        if value is not None and (not isinstance(value, str) or len(value) > maximum):
            raise NativeProtocolError(f"{name} must be bounded text or null")
    if case.required_keywords is not None:
        if not isinstance(case.required_keywords, tuple) or len(case.required_keywords) > 100:
            raise NativeProtocolError("required_keywords must be a bounded tuple")
        if any(not isinstance(word, str) or not word or len(word) > 256 for word in case.required_keywords):
            raise NativeProtocolError("required_keywords contains invalid text")
    if case.expects_fallback is not None and type(case.expects_fallback) is not bool:
        raise NativeProtocolError("expects_fallback must be boolean or null")
    if case.generation_binding is not None:
        _fingerprint(case.generation_binding, "case generation_binding")
        if case.generation_binding != binding.generation_binding:
            raise NativeProtocolError("mixed generation bindings")
    if case.judge_binding is not None:
        _fingerprint(case.judge_binding, "case judge_binding")
        if case.judge_binding != binding.judge_binding:
            raise NativeProtocolError("mixed judge bindings")
    if case.answer is not None and case.generation_binding is None:
        raise NativeProtocolError("completed generation requires its binding")
    if case.answer is not None and case.generation_context_sha256 is None:
        raise NativeProtocolError("completed generation requires its rendered-evidence hash")
    if case.rendered_context:
        if not parse_evidence_context(case.rendered_context):
            raise NativeProtocolError("rendered_context is not canonical source evidence")
    context_sha256 = (
        "sha256:" + hashlib.sha256(case.rendered_context.encode("utf-8")).hexdigest()
        if case.rendered_context is not None else None
    )
    if case.generation_context_sha256 is not None:
        _fingerprint(case.generation_context_sha256, "generation_context_sha256")
        if case.generation_context_sha256 != context_sha256:
            raise NativeProtocolError("generation did not receive the same rendered evidence")
    if case.judge_context_sha256 is not None:
        _fingerprint(case.judge_context_sha256, "judge_context_sha256")
        if case.judge_context_sha256 != context_sha256:
            raise NativeProtocolError("judging did not receive the same rendered evidence")
    if case.judge_scores is not None:
        if binding.judge_binding is None:
            raise NativeProtocolError("judge scores require a judge binding")
        if case.judge_binding is None:
            raise NativeProtocolError("judge scores require their case judge binding")
        if case.generation_context_sha256 is None or case.judge_context_sha256 is None:
            raise NativeProtocolError("judge scores require matching generation/judge evidence hashes")
        if case.answer is None or case.rendered_context is None:
            raise NativeProtocolError("judge scores require answer and rendered context")
        if not case.ground_truth:
            raise MissingGroundTruth("judge scores require ground truth")
        if not isinstance(case.judge_scores, Mapping) or set(case.judge_scores) != set(_JUDGE_IDS):
            raise NativeProtocolError("judge scores must contain exactly three native metric IDs")
        for metric_id in _JUDGE_IDS:
            _ratio(case.judge_scores[metric_id], metric_id)


def evaluate_case(case: NativeCaseInput, binding: NativeReportBinding) -> NativeCaseResult:
    """Apply existing native deterministic semantics and record bound judge scores."""
    _validate_case_input(case, binding)
    metrics: list[CaseMetricResult] = []
    for metric_id in _JUDGE_IDS:
        if case.answer is None:
            metrics.append(_metric(metric_id, "unavailable", None, "missing_generation"))
        elif case.rendered_context is None:
            metrics.append(_metric(metric_id, "unavailable", None, "missing_context"))
        elif not case.ground_truth:
            metrics.append(_metric(metric_id, "unavailable", None, "missing_ground_truth"))
        elif binding.judge_binding is None:
            metrics.append(_metric(metric_id, "unavailable", None, "judge_not_configured"))
        elif case.judge_scores is None:
            metrics.append(_metric(metric_id, "unavailable", None, "judge_not_run"))
        else:
            metrics.append(_metric(metric_id, "computed", _ratio(case.judge_scores[metric_id], metric_id)))

    if case.answer is None:
        metrics.append(_metric("native.citation_index_validity", "unavailable", None, "missing_generation"))
    elif case.rendered_context is None:
        metrics.append(_metric("native.citation_index_validity", "unavailable", None, "missing_context"))
    else:
        blocks = parse_evidence_context(case.rendered_context)
        score = compute_citation_correctness(case.answer, len(blocks))
        metrics.append(_metric("native.citation_index_validity", "computed", score) if score is not None
                       else _metric("native.citation_index_validity", "not_applicable", None, "no_citations"))

    if not case.required_keywords:
        metrics.append(_metric("native.keyword_recall_proxy", "not_applicable", None, "no_required_keywords"))
    elif case.rendered_context is None:
        metrics.append(_metric("native.keyword_recall_proxy", "unavailable", None, "missing_context"))
    else:
        blocks = parse_evidence_context(case.rendered_context)
        chunks = [SimpleNamespace(text=block["text"]) for block in blocks]
        score = compute_recall_proxy(list(case.required_keywords), chunks)
        metrics.append(_metric("native.keyword_recall_proxy", "computed", score))

    if case.expects_fallback is None:
        metrics.append(_metric("native.fallback_correctness", "not_applicable", None, "missing_fallback_expectation"))
    elif case.answer is None:
        metrics.append(_metric("native.fallback_correctness", "unavailable", None, "missing_generation"))
    else:
        metrics.append(_metric("native.fallback_correctness", "computed",
                               check_fallback_correctness(case.answer, case.expects_fallback)))
    return NativeCaseResult(
        case.case_id,
        "sha256:" + hashlib.sha256(case.rendered_context.encode("utf-8")).hexdigest()
        if case.rendered_context is not None else None,
        tuple(metrics),
    )


def _aggregate(cases: Sequence[NativeCaseResult]) -> tuple[AggregateMetricResult, ...]:
    results: list[AggregateMetricResult] = []
    for definition in METRIC_DEFINITIONS:
        rows = [next(item for item in case.metrics if item.metric_id == definition.metric_id) for case in cases]
        values = [float(row.value) for row in rows if row.status == "computed"]
        unavailable_count = sum(row.status == "unavailable" for row in rows)
        not_applicable_count = sum(row.status == "not_applicable" for row in rows)
        status = "computed" if values else ("unavailable" if unavailable_count else "not_applicable")
        # Sorting makes the sum independent of case order and fsum avoids
        # per-case rounding drift. Existing reports display four decimals.
        value = round(math.fsum(sorted(values)) / len(values), 4) if values else None
        results.append(AggregateMetricResult(
            definition.metric_id, definition.metric_version, status, value,
            len(rows), len(values), unavailable_count, not_applicable_count,
        ))
    return tuple(results)


def _validate_case_batch(cases: Sequence[NativeCaseInput], binding: NativeReportBinding) -> None:
    _validate_binding(binding)
    if not cases:
        raise EmptyEvaluationSet("empty evaluation set cannot produce a native report")
    if len(cases) > MAX_CASES:
        raise NativeProtocolError("too many evaluation cases")
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise NativeProtocolError("duplicate case ID")
    for case in cases:
        _validate_case_input(case, binding)


def preflight_native_cases(
    cases: Sequence[NativeCaseInput], binding: NativeReportBinding,
) -> NativePreflight:
    """Validate frozen inputs and expose unmet judge coverage without pricing it.

    EVAL-003 owns provider pricing, attempts, and budgets. This core never
    makes a provider call; missing scores are a required external input, not
    a zero-cost promise about future judging.
    """
    _validate_case_batch(cases, binding)
    bound = sum(case.judge_scores is not None for case in cases)
    eligible_unjudged = sum(
        case.judge_scores is None
        and case.answer is not None
        and case.rendered_context is not None
        and bool(case.ground_truth)
        for case in cases
    )
    return NativePreflight(len(cases), bound, eligible_unjudged)


def _report_payload(report: NativeReport, *, include_digest: bool) -> dict[str, Any]:
    payload = asdict(report)
    if not include_digest:
        payload.pop("digest")
    return payload


def _digest(report: NativeReport) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(_report_payload(report, include_digest=False))).hexdigest()


def build_native_report(
    run_id: str,
    cases: Sequence[NativeCaseInput],
    binding: NativeReportBinding,
) -> NativeReport:
    """Build a reproducible report without provider, network, or storage I/O."""
    _safe_identifier(run_id, "run_id", case_id=True)
    _validate_case_batch(cases, binding)
    case_results = tuple(sorted((evaluate_case(case, binding) for case in cases), key=lambda row: row.case_id))
    status = "incomplete" if any(
        item.status == "unavailable" for row in case_results for item in row.metrics
    ) else "complete"
    report = NativeReport(
        PROTOCOL_NAME, PROTOCOL_VERSION, run_id, status, binding,
        METRIC_DEFINITIONS, case_results, _aggregate(case_results), "",
    )
    report = replace(report, digest=_digest(report))
    if len(canonical_report_bytes(report)) > MAX_REPORT_BYTES:
        raise NativeProtocolError("native report exceeds the size bound")
    return report


def canonical_report_bytes(report: NativeReport) -> bytes:
    """Serialize to the repository's sorted-key, finite canonical JSON."""
    return canonical_json_bytes(_report_payload(report, include_digest=True))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise NativeProtocolError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise NativeProtocolError(f"non-finite JSON constant: {value}")


def _exact_fields(value: Any, names: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != names:
        raise CorruptNativeReport(f"{label} has invalid fields")
    return value


def _parse_metric(value: Any, definition: MetricDefinition) -> CaseMetricResult:
    value = _exact_fields(value, set(CaseMetricResult.__dataclass_fields__), "case metric")
    if value["metric_id"] != definition.metric_id or type(value["metric_version"]) is not int or value["metric_version"] != definition.metric_version:
        raise NativeProtocolError("metric ID/version mismatch")
    status = value["status"]
    raw = value["value"]
    reason = value["reason_code"]
    if status == "computed":
        if reason is not None:
            raise NativeProtocolError("computed metric cannot have an unavailable reason")
        if definition.value_kind == "boolean":
            if type(raw) is not bool:
                raise NativeProtocolError("boolean metric value is malformed")
        else:
            raw = _ratio(raw, definition.metric_id)
    elif status in ("unavailable", "not_applicable"):
        if raw is not None or reason not in _REASONS or reason not in _ALLOWED_REASONS[definition.metric_id][status]:
            raise NativeProtocolError("unavailable metric value/reason is malformed")
    else:
        raise NativeProtocolError("unsupported metric status")
    return CaseMetricResult(definition.metric_id, definition.metric_version, status, raw, reason)


def parse_native_report(raw: bytes | str | Mapping[str, Any]) -> NativeReport:
    """Fail closed on legacy/future/corrupt reports; verify digest and totals."""
    try:
        if isinstance(raw, (bytes, str)):
            encoded = raw if isinstance(raw, bytes) else raw.encode("utf-8")
            if len(encoded) > MAX_REPORT_BYTES:
                raise NativeProtocolError("native report exceeds the size bound")
            payload = json.loads(
                encoded, object_pairs_hook=_unique_object, parse_constant=_reject_constant,
            )
        elif isinstance(raw, Mapping):
            encoded = canonical_json_bytes(dict(raw))
            if len(encoded) > MAX_REPORT_BYTES:
                raise NativeProtocolError("native report exceeds the size bound")
            payload = json.loads(encoded, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        else:
            raise NativeProtocolError("native report must be JSON or an object")
        payload = _exact_fields(payload, set(NativeReport.__dataclass_fields__), "native report")
        if payload["protocol"] != PROTOCOL_NAME or type(payload["protocol_version"]) is not int or payload["protocol_version"] != PROTOCOL_VERSION:
            raise UnsupportedNativeProtocolVersion("unsupported native protocol/version")
        run_id = _safe_identifier(payload["run_id"], "run_id", case_id=True)
        raw_binding = _exact_fields(payload["binding"], set(NativeReportBinding.__dataclass_fields__), "binding")
        binding = NativeReportBinding(**raw_binding)
        _validate_binding(binding)
        expected_definitions = json.loads(canonical_json_bytes([asdict(item) for item in METRIC_DEFINITIONS]))
        if payload["metric_definitions"] != expected_definitions:
            raise NativeProtocolError("metric definitions or versions differ from the native registry")
        raw_cases = payload["cases"]
        if not isinstance(raw_cases, list) or not 1 <= len(raw_cases) <= MAX_CASES:
            raise NativeProtocolError("native cases are empty or oversized")
        cases: list[NativeCaseResult] = []
        for raw_case in raw_cases:
            raw_case = _exact_fields(raw_case, set(NativeCaseResult.__dataclass_fields__), "case")
            case_id = _safe_identifier(raw_case["case_id"], "case_id", case_id=True)
            raw_metrics = raw_case["metrics"]
            if not isinstance(raw_metrics, list) or len(raw_metrics) != len(METRIC_DEFINITIONS):
                raise NativeProtocolError("case metric count is invalid")
            context_sha256 = raw_case["context_sha256"]
            if context_sha256 is not None:
                _fingerprint(context_sha256, "context_sha256")
            metrics = tuple(_parse_metric(raw_metric, definition) for raw_metric, definition in zip(raw_metrics, METRIC_DEFINITIONS))
            if context_sha256 is None and any(item.status == "computed" for item in metrics[:5]):
                raise CorruptNativeReport("computed evidence metrics require a context hash")
            if binding.judge_binding is None and any(item.status == "computed" for item in metrics[:3]):
                raise CorruptNativeReport("computed judge metrics require a judge binding")
            cases.append(NativeCaseResult(case_id, context_sha256, metrics))
        if [case.case_id for case in cases] != sorted({case.case_id for case in cases}):
            raise NativeProtocolError("case IDs must be unique and ordered")
        expected_status = "incomplete" if any(
            item.status == "unavailable" for row in cases for item in row.metrics
        ) else "complete"
        if payload["status"] != expected_status:
            raise NativeProtocolError("report completeness status is inconsistent")
        aggregates = _aggregate(cases)
        if payload["aggregates"] != [asdict(item) for item in aggregates]:
            raise NativeProtocolError("aggregate values or denominators are inconsistent")
        report = NativeReport(
            PROTOCOL_NAME, PROTOCOL_VERSION, run_id, expected_status, binding,
            METRIC_DEFINITIONS, tuple(cases), aggregates, payload["digest"],
        )
        if report.digest != _digest(report):
            raise CorruptNativeReport("native report digest mismatch")
        return report
    except NativeProtocolError as error:
        if isinstance(error, CorruptNativeReport):
            raise
        raise CorruptNativeReport(str(error)) from error
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError, OverflowError) as error:
        raise CorruptNativeReport("native report is malformed") from error
