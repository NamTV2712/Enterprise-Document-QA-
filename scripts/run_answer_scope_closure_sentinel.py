"""Run one final Answer Scope Closure v1 sentinel replicate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import run_answer_scope_sentinel as base
from scripts.diagnostics.answer_scope_closure_reproducibility import (
    _revenue_context,
)
from src.evaluation.revenue_intent_contract import (
    MICROSOFT_MAIN_REVENUE_QUESTION,
    REVENUE_INTENT_CONTRACT_FINGERPRINT,
    audit_revenue_intent_scope,
)


def run(
    *,
    replicate_id: str,
    artifact_path: Path = base.base.ARTIFACT_PATH,
    gen_checkpoint: Path | None = None,
    judge_checkpoint: Path | None = None,
    output: Path | None = None,
    fresh: bool = False,
    max_gen_retries: int = 0,
    max_judge_retries: int = 0,
) -> dict[str, Any]:
    report = base.run(
        replicate_id=replicate_id,
        artifact_path=artifact_path,
        gen_checkpoint=gen_checkpoint,
        judge_checkpoint=judge_checkpoint,
        output=output,
        fresh=fresh,
        max_gen_retries=max_gen_retries,
        max_judge_retries=max_judge_retries,
        deterministic_risk_renderer=True,
        deterministic_fact_renderer=True,
        deterministic_revenue_renderer=True,
    )
    context = _revenue_context()
    answer = next(
        (
            str(case.get("answer") or "")
            for case in report.get("cases", [])
            if case.get("question") == MICROSOFT_MAIN_REVENUE_QUESTION
        ),
    )
    revenue_scope = audit_revenue_intent_scope(
        MICROSOFT_MAIN_REVENUE_QUESTION, context, answer
    )
    report["audit"] = "answer_scope_sentinel_closure_v1"
    report["revenue_intent_contract_fingerprint"] = (
        REVENUE_INTENT_CONTRACT_FINGERPRINT
    )
    report["revenue_intent_scope"] = revenue_scope
    report.setdefault("gates", {})["revenue_intent_scope_contract"] = (
        revenue_scope.get("passed") is True
    )
    report["passed"] = all(report.get("gates", {}).values())
    if output is None:
        raise RuntimeError("Sentinel output path is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replicate-id", required=True)
    parser.add_argument("--artifact", type=Path, default=base.base.ARTIFACT_PATH)
    parser.add_argument("--gen-checkpoint", type=Path)
    parser.add_argument("--judge-checkpoint", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
    # Accepted for compatibility with the shared campaign runner; this
    # closure wrapper always enables all three deterministic renderers.
    parser.add_argument("--deterministic-risk-renderer", action="store_true")
    parser.add_argument("--deterministic-fact-renderer", action="store_true")
    parser.add_argument("--deterministic-revenue-renderer", action="store_true")
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
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
