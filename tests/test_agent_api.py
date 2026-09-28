"""AGENT-003 private transport and API-001 refusal contracts."""

from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI
from pydantic import SecretStr

from src.api import access
from src.api.routers.agent_runs import create_agent_run_router
from tests.test_agent_durable import _create, _service
from tests.test_agent_orchestration import DOC, _final, _tool


TOKEN = "agent-local-token-0123456789-abcdef"
BODY = {"goal": "Find relevant risk evidence.", "locale": "vi"}


def _headers(*, token=TOKEN, host="localhost:8000", origin="http://localhost:3000"):
    headers = {"Host": host, "Origin": origin, "Idempotency-Key": "agent-http-key"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _call(app, method, path, *, headers=None, body=None, peer="127.0.0.1"):
    async def request():
        transport = httpx.ASGITransport(app=app, client=(peer, 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
            return await client.request(method, path, headers=headers or _headers(), json=body)
    return asyncio.run(request())


def _local(monkeypatch, *, execution=True):
    monkeypatch.setattr(access.settings, "workspace_mode", "local")
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr(TOKEN))
    monkeypatch.setattr(access.settings, "local_workspace_allowed_origins", "http://localhost:3000")
    monkeypatch.setattr(access.settings, "local_workspace_allowed_hosts", "localhost:8000")
    monkeypatch.setattr(access.settings, "enable_workspace_execution", execution)


def test_agent_routes_refuse_public_and_bad_local_access_before_opening_store(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(create_agent_run_router(lambda: (_ for _ in ()).throw(
        AssertionError("private store opened before authorization"))))
    monkeypatch.setattr(access.settings, "workspace_mode", "public")
    assert _call(app, "GET", "/agent/runs").status_code == 404
    assert _call(app, "POST", "/agent/runs", body=BODY).status_code == 404
    _local(monkeypatch, execution=False)
    assert _call(app, "GET", "/agent/runs", headers=_headers(token=None)).status_code == 401
    assert _call(app, "GET", "/agent/runs", headers=_headers(token="wrong")).status_code == 401
    assert _call(app, "GET", "/agent/runs", headers=_headers(host="localhost:8001")).status_code == 403
    assert _call(app, "GET", "/agent/runs", headers=_headers(origin="http://evil")).status_code == 403
    assert _call(app, "GET", "/agent/runs", peer="203.0.113.9").status_code == 403
    assert _call(app, "GET", "/agent/runs", headers={**_headers(),
        "X-Forwarded-For": "127.0.0.1"}, peer="203.0.113.9").status_code == 403
    assert _call(app, "POST", "/agent/runs", body=BODY).status_code == 403
    assert not (tmp_path / "workspace.sqlite3").exists()


def test_agent_http_create_detail_result_events_resume_and_revision(tmp_path, monkeypatch):
    service, repo, calls, _, _ = _service(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Grounded answer.", ("document_id", DOC)),
    ))
    app = FastAPI()
    app.include_router(create_agent_run_router(lambda: service))
    _local(monkeypatch)
    created = _call(app, "POST", "/agent/runs", body=BODY)
    assert created.status_code == 201, created.text
    run_id = created.json()["run_id"]
    assert created.json()["state"] == "queued" and created.headers["etag"] == '"1"'
    assert created.json()["frozen"]["locale"] == "vi"
    assert calls == ["read_document"]
    detail = _call(app, "GET", f"/agent/runs/{run_id}")
    assert detail.status_code == 200 and detail.json()["state"] == "succeeded"
    assert detail.json()["result"]["answer"] == "Grounded answer."
    assert detail.json()["result"]["tool_call_count"] == 1
    assert detail.headers["etag"] == f'"{detail.json()["revision"]}"'
    assert _call(app, "GET", f"/agent/runs/{run_id}/results").json()["result"] == detail.json()["result"]
    listed = _call(app, "GET", "/agent/runs?state=succeeded&page=1&page_size=10")
    assert listed.status_code == 200 and listed.json()["total"] == 1
    replay = _call(app, "POST", "/agent/runs", body=BODY)
    assert replay.json()["run_id"] == run_id and calls == ["read_document"]
    events = _call(app, "GET", f"/agent/runs/{run_id}/events")
    assert events.status_code == 200 and events.headers["content-type"].startswith("text/event-stream")
    assert "id: 1\nevent: created\n" in events.text
    assert "event: agent_decision" in events.text
    assert "Grounded answer" not in events.text
    resumed = _call(app, "GET", f"/agent/runs/{run_id}/events",
                    headers={**_headers(), "Last-Event-ID": "3"})
    assert "id: 1\n" not in resumed.text and "id: 4\n" in resumed.text
    assert _call(app, "GET", f"/agent/runs/{run_id}/events",
                 headers={**_headers(), "Last-Event-ID": "1,2"}).status_code == 422
    assert _call(app, "GET", f"/agent/runs/{run_id}/events?token={TOKEN}",
                 headers=_headers(token=None)).status_code == 401
    assert _call(app, "POST", f"/agent/runs/{run_id}/cancel",
                 headers={**_headers(), "If-Match": f'"{detail.json()["revision"]}"'}).status_code == 409
    assert repo.get_job("job_" + run_id[6:]).state == "succeeded"


def test_agent_http_queued_cancel_validation_and_execution_gate(tmp_path, monkeypatch):
    service, _, calls, _, _ = _service(tmp_path)
    app = FastAPI()
    app.include_router(create_agent_run_router(lambda: service))
    _local(monkeypatch)
    queued = _create(service, key="cancel-api")
    path = f"/agent/runs/{queued.run_id}"
    assert _call(app, "POST", path + "/cancel").status_code == 428
    assert _call(app, "POST", path + "/cancel",
                 headers={**_headers(), "If-Match": "bad"}).status_code == 422
    cancelled = _call(app, "POST", path + "/cancel",
                      headers={**_headers(), "If-Match": '"1"'})
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
    assert _call(app, "POST", path + "/cancel",
                 headers={**_headers(), "If-Match": '"1"'}).status_code == 409
    assert calls == []
    assert _call(app, "GET", "/agent/runs/not-a-run").status_code == 404
    assert _call(app, "GET", "/agent/runs/agent_missing").status_code == 404
    assert _call(app, "POST", "/agent/runs", body={"goal": "bad"}).status_code == 422
    assert _call(app, "POST", "/agent/runs", body={**BODY, "extra": 1}).status_code == 422
    assert _call(app, "POST", "/agent/runs", body=BODY,
                 headers={key: value for key, value in _headers().items()
                          if key != "Idempotency-Key"}).status_code == 422
    _local(monkeypatch, execution=False)
    assert _call(app, "GET", path).status_code == 200
    assert _call(app, "POST", "/agent/runs", body=BODY).status_code == 403
    assert _call(app, "POST", path + "/cancel",
                 headers={**_headers(), "If-Match": '"2"'}).status_code == 403
