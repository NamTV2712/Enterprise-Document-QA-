import json
from pathlib import Path

import pytest

from scripts.add_table_chunks import _can_attempt_table_discovery
from src.ingestion.table_discovery import (
    discover_financial_tables,
    discover_root_anchor_tables,
    discover_same_document_interval_tables,
    discover_statement_link_tables,
)

def _fixture(tmp_path: Path):
    html = tmp_path / "f.html"
    html.write_text('''<a href="#fs">Financial Statements</a><div id="fs"></div>
      <p>Item 9. Changes</p><a href="#inc">Consolidated Statements of Income</a><div id="inc"></div>
      <table><tr><th>2025</th><th>2024</th></tr><tr><td>Revenue</td><td>10</td><td>9</td></tr></table>''', encoding="utf-8")
    sections = tmp_path / "s.json"
    sections.write_text(json.dumps({"sections": {"financial_statements": "Item 8. Financial Statements"}}), encoding="utf-8")
    return html, sections

def test_statement_link_fallback_discovers_parseable_table(tmp_path):
    html, sections = _fixture(tmp_path)
    tables, mode = discover_financial_tables(html, sections)
    assert mode == "statement_toc_links" and len(tables) == 1

def test_fallback_is_empty_without_valid_statement_link(tmp_path):
    html, _ = _fixture(tmp_path)
    html.write_text('<a href="#bad">Consolidated Statements of Income</a>', encoding="utf-8")
    assert discover_statement_link_tables(html) == []


def test_root_financial_anchor_recovers_preceding_statement_tables(tmp_path):
    html = tmp_path / "pep.html"
    html.write_text(
        """<table><tr><td>2025</td><td>2024</td><td>2023</td></tr>
        <tr><td>Net Revenue</td><td>93</td><td>91</td><td>90</td></tr></table>
        <p>Other discussion</p>
        <a href="#fs">Financial Statements and Supplementary Data</a>
        <div id="fs"></div>
        <table><tr><td>2025</td><td>2024</td></tr>
        <tr><td>Exhibit income</td><td>1</td><td>2</td></tr></table>""",
        encoding="utf-8",
    )
    tables = discover_root_anchor_tables(html)
    assert len(tables) == 1
    assert "Net Revenue" in tables[0].get_text(" ", strip=True)


def test_root_anchor_fallback_is_used_when_individual_links_absent(tmp_path):
    html = tmp_path / "pep.html"
    html.write_text(
        """<table><tr><td>2025</td><td>2024</td></tr>
        <tr><td>Total assets</td><td>10</td><td>9</td></tr></table>
        <a href="#fs">Financial Statements</a><div id="fs"></div>""",
        encoding="utf-8",
    )
    sections = tmp_path / "s.json"
    sections.write_text(json.dumps({"sections": {"financial_statements": "Item 8"}}), encoding="utf-8")
    tables, mode = discover_financial_tables(html, sections)
    assert mode == "statement_toc_links"
    assert len(tables) == 1


def test_same_document_interval_is_bounded_deduplicated_and_parseable(tmp_path):
    html = tmp_path / "hard-group.html"
    income = "<table><tr><th>2025</th><th>2024</th></tr><tr><td>Net income</td><td>4</td><td>3</td></tr></table>"
    balance = "<table><tr><th>2025</th><th>2024</th></tr><tr><td>Total assets</td><td>8</td><td>7</td></tr></table>"
    html.write_text(
        "<table><tr><td>2025</td><td>2024</td></tr><tr><td>Before boundary</td><td>1</td><td>0</td></tr></table>"
        '<a href="#statements">Consolidated Financial Statements</a>'
        f'<div id="statements">{income}{income}{balance}</div>'
        "<p>Notes to Consolidated Financial Statements</p>"
        "<table><tr><td>2025</td><td>2024</td></tr><tr><td>After boundary</td><td>1</td><td>0</td></tr></table>",
        encoding="utf-8",
    )

    tables = discover_same_document_interval_tables(html)

    assert len(tables) == 2
    text = " ".join(table.get_text(" ", strip=True) for table in tables)
    assert "Net income" in text and "Total assets" in text
    assert "Before boundary" not in text and "After boundary" not in text


def test_same_document_resolver_is_narrowly_enabled_for_authorized_tickers(tmp_path):
    html = tmp_path / "hard-group.html"
    html.write_text(
        '<a href="#statements">Consolidated Financial Statements</a>'
        '<div id="statements"><table><tr><th>2025</th><th>2024</th></tr>'
        "<tr><td>Total assets</td><td>8</td><td>7</td></tr></table></div>"
        "<p>Notes to Consolidated Financial Statements</p>",
        encoding="utf-8",
    )
    sections = tmp_path / "s.json"
    sections.write_text(json.dumps({"ticker": "IBM", "sections": {}}), encoding="utf-8")

    tables, mode = discover_financial_tables(html, sections)

    assert len(tables) == 1
    assert mode == "statement_toc_links"


def test_same_document_resolver_handles_missing_financial_statements(tmp_path):
    html = tmp_path / "hard-group.html"
    html.write_text(
        '<a href="#statements">Consolidated Financial Statements</a>'
        '<div id="statements"><table><tr><th>2025</th><th>2024</th></tr>'
        "<tr><td>Total assets</td><td>8</td><td>7</td></tr></table></div>"
        "<p>Notes to Consolidated Financial Statements</p>",
        encoding="utf-8",
    )
    sections = tmp_path / "s.json"
    sections.write_text(json.dumps({"ticker": "CVX", "sections": {}}), encoding="utf-8")

    tables, mode = discover_financial_tables(html, sections)

    assert len(tables) == 1
    assert mode == "same_document_statement_interval"


def test_chunk_append_preserves_missing_section_skip_outside_verified_routes():
    missing = {"sections": {}}

    assert _can_attempt_table_discovery("CVX", missing) is True
    assert _can_attempt_table_discovery("IBM", missing) is False
    assert _can_attempt_table_discovery(
        "IBM", {"sections": {"financial_statements": "x"}}
    ) is True


def _real_corpus_root() -> Path | None:
    root = Path(__file__).resolve().parents[1] / "data"
    return root if all((root / "raw" / ticker).is_dir() for ticker in ("CVX", "XOM", "JPM")) else None


@pytest.mark.skipif(_real_corpus_root() is None, reason="local same-document corpus is unavailable")
def test_authorized_same_document_routes_match_preregistered_counts():
    root = _real_corpus_root()
    assert root is not None
    for ticker, expected_count in {"CVX": 33, "XOM": 4, "JPM": 6}.items():
        sections_path = next((root / "processed" / ticker).glob("*_sections.json"))
        html_path = root / "raw" / ticker / f"{sections_path.stem.removesuffix('_sections')}.html"

        tables, mode = discover_financial_tables(html_path, sections_path)

        assert mode == "same_document_statement_interval"
        assert len(tables) == expected_count
