import json
from pathlib import Path
from bs4 import BeautifulSoup
from scripts.diagnostics.toc_anchor_counterfactual import _find_toc_anchors_for_financial_statements, _evaluate_gates, _get_counterfactual_result, _run_counterfactual

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

def test_run_counterfactual_deterministic(tmp_path):
    _, _, proc, raw = _fixture(tmp_path)
    assert json.dumps(_run_counterfactual("TEST", proc, raw), sort_keys=True) == json.dumps(_run_counterfactual("TEST", proc, raw), sort_keys=True)
