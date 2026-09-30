"""Production resolver and existing private API exercised without providers."""

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from src.api import app as application
from src.agent import provider
from src.agent.registry import build_tool_registry
from tests.test_agent_api import _call, _headers
from tests.test_agent_orchestration import DOC, _services
from tests.test_agent_provider import BEARER, KEY, FakeSDK, final, tool, wire


@pytest.fixture
def configured(tmp_path, monkeypatch):
    for name in ("groq_api_key", "groq_api_key2", "groq_api_key3", "groq_api_key4", "groq_api_key5"):
        monkeypatch.setattr(application.settings, name, KEY if name == "groq_api_key5" else "")
    monkeypatch.setattr(application.settings, "groq_key_policy", "key5_only")
    monkeypatch.setattr(application.settings, "workspace_mode", "local")
    monkeypatch.setattr(application.settings, "local_workspace_token", SecretStr(BEARER))
    monkeypatch.setattr(application.settings, "local_workspace_allowed_hosts", "localhost:8000")
    monkeypatch.setattr(application.settings, "local_workspace_allowed_origins", "http://localhost:3000")
    monkeypatch.setattr(application.settings, "enable_workspace_execution", True)
    monkeypatch.setattr(application.settings, "workspace_db_path", tmp_path / "workspace.sqlite3")
    monkeypatch.setattr(application.settings, "workspace_runs_dir", tmp_path / "runs")
    monkeypatch.setitem(application._state, "pipeline", SimpleNamespace(generator=SimpleNamespace(model="openai/gpt-oss-120b")))
    calls = []
    monkeypatch.setattr(application, "create_agent_tool_registry", lambda: build_tool_registry(_services(calls)))
    sdk = FakeSDK(wire(tool(document_id=DOC)), wire(final(refs=(("document_id", DOC),))))
    monkeypatch.setattr(provider, "AsyncGroq", sdk)
    return sdk, calls


def headers():
    return _headers(token=BEARER)


def test_existing_private_capability_and_create_use_actual_resolver(configured, caplog):
    sdk, calls = configured
    app = application.app
    status = _call(app, "GET", "/system/configuration-status", headers=headers())
    assert status.status_code == 200
    assert status.json()["agent_decision_provider"]["available"] is True
    assert not sdk.requests
    create = _call(app, "POST", "/agent/runs", headers=headers(), body={
        "goal": "Find risk evidence.", "allow_decision_provider_execution": True})
    assert create.status_code == 201, create.text
    run_id = create.json()["run_id"]
    frozen = create.json()["frozen"]
    assert frozen["decision_provider"]["mechanism"] == "native_strict_json_schema"
    assert frozen["allow_provider_tool_execution"] is False
    assert calls == ["read_document"] and len(sdk.requests) == 2
    detail = _call(app, "GET", f"/agent/runs/{run_id}", headers=headers())
    result = _call(app, "GET", f"/agent/runs/{run_id}/results", headers=headers())
    events = _call(app, "GET", f"/agent/runs/{run_id}/events", headers=headers())
    report = _call(app, "GET", f"/agent/runs/{run_id}/evaluation", headers=headers())
    assert detail.json()["state"] == "succeeded" and result.json()["result"]["answer"]
    assert report.status_code == 200 and len(report.json()["metrics"]) == 21
    assert len(sdk.requests) == 2
    repeat = _call(app, "POST", "/agent/runs", headers=headers(), body={
        "goal": "Find risk evidence.", "allow_decision_provider_execution": True})
    assert repeat.json()["run_id"] == run_id and len(sdk.requests) == 2
    combined = status.text + create.text + detail.text + result.text + events.text + report.text + caplog.text
    assert KEY not in combined and BEARER not in combined
    assert "CONTROL_JSON" not in combined and "Request options" not in combined


@pytest.mark.parametrize("missing,unsupported", [(True, False), (False, True)])
def test_unavailable_configuration_is_truthful_without_sdk_calls(configured, monkeypatch, missing, unsupported):
    sdk, calls = configured
    if missing:
        monkeypatch.setattr(application.settings, "groq_api_key5", "")
    if unsupported:
        monkeypatch.setitem(application._state, "pipeline", SimpleNamespace(generator=SimpleNamespace(model="ordinary-chat-only")))
    status = _call(application.app, "GET", "/system/configuration-status", headers=headers())
    assert status.json()["agent_decision_provider"]["available"] is False
    create = _call(application.app, "POST", "/agent/runs", headers=headers(), body={
        "goal": "Check provider availability.", "allow_decision_provider_execution": True})
    detail = _call(application.app, "GET", "/agent/runs/" + create.json()["run_id"], headers=headers())
    assert detail.json()["result"]["failure"]["code"] == "decision_provider_unavailable"
    assert not sdk.requests and not calls


def test_private_execution_and_decision_grants_are_required_before_transport(configured, monkeypatch):
    sdk, calls = configured
    denied = _call(application.app, "POST", "/agent/runs", headers=_headers(token="invalid"), body={"goal": "Find evidence."})
    assert denied.status_code == 401
    monkeypatch.setattr(application.settings, "enable_workspace_execution", False)
    assert _call(application.app, "POST", "/agent/runs", headers=headers(), body={"goal": "Find evidence."}).status_code == 403
    monkeypatch.setattr(application.settings, "enable_workspace_execution", True)
    created = _call(application.app, "POST", "/agent/runs", headers=headers(), body={"goal": "Find evidence."})
    detail = _call(application.app, "GET", "/agent/runs/" + created.json()["run_id"], headers=headers())
    assert detail.json()["result"]["failure"]["code"] == "decision_provider_required"
    assert not sdk.requests and not calls


@pytest.mark.parametrize("secret", [KEY, BEARER])
def test_runtime_secret_create_refuses_before_sqlite_or_response_leak(configured, secret):
    sdk, calls = configured
    response = _call(application.app, "POST", "/agent/runs", headers=headers(), body={"goal": f"Find {secret}."})
    assert response.status_code == 422
    assert secret not in response.text and not sdk.requests and not calls
    assert application._agent_durable_service().list(state=None, page=1, page_size=25).total == 0


@pytest.mark.parametrize("secret", [KEY, BEARER])
def test_runtime_secret_observation_never_enters_api_state_result_events_or_evaluation(configured, monkeypatch, secret, caplog):
    sdk, calls = configured
    monkeypatch.setattr(application, "create_agent_tool_registry", lambda: build_tool_registry(_services(calls, text=secret)))
    created = _call(application.app, "POST", "/agent/runs", headers=headers(), body={
        "goal": "Find risk evidence.", "allow_decision_provider_execution": True})
    run_id = created.json()["run_id"]
    detail = _call(application.app, "GET", f"/agent/runs/{run_id}", headers=headers())
    events = _call(application.app, "GET", f"/agent/runs/{run_id}/events", headers=headers())
    report = _call(application.app, "GET", f"/agent/runs/{run_id}/evaluation", headers=headers())
    assert detail.json()["result"]["failure"]["code"] == "invalid_observation"
    assert detail.json()["result"]["observation_count"] == 0
    assert len(sdk.requests) == 1 and report.status_code == 200
    assert secret not in created.text + detail.text + events.text + report.text + caplog.text
