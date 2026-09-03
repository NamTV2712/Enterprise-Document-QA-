"""Run the final provider-free Answer Scope closure contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.evaluation.revenue_intent_contract import (
    MICROSOFT_MAIN_REVENUE_QUESTION,
    REVENUE_INTENT_CONTRACT_FINGERPRINT,
    audit_revenue_intent_scope,
)
from src.evaluation.test_set import TEST_SET
from src.generation.enumeration_completeness import (
    assess_enumeration_completeness,
    extract_evidence_items,
)
from src.generation.enumeration_answer_renderer import (
    ENUMERATION_ANSWER_RENDERER_FINGERPRINT,
    render_deterministic_revenue_answer,
)
from src.generation.period_value_completeness import parse_evidence_sources


ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
DEFAULT_OUTPUT = Path("data/diagnostics/answer_scope_closure_v1_offline.json")
HISTORICAL_V19 = Path(
    "data/eval_artifacts/answer_scope_v19_sentinel_summary_r1.json"
)
EXHAUSTIVE_REVENUE_QUESTION = "What are all of Microsoft's revenue sources?"


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _case_context(
    artifact_by_question: dict[str, dict[str, Any]],
    test_by_question: dict[str, Any],
    question: str,
) -> str:
    return render_case_context(
        artifact_by_question[question],
        required_keywords=test_by_question[question].required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
    )


def _historical_answer() -> str | None:
    if not HISTORICAL_V19.exists():
        return None
    payload = json.loads(HISTORICAL_V19.read_text(encoding="utf-8"))
    for case in payload.get("cases", []):
        if case.get("question") == MICROSOFT_MAIN_REVENUE_QUESTION:
            answer = case.get("answer")
            return str(answer) if answer else None
    return None


def run(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    output: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact_by_question = {
        case["question"]: case for case in artifact["cases"]
    }
    test_by_question = {
        case.question: case for case in TEST_SET if case.priority <= 2
    }
    rows: dict[str, dict[str, Any]] = {}
    source_boundaries_valid = True
    render_deterministic = True
    for question, test_case in test_by_question.items():
        context = _case_context(artifact_by_question, test_by_question, question)
        repeat = _case_context(artifact_by_question, test_by_question, question)
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

    context = _case_context(
        artifact_by_question, test_by_question, MICROSOFT_MAIN_REVENUE_QUESTION
    )
    main_answer = render_deterministic_revenue_answer(
        MICROSOFT_MAIN_REVENUE_QUESTION, context
    ) or ""
    exhaustive_answer = render_deterministic_revenue_answer(
        EXHAUSTIVE_REVENUE_QUESTION, context
    ) or ""
    main_scope = audit_revenue_intent_scope(
        MICROSOFT_MAIN_REVENUE_QUESTION, context, main_answer
    )
    exhaustive_scope = audit_revenue_intent_scope(
        EXHAUSTIVE_REVENUE_QUESTION, context, exhaustive_answer
    )
    evidence_items = extract_evidence_items(
        "revenue", parse_evidence_sources(context)
    )
    support_items = [
        item.label for item in evidence_items if item.evidence_role == "supporting"
    ]
    historical_answer = _historical_answer()
    historical_scope = (
        audit_revenue_intent_scope(
            MICROSOFT_MAIN_REVENUE_QUESTION, context, historical_answer
        )
        if historical_answer
        else {"applicable": False, "passed": False, "reason": "missing_report"}
    )
    gates = {
        "priority_2_case_count": len(rows) == 30,
        "source_boundaries_valid": source_boundaries_valid,
        "render_deterministic": render_deterministic,
        "revenue_supporting_item_present": (
            "search and news advertising" in {
                label.casefold() for label in support_items
            }
        ),
        "main_renderer_applied": bool(main_answer),
        "main_renderer_excludes_supporting_heading": (
            "Search and News Advertising" not in main_answer
        ),
        "main_scope_contract": main_scope.get("passed") is True,
        "exhaustive_scope_contract": exhaustive_scope.get("passed") is True,
        "exhaustive_renderer_keeps_supporting_heading": (
            "search and news advertising" in exhaustive_answer.casefold()
        ),
        "historical_v19_scope_contract": historical_scope.get("passed") is True,
        "generation_ground_truth_dependency": (
            main_scope.get("generation_ground_truth_dependency") is False
            and exhaustive_scope.get("generation_ground_truth_dependency") is False
        ),
    }
    report = {
        "schema_version": 1,
        "audit": "answer_scope_closure_offline_v1",
        "official": False,
        "artifact_path": str(artifact_path),
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V6,
        "num_cases": len(rows),
        "rows": rows,
        "revenue": {
            "question": MICROSOFT_MAIN_REVENUE_QUESTION,
            "main_answer": main_answer,
            "exhaustive_answer": exhaustive_answer,
            "main_scope": main_scope,
            "exhaustive_scope": exhaustive_scope,
            "supporting_evidence_items": support_items,
            "historical_v19_scope": historical_scope,
        },
        "fingerprints": {
            "revenue_intent_contract": REVENUE_INTENT_CONTRACT_FINGERPRINT,
            "enumeration": __import__(
                "src.generation.enumeration_completeness",
                fromlist=["ENUMERATION_COMPLETENESS_FINGERPRINT"],
            ).ENUMERATION_COMPLETENESS_FINGERPRINT,
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
    args = parser.parse_args(argv)
    report = run(artifact_path=args.artifact, output=args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
