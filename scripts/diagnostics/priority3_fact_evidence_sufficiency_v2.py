"""Provider-free Fact Evidence Sufficiency v2 audit over the P3 shadow."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import load_bound_artifact
from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    CONTEXT_STRATEGY_SELECTIVE_V7,
    collect_entries,
    pack_case_context,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_case_selector import select_test_cases
from src.evaluation.test_set import TEST_SET
from src.generation.fact_context import (
    FACT_CONTEXT_SELECTOR_FINGERPRINT_V2,
    select_fact_context_v2,
)
from src.generation.period_value_completeness import render_chunk_evidence


DEFAULT_ARTIFACT = Path("data/eval_artifacts/phase1_priority3_shadow_v1.json")
DEFAULT_GENERATION = Path(
    "data/eval_artifacts/phase2_gen_priority3_shadow_v1.jsonl"
)
DEFAULT_OFFICIAL = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
DEFAULT_OUTPUT = Path(
    "data/diagnostics/priority3_fact_evidence_sufficiency_v2.json"
)
EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:98cb84d80987642f1272f49fa7fd0040237cd34d4fc9b82a7409bb6a248fdf97"
)
OFFICIAL_N30_SHA256 = (
    "a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)
EXPECTED_P3_CASES = 22
EXPECTED_FACT_CASES = 9
_SOURCE_RE = re.compile(r"[\[【]Source\s+(\d+)[\]】]", re.IGNORECASE)


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _roundtrip(context: str) -> bool:
    blocks = parse_evidence_context(context)
    chunks = [
        {"citation": block["citation"], "text": block["text"]}
        for block in blocks
    ]
    return bool(blocks) and render_chunk_evidence(chunks) == context


def _cited_ids(answer: str, source_ids: list[str]) -> set[str]:
    cited: set[str] = set()
    for match in _SOURCE_RE.finditer(answer):
        number = int(match.group(1))
        if 1 <= number <= len(source_ids):
            cited.add(source_ids[number - 1])
    return cited


def _answer_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["question"]] = row
    return rows


def _selection_row(
    case_payload: dict[str, Any],
    test_case: Any,
    generation_row: dict[str, Any],
) -> dict[str, Any]:
    baseline_packed = pack_case_context(
        case_payload,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
    )
    candidate_packed = pack_case_context(
        case_payload,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
    )
    baseline_context = render_case_context(
        case_payload,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
    )
    candidate_context = render_case_context(
        case_payload,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
    )
    selection = select_fact_context_v2(case_payload)
    all_entries = collect_entries(case_payload)
    baseline_entries = [
        block for block in parse_evidence_context(baseline_context)
    ]
    candidate_entries = [
        block for block in parse_evidence_context(candidate_context)
    ]
    all_ids = {entry.get("chunk_id") for entry in all_entries}
    candidate_ids = {
        entry.get("chunk_id") for entry in candidate_packed.kept
    }
    baseline_ids = [entry.get("chunk_id") for entry in baseline_packed.kept]
    candidate_ids_in_order = [
        entry.get("chunk_id") for entry in candidate_packed.kept
    ]
    structured_ids = {
        entry.get("chunk_id")
        for entry in all_entries
        if isinstance(entry.get("score"), (int, float))
        and entry["score"] >= 10.0
    }
    answer = generation_row.get("answer") or ""
    baseline_cited_ids = _cited_ids(answer, baseline_ids)
    missing_keywords = [
        keyword
        for keyword in test_case.required_keywords
        if str(keyword).casefold() not in candidate_context.casefold()
    ]
    label_probe = copy.deepcopy(case_payload)
    label_probe["required_keywords"] = ["not a selector input"]
    label_probe["ground_truth"] = {"not": "a selector input"}
    label_probe["scores"] = {"context_precision": 0.0}
    label_selection = select_fact_context_v2(label_probe)
    replay = select_fact_context_v2(case_payload)
    answer_audit = audit_answer(
        answer, [block["text"] for block in candidate_entries]
    )
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
        "candidate_chunk_ids": candidate_ids_in_order,
        "partial_candidate_ids": list(selection.partial_ids),
        "fuzzy_candidate_ids": list(selection.fuzzy_ids),
        "baseline_context_sha256": _sha256_text(baseline_context),
        "candidate_context_sha256": _sha256_text(candidate_context),
        "baseline_source_count": len(baseline_entries),
        "candidate_source_count": len(candidate_entries),
        "baseline_text_chars": sum(len(block["text"]) for block in baseline_entries),
        "candidate_text_chars": sum(len(block["text"]) for block in candidate_entries),
        "changed": baseline_context != candidate_context,
        "candidate_subset_of_frozen_evidence": candidate_ids.issubset(all_ids),
        "structured_hits_preserved": structured_ids.issubset(candidate_ids),
        "current_cited_support_preserved": baseline_cited_ids.issubset(candidate_ids),
        "source_order_preserved": (
            candidate_ids_in_order
            == [
                entry.get("chunk_id")
                for entry in all_entries
                if entry.get("chunk_id") in candidate_ids
            ]
            if case_payload.get("category") == "fact_lookup"
            else candidate_context == baseline_context
        ),
        "candidate_required_keywords_present": not missing_keywords,
        "missing_required_keywords": missing_keywords,
        "baseline_roundtrip": _roundtrip(baseline_context),
        "candidate_roundtrip": _roundtrip(candidate_context),
        "label_free": label_selection.kept_ids == selection.kept_ids,
        "deterministic_replay": replay == selection,
        "partial_or_fuzzy_not_authoritative": (
            selection.tier not in {"partial_terms_support_only", "fuzzy_diagnostic_only"}
            or selection.kept_ids == selection.all_ids
        ),
        "answer_integrity": answer_audit.to_dict(),
    }


def run(
    artifact_path: Path = DEFAULT_ARTIFACT,
    generation_path: Path = DEFAULT_GENERATION,
    official_path: Path = DEFAULT_OFFICIAL,
    output: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    artifact, _ = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V7,
    )
    generation = _answer_rows(generation_path)
    selected = select_test_cases(TEST_SET, priority=3, exact_priority=True)
    artifact_by_question = {case["question"]: case for case in artifact["cases"]}
    test_by_question = {case.question: case for case in selected.cases}
    rows: list[dict[str, Any]] = []
    for question in selected.questions:
        case_payload = artifact_by_question[question]
        rows.append(
            _selection_row(
                case_payload,
                test_by_question[question],
                generation[question],
            )
        )

    fact_rows = [row for row in rows if row["category"] == "fact_lookup"]
    non_fact_rows = [row for row in rows if row["category"] != "fact_lookup"]
    official_sha = _file_sha256(official_path).removeprefix("sha256:")
    gates = {
        "exact_p3_scope": len(rows) == EXPECTED_P3_CASES
        and all(row["question"] in artifact_by_question for row in rows),
        "exact_fact_case_count": len(fact_rows) == EXPECTED_FACT_CASES,
        "all_generation_answers_present": len(generation) == EXPECTED_P3_CASES
        and all(row["question"] in generation for row in rows),
        "all_contexts_roundtrip": all(
            row["baseline_roundtrip"] and row["candidate_roundtrip"] for row in rows
        ),
        "candidate_subset_of_frozen_evidence": all(
            row["candidate_subset_of_frozen_evidence"] for row in rows
        ),
        "structured_hits_preserved": all(
            row["structured_hits_preserved"] for row in rows
        ),
        "current_cited_support_preserved": all(
            row["current_cited_support_preserved"] for row in fact_rows
        ),
        "source_order_preserved": all(
            row["source_order_preserved"] for row in rows
        ),
        "required_keywords_present": all(
            row["candidate_required_keywords_present"] for row in rows
        ),
        "label_free": all(row["label_free"] for row in fact_rows),
        "deterministic_replay": all(
            row["deterministic_replay"] for row in fact_rows
        ),
        "partial_or_fuzzy_never_remove_context": all(
            row["partial_or_fuzzy_not_authoritative"] for row in fact_rows
        ),
        "non_fact_byte_identity": len(non_fact_rows) == 13
        and all(not row["changed"] for row in non_fact_rows),
        "fact_single_safe_source": len(fact_rows) == EXPECTED_FACT_CASES
        and all(
            row["candidate_source_count"] == 1
            and row["selector_tier"]
            in {"structured_exact", "exact_phrase", "full_terms"}
            for row in fact_rows
        ),
        "fact_answer_integrity_preserved": all(
            not row["answer_integrity"]["uncited_answer"]
            and not row["answer_integrity"]["out_of_range_citations"]
            and not row["answer_integrity"]["unsupported_numeric_claims"]
            and not row["answer_integrity"]["fallback_answer"]
            for row in fact_rows
        ),
        "official_n30_unchanged": official_sha == OFFICIAL_N30_SHA256,
        "provider_free": True,
    }
    fact_baseline_chars = sum(row["baseline_text_chars"] for row in fact_rows)
    fact_candidate_chars = sum(row["candidate_text_chars"] for row in fact_rows)
    report = {
        "schema_version": 1,
        "audit": "priority3_fact_evidence_sufficiency_v2",
        "official": False,
        "promotion_eligible": False,
        "artifact_path": str(artifact_path),
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "generation_checkpoint": str(generation_path),
        "official_path": str(official_path),
        "official_n30_sha256": _file_sha256(official_path),
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V7,
        "selector_fingerprint": FACT_CONTEXT_SELECTOR_FINGERPRINT_V2,
        "num_selected": len(rows),
        "num_fact_cases": len(fact_rows),
        "fact_baseline_text_chars": fact_baseline_chars,
        "fact_candidate_text_chars": fact_candidate_chars,
        "fact_text_reduction_ratio": round(
            1 - fact_candidate_chars / max(fact_baseline_chars, 1), 4
        ),
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
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--generation", type=Path, default=DEFAULT_GENERATION)
    parser.add_argument("--official", type=Path, default=DEFAULT_OFFICIAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(args.artifact, args.generation, args.official, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
