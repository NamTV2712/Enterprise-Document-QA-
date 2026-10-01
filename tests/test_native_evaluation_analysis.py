"""Hand-computable EVAL-002 facts over validated EVAL-001 reports."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import socket

import pytest

from src.evaluation.dataset_binding import evaluation_dataset_revision
from src.evaluation.native_analysis import (
    IncompatibleNativeReports,
    UnknownNativeMetric,
    compare_native_reports,
    metric_binding_group,
    native_failures,
    native_trends,
)
from src.evaluation.native_protocol import (
    NativeCaseInput,
    NativeProtocolError,
    NativeReportBinding,
    build_native_report,
    canonical_report_bytes,
)
from src.evaluation.native_publication import (
    NativePublicationError,
    PublishedNativeReport,
    UnsupportedNativePublicationVersion,
    get_published_native_report,
    list_published_native_reports,
)
from src.evaluation.test_set import TEST_SET
from src.retrieval.canonical_json import canonical_json_bytes


CONTEXT = "[Source 1] Synthetic filing\nRevenue was 10.\n"
CONTEXT_HASH = "sha256:" + hashlib.sha256(CONTEXT.encode()).hexdigest()


def binding(**changes):
    base = NativeReportBinding(
        "native", 1, "evaluation-test-set", "evaluation-test-set-v1",
        evaluation_dataset_revision(TEST_SET), "synthetic-model",
        "sha256:" + "a" * 64, "sha256:" + "b" * 64,
        "sha256:" + "c" * 64, "sha256:" + "d" * 64,
        "sha256:" + "e" * 64, "sha256:" + "f" * 64,
        "sha256:" + "1" * 64, "sha256:" + "2" * 64,
        "synthetic-judge", "sha256:" + "3" * 64,
        "sha256:" + "4" * 64,
    )
    return replace(base, **changes)


def case(case_id="case-a", *, faith=0.5, answer="Revenue was 10 [Source 1].",
         keywords=("10",), fallback=False, judge=True):
    return NativeCaseInput(
        case_id, answer, CONTEXT, "Revenue was 10.", keywords, fallback,
        {
            "native.faithfulness": faith,
            "native.answer_relevancy": 0.5,
            "native.context_precision": 0.5,
        } if judge else None,
        CONTEXT_HASH, CONTEXT_HASH if judge else None,
        "sha256:" + "c" * 64, "sha256:" + "4" * 64 if judge else None,
    )


def report(run_id, cases=None, bind=None):
    return build_native_report(run_id, cases if cases is not None else [case()], bind or binding())


def by_metric(comparison, metric_id):
    return next(item for item in comparison.metrics if item.metric_id == metric_id)


def test_direct_delta_identity_direction_and_source_immutability():
    baseline = report("baseline", [case(faith=0.5)])
    candidate = report("candidate", [case(faith=0.75)])
    before = canonical_report_bytes(baseline), canonical_report_bytes(candidate)
    result = compare_native_reports(baseline, candidate)
    assert result.eligible_for_complete_comparison is True
    assert result.eligibility_reasons == ()
    assert by_metric(result, "native.faithfulness").candidate_minus_baseline == 0.25
    assert by_metric(compare_native_reports(candidate, baseline), "native.faithfulness").candidate_minus_baseline == -0.25
    assert by_metric(compare_native_reports(baseline, baseline), "native.faithfulness").candidate_minus_baseline == 0.0
    assert result.cases[0].metrics[0].candidate_minus_baseline == 0.25
    assert (canonical_report_bytes(baseline), canonical_report_bytes(candidate)) == before
    assert (baseline.digest, candidate.digest) == (result.baseline_digest, result.candidate_digest)


def test_zero_false_and_missing_states_never_become_numeric_zero():
    zero = report("zero", [case(faith=0.0, answer="could not find sufficient information [Source 9]", keywords=("absent",))])
    positive = report("positive", [case(faith=0.75)])
    result = compare_native_reports(zero, positive)
    assert by_metric(result, "native.faithfulness").candidate_minus_baseline == 0.75
    assert by_metric(result, "native.fallback_correctness").baseline.value == 0.0
    assert result.cases[0].metrics[-1].baseline.value is False

    unjudged = report("unjudged", [case(judge=False)])
    unavailable = by_metric(compare_native_reports(unjudged, positive), "native.faithfulness")
    assert unavailable.status == "unavailable"
    assert unavailable.candidate_minus_baseline is None
    assert unavailable.baseline.denominator == 0
    assert unavailable.baseline.unavailable_count == 1
    assert "incomplete_report" in compare_native_reports(unjudged, positive).eligibility_reasons
    no_keywords = report("no-keywords", [case(keywords=())])
    not_applicable = by_metric(compare_native_reports(no_keywords, positive), "native.keyword_recall_proxy")
    assert not_applicable.status == "not_applicable"
    assert not_applicable.candidate_minus_baseline is None
    assert not_applicable.baseline.not_applicable_count == 1


def test_case_union_pairs_by_id_and_blocks_changed_aggregate_universe():
    baseline = report("baseline", [case("case-b"), case("case-a")])
    candidate = report("candidate", [case("case-c"), case("case-b")])
    result = compare_native_reports(baseline, candidate)
    assert [(item.case_id, item.pairing) for item in result.cases] == [
        ("case-a", "baseline_only"), ("case-b", "paired"), ("case-c", "candidate_only"),
    ]
    assert result.same_case_universe is False
    assert result.eligible_for_complete_comparison is False
    assert "case_universe_changed" in result.eligibility_reasons
    assert all(item.status == "incompatible" and item.candidate_minus_baseline is None for item in result.metrics)
    assert result.cases[0].metrics[0].status == "unpaired"
    assert result.cases[1].metrics[0].status == "comparable"


def test_equal_denominators_do_not_hide_different_computed_case_coverage():
    baseline = report("baseline", [case("case-a"), case("case-b", judge=False)])
    candidate = report("candidate", [case("case-a", judge=False), case("case-b")])
    result = compare_native_reports(baseline, candidate)
    faith = by_metric(result, "native.faithfulness")
    assert faith.baseline.denominator == faith.candidate.denominator == 1
    assert faith.same_computed_case_coverage is False
    assert faith.status == "incompatible"
    assert faith.reason_code == "computed_case_coverage_changed"
    assert faith.candidate_minus_baseline is None


def test_binding_and_metric_version_fail_closed():
    baseline = report("baseline")
    with pytest.raises(IncompatibleNativeReports, match="dataset"):
        compare_native_reports(baseline, report("changed", bind=binding(dataset_revision="sha256:" + "9" * 64)))
    with pytest.raises(IncompatibleNativeReports, match="context"):
        compare_native_reports(baseline, report("changed", bind=binding(context_binding="sha256:" + "9" * 64)))
    changed_judge = report("changed", bind=binding(judge_prompt_sha256="sha256:" + "9" * 64))
    mixed = compare_native_reports(baseline, changed_judge)
    assert by_metric(mixed, "native.faithfulness").status == "incompatible"
    assert by_metric(mixed, "native.citation_index_validity").status == "comparable"
    with pytest.raises(UnknownNativeMetric):
        compare_native_reports(baseline, baseline, ["native.nonexistent"])
    forged = replace(baseline, protocol_version=2)
    with pytest.raises(NativeProtocolError):
        compare_native_reports(forged, baseline)
    altered = replace(baseline, metric_definitions=(replace(baseline.metric_definitions[0], metric_version=2),) + baseline.metric_definitions[1:])
    with pytest.raises(NativeProtocolError):
        compare_native_reports(altered, baseline)


def test_metric_order_is_registry_order_independent_of_request_order():
    result = compare_native_reports(report("a"), report("b"), ["native.fallback_correctness", "native.faithfulness"])
    assert [item.metric_id for item in result.metrics] == ["native.faithfulness", "native.fallback_correctness"]


def test_failure_categories_are_direct_facts_not_judge_thresholds():
    low_judge = case(faith=0.0, answer="could not find sufficient information [Source 9]", keywords=("absent",))
    missing_judge = case("case-b", judge=False)
    analysis = native_failures(report("failures", [missing_judge, low_judge]))
    assert dict(analysis.category_counts) == {
        "fallback_expectation_mismatch": 1,
        "invalid_citation_index": 1,
        "missing_required_keyword": 1,
        "unavailable_prerequisite": 3,
    }
    assert not any(item.category_id == "faithfulness_failure" for item in analysis.findings)
    assert all(item.metric_id != "native.faithfulness" or item.category_id == "unavailable_prerequisite" for item in analysis.findings)
    assert [item.category_id for item in analysis.findings[:3]] == [
        "fallback_expectation_mismatch", "invalid_citation_index", "missing_required_keyword",
    ]
    assert "Revenue was 10" not in repr(analysis)


def test_trend_groups_compatible_history_and_orders_by_publication_time():
    first = report("run-a", [case(faith=0.5)])
    second = report("run-b", [case(faith=0.75)])
    other = report("run-c", [case(faith=0.1)], binding(context_binding="sha256:" + "9" * 64))
    publications = [
        PublishedNativeReport(datetime(2026, 2, 1, tzinfo=timezone.utc), second),
        PublishedNativeReport(datetime(2026, 3, 1, tzinfo=timezone.utc), other),
        PublishedNativeReport(datetime(2026, 1, 1, tzinfo=timezone.utc), first),
    ]
    groups = native_trends(publications, "native.faithfulness")
    assert len(groups) == 2
    matched = next(group for group in groups if group.binding_group == metric_binding_group(first, "native.faithfulness"))
    assert [point.run_id for point in matched.points] == ["run-a", "run-b"]
    assert [point.aggregate.value for point in matched.points] == [0.5, 0.75]
    assert all(len(group.points) >= 1 for group in groups)
    assert native_trends([], "native.faithfulness") == ()


def test_trend_separates_changed_coverage_and_uses_run_id_for_time_ties():
    a = report("run-a", [case("case-a"), case("case-b", judge=False)])
    b = report("run-b", [case("case-a", judge=False), case("case-b")])
    c = report("run-c", [case("case-a"), case("case-b", judge=False)])
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    groups = native_trends([
        PublishedNativeReport(instant, c),
        PublishedNativeReport(instant, b),
        PublishedNativeReport(instant, a),
    ], "native.faithfulness")
    assert len(groups) == 2
    matched = next(group for group in groups if group.binding_group == metric_binding_group(a, "native.faithfulness"))
    assert [point.run_id for point in matched.points] == ["run-a", "run-c"]


def _write_publication(root, native_report, published_at="2026-01-01T00:00:00Z"):
    payload = {"schema_version": 1, "published_at": published_at, "report": asdict(native_report)}
    path = root / f"{native_report.run_id}.native.json"
    path.write_bytes(canonical_json_bytes(payload))
    return path


def test_publication_reader_uses_existing_directory_and_validates_digest(tmp_path):
    assert list_published_native_reports(root=tmp_path) == ()
    native = report("published")
    path = _write_publication(tmp_path, native)
    loaded = get_published_native_report("published", root=tmp_path)
    assert loaded.report == native
    assert loaded.published_at == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert [item.report.run_id for item in list_published_native_reports(root=tmp_path)] == ["published"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["report"]["digest"] = "sha256:" + "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(NativePublicationError):
        get_published_native_report("published", root=tmp_path)


def test_publication_rejects_legacy_future_naive_and_path_traversal(tmp_path):
    native = report("published")
    path = _write_publication(tmp_path, native, "2026-01-01T00:00:00")
    with pytest.raises(NativePublicationError, match="timezone"):
        get_published_native_report("published", root=tmp_path)
    _write_publication(tmp_path, native)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["report"]["protocol_version"] = 2
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(UnsupportedNativePublicationVersion, match="protocol version"):
        get_published_native_report("published", root=tmp_path)
    with pytest.raises(NativePublicationError):
        get_published_native_report("../private", root=tmp_path)
    path.unlink()
    (tmp_path / "legacy.json").write_text("{}", encoding="utf-8")
    assert list_published_native_reports(root=tmp_path) == ()


def test_publication_rejects_nonfinite_and_duplicate_envelope_keys(tmp_path):
    native = report("published")
    path = _write_publication(tmp_path, native)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["report"]["cases"][0]["metrics"][0]["value"] = float("nan")
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(NativePublicationError):
        get_published_native_report("published", root=tmp_path)
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(NativePublicationError, match="duplicate"):
        get_published_native_report("published", root=tmp_path)


def test_analysis_is_provider_free(monkeypatch):
    baseline = report("baseline")
    candidate = report("candidate")
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network")))
    compare_native_reports(baseline, candidate)
    native_failures(baseline)
    native_trends([PublishedNativeReport(datetime.now(timezone.utc), baseline)], "native.faithfulness")
