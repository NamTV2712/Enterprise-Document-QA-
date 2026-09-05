"""Create and verify the pre-registered Evidence Contract v3 protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from scripts.run_answerability_stability_sentinel import (
    ARTIFACT_PATH,
    EXPECTED_ARTIFACT_FINGERPRINT,
    EXPECTED_REFERENCE_SHA256,
    SENTINEL_QUESTIONS,
)
from src.evaluation.evidence_contract_v3 import (
    PROFILE_FINGERPRINT,
    RUBRIC,
)
from src.generation.comparative_answer_renderer import (
    COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT,
)
from src.generation.comparative_evidence import COMPARATIVE_EVIDENCE_V3_FINGERPRINT


CAMPAIGN_ID = "evidence_contract_v3_retry_disabled"
CAMPAIGN_VERSION = "evidence-contract-v3-candidate-2-retry-disabled"
MAX_REQUESTS = 60
DEFAULT_OUTPUT = Path("data/diagnostics/evidence_contract_v3_retry_disabled_manifest.json")
def campaign_output_paths(campaign_id: str) -> tuple[Path, ...]:
    """Return every mutable output owned by one campaign identity."""
    return (
        Path(f"data/eval_artifacts/{campaign_id}_r1.json"),
        Path(f"data/eval_artifacts/{campaign_id}_r2.json"),
        Path(f"data/eval_artifacts/{campaign_id}_r1_generation.jsonl"),
        Path(f"data/eval_artifacts/{campaign_id}_r2_generation.jsonl"),
        Path(f"data/eval_artifacts/{campaign_id}_r1_judge.jsonl"),
        Path(f"data/eval_artifacts/{campaign_id}_r2_judge.jsonl"),
        Path(f"data/diagnostics/{campaign_id}_campaign_ledger.jsonl"),
        Path(f"data/diagnostics/{campaign_id}_calibration.json"),
        Path(f"data/diagnostics/{campaign_id}_legacy_comparison.json"),
        Path(f"data/diagnostics/{campaign_id}_reproducibility.json"),
        Path(f"data/diagnostics/{campaign_id}_campaign_status.json"),
    )


NEW_OUTPUTS = campaign_output_paths(CAMPAIGN_ID)


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _artifact_identity(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    embedded = (
        payload.get("artifact_fingerprint")
        or (payload.get("fingerprints") or {}).get("artifact")
        or payload.get("artifact_sha256")
    )
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "embedded_fingerprint": embedded,
        "expected_embedded_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "matches_expected_embedded_fingerprint": embedded == EXPECTED_ARTIFACT_FINGERPRINT,
    }


def build_manifest(
    artifact_path: Path = ARTIFACT_PATH,
    campaign_id: str = CAMPAIGN_ID,
    output_paths: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    artifact = _artifact_identity(artifact_path)
    paths = output_paths or campaign_output_paths(campaign_id)
    output_values = [str(path) for path in paths]
    resolved = [path.resolve() for path in paths]
    errors: list[str] = []
    if len(set(resolved)) != len(resolved):
        errors.append("new output paths are not distinct")
    if any(path.resolve() == artifact_path.resolve() for path in paths):
        errors.append("new output path overlaps canonical artifact")
    if artifact["matches_expected_embedded_fingerprint"] is not True:
        errors.append("canonical artifact fingerprint does not match the registered artifact")
    return {
        "schema_version": 1,
        "campaign_id": campaign_id,
        "campaign_version": CAMPAIGN_VERSION if campaign_id == CAMPAIGN_ID else f"{CAMPAIGN_VERSION}:{campaign_id}",
        "git_commit": _git_commit(),
        "canonical_artifact": artifact,
        "official_result": {
            "path": "data/eval_artifacts/phase2_results_packed_selective_v2.json",
            "sha256": EXPECTED_REFERENCE_SHA256,
        },
        "questions": list(SENTINEL_QUESTIONS),
        "context_strategy": "selective_packed_v7_fact_generalization_candidate",
        "evidence_contract": {
            "profile_fingerprint": PROFILE_FINGERPRINT,
            "rubric_sha256": "sha256:" + hashlib.sha256(RUBRIC.encode()).hexdigest(),
            "evidence_fingerprint": COMPARATIVE_EVIDENCE_V3_FINGERPRINT,
            "renderer_fingerprint": COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT,
        },
        "provider_protocol": {
            "max_requests": MAX_REQUESTS,
            "retry_policy": "zero SDK retries; at most one explicit transport retry per logical operation",
            "calibration_requests": 12,
            "sentinel_requests": 24,
            "legacy_comparison_requests": 12,
            "reserved_retry_budget": 12,
            "run_ids": (
                ["evidence-contract-v3-r1", "evidence-contract-v3-r2"]
                if campaign_id == CAMPAIGN_ID
                else [f"{campaign_id}-r1", f"{campaign_id}-r2"]
            ),
        },
        "pre_registered_gates": {
            "minimum_replicates": 2,
            "per_case_faithfulness": 1.0,
            "per_case_answer_relevancy": 1.0,
            "dependency_answer_relevancy": 1.0,
            "microsoft_risk_answer_relevancy_floor": 0.95,
            "aggregate_answer_relevancy_floor": 0.975,
            "aggregate_context_precision_floor": 0.67,
            "best_of_selection_forbidden": True,
        },
        "registered_outputs": output_values,
        "errors": errors,
        "passed": not errors,
    }


def verify_manifest(
    path: Path,
    artifact_path: Path = ARTIFACT_PATH,
    campaign_id: str = CAMPAIGN_ID,
    output_paths: tuple[Path, ...] | None = None,
) -> tuple[str, ...]:
    errors: list[str] = []
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return (f"cannot read manifest: {error}",)
    current = build_manifest(artifact_path, campaign_id, output_paths)
    for key in ("campaign_id", "campaign_version", "questions", "context_strategy",
                "evidence_contract", "provider_protocol", "registered_outputs"):
        if stored.get(key) != current.get(key):
            errors.append(f"manifest field changed: {key}")
    if stored.get("canonical_artifact", {}).get("sha256") != current["canonical_artifact"]["sha256"]:
        errors.append("canonical artifact hash changed")
    errors.extend(str(item) for item in current.get("errors", []))
    return tuple(dict.fromkeys(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--campaign-id", default=CAMPAIGN_ID)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        errors = verify_manifest(
            args.output,
            args.artifact,
            args.campaign_id,
            campaign_output_paths(args.campaign_id),
        )
        print(json.dumps({"path": str(args.output), "errors": list(errors), "passed": not errors}, indent=2))
        return 0 if not errors else 1
    manifest = build_manifest(
        args.artifact,
        args.campaign_id,
        campaign_output_paths(args.campaign_id),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
