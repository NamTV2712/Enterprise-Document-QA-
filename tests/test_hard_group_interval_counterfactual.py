import json
from pathlib import Path

import pytest

from scripts.diagnostics.hard_group_interval_counterfactual import _find_paths, audit_interval, main


def _fixture(tmp_path: Path, duplicate: bool = False, stop: bool = True):
    ticker = "CVX"
    processed = tmp_path / "processed" / ticker
    raw = tmp_path / "raw" / ticker
    processed.mkdir(parents=True)
    raw.mkdir(parents=True)
    accession = "000000000026000001"
    sections = processed / f"{accession}_sections.json"
    sections.write_text(json.dumps({"ticker": ticker, "sections": {"business": "x"}}), encoding="utf-8")
    income = "<table><tr><th>2025</th><th>2024</th></tr><tr><td>Net income</td><td>2</td><td>1</td></tr></table>"
    balance = "<table><tr><th>2025</th><th>2024</th></tr><tr><td>Total assets</td><td>4</td><td>3</td></tr></table>"
    cash = "<table><tr><th>2025</th><th>2024</th></tr><tr><td>Net cash provided by operating activities</td><td>6</td><td>5</td></tr></table>"
    html = raw / f"{accession}.html"
    html.write_text(
        '<a href="#income">Consolidated Statement of Income</a><div id="income">'
        + income + balance + cash + (income if duplicate else "")
        + ("<p>Notes to Consolidated Financial Statements</p>" if stop else "")
        + "</div>",
        encoding="utf-8",
    )
    return html, sections, processed.parent, raw.parent


def test_interval_selects_statement_anchor_and_passes_clean_gates(tmp_path):
    html, sections, _, _ = _fixture(tmp_path)
    report = audit_interval(html, sections)
    assert report["selected_start"]["label"] == "Consolidated Statement of Income"
    assert report["overall_pass"] is True
    assert report["statement_categories"] == ["balance_sheet", "cash_flow", "income"]
    assert report["fiscal_years"] == ["2024", "2025"]


def test_interval_fails_when_duplicate_table_remains(tmp_path):
    html, sections, _, _ = _fixture(tmp_path, duplicate=True)
    report = audit_interval(html, sections)
    assert report["gates"]["no_duplicate_tables"] is False
    assert report["overall_pass"] is False


def test_cli_is_byte_deterministic_and_read_only(tmp_path, monkeypatch):
    html, sections, processed, raw = _fixture(tmp_path)
    before = {path: path.read_bytes() for path in (html, sections)}

    class DataSettings:
        data_processed_dir = processed
        data_raw_dir = raw

    monkeypatch.setattr("scripts.diagnostics.hard_group_interval_counterfactual.settings", DataSettings())
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert main(["--tickers", "CVX", "--output", str(first)]) == 0
    assert main(["--tickers", "CVX", "--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()
    assert {path: path.read_bytes() for path in before} == before


def _real_corpus_root() -> Path | None:
    root = Path(__file__).resolve().parents[1] / "data"
    return root if all((root / "raw" / ticker).is_dir() for ticker in ("CVX", "XOM", "JPM")) else None


@pytest.mark.skipif(_real_corpus_root() is None, reason="local same-document corpus is unavailable")
def test_real_same_document_intervals_pass_preregistered_gates():
    root = _real_corpus_root()
    assert root is not None
    expected_table_counts = {"CVX": 33, "XOM": 4, "JPM": 6}
    for ticker, expected_table_count in expected_table_counts.items():
        report = audit_interval(*_find_paths(ticker, root / "processed", root / "raw"))
        assert report["overall_pass"] is True
        assert len(report["tables"]) == expected_table_count
        assert report["statement_categories"] == ["balance_sheet", "cash_flow", "equity", "income"]
