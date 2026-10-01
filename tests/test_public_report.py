import json

import pytest

from src.evaluation.public_report import (
    PublicReportError,
    example_report,
    get_public_report,
    list_public_reports,
    normalize_public_report,
    publish_public_report,
)


def test_example_report_round_trips_through_public_publisher(tmp_path) -> None:
    path = publish_public_report(example_report(), root=tmp_path)

    assert path.name == "recorded-demo-v1.json"
    assert get_public_report("recorded-demo-v1", root=tmp_path)["cases"][0]["language"] == "en"
    assert list_public_reports(root=tmp_path)[0]["case_count"] == 2


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda payload: payload.update({"cases": []}), "cases must be a non-empty list"),
        (lambda payload: payload["cases"].append(payload["cases"][0]), "duplicate case_id"),
        (lambda payload: payload["provenance"].pop("rubric_fingerprint"), "missing provenance"),
        (lambda payload: payload["cases"][0].update({"scores": {"answer_relevancy": 2}}), "between 0 and 1"),
        (lambda payload: payload.update({"run_id": "..\\outside"}), "unsupported characters"),
    ],
)
def test_public_report_rejects_invalid_or_unsafe_payloads(mutator, message) -> None:
    payload = example_report("report-under-test")
    mutator(payload)

    with pytest.raises(PublicReportError, match=message):
        normalize_public_report(payload)


def test_publisher_refuses_overwrite_and_reader_ignores_malformed_files(tmp_path) -> None:
    publish_public_report(example_report("valid"), root=tmp_path)
    with pytest.raises(PublicReportError, match="already exists"):
        publish_public_report(example_report("valid"), root=tmp_path)
    (tmp_path / "malformed.json").write_text(json.dumps({"run_id": "malformed"}), encoding="utf-8")

    assert [item["run_id"] for item in list_public_reports(root=tmp_path)] == ["valid"]
