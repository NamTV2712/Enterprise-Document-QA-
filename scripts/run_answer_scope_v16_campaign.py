"""Run the resumable V16 major-risk-scope campaign."""

from __future__ import annotations

from pathlib import Path

from scripts import run_answer_scope_campaign as base
from scripts.run_answer_scope_v15_campaign import _configure_v15


ROOT = Path(__file__).resolve().parents[1]


def _configure_v16() -> None:
    _configure_v15()
    campaign_dir = ROOT / "data/diagnostics/answer_scope_v16_campaign"
    base.CAMPAIGN_ID = "answer_scope_v16"
    base.CAMPAIGN_DIR = campaign_dir
    base.STATE_PATH = campaign_dir / "state.json"
    base.SENTINEL_AUDIT_VERSION = "v16"
    base.REPRO_AUDIT_VERSION = "v16"
    base.OFFLINE_AUDIT_VERSION = "v16"
    base.OFFLINE_REPORT = ROOT / "data/diagnostics/answer_scope_v16_offline.json"
    base.REPRO_REPORT = ROOT / "data/diagnostics/answer_scope_v16_reproducibility.json"
    base.SENTINEL_R1 = ROOT / "data/eval_artifacts/answer_scope_v16_sentinel_summary_r1.json"
    base.SENTINEL_R2 = ROOT / "data/eval_artifacts/answer_scope_v16_sentinel_summary_r2.json"
    base.SENTINEL_GEN_R1 = ROOT / "data/eval_artifacts/answer_scope_v16_sentinel_gen_r1.jsonl"
    base.SENTINEL_JUDGE_R1 = ROOT / "data/eval_artifacts/answer_scope_v16_sentinel_judge_r1.jsonl"
    base.SENTINEL_GEN_R2 = ROOT / "data/eval_artifacts/answer_scope_v16_sentinel_gen_r2.jsonl"
    base.SENTINEL_JUDGE_R2 = ROOT / "data/eval_artifacts/answer_scope_v16_sentinel_judge_r2.jsonl"
    base.N30_RESULT = ROOT / "data/eval_artifacts/phase2_results_answer_scope_v16_candidate.json"
    base.N30_GEN = ROOT / "data/eval_artifacts/answer_scope_v16_phase2_gen.jsonl"
    base.N30_JUDGE = ROOT / "data/eval_artifacts/answer_scope_v16_phase2_judge.jsonl"
    base.ADMISSION_REPORT = ROOT / "data/diagnostics/phase2_admission_answer_scope_v16.json"
    base.SOURCE_PATHS = (
        ROOT / "src/generation/prompt_contracts.py",
        ROOT / "src/generation/enumeration_completeness.py",
        ROOT / "src/generation/answer_completion.py",
        ROOT / "src/generation/risk_answer_shape.py",
        ROOT / "src/evaluation/phase2_runtime.py",
        ROOT / "scripts/run_answer_stability_sentinel.py",
        ROOT / "scripts/run_answer_scope_sentinel.py",
        ROOT / "scripts/diagnostics/answer_scope_v14_offline.py",
        ROOT / "scripts/diagnostics/answer_scope_v14_reproducibility.py",
        ROOT / "scripts/run_evaluation_phase2.py",
        ROOT / "scripts/run_answer_scope_campaign.py",
        ROOT / "scripts/run_answer_scope_v14_campaign.py",
        ROOT / "scripts/run_answer_scope_v15_campaign.py",
        ROOT / "scripts/run_answer_scope_v16_campaign.py",
    )


def main() -> int:
    _configure_v16()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
