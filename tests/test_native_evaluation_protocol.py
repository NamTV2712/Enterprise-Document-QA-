"""Hand-computable contracts for the provider-free native evaluation protocol."""

from dataclasses import asdict, replace
import hashlib
import json

import pytest

from src.api.registry import RegistryService
from src.evaluation.dataset_binding import (
    EVALUATION_DATASET_ID,
    EVALUATION_DATASET_VERSION,
    evaluation_dataset_revision,
)
from src.evaluation.native_protocol import (
    METRIC_DEFINITIONS,
    MAX_CASES,
    MAX_REPORT_BYTES,
    NativeCaseInput,
    NativeProtocolError,
    MissingGroundTruth,
    EmptyEvaluationSet,
    CorruptNativeReport,
    UnsupportedNativeProtocolVersion,
    NativeReportBinding,
    build_native_report,
    canonical_report_bytes,
    parse_native_report,
    preflight_native_cases,
    validate_metric_definitions,
)
from src.evaluation.test_set import TEST_SET


def binding(**overrides):
    base = NativeReportBinding(
        engine_id="native",
        engine_version=1,
        dataset_id=EVALUATION_DATASET_ID,
        dataset_version=EVALUATION_DATASET_VERSION,
        dataset_revision=evaluation_dataset_revision(TEST_SET),
        generator_model_id="openai/gpt-oss-120b",
        generator_model_fingerprint="sha256:" + "5" * 64,
        generation_prompt_sha256="sha256:" + "6" * 64,
        generation_binding="sha256:" + "1" * 64,
        retrieval_binding="sha256:" + "2" * 64,
        retrieval_config_fingerprint="sha256:" + "7" * 64,
        embedding_fingerprint="sha256:" + "8" * 64,
        reranker_fingerprint="sha256:" + "9" * 64,
        context_binding="sha256:" + "3" * 64,
        judge_model_id="openai/gpt-oss-120b",
        judge_prompt_sha256="sha256:" + "a" * 64,
        judge_binding="sha256:" + "4" * 64,
    )
    return replace(base, **overrides)


def case(case_id="case-a", **overrides):
    context = "[Source 1] Apple filing\nApple total net sales were 391,035.\n"
    context_sha256 = "sha256:" + hashlib.sha256(context.encode("utf-8")).hexdigest()
    base = NativeCaseInput(
        case_id=case_id,
        answer="Apple reported 391,035 [Source 1] and an invalid [Source 3].",
        rendered_context=context,
        ground_truth="Apple total net sales were 391,035.",
        required_keywords=("391,035", "Deloitte"),
        expects_fallback=False,
        judge_scores={
            "native.faithfulness": 0.25,
            "native.answer_relevancy": 1.0,
            "native.context_precision": 0.5,
        },
        generation_context_sha256=context_sha256,
        judge_context_sha256=context_sha256,
        generation_binding="sha256:" + "1" * 64,
        judge_binding="sha256:" + "4" * 64,
    )
    if overrides.get("rendered_context", context) is None:
        overrides.setdefault("generation_context_sha256", None)
        overrides.setdefault("judge_context_sha256", None)
    if overrides.get("judge_scores", base.judge_scores) is None:
        overrides.setdefault("judge_context_sha256", None)
        overrides.setdefault("judge_binding", None)
    if overrides.get("answer", base.answer) is None:
        overrides.setdefault("generation_binding", None)
    return replace(base, **overrides)


def metric(report, case_id, metric_id):
    row = next(row for row in report.cases if row.case_id == case_id)
    return next(item for item in row.metrics if item.metric_id == metric_id)


def aggregate(report, metric_id):
    return next(item for item in report.aggregates if item.metric_id == metric_id)


def test_definition_identity_order_versions_and_semantics() -> None:
    assert [item.metric_id for item in METRIC_DEFINITIONS] == [
        "native.faithfulness", "native.answer_relevancy", "native.context_precision",
        "native.citation_index_validity", "native.keyword_recall_proxy",
        "native.fallback_correctness",
    ]
    assert len({item.metric_id for item in METRIC_DEFINITIONS}) == 6
    assert {item.metric_version for item in METRIC_DEFINITIONS} == {1}
    assert {item.direction for item in METRIC_DEFINITIONS} == {"higher_is_better"}
    assert [item.value_kind for item in METRIC_DEFINITIONS] == [
        "ratio", "ratio", "ratio", "ratio", "ratio", "boolean",
    ]
    assert "not claim support" in METRIC_DEFINITIONS[3].meaning
    assert "not Recall@K" in METRIC_DEFINITIONS[4].meaning
    with pytest.raises(NativeProtocolError, match="duplicate metric ID"):
        validate_metric_definitions([METRIC_DEFINITIONS[0], METRIC_DEFINITIONS[0]])


def test_api_006_dataset_binding_is_byte_identical() -> None:
    # The registry and protocol must use the same helper, not merely two
    # coincidentally equal revision algorithms.
    assert evaluation_dataset_revision(TEST_SET).startswith("sha256:")
    assert RegistryService._evaluation_dataset.__globals__["evaluation_dataset_revision"] is evaluation_dataset_revision
    previous_api_006_bytes = json.dumps(
        [asdict(item) for item in TEST_SET], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert evaluation_dataset_revision(TEST_SET) == "sha256:" + hashlib.sha256(previous_api_006_bytes).hexdigest()


def test_per_case_native_scores_are_exact_and_zero_is_computed() -> None:
    report = build_native_report("run-a", [case()], binding())
    assert report.protocol_version == 1
    assert metric(report, "case-a", "native.faithfulness").value == 0.25
    assert metric(report, "case-a", "native.citation_index_validity").value == 0.5
    assert metric(report, "case-a", "native.keyword_recall_proxy").value == 0.5
    assert metric(report, "case-a", "native.fallback_correctness").value is True
    assert metric(report, "case-a", "native.fallback_correctness").status == "computed"

    zero = build_native_report("run-zero", [case(
        answer="The answer cites [Source 9] and is a fallback: could not find sufficient information",
        required_keywords=("absent",),
        expects_fallback=False,
        judge_scores={
            "native.faithfulness": 0.0,
            "native.answer_relevancy": 0.0,
            "native.context_precision": 0.0,
        },
    )], binding())
    assert metric(zero, "case-a", "native.citation_index_validity").value == 0.0
    assert metric(zero, "case-a", "native.keyword_recall_proxy").value == 0.0
    assert metric(zero, "case-a", "native.fallback_correctness").value is False
    assert aggregate(zero, "native.fallback_correctness").value == 0.0


def test_missing_prerequisites_are_not_zero_and_denominators_are_explicit() -> None:
    missing = case("case-b", answer=None, rendered_context=None, judge_scores=None,
                   required_keywords=None, expects_fallback=None)
    report = build_native_report("run-missing", [case(), missing], binding())
    assert report.status == "incomplete"
    faith = metric(report, "case-b", "native.faithfulness")
    assert faith.status == "unavailable" and faith.value is None
    assert faith.reason_code == "missing_generation"
    recall = metric(report, "case-b", "native.keyword_recall_proxy")
    assert recall.status == "not_applicable" and recall.value is None
    assert aggregate(report, "native.faithfulness").denominator == 1
    assert aggregate(report, "native.faithfulness").unavailable_count == 1
    assert aggregate(report, "native.keyword_recall_proxy").not_applicable_count == 1

    no_citation = build_native_report("run-no-citation", [case(
        answer="Apple reported 391,035.", required_keywords=(), judge_scores=None,
    )], binding(judge_model_id=None, judge_prompt_sha256=None, judge_binding=None))
    assert metric(no_citation, "case-a", "native.citation_index_validity").status == "not_applicable"
    assert metric(no_citation, "case-a", "native.keyword_recall_proxy").status == "not_applicable"
    assert aggregate(no_citation, "native.citation_index_validity").value is None
    assert aggregate(no_citation, "native.citation_index_validity").denominator == 0

    without_truth = build_native_report("run-no-truth", [case(
        judge_scores=None, ground_truth=None,
    )], binding(judge_model_id=None, judge_prompt_sha256=None, judge_binding=None))
    assert metric(without_truth, "case-a", "native.answer_relevancy").reason_code == "missing_ground_truth"


def test_aggregation_is_order_independent_and_rounds_only_final_mean() -> None:
    first = case("case-a", judge_scores={
        "native.faithfulness": 0.00004,
        "native.answer_relevancy": 0.1,
        "native.context_precision": 0.3,
    })
    second = case("case-b", judge_scores={
        "native.faithfulness": 0.00006,
        "native.answer_relevancy": 0.2,
        "native.context_precision": 0.4,
    })
    left = build_native_report("run-order", [second, first], binding())
    right = build_native_report("run-order", [first, second], binding())
    assert left == right
    assert [row.case_id for row in left.cases] == ["case-a", "case-b"]
    assert aggregate(left, "native.faithfulness").value == 0.0001
    assert aggregate(left, "native.faithfulness").denominator == 2
    assert canonical_report_bytes(left) == canonical_report_bytes(right)


def test_report_round_trip_digest_and_no_private_inputs() -> None:
    report = build_native_report("run-roundtrip", [case()], binding())
    encoded = canonical_report_bytes(report)
    assert parse_native_report(encoded) == report
    assert parse_native_report(asdict(report)) == report
    assert b"391,035" not in encoded  # answer, truth, and evidence are not report fields
    assert b"[Source" not in encoded
    assert b"sha256:" in encoded
    assert encoded == canonical_report_bytes(parse_native_report(encoded))
    payload = json.loads(encoded)
    assert payload["protocol"] == "native-evaluation"
    assert payload["protocol_version"] == 1
    assert payload["binding"]["dataset_revision"] == evaluation_dataset_revision(TEST_SET)
    assert payload["binding"]["judge_binding"] == binding().judge_binding
    assert payload["cases"][0]["context_sha256"] == case().generation_context_sha256


@pytest.mark.parametrize("malformation", [
    "legacy", "future", "nan", "infinity", "digest", "aggregate", "duplicate_case", "metric_reason",
])
def test_parser_fails_closed_on_legacy_future_and_corrupt_payloads(malformation: str) -> None:
    payload = json.loads(canonical_report_bytes(build_native_report("run-corrupt", [case()], binding())))
    if malformation == "legacy":
        payload.pop("protocol")
    elif malformation == "future":
        payload["protocol_version"] = 2
    elif malformation == "nan":
        payload["cases"][0]["metrics"][0]["value"] = float("nan")
    elif malformation == "infinity":
        payload["cases"][0]["metrics"][0]["value"] = float("inf")
    elif malformation == "digest":
        payload["digest"] = "sha256:" + "0" * 64
    elif malformation == "aggregate":
        payload["aggregates"][0]["value"] = 0.9
    elif malformation == "metric_reason":
        payload["cases"][0]["metrics"][0] = {
            "metric_id": "native.faithfulness", "metric_version": 1,
            "status": "not_applicable", "value": None, "reason_code": "no_citations",
        }
    else:
        payload["cases"].append(payload["cases"][0])
    with pytest.raises(NativeProtocolError):
        parse_native_report(json.dumps(payload))


def test_parser_rejects_duplicate_json_keys() -> None:
    with pytest.raises(NativeProtocolError, match="duplicate JSON key"):
        parse_native_report('{"protocol":"native-evaluation","protocol":"native-evaluation"}')


@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), -0.1, 1.1, True])
def test_non_finite_or_out_of_range_judge_score_is_rejected(bad_score) -> None:
    scores = dict(case().judge_scores)
    scores["native.faithfulness"] = bad_score
    with pytest.raises(NativeProtocolError):
        build_native_report("run-invalid", [case(judge_scores=scores)], binding())


def test_missing_truth_invalid_identity_and_empty_set_are_rejected() -> None:
    with pytest.raises(MissingGroundTruth, match="ground truth"):
        build_native_report("run-no-truth", [case(ground_truth=None)], binding())
    with pytest.raises(NativeProtocolError, match="duplicate case"):
        build_native_report("run-duplicate", [case(), case()], binding())
    with pytest.raises(EmptyEvaluationSet, match="empty"):
        build_native_report("run-empty", [], binding())
    with pytest.raises(NativeProtocolError):
        build_native_report("run-bad-path", [case()], binding(generator_model_id="C:/secrets/token"))
    with pytest.raises(NativeProtocolError):
        build_native_report("run-bad-secret", [case()], binding(generator_model_id="gsk_secret"))


def test_case_text_count_and_serialized_payload_are_bounded() -> None:
    with pytest.raises(NativeProtocolError, match="bounded text"):
        build_native_report("run-long-answer", [case(answer="x" * 100_001)], binding())
    with pytest.raises(NativeProtocolError, match="too many"):
        build_native_report("run-many", [case()] * (MAX_CASES + 1), binding())
    with pytest.raises(CorruptNativeReport, match="size bound"):
        parse_native_report(b" " * (MAX_REPORT_BYTES + 1))


def test_judge_scores_require_exact_binding_and_provider_free(monkeypatch) -> None:
    import socket
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network")))
    with pytest.raises(NativeProtocolError, match="judge binding"):
        build_native_report("run-unbound", [case()], binding(judge_binding=None))
    with pytest.raises(NativeProtocolError, match="same rendered evidence"):
        build_native_report("run-drift", [case(judge_context_sha256="sha256:" + "f" * 64)], binding())
    with pytest.raises(NativeProtocolError, match="mixed judge bindings"):
        build_native_report("run-mixed", [case(judge_binding="sha256:" + "f" * 64)], binding())
    report = build_native_report("run-offline", [case()], binding())
    assert report.status == "complete"


def test_report_errors_have_distinct_domain_types() -> None:
    report = json.loads(canonical_report_bytes(build_native_report("run-errors", [case()], binding())))
    report["protocol_version"] = 9
    with pytest.raises(UnsupportedNativeProtocolVersion):
        parse_native_report(report)
    report["protocol_version"] = 1
    report["digest"] = "sha256:" + "0" * 64
    with pytest.raises(CorruptNativeReport):
        parse_native_report(report)


def test_parser_requires_evidence_and_judge_binding_for_computed_scores() -> None:
    base = json.loads(canonical_report_bytes(build_native_report("run-bindings", [case()], binding())))
    without_context = json.loads(json.dumps(base))
    without_context["cases"][0]["context_sha256"] = None
    with pytest.raises(CorruptNativeReport, match="context hash"):
        parse_native_report(without_context)
    without_judge = json.loads(json.dumps(base))
    without_judge["binding"]["judge_model_id"] = None
    without_judge["binding"]["judge_prompt_sha256"] = None
    without_judge["binding"]["judge_binding"] = None
    with pytest.raises(CorruptNativeReport, match="judge binding"):
        parse_native_report(without_judge)


def test_preflight_reports_unpriced_external_judge_coverage_without_execution() -> None:
    unjudged = case("case-b", judge_scores=None)
    preflight = preflight_native_cases([case(), unjudged], binding())
    assert preflight.total_cases == 2
    assert preflight.bound_judge_cases == 1
    assert preflight.cases_requiring_external_judging == 1
    assert preflight.core_provider_calls == 0
