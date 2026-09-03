"""Run provider-free gates for the Answer Scope v13 contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V6, render_case_context
from src.evaluation.test_set import TEST_SET
from src.generation.enumeration_completeness import (
    assess_enumeration_completeness,
    extract_evidence_items,
)
from src.generation.period_value_completeness import parse_evidence_sources
from src.generation.prompt_contracts import (
    ENUMERATION_COMPLETENESS_CONTRACT,
    RISK_FOCUS_CONTRACT,
    answer_completion_contract_for_question,
)


ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
DEFAULT_OUTPUT = Path("data/diagnostics/answer_scope_v13_offline.json")
MICROSOFT_RISK_QUESTION = "What are all the major risk factors Microsoft discloses?"
APPLE_QUALITY_QUESTION = "What quality and manufacturing risks does Apple mention?"


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def run(
    *, artifact_path: Path = ARTIFACT_PATH, output: Path | None = DEFAULT_OUTPUT
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    by_question = {case["question"]: case for case in artifact["cases"]}
    test_by_question = {case.question: case for case in TEST_SET if case.priority <= 2}
    rows: dict[str, dict[str, Any]] = {}
    source_boundaries_valid = True
    render_deterministic = True
    for question, test_case in test_by_question.items():
        payload = by_question[question]
        context = render_case_context(
            payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )
        repeat = render_case_context(
            payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )
        sources = parse_evidence_sources(context)
        boundary_ok = bool(sources) and all(
            source.number > 0 and bool(source.text.strip()) for source in sources
        )
        source_boundaries_valid = source_boundaries_valid and boundary_ok
        render_deterministic = render_deterministic and context == repeat
        rows[question] = {
            "context_sha256": _sha256(context),
            "source_count": len(sources),
            "source_boundary_parse_passed": boundary_ok,
            "render_deterministic": context == repeat,
        }

    microsoft_sources = parse_evidence_sources(
        render_case_context(
            by_question[MICROSOFT_RISK_QUESTION],
            required_keywords=test_by_question[MICROSOFT_RISK_QUESTION].required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )
    )
    microsoft_items = extract_evidence_items("risk", microsoft_sources)
    role_counts = {
        role: sum(item.evidence_role == role for item in microsoft_items)
        for role in ("canonical", "supporting")
    }
    synthetic_answer = "\n".join(
        f"- {item.label} [Source {item.source_number}]"
        for item in microsoft_items
    )
    microsoft_assessment = assess_enumeration_completeness(
        MICROSOFT_RISK_QUESTION,
        "\n".join(
            f"[Source {source.number}] {source.text}" for source in microsoft_sources
        ),
        synthetic_answer,
    )
    risk_contract = answer_completion_contract_for_question(APPLE_QUALITY_QUESTION)
    gates = {
        "priority_2_case_count": len(rows) == 30,
        "source_boundaries_valid": source_boundaries_valid,
        "render_deterministic": render_deterministic,
        "microsoft_roles_present": bool(microsoft_items),
        "microsoft_has_primary_and_supporting_roles": (
            role_counts["canonical"] > 0 and role_counts["supporting"] > 0
        ),
        "microsoft_complete_role_aware_assessment": (
            microsoft_assessment.passed and microsoft_assessment.missing_items == ()
        ),
        "apple_direct_scope_contract": (
            "design or manufacturing defects" in risk_contract
            and "third-party components or products" in risk_contract
            and "generic supplier continuity" in risk_contract
        ),
        "risk_enumeration_contract_has_two_tiers": (
            "primary list" in ENUMERATION_COMPLETENESS_CONTRACT
            and "additional section" in ENUMERATION_COMPLETENESS_CONTRACT
        ),
    }
    report = {
        "schema_version": 1,
        "audit": "answer_scope_offline_v13",
        "official": False,
        "artifact_path": str(artifact_path),
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V6,
        "num_cases": len(rows),
        "rows": rows,
        "microsoft_risk_role_counts": role_counts,
        "microsoft_risk_labels": [item.label for item in microsoft_items],
        "fingerprints": {
            "risk_focus": __import__(
                "src.generation.prompt_contracts", fromlist=["RISK_FOCUS_CONTRACT_FINGERPRINT"]
            ).RISK_FOCUS_CONTRACT_FINGERPRINT,
            "enumeration": __import__(
                "src.generation.enumeration_completeness",
                fromlist=["ENUMERATION_COMPLETENESS_FINGERPRINT"],
            ).ENUMERATION_COMPLETENESS_FINGERPRINT,
        },
        "gates": gates,
        "passed": all(gates.values()),
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(artifact_path=args.artifact, output=args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
