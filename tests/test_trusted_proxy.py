"""Trusted-proxy rate-limit identity tests.

Covers the shared-bucket fix for deployments behind ngrok/Docker proxies
while proving that direct clients cannot forge their bucket through
X-Forwarded-For, and that the empty default keeps legacy peer keying.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from configs.settings import settings
from src.api import app as app_module
from src.api.proxy import resolve_client_ip
from src.generation.generator import RAGResponse

PROXY_PEER = "203.0.113.9"
CLIENT_A = "198.51.100.71"
CLIENT_B = "198.51.100.72"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Keep in-memory rate-limit counters isolated between tests."""
    app_module.limiter.reset()
    yield
    app_module.limiter.reset()


@pytest.fixture
def mock_pipeline():
    """Minimal fake pipeline sufficient for /query 200 responses."""
    pipeline = MagicMock()
    pipeline.query.return_value = RAGResponse(
        answer="Apple faces competition risks.",
        retrieved_chunks=[],
        model_used="mock-model",
    )
    return pipeline


@pytest.fixture
def mock_decomposer():
    return MagicMock()


# ---------------------------------------------------------------------------
# Pure resolver behavior
# ---------------------------------------------------------------------------


def test_default_empty_cidrs_ignores_forwarded_header() -> None:
    assert (
        resolve_client_ip("198.51.100.5", "1.2.3.4", "") == "198.51.100.5"
    )


def test_untrusted_peer_cannot_spoof_identity_via_forwarded_header() -> None:
    assert (
        resolve_client_ip(
            "198.51.100.5", "6.6.6.6", "203.0.113.0/24"
        )
        == "198.51.100.5"
    )


def test_single_trusted_hop_returns_forwarded_client() -> None:
    assert (
        resolve_client_ip(PROXY_PEER, CLIENT_A, "203.0.113.0/24") == CLIENT_A
    )


def test_multiple_trusted_hops_pick_first_non_trusted_from_right() -> None:
    chain = f"{CLIENT_A}, 10.0.0.1, {PROXY_PEER}"
    cidrs = "203.0.113.0/24,10.0.0.0/8"
    assert resolve_client_ip(PROXY_PEER, chain, cidrs) == CLIENT_A


def test_all_hops_trusted_falls_back_to_peer() -> None:
    chain = "10.0.0.1, 10.0.0.2"
    assert (
        resolve_client_ip("10.0.0.3", chain, "10.0.0.0/8") == "10.0.0.3"
    )


@pytest.mark.parametrize(
    "forwarded",
    [
        None,
        "",
        "not-an-ip",
        f"{CLIENT_A}, evil-injection",
        f"{CLIENT_A}:8080",
        f"{CLIENT_A},,",
        "'; DROP TABLE users; --",
    ],
)
def test_malformed_header_falls_back_to_peer(forwarded: str | None) -> None:
    assert (
        resolve_client_ip(PROXY_PEER, forwarded, "203.0.113.0/24")
        == PROXY_PEER
    )


def test_ipv6_proxy_and_client_are_supported() -> None:
    resolved = resolve_client_ip(
        "2001:db8::1",
        "2606:2800:220:1::42",
        "2001:db8::/32",
    )
    assert resolved == "2606:2800:220:1::42"


def test_bracketed_ipv6_tokens_are_tolerated() -> None:
    resolved = resolve_client_ip(
        "[2001:db8::1]",
        "[2606:2800:220:1::42]",
        "2001:db8::/32",
    )
    assert resolved == "2606:2800:220:1::42"


def test_invalid_cidr_entries_grant_no_trust_but_do_not_crash() -> None:
    resolved = resolve_client_ip(
        PROXY_PEER, CLIENT_A, "999.999.0.0/16, not-a-cidr, 203.0.113.0/24"
    )
    assert resolved == CLIENT_A


def test_missing_peer_address_reports_unknown() -> None:
    assert resolve_client_ip(None, None, "") == "unknown"


# ---------------------------------------------------------------------------
# API-level rate-limit isolation
# ---------------------------------------------------------------------------


def _post(client: httpx.AsyncClient, path: str) -> httpx.Response:
    return client.post(path, json={"question": "What are Apple's risks?"})


def _make_transport(peer: tuple[str, int]) -> httpx.ASGITransport:
    return httpx.ASGITransport(app=app_module.app, client=peer)


async def _exhaust_burst(client: httpx.AsyncClient, headers: dict | None) -> None:
    request_headers = headers or {}
    for _ in range(10):
        response = await client.post(
            "/query",
            json={"question": "What are Apple's risks?"},
            headers=request_headers,
        )
        assert response.status_code == 200


def test_two_clients_behind_trusted_proxy_get_separate_buckets(
    mock_pipeline, mock_decomposer, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_cidrs", "203.0.113.0/24")
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline
    app_module._state["decomposer"] = mock_decomposer

    async def run_requests() -> tuple[httpx.Response, httpx.Response]:
        transport_a = _make_transport((PROXY_PEER, 50000))
        transport_b = _make_transport((PROXY_PEER, 50000))
        async with (
            httpx.AsyncClient(transport=transport_a, base_url="http://test") as via_proxy_a,
            httpx.AsyncClient(transport=transport_b, base_url="http://test") as via_proxy_b,
        ):
            await _exhaust_burst(via_proxy_a, {"X-Forwarded-For": CLIENT_A})
            blocked_same_client = await via_proxy_a.post(
                "/query",
                json={"question": "What are Apple's risks?"},
                headers={"X-Forwarded-For": CLIENT_A},
            )
            other_client_allowed = await via_proxy_b.post(
                "/query",
                json={"question": "What are Apple's risks?"},
                headers={"X-Forwarded-For": CLIENT_B},
            )
            return blocked_same_client, other_client_allowed

    try:
        blocked, allowed = asyncio.run(run_requests())
    finally:
        app_module._state.clear()

    assert blocked.status_code == 429
    assert allowed.status_code == 200


def test_direct_client_cannot_shard_buckets_with_unique_headers(
    mock_pipeline, mock_decomposer, monkeypatch
) -> None:
    """Unique XFF values must all land in the same unconfigured-peer bucket."""
    monkeypatch.setattr(settings, "trusted_proxy_cidrs", "")
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline
    app_module._state["decomposer"] = mock_decomposer

    async def run_requests() -> list[httpx.Response]:
        transport = _make_transport(("198.51.100.90", 50000))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as direct_client:
            responses = []
            for index in range(12):
                response = await direct_client.post(
                    "/query",
                    json={"question": "What are Apple's risks?"},
                    headers={"X-Forwarded-For": f"10.9.9.{index}"},
                )
                responses.append(response)
            return responses

    try:
        responses = asyncio.run(run_requests())
    finally:
        app_module._state.clear()

    statuses = [response.status_code for response in responses]
    # One shared bucket: exactly the first ten pass and the rest are limited.
    assert statuses == [200] * 10 + [429] * 2
