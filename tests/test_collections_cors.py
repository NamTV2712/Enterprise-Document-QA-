"""CORS coverage for the protected collection PATCH contract."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from pydantic import SecretStr

from src.api import access
from src.api.app import app


ORIGIN = "http://localhost:3000"
TOKEN = "collections-cors-token-0123456789abcdef"


async def _request(
    method: str,
    path: str,
    *,
    headers: dict[str, str],
    json: object | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        return await client.request(method, path, headers=headers, json=json)


def _call(method: str, path: str, *, headers: dict[str, str], json: object | None = None) -> httpx.Response:
    return asyncio.run(_request(method, path, headers=headers, json=json))


def _preflight(*, origin: str = ORIGIN, method: str = "PATCH", headers: str = "authorization,content-type") -> httpx.Response:
    return _call(
        "OPTIONS",
        "/collections/col-cors",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_approved_collection_patch_preflight_succeeds() -> None:
    response = _preflight()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "PATCH" in response.headers["access-control-allow-methods"]
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


@pytest.mark.parametrize(
    ("origin", "method", "headers"),
    [
        ("https://untrusted.example", "PATCH", "authorization,content-type"),
        (ORIGIN, "PUT", "authorization,content-type"),
        (ORIGIN, "PATCH", "authorization,x-unapproved-workspace-header"),
    ],
)
def test_collection_preflight_keeps_the_existing_allowlist(
    origin: str,
    method: str,
    headers: str,
) -> None:
    assert _preflight(origin=origin, method=method, headers=headers).status_code == 400


@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_successful_preflight_does_not_bypass_collection_authorization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    token: str | None,
) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "local")
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr(TOKEN))
    monkeypatch.setattr(access.settings, "local_workspace_allowed_origins", ORIGIN)
    monkeypatch.setattr(access.settings, "local_workspace_allowed_hosts", "localhost,127.0.0.1,[::1]")
    monkeypatch.setattr(access.settings, "workspace_db_path", tmp_path / "workspace.sqlite3")
    headers = {"Host": "localhost:8000", "Origin": ORIGIN}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    assert _preflight().status_code == 200
    response = _call(
        "PATCH",
        "/collections/col-cors",
        headers=headers,
        json={"revision": 1, "name": "Denied"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert not (tmp_path / "workspace.sqlite3").exists()
