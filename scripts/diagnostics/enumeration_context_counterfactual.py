"""Provider-free audit for enumeration branch-consensus packing.

The candidate composes the admitted selective-v2 policy with a label-free
enumeration selector.  Only strong branch-consensus enumeration plans may
change; every other rendered context must remain byte-identical.  The audit
also replays the promoted official answers against candidate source numbering
to catch citation or grounding damage before any provider call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import tiktoken

from scripts.diagnostics.comparative_packing_v3 import (
    _source_boundaries_match,
    _term_coverage,
)
from scripts.run_evaluation_phase2 import EXPECTED_ARTIFACT_FINGERPRINT
from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V5,
    collect_entries,
    effective_case_context_strategy,
    pack_case_context,
    render_packed_blocks,
)
from src.evaluation.evidence_contracts import evidence_terms
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.enumeration_context import (
    ENUMERATION_CONSENSUS_FINGERPRINT,
    EnumerationBranch,
    enumeration_consensus_profile,
)
from src.generation.period_value_completeness import assess_grounded_completion


ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
OFFICIAL_RESULTS = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
DEFAULT_OUTPUT = Path(
    "data/diagnostics/enumeration_context_counterfactual_v1.json"
)
EXPECTED_OFFICIAL_SHA256 = (
    "sha256:db121babe17ac213222dead90a476e03a2fa256007f0335deac01ff1ff8fc648"
)
EXPECTED_CASES = 30
EXPECTED_ENUMERATION_CASES = 4


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _branches(case_payload: dict[str, Any]) -> list[EnumerationBranch]:
    return [
        EnumerationBranch(
            query=(
                query_entry.get("query", {}).get("effective_query")
                or query_entry.get("query", {}).get("retrieval_query")
                or ""
            ),
            ticker=query_entry.get("query", {}).get("ticker"),
            chunks=query_entry.get("chunks", []),
        )
        for query_entry in case_payload.get("queries", [])
    ]


def _structured_ids(entries: list[dict[str, Any]]) -> set[str]:
    return {
        entry.get("chunk_id")
        for entry in entries
        if isinstance(entry.get("score"), (int, float))
        and entry["score"] >= 10.0
    }


def _answer_integrity(
    answer: str,
    candidate_context: str,
    expects_fallback: bool,
) -> tuple[bool, dict[str, Any]]:
    source_texts = [
        block["text"] for block in parse_evidence_context(candidate_context)
    ]
    audit = audit_answer(answer, source_texts)
    passed = not (
        (audit.uncited_answer and not audit.fallback_answer)
        or audit.malformed_line_citations
        or audit.out_of_range_citations
        or audit.unsupported_numeric_claims
        or (audit.fallback_answer and not expects_fallback)
    )
    return passed, audit.to_dict()


def _measure_case(
    case_payload: dict[str, Any],
    test_case: Any,
    official_case: dict[str, Any],
    encoder: Any,
) -> dict[str, Any]:
    category = case_payload.get("category", "")
    baseline = pack_case_context(
        case_payload,
        required_keywords=test_case.required_keywords,
        strategy=effective_case_context_strategy(
            CONTEXT_STRATEGY_SELECTIVE_V2, category
        ),
    )
    candidate = pack_case_context(
        case_payload,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
    )
    label_shadow = pack_case_context(
        case_payload,
        required_keywords=["deliberately different audit-only label"],
        strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
    )
    baseline_rendered = render_packed_blocks(baseline)
    candidate_rendered = render_packed_blocks(candidate)
    entries = collect_entries(case_payload)
    full_ids = {entry.get("chunk_id") for entry in entries}
    candidate_ids = set(candidate.kept_ids)
    terms = evidence_terms(case_payload["question"], test_case.required_keywords)
    baseline_coverage = _term_coverage(terms, baseline_rendered)
    candidate_coverage = _term_coverage(terms, candidate_rendered)
    answer = official_case.get("answer") or ""
    integrity_passed, integrity = _answer_integrity(
        answer, candidate_rendered, test_case.expects_fallback
    )
    citations = integrity.get("canonical_citations") or []
    citation_mapping_preserved = all(
        isinstance(source, int)
        and 1 <= source <= len(candidate.kept_ids)
        and source <= len(baseline.kept_ids)
        and candidate.kept_ids[source - 1] == baseline.kept_ids[source - 1]
        for source in citations
    )
    completion = assess_grounded_completion(
        case_payload["question"], candidate_rendered, answer
    )

    profile = enumeration_consensus_profile(_branches(case_payload))
    branch_representatives = []
    if category == "enumeration":
        for query_entry in case_payload.get("queries", []):
            available = list(dict.fromkeys(
                chunk.get("chunk_id") for chunk in query_entry.get("chunks", [])
            ))
            kept = [chunk_id for chunk_id in available if chunk_id in candidate_ids]
            branch_representatives.append({
                "effective_query": (
                    query_entry.get("query", {}).get("effective_query")
                    or query_entry.get("query", {}).get("retrieval_query")
                ),
                "available_chunk_ids": available,
                "kept_chunk_ids": kept,
                "representative_kept": bool(kept),
            })

    changed = baseline_rendered != candidate_rendered
    return {
        "question": case_payload["question"],
        "category": category,
        "baseline_context_sha256": _sha256_text(baseline_rendered),
        "candidate_context_sha256": _sha256_text(candidate_rendered),
        "baseline_chunks": len(baseline.kept),
        "candidate_chunks": len(candidate.kept),
        "baseline_tokens": len(encoder.encode(baseline_rendered)),
        "candidate_tokens": len(encoder.encode(candidate_rendered)),
        "baseline_chunk_ids": baseline.kept_ids,
        "candidate_chunk_ids": candidate.kept_ids,
        "changed": changed,
        "non_enumeration_identity": category == "enumeration" or not changed,
        "change_is_consensus_qualified": not changed or (
            category == "enumeration" and profile.eligible
        ),
        "ineligible_enumeration_identity": (
            category != "enumeration" or profile.eligible or not changed
        ),
        "candidate_subset_of_frozen_evidence": candidate_ids.issubset(full_ids),
        "structured_hits_preserved": _structured_ids(entries).issubset(
            candidate_ids
        ),
        "required_term_coverage_preserved": (
            candidate_coverage == baseline_coverage
        ),
        "source_boundaries_passed": _source_boundaries_match(
            candidate_rendered, candidate.kept
        ),
        "label_invariant_selection": (
            category != "enumeration"
            or candidate.kept_ids == label_shadow.kept_ids
        ),
        "branch_representatives": branch_representatives,
        "branch_representatives_passed": all(
            row["representative_kept"] for row in branch_representatives
        ),
        "consensus_profile": asdict(profile)
        if category == "enumeration"
        else None,
        "official_answer_integrity": integrity,
        "official_answer_integrity_passed": integrity_passed,
        "official_citation_mapping_preserved": citation_mapping_preserved,
        "completion_correction_required": completion.correction_required,
        "completion_grounding_passed": completion.grounding_passed,
    }


def run(
    artifact_path: Path = ARTIFACT_PATH,
    official_path: Path = OFFICIAL_RESULTS,
    expected_official_sha256: str = EXPECTED_OFFICIAL_SHA256,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    embedded = artifact.get("fingerprints", {}).get("artifact")
    if embedded != EXPECTED_ARTIFACT_FINGERPRINT:
        raise RuntimeError(
            f"Artifact fingerprint drift: expected {EXPECTED_ARTIFACT_FINGERPRINT}, "
            f"found {embedded}"
        )
    official_sha256 = _file_sha256(official_path)
    if official_sha256 != expected_official_sha256:
        raise RuntimeError(
            f"Official result drift: expected {expected_official_sha256}, "
            f"found {official_sha256}"
        )
    official = json.loads(official_path.read_text(encoding="utf-8"))
    if (
        official.get("official") is not True
        or official.get("context_strategy") != CONTEXT_STRATEGY_SELECTIVE_V2
    ):
        raise RuntimeError("Reference result is not the protected official v2 run")

    metadata = {
        case.question: case for case in TEST_SET if case.priority <= 2
    }
    official_cases = {
        case.get("question"): case for case in official.get("cases", [])
    }
    encoder = tiktoken.get_encoding("cl100k_base")
    rows = [
        _measure_case(
            case_payload,
            metadata[case_payload["question"]],
            official_cases[case_payload["question"]],
            encoder,
        )
        for case_payload in artifact.get("cases", [])
        if case_payload.get("question") in metadata
        and case_payload.get("question") in official_cases
    ]
    rows.sort(key=lambda row: row["question"])
    enumeration = [row for row in rows if row["category"] == "enumeration"]
    non_enumeration = [row for row in rows if row["category"] != "enumeration"]
    changed = [row for row in rows if row["changed"]]
    baseline_tokens = sum(row["baseline_tokens"] for row in rows)
    candidate_tokens = sum(row["candidate_tokens"] for row in rows)
    gates = {
        "provider_calls_zero": True,
        "case_set_complete": len(rows) == EXPECTED_CASES,
        "enumeration_set_complete": (
            len(enumeration) == EXPECTED_ENUMERATION_CASES
        ),
        "non_enumeration_context_identity": all(
            row["non_enumeration_identity"] for row in non_enumeration
        ),
        "only_consensus_qualified_contexts_change": bool(changed)
        and all(row["change_is_consensus_qualified"] for row in changed),
        "ineligible_enumerations_unchanged": all(
            row["ineligible_enumeration_identity"] for row in enumeration
        ),
        "frozen_evidence_subset": all(
            row["candidate_subset_of_frozen_evidence"] for row in rows
        ),
        "structured_hits_preserved": all(
            row["structured_hits_preserved"] for row in rows
        ),
        "required_term_coverage_preserved": all(
            row["required_term_coverage_preserved"] for row in rows
        ),
        "source_boundaries_preserved": all(
            row["source_boundaries_passed"] for row in rows
        ),
        "evaluation_labels_do_not_affect_selection": all(
            row["label_invariant_selection"] for row in enumeration
        ),
        "enumeration_branch_representatives_preserved": all(
            row["branch_representatives_passed"] for row in enumeration
        ),
        "official_answer_integrity_preserved": all(
            row["official_answer_integrity_passed"] for row in rows
        ),
        "official_citation_mapping_preserved": all(
            row["official_citation_mapping_preserved"] for row in rows
        ),
        "completion_policy_preserved": all(
            not row["completion_correction_required"]
            and row["completion_grounding_passed"]
            for row in rows
        ),
        "candidate_tokens_not_above_baseline": candidate_tokens <= baseline_tokens,
    }
    report = {
        "schema_version": 1,
        "audit": "enumeration_context_counterfactual_v1",
        "provider_calls": 0,
        "artifact_fingerprint": embedded,
        "artifact_sha256": _file_sha256(artifact_path),
        "official_result_sha256": official_sha256,
        "enumeration_selector_fingerprint": ENUMERATION_CONSENSUS_FINGERPRINT,
        "baseline_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "candidate_strategy": CONTEXT_STRATEGY_SELECTIVE_V5,
        "pre_registered_gates": {
            "expected_cases": EXPECTED_CASES,
            "expected_enumeration_cases": EXPECTED_ENUMERATION_CASES,
            "at_least_one_consensus_qualified_enumeration_change": True,
            "all_non_enumeration_contexts_byte_identical": True,
            "all_ineligible_enumerations_byte_identical": True,
            "candidate_is_subset_of_frozen_evidence": True,
            "structured_hits_and_required_terms_preserved": True,
            "selection_is_invariant_to_evaluation_labels": True,
            "every_enumeration_branch_retains_a_representative": True,
            "official_answer_integrity_and_citation_mapping_preserved": True,
            "grounded_completion_behavior_preserved": True,
            "candidate_tokens_not_above_baseline": True,
        },
        "num_cases": len(rows),
        "num_enumeration_cases": len(enumeration),
        "changed_cases": len(changed),
        "changed_questions": [row["question"] for row in changed],
        "consensus_eligible_enumeration_cases": sum(
            row["consensus_profile"]["eligible"] for row in enumeration
        ),
        "baseline_tokens": baseline_tokens,
        "candidate_tokens": candidate_tokens,
        "candidate_token_delta": candidate_tokens - baseline_tokens,
        "gates": gates,
        "passed": all(gates.values()),
        "cases": rows,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--official", type=Path, default=OFFICIAL_RESULTS)
    parser.add_argument(
        "--expected-official-sha256", default=EXPECTED_OFFICIAL_SHA256
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    report = run(
        args.artifact, args.official, args.expected_official_sha256
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "passed": report["passed"],
        "changed_questions": report["changed_questions"],
        "baseline_tokens": report["baseline_tokens"],
        "candidate_tokens": report["candidate_tokens"],
        "candidate_token_delta": report["candidate_token_delta"],
        "gates": report["gates"],
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
