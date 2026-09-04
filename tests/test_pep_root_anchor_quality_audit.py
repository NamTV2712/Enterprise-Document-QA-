import json
from dataclasses import asdict
from pathlib import Path

import pytest

from scripts.diagnostics.pep_root_anchor_quality_audit import (
    _find_paths,
    _classify_table,
    audit_pep_root_anchor_tables,
    main,
)
from src.ingestion.chunker import build_table_chunks
from src.ingestion.table_discovery import discover_root_anchor_tables


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    ticker = "PEP"
    accession = "0000000000-26-000001"
    processed = tmp_path / "processed" / ticker
    raw = tmp_path / "raw" / ticker
    processed.mkdir(parents=True)
    raw.mkdir(parents=True)
    sections_path = processed / f"{accession.replace('-', '')}_sections.json"
    filing_data = {
        "ticker": ticker,
        "accession_number": accession,
        "filing_date": "2026-01-01",
        "report_date": "2025-12-31",
        "sections": {"financial_statements": "Item 8"},
    }
    sections_path.write_text(json.dumps(filing_data), encoding="utf-8")
    html_path = raw / f"{accession.replace('-', '')}.html"
    html_path.write_text(
        """<table><tr><th>2025</th><th>2024</th></tr>
        <tr><td>Net Revenue</td><td>100</td><td>90</td></tr>
        <tr><td>Cost of sales</td><td>60</td><td>50</td></tr>
        <tr><td>Gross profit</td><td>40</td><td>40</td></tr></table>
        <table><tr><th>2025</th><th>2024</th></tr>
        <tr><td>Pension expense</td><td>2</td><td>1</td></tr>
        <tr><td>Net income</td><td>8</td><td>7</td></tr></table>
        <a href="#fs">Financial Statements</a><div id="fs"></div>""",
        encoding="utf-8",
    )
    chunks_path = sections_path.with_name(f"{accession.replace('-', '')}_chunks.jsonl")
    tables = discover_root_anchor_tables(html_path)
    chunks_path.write_text(
        "".join(json.dumps(asdict(chunk)) + "\n" for chunk in build_table_chunks(html_path, tables, filing_data)),
        encoding="utf-8",
    )
    return html_path, sections_path, chunks_path, processed.parent, raw.parent


def test_classification_separates_primary_statement_and_note():
    assert _classify_table(["Net Revenue", "Cost of sales", "Gross profit"])[0] == "primary_income_statement"
    assert _classify_table(["Pension expense", "Net income"])[0] == "financial_note"


def test_audit_matches_canonical_and_is_deterministic(tmp_path):
    html, sections, chunks, _, _ = _fixture(tmp_path)
    before = {path: path.read_bytes() for path in (html, sections, chunks)}
    first = audit_pep_root_anchor_tables(html, sections, chunks)
    second = audit_pep_root_anchor_tables(html, sections, chunks)
    assert first == second
    assert first["root_anchor_table_count"] == 2
    assert first["candidate_matches_canonical"] is True
    assert first["classification_counts"] == {
        "financial_note": 1,
        "primary_income_statement": 1,
    }
    assert {path: path.read_bytes() for path in before} == before


def test_cli_honors_output_and_does_not_modify_inputs(tmp_path, monkeypatch):
    html, sections, chunks, processed, raw = _fixture(tmp_path)
    before = {path: path.read_bytes() for path in (html, sections, chunks)}

    class DataSettings:
        data_processed_dir = processed
        data_raw_dir = raw

    monkeypatch.setattr("scripts.diagnostics.pep_root_anchor_quality_audit.settings", DataSettings())
    output_one = tmp_path / "audit-one.json"
    output_two = tmp_path / "audit-two.json"
    assert main(["--output", str(output_one)]) == 0
    assert main(["--output", str(output_two)]) == 0
    assert output_one.read_bytes() == output_two.read_bytes()
    assert {path: path.read_bytes() for path in before} == before


def _real_corpus_root() -> Path | None:
    root = Path(__file__).resolve().parents[1] / "data"
    return root if (root / "processed" / "PEP").is_dir() and (root / "raw" / "PEP").is_dir() else None


@pytest.mark.skipif(_real_corpus_root() is None, reason="local PEP corpus is unavailable")
def test_real_pep_root_anchor_set_matches_canonical_artifact():
    root = _real_corpus_root()
    assert root is not None
    html, sections, chunks = _find_paths("PEP", root / "processed", root / "raw")
    report = audit_pep_root_anchor_tables(html, sections, chunks)
    assert report["root_anchor_table_count"] == 29
    assert report["candidate_matches_canonical_without_unit_metadata"] is True
    assert report["classification_counts"] == {
        "financial_note": 14,
        "primary_balance_sheet": 1,
        "primary_cash_flow_statement": 1,
        "primary_comprehensive_income": 1,
        "primary_equity_statement": 1,
        "primary_income_statement": 1,
        "supporting_financial_table": 10,
    }
