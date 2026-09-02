"""Run a provider-free audit of the Answer Stability/Completeness contract.

The audit renders the frozen Phase 1 evidence with a selected context policy
and inspects generated answers from an existing Phase 2 result.  It never
calls a provider and never uses reference answers or benchmark labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.generation.answer_stability import ANSWER_STABILITY_FINGERPRINT
from src.generation.answer_stability import assess_answer_stability


DEFAULT_PHASE1 = Path("data/eval_artifacts/phase1_priority2.json")
DEFAULT_OFFICIAL = Path("data/eval_artifacts/phase2_results_packed_selective_v2.json")
DEFAULT_CANDIDATE = Path(
    "data/eval_artifacts/phase2_results_fact_evidence_v1_candidate.json"
)
DEFAULT_OUTPUT = Path("data/diagnostics/answer_stability_contract_v1.json")
EXPECTED_OFFICIAL_SHA256 = (
    "sha256:a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)
EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:1ad021ce72af2116f9b4f7ad780d5c6e809fd5a01e46d30d0ae4bfecd62599d9"
)


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _artifact_fingerprint(artifact: dict[str, Any]) -> str:
    fingerprints = artifact.get("fingerprints") or {}
    value = fingerprints.get("artifact")
    if isinstance(value, str):
        return value
    value = artifact.get("artifact_fingerprint")
    if isinstance(value, str):
        return value
    raise RuntimeError("Phase 1 artifact has no artifact fingerprint")


def audit_result(
    artifact: dict[str, Any],
    result: dict[str, Any],
    strategy: str,
) -> dict[str, Any]:
    answers = {
        case.get("question"): case.get("answer", "")
        for case in result.get("cases", [])
        if isinstance(case.get("question"), str)
    }
    rows: list[dict[str, Any]] = []
    for case in artifact.get("cases", []):
        question = case.get("question")
        if not isinstance(question, str):
            continue
        assessment = assess_answer_stability(
            question,
            render_case_context(case, strategy=strategy),
            answers.get(question, ""),
        )
        rows.append(
            {
                "question": question,
                "category": case.get("category"),
                "applicable": assessment.applicable,
                "kind": assessment.kind,
                "passed": assessment.passed,
                "expected_facts": [
                    {
                        "value": fact.value,
                        "source_number": fact.source_number,
                    }
                    for fact in assessment.expected_facts
                ],
                "missing_facts": [
                    {
                        "value": fact.value,
                        "source_number": fact.source_number,
                    }
                    for fact in assessment.missing_facts
                ],
            }
        )
    applicable = [row for row in rows if row["applicable"]]
    return {
        "result_path": str(result.get("_path", "")),
        "result_sha256": result.get("_sha256"),
        "result_strategy": result.get("context_strategy"),
        "render_strategy": strategy,
        "case_count": len(rows),
        "applicable_count": len(applicable),
        "passed_count": sum(row["passed"] for row in applicable),
        "failed_questions": [
            row["question"] for row in applicable if not row["passed"]
        ],
        "rows": rows,
    }


def build_report(
    artifact: dict[str, Any],
    official: dict[str, Any],
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    official_audit = audit_result(
        artifact, official, CONTEXT_STRATEGY_SELECTIVE_V5
    )
    candidate_audit = (
        audit_result(artifact, candidate, CONTEXT_STRATEGY_SELECTIVE_V6)
        if candidate is not None
        else None
    )
    candidate_azure = None
    if candidate_audit is not None:
        candidate_azure = next(
            (
                row
                for row in candidate_audit["rows"]
                if row["question"]
                == "How does Microsoft describe its Azure and cloud services growth?"
            ),
            None,
        )
    gates = {
        "artifact_fingerprint_pinned": (
            _artifact_fingerprint(artifact) == EXPECTED_ARTIFACT_FINGERPRINT
        ),
        "official_case_set_complete": official_audit["case_count"] == 30,
        "official_stability_passes": (
            not official_audit["failed_questions"]
        ),
        "official_contract_has_no_missing_facts": (
            all(not row["missing_facts"] for row in official_audit["rows"])
        ),
        "known_candidate_azure_omission_is_detected": (
            candidate_azure is not None
            and candidate_azure["applicable"] is True
            and candidate_azure["passed"] is False
            and [item["value"] for item in candidate_azure["missing_facts"]]
            == ["$168.9 billion"]
        ),
    }
    if candidate_audit is None:
        gates["known_candidate_azure_omission_is_detected"] = True
    return {
        "schema_version": 1,
        "audit": "answer_stability_contract_v1",
        "official": False,
        "answer_stability_fingerprint": ANSWER_STABILITY_FINGERPRINT,
        "phase1_artifact_fingerprint": _artifact_fingerprint(artifact),
        "official_audit": official_audit,
        "candidate": candidate_audit,
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(
    phase1: Path = DEFAULT_PHASE1,
    official_path: Path = DEFAULT_OFFICIAL,
    candidate_path: Path | None = DEFAULT_CANDIDATE,
    output: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    artifact = json.loads(phase1.read_text(encoding="utf-8"))
    official = json.loads(official_path.read_text(encoding="utf-8"))
    if _file_sha256(official_path) != EXPECTED_OFFICIAL_SHA256:
        raise RuntimeError("Protected official result SHA-256 drift")
    official["_path"] = str(official_path)
    official["_sha256"] = _file_sha256(official_path)
    candidate = None
    if candidate_path is not None and candidate_path.exists():
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["_path"] = str(candidate_path)
        candidate["_sha256"] = _file_sha256(candidate_path)
    report = build_report(artifact, official, candidate)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--phase1", type=Path, default=DEFAULT_PHASE1)
    parser.add_argument("--official", type=Path, default=DEFAULT_OFFICIAL)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(args.phase1, args.official, args.candidate, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
