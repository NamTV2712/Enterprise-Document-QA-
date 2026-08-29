"""Offline audit of the frozen decomposed retrieval plans.

Reads the Phase 1 artifact and classifies every decomposed case:

- ``plan_gap``: a planned subquery returned no chunks, or an expected
  ticker has zero planned queries or zero retrieved evidence
- ``retrieval_miss``: subqueries executed but ground-truth keywords or
  numeric facts are absent from the retrieved evidence
- ``evidence_ok``: all required facts present with balanced tickers

The audit is read-only and fully deterministic. It never contacts a
provider, so it runs under the offline guard like any other test tooling.

Usage:
    python -m scripts.diagnostics.audit_decomposed_plans \
        --artifact data/eval_artifacts/phase1_priority2.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.evaluation.evidence_contracts import EXPECTED_FACT_OVERRIDES
from src.evaluation.test_set import TEST_SET
from src.retrieval.query_normalizer import COMPANY_ALIASES

STATUS_PLAN_GAP = "plan_gap"
STATUS_RETRIEVAL_MISS = "retrieval_miss"
STATUS_EVIDENCE_OK = "evidence_ok"

_NUMBER_PATTERN = re.compile(r"\$?\d[\d,\.]*")
_FALLBACK_PHRASES = (
    "could not find",
    "cannot find",
    "not enough information",
    "insufficient information",
    "unable to answer",
    "i don't have",
    "do not have enough",
)

def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _chunk_ticker(chunk_id: str) -> str:
    """Chunk ids are prefixed with the ticker, e.g. ``AAPL_0000...``."""
    return chunk_id.split("_", 1)[0]


def _chunk_audit_text(chunk: dict[str, Any]) -> str:
    """Searchable evidence including deterministic entity attribution.

    Financial-table bodies often omit the company name because ticker and
    filing identity live in chunk metadata. Treat known aliases for that
    ticker as evidence attribution while still requiring numeric and topical
    facts to occur in the actual chunk text.
    """
    ticker = chunk.get("ticker") or _chunk_ticker(chunk.get("chunk_id", ""))
    aliases = COMPANY_ALIASES.get(ticker, ())
    return " ".join(
        [ticker, *aliases, chunk.get("citation", ""), chunk.get("text", "")]
    )


def extract_required_numbers(ground_truth: str) -> list[str]:
    """Numeric facts the evidence must contain (comma-formatted aware).

    Bare four-digit years such as ``2024`` are excluded: a calendar year is
    period metadata, not a financial fact, and financial-table chunk bodies
    frequently omit year headers while carrying the required amounts.
    """
    candidates = []
    for match in _NUMBER_PATTERN.findall(ground_truth):
        cleaned = match.strip("$").rstrip(",.")
        if re.fullmatch(r"(?:19|20)\d{2}", cleaned):
            continue
        if len(cleaned.replace(",", "").replace(".", "")) >= 3:
            candidates.append(cleaned)
    return sorted(set(candidates))


def audit_decomposed_case(
    case_payload: dict[str, Any],
    required_keywords: list[str],
    ground_truth: str,
) -> dict[str, Any]:
    """Classify one decomposed case from its frozen evidence only."""
    subquery_reports: list[dict[str, Any]] = []
    final_chunks_by_id: dict[str, dict[str, Any]] = {}
    for query_entry in case_payload.get("queries", []):
        query = query_entry["query"]
        chunks = query_entry["chunks"]
        ticker_counts: dict[str, int] = defaultdict(int)
        for chunk in chunks:
            ticker_counts[_chunk_ticker(chunk["chunk_id"])] += 1
        for chunk in chunks:
            final_chunks_by_id.setdefault(chunk["chunk_id"], chunk)
        subquery_reports.append(
            {
                "effective_query": query["effective_query"],
                "ticker_filter": query["ticker"],
                "section_filter": query["section"],
                "query_source": query["query_source"],
                "num_chunks": len(chunks),
                "chunk_tickers": dict(sorted(ticker_counts.items())),
                "empty": not chunks,
            }
        )

    expected_tickers = sorted({
        query["ticker"]
        for query in (q["query"] for q in case_payload.get("queries", []))
        if query["ticker"]
    })
    evidence_ticker_counts: dict[str, int] = defaultdict(int)
    for chunk_id in case_payload.get("final_chunk_ids", []):
        evidence_ticker_counts[_chunk_ticker(chunk_id)] += 1

    missing_ticker_queries = [
        ticker for ticker in expected_tickers
        if not any(
            report["ticker_filter"] == ticker
            for report in subquery_reports
        )
    ]
    empty_subqueries = [r for r in subquery_reports if r["empty"]]
    unbalanced_tickers = {
        ticker: evidence_ticker_counts.get(ticker, 0)
        for ticker in expected_tickers
        if evidence_ticker_counts.get(ticker, 0) == 0
    }

    compact_evidence = " ".join(
        _compact(_chunk_audit_text(final_chunks_by_id[cid]))
        for cid in case_payload.get("final_chunk_ids", [])
        if cid in final_chunks_by_id
    )
    missing_keywords = [
        keyword for keyword in required_keywords
        if _compact(keyword) not in compact_evidence
    ]
    required_numbers = set(extract_required_numbers(ground_truth))
    required_numbers.update(
        EXPECTED_FACT_OVERRIDES.get(case_payload["question"], ())
    )
    missing_numbers = [
        number for number in sorted(required_numbers)
        if number not in compact_evidence and number.replace(",", "") not in compact_evidence.replace(",", "")
    ]

    if empty_subqueries or missing_ticker_queries or unbalanced_tickers:
        status = STATUS_PLAN_GAP
    elif missing_keywords or missing_numbers:
        status = STATUS_RETRIEVAL_MISS
    else:
        status = STATUS_EVIDENCE_OK

    return {
        "question": case_payload["question"],
        "category": case_payload["category"],
        "status": status,
        "subqueries": subquery_reports,
        "expected_tickers": expected_tickers,
        "evidence_ticker_counts": dict(sorted(evidence_ticker_counts.items())),
        "missing_ticker_queries": missing_ticker_queries,
        "empty_subqueries": [r["effective_query"] for r in empty_subqueries],
        "unbalanced_tickers": unbalanced_tickers,
        "missing_keywords": missing_keywords,
        "missing_ground_truth_numbers": missing_numbers,
        "final_chunk_count": len(case_payload.get("final_chunk_ids", [])),
    }


def load_official_fallback_questions(artifact_path: Path) -> set[str]:
    """Questions whose historical llama-era answer was a fallback."""
    if not artifact_path.exists():
        return set()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    fallback = set()
    for record in payload.get("results", []):
        answer = (record.get("answer") or "").lower()
        if any(phrase in answer for phrase in _FALLBACK_PHRASES):
            fallback.add(record.get("question", ""))
    return fallback


def run_audit(artifact_path: Path, official_artifact_path: Path) -> dict[str, Any]:
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    case_meta = {tc.question: tc for tc in TEST_SET}
    historical_fallbacks = load_official_fallback_questions(official_artifact_path)

    reports = []
    for case_payload in payload.get("cases", []):
        question = case_payload["question"]
        if case_payload.get("route") != "decomposed":
            continue
        meta = case_meta.get(question)
        report = audit_decomposed_case(
            case_payload,
            required_keywords=meta.required_keywords if meta else [],
            ground_truth=meta.ground_truth if meta else "",
        )
        report["historical_answer_was_fallback"] = question in historical_fallbacks
        reports.append(report)

    by_status = defaultdict(list)
    for report in reports:
        by_status[report["status"]].append(report["question"])

    return {
        "audit_schema_version": 1,
        "artifact_fingerprint": payload["fingerprints"]["artifact"],
        "num_decomposed_cases": len(reports),
        "status_counts": {k: len(v) for k, v in sorted(by_status.items())},
        "cases": reports,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Decomposed plan audit",
        f"  Artifact : {report['artifact_fingerprint']}",
        f"  Cases    : {report['num_decomposed_cases']}",
        f"  Statuses : {report['status_counts']}",
        "",
    ]
    for case in report["cases"]:
        marker = {
            STATUS_PLAN_GAP: "[PLAN-GAP]",
            STATUS_RETRIEVAL_MISS: "[RETRIEVAL-MISS]",
            STATUS_EVIDENCE_OK: "[OK]",
        }[case["status"]]
        lines.append(f"{marker} {case['question'][:70]}")
        lines.append(
            f"    tickers={case['expected_tickers']} "
            f"evidence={case['evidence_ticker_counts']} "
            f"chunks={case['final_chunk_count']}"
        )
        if case["empty_subqueries"]:
            lines.append(f"    empty subqueries: {case['empty_subqueries']}")
        if case["missing_ticker_queries"]:
            lines.append(
                f"    tickers without any query: {case['missing_ticker_queries']}"
            )
        if case["missing_keywords"]:
            lines.append(f"    missing keywords: {case['missing_keywords']}")
        if case["missing_ground_truth_numbers"]:
            lines.append(
                f"    missing GT numbers: {case['missing_ground_truth_numbers']}"
            )
        if case["historical_answer_was_fallback"]:
            lines.append("    note: historical llama-era answer was a fallback")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("data/eval_artifacts/phase1_priority2.json"),
    )
    parser.add_argument(
        "--official-artifact",
        type=Path,
        default=Path("data/evaluation_results_v2.json"),
        help="Historical results used only to flag past fallback answers.",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run_audit(args.artifact, args.official_artifact)
    print(render_report(report))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nJSON report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
