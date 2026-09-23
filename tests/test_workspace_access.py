"""Hermetic API-001 local workspace access-boundary tests."""

from __future__ import annotations

import asyncio
import logging

import httpx
import pytest
from fastapi import Depends, FastAPI
from pydantic import SecretStr, ValidationError

from configs.settings import Settings
from src.api import access
from src.api import app as app_module
from src.api.access import AccessGrant


WORKSPACE_TOKEN = "workspace-test-token-0123456789-abcdef"
PROVIDER_SECRET = "provider-secret-must-never-leak"
LOCAL_ORIGIN = "http://localhost:3000"
LOCAL_HOST = "localhost:8000"


boundary_app = FastAPI()


@boundary_app.get(
    "/public",
    dependencies=[Depends(access.require_public_provider_free_access)],
)
async def public_probe() -> dict[str, str]:
    return {"capability": "public_provider_free"}


@boundary_app.get("/private")
async def private_read(
    grant: AccessGrant = Depends(access.require_local_workspace_access),
) -> dict[str, list[str]]:
    return {"capabilities": sorted(capability.value for capability in grant.capabilities)}


@boundary_app.post("/private")
async def private_write(
    grant: AccessGrant = Depends(access.require_local_workspace_access),
) -> dict[str, list[str]]:
    return {"capabilities": sorted(capability.value for capability in grant.capabilities)}


@boundary_app.post("/jobs")
async def execution_probe(
    grant: AccessGrant = Depends(access.require_execution_access),
) -> dict[str, list[str]]:
    return {"capabilities": sorted(capability.value for capability in grant.capabilities)}


def _set_public_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "public")
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr(""))
    monkeypatch.setattr(access.settings, "enable_workspace_execution", False)


def _set_local_mode(
    monkeypatch: pytest.MonkeyPatch,
    *,
    execution: bool = False,
) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "local")
    monkeypatch.setattr(
        access.settings,
        "local_workspace_token",
        SecretStr(WORKSPACE_TOKEN),
    )
    monkeypatch.setattr(
        access.settings,
        "local_workspace_allowed_origins",
        LOCAL_ORIGIN,
    )
    monkeypatch.setattr(
        access.settings,
        "local_workspace_allowed_hosts",
        "localhost,127.0.0.1,[::1]",
    )
    monkeypatch.setattr(access.settings, "enable_workspace_execution", execution)


def _headers(
    *,
    token: str | None = WORKSPACE_TOKEN,
    origin: str | None = LOCAL_ORIGIN,
    host: str = LOCAL_HOST,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    headers = {"Host": host}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if origin is not None:
        headers["Origin"] = origin
    if extra:
        headers.update(extra)
    return headers


async def _request(
    app: FastAPI,
    method: str,
    path: str,
    *,
    peer: str = "127.0.0.1",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, client=(peer, 50000))
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://localhost:8000",
    ) as client:
        return await client.request(method, path, headers=headers)


def _call(
    method: str,
    path: str,
    *,
    app: FastAPI = boundary_app,
    peer: str = "127.0.0.1",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return asyncio.run(_request(app, method, path, peer=peer, headers=headers))


def test_public_mode_allows_public_provider_free_endpoint(monkeypatch) -> None:
    _set_public_mode(monkeypatch)

    response = _call("GET", "/public")

    assert response.status_code == 200
    assert response.json() == {"capability": "public_provider_free"}


def test_public_mode_denies_private_read(monkeypatch) -> None:
    _set_public_mode(monkeypatch)

    response = _call("GET", "/private", headers=_headers())

    assert response.status_code == 404
    assert response.json() == {"detail": "Local workspace capability is unavailable"}


def test_public_mode_denies_private_write(monkeypatch) -> None:
    _set_public_mode(monkeypatch)

    response = _call("POST", "/private", headers=_headers())

    assert response.status_code == 404
    assert response.json() == {"detail": "Local workspace capability is unavailable"}


def test_local_mode_requires_explicit_strong_token_configuration() -> None:
    with pytest.raises(ValidationError, match="LOCAL_WORKSPACE_TOKEN"):
        Settings(workspace_mode="local", local_workspace_token="")


def test_local_mode_missing_token_is_deterministic(monkeypatch) -> None:
    _set_local_mode(monkeypatch)

    response = _call("GET", "/private", headers=_headers(token=None))

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Local workspace authentication required"}


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer wrong-token",
        "Basic workspace-test-token",
        "Bearer",
        f"Bearer {WORKSPACE_TOKEN} extra",
        "",
    ],
)
def test_local_mode_invalid_or_malformed_token_is_deterministic(
    monkeypatch,
    authorization: str,
) -> None:
    _set_local_mode(monkeypatch)
    headers = _headers(token=None)
    if authorization:
        headers["Authorization"] = authorization

    response = _call("GET", "/private", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Local workspace authentication required"}


def test_local_mode_valid_token_allows_private_read_and_write(monkeypatch) -> None:
    _set_local_mode(monkeypatch)

    read_response = _call("GET", "/private", headers=_headers())
    write_response = _call("POST", "/private", headers=_headers())

    assert read_response.status_code == 200
    assert write_response.status_code == 200
    assert read_response.json()["capabilities"] == [
        "local_workspace",
        "public_provider_free",
    ]


def test_non_loopback_peer_is_rejected_with_valid_token(monkeypatch) -> None:
    _set_local_mode(monkeypatch)

    response = _call(
        "GET",
        "/private",
        peer="198.51.100.25",
        headers=_headers(),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Local workspace access is restricted to loopback clients"
    }


def test_forwarding_headers_cannot_spoof_loopback_peer(monkeypatch) -> None:
    _set_local_mode(monkeypatch)

    response = _call(
        "GET",
        "/private",
        peer="198.51.100.25",
        headers=_headers(
            extra={
                "Forwarded": "for=127.0.0.1;host=localhost",
                "X-Forwarded-For": "127.0.0.1",
                "X-Forwarded-Host": "localhost",
            }
        ),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Local workspace access is restricted to loopback clients"
    }


def test_exact_allowed_origin_and_originless_local_client_are_allowed(monkeypatch) -> None:
    _set_local_mode(monkeypatch)

    browser_response = _call("GET", "/private", headers=_headers())
    originless_response = _call(
        "GET",
        "/private",
        headers=_headers(origin=None),
    )

    assert browser_response.status_code == 200
    assert originless_response.status_code == 200


@pytest.mark.parametrize(
    "origin",
    [
        "https://untrusted.example",
        "http://localhost:3000.evil.example",
        "http://localhost:3000/",
        "null",
    ],
)
def test_non_exact_or_denied_origin_is_rejected(monkeypatch, origin: str) -> None:
    _set_local_mode(monkeypatch)

    response = _call("GET", "/private", headers=_headers(origin=origin))

    assert response.status_code == 403
    assert response.json() == {"detail": "Local workspace request origin is not allowed"}


@pytest.mark.parametrize(
    "host",
    [
        "localhost.evil.example:8000",
        "198.51.100.25:8000",
        "localhost:8000/hidden",
        "",
    ],
)
def test_non_exact_or_denied_host_is_rejected(monkeypatch, host: str) -> None:
    _set_local_mode(monkeypatch)

    response = _call("GET", "/private", headers=_headers(host=host))

    assert response.status_code == 403
    assert response.json() == {"detail": "Local workspace request host is not allowed"}


def test_configured_host_port_is_enforced(monkeypatch) -> None:
    _set_local_mode(monkeypatch)
    monkeypatch.setattr(
        access.settings,
        "local_workspace_allowed_hosts",
        "localhost:8000",
    )

    matching = _call("GET", "/private", headers=_headers(host="localhost:8000"))
    mismatched = _call("GET", "/private", headers=_headers(host="localhost:9000"))

    assert matching.status_code == 200
    assert mismatched.status_code == 403
    assert mismatched.json() == {
        "detail": "Local workspace request host is not allowed"
    }


def test_execution_capability_is_separate_and_disabled_by_default(monkeypatch) -> None:
    _set_local_mode(monkeypatch, execution=False)

    denied = _call("POST", "/jobs", headers=_headers())
    _set_local_mode(monkeypatch, execution=True)
    allowed = _call("POST", "/jobs", headers=_headers())

    assert denied.status_code == 403
    assert denied.json() == {"detail": "Workspace execution capability is disabled"}
    assert allowed.status_code == 200
    assert allowed.json()["capabilities"] == [
        "execution_jobs",
        "local_workspace",
        "public_provider_free",
    ]


def test_configuration_status_is_protected_and_redacts_all_secrets(
    monkeypatch,
    caplog,
) -> None:
    _set_local_mode(monkeypatch)
    monkeypatch.setattr(app_module.settings, "groq_api_key", PROVIDER_SECRET)
    caplog.set_level(logging.DEBUG)

    response = _call(
        "GET",
        "/system/configuration-status",
        app=app_module.app,
        headers=_headers(),
    )
    invalid = _call(
        "GET",
        "/system/configuration-status",
        app=app_module.app,
        headers=_headers(token="invalid-token"),
    )
    combined = response.text + invalid.text + caplog.text

    assert response.status_code == 200
    assert response.json() == {
        "deployment_mode": "local",
        "capabilities": {
            "public_provider_free": True,
            "local_workspace": True,
            "execution_jobs": False,
        },
    }
    assert invalid.status_code == 401
    assert WORKSPACE_TOKEN not in combined
    assert PROVIDER_SECRET not in combined
    assert "groq" not in response.text.casefold()


def test_configuration_status_fails_closed_in_public_mode(monkeypatch) -> None:
    _set_public_mode(monkeypatch)

    response = _call(
        "GET",
        "/system/configuration-status",
        app=app_module.app,
        headers=_headers(),
    )

    assert response.status_code == 404


def test_secret_setting_repr_and_json_are_redacted() -> None:
    configured = Settings(
        workspace_mode="local",
        local_workspace_token=WORKSPACE_TOKEN,
        allowed_origins=LOCAL_ORIGIN,
        local_workspace_allowed_origins=LOCAL_ORIGIN,
        local_workspace_allowed_hosts="localhost,127.0.0.1,[::1]",
    )

    assert WORKSPACE_TOKEN not in repr(configured)
    assert WORKSPACE_TOKEN not in configured.model_dump_json()
    assert configured.local_workspace_token.get_secret_value() == WORKSPACE_TOKEN


def test_local_settings_reject_remote_origins_hosts_and_cors_mismatch() -> None:
    with pytest.raises(ValidationError, match=r"loopback HTTP\(S\) origins"):
        Settings(
            workspace_mode="local",
            local_workspace_token=WORKSPACE_TOKEN,
            allowed_origins="https://example.com",
            local_workspace_allowed_origins="https://example.com",
        )
    with pytest.raises(ValidationError, match="localhost or loopback"):
        Settings(
            workspace_mode="local",
            local_workspace_token=WORKSPACE_TOKEN,
            local_workspace_allowed_hosts="workspace.internal",
        )
    with pytest.raises(ValidationError, match="included in ALLOWED_ORIGINS"):
        Settings(
            workspace_mode="local",
            local_workspace_token=WORKSPACE_TOKEN,
            allowed_origins="http://localhost:5173",
            local_workspace_allowed_origins=LOCAL_ORIGIN,
        )


def test_settings_validation_exception_redacts_all_input_values() -> None:
    exception_secret = "workspace-exception-secret-0123456789abcdef"

    with pytest.raises(ValidationError) as captured:
        Settings(
            workspace_mode="local",
            local_workspace_token=exception_secret,
            allowed_origins="https://example.com",
            local_workspace_allowed_origins="https://example.com",
        )

    message = str(captured.value)
    assert exception_secret not in message
    assert "input_value" not in message
