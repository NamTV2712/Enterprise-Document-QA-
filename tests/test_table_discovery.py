import json
from pathlib import Path
from src.ingestion.table_discovery import (
    discover_financial_tables,
    discover_root_anchor_tables,
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
