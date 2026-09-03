"""Run provider-free gates for the Answer Scope v14 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.diagnostics import answer_scope_offline as v13
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.evaluation.test_set import TEST_SET
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.evidence_fact_renderer import (
    EVIDENCE_FACT_RENDERER_FINGERPRINT,
    render_auditor_fact,
)
from src.generation.enumeration_answer_renderer import (
    ENUMERATION_ANSWER_RENDERER_FINGERPRINT,
    render_deterministic_revenue_answer,
)
from src.generation.enumeration_completeness import (
    assess_enumeration_completeness,
    enumeration_kind,
)
from src.generation.period_value_completeness import parse_evidence_sources
from src.generation.prompt_contracts import RISK_FOCUS_CONTRACT_FINGERPRINT
from src.generation.prompt_contracts import (
    RISK_COMPARISON_CONTRACT,
    RISK_COMPARISON_CONTRACT_FINGERPRINT,
    answer_completion_contract_for_question,
)
from src.generation.risk_answer_shape import (
    RISK_ANSWER_SHAPE_FINGERPRINT,
    assess_risk_answer_shape,
    render_deterministic_risk_answer,
)


ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
DEFAULT_OUTPUT = Path("data/diagnostics/answer_scope_v14_offline.json")
MICROSOFT_RISK_QUESTION = "What are all the major risk factors Microsoft discloses?"
APPLE_QUALITY_QUESTION = "What quality and manufacturing risks does Apple mention?"


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def run(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    output: Path | None = DEFAULT_OUTPUT,
    audit_version: str = "v14",
) -> dict[str, Any]:
    inherited = v13.run(artifact_path=artifact_path, output=None)
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    by_question = {case["question"]: case for case in artifact["cases"]}
    test_by_question = {
        case.question: case for case in TEST_SET if case.priority <= 2
    }

    risk_rows: dict[str, dict[str, Any]] = {}
    for question, test_case in test_by_question.items():
        if enumeration_kind(question) != "risk":
            continue
        context = render_case_context(
            by_question[question],
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )
        first = render_deterministic_risk_answer(question, context)
        second = render_deterministic_risk_answer(question, context)
        shape = assess_risk_answer_shape(question, context, first or "")
        risk_rows[question] = {
            "context_sha256": _sha256(context),
            "rendered_answer_sha256": _sha256(first or ""),
            "rendered_answer": first,
            "render_byte_stable": first == second,
            "shape": {
                "applicable": shape.applicable,
                "canonical_count": shape.canonical_count,
                "supporting_count": shape.supporting_count,
                "reason_codes": list(shape.reason_codes),
                "passed": shape.passed,
            },
            "source_count": len(parse_evidence_sources(context)),
        }

    microsoft = risk_rows.get(MICROSOFT_RISK_QUESTION) or {}
    apple_case = by_question[APPLE_QUALITY_QUESTION]
    apple_meta = test_by_question[APPLE_QUALITY_QUESTION]
    apple_context = render_case_context(
        apple_case,
        required_keywords=apple_meta.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
    )
    gates = {
        **(inherited.get("gates") or {}),
        "risk_rows_present": bool(risk_rows),
        "microsoft_renderer_shape_passed": (
            microsoft.get("shape", {}).get("passed") is True
        ),
        "microsoft_renderer_byte_stable": (
            microsoft.get("render_byte_stable") is True
        ),
        "scoped_apple_does_not_activate_exhaustive_renderer": (
            render_deterministic_risk_answer(
                APPLE_QUALITY_QUESTION, apple_context
            )
            is None
        ),
    }
    if audit_version.startswith(("v17", "v18", "v19")):
        auditor_question = "Who audited Microsoft's financial statements?"
        auditor_test = test_by_question[auditor_question]
        auditor_context = render_case_context(
            by_question[auditor_question],
            required_keywords=auditor_test.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )
        auditor_first = render_auditor_fact(auditor_question, auditor_context)
        auditor_second = render_auditor_fact(auditor_question, auditor_context)
        comparison_question = (
            "Compare Apple's and Amazon's approach to international operations risk."
        )
        comparison_contract = answer_completion_contract_for_question(
            comparison_question
        )
        gates.update(
            {
                "auditor_fact_renderer_present": bool(auditor_first),
                "auditor_fact_renderer_byte_stable": (
                    auditor_first == auditor_second
                ),
                "risk_comparison_contract_present": (
                    RISK_COMPARISON_CONTRACT in comparison_contract
                ),
            }
        )
    if audit_version.startswith(("v18", "v19")):
        revenue_question = "What are the main sources of revenue for Microsoft?"
        revenue_test = test_by_question[revenue_question]
        revenue_context = render_case_context(
            by_question[revenue_question],
            required_keywords=revenue_test.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )
        revenue_first = render_deterministic_revenue_answer(
            revenue_question, revenue_context
        )
        revenue_second = render_deterministic_revenue_answer(
            revenue_question, revenue_context
        )
        gates.update(
            {
                "revenue_renderer_present": bool(revenue_first),
                "revenue_renderer_byte_stable": revenue_first == revenue_second,
                "revenue_renderer_uses_canonical_citations": bool(
                    revenue_first
                    and all(
                        f"[Source {item.source_number}]" in revenue_first
                        for item in assess_enumeration_completeness(
                            revenue_question, revenue_context, ""
                        ).required_items
                    )
                ),
            }
        )
    report = {
        "schema_version": 1,
        "audit": f"answer_scope_offline_{audit_version}",
        "official": False,
        "artifact_path": str(artifact_path),
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V6,
        "inherited_v13_gates": inherited.get("gates"),
        "risk_rows": risk_rows,
        "fingerprints": {
            "risk_answer_shape": RISK_ANSWER_SHAPE_FINGERPRINT,
            "answer_completion": ANSWER_COMPLETION_FINGERPRINT,
            "evidence_fact_renderer": EVIDENCE_FACT_RENDERER_FINGERPRINT,
            "risk_focus": RISK_FOCUS_CONTRACT_FINGERPRINT,
            "risk_comparison": RISK_COMPARISON_CONTRACT_FINGERPRINT,
            "enumeration_answer_renderer": ENUMERATION_ANSWER_RENDERER_FINGERPRINT,
        },
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-version", default="v14")
    args = parser.parse_args(argv)
    report = run(
        artifact_path=args.artifact,
        output=args.output,
        audit_version=args.audit_version,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
