import json
from pathlib import Path
from src.ingestion.table_discovery import discover_financial_tables, discover_statement_link_tables

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
