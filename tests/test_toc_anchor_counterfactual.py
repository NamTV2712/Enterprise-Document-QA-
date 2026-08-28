import json
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup
import pytest
from scripts.diagnostics.toc_anchor_counterfactual import (
    _collect_linked_statement_tables,
    _collect_linked_statement_tables_with_evidence,
    _find_toc_anchors_for_financial_statements,
    _get_counterfactual_result,
    _get_table_fingerprint,
    _evaluate_gates,
    _run_counterfactual,
    main,
)

def _fixture(tmp_path: Path, ticker="TEST", stop=True, duplicate=False):
    proc, raw = tmp_path / "processed" / ticker, tmp_path / "raw" / ticker
    proc.mkdir(parents=True); raw.mkdir(parents=True)
    accession = f"0000000000-26-{ticker}-AUDIT"
    payload = {"ticker": ticker, "accession_number": accession, "filing_date": "2026-01-01", "report_date": "2025-12-31", "sections": {"financial_statements": "Item 8. Financial Statements\nBody"}}
    (proc / f"{ticker}_sections.json").write_text(json.dumps(payload), encoding="utf-8")
    table = "<table><tr><th>2025</th><th>2024</th></tr><tr><td>Total assets</td><td>100</td><td>90</td></tr></table>"
    html = f'<a href="#bad">Financial Statements</a><a href="#fs">Financial Statements</a><a href="#ex">Notes to Financial Statements</a><div id="fs">Item 8. Financial Statements</div>{table}{table if duplicate else ""}{"<p>Item 9. Changes</p>" if stop else ""}<div id="ex">Notes</div>'
    hp = raw / (accession.replace("-", "") + ".html"); hp.write_text(f"<html><body>{html}</body></html>", encoding="utf-8")
    return hp, proc / f"{ticker}_sections.json", proc, raw

def test_anchor_priority_and_exclusions(tmp_path):
    soup = BeautifulSoup('<a href="#x">Notes to Financial Statements</a><a href="#y">Financial Statements</a><a href="#z">Item 8. Financial Statements and Supplementary Data</a><div id="x"/><div id="y"/><div id="z"/>', "lxml")
    found = _find_toc_anchors_for_financial_statements(soup)
    assert found[0]["rank"] == 0 and found[0]["target_id"] == "z"
    assert all(x["target_id"] != "x" for x in found)

def test_real_result_deduplicates_and_extracts_evidence(tmp_path):
    hp, sp, proc, _ = _fixture(tmp_path, duplicate=True)
    result = _get_counterfactual_result("TEST", hp, sp, proc)
    assert result["candidate_table_count_before_dedup"] == 2
    assert result["candidate_table_count_after_dedup"] == 1
    assert result["fiscal_years"] == ["2024", "2025"] and result["sample_row_labels"]

def test_stop_boundary_and_gate_failure(tmp_path):
    hp, sp, proc, _ = _fixture(tmp_path, stop=False)
    result = _get_counterfactual_result("TEST", hp, sp, proc)
    assert result["gates"]["clear_stop_boundary"] is False and result["overall_pass"] is False
    assert _evaluate_gates(False, True, True, True, True, True, True)["overall_pass"] is False


def test_post_boundary_table_is_reported_but_never_built(tmp_path):
    hp, sp, proc, _ = _fixture(tmp_path)
    html = hp.read_text(encoding="utf-8").replace(
        '<div id="ex">Notes</div>',
        '<table><tr><th>2025</th><th>2024</th></tr><tr><td>Total assets</td><td>8</td><td>7</td></tr></table><div id="ex">Notes</div>',
    )
    hp.write_text(html, encoding="utf-8")
    result = _get_counterfactual_result("TEST", hp, sp, proc)
    assert result["tables_after_boundary"] == 1
    assert result["buildable_chunk_count"] == 1
    assert result["gates"]["no_post_boundary_tables"] is True

def test_run_counterfactual_deterministic(tmp_path):
    _, _, proc, raw = _fixture(tmp_path)
    assert json.dumps(_run_counterfactual("TEST", proc, raw), sort_keys=True) == json.dumps(_run_counterfactual("TEST", proc, raw), sort_keys=True)


def test_broken_exact_href_falls_back_to_valid_root_anchor(tmp_path):
    soup = BeautifulSoup(
        '<a href="#missing">Item 8. Financial Statements and Supplementary Data</a>'
        '<a href="#valid">Financial Statements</a><div id="valid">Item 8 body</div>',
        "lxml",
    )
    found = _find_toc_anchors_for_financial_statements(soup)
    selected = next(item for item in found if item["target"] is not None)
    assert selected["target_id"] == "valid"
    assert found[0]["resolution"].startswith("target_not_found")


def test_statement_links_deduplicate_same_table_by_content_fingerprint():
    soup = BeautifulSoup(
        '<a href="#one">Consolidated Statements of Income</a>'
        '<a href="#two">Consolidated Statements of Income</a>'
        '<div id="one">one</div><div id="two">two</div>'
        '<table><tr><th>2025</th><th>2024</th></tr><tr><td>Revenue</td><td>2</td><td>1</td></tr></table>',
        "lxml",
    )
    tables = _collect_linked_statement_tables(soup, {id(node): i for i, node in enumerate(soup.descendants)})
    assert len(tables) == 1
    assert _get_table_fingerprint(tables[0])


def test_statement_link_intervals_do_not_overlap():
    soup = BeautifulSoup(
        '<a href="#one">Consolidated Statements of Income</a><div id="one">one</div>'
        '<table><tr><th>2025</th><th>2024</th></tr><tr><td>Revenue</td><td>2</td><td>1</td></tr></table>'
        '<a href="#two">Consolidated Balance Sheets</a><div id="two">two</div>'
        '<table><tr><th>2025</th><th>2024</th></tr><tr><td>Total assets</td><td>4</td><td>3</td></tr></table>',
        "lxml",
    )
    positions = {id(node): i for i, node in enumerate(soup.descendants)}
    tables, duplicate_count, intervals = _collect_linked_statement_tables_with_evidence(soup, positions, None)
    assert len(tables) == 2
    assert duplicate_count == 0
    assert intervals[0]["stop_position"] == intervals[1]["start_position"]


def test_gate_fails_for_duplicate_chunks_even_with_other_evidence():
    gates = _evaluate_gates(True, True, True, True, True, False, True)
    assert gates["no_duplicate_chunks"] is False
    assert gates["overall_pass"] is False


def test_output_argument_writes_requested_path(tmp_path, monkeypatch):
    _, _, proc, raw = _fixture(tmp_path)
    class DataSettings:
        data_processed_dir = proc.parent
        data_raw_dir = raw.parent
    monkeypatch.setattr("scripts.diagnostics.toc_anchor_counterfactual.settings", DataSettings())
    output = tmp_path / "nested" / "report-one.json"
    second_output = tmp_path / "nested" / "report-two.json"
    assert main(["--tickers", "TEST", "--output", str(output)]) == 0
    assert main(["--tickers", "TEST", "--output", str(second_output)]) == 0
    first = output.read_bytes()
    assert json.loads(first)["schema_version"] == 2
    assert second_output.read_bytes() == first


def _real_corpus_root() -> Path | None:
    root = Path(__file__).resolve().parents[1] / "data"
    return root if (root / "processed").is_dir() and (root / "raw").is_dir() else None


@pytest.mark.skipif(_real_corpus_root() is None, reason="local SEC corpus is unavailable")
def test_real_controls_are_read_only_and_pass(tmp_path):
    root = _real_corpus_root()
    assert root is not None
    chunk_files = sorted((root / "processed").glob("*/*_chunks.jsonl"))
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in chunk_files}
    output = tmp_path / "controls.json"
    assert main(["--tickers", "AAPL", "MSFT", "AMZN", "--output", str(output)]) == 0
    results = {item["ticker"]: item for item in json.loads(output.read_text(encoding="utf-8"))["results"]}
    assert all(results[ticker]["overall_pass"] for ticker in ("AAPL", "MSFT", "AMZN"))
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in chunk_files}
    assert after == before
