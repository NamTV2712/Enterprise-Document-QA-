"""Tests for the read-only financial-table coverage audit."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.diagnostics.financial_table_audit import (
    _audit_digest,
    _audit_one,
)


def _write_filing(
    tmp_path: Path,
    ticker: str,
    *,
    fs_text: str | None,
    table_html: str = "",
    extra_html: str = "",
) -> tuple[Path, Path]:
    processed = tmp_path / "processed" / ticker
    raw = tmp_path / "raw" / ticker
    processed.mkdir(parents=True)
    raw.mkdir(parents=True)
    sections: dict[str, str] = {"business": "Business body " * 50}
    if fs_text is not None:
        sections["financial_statements"] = fs_text
    sections_payload = {
        "ticker": ticker,
        "accession_number": f"0000000000-26-{ticker}-AUDIT",
        "filing_date": "2026-01-01",
        "report_date": "2025-12-31",
        "sections": sections,
    }
    sections_path = processed / f"{ticker}_sections.json"
    sections_path.write_text(
        json.dumps(sections_payload), encoding="utf-8"
    )
    html = (
        "<html><body>"
        + extra_html
        + f"<div id='fs'>{fs_text or ''}</div>{table_html}"
        + "</body></html>"
    )
    html_path = raw / f"{ticker}_audit.html"
    # Match the accession-derived name the audit expects.
    html_path = raw / (
        sections_payload["accession_number"].replace("-", "") + ".html"
    )
    html_path.write_text(html, encoding="utf-8")
    return html_path, sections_path


def test_fs_missing_is_classified_without_tables(tmp_path: Path) -> None:
    html_path, sections_path = _write_filing(
        tmp_path, "CVXX", fs_text=None,
        extra_html="<p>Consolidated Statement of Cash Flows</p><table><tr><td>x</td></tr></table>",
    )

    report = _audit_one("CVXX", html_path, sections_path, tmp_path / "processed")

    assert report["causes"] == ["financial_statements_missing"]
    assert report["has_financial_statements"] is False
    assert report["statement_like_tables_anywhere"]


def test_anchor_without_window_tables_is_layout_or_exhibit(
    tmp_path: Path,
) -> None:
    fs_text = "Item 8. Financial Statements and Supplementary Data\n" + (
        "Statement narrative line here.\n" * 30
    )
    html_path, sections_path = _write_filing(
        tmp_path,
        "NVDDA",
        fs_text=fs_text,
        extra_html=(
            "<p>Item 9. Changes in and Disagreements with Accountants</p>"
            "<h3>Consolidated Balance Sheets (In millions)</h3>"
            "<table><tr><th>2025</th><th>2024</th></tr>"
            "<tr><td>Total assets</td><td>100</td></tr></table>"
        ),
    )

    report = _audit_one("NVDDA", html_path, sections_path, tmp_path / "processed")

    assert report["causes"] == ["layout_or_exhibit"]
    assert report["start_anchor_found"] is True
    # Samples are truncated at 80 chars, hence the partial phrase.
    assert any("Consolidated Balance Sheet" in s for s in
               report["statement_like_tables_outside_window"])


def test_window_table_without_year_header_is_row_filter_miss(
    tmp_path: Path,
) -> None:
    fs_text = "Item 8. Financial Statements and Supplementary Data\n" + (
        "Statement narrative line here.\n" * 30
    )
    table_html = (
        "<table><tr><td>Current year</td><td>Prior year</td></tr>"
        "<tr><td>Total assets</td><td>100</td></tr></table>"
    )
    html_path, sections_path = _write_filing(
        tmp_path, "AVGG", fs_text=fs_text, table_html=table_html
    )

    report = _audit_one("AVGG", html_path, sections_path, tmp_path / "processed")

    assert report["causes"] == ["row_filter_miss"]
    assert report["window_table_count"] == 1
    assert report["tables_with_parsed_rows"] == 0
    assert report["chunks_buildable_now"] == 0


def test_year_header_table_is_buildable_and_flags_pipeline_stale(
    tmp_path: Path,
) -> None:
    fs_text = "Item 8. Financial Statements and Supplementary Data\n" + (
        "Statement narrative line here.\n" * 30
    )
    table_html = (
        "<table><tr><th>Dec. 31,</th><th>2025</th><th>2024</th></tr>"
        "<tr><td>Total assets</td><td>100</td><td>90</td></tr></table>"
    )
    html_path, sections_path = _write_filing(
        tmp_path, "PIPE", fs_text=fs_text, table_html=table_html
    )
    embedded = tmp_path / "processed" / "PIPE"
    (embedded / "pipe_chunks_embedded.jsonl").write_text(
        json.dumps({
            "chunk_id": "PIPE_c0", "ticker": "PIPE", "section": "business",
            "text": "business text",
        })
        + "\n",
        encoding="utf-8",
    )

    report = _audit_one("PIPE", html_path, sections_path, tmp_path / "processed")

    assert report["causes"] == ["pipeline_stale"]
    assert report["chunks_buildable_now"] >= 1
    assert report["embedded_financial_table_chunks"] is None or (
        report["embedded_financial_table_chunks"] >= 0
    )


def test_audit_digest_is_order_insensitive_and_change_sensitive(
    tmp_path: Path,
) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("alpha", encoding="utf-8")
    b.write_text("beta", encoding="utf-8")

    first = _audit_digest([a, b])
    second = _audit_digest([b, a])
    assert first == second

    b.write_text("gamma", encoding="utf-8")
    assert _audit_digest([a, b]) != first
