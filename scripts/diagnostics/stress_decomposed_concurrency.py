"""Stress the decomposed-query endpoint with concurrent HTTP requests."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
QUESTION = (
    "Which company among Apple, Microsoft, and Amazon has the highest "
    "cybersecurity risk exposure?"
)


async def send_decomposed(client: httpx.AsyncClient, base_url: str) -> Any:
    return await client.post(
        f"{base_url}/query/decomposed",
        json={"question": QUESTION, "top_k": 3},
        timeout=90.0,
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--requests", type=int, default=3)
    args = parser.parse_args()

    async with httpx.AsyncClient() as client:
        tasks = [send_decomposed(client, args.base_url) for _ in range(args.requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    failures = []
    for index, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Request {index}: EXCEPTION - {result}")
            failures.append(result)
            continue

        try:
            payload = result.json()
        except Exception:
            payload = {"raw": result.text}
        print(
            f"Request {index}: status={result.status_code}, "
            f"num_sub_queries={len(payload.get('sub_queries', []))}, "
            f"detail={str(payload.get('detail', ''))[:160]}"
        )
        if result.status_code != 200:
            failures.append(payload)

    if failures:
        raise AssertionError(f"Expected all decomposed requests to succeed, got {failures}")


if __name__ == "__main__":
    asyncio.run(main())
