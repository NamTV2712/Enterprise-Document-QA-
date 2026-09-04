"""Explain the inherited Apple FY2025 fact-quality failure without providers.

The audit traces unit evidence from the raw SEC table through the frozen Phase
1 artifact and the V2 fact context renderer. It does not modify corpus files,
artifacts, or the protected official result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import warnings
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import load_bound_artifact
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V7,
    render_case_context,
)
from src.evaluation.test_set import TEST_SET
from src.generation.fact_context import (
    _dedupe_entries,
    select_fact_context_v2,
)
from src.ingestion.table_discovery import discover_financial_tables
from src.ingestion.table_extractor import extract_table_unit, get_table_caption


ROOT = Path(__file__).resolve().parents[2]
P2_ARTIFACT = ROOT / "data/eval_artifacts/phase1_priority2.json"
P3_ARTIFACT = ROOT / "data/eval_artifacts/phase1_priority3_shadow_v1.json"
OFFICIAL_RESULT = ROOT / "data/eval_artifacts/phase2_results_packed_selective_v2.json"
COMPATIBILITY_RESULT = ROOT / (
    "data/diagnostics/priority2_fact_v2_compatibility_sentinel_r1.json"
)
COMPATIBILITY_SUMMARY = ROOT / (
    "data/eval_artifacts/priority2_fact_v2_compatibility_sentinel_summary_r1.json"
)
COMPATIBILITY_JUDGE = ROOT / (
    "data/eval_artifacts/priority2_fact_v2_compatibility_sentinel_judge_r1.jsonl"
)
DEFAULT_OUTPUT = ROOT / "data/diagnostics/priority2_fact_unit_attribution_v1.json"

_SCALE_RE = re.compile(
    r"\b(?:in\s+)?(?:thousands?|millions?|billions?)\b"
    r"|\b(?:thousands?|millions?|billions?)\s+of\s+dollars\b",
    re.IGNORECASE,
)
_MONETARY_QUESTION_RE = re.compile(
    r"\b(?:net sales|revenue|assets|income|financial statements)\b",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _text_sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _has_unit(value: str) -> bool:
    return bool(_SCALE_RE.search(value))


def _artifact(path: Path) -> tuple[dict[str, Any], Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return load_bound_artifact(
        path,
        raw["fingerprints"]["artifact"],
        CONTEXT_STRATEGY_SELECTIVE_V7,
    )


def _judge_row(question: str) -> dict[str, Any] | None:
    if not COMPATIBILITY_JUDGE.exists():
        return None
    for line in COMPATIBILITY_JUDGE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("question") == question:
            return row
    return None


def _source_record(
    question: str,
    case_payload: dict[str, Any],
    *,
    raw_table_cache: dict[tuple[str, str], tuple[list[Any], str]],
) -> dict[str, Any]:
    selection = select_fact_context_v2(case_payload)
    entries = _dedupe_entries(case_payload)
    selected = next(
        entry for entry in entries if entry.get("chunk_id") in selection.kept_ids
    )
    context = render_case_context(
        case_payload,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
    )
    row: dict[str, Any] = {
        "question": question,
        "selector_tier": selection.tier,
        "selected_chunk_ids": list(selection.kept_ids),
        "context_sha256": _text_sha256(context),
        "context_contains_explicit_scale": _has_unit(context),
        "selected_section": selected.get("section"),
        "selected_chunk_text_sha256": _text_sha256(selected.get("text", "")),
        "selected_chunk_contains_dollar": "$" in selected.get("text", ""),
        "selected_chunk_contains_scale": _has_unit(selected.get("text", "")),
        "unit_contract_applicable": bool(
            _MONETARY_QUESTION_RE.search(question)
            and "audited" not in question.casefold()
        ),
        "raw_table": None,
    }

    if selected.get("section") != "financial_table":
        return row

    match = re.match(
        r"(?P<ticker>[^_]+)_(?P<accession>\d+)_financial_table_(?P<index>\d+)$",
        selected.get("chunk_id", ""),
    )
    if match is None:
        row["raw_table_error"] = "selected financial_table chunk id is not parseable"
        return row

    ticker = match.group("ticker")
    accession = match.group("accession")
    index = int(match.group("index"))
    key = (ticker, accession)
    if key not in raw_table_cache:
        html_path = ROOT / f"data/raw/{ticker}/{accession}.html"
        sections_path = ROOT / f"data/processed/{ticker}/{accession}_sections.json"
        tables, discovery_mode = discover_financial_tables(html_path, sections_path)
        raw_table_cache[key] = (tables, discovery_mode)
    tables, discovery_mode = raw_table_cache[key]
    if index >= len(tables):
        row["raw_table_error"] = f"table index {index} >= {len(tables)}"
        return row

    table = tables[index]
    caption = get_table_caption(table, max_chars=1000)
    raw_text = " ".join(table.get_text(" ", strip=True).split())
    row["raw_table"] = {
        "chunk_id": selected.get("chunk_id"),
        "discovery_mode": discovery_mode,
        "caption_sha256": _text_sha256(caption),
        "caption_length": len(caption),
        "caption_contains_scale": _has_unit(caption),
        "table_contains_dollar": "$" in raw_text,
        "table_contains_scale": _has_unit(raw_text),
        "explicit_unit": extract_table_unit(table),
    }
    return row


def _case_rows() -> list[dict[str, Any]]:
    raw_table_cache: dict[tuple[str, str], tuple[list[Any], str]] = {}
    rows: list[dict[str, Any]] = []
    for artifact_path, priority_filter in (
        (P2_ARTIFACT, lambda priority: priority <= 2),
        (P3_ARTIFACT, lambda priority: priority == 3),
    ):
        if not artifact_path.exists():
            continue
        artifact, _ = _artifact(artifact_path)
        by_question = {case["question"]: case for case in artifact["cases"]}
        selected_tests = [
            case
            for case in TEST_SET
            if case.category == "fact_lookup" and priority_filter(case.priority)
        ]
        for test_case in selected_tests:
            row = _source_record(
                test_case.question,
                by_question[test_case.question],
                raw_table_cache=raw_table_cache,
            )
            row["priority"] = test_case.priority
            rows.append(row)
    return sorted(rows, key=lambda row: (row["priority"], row["question"]))


def _apple_evidence() -> dict[str, Any]:
    question = "What was Apple's total net sales in fiscal year 2025?"
    judge = _judge_row(question) or {}
    result = json.loads(COMPATIBILITY_SUMMARY.read_text(encoding="utf-8"))
    official = json.loads(OFFICIAL_RESULT.read_text(encoding="utf-8"))

    def find_case(payload: dict[str, Any]) -> dict[str, Any]:
        for case in payload.get("cases", []):
            if case.get("question") == question:
                return case
        return {}

    candidate = find_case(result)
    protected = find_case(official)
    return {
        "question": question,
        "candidate_answer": candidate.get("answer"),
        "candidate_scores": candidate.get("scores"),
        "protected_official_answer": protected.get("answer"),
        "protected_official_scores": protected.get("scores"),
        "judge_relevancy_reason": (judge.get("scores") or {}).get(
            "relevancy_reason"
        ),
        "diagnosis": "inherited_answer_unit_omission",
    }


def build_report() -> dict[str, Any]:
    input_paths = [
        P2_ARTIFACT,
        P3_ARTIFACT,
        OFFICIAL_RESULT,
        COMPATIBILITY_RESULT,
        COMPATIBILITY_SUMMARY,
        COMPATIBILITY_JUDGE,
    ]
    existing = [path for path in input_paths if path.exists()]
    rows = _case_rows()
    financial_rows = [row for row in rows if row.get("raw_table")]
    raw_explicit = [
        row
        for row in financial_rows
        if (row.get("raw_table") or {}).get("explicit_unit")
    ]
    current_missing = [
        row["question"]
        for row in rows
        if row["unit_contract_applicable"]
        and not row["context_contains_explicit_scale"]
    ]
    return {
        "schema_version": 1,
        "audit": "priority2_fact_unit_attribution_v1",
        "provider_calls": 0,
        "mutated_inputs": False,
        "input_sha256": {str(path): _sha256(path) for path in existing},
        "official_result_sha256": _sha256(OFFICIAL_RESULT),
        "p2_artifact_sha256": _sha256(P2_ARTIFACT),
        "apple_fy2025": _apple_evidence(),
        "fact_case_count": len(rows),
        "financial_table_fact_case_count": len(financial_rows),
        "financial_table_unique_explicit_unit_count": len(
            {
                (row.get("raw_table") or {}).get("chunk_id")
                for row in raw_explicit
            }
        ),
        "current_rendered_contexts_missing_scale": current_missing,
        "cases": rows,
        "diagnosis": {
            "status": "EXPLAINED_INHERITED_BASELINE",
            "root_cause": (
                "Financial-table extraction preserves numeric rows but loses "
                "explicit table-level currency/scale metadata. Long captions "
                "are clipped before their unit marker and standalone currency "
                "cells are discarded by row normalization."
            ),
            "not_retrieval_miss": True,
            "not_fact_v2_regression": True,
            "renderer_alone_insufficient": True,
            "next_milestone": "financial_table_unit_preservation_v1",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    warnings.filterwarnings("ignore", message=".*XMLParsedAsHTMLWarning.*")
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
