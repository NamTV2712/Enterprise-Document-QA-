"""Provider-free audit for the evidence-derived enumeration contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.enumeration_completeness import (
    assess_enumeration_completeness,
)
from src.generation.period_value_completeness import (
    parse_evidence_sources,
    render_chunk_evidence,
)


DEFAULT_OUTPUT = Path("data/diagnostics/enumeration_answer_completeness_v1.json")


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _case_context(case: dict[str, Any], test_case: Any) -> str:
    return render_case_context(
        case,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
    )


def _roundtrip_passes(context: str) -> bool:
    blocks = parse_evidence_context(context)
    chunks = [
        {"citation": block["citation"], "text": block["text"]}
        for block in blocks
    ]
    return bool(blocks) and render_chunk_evidence(chunks) == context


def run(
    artifact_path: Path = ARTIFACT_PATH,
    output: Path | None = None,
) -> dict[str, Any]:
    artifact, _ = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V5,
    )
    selected = [case for case in TEST_SET if case.priority <= 2]
    test_by_question = {case.question: case for case in selected}
    artifact_by_question = {case["question"]: case for case in artifact["cases"]}

    rows: list[dict[str, Any]] = []
    for question, test_case in test_by_question.items():
        case = artifact_by_question.get(question)
        if case is None:
            rows.append({"question": question, "status": "missing_artifact_case"})
            continue
        context = _case_context(case, test_case)
        sources = parse_evidence_sources(context)
        assessment = assess_enumeration_completeness(
            question, context, test_case.ground_truth
        )
        rows.append({
            "question": question,
            "category": test_case.category,
            "context_sha256": _sha256(context),
            "source_count": len(sources),
            "roundtrip": _roundtrip_passes(context),
            "enumeration_applicable": assessment.applicable,
            "enumeration_kind": assessment.kind,
            "evidence_items": [item.label for item in assessment.evidence_items],
            "evidence_aliases": [
                alias
                for item in assessment.evidence_items
                for alias in item.aliases
            ],
            "missing_against_ground_truth": [
                item.label for item in assessment.missing_items
            ],
        })

    enum_rows = {
        row["question"]: row
        for row in rows
        if row.get("category") == "enumeration"
    }
    non_enum_rows = [
        row for row in rows if row.get("category") != "enumeration"
    ]
    expected_enum = {
        "What are the main sources of revenue for Microsoft?": {
            "Microsoft 365", "Azure", "LinkedIn", "Dynamics", "Gaming",
            "Search and News Advertising", "Windows and Devices",
        },
        "What are all the product categories Apple sells?": {
            "smartphones", "personal computers", "tablets", "wearables",
            "accessories", "services",
        },
        "What are the different business segments Amazon operates?": {
            "North America", "International", "Amazon Web Services",
        },
        "What are all the major risk factors Microsoft discloses?": {
            "Strategic And Competitive Risks", "Trade", "Cybersecurity", "AI",
            "Handling of personal data", "Operational Risks",
            "Legal, Regulatory, And Litigation Risks",
        },
    }

    item_checks: dict[str, bool] = {}
    for question, expected_labels in expected_enum.items():
        row = enum_rows.get(question, {})
        observed = {
            value.casefold()
            for value in row.get("evidence_items", [])
            + row.get("evidence_aliases", [])
        }
        item_checks[question] = (
            row.get("enumeration_applicable") is True
            and {label.casefold() for label in expected_labels}.issubset(observed)
        )

    enum_replay_same = True
    for question, test_case in test_by_question.items():
        case = artifact_by_question.get(question)
        if case is None:
            enum_replay_same = False
            continue
        first = _case_context(case, test_case)
        second = _case_context(case, test_case)
        enum_replay_same = enum_replay_same and first == second

    gates = {
        "all_priority_cases_present": len(rows) == len(selected),
        "all_contexts_have_source_roundtrip": len(rows) == len(selected)
        and all(row.get("roundtrip") is True for row in rows),
        "exactly_four_enumeration_cases": len(enum_rows) == 4,
        "all_enumeration_cases_applicable": len(enum_rows) == 4
        and all(row.get("enumeration_applicable") is True for row in enum_rows.values()),
        "non_enumeration_cases_noop": len(non_enum_rows) == len(selected) - 4
        and all(row.get("enumeration_applicable") is False for row in non_enum_rows),
        "required_evidence_items_present": all(item_checks.values()),
        "renderer_repeat_is_identical": enum_replay_same,
        "provider_free": True,
    }
    report = {
        "schema_version": 1,
        "audit": "enumeration_answer_completeness_v1",
        "official": False,
        "artifact_path": str(artifact_path),
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V5,
        "num_selected": len(selected),
        "num_enumeration": len(enum_rows),
        "rows": rows,
        "item_checks": item_checks,
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
    report = run(args.artifact, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
