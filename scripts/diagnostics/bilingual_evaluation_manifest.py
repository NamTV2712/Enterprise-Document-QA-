"""Register and verify the provider-backed bilingual evaluation protocol.

The manifest is intentionally provider-free.  It freezes the five intents,
their English/Vietnamese questions, the canonical evidence artifact, and the
60-request accounting before any provider call is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Support both ``python -m ...`` and the documented direct script invocation.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.run_answerability_stability_sentinel import (
    ARTIFACT_PATH,
    EXPECTED_ARTIFACT_FINGERPRINT,
    EXPECTED_REFERENCE_SHA256,
    SENTINEL_QUESTIONS,
)


CAMPAIGN_ID = "bilingual_evaluation_v1_window_01"
CAMPAIGN_VERSION = "bilingual-evaluation-v1-candidate-1"
MAX_REQUESTS = 60
CALIBRATION_REQUESTS = 12
SENTINEL_REQUESTS = 40
RESERVED_RETRY_BUDGET = 8
LANGUAGES = ("en", "vi")

# These are source questions from the frozen artifact.  The translations are
# authored fixtures, not output from the normalizer or the provider.
BILINGUAL_CASES: tuple[dict[str, str], ...] = (
    {
        "intent": "dependency",
        "source_question": SENTINEL_QUESTIONS[0],
        "en": "Which company depends more on cloud/subscription revenue, Microsoft or Apple?",
        "vi": "Microsoft hay Apple phụ thuộc nhiều hơn vào doanh thu cloud hoặc subscription?",
    },
    {
        "intent": "major-risk",
        "source_question": SENTINEL_QUESTIONS[1],
        "en": "What are all the major risk factors Microsoft discloses?",
        "vi": "Microsoft công bố tất cả những nhóm rủi ro chính nào?",
    },
    {
        "intent": "growth-comparison",
        "source_question": SENTINEL_QUESTIONS[2],
        "en": "How does Amazon's AWS segment compare with Microsoft's cloud business in terms of growth?",
        "vi": "Tốc độ tăng trưởng của AWS của Amazon so với mảng cloud của Microsoft như thế nào?",
    },
    {
        "intent": "period-revenue",
        "source_question": SENTINEL_QUESTIONS[3],
        "en": "Which company, Apple or Amazon, had higher total revenue in fiscal year 2024?",
        "vi": "Trong năm tài chính 2024, Apple hay Amazon có tổng doanh thu cao hơn?",
    },
    {
        "intent": "international-risk",
        "source_question": SENTINEL_QUESTIONS[4],
        "en": "Compare Apple's and Amazon's approach to international operations risk.",
        "vi": "Hãy so sánh cách Apple và Amazon đề cập đến rủi ro hoạt động quốc tế.",
    },
)


def case_records() -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "case_id": f"{case['intent']}-{language}",
            "intent": case["intent"],
            "source_question": case["source_question"],
            "language": language,
            "question": case[language],
        }
        for case in BILINGUAL_CASES
        for language in LANGUAGES
    )


def campaign_output_paths(campaign_id: str) -> tuple[Path, ...]:
    prefix = Path("data/diagnostics") / campaign_id
    return (
        prefix.with_name(prefix.name + "_manifest.json"),
        prefix.with_name(prefix.name + "_campaign_ledger.jsonl"),
        prefix.with_name(prefix.name + "_calibration.json"),
        prefix.with_name(prefix.name + "_r1_generation.jsonl"),
        prefix.with_name(prefix.name + "_r1_judge.jsonl"),
        prefix.with_name(prefix.name + "_r2_generation.jsonl"),
        prefix.with_name(prefix.name + "_r2_judge.jsonl"),
        prefix.with_name(prefix.name + "_status.json"),
    )


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _artifact_identity(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    embedded = payload.get("artifact_fingerprint") or (payload.get("fingerprints") or {}).get("artifact")
    return {
        "path": str(path),
        "sha256": _sha256_file(path),
        "embedded_fingerprint": embedded,
        "expected_embedded_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "matches_expected_embedded_fingerprint": embedded == EXPECTED_ARTIFACT_FINGERPRINT,
    }


def build_manifest(
    artifact_path: Path = ARTIFACT_PATH,
    campaign_id: str = CAMPAIGN_ID,
) -> dict[str, Any]:
    outputs = campaign_output_paths(campaign_id)
    resolved = [path.resolve() for path in outputs]
    errors: list[str] = []
    if len(set(resolved)) != len(resolved):
        errors.append("registered output paths are not distinct")
    artifact = _artifact_identity(artifact_path)
    if not artifact["matches_expected_embedded_fingerprint"]:
        errors.append("canonical artifact fingerprint does not match the registered artifact")
    cases = list(case_records())
    binding_payload = {
        "version": CAMPAIGN_VERSION,
        "cases": cases,
        "languages": LANGUAGES,
        "artifact_sha256": artifact["sha256"],
    }
    profile_fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(binding_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
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
        "profile_fingerprint": profile_fingerprint,
        "cases": cases,
        "provider_protocol": {
            "max_requests": MAX_REQUESTS,
            "calibration_requests": CALIBRATION_REQUESTS,
            "sentinel_requests": SENTINEL_REQUESTS,
            "reserved_retry_budget": RESERVED_RETRY_BUDGET,
            "sdk_retries": 0,
            "explicit_retries_per_logical_operation": 1,
            "unknown_outcome_policy": "INCOMPLETE; start a new campaign after provider authorization",
        },
        "registered_outputs": [str(path) for path in outputs],
        "passed": not errors and len(cases) == 10,
        "errors": errors,
    }


def verify_manifest(path: Path, artifact_path: Path = ARTIFACT_PATH, campaign_id: str = CAMPAIGN_ID) -> tuple[str, ...]:
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return (f"cannot read manifest: {error}",)
    current = build_manifest(artifact_path, campaign_id)
    errors = list(current["errors"])
    for key in ("campaign_id", "campaign_version", "profile_fingerprint", "cases", "provider_protocol", "registered_outputs"):
        if stored.get(key) != current.get(key):
            errors.append(f"manifest field changed: {key}")
    if stored.get("canonical_artifact", {}).get("sha256") != current["canonical_artifact"]["sha256"]:
        errors.append("canonical artifact hash changed")
    return tuple(dict.fromkeys(errors))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-id", default=CAMPAIGN_ID)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    output = args.output or Path(f"data/diagnostics/{args.campaign_id}_manifest.json")
    if args.check:
        errors = verify_manifest(output, args.artifact, args.campaign_id)
        print(json.dumps({"path": str(output), "errors": list(errors), "passed": not errors}, indent=2))
        return 0 if not errors else 1
    manifest = build_manifest(args.artifact, args.campaign_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
