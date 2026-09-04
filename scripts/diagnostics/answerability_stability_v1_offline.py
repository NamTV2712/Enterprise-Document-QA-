"""Provider-free audit for the comparative answerability guard."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    CONTEXT_STRATEGY_SELECTIVE_V7,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_FINGERPRINT,
    assess_comparative_answerability,
)
from src.generation.period_value_completeness import FALLBACK_ANSWER


ARTIFACT_PATH = Path(
    "data/eval_artifacts/phase1_priority2_financial_table_units.json"
)
CANDIDATE_PATH = Path(
    "data/eval_artifacts/phase2_results_p2_canonical_units_v7_20260904.json"
)
DEFAULT_OUTPUT = Path(
    "data/diagnostics/answerability_stability_v1_offline.json"
)
TARGET_QUESTION = (
    "Which company depends more on cloud/subscription revenue, Microsoft or Apple?"
)
OUT_OF_CORPUS_QUESTION = "What are Disney's main risk factors?"


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    candidate_path: Path = CANDIDATE_PATH,
    output: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact_by_question = {case["question"]: case for case in artifact["cases"]}
    test_by_question = {
        case.question: case for case in TEST_SET if case.priority <= 2
    }

    rows: dict[str, dict[str, Any]] = {}
    context_deterministic = True
    non_fact_v5_identity = True
    comparative_counterfactuals_passed = True
    for question, test_case in test_by_question.items():
        payload = artifact_by_question[question]
        context = render_case_context(
            payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        repeat = render_case_context(
            payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        deterministic = context == repeat
        context_deterministic = context_deterministic and deterministic
        row: dict[str, Any] = {
            "context_sha256": _sha256_text(context),
            "source_count": len(parse_evidence_context(context)),
            "render_deterministic": deterministic,
        }
        if test_case.category != "fact_lookup":
            v5_context = render_case_context(
                payload,
                required_keywords=test_case.required_keywords,
                strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
            )
            same_as_v5 = context == v5_context
            row["v5_context_sha256"] = _sha256_text(v5_context)
            row["v5_v7_context_identical"] = same_as_v5
            non_fact_v5_identity = non_fact_v5_identity and same_as_v5
        if test_case.category == "comparative":
            counterfactual = assess_comparative_answerability(
                question, context, FALLBACK_ANSWER
            )
            row.update(
                {
                    "counterfactual_applicable": counterfactual.applicable,
                    "counterfactual_evidence_sufficient": (
                        counterfactual.evidence_sufficient
                    ),
                    "counterfactual_expected_tickers": list(
                        counterfactual.expected_tickers
                    ),
                    "counterfactual_missing_tickers": list(
                        counterfactual.missing_tickers
                    ),
                    "counterfactual_intent_groups": list(
                        counterfactual.intent_groups
                    ),
                }
            )
            comparative_counterfactuals_passed = (
                comparative_counterfactuals_passed
                and counterfactual.applicable
                and counterfactual.evidence_sufficient
                and counterfactual.retry_required
            )
        rows[question] = row

    negative_context = render_case_context(
        artifact_by_question[TARGET_QUESTION],
        strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
    )
    first_source = parse_evidence_context(negative_context)[0]
    one_sided = assess_comparative_answerability(
        TARGET_QUESTION,
        f"[Source 1] {first_source['citation']}\n{first_source['text']}",
        FALLBACK_ANSWER,
    )
    unknown = assess_comparative_answerability(
        OUT_OF_CORPUS_QUESTION,
        negative_context,
        FALLBACK_ANSWER,
    )

    candidate = _load_json(candidate_path)
    candidate_rows = {
        case.get("question"): case for case in (candidate or {}).get("cases", [])
    }
    replay: dict[str, Any] = {}
    if candidate is not None:
        for question in sorted(test_by_question):
            answer = (candidate_rows.get(question) or {}).get("answer") or ""
            context = render_case_context(
                artifact_by_question[question],
                required_keywords=test_by_question[question].required_keywords,
                strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
            )
            assessment = assess_comparative_answerability(question, context, answer)
            replay[question] = {
                "final_answer_fallback": assessment.draft_is_fallback,
                "retry_required_if_replayed": assessment.retry_required,
                "evidence_sufficient": assessment.evidence_sufficient,
            }

    gates = {
        "priority_2_case_count": len(rows) == 30,
        "context_deterministic": context_deterministic,
        "non_fact_v5_contexts_unchanged": non_fact_v5_identity,
        "comparative_counterfactuals_sufficient": comparative_counterfactuals_passed,
        "one_sided_negative_is_safe": (
            one_sided.applicable
            and not one_sided.evidence_sufficient
            and not one_sided.retry_required
            and one_sided.missing_tickers == ("AAPL",)
        ),
        "unknown_company_negative_is_safe": (
            not unknown.applicable and not unknown.retry_required
        ),
    }
    report = {
        "schema_version": 1,
        "audit": "answerability_stability_v1_offline",
        "official": False,
        "provider_free": True,
        "artifact_path": str(artifact_path),
        "candidate_path": str(candidate_path),
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V7,
        "answerability_fingerprint": COMPARATIVE_ANSWERABILITY_FINGERPRINT,
        "target_question": TARGET_QUESTION,
        "rows": rows,
        "candidate_replay": replay,
        "negative_cases": {
            "one_sided": {
                "evidence_sufficient": one_sided.evidence_sufficient,
                "retry_required": one_sided.retry_required,
                "missing_tickers": list(one_sided.missing_tickers),
            },
            "unknown_company": {
                "applicable": unknown.applicable,
                "retry_required": unknown.retry_required,
            },
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
