"""Provider-free audit for conservative fact evidence sufficiency."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.diagnostics.phase2_admission import BASELINE_RESULTS
from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V2,
    collect_entries,
    pack_case_context,
    render_packed_blocks,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.fact_context import (
    FACT_CONTEXT_SELECTOR_FINGERPRINT,
    FactContextSelection,
    select_fact_context,
    selected_fact_entries,
)
from src.generation.period_value_completeness import render_chunk_evidence


DEFAULT_OUTPUT = Path(
    "data/diagnostics/fact_evidence_sufficiency_v1.json"
)
OFFICIAL_RESULTS = BASELINE_RESULTS
EXPECTED_CASES = 30
EXPECTED_FACT_CASES = 8
TARGET_SINGLE_SOURCE_QUESTIONS = {
    "What was Microsoft's total assets as of fiscal year 2025?",
    "What was Amazon's AWS net sales in 2025?",
    "Who audited Apple's financial statements and when was the report signed?",
    "Who audited Microsoft's financial statements?",
}
_SOURCE_RE = re.compile(r"\[Source\s+(\d+)\]")


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _roundtrip(context: str) -> bool:
    blocks = parse_evidence_context(context)
    chunks = [
        {"citation": block["citation"], "text": block["text"]}
        for block in blocks
    ]
    return bool(blocks) and render_chunk_evidence(chunks) == context


def _baseline_selection(
    case_payload: dict[str, Any],
    test_case: Any,
) -> tuple[list[dict[str, Any]], str]:
    packed = pack_case_context(
        case_payload,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
    )
    return packed.kept, render_packed_blocks(packed)


def _current_cited_ids(answer: str, baseline_ids: list[str]) -> set[str]:
    cited: set[str] = set()
    for match in _SOURCE_RE.finditer(answer):
        source_number = int(match.group(1))
        if 1 <= source_number <= len(baseline_ids):
            cited.add(baseline_ids[source_number - 1])
    return cited


def _selection_row(
    case_payload: dict[str, Any],
    test_case: Any,
    official_case: dict[str, Any],
) -> dict[str, Any]:
    baseline_entries, baseline_context = _baseline_selection(case_payload, test_case)
    selection = select_fact_context(case_payload)
    candidate_entries = selected_fact_entries(case_payload, selection)
    candidate_context = (
        render_chunk_evidence(candidate_entries)
        if case_payload.get("category") == "fact_lookup"
        else baseline_context
    )
    all_entries = collect_entries(case_payload)
    all_ids = {entry.get("chunk_id") for entry in all_entries}
    candidate_ids = {entry.get("chunk_id") for entry in candidate_entries}
    baseline_ids = [entry.get("chunk_id") for entry in baseline_entries]
    structured_ids = {
        entry.get("chunk_id")
        for entry in all_entries
        if isinstance(entry.get("score"), (int, float))
        and entry["score"] >= 10.0
    }
    cited_ids = _current_cited_ids(official_case.get("answer") or "", baseline_ids)

    label_probe = copy.deepcopy(case_payload)
    label_probe["required_keywords"] = ["not a selector input"]
    label_probe["ground_truth"] = {"not": "a selector input"}
    label_probe["answer"] = "not a selector input"
    label_probe["scores"] = {"context_precision": 0.0}
    label_selection = select_fact_context(label_probe)
    replay = select_fact_context(case_payload)

    return {
        "question": case_payload["question"],
        "category": case_payload.get("category"),
        "selector_tier": selection.tier,
        "query_ticker": selection.profile.ticker,
        "query_section": selection.profile.section,
        "query_periods": list(selection.profile.periods),
        "metric_groups": [name for name, _ in selection.profile.metric_groups],
        "all_chunk_ids": list(selection.all_ids),
        "baseline_chunk_ids": baseline_ids,
        "candidate_chunk_ids": list(selection.kept_ids),
        "partial_candidate_ids": list(selection.partial_ids),
        "fuzzy_candidate_ids": list(selection.fuzzy_ids),
        "baseline_context_sha256": _sha256_text(baseline_context),
        "candidate_context_sha256": _sha256_text(candidate_context),
        "baseline_source_count": len(baseline_entries),
        "candidate_source_count": len(candidate_entries),
        "changed": baseline_context != candidate_context,
        "candidate_subset_of_frozen_evidence": candidate_ids.issubset(all_ids),
        "structured_hits_preserved": structured_ids.issubset(candidate_ids),
        "current_cited_support_preserved": cited_ids.issubset(candidate_ids),
        "baseline_roundtrip": _roundtrip(baseline_context),
        "candidate_roundtrip": _roundtrip(candidate_context),
        "source_order_preserved": [
            entry.get("chunk_id") for entry in candidate_entries
        ] == [
            entry.get("chunk_id")
            for entry in all_entries
            if entry.get("chunk_id") in candidate_ids
        ],
        "label_free": label_selection.kept_ids == selection.kept_ids,
        "deterministic_replay": replay == selection,
        "partial_or_fuzzy_not_authoritative": (
            selection.tier not in {"partial_terms_support_only", "fuzzy_diagnostic_only"}
            or selection.kept_ids == selection.all_ids
        ),
        "official_answer_sha256": _sha256_text(official_case.get("answer") or ""),
    }


def run(
    artifact_path: Path = ARTIFACT_PATH,
    official_path: Path = OFFICIAL_RESULTS,
    output: Path | None = None,
) -> dict[str, Any]:
    artifact, _ = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V2,
    )
    official = json.loads(official_path.read_text(encoding="utf-8"))
    selected = [case for case in TEST_SET if case.priority <= 2]
    artifact_by_question = {case["question"]: case for case in artifact["cases"]}
    official_by_question = {case["question"]: case for case in official["cases"]}
    test_by_question = {case.question: case for case in selected}

    rows: list[dict[str, Any]] = []
    for test_case in selected:
        case_payload = artifact_by_question.get(test_case.question)
        official_case = official_by_question.get(test_case.question, {})
        if case_payload is None:
            rows.append({"question": test_case.question, "status": "missing_artifact_case"})
            continue
        rows.append(_selection_row(case_payload, test_case, official_case))

    fact_rows = [row for row in rows if row.get("category") == "fact_lookup"]
    non_fact_rows = [row for row in rows if row.get("category") != "fact_lookup"]
    target_rows = {
        row["question"]: row
        for row in fact_rows
        if row["question"] in TARGET_SINGLE_SOURCE_QUESTIONS
    }
    gates = {
        "all_priority_cases_present": len(rows) == EXPECTED_CASES
        and all(row.get("status") is None for row in rows),
        "exactly_eight_fact_cases": len(fact_rows) == EXPECTED_FACT_CASES,
        "all_contexts_have_source_roundtrip": len(rows) == EXPECTED_CASES
        and all(row.get("baseline_roundtrip") and row.get("candidate_roundtrip") for row in rows),
        "non_fact_byte_identity": len(non_fact_rows) == EXPECTED_CASES - EXPECTED_FACT_CASES
        and all(not row.get("changed") for row in non_fact_rows),
        "candidate_subset_of_frozen_evidence": all(
            row.get("candidate_subset_of_frozen_evidence") is True for row in rows
        ),
        "structured_hits_preserved": all(
            row.get("structured_hits_preserved") is True for row in rows
        ),
        "current_cited_support_preserved": all(
            row.get("current_cited_support_preserved") is True for row in rows
        ),
        "source_order_preserved": all(
            row.get("source_order_preserved") is True for row in rows
        ),
        "label_free": all(row.get("label_free") is True for row in rows),
        "deterministic_replay": all(
            row.get("deterministic_replay") is True for row in rows
        ),
        "partial_or_fuzzy_never_remove_context": all(
            row.get("partial_or_fuzzy_not_authoritative") is True for row in rows
        ),
        "target_four_present": set(target_rows) == TARGET_SINGLE_SOURCE_QUESTIONS,
        "target_four_single_self_contained_source": (
            set(target_rows) == TARGET_SINGLE_SOURCE_QUESTIONS
            and all(
                target_rows[question]["candidate_source_count"] == 1
                and target_rows[question]["selector_tier"]
                in {"structured_exact", "exact_phrase", "full_terms"}
                for question in TARGET_SINGLE_SOURCE_QUESTIONS
            )
        ),
        "provider_free": True,
    }
    report = {
        "schema_version": 1,
        "audit": "fact_evidence_sufficiency_v1",
        "official": False,
        "artifact_path": str(artifact_path),
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "official_path": str(official_path),
        "official_context_strategy": official.get("context_strategy"),
        "selector_fingerprint": FACT_CONTEXT_SELECTOR_FINGERPRINT,
        "num_selected": len(rows),
        "num_fact_cases": len(fact_rows),
        "rows": rows,
        "gates": gates,
        "passed": all(gates.values()),
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--official", type=Path, default=OFFICIAL_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(args.artifact, args.official, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
