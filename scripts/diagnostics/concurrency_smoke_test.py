r"""Exercise the FastAPI service through real HTTP concurrent requests.

Run the API first:
    .venv\Scripts\python.exe -m uvicorn src.api.app:app --port 8000
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://localhost:8000"


async def send_query(
    client: httpx.AsyncClient,
    base_url: str,
    session_id: str,
    question: str,
) -> dict[str, Any]:
    response = await client.post(
        f"{base_url}/query",
        json={"question": question, "session_id": session_id},
        timeout=60.0,
    )
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text}
    return {"status_code": response.status_code, "payload": payload}


async def fetch_history(
    client: httpx.AsyncClient,
    base_url: str,
    session_id: str,
) -> dict[str, Any]:
    response = await client.get(f"{base_url}/session/{session_id}/history", timeout=30.0)
    response.raise_for_status()
    return response.json()


async def clear_session(client: httpx.AsyncClient, base_url: str, session_id: str) -> None:
    await client.delete(f"{base_url}/session/{session_id}", timeout=30.0)


async def test_session_isolation_under_concurrency(base_url: str) -> None:
    """Send requests for two sessions concurrently and verify histories stay isolated."""
    session_a = "concurrent-session-A"
    session_b = "concurrent-session-B"

    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            clear_session(client, base_url, session_a),
            clear_session(client, base_url, session_b),
        )
        results = await asyncio.gather(
            send_query(client, base_url, session_a, "What are Apple's risk factors?"),
            send_query(client, base_url, session_b, "What is Microsoft's revenue?"),
            send_query(client, base_url, session_a, "What about Apple's revenue?"),
            send_query(client, base_url, session_b, "What about Microsoft's risks?"),
        )

        for index, result in enumerate(results):
            payload = result["payload"]
            answer = payload.get("answer") or payload.get("detail") or payload.get("raw", "")
            print(f"Request {index}: status={result['status_code']} answer={str(answer)[:120]}")

        failed = [result for result in results if result["status_code"] != 200]
        if failed:
            raise AssertionError(f"Expected all requests to succeed, got {failed}")

        hist_a = await fetch_history(client, base_url, session_a)
        hist_b = await fetch_history(client, base_url, session_b)

    print("\nSession A history:", hist_a)
    print("\nSession B history:", hist_b)

    a_questions = [turn["user"] for turn in hist_a["turns"]]
    b_questions = [turn["user"] for turn in hist_b["turns"]]

    assert all("Apple" in question or "apple" in question for question in a_questions), a_questions
    assert all("Microsoft" in question for question in b_questions), b_questions
    print("\nPASS: Session isolation held under concurrent HTTP requests")


async def test_same_session_rapid_fire(base_url: str) -> None:
    """Send multiple near-simultaneous requests to one session and count stored turns."""
    session_id = "rapid-fire-session"
    async with httpx.AsyncClient() as client:
        await clear_session(client, base_url, session_id)
        results = await asyncio.gather(
            *[
                send_query(client, base_url, session_id, f"Question number {index} about Apple")
                for index in range(5)
            ]
        )
        failed = [result for result in results if result["status_code"] != 200]
        for index, result in enumerate(results):
            print(f"Rapid request {index}: status={result['status_code']}")
        if failed:
            raise AssertionError(f"Expected all rapid-fire requests to succeed, got {failed}")

        history = await fetch_history(client, base_url, session_id)

    turns = history["turns"]
    print(f"\nStored turns: {len(turns)} (expected: 5, capped by MAX_HISTORY_TURNS=5)")
    assert len(turns) == 5, turns
    print("PASS: Same-session rapid-fire requests retained all recent turns")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    async with httpx.AsyncClient() as client:
        health = await client.get(f"{args.base_url}/health", timeout=30.0)
        health.raise_for_status()
        print("Health:", health.json())

    await test_session_isolation_under_concurrency(args.base_url)
    await test_same_session_rapid_fire(args.base_url)


if __name__ == "__main__":
    asyncio.run(main())
