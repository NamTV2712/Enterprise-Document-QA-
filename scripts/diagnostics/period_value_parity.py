"""Offline parity audit for the shared period/value completion policy.

The audit consumes the frozen Phase 1 artifact only. It renders the exact
``selective_packed_v2`` context used by Phase 2, round-trips its source blocks
through the production adapter, and verifies that generation, deterministic
metrics, and judging can consume the same evidence content. A full-evidence
shadow check also prevents broader contexts from activating extra or ambiguous
period/value rows. No provider, retriever, or mutable evaluation result is
touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    EXPECTED_ARTIFACT_FINGERPRINT,
    build_production_judge_prompt,
    compute_case_metrics,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V2,
    render_case_context,
)
from src.evaluation.generation_checkpoint import (
    build_evidence_context,
    parse_evidence_context,
)
from src.evaluation.phase2_runtime import JUDGE_CONTEXT_BUILDER_FINGERPRINT
from src.evaluation.test_set import TEST_SET
from src.generation.period_value_completeness import (
    assess_period_value_completeness,
    parse_evidence_sources,
    render_chunk_evidence,
)


EXPECTED_CASES = 30
EXPECTED_APPLICABLE_CASES = 1
AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)
EXPECTED_AWS_PAIRS = [
    {"period": "2024", "value": "107,556", "source_number": 1},
    {"period": "2025", "value": "128,725", "source_number": 1},
]


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _source_signature(context: str) -> list[dict[str, Any]]:
    return [
        {
            "number": source.number,
            "citation": source.citation,
            "text": source.text,
        }
        for source in parse_evidence_sources(context)
    ]


def _pair_rows(assessment: Any) -> list[dict[str, Any]]:
    return [
        {
            "period": pair.period,
            "value": pair.value,
            "source_number": pair.source_number,
        }
        for pair in assessment.evidence_pairs
    ]


def _judge_content_parity(
    question: str,
    context: str,
    ground_truth: str,
) -> bool:
    """Ensure the judge prompt contains each exact rendered source block."""
    prompt = build_production_judge_prompt(
        question,
        "placeholder answer [Source 1].",
        context,
        ground_truth,
    )
    cursor = -1
    for index, source in enumerate(parse_evidence_sources(context), start=1):
        fragment = f"[Chunk {index}] {source.citation}\n{source.text}"
        position = prompt.find(fragment, cursor + 1)
        if position < 0:
            return False
        cursor = position + len(fragment)
    return True


def audit_case(case_payload: dict[str, Any], test_case: Any) -> dict[str, Any]:
    """Audit one frozen case without making a provider call."""
    context = render_case_context(
        case_payload,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
    )
    parsed_legacy = parse_evidence_context(context)
    parsed_shared = _source_signature(context)
    production_context = render_chunk_evidence(parsed_legacy)
    assessment = assess_period_value_completeness(
        test_case.question,
        context,
        "",
    )
    full_assessment = assess_period_value_completeness(
        test_case.question,
        build_evidence_context(case_payload),
        "",
    )
    compute_case_metrics(
        case_payload,
        "",
        test_case.required_keywords,
        test_case.expects_fallback,
        evidence_context=context,
    )
    return {
        "question": test_case.question,
        "category": test_case.category,
        "context_sha256": _sha256_bytes(context.encode("utf-8")),
        "source_count": len(parsed_shared),
        "source_boundary_parity": parsed_shared == [
            {
                "number": int(block["number"]),
                "citation": block["citation"],
                "text": block["text"],
            }
            for block in parsed_legacy
        ],
        "production_adapter_parity": production_context == context,
        "context_deterministic": context
        == render_case_context(
            case_payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
        ),
        "generation_context_sha256": _sha256_bytes(
            context.encode("utf-8")
        ),
        "metrics_source_sha256": _sha256_bytes(
            "\n\n".join(block["text"] for block in parsed_legacy).encode(
                "utf-8"
            )
        ),
        "judge_content_parity": _judge_content_parity(
            test_case.question,
            context,
            test_case.ground_truth,
        ),
        "judge_context_builder_fingerprint": JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        "metrics_context_source_count": len(parsed_legacy),
        "period_value": {
            "applicable": assessment.applicable,
            "pairs": _pair_rows(assessment),
            "pair_count": len(assessment.evidence_pairs),
        },
        "full_evidence_period_value": {
            "applicable": full_assessment.applicable,
            "pairs": _pair_rows(full_assessment),
            "pair_count": len(full_assessment.evidence_pairs),
        },
    }


def build_report(
    artifact: dict[str, Any],
    *,
    artifact_file_sha256: str,
    priority: int = 2,
) -> dict[str, Any]:
    """Build a deterministic report from an already-loaded artifact."""
    metadata = {case.question: case for case in TEST_SET}
    selected_payloads = [
        payload
        for payload in artifact.get("cases", [])
        if payload.get("question") in metadata
        and metadata[payload["question"]].priority <= priority
    ]
    rows = [
        audit_case(payload, metadata[payload["question"]])
        for payload in selected_payloads
    ]
    rows.sort(key=lambda row: row["question"])
    applicable = [
        row for row in rows if row["period_value"]["applicable"]
    ]
    full_applicable = [
        row
        for row in rows
        if row["full_evidence_period_value"]["applicable"]
    ]
    aws_row = next(
        (row for row in rows if row["question"] == AWS_QUESTION),
        None,
    )
    all_case_parity = all(
        row["source_boundary_parity"]
        and row["production_adapter_parity"]
        and row["context_deterministic"]
        and row["judge_content_parity"]
        for row in rows
    )
    report: dict[str, Any] = {
        "schema_version": 2,
        "artifact_fingerprint": artifact.get("fingerprints", {}).get(
            "artifact"
        ),
        "artifact_file_sha256": artifact_file_sha256,
        "priority": priority,
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "expected_policy": {
            "cases": EXPECTED_CASES,
            "applicable_cases": EXPECTED_APPLICABLE_CASES,
            "full_evidence_applicable_cases": EXPECTED_APPLICABLE_CASES,
            "aws_pairs": EXPECTED_AWS_PAIRS,
        },
        "num_cases": len(rows),
        "num_applicable_cases": len(applicable),
        "num_full_evidence_applicable_cases": len(full_applicable),
        "source_boundary_parity_cases": sum(
            row["source_boundary_parity"] for row in rows
        ),
        "production_adapter_parity_cases": sum(
            row["production_adapter_parity"] for row in rows
        ),
        "generation_metrics_judge_parity_cases": sum(
            row["judge_content_parity"] for row in rows
        ),
        "all_case_parity": all_case_parity,
        "applicable_questions": [row["question"] for row in applicable],
        "full_evidence_applicable_questions": [
            row["question"] for row in full_applicable
        ],
        "aws_pairs": (
            aws_row["period_value"]["pairs"] if aws_row is not None else []
        ),
        "full_evidence_aws_pairs": (
            aws_row["full_evidence_period_value"]["pairs"]
            if aws_row is not None
            else []
        ),
        "cases": rows,
    }
    report["passed"] = bool(
        report["artifact_fingerprint"] == EXPECTED_ARTIFACT_FINGERPRINT
        and report["num_cases"] == EXPECTED_CASES
        and report["num_applicable_cases"] == EXPECTED_APPLICABLE_CASES
        and report["num_full_evidence_applicable_cases"]
        == EXPECTED_APPLICABLE_CASES
        and report["applicable_questions"] == [AWS_QUESTION]
        and report["full_evidence_applicable_questions"] == [AWS_QUESTION]
        and report["aws_pairs"] == EXPECTED_AWS_PAIRS
        and report["full_evidence_aws_pairs"] == EXPECTED_AWS_PAIRS
        and all_case_parity
    )
    return report


def run(artifact_path: Path, priority: int = 2) -> dict[str, Any]:
    """Load and audit the frozen artifact without mutating it."""
    raw = artifact_path.read_bytes()
    artifact = json.loads(raw.decode("utf-8"))
    return build_report(
        artifact,
        artifact_file_sha256=_sha256_bytes(raw),
        priority=priority,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("data/eval_artifacts/phase1_priority2.json"),
    )
    parser.add_argument("--priority", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run(args.artifact, args.priority)
    rendered = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
