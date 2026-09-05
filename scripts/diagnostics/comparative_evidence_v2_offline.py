"""Provider-free audit for Comparative Evidence Contract v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.diagnostics.answerability_stability_v1_offline import (
    ARTIFACT_PATH,
    CANDIDATE_PATH,
    TARGET_QUESTION,
    run as run_answerability_audit,
)
from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V7, render_case_context
from src.evaluation.test_set import TEST_SET
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.comparative_answer_renderer import (
    COMPARATIVE_ANSWER_RENDERER_FINGERPRINT,
    render_dependency_comparison,
)
from src.generation.comparative_evidence import COMPARATIVE_EVIDENCE_FINGERPRINT
from src.generation.comparative_answerability import COMPARATIVE_ANSWERABILITY_FINGERPRINT
from src.generation.period_value_completeness import validate_grounded_answer


DEFAULT_OUTPUT = Path("data/diagnostics/comparative_evidence_v2_offline.json")


def run(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    candidate_path: Path = CANDIDATE_PATH,
    output: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    base = run_answerability_audit(
        artifact_path=artifact_path,
        candidate_path=candidate_path,
        output=None,
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    target_payload = next(case for case in artifact["cases"] if case["question"] == TARGET_QUESTION)
    target_test = next(case for case in TEST_SET if case.question == TARGET_QUESTION)
    target_context = render_case_context(
        target_payload,
        required_keywords=target_test.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
    )
    target_answer = render_dependency_comparison(TARGET_QUESTION, target_context)
    renderer_passed = bool(
        target_answer
        and "do not establish which company depends more" in target_answer
        and validate_grounded_answer(target_answer, target_context)
    )
    base.update(
        {
            "schema_version": 2,
            "audit": "comparative_evidence_v2_offline",
            "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
            "answerability_fingerprint": COMPARATIVE_ANSWERABILITY_FINGERPRINT,
            "comparative_evidence_fingerprint": COMPARATIVE_EVIDENCE_FINGERPRINT,
            "comparative_answer_renderer_fingerprint": COMPARATIVE_ANSWER_RENDERER_FINGERPRINT,
            "target_renderer_answer": target_answer,
        }
    )
    base["gates"].update({"dependency_renderer_contract": renderer_passed})
    base["passed"] = all(base["gates"].values())
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(
        artifact_path=args.artifact,
        candidate_path=args.candidate,
        output=args.output,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
