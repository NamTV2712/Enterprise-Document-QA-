"""Browser preflight must admit EVAL-003's required idempotency header."""

import asyncio

import httpx
import pytest
from pydantic import SecretStr

from src.api import app as app_module


ORIGIN = "http://localhost:3000"


async def _request(method, path, *, headers, json=None):
    # No lifespan: no models, corpus, database, or provider are initialized.
    transport = httpx.ASGITransport(app=app_module.app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        return await client.request(method, path, headers=headers, json=json)


def _call(method, path, *, headers, json=None):
    return asyncio.run(_request(method, path, headers=headers, json=json))


def _preflight(*, origin=ORIGIN, method="POST", headers="authorization,content-type,idempotency-key"):
    return _call("OPTIONS", "/evaluation/jobs", headers={
        "Origin": origin,
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": headers,
    })


def test_evaluation_creation_preflight_admits_required_idempotency_header():
    response = _preflight()
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()


@pytest.mark.parametrize("changes", [
    {"origin": "https://untrusted.example"},
    {"method": "PUT"},
    {"headers": "authorization,content-type,idempotency-key,x-unapproved-header"},
])
def test_evaluation_preflight_preserves_explicit_allowlists(changes):
    assert _preflight(**changes).status_code == 400


@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_evaluation_preflight_does_not_authorize_job_creation(monkeypatch, tmp_path, token):
    configured = app_module.settings
    monkeypatch.setattr(configured, "workspace_mode", "local")
    monkeypatch.setattr(configured, "local_workspace_token", SecretStr("evaluation-test-token-0123456789abcdef"))
    monkeypatch.setattr(configured, "local_workspace_allowed_origins", ORIGIN)
    monkeypatch.setattr(configured, "local_workspace_allowed_hosts", "localhost:8000")
    monkeypatch.setattr(configured, "enable_workspace_execution", True)
    monkeypatch.setattr(configured, "workspace_db_path", tmp_path / "workspace.sqlite3")
    headers = {"Origin": ORIGIN, "Idempotency-Key": "browser-attempt"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    assert _preflight().status_code == 200
    response = _call("POST", "/evaluation/jobs", headers=headers, json={})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert not configured.workspace_db_path.exists()
