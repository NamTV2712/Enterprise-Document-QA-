"""Run the complete Answer Scope v13 campaign with resumable checkpoints.

The campaign never overwrites the protected official result until the clean
candidate passes the provider-free admission audit. Provider quota pauses leave
all compatible checkpoints in place and can be resumed with the same command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_ID = "answer_scope_v13"
DETERMINISTIC_RISK_RENDERER = False
DETERMINISTIC_FACT_RENDERER = False
DETERMINISTIC_REVENUE_RENDERER = False
# Final closure campaigns may complete both independent sentinel reports even
# when the first is a legitimate semantic NO-GO. Historical campaigns keep
# the original fail-fast behavior.
CONTINUE_AFTER_SENTINEL_NO_GO = False
SENTINEL_MODULE = "scripts.run_answer_scope_sentinel"
OFFLINE_MODULE = "scripts.diagnostics.answer_scope_offline"
REPRO_MODULE = "scripts.diagnostics.answer_scope_reproducibility"
SENTINEL_AUDIT_VERSION = "v13"
REPRO_AUDIT_VERSION = ""
OFFLINE_AUDIT_VERSION = ""
CAMPAIGN_DIR = ROOT / "data/diagnostics/answer_scope_v13_campaign"
STATE_PATH = CAMPAIGN_DIR / "state.json"
OFFLINE_REPORT = ROOT / "data/diagnostics/answer_scope_v13_offline.json"
REPRO_REPORT = ROOT / "data/diagnostics/answer_scope_v13_reproducibility.json"
SENTINEL_R1 = ROOT / "data/eval_artifacts/answer_scope_v13_sentinel_summary_r1.json"
SENTINEL_R2 = ROOT / "data/eval_artifacts/answer_scope_v13_sentinel_summary_r2.json"
SENTINEL_GEN_R1 = ROOT / "data/eval_artifacts/answer_scope_v13_sentinel_gen_r1.jsonl"
SENTINEL_JUDGE_R1 = ROOT / "data/eval_artifacts/answer_scope_v13_sentinel_judge_r1.jsonl"
SENTINEL_GEN_R2 = ROOT / "data/eval_artifacts/answer_scope_v13_sentinel_gen_r2.jsonl"
SENTINEL_JUDGE_R2 = ROOT / "data/eval_artifacts/answer_scope_v13_sentinel_judge_r2.jsonl"
N30_RESULT = ROOT / "data/eval_artifacts/phase2_results_answer_scope_v13_candidate.json"
N30_GEN = ROOT / "data/eval_artifacts/answer_scope_v13_phase2_gen.jsonl"
N30_JUDGE = ROOT / "data/eval_artifacts/answer_scope_v13_phase2_judge.jsonl"
ADMISSION_REPORT = ROOT / "data/diagnostics/phase2_admission_answer_scope_v13.json"
OFFICIAL_RESULT = ROOT / "data/eval_artifacts/phase2_results_packed_selective_v2.json"
PHASE1_ARTIFACT = ROOT / "data/eval_artifacts/phase1_priority2.json"
STRATEGY = "selective_packed_v6_fact_candidate"
SOURCE_PATHS = (
    ROOT / "src/generation/prompt_contracts.py",
    ROOT / "src/generation/enumeration_completeness.py",
    ROOT / "src/generation/answer_completion.py",
    ROOT / "src/generation/risk_answer_shape.py",
    ROOT / "scripts/run_answer_scope_sentinel.py",
    ROOT / "scripts/diagnostics/answer_scope_offline.py",
    ROOT / "scripts/diagnostics/answer_scope_reproducibility.py",
    ROOT / "scripts/run_answer_scope_campaign.py",
)


class CampaignNoGo(RuntimeError):
    """A complete stage produced a legitimate failed quality gate."""


class CampaignWaitingQuota(RuntimeError):
    """A provider stage stopped before completion because quota was exhausted."""


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _source_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in SOURCE_PATHS:
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _new_state(manifest: dict[str, Any]) -> dict[str, Any]:
    state = {
        "schema_version": 1,
        "campaign": CAMPAIGN_ID,
        "status": "RUNNING",
        "current_stage": None,
        "manifest": manifest,
        "stages": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(STATE_PATH, state)
    return state


def _load_or_create_state(*, restart: bool = False) -> dict[str, Any]:
    manifest = {
        "campaign": CAMPAIGN_ID,
        "git_head": _git_head(),
        "python": sys.executable,
        "phase1_artifact_sha256": _sha256(PHASE1_ARTIFACT),
        "official_sha256": _sha256(OFFICIAL_RESULT),
        "strategy": STRATEGY,
        "source_fingerprint": _source_fingerprint(),
    }
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if restart:
            backup = STATE_PATH.with_name("state.previous.json")
            shutil.copy2(STATE_PATH, backup)
            return _new_state(manifest)
        if state.get("manifest") != manifest:
            raise RuntimeError(
                "Answer Scope campaign manifest drifted; start a new campaign "
                "instead of resuming incompatible checkpoints."
            )
        return state
    return _new_state(manifest)


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write(STATE_PATH, state)


def _mark(state: dict[str, Any], stage: str, status: str, **details: Any) -> None:
    state["current_stage"] = stage
    state["stages"][stage] = {"status": status, **details}
    _save_state(state)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _provider_report_status(path: Path) -> str | None:
    report = _load_json(path)
    if report is None:
        return None
    if report.get("passed") is True:
        return "PASSED"
    if report.get("admission") is False:
        return "NO_GO"
    if report.get("provider_complete") is True:
        # Sentinel reports expose an explicit ``passed`` field; the Phase 2
        # candidate summary exposes only ``provider_complete`` and is healthy
        # when it has no stopped reason.
        return "NO_GO" if "passed" in report else "PASSED"
    if str(report.get("audit") or "").startswith(
        "answer_scope_reproducibility_v"
    ):
        return "NO_GO"
    stopped = str(report.get("stopped_reason") or "").casefold()
    if "quota" in stopped or "rate" in stopped or any(
        "quota" in str(case.get("error") or "").casefold()
        for case in report.get("cases", [])
        if isinstance(case, dict)
    ):
        return "WAITING_QUOTA"
    return None


def _run_command(state: dict[str, Any], stage: str, command: list[str], report: Path | None = None) -> None:
    print(f"[answer-scope] {stage}: running")
    _mark(state, stage, "RUNNING", command=command)
    log_path = CAMPAIGN_DIR / f"{stage}.log"
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    if result.returncode == 0:
        _mark(state, stage, "PASSED", returncode=0, log=str(log_path))
        print(f"[answer-scope] {stage}: passed")
        return
    report_status = _provider_report_status(report) if report else None
    if report_status == "WAITING_QUOTA":
        state["status"] = "WAITING_QUOTA"
        _mark(
            state,
            stage,
            "WAITING_QUOTA",
            returncode=result.returncode,
            log=str(log_path),
        )
        raise CampaignWaitingQuota(f"{stage} paused for provider quota")
    if report_status == "NO_GO":
        state["status"] = "NO_GO"
        _mark(state, stage, "NO_GO", returncode=result.returncode, log=str(log_path))
        raise CampaignNoGo(f"{stage} failed its registered quality gates")
    state["status"] = "FAILED"
    _mark(state, stage, "FAILED", returncode=result.returncode, log=str(log_path))
    raise RuntimeError(f"{stage} failed with exit code {result.returncode}")


def _stage_done(state: dict[str, Any], stage: str) -> bool:
    return state.get("stages", {}).get(stage, {}).get("status") == "PASSED"


def _run_once(state: dict[str, Any]) -> None:
    if not _stage_done(state, "offline"):
        offline_command = [
            sys.executable,
            "-m",
            OFFLINE_MODULE,
            "--output",
            str(OFFLINE_REPORT.relative_to(ROOT)),
        ]
        if OFFLINE_AUDIT_VERSION:
            offline_command.extend(["--audit-version", OFFLINE_AUDIT_VERSION])
        _run_command(
            state,
            "offline",
            offline_command,
        )
    if not _stage_done(state, "tests"):
        _run_command(state, "tests", [sys.executable, "-m", "pytest", "-q"])

    sentinel_specs = (
        (
            "sentinel_r1",
            "r1",
            SENTINEL_GEN_R1,
            SENTINEL_JUDGE_R1,
            SENTINEL_R1,
        ),
        (
            "sentinel_r2",
            "r2",
            SENTINEL_GEN_R2,
            SENTINEL_JUDGE_R2,
            SENTINEL_R2,
        ),
    )
    for stage, replicate_id, gen, judge, summary in sentinel_specs:
        if _stage_done(state, stage):
            continue
        existing_status = _provider_report_status(summary)
        if existing_status == "PASSED":
            _mark(state, stage, "PASSED", reused=True)
            continue
        if existing_status == "NO_GO":
            state["status"] = "NO_GO"
            _mark(state, stage, "NO_GO", reused=True)
            if CONTINUE_AFTER_SENTINEL_NO_GO:
                continue
            raise CampaignNoGo(f"{stage} already contains a complete failed report")
        sentinel_command = [
            sys.executable,
            "-m",
            SENTINEL_MODULE,
            "--replicate-id",
            replicate_id,
            "--gen-checkpoint",
            str(gen.relative_to(ROOT)),
            "--judge-checkpoint",
            str(judge.relative_to(ROOT)),
            "--output",
            str(summary.relative_to(ROOT)),
            "--max-gen-retries",
            "0",
            "--max-judge-retries",
            "0",
        ]
        if DETERMINISTIC_RISK_RENDERER:
            sentinel_command.append("--deterministic-risk-renderer")
        if DETERMINISTIC_FACT_RENDERER:
            sentinel_command.append("--deterministic-fact-renderer")
        if DETERMINISTIC_REVENUE_RENDERER:
            sentinel_command.append("--deterministic-revenue-renderer")
        if SENTINEL_AUDIT_VERSION:
            sentinel_command.extend(["--audit-version", SENTINEL_AUDIT_VERSION])
        try:
            _run_command(
                state,
                stage,
                sentinel_command,
                report=summary,
            )
        except CampaignNoGo:
            if not CONTINUE_AFTER_SENTINEL_NO_GO:
                raise

    failed_sentinels = [
        stage
        for stage in ("sentinel_r1", "sentinel_r2")
        if state.get("stages", {}).get(stage, {}).get("status") == "NO_GO"
    ]
    if failed_sentinels:
        state["status"] = "NO_GO"
        _mark(
            state,
            "campaign",
            "NO_GO",
            failed_sentinel_stages=failed_sentinels,
        )
        raise CampaignNoGo(
            "sentinel quality gates failed: " + ", ".join(failed_sentinels)
        )

    if not _stage_done(state, "reproducibility"):
        repro_command = [
            sys.executable,
            "-m",
            REPRO_MODULE,
            "--r1",
            str(SENTINEL_R1.relative_to(ROOT)),
            "--r2",
            str(SENTINEL_R2.relative_to(ROOT)),
            "--output",
            str(REPRO_REPORT.relative_to(ROOT)),
        ]
        if REPRO_AUDIT_VERSION:
            repro_command.extend(["--audit-version", REPRO_AUDIT_VERSION])
        _run_command(
            state,
            "reproducibility",
            repro_command,
            report=REPRO_REPORT,
        )

    if not _stage_done(state, "n30"):
        n30_command = [
            sys.executable,
            "-m",
            "scripts.run_evaluation_phase2",
            "--priority",
            "2",
            "--artifact",
            str(PHASE1_ARTIFACT.relative_to(ROOT)),
            "--context-strategy",
            STRATEGY,
            "--reproducibility-report",
            str(REPRO_REPORT.relative_to(ROOT)),
            "--gen-checkpoint",
            str(N30_GEN.relative_to(ROOT)),
            "--judge-checkpoint",
            str(N30_JUDGE.relative_to(ROOT)),
            "--output",
            str(N30_RESULT.relative_to(ROOT)),
            "--max-gen-retries",
            "0",
            "--max-judge-retries",
            "0",
        ]
        if DETERMINISTIC_RISK_RENDERER:
            n30_command.append("--deterministic-risk-renderer")
        if DETERMINISTIC_FACT_RENDERER:
            n30_command.append("--deterministic-fact-renderer")
        if DETERMINISTIC_REVENUE_RENDERER:
            n30_command.append("--deterministic-revenue-renderer")
        _run_command(
            state,
            "n30",
            n30_command,
            report=N30_RESULT,
        )

    if not _stage_done(state, "admission"):
        _run_command(
            state,
            "admission",
            [
                sys.executable,
                "-m",
                "scripts.diagnostics.phase2_admission",
                "--candidate",
                str(N30_RESULT.relative_to(ROOT)),
                "--baseline",
                str(OFFICIAL_RESULT.relative_to(ROOT)),
                "--artifact",
                str(PHASE1_ARTIFACT.relative_to(ROOT)),
                "--output",
                str(ADMISSION_REPORT.relative_to(ROOT)),
            ],
            report=ADMISSION_REPORT,
        )
        admission = _load_json(ADMISSION_REPORT) or {}
        if admission.get("passed") is not True:
            state["status"] = "NO_GO"
            _mark(state, "admission", "NO_GO", gates=admission.get("gates"))
            raise CampaignNoGo("N=30 admission failed")

    state["status"] = "READY_TO_PROMOTE"
    _mark(state, "campaign", "READY_TO_PROMOTE")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resume", action="store_true", help="Resume the locked campaign state")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Archive a failed infrastructure state and start a fresh campaign",
    )
    args = parser.parse_args(argv)
    state = _load_or_create_state(restart=args.restart)
    if state.get("status") == "FAILED" or (
        state.get("status") == "NO_GO" and not CONTINUE_AFTER_SENTINEL_NO_GO
    ):
        print(f"[answer-scope] campaign is terminal: {state['status']}")
        return 2
    try:
        _run_once(state)
    except CampaignWaitingQuota as error:
        print(f"[answer-scope] {error}; rerun the same command after quota recovery")
        return 75
    except CampaignNoGo as error:
        print(f"[answer-scope] NO-GO: {error}")
        return 2
    print("[answer-scope] all evaluation gates passed; candidate is ready for guarded promotion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
