"""Run one quota-gated ten-case Answer Scope v13 sentinel.

This campaign-specific wrapper keeps the previously validated Phase 2 runner
and checkpoint implementation, but uses a new sentinel contract and new clean
artifact paths. It deliberately remains non-official.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import run_answer_stability_sentinel as base
from src.generation.enumeration_answer_renderer import (
    ENUMERATION_ANSWER_RENDERER_FINGERPRINT,
)


SENTINEL_QUESTIONS = (
    "What quality and manufacturing risks does Apple mention?",
    "What are all the major risk factors Microsoft discloses?",
    "Summarize the key risk factors related to competition for Apple.",
    "What does Microsoft say about cybersecurity risks?",
    "What risks does Amazon face related to its international operations?",
    "What are the main sources of revenue for Microsoft?",
    "How does Microsoft describe its Azure and cloud services growth?",
    "How does Amazon's AWS segment compare to Microsoft's cloud business in terms of growth?",
    "What was Apple's total net sales in fiscal year 2025?",
    "What was Amazon's consolidated net sales in 2024?",
)
APPLE_QUALITY_QUESTION = SENTINEL_QUESTIONS[0]
MICROSOFT_RISK_QUESTION = SENTINEL_QUESTIONS[1]
RISK_TARGET_QUESTIONS = frozenset(SENTINEL_QUESTIONS[:2])
RISK_CONTROL_QUESTIONS = frozenset(SENTINEL_QUESTIONS[2:5])
ENUMERATION_CONTROL_QUESTIONS = frozenset({SENTINEL_QUESTIONS[5]})
REVENUE_QUESTION = SENTINEL_QUESTIONS[5]
NUMERIC_CANARY_QUESTIONS = frozenset(SENTINEL_QUESTIONS[6:8])
CROSS_DOCUMENT_COMPARISON_QUESTIONS = frozenset({SENTINEL_QUESTIONS[7]})
FACT_QUESTIONS = frozenset()
REGRESSION_QUESTIONS = frozenset(SENTINEL_QUESTIONS)


def sentinel_artifact_paths(replicate_id: str) -> tuple[Path, Path, Path]:
    if not replicate_id or not all(
        character.isalnum() or character in "-_" for character in replicate_id
    ):
        raise ValueError("replicate_id must contain only letters, digits, '-' or '_'")
    base_path = "data/eval_artifacts/answer_scope_v13_sentinel"
    return (
        Path(f"{base_path}_gen_{replicate_id}.jsonl"),
        Path(f"{base_path}_judge_{replicate_id}.jsonl"),
        Path(f"{base_path}_summary_{replicate_id}.json"),
    )


def _scope_contract_audit(report: dict[str, Any]) -> dict[str, Any]:
    completion_rows = report.get("period_value_corrections") or {}
    microsoft = completion_rows.get(MICROSOFT_RISK_QUESTION) or {}
    revenue = completion_rows.get(REVENUE_QUESTION) or {}
    fact_question = "Who audited Microsoft's financial statements?"
    fact_case_present = fact_question in completion_rows
    evidence_items = microsoft.get("evidence_items") or []
    roles_present = bool(evidence_items) and all(
        item.get("evidence_role") in {"canonical", "supporting"}
        for item in evidence_items
        if isinstance(item, dict)
    )
    role_counts = {
        role: sum(
            item.get("evidence_role") == role
            for item in evidence_items
            if isinstance(item, dict)
        )
        for role in ("canonical", "supporting")
    }
    apple_answer = next(
        (
            case.get("answer", "")
            for case in report.get("cases", [])
            if case.get("question") == APPLE_QUALITY_QUESTION
        ),
    )
    lowered_apple = apple_answer.casefold()
    broadening_terms = {
        "pandemic",
        "natural disaster",
        "industrial accident",
        "generic supply chain",
    }
    return {
        "microsoft_roles_present": roles_present,
        "microsoft_role_counts": role_counts,
        "microsoft_has_canonical_and_supporting": (
            role_counts["canonical"] > 0 and role_counts["supporting"] > 0
        ),
        "apple_direct_scope_present": any(
            term in lowered_apple
            for term in ("defect", "third-party", "component")
        ),
        "apple_unrequested_broadening_absent": not any(
            term in lowered_apple for term in broadening_terms
        ),
        "microsoft_deterministic_renderer_applied": (
            microsoft.get("answer_rendered_deterministically") is True
        ),
        "deterministic_fact_renderer_applied": (
            fact_case_present
            and (completion_rows.get(fact_question) or {}).get(
                "answer_rendered_deterministically"
            )
            is True
        ),
        "deterministic_fact_renderer_case_present": fact_case_present,
        "deterministic_revenue_renderer_applied": (
            revenue.get("answer_rendered_deterministically") is True
        ),
    }


def _install_contract() -> dict[str, Any]:
    """Install the v13 contract in the legacy runner for one call only."""
    saved = {
        name: getattr(base, name)
        for name in (
            "SENTINEL_QUESTIONS",
            "APPLE_QUALITY_QUESTION",
            "MICROSOFT_RISK_QUESTION",
            "FACT_QUESTIONS",
            "RISK_TARGET_QUESTIONS",
            "RISK_CONTROL_QUESTIONS",
            "ENUMERATION_CONTROL_QUESTIONS",
            "NUMERIC_CANARY_QUESTIONS",
            "CROSS_DOCUMENT_COMPARISON_QUESTIONS",
            "REGRESSION_QUESTIONS",
        )
    }
    base.SENTINEL_QUESTIONS = SENTINEL_QUESTIONS
    base.APPLE_QUALITY_QUESTION = APPLE_QUALITY_QUESTION
    base.MICROSOFT_RISK_QUESTION = MICROSOFT_RISK_QUESTION
    base.FACT_QUESTIONS = FACT_QUESTIONS
    base.RISK_TARGET_QUESTIONS = RISK_TARGET_QUESTIONS
    base.RISK_CONTROL_QUESTIONS = RISK_CONTROL_QUESTIONS
    base.ENUMERATION_CONTROL_QUESTIONS = ENUMERATION_CONTROL_QUESTIONS
    base.NUMERIC_CANARY_QUESTIONS = NUMERIC_CANARY_QUESTIONS
    base.CROSS_DOCUMENT_COMPARISON_QUESTIONS = CROSS_DOCUMENT_COMPARISON_QUESTIONS
    base.REGRESSION_QUESTIONS = REGRESSION_QUESTIONS
    return saved


def _restore_contract(saved: dict[str, Any]) -> None:
    for name, value in saved.items():
        setattr(base, name, value)


def run(
    *,
    replicate_id: str,
    artifact_path: Path = base.ARTIFACT_PATH,
    gen_checkpoint: Path | None = None,
    judge_checkpoint: Path | None = None,
    output: Path | None = None,
    fresh: bool = False,
    max_gen_retries: int = 0,
    max_judge_retries: int = 0,
    deterministic_risk_renderer: bool = False,
    deterministic_fact_renderer: bool = False,
    deterministic_revenue_renderer: bool = False,
    audit_version: str | None = None,
) -> dict[str, Any]:
    default_gen, default_judge, default_output = sentinel_artifact_paths(replicate_id)
    gen_checkpoint = gen_checkpoint or default_gen
    judge_checkpoint = judge_checkpoint or default_judge
    output = output or default_output
    saved = _install_contract()
    try:
        report = base.run(
            replicate_id=replicate_id,
            artifact_path=artifact_path,
            gen_checkpoint=gen_checkpoint,
            judge_checkpoint=judge_checkpoint,
            output=output,
            fresh=fresh,
            max_gen_retries=max_gen_retries,
            max_judge_retries=max_judge_retries,
            deterministic_risk_renderer=deterministic_risk_renderer,
            deterministic_fact_renderer=deterministic_fact_renderer,
            deterministic_revenue_renderer=deterministic_revenue_renderer,
        )
    finally:
        _restore_contract(saved)

    scope_audit = _scope_contract_audit(report)
    version = audit_version or ("v14" if deterministic_risk_renderer else "v13")
    if not version.startswith("v") or not version[1:].isdigit():
        raise ValueError("audit_version must look like v13 or v14")
    report["audit"] = f"answer_scope_sentinel_{version}"
    report["sentinel_questions"] = list(SENTINEL_QUESTIONS)
    report["scope_contract_audit"] = scope_audit
    report["pre_registered_gates"] = {
        "ten_cases_complete": True,
        "regression_contexts_byte_identical": True,
        "risk_targets_at_least_0_95": True,
        "faithfulness_exactly_1_0": True,
        "semantic_drop_no_more_than_0_10": True,
        "deterministic_grounding_contracts": True,
        "azure_numeric_stability_canary": True,
        "aws_numeric_comparison_canary": True,
        "risk_evidence_roles_contract": True,
    }
    report.setdefault("gates", {})["risk_evidence_roles_contract"] = all(
        (
            scope_audit["microsoft_roles_present"],
            scope_audit["microsoft_has_canonical_and_supporting"],
            scope_audit["apple_direct_scope_present"],
            scope_audit["apple_unrequested_broadening_absent"],
        )
    )
    if deterministic_risk_renderer:
        report["pre_registered_gates"]["deterministic_risk_renderer"] = True
        report.setdefault("gates", {})["deterministic_risk_renderer"] = (
            scope_audit["microsoft_deterministic_renderer_applied"]
        )
    if deterministic_fact_renderer:
        report["pre_registered_gates"]["deterministic_fact_renderer"] = True
        report.setdefault("gates", {})["deterministic_fact_renderer"] = (
            not scope_audit["deterministic_fact_renderer_case_present"]
            or scope_audit["deterministic_fact_renderer_applied"]
        )
    if deterministic_revenue_renderer:
        report["pre_registered_gates"]["deterministic_revenue_renderer"] = True
        report.setdefault("gates", {})["deterministic_revenue_renderer"] = (
            scope_audit["deterministic_revenue_renderer_applied"]
        )
    report["enumeration_answer_renderer_fingerprint"] = (
        ENUMERATION_ANSWER_RENDERER_FINGERPRINT
    )
    report["deterministic_revenue_renderer"] = deterministic_revenue_renderer
    report["passed"] = all(report.get("gates", {}).values())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replicate-id", required=True)
    parser.add_argument("--artifact", type=Path, default=base.ARTIFACT_PATH)
    parser.add_argument("--gen-checkpoint", type=Path)
    parser.add_argument("--judge-checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
    parser.add_argument(
        "--deterministic-risk-renderer",
        action="store_true",
        help="Use the candidate-only provider-free exhaustive-risk renderer.",
    )
    parser.add_argument(
        "--deterministic-fact-renderer",
        action="store_true",
        help="Use the candidate-only provider-free auditor fact renderer.",
    )
    parser.add_argument(
        "--deterministic-revenue-renderer",
        action="store_true",
        help="Use the candidate-only provider-free revenue renderer.",
    )
    parser.add_argument(
        "--audit-version",
        help="Version label for this isolated candidate report.",
    )
    args = parser.parse_args(argv)
    report = run(
        replicate_id=args.replicate_id,
        artifact_path=args.artifact,
        gen_checkpoint=args.gen_checkpoint,
        judge_checkpoint=args.judge_checkpoint,
        output=args.output,
        fresh=args.fresh,
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
        deterministic_risk_renderer=args.deterministic_risk_renderer,
        deterministic_fact_renderer=args.deterministic_fact_renderer,
        deterministic_revenue_renderer=args.deterministic_revenue_renderer,
        audit_version=args.audit_version,
    )
    # Windows consoles may use cp1252; JSON escaping keeps a completed provider
    # run from being misclassified as a campaign failure after the artifact was
    # already written successfully.
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
