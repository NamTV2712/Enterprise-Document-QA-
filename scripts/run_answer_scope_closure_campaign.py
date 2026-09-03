"""Run the single terminal Answer Scope Closure v1 campaign.

This campaign performs the provider-free contract, both sentinel replicates,
reproducibility, conditional N=30 admission, and guarded promotion. A
semantic NO-GO is terminal for this improvement area; it never creates a new
answer variant.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts import run_answer_scope_campaign as base
from src.evaluation.revenue_intent_contract import (
    REVENUE_INTENT_CONTRACT_FINGERPRINT,
)


ROOT = Path(__file__).resolve().parents[1]


def _configure_closure() -> None:
    from scripts.run_answer_scope_v19_campaign import _configure_v19

    _configure_v19()
    campaign_dir = ROOT / "data/diagnostics/answer_scope_closure_v1_campaign"
    base.CAMPAIGN_ID = "answer_scope_closure_v1"
    base.CAMPAIGN_DIR = campaign_dir
    base.STATE_PATH = campaign_dir / "state.json"
    base.CONTINUE_AFTER_SENTINEL_NO_GO = True
    base.SENTINEL_MODULE = "scripts.run_answer_scope_closure_sentinel"
    base.OFFLINE_MODULE = "scripts.diagnostics.answer_scope_closure_offline"
    base.REPRO_MODULE = (
        "scripts.diagnostics.answer_scope_closure_reproducibility"
    )
    base.SENTINEL_AUDIT_VERSION = ""
    base.REPRO_AUDIT_VERSION = ""
    base.OFFLINE_AUDIT_VERSION = ""
    base.OFFLINE_REPORT = ROOT / "data/diagnostics/answer_scope_closure_v1_offline.json"
    base.REPRO_REPORT = ROOT / "data/diagnostics/answer_scope_closure_v1_reproducibility.json"
    base.SENTINEL_R1 = ROOT / "data/eval_artifacts/answer_scope_closure_v1_sentinel_summary_r1.json"
    base.SENTINEL_R2 = ROOT / "data/eval_artifacts/answer_scope_closure_v1_sentinel_summary_r2.json"
    base.SENTINEL_GEN_R1 = ROOT / "data/eval_artifacts/answer_scope_closure_v1_sentinel_gen_r1.jsonl"
    base.SENTINEL_JUDGE_R1 = ROOT / "data/eval_artifacts/answer_scope_closure_v1_sentinel_judge_r1.jsonl"
    base.SENTINEL_GEN_R2 = ROOT / "data/eval_artifacts/answer_scope_closure_v1_sentinel_gen_r2.jsonl"
    base.SENTINEL_JUDGE_R2 = ROOT / "data/eval_artifacts/answer_scope_closure_v1_sentinel_judge_r2.jsonl"
    base.N30_RESULT = ROOT / "data/eval_artifacts/phase2_results_answer_scope_closure_v1_candidate.json"
    base.N30_GEN = ROOT / "data/eval_artifacts/answer_scope_closure_v1_phase2_gen.jsonl"
    base.N30_JUDGE = ROOT / "data/eval_artifacts/answer_scope_closure_v1_phase2_judge.jsonl"
    base.ADMISSION_REPORT = ROOT / "data/diagnostics/phase2_admission_answer_scope_closure_v1.json"
    base.SOURCE_PATHS = (
        ROOT / "src/generation/prompt_contracts.py",
        ROOT / "src/generation/enumeration_completeness.py",
        ROOT / "src/generation/answer_completion.py",
        ROOT / "src/generation/risk_answer_shape.py",
        ROOT / "src/generation/evidence_fact_renderer.py",
        ROOT / "src/generation/enumeration_answer_renderer.py",
        ROOT / "src/evaluation/revenue_intent_contract.py",
        ROOT / "src/evaluation/phase2_runtime.py",
        ROOT / "scripts/run_answer_stability_sentinel.py",
        ROOT / "scripts/run_answer_scope_sentinel.py",
        ROOT / "scripts/run_answer_scope_closure_sentinel.py",
        ROOT / "scripts/diagnostics/answer_scope_closure_offline.py",
        ROOT / "scripts/diagnostics/answer_scope_closure_reproducibility.py",
        ROOT / "scripts/run_evaluation_phase2.py",
        ROOT / "scripts/run_answer_scope_campaign.py",
        ROOT / "scripts/run_answer_scope_closure_campaign.py",
    )


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_closure(
    state: dict[str, Any],
    *,
    status: str,
    reason: str,
    promotion: dict[str, Any] | None = None,
) -> None:
    closure = {
        "schema_version": 1,
        "campaign": base.CAMPAIGN_ID,
        "status": status,
        "reason": reason,
        "official_sha256": base._sha256(base.OFFICIAL_RESULT),
        "revenue_intent_contract_fingerprint": REVENUE_INTENT_CONTRACT_FINGERPRINT,
        "stages": state.get("stages", {}),
    }
    if promotion is not None:
        closure["promotion"] = promotion
    path = ROOT / "data/diagnostics/answer_scope_closure_v1.json"
    base._atomic_write(path, closure)
    state["status"] = status
    state["closure"] = closure
    base._mark(state, "campaign", status, closure_path=str(path))


def _promotion_command(*, apply: bool) -> list[str]:
    candidate = _load(base.N30_RESULT)
    official = _load(base.OFFICIAL_RESULT)
    binding = candidate.get("binding")
    candidate_strategy = candidate.get("context_strategy")
    official_strategy = official.get("context_strategy")
    if not all(
        isinstance(value, str) and value
        for value in (binding, candidate_strategy, official_strategy)
    ):
        raise RuntimeError("promotion inputs are missing binding or strategy")
    command = [
        sys.executable,
        "-m",
        "scripts.promote_phase2_result",
        "--candidate",
        str(base.N30_RESULT.relative_to(ROOT)),
        "--admission",
        str(base.ADMISSION_REPORT.relative_to(ROOT)),
        "--official",
        str(base.OFFICIAL_RESULT.relative_to(ROOT)),
        "--archive-dir",
        "data/eval_artifacts/archive",
        "--receipt",
        "data/diagnostics/answer_scope_closure_v1_promotion.json",
        "--expected-candidate-sha256",
        base._sha256(base.N30_RESULT),
        "--expected-admission-sha256",
        base._sha256(base.ADMISSION_REPORT),
        "--expected-official-sha256",
        base._sha256(base.OFFICIAL_RESULT),
        "--expected-binding",
        binding,
        "--expected-candidate-strategy",
        candidate_strategy,
        "--expected-official-strategy",
        official_strategy,
    ]
    if apply:
        command.append("--apply")
    return command


def _promote_and_close(state: dict[str, Any]) -> int:
    campaign_dir = base.CAMPAIGN_DIR
    campaign_dir.mkdir(parents=True, exist_ok=True)
    dry_log = campaign_dir / "promotion_dry_run.log"
    apply_log = campaign_dir / "promotion_apply.log"
    for apply, log_path in ((False, dry_log), (True, apply_log)):
        command = _promotion_command(apply=apply)
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        log_path.write_text(
            result.stdout + result.stderr,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"promotion {'apply' if apply else 'dry-run'} failed; see {log_path}"
            )
    official = _load(base.OFFICIAL_RESULT)
    if official.get("official") is not True:
        raise RuntimeError("promoted official self-check failed")
    receipt_path = ROOT / "data/diagnostics/answer_scope_closure_v1_promotion.json"
    receipt = _load(receipt_path)
    _write_closure(
        state,
        status="CLOSED_GO_PROMOTED",
        reason="candidate passed both sentinels, reproducibility, N=30 admission, and guarded promotion",
        promotion=receipt,
    )
    print("[answer-scope-closure] CLOSED_GO_PROMOTED")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args(argv)
    _configure_closure()

    if not args.restart:
        state = base._load_or_create_state()
        if state.get("status") == "CLOSED_GO_PROMOTED":
            print("[answer-scope-closure] campaign is already CLOSED_GO_PROMOTED")
            return 0
        if state.get("status") == "CLOSED_NO_GO":
            print("[answer-scope-closure] campaign is already CLOSED_NO_GO")
            return 2
        if state.get("status") == "READY_TO_PROMOTE":
            try:
                return _promote_and_close(state)
            except Exception as error:
                print(f"[answer-scope-closure] promotion failed: {error}")
                return 1

    base_args = ["--restart"] if args.restart else []
    return_code = base.main(base_args)
    state = base._load_or_create_state()
    if return_code == 0:
        try:
            return _promote_and_close(state)
        except Exception as error:
            state["status"] = "FAILED"
            base._mark(state, "campaign", "FAILED", error=str(error))
            print(f"[answer-scope-closure] promotion failed: {error}")
            return 1
    if return_code == 75:
        return return_code
    if state.get("status") == "NO_GO":
        _write_closure(
            state,
            status="CLOSED_NO_GO",
            reason="a registered semantic or admission gate failed; protected official retained",
        )
        print("[answer-scope-closure] CLOSED_NO_GO; protected official retained")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
