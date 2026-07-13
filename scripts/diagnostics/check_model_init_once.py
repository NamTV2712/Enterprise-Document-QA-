"""Verify retrieval models are initialized once per FastAPI server lifetime.

The script starts a real Uvicorn subprocess, sends several HTTP requests, then
counts model-initialization log lines. It is intended as a diagnostic guard for
accidental per-request model loading.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx


BASE_URL = "http://127.0.0.1:8000"
REQUEST_COUNT = 3


def wait_for_health(timeout_seconds: float = 180.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code == 200 and response.json().get("pipeline_ready"):
                return
        except Exception as error:
            last_error = error
        time.sleep(1.0)
    raise RuntimeError(f"Server did not become healthy: {last_error}")


def main() -> None:
    log_dir = Path(".diagnostics")
    log_dir.mkdir(exist_ok=True)
    stdout_path = log_dir / "model_init_check_stdout.log"
    stderr_path = log_dir / "model_init_check_stderr.log"

    stdout_file = stdout_path.open("w", encoding="utf-8")
    stderr_file = stderr_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        stdout=stdout_file,
        stderr=stderr_file,
        text=True,
    )

    startup_error: Exception | None = None
    try:
        try:
            wait_for_health()
        except Exception as error:
            startup_error = error
        if startup_error is None:
            with httpx.Client(timeout=90.0) as client:
                for index in range(REQUEST_COUNT):
                    response = client.post(
                        f"{BASE_URL}/query",
                        json={
                            "question": "What are Apple's main risk factors?",
                            "ticker": "AAPL",
                            "section": "risk_factors",
                            "top_k": 1,
                        },
                    )
                    print(f"Request {index + 1}: status={response.status_code}")
                    response.raise_for_status()
    finally:
        process.terminate()
        try:
            process.wait(timeout=20.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=20.0)
        stdout_file.close()
        stderr_file.close()

    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    logs = f"{stdout}\n{stderr}"
    if startup_error is not None:
        print("Server startup failed. Captured log tail:")
        print(logs[-4000:])
        raise startup_error

    embedder_inits = logs.count("Loading embedding model:")
    cross_encoder_inits = logs.count("Loading cross-encoder:")
    print(f"Embedder init log count: {embedder_inits}")
    print(f"Cross-encoder init log count: {cross_encoder_inits}")

    if embedder_inits != 1 or cross_encoder_inits != 1:
        raise AssertionError(
            "Expected exactly one Embedder and CrossEncoder initialization per server lifetime"
        )


if __name__ == "__main__":
    main()
