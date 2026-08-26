"""Offline per-case context-packing baseline over the frozen artifact.

For every selected case this diagnostic reports chunk counts, rendered
token counts (tiktoken ``cl100k_base``, the same encoder the chunker
uses), route/category, required-keyword coverage, and comparative ticker
coverage under BOTH the full-evidence strategy and route-aware packing.
It is fully deterministic and never contacts a provider.

Usage:
    python -m scripts.diagnostics.context_packing_baseline \
        --artifact data/eval_artifacts/phase1_priority2.json --priority 2
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import tiktoken

from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    CONTEXT_STRATEGY_ROUTE_AWARE,
    pack_case_context,
    render_packed_blocks,
)
from src.evaluation.generation_checkpoint import build_evidence_context
from src.evaluation.test_set import TEST_SET

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = Path("data/diagnostics/context_packing_baseline.json")


def _compact(text: str) -> str:
    return "".join(text.split()).lower()


def _keyword_coverage(keywords: list[str], rendered: str) -> dict[str, bool]:
    compact = _compact(rendered)
    return {kw: _compact(kw) in compact for kw in keywords}


def measure_case(
    case_payload: dict,
    meta: dict[str, Any],
    encoder,
) -> dict[str, Any]:
    """Full-vs-packed measurements for one case."""
    keywords = meta.get("required_keywords") or []

    full_rendered = build_evidence_context(case_payload)
    full_chunks = len({
        c.get("chunk_id")
        for q in case_payload.get("queries", [])
        for c in q.get("chunks", [])
    })

    packed = pack_case_context(
        case_payload,
        required_keywords=keywords,
        strategy=CONTEXT_STRATEGY_ROUTE_AWARE,
    )
    packed_rendered = render_packed_blocks(packed)

    full_cov = _keyword_coverage(keywords, full_rendered)
    packed_cov = _keyword_coverage(keywords, packed_rendered)

    expected_tickers = sorted({
        q["query"].get("ticker")
        for q in case_payload.get("queries", [])
        if isinstance(q.get("query"), dict) and q["query"].get("ticker")
    })
    kept_tickers = {
        (e.get("ticker") or (e.get("chunk_id") or "").split("_", 1)[0])
        for e in packed.kept
    }
    full_tickers = {
        (e.get("ticker") or (e.get("chunk_id") or "").split("_", 1)[0])
        for e in (
            c for q in case_payload.get("queries", []) for c in q.get("chunks", [])
        )
    }

    row: dict[str, Any] = {
        "question": case_payload["question"],
        "category": case_payload.get("category"),
        "route": "decomposed" if expected_tickers else "direct",
        "full": {
            "num_chunks": full_chunks,
            "num_tokens": count_tokens(full_rendered, encoder),
            "keywords_covered": sum(full_cov.values()),
            "num_keywords": len(full_cov),
            "tickers_with_evidence": sorted(full_tickers)
            if expected_tickers else None,
        },
        "packed": {
            "num_chunks": len(packed.kept),
            "num_tokens": count_tokens(packed_rendered, encoder),
            "keywords_covered": sum(packed_cov.values()),
            "num_keywords": len(packed_cov),
            "tickers_with_evidence": sorted(kept_tickers)
            if expected_tickers else None,
            "uncovered_keywords": packed.uncovered_keywords,
        },
    }
    row["token_reduction_pct"] = round(
        100.0
        * (row["full"]["num_tokens"] - row["packed"]["num_tokens"])
        / max(row["full"]["num_tokens"], 1),
        2,
    )
    row["coverage_preserved"] = (
        packed_cov == full_cov
        and (
            not expected_tickers
            or set(row["packed"]["tickers_with_evidence"] or [])
            == set(expected_tickers)
        )
    )
    return row


def count_tokens(text: str, encoder) -> int:
    return len(encoder.encode(text))


def run_baseline(artifact_path: Path, priority: int) -> dict[str, Any]:
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    meta_by_question = {tc.question: tc for tc in TEST_SET}
    encoder = tiktoken.get_encoding("cl100k_base")

    rows = []
    for case in payload.get("cases", []):
        if case["question"] not in meta_by_question:
            continue
        meta_tc = meta_by_question[case["question"]]
        if meta_tc.priority > priority:
            continue
        rows.append(measure_case(case, vars(meta_tc), encoder))

    total_full = sum(r["full"]["num_tokens"] for r in rows)
    total_packed = sum(r["packed"]["num_tokens"] for r in rows)
    summary = {
        "schema_version": 1,
        "artifact": str(artifact_path),
        "artifact_fingerprint": payload.get("fingerprints", {}).get("artifact"),
        "priority": priority,
        "strategies": [CONTEXT_STRATEGY_FULL_EVIDENCE, CONTEXT_STRATEGY_ROUTE_AWARE],
        "num_cases": len(rows),
        "total_tokens_full": total_full,
        "total_tokens_packed": total_packed,
        "total_token_reduction_pct": round(
            100.0 * (total_full - total_packed) / max(total_full, 1), 2
        ),
        "avg_chunks_full": round(
            sum(r["full"]["num_chunks"] for r in rows) / max(len(rows), 1), 3
        ),
        "avg_chunks_packed": round(
            sum(r["packed"]["num_chunks"] for r in rows) / max(len(rows), 1), 3
        ),
        "coverage_preserved_cases": sum(
            1 for r in rows if r["coverage_preserved"]
        ),
        "cases": rows,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("data/eval_artifacts/phase1_priority2.json"),
    )
    parser.add_argument("--priority", type=int, default=2)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    summary = run_baseline(args.artifact, args.priority)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== Context-packing baseline ===")
    print(f"  cases                 : {summary['num_cases']}")
    print(f"  tokens full vs packed : {summary['total_tokens_full']} -> "
          f"{summary['total_tokens_packed']} "
          f"({summary['total_token_reduction_pct']}% reduction)")
    print(f"  avg chunks            : {summary['avg_chunks_full']} -> "
          f"{summary['avg_chunks_packed']}")
    print(f"  coverage preserved    : "
          f"{summary['coverage_preserved_cases']}/{summary['num_cases']}")
    logger.info("Baseline written: %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
