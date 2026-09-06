"""Write a non-secret receipt for a local Docker release smoke test.

The receipt is intended for ``data/diagnostics/`` and is therefore not a
source artifact. It records the commit, image identity, pinned model labels,
and provider-free readiness endpoints without making a generation request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_LABELS = (
    "org.opencontainers.image.revision",
    "ai.edqa.embedding-model",
    "ai.edqa.embedding-revision",
    "ai.edqa.reranker-model",
    "ai.edqa.reranker-revision",
)


def run_command(*args: str) -> str:
    completed = subprocess.run(
        list(args),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.load(response)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a local Docker release receipt without provider calls.")
    parser.add_argument("--image", required=True, help="Fully tagged image, for example edqa-api:<commit>.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/local_release_receipt.json"))
    parser.add_argument(
        "--preflight",
        type=Path,
        default=Path("data/diagnostics/local_release_preflight_after_wip.json"),
    )
    args = parser.parse_args()

    commit = run_command("git", "rev-parse", "HEAD")
    dirty = run_command("git", "status", "--porcelain")
    image_raw = run_command("docker", "image", "inspect", args.image)
    image = json.loads(image_raw)[0]
    labels = image.get("Config", {}).get("Labels", {}) or {}
    health = fetch_json(f"{args.base_url.rstrip('/')}/health/ready")
    tickers = fetch_json(f"{args.base_url.rstrip('/')}/supported-tickers")

    missing_labels = [key for key in REQUIRED_LABELS if not labels.get(key)]
    checks = {
        "clean_worktree": not dirty,
        "image_revision_matches_git": labels.get("org.opencontainers.image.revision") == commit,
        "health_ready": health.get("pipeline_ready") is True and health.get("status") == "ok",
        "health_revision_matches_git": health.get("build", {}).get("revision") == commit,
        "supported_tickers_nonempty": bool(tickers.get("tickers")),
        "required_image_labels_present": not missing_labels,
    }
    receipt = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kind": "local_docker_release_receipt",
        "provider_calls": 0,
        "git": {"commit": commit, "dirty": bool(dirty), "dirty_paths": dirty.splitlines()},
        "image": {
            "reference": args.image,
            "id": image.get("Id"),
            "repo_digests": image.get("RepoDigests", []),
            "size_bytes": image.get("Size"),
            "labels": {key: labels.get(key) for key in REQUIRED_LABELS},
        },
        "offline_smoke": {
            "base_url": args.base_url,
            "health_ready": health,
            "supported_tickers": tickers,
        },
        "preflight": {
            "path": str(args.preflight),
            "sha256": sha256_file(REPO_ROOT / args.preflight),
        },
        "checks": checks,
        "missing_image_labels": missing_labels,
        "overall": "PASS" if all(checks.values()) else "FAIL",
    }
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Release receipt: {receipt['overall']}")
    print(f"Receipt written to {output}")
    return 0 if receipt["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
