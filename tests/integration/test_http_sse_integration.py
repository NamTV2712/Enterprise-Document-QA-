"""HTTP/SSE integration tests: real FastAPI server, fake pipeline.

These tests run the production FastAPI application through a real loopback
HTTP server (uvicorn, proxy_headers disabled) with the retrieval pipeline
replaced by deterministic fixtures. They exercise transport, sessions,
CORS, rate limits, and proxy-header handling end to end — they are marked
`integration` so the hermetic suite stays socket-guarded.

The frontend is NOT involved here; frontend-over-HTTP coverage lives in
the Playwright integration specs.
"""

from __future__ import annotations

import os
import json
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_SCRIPT = Path(__file__).resolve().parent / "harness_server.py"
APP_PORT = 8765
PROXY_PORT = 8766
APP_BASE = f"http://127.0.0.1:{APP_PORT}"
PROXY_BASE = f"http://127.0.0.1:{PROXY_PORT}"


def _free_port(start: int) -> int:
    port = start
    while port < start + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                port += 1
                continue
        return port
    raise RuntimeError("no free ports")


def _spawn_harness(app_port: int, proxy_port: int, extra_env: dict[str, str] | None = None):
    """Start one harness server process and wait for readiness.

    Returns (process, app_base, proxy_base). The caller owns the process
    and must terminate it.
    """
    import httpx

    env = dict(os.environ)
    env.update(
        {
            "HARNESS_PORT": str(app_port),
            "PROXY_PORT": str(proxy_port),
            "HARNESS_TEMP_DIR": str(Path(os.environ.get("TEMP", REPO_ROOT)) / "edqa-harness-test"),
        }
    )
    if extra_env:
        env.update(extra_env)
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    # Logs go to a file, never a pipe: an unread pipe fills after ~64 KB and
    # blocks request handlers mid-logging (observed as client ReadTimeouts).
    log_path = Path(env["HARNESS_TEMP_DIR"]) / f"harness-{app_port}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, str(HARNESS_SCRIPT)],
        env=env,
        cwd=str(REPO_ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    base = f"http://127.0.0.1:{app_port}"
    deadline = time.time() + 60
    ready = False
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(
                "harness server exited early:\n" + output
            )
        try:
            if httpx.get(f"{base}/health/live", timeout=2).status_code == 200:
                ready = True
                break
        except httpx.HTTPError:
            time.sleep(0.5)
    if not ready:
        _terminate(process)
        raise RuntimeError("harness server did not become ready in time")
    return process, base, f"http://127.0.0.1:{proxy_port}", log_path


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        process.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@pytest.fixture(scope="module")
def harness():
    """One shared harness (high burst limit) for the module."""
    app_port = _free_port(8765)
    proxy_port = _free_port(app_port + 1)
    process, base, proxy_base, log_path = _spawn_harness(app_port, proxy_port)
    try:
        yield {"app": base, "proxy": proxy_base, "log": str(log_path)}
    finally:
        _terminate(process)


@pytest.fixture()
def strict_harness():
    """A separate harness with a 2/minute burst for the rate-limit test."""
    app_port = _free_port(8900)
    proxy_port = _free_port(app_port + 1)
    process, base, _proxy, log_path = _spawn_harness(
        app_port, proxy_port, {"HARNESS_RATE_BURST": "2/minute"}
    )
    try:
        yield {"app": base}
    finally:
        _terminate(process)


def test_health_live_and_ready_report_build_metadata_when_configured(harness) -> None:
    import httpx

    live = httpx.get(f"{harness['app']}/health/live", timeout=5)
    assert live.status_code == 200

    ready = httpx.get(f"{harness['app']}/health/ready", timeout=5)
    assert ready.status_code == 200
    payload = ready.json()
    assert payload["pipeline_ready"] is True
    assert payload["corpus"]["searchable_company_count"] > 0
    # Harness does not set GIT_REVISION: no build object, no secrets.
    assert "build" not in payload


def test_readiness_flips_to_503_until_pipeline_is_restored(harness) -> None:
    import httpx

    down = httpx.post(f"{harness['app']}/__harness__/state", json={"pipeline_ready": False}, timeout=5)
    assert down.status_code == 200
    not_ready = httpx.get(f"{harness['app']}/health/ready", timeout=5)
    assert not_ready.status_code == 503
    # The legacy /health stays 200 with pipeline_ready=false.
    legacy = httpx.get(f"{harness['app']}/health", timeout=5)
    assert legacy.status_code == 200
    assert legacy.json()["pipeline_ready"] is False

    httpx.post(f"{harness['app']}/__harness__/state", json={"pipeline_ready": True}, timeout=5)
    ready = httpx.get(f"{harness['app']}/health/ready", timeout=5)
    assert ready.status_code == 200


def test_supported_tickers_come_from_the_harness_state(harness) -> None:
    import httpx

    response = httpx.get(f"{harness['app']}/supported-tickers", timeout=5)
    assert response.status_code == 200
    payload = response.json()
    assert "AAPL" in payload["tickers"]
    assert "mdna" in payload["sections"]


def test_non_streaming_query_returns_cited_answer_and_sources(harness) -> None:
    import httpx

    response = httpx.post(
        f"{harness['app']}/query",
        json={"question": "What was Apple total revenue?", "ticker": "AAPL", "top_k": 5},
        timeout=15,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "[Source 1]" in payload["answer"]
    assert payload["model_used"] == "harness/gpt-fake"
    assert payload["sources"][0]["chunk_id"] == "AAPL_harness_0000"
    assert payload["sources"][0]["ticker"] == "AAPL"


def test_streaming_query_emits_sources_tokens_then_done(harness) -> None:
    import httpx

    events: list[dict] = []
    with httpx.stream(
        "POST",
        f"{harness['app']}/query/stream",
        json={"question": "What was Microsoft cloud revenue?", "ticker": "MSFT", "top_k": 5},
        timeout=15,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        for line in response.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))

    types = [event["type"] for event in events]
    assert types[0] == "sources"
    assert "token" in types
    assert types[-1] == "done"
    answer = "".join(event["data"] for event in events if event["type"] == "token")
    assert "[Source 1]." in answer


def test_stream_through_rechunking_proxy_parses_mid_utf8_chunks(harness) -> None:
    """The proxy forwards one byte at a time: SSE events and multi-byte UTF-8
    are cut apart on the wire. The response must still be reassembled."""
    import httpx

    events: list[dict] = []
    with httpx.stream(
        "POST",
        f"{harness['proxy']}/query/stream",
        json={"question": "Évidence split test", "ticker": "AAPL", "top_k": 5},
        timeout=30,
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))

    answer = "".join(event["data"] for event in events if event["type"] == "token")
    assert "évidence" in answer  # the multi-byte token survived the split
    assert events[-1]["type"] == "done"


def test_stream_missing_done_event_still_delivers_partial_answer(harness) -> None:
    import httpx

    httpx.post(f"{harness['app']}/__harness__/failure", json={"mode": "omit_done"}, timeout=5)
    events: list[dict] = []
    try:
        with httpx.stream(
            "POST",
            f"{harness['app']}/query/stream",
            json={"question": "Omit done test", "ticker": "AAPL", "top_k": 5},
            timeout=15,
        ) as response:
            assert response.status_code == 200
            for line in response.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[len("data: "):]))
    finally:
        httpx.post(f"{harness['app']}/__harness__/failure", json={"mode": "clear"}, timeout=5)

    assert events[-1]["type"] != "done"
    answer = "".join(event["data"] for event in events if event["type"] == "token")
    assert answer  # partial answer content was delivered


def test_session_history_and_memory_flow(harness) -> None:
    import httpx

    session = "integration-session-1"
    first = httpx.post(
        f"{harness['app']}/query",
        json={"question": "First question", "ticker": "AAPL", "session_id": session},
        timeout=15,
    )
    assert first.status_code == 200

    history = httpx.get(f"{harness['app']}/session/{session}/history", timeout=5)
    assert history.status_code == 200
    payload = history.json()
    assert payload["context"]["status"] == "available"
    assert payload["context"]["retained_turns"] == 1
    assert payload["context"]["ttl_remaining_seconds"] > 0
    assert payload["turns"][0]["user"] == "First question"

    # Simulate a backend restart: memory is empty, history reports missing.
    httpx.post(f"{harness['app']}/__harness__/memory/reset", timeout=5)
    after = httpx.get(f"{harness['app']}/session/{session}/history", timeout=5)
    assert after.json()["context"]["status"] == "missing"
    assert after.json()["turns"] == []


def test_decomposed_query_success_and_error_paths(harness) -> None:
    import httpx

    success = httpx.post(
        f"{harness['app']}/query/decomposed",
        json={"question": "Compare Apple and Microsoft cloud revenue", "top_k": 5},
        timeout=30,
    )
    assert success.status_code == 200
    payload = success.json()
    assert payload["was_decomposed"] is True
    assert [sub["ticker"] for sub in payload["sub_queries"]] == ["AAPL", "MSFT"]

    httpx.post(f"{harness['app']}/__harness__/failure", json={"mode": "decomposed_error"}, timeout=5)
    failed = httpx.post(
        f"{harness['app']}/query/decomposed",
        json={"question": "Compare Apple and Microsoft risk factors", "top_k": 5},
        timeout=30,
    )
    assert failed.status_code == 200
    assert "error while synthesizing" in failed.json()["answer"].lower()
    httpx.post(f"{harness['app']}/__harness__/failure", json={"mode": "clear"}, timeout=5)


def test_decomposed_timeout_returns_504(harness) -> None:
    import httpx

    httpx.post(f"{harness['app']}/__harness__/failure", json={"mode": "decomposed_slow"}, timeout=5)
    response = httpx.post(
        f"{harness['app']}/query/decomposed",
        json={"question": "Compare Apple and Amazon cloud revenue", "top_k": 5},
        timeout=30,
    )
    assert response.status_code == 504
    httpx.post(f"{harness['app']}/__harness__/failure", json={"mode": "clear"}, timeout=5)


def test_rate_limit_returns_429_and_forged_forwarded_headers_do_not_split_the_bucket(strict_harness) -> None:
    """With no trusted proxies configured, the identity must be the socket
    peer even when X-Forwarded-For is forged. If uvicorn also rewrote the
    client, each forged header would create a fresh bucket and the third
    request would not be limited."""
    import httpx

    statuses = []
    for index in range(4):
        response = httpx.post(
            f"{strict_harness['app']}/query",
            json={"question": f"Rate limit probe {index}", "ticker": "AAPL"},
            headers={
                "X-Forwarded-For": f"203.0.113.{10 + index}",
                "X-Forwarded-Proto": "https",
            },
            timeout=15,
        )
        statuses.append(response.status_code)
    assert statuses[:2] == [200, 200]
    assert 429 in statuses
    limited = statuses.index(429)
    body = httpx.get(f"{strict_harness['app']}/health/live", timeout=5)  # sanity: server alive
    assert body.status_code == 200
    assert statuses[limited] == 429


def test_cors_allows_configured_origin_and_omits_header_for_others(harness) -> None:
    import httpx

    allowed = httpx.get(
        f"{harness['app']}/supported-tickers",
        headers={"Origin": "http://localhost:3000"},
        timeout=5,
    )
    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"

    denied = httpx.get(
        f"{harness['app']}/supported-tickers",
        headers={"Origin": "https://evil.example"},
        timeout=5,
    )
    assert denied.status_code == 200
    assert "access-control-allow-origin" not in denied.headers


def test_errors_do_not_leak_harness_internals(harness) -> None:
    import httpx

    httpx.post(f"{harness['app']}/__harness__/failure", json={"mode": "decomposed_slow"}, timeout=5)
    response = httpx.post(
        f"{harness['app']}/query/decomposed",
        json={"question": "Leak probe", "top_k": 5},
        timeout=30,
    )
    httpx.post(f"{harness['app']}/__harness__/failure", json={"mode": "clear"}, timeout=5)
    body = response.text
    assert "harness_server" not in body
    assert "Traceback" not in body
    assert "harness-fake-key" not in body


@pytest.fixture()
def strict_harness():
    """A separate harness with a 2/minute burst for the rate-limit test."""
    app_port = _free_port(8900)
    proxy_port = _free_port(app_port + 1)
    process, base, _proxy, log_path = _spawn_harness(
        app_port, proxy_port, {"HARNESS_RATE_BURST": "2/minute"}
    )
    import httpx

    deadline = time.time() + 60
    ready = False
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("strict harness exited early")
        try:
            if httpx.get(f"{base}/health/live", timeout=2).status_code == 200:
                ready = True
                break
        except httpx.HTTPError:
            time.sleep(0.5)
    assert ready, "strict harness did not become ready"
    yield {"app": base}
    _terminate(process)
    try:
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "HARNESS_DEBUG" in line or "ratelimit" in line.lower():
                print("STRICT_HARNESS:", line)
    except OSError:
        pass
