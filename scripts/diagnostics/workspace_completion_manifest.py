"""Write a source-bound, provider-free workspace completion manifest.

The output belongs in ``data/diagnostics/``.  It records the clean source
commit, the staged-diff identity of that commit, lockfile hashes, production
frontend asset sizes, and the already measured Library p95 values.  It never
reads secrets or makes a network/provider request.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> str:
    completed = subprocess.run(
        list(args),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _asset_manifest() -> list[dict[str, object]]:
    asset_dir = REPO_ROOT / "frontend" / "dist" / "assets"
    if not asset_dir.is_dir():
        raise FileNotFoundError(f"production assets are missing: {asset_dir}")
    assets: list[dict[str, object]] = []
    for path in sorted(item for item in asset_dir.rglob("*") if item.is_file()):
        raw = path.read_bytes()
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        assets.append(
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "bytes": len(raw),
                "gzip_bytes": len(compressed),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return assets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--library-p95-chromium", type=float, required=True)
    parser.add_argument("--library-p95-firefox", type=float, required=True)
    parser.add_argument("--frontend-tests", required=True)
    parser.add_argument("--browser-tests", required=True)
    parser.add_argument("--backend-tests", required=True)
    args = parser.parse_args()

    commit = _run("git", "rev-parse", "HEAD")
    parent = _run("git", "rev-parse", "HEAD^")
    dirty = _run("git", "status", "--porcelain")
    diff_check = subprocess.run(
        ["git", "diff", "--check", "HEAD^", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    lockfiles = {}
    for relative in (
        "frontend/package.json",
        "frontend/bun.lock",
        "pyproject.toml",
        "requirements.txt",
    ):
        path = REPO_ROOT / relative
        if path.is_file():
            lockfiles[relative] = _sha256(path)

    assets = _asset_manifest()
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kind": "workspace_completion_manifest",
        "provider_calls": 0,
        "git": {
            "commit": commit,
            "parent_commit": parent,
            "clean_worktree": not bool(dirty),
            "dirty_paths": dirty.splitlines(),
            "commit_diff_check": diff_check.returncode == 0,
            "commit_diff_stat": _run("git", "diff", "--stat", "HEAD^", "HEAD"),
        },
        "lockfiles": lockfiles,
        "frontend_production_assets": assets,
        "performance": {
            "fixture": "100 conversations / 10,000 messages",
            "warm_samples": 100,
            "p95_ms": {
                "chromium": args.library_p95_chromium,
                "firefox": args.library_p95_firefox,
            },
            "threshold_ms": 200,
        },
        "offline_gates": {
            "frontend": args.frontend_tests,
            "browser": args.browser_tests,
            "backend": args.backend_tests,
        },
    }
    checks = {
        "clean_worktree": manifest["git"]["clean_worktree"],
        "commit_diff_check": manifest["git"]["commit_diff_check"],
        "production_assets_present": bool(assets),
        "library_p95_under_200ms": (
            args.library_p95_chromium < 200 and args.library_p95_firefox < 200
        ),
    }
    manifest["checks"] = checks
    manifest["overall"] = "PASS" if all(checks.values()) else "FAIL"

    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Workspace completion manifest: {manifest['overall']}")
    print(f"Manifest written to {output}")
    return 0 if manifest["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
