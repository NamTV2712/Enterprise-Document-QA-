"""Read-only release preflight for the local Docker release.

Reports PASS / FAIL / BLOCKED / WARN per check and never prints secrets:
only configuration variable names and non-secret values (model ids,
revisions, paths). A failing check never triggers repair work — the script
reports exactly what needs attention and exits.

Exit codes: 0 when nothing FAILED (BLOCKED items are informational for the
Docker runtime smoke), 1 when at least one check FAILED.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

STATUS_ORDER = {"PASS": 0, "WARN": 1, "BLOCKED": 2, "FAIL": 3}


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | WARN | BLOCKED | FAIL
    detail: str
    data: dict = field(default_factory=dict)


def _run_docker_info() -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"docker CLI unavailable or timed out: {error}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        return False, detail[0] if detail else "docker daemon not reachable"
    return True, completed.stdout.strip()


def check_docker_daemon() -> CheckResult:
    running, detail = _run_docker_info()
    if running:
        return CheckResult("docker_daemon", "PASS", f"Docker daemon reachable (server {detail}).")
    return CheckResult(
        "docker_daemon",
        "BLOCKED",
        f"Docker daemon is not running ({detail}). Runtime smoke will be BLOCKED until Docker Desktop is started.",
        {"docker_server_version": None},
    )


def check_host_resources() -> CheckResult:
    import platform

    arch = platform.machine()
    _total, _used, free_bytes = shutil.disk_usage(REPO_ROOT)
    free_gib = free_bytes / (1024**3)
    if free_gib < 6:
        return CheckResult(
            "host_resources",
            "FAIL",
            f"Only {free_gib:.1f} GiB free at {REPO_ROOT}; the Docker build needs roughly 6 GiB for CPU wheels and models.",
            {"arch": arch, "free_gib": round(free_gib, 1)},
        )
    return CheckResult(
        "host_resources",
        "PASS",
        f"Architecture {arch}; {free_gib:.1f} GiB free at {REPO_ROOT} (build needs ~6 GiB).",
        {"arch": arch, "free_gib": round(free_gib, 1)},
    )


def check_git_state() -> CheckResult:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT, timeout=15
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=REPO_ROOT, timeout=15
        ).stdout
    except (OSError, subprocess.TimeoutExpired) as error:
        return CheckResult("git_state", "FAIL", f"git commands failed: {error}")
    dirty = [line for line in status.splitlines() if line.strip()]
    if dirty:
        names = ", ".join(line.split()[-1] for line in dirty[:5])
        return CheckResult(
            "git_state",
            "WARN",
            f"Worktree is dirty ({len(dirty)} changed paths: {names}); release receipts should pin a clean commit.",
            {"commit": commit, "dirty_count": len(dirty)},
        )
    return CheckResult("git_state", "PASS", f"Clean worktree at commit {commit[:12]}.", {"commit": commit})


def check_index_and_config_alignment(env: dict[str, str]) -> CheckResult:
    manifest_path = REPO_ROOT / env.get("QDRANT_INDEX_MANIFEST_PATH", "data/processed/qdrant_index_manifest.json")
    if not manifest_path.is_file():
        return CheckResult(
            "index_and_config",
            "FAIL",
            f"Index manifest is missing at {manifest_path}; local startup cannot verify index trust.",
        )
    try:
        import json

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return CheckResult("index_and_config", "FAIL", f"Index manifest unreadable: {error}")

    manifest_model = manifest.get("embedding_model_id")
    manifest_revision = manifest.get("embedding_model_revision")
    configured_model = env.get("EMBEDDING_MODEL_ID")
    configured_revision = env.get("EMBEDDING_MODEL_REVISION")

    problems: list[str] = []
    if configured_model and manifest_model and configured_model != manifest_model:
        problems.append(f"model id mismatch: manifest {manifest_model} vs configured {configured_model}")
    if configured_revision and manifest_revision and configured_revision != manifest_revision:
        problems.append(
            f"model revision mismatch: manifest {manifest_revision} vs configured {configured_revision}"
        )
    if not configured_revision:
        problems.append("EMBEDDING_MODEL_REVISION is not set in configuration")
    if problems:
        return CheckResult(
            "index_and_config",
            "FAIL",
            "; ".join(problems) + ".",
            {
                "manifest_model": manifest_model,
                "manifest_revision": manifest_revision,
                "configured_revision_present": bool(configured_revision),
            },
        )
    return CheckResult(
        "index_and_config",
        "PASS",
        f"Index manifest and configuration agree on {manifest_model} @ {manifest_revision}.",
        {
            "manifest_model": manifest_model,
            "manifest_revision": manifest_revision,
            "index_manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
        },
    )


def check_artifact_paths(env: dict[str, str]) -> CheckResult:
    processed_dir = REPO_ROOT / env.get("DATA_PROCESSED_DIR", "data/processed")
    qdrant_dir = processed_dir / "qdrant"
    embedded_files = list(processed_dir.glob("*/*_chunks_embedded.jsonl"))
    missing: list[str] = []
    if not qdrant_dir.is_dir():
        missing.append(str(qdrant_dir.relative_to(REPO_ROOT)))
    if not embedded_files:
        missing.append("*/*_chunks_embedded.jsonl (no embedded chunk files)")
    if missing:
        return CheckResult(
            "artifact_paths",
            "FAIL",
            f"Missing local-startup artifacts: {'; '.join(missing)}.",
            {"embedded_chunk_files": len(embedded_files)},
        )
    return CheckResult(
        "artifact_paths",
        "PASS",
        f"Local startup artifacts present: {len(embedded_files)} embedded chunk files and the Qdrant directory.",
        {"embedded_chunk_files": len(embedded_files)},
    )


def check_model_cache(env: dict[str, str]) -> CheckResult:
    hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    hub = hf_home / "hub"
    revision = env.get("EMBEDDING_MODEL_REVISION", "")
    model_dir_name = f"models--{env.get('EMBEDDING_MODEL_ID', 'nomic-ai/nomic-embed-text-v1.5').replace('/', '--')}"
    model_dir = hub / model_dir_name
    nomic_cached = model_dir.is_dir()
    reranker_cached = (hub / "models--cross-encoder--ms-marco-MiniLM-L-6-v2").is_dir()
    revision_hint = ""
    if nomic_cached and revision:
        revision_hint = f"; pinned revision {revision} {'has snapshots' if any(model_dir.glob('snapshots/*')) else 'has no local snapshot yet'}"
    if nomic_cached and reranker_cached:
        return CheckResult(
            "model_cache",
            "PASS",
            f"Embedding and reranker models are present in the local Hugging Face cache{revision_hint}. The Docker build downloads its own copies.",
            {"embedding_model_cached": True, "reranker_cached": True},
        )
    return CheckResult(
        "model_cache",
        "WARN",
        "Model cache is incomplete; the Docker build will download pinned models from Hugging Face during build.",
        {"embedding_model_cached": nomic_cached, "reranker_cached": reranker_cached},
    )


def check_port_and_lock(env: dict[str, str]) -> CheckResult:
    port = int(env.get("RELEASE_PORT", "8000"))
    available = True
    detail_parts: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
    except OSError:
        available = False
        detail_parts.append(f"port {port} is already in use")
    lock_file = REPO_ROOT / env.get("QDRANT_LOCAL_PATH", "data/processed/qdrant") / "lock"
    if lock_file.exists():
        detail_parts.append(
            "Qdrant lock file exists (normal after an unclean shutdown; Qdrant local recreates it on start)"
        )
    if not available:
        return CheckResult(
            "port_and_lock",
            "FAIL",
            "; ".join(detail_parts) + f". Stop the other process or set RELEASE_PORT.",
            {"port": port, "port_available": False},
        )
    return CheckResult(
        "port_and_lock",
        "PASS",
        ("; ".join(detail_parts) + f"; port {port} is free.") if detail_parts else f"Port {port} is free.",
        {"port": port, "port_available": True},
    )


def check_dockerignore() -> CheckResult:
    ignore_path = REPO_ROOT / ".dockerignore"
    if not ignore_path.is_file():
        return CheckResult("dockerignore", "FAIL", ".dockerignore is missing.")
    entries = {
        line.strip().rstrip("/")
        for line in ignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    required = {"data", "frontend", ".env"}
    missing = sorted(required - entries)
    if missing:
        return CheckResult(
            "dockerignore",
            "FAIL",
            f".dockerignore is missing required entries: {', '.join(missing)}.",
            {"missing": missing},
        )
    return CheckResult(
        "dockerignore",
        "PASS",
        "Build context excludes data/, frontend/, and .env secrets.",
        {"entries": sorted(entries)},
    )


def load_env_without_secrets() -> dict[str, str]:
    """Parse .env but expose only non-secret, release-relevant keys."""
    safe_keys = [
        "QDRANT_MODE",
        "QDRANT_LOCAL_PATH",
        "QDRANT_INDEX_MANIFEST_PATH",
        "EMBEDDING_MODEL_ID",
        "EMBEDDING_MODEL_REVISION",
        "DATA_PROCESSED_DIR",
        "ALLOWED_ORIGINS",
    ]
    values: dict[str, str] = {}
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw = line.partition("=")
            key = key.strip()
            if key in safe_keys:
                values[key] = raw.strip().strip('"').strip("'")
    for key in safe_keys:
        if key not in values and os.environ.get(key):
            values[key] = os.environ[key]
    return values


CHECKS = [
    check_docker_daemon,
    check_host_resources,
    check_git_state,
    check_artifact_paths,
    check_index_and_config_alignment,
    check_model_cache,
    check_port_and_lock,
    check_dockerignore,
]


def run_preflight() -> tuple[str, list[CheckResult]]:
    env = load_env_without_secrets()
    results = []
    index_result: CheckResult | None = None
    for check in CHECKS:
        if check is check_index_and_config_alignment:
            index_result = check(env)
            results.append(index_result)
            continue
        if check is check_artifact_paths or check is check_port_and_lock or check is check_model_cache:
            results.append(check(env))
            continue
        results.append(check())
    worst = max((STATUS_ORDER[result.status] for result in results), default=0)
    overall = {0: "PASS", 1: "PASS_WITH_WARNINGS", 2: "BLOCKED", 3: "FAILED"}[worst]
    if index_result is not None and index_result.status == "FAIL":
        overall = "FAILED"
    return overall, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only release preflight (no repairs, no secrets).")
    parser.add_argument("--json", type=Path, help="Write the report as JSON to this path (outside Git is recommended).")
    args = parser.parse_args()

    overall, results = run_preflight()
    print(f"Release preflight: {overall}")
    for result in results:
        print(f"  [{result.status:7}] {result.name}: {result.detail}")

    if args.json:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall": overall,
            "checks": [
                {"name": r.name, "status": r.status, "detail": r.detail, "data": r.data}
                for r in results
            ],
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"JSON report written to {args.json}")

    return 1 if any(r.status == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
