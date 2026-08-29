import json
from pathlib import Path

from scripts.diagnostics.ibm_companion_document_audit import (
    _candidates,
    _statement_evidence,
    audit_companion,
    main,
)
from bs4 import BeautifulSoup


def _fixture(tmp_path: Path, links: str = '<a href="ibm-2025_d2.htm">Annual Report to Stockholders</a>', companion: str | None = None):
    raw = tmp_path / "raw" / "IBM"
    processed = tmp_path / "processed" / "IBM"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    accession = "000000000026000001"
    html = raw / f"{accession}.html"
    html.write_text(
        "<p>Item 8. Financial Statements and Supplementary Data: Refer to pages 42 through 116 "
        "of IBM's Annual Report to Stockholders, incorporated herein by reference.</p>" + links,
        encoding="utf-8",
    )
    sections = processed / f"{accession}_sections.json"
    sections.write_text(json.dumps({"ticker": "IBM", "accession_number": "0000000000-26-000001", "filing_date": "2026-02-01", "report_date": "2025-12-31", "sections": {}}), encoding="utf-8")
    chunks = processed / f"{accession}_chunks.jsonl"
    chunks.write_text('{"chunk_id":"IBM_business_0000"}\n', encoding="utf-8")
    if companion is not None:
        (raw / "ibm-2025_d2.htm").write_text(companion, encoding="utf-8")
    return html, sections, chunks, raw.parent, processed.parent


def test_selects_relative_companion_candidate_and_records_missing(tmp_path):
    html, sections, chunks, _, _ = _fixture(tmp_path)
    report = audit_companion(html, sections, chunks)
    assert report["status"] == "companion_missing"
    assert report["incorporation_evidence"]["page_range"] == {"start": 42, "end": 116}
    assert report["companion_candidates"][0]["provenance"] == "relative_filing_link"
    assert report["gates"]["unique_companion"] == "fail"
    assert report["overall_pass"] is False


def test_external_candidate_is_not_treated_as_local_companion(tmp_path):
    html, *_ = _fixture(tmp_path, '<a href="https://example.test/annual.htm">Annual Report to Stockholders</a>')
    candidates = _candidates(BeautifulSoup(html.read_bytes(), "lxml"), html.parent)
    assert candidates[0]["provenance"] == "external_link"
    assert candidates[0]["exists"] is False


def test_ambiguous_candidates_are_not_selected(tmp_path):
    links = '<a href="a.htm">Annual Report to Stockholders</a><a href="b.htm">Annual Report to Stockholders</a>'
    html, sections, chunks, _, _ = _fixture(tmp_path, links)
    (html.parent / "a.htm").write_text("<html/>", encoding="utf-8")
    (html.parent / "b.htm").write_text("<html/>", encoding="utf-8")
    report = audit_companion(html, sections, chunks)
    assert report["status"] == "ambiguous_companion"
    assert report["selected_companion"] is None


def test_statement_evidence_detects_duplicate_missing_year_and_contamination(tmp_path):
    path = tmp_path / "companion.htm"
    table = "<table><tr><th>2025</th><th>2024</th></tr><tr><td>Total assets</td><td>2</td><td>1</td></tr></table>"
    path.write_text('<div data-page="42"></div>' + table + table + "<p>Item 9. Changes</p>" + '<div data-page="116"></div>', encoding="utf-8")
    evidence = _statement_evidence(path, {"start": 42, "end": 116})
    assert evidence["table_count"] == 2
    assert evidence["unique_fingerprints"] == 1
    assert evidence["fiscal_years"] == ["2024", "2025"]
    assert "item 9" in evidence["contamination_markers"]


def test_complete_companion_fixture_passes_content_gates(tmp_path):
    table = lambda label: f"<table><tr><th>2025</th><th>2024</th><th>2023</th></tr><tr><td>{label}</td><td>3</td><td>2</td><td>1</td></tr></table>"
    companion = '<div data-page="42"></div>' + table("Net income") + table("Total assets") + table("Net cash provided by operating activities") + '<div data-page="116"></div>'
    html, sections, chunks, *_ = _fixture(tmp_path, companion=companion)
    report = audit_companion(html, sections, chunks)
    assert report["status"] == "candidate_requires_validation"
    assert report["statement_evidence"]["page_range_resolved"] is True
    assert all(value == "pass" for name, value in report["gates"].items() if name not in {"reports_byte_identical", "input_hashes_unchanged"})
    assert report["overall_pass"] is False


def test_complete_companion_cli_passes_all_gates(tmp_path, monkeypatch):
    table = lambda label: f"<table><tr><th>2025</th><th>2024</th><th>2023</th></tr><tr><td>{label}</td><td>3</td><td>2</td><td>1</td></tr></table>"
    companion = '<div data-page="42"></div>' + table("Net income") + table("Total assets") + table("Net cash provided by operating activities") + '<div data-page="116"></div>'
    html, sections, chunks, raw, processed = _fixture(tmp_path, companion=companion)

    class DataSettings:
        data_raw_dir = raw
        data_processed_dir = processed

    monkeypatch.setattr("scripts.diagnostics.ibm_companion_document_audit.settings", DataSettings())
    output = tmp_path / "complete.json"
    assert main(["--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["result"]["overall_pass"] is True
    assert all(value == "pass" for value in report["result"]["gates"].values())


def test_broken_page_markers_leave_interval_unresolved(tmp_path):
    path = tmp_path / "companion.htm"
    path.write_text('<div data-page="41"></div><table><tr><th>2025</th><th>2024</th></tr><tr><td>Total assets</td><td>2</td><td>1</td></tr></table>', encoding="utf-8")
    evidence = _statement_evidence(path, {"start": 42, "end": 116})
    assert evidence["page_range_resolved"] is False
    assert evidence["table_count"] == 0


def test_broken_reference_has_no_false_companion(tmp_path):
    html, sections, chunks, *_ = _fixture(tmp_path, '<a href="missing.htm">Annual Report to Stockholders</a>')
    report = audit_companion(html, sections, chunks)
    assert report["status"] == "companion_missing"
    assert report["companion_candidates"][0]["decision"] == "missing_local_document"


def test_cli_is_deterministic_and_does_not_mutate_inputs(tmp_path, monkeypatch):
    html, sections, chunks, raw, processed = _fixture(tmp_path)

    class DataSettings:
        data_raw_dir = raw
        data_processed_dir = processed

    monkeypatch.setattr("scripts.diagnostics.ibm_companion_document_audit.settings", DataSettings())
    before = {path: path.read_bytes() for path in (html, sections, chunks)}
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    assert main(["--output", str(first)]) == 0
    assert main(["--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()
    assert {path: path.read_bytes() for path in before} == before


def test_real_ibm_audit_is_missing_companion_without_changing_corpus():
    root = Path(__file__).resolve().parents[1] / "data"
    html = root / "raw" / "IBM" / "000005114326000010.html"
    sections = root / "processed" / "IBM" / "000005114326000010_sections.json"
    chunks = root / "processed" / "IBM" / "000005114326000010_chunks.jsonl"
    if not html.is_file():
        return
    report = audit_companion(html, sections, chunks)
    assert report["status"] == "companion_missing"
    assert report["incorporation_evidence"]["page_range"] == {"start": 42, "end": 116}
