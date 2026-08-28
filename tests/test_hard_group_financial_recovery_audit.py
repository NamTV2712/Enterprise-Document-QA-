import json
from pathlib import Path

import pytest

from scripts.diagnostics.hard_group_financial_recovery_audit import _find_paths, audit_filing, main


def _fixture(tmp_path: Path, ticker: str = "CVX", external: bool = False):
    processed = tmp_path / "processed" / ticker
    raw = tmp_path / "raw" / ticker
    processed.mkdir(parents=True)
    raw.mkdir(parents=True)
    accession = "000000000026000001"
    sections = processed / f"{accession}_sections.json"
    sections.write_text(
        json.dumps({
            "ticker": ticker,
            "accession_number": "0000000000-26-000001",
            "sections": {"business": "body"},
        }),
        encoding="utf-8",
    )
    chunks = processed / f"{accession}_chunks.jsonl"
    chunks.write_text(json.dumps({"chunk_id": f"{ticker}_business_0000", "section": "business"}) + "\n", encoding="utf-8")
    external_text = "Annual Report to Stockholders is incorporated by reference. " if external else ""
    table = "" if external else "<table><tr><th>2025</th><th>2024</th></tr><tr><td>Total assets</td><td>2</td><td>1</td></tr></table>"
    html = raw / f"{accession}.html"
    html.write_text(
        f"<p>Item 8. Financial Statements and Supplementary Data</p>{external_text}"
        f'<a href="#statements">Financial Table of Contents</a><div id="statements">'
        f"Consolidated Financial Statements {table}</div>",
        encoding="utf-8",
    )
    return html, sections, chunks, processed.parent, raw.parent


def test_same_document_index_is_classified_from_real_dom_evidence(tmp_path):
    html, sections, chunks, _, _ = _fixture(tmp_path)
    report = audit_filing(html, sections, chunks)
    assert report["route_classification"] == "same_document_internal_index"
    assert report["route_supported_by_current_raw_document"] is True
    assert report["statement_table_count"] == 1
    assert report["financial_link_targets"][0]["target_position"] is not None
    assert report["production_ready"] is False


def test_external_annual_report_requires_separate_document(tmp_path):
    html, sections, chunks, _, _ = _fixture(tmp_path, ticker="IBM", external=True)
    report = audit_filing(html, sections, chunks)
    assert report["route_classification"] == "external_annual_report_required"
    assert report["route_supported_by_current_raw_document"] is False


def test_cli_is_deterministic_and_read_only(tmp_path, monkeypatch):
    html, sections, chunks, processed, raw = _fixture(tmp_path)
    before = {path: path.read_bytes() for path in (html, sections, chunks)}

    class DataSettings:
        data_processed_dir = processed
        data_raw_dir = raw

    monkeypatch.setattr("scripts.diagnostics.hard_group_financial_recovery_audit.settings", DataSettings())
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert main(["--tickers", "CVX", "--output", str(first)]) == 0
    assert main(["--tickers", "CVX", "--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()
    assert {path: path.read_bytes() for path in before} == before


def _real_corpus_root() -> Path | None:
    root = Path(__file__).resolve().parents[1] / "data"
    return root if all((root / "raw" / ticker).is_dir() for ticker in ("CVX", "XOM", "JPM", "IBM")) else None


@pytest.mark.skipif(_real_corpus_root() is None, reason="local hard-group corpus is unavailable")
def test_real_hard_group_routes_and_fresh_extraction_guardrails():
    root = _real_corpus_root()
    assert root is not None
    expected = {
        "CVX": "same_document_internal_index",
        "XOM": "same_document_internal_index",
        "JPM": "same_document_page_anchor",
        "IBM": "external_annual_report_required",
    }
    for ticker, route in expected.items():
        report = audit_filing(*_find_paths(ticker, root / "processed", root / "raw"))
        assert report["route_classification"] == route
        assert report["fresh_extraction"]["fresh_fs_quality_valid"] is False
        assert report["production_ready"] is False
