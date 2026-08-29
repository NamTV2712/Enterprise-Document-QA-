"""Tests for the read-only corpus coverage matrix audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.corpus_coverage_matrix import (
    SCHEMA_VERSION,
    TEXT_SECTIONS,
    build_coverage_report,
    render_terminal_report,
    report_to_json,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Baseline documented in PROJECT_STATE.md after the IBM companion recovery.
EXPECTED_BASELINE = {
    "configured_tickers": 50,
    "searchable_tickers": 50,
    "clean_tickers": 46,
    "degraded_tickers": 4,
    "missing_tickers": 0,
    "tickers_with_financial_table": 50,
    "total_chunks": 10053,
}
EXPECTED_CORPUS_FINGERPRINT = (
    "sha256:1d5b99ed962ab9dff88f268ea17da4efd5c7128900961a123bdfb5e49716c8f4"
)
EXPECTED_DEGRADED = {"CVX", "IBM", "JPM", "XOM"}
EXPECTED_NO_TABLE = set()


def _make_corpus(tmp_path: Path, spec: dict[str, list[tuple[str, int]]]) -> Path:
    """Create a synthetic embedded-chunk corpus from {ticker: [(section, n)]}."""
    root = tmp_path / "processed"
    for ticker, sections in spec.items():
        ticker_dir = root / ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)
        lines = []
        index = 0
        for section, count in sections:
            for _ in range(count):
                record = {
                    "chunk_id": f"{ticker}_c{index}",
                    "ticker": ticker,
                    "section": section,
                    "accession_number": f"0000000000-25-{ticker.replace('-', '')}",
                    "chunk_index": index,
                    "text": f"{ticker} {section} {index}",
                }
                lines.append(json.dumps(record))
                index += 1
        (ticker_dir / f"{ticker.lower()}_chunks_embedded.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
    return root


def _tree_digest(root: Path) -> dict[str, str]:
    """SHA-256 of every file under root, keyed by relative path."""
    digest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return digest


def test_statuses_sections_and_table_flags(tmp_path) -> None:
    root = _make_corpus(
        tmp_path,
        {
            "AAPL": [(section, 2) for section in TEXT_SECTIONS]
            + [("financial_table", 3)],
            "MSFT": [("business", 1), ("risk_factors", 1), ("financial_statements", 1)],
            "TSLA": [("financial_table", 1)],
        },
    )
    # Ticker directory entirely absent -> missing
    report = build_coverage_report(root, tickers=["AAPL", "MSFT", "TSLA", "ZZZZ"])

    rows = {row["ticker"]: row for row in report["tickers"]}
    assert [row["ticker"] for row in report["tickers"]] == [
        "AAPL", "MSFT", "TSLA", "ZZZZ",
    ]

    assert rows["AAPL"]["status"] == "clean"
    assert rows["AAPL"]["sections_missing"] == []
    assert rows["AAPL"]["has_financial_table"] is True
    assert rows["AAPL"]["text_chunk_count"] == 8
    assert rows["AAPL"]["financial_table_chunk_count"] == 3

    assert rows["MSFT"]["status"] == "degraded"
    assert rows["MSFT"]["sections_missing"] == ["mdna"]
    assert rows["MSFT"]["has_financial_table"] is False

    # Only a table chunk is not enough text coverage to be clean
    assert rows["TSLA"]["status"] == "degraded"
    assert len(rows["TSLA"]["sections_missing"]) == len(TEXT_SECTIONS)

    assert rows["ZZZZ"]["status"] == "missing"
    assert rows["ZZZZ"]["total_chunk_count"] == 0

    summary = report["summary"]
    assert summary["clean_tickers"] == 1
    assert summary["degraded_tickers"] == 2
    assert summary["missing_tickers"] == 1
    assert summary["tickers_with_financial_table"] == 2


def test_repeated_runs_are_byte_identical(tmp_path) -> None:
    root = _make_corpus(
        tmp_path,
        {
            "AAPL": [(section, 2) for section in TEXT_SECTIONS],
            "MSFT": [("risk_factors", 1), ("mdna", 1)],
        },
    )
    first = build_coverage_report(root)
    second = build_coverage_report(root)

    assert first == second
    assert report_to_json(first) == report_to_json(second)


def test_audit_never_modifies_corpus_directory(tmp_path) -> None:
    root = _make_corpus(
        tmp_path,
        {
            "AAPL": [(section, 1) for section in TEXT_SECTIONS],
            "MSFT": [("business", 1)],
        },
    )
    before = _tree_digest(root)

    report = build_coverage_report(root)
    render_terminal_report(report)
    json_output = report_to_json(report)

    assert _tree_digest(root) == before
    assert report and json_output


def test_report_schema_and_fingerprint_shape(tmp_path) -> None:
    root = _make_corpus(tmp_path, {"AAPL": [("business", 1)]})
    report = build_coverage_report(root)

    assert report["schema_version"] == SCHEMA_VERSION == 1
    fingerprint = report["corpus_fingerprint"]
    assert isinstance(fingerprint, str)
    assert fingerprint.startswith("sha256:")


def test_empty_corpus_reports_zeroes_without_crash(tmp_path) -> None:
    report = build_coverage_report(tmp_path / "does_not_exist", tickers=["AAPL"])

    assert report["summary"]["configured_tickers"] == 1
    assert report["summary"]["searchable_tickers"] == 0
    assert report["corpus_fingerprint"] is None
    assert report["tickers"][0]["status"] == "missing"


def _real_corpus_dir() -> Path | None:
    candidate = PROJECT_ROOT / "data" / "processed"
    if not candidate.is_dir():
        return None
    if not any(candidate.glob("*/*_chunks_embedded.jsonl")):
        return None
    return candidate


@pytest.mark.skipif(_real_corpus_dir() is None, reason="local corpus not available")
def test_local_corpus_matches_documented_baseline() -> None:
    report = build_coverage_report(_real_corpus_dir())

    summary = report["summary"]
    assert report["corpus_fingerprint"] == EXPECTED_CORPUS_FINGERPRINT
    for key, expected in EXPECTED_BASELINE.items():
        assert summary[key] == expected, (
            f"{key} drifted from documented baseline: "
            f"got {summary[key]}, expected {expected}"
        )

    degraded = {
        row["ticker"] for row in report["tickers"]
        if row["status"] == "degraded"
    }
    no_table = {
        row["ticker"] for row in report["tickers"]
        if row["status"] != "missing" and not row["has_financial_table"]
    }
    assert degraded == EXPECTED_DEGRADED
    assert no_table == EXPECTED_NO_TABLE
