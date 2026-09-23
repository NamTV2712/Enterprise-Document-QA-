"""Protected DATA-002 HTTP contract tests."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from src.api import access
from src.api import app as app_module
from src.api.routers import workspace_transfer as workspace_transfer_router
from src.workspace.transfer import build_workspace_backup


TOKEN = "workspace-transfer-token-0123456789abcdef"
ORIGIN = "http://localhost:3000"


def _empty_backup() -> dict:
    return build_workspace_backup(
        conversations=[],
        collections=[],
        evidence_items=[],
        favorites=[],
        tombstones=[],
        exported_at="2025-01-01T00:00:00Z",
    )


async def _request(method: str, path: str, *, json: object | None = None, content: str | None = None, peer: str = "127.0.0.1", headers: dict[str, str] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app_module.app, client=(peer, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        return await client.request(method, path, json=json, content=content, headers=headers)


def _call(method: str, path: str, **kwargs) -> httpx.Response:
    return asyncio.run(_request(method, path, **kwargs))


def _headers(*, token: str | None = TOKEN) -> dict[str, str]:
    headers = {"Host": "localhost:8000", "Origin": ORIGIN}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _local(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "local")
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr(TOKEN))
    monkeypatch.setattr(access.settings, "local_workspace_allowed_origins", ORIGIN)
    monkeypatch.setattr(access.settings, "local_workspace_allowed_hosts", "localhost,127.0.0.1,[::1]")
    monkeypatch.setattr(access.settings, "workspace_db_path", tmp_path / "workspace.sqlite3")


NOW = 1_735_689_600_000


def _conversation_record(*, legacy_id: str = "conversation-1", revision: int = 2) -> dict:
    payload = {
        "schemaVersion": 4,
        "id": legacy_id,
        "sessionId": "session-1",
        "title": "Revenue review",
        "titleMode": "custom",
        "revision": revision,
        "createdAt": NOW,
        "updatedAt": NOW + revision,
        "messages": [
            {"id": "question-1", "role": "user", "content": "How did revenue change?"},
            {"id": "answer-1", "role": "assistant", "content": "Revenue increased [1]."},
        ],
        "draft": "",
        "bookmarkedMessageIds": [],
    }
    return {
        "legacy_id": legacy_id,
        "schema_version": 4,
        "revision": revision,
        "created_at": NOW,
        "updated_at": NOW + revision,
        "payload": payload,
    }


def test_public_mode_cannot_preview_import_or_export_private_workspace(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "public")
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr(""))
    monkeypatch.setattr(access.settings, "workspace_db_path", tmp_path / "must-not-exist.sqlite3")
    backup = _empty_backup()

    responses = [
        _call("POST", "/workspace/imports/preview", json=backup, headers=_headers()),
        _call("POST", "/workspace/imports", json={"backup": backup, "preview_digest": backup["digest"]}, headers=_headers()),
        _call("GET", "/workspace/export", headers=_headers()),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404]
    assert not (tmp_path / "must-not-exist.sqlite3").exists()


def test_local_routes_require_api001_token_and_loopback(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    backup = _empty_backup()

    missing = _call("POST", "/workspace/imports/preview", json=backup, headers=_headers(token=None))
    remote = _call("POST", "/workspace/imports/preview", json=backup, peer="198.51.100.8", headers={**_headers(), "Forwarded": "for=127.0.0.1;host=localhost"})

    assert missing.status_code == 401
    assert remote.status_code == 403


def test_local_preview_import_export_contract(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    backup = _empty_backup()

    preview = _call("POST", "/workspace/imports/preview", json=backup, headers=_headers())
    committed = _call(
        "POST",
        "/workspace/imports",
        json={"backup": backup, "preview_digest": backup["digest"]},
        headers=_headers(),
    )
    exported = _call("GET", "/workspace/export", headers=_headers())

    assert preview.status_code == 200
    assert preview.json()["digest"] == backup["digest"]
    assert committed.status_code == 200
    assert committed.json()["status"] == "committed"
    assert exported.status_code == 200
    assert exported.json()["format"] == backup["format"]


def test_http_import_is_idempotent_with_a_stable_receipt(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    backup = build_workspace_backup(
        conversations=[_conversation_record()],
        collections=[],
        evidence_items=[],
        favorites=[],
        tombstones=[],
    )

    preview = _call("POST", "/workspace/imports/preview", json=backup, headers=_headers())
    first = _call(
        "POST",
        "/workspace/imports",
        json={"backup": backup, "preview_digest": backup["digest"]},
        headers=_headers(),
    )
    second = _call(
        "POST",
        "/workspace/imports",
        json={"backup": backup, "preview_digest": backup["digest"]},
        headers=_headers(),
    )

    assert preview.status_code == 200
    assert preview.json()["records_to_create"] == 1
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["status"] == "committed"
    assert first.json()["duplicates"] == 0


def test_unpaired_surrogate_backup_fails_closed_with_400(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    backup = build_workspace_backup(
        conversations=[_conversation_record()],
        collections=[],
        evidence_items=[],
        favorites=[],
        tombstones=[],
    )
    backup["conversations"][0]["payload"]["title"] = json.loads('"bad \\ud800 title"')
    # The wire form is the ASCII-escaped JSON a browser would transmit; the
    # server must reject the decoded surrogate before touching storage.
    body = json.dumps(backup)
    surrogate_headers = {**_headers(), "Content-Type": "application/json"}

    preview = _call("POST", "/workspace/imports/preview", content=body, headers=surrogate_headers)
    imported = _call(
        "POST",
        "/workspace/imports",
        content=json.dumps({"backup": backup, "preview_digest": backup["digest"]}),
        headers=surrogate_headers,
    )

    assert preview.status_code == 400
    assert "surrogate" in preview.json()["detail"]
    assert imported.status_code == 400


def test_oversized_import_stream_stops_at_the_first_chunk_over_limit(monkeypatch) -> None:
    monkeypatch.setattr(workspace_transfer_router, "MAX_BACKUP_BYTES", 8)

    class ChunkedRequest:
        headers = {"content-length": "8"}  # Deliberately under-reports the stream.

        def __init__(self) -> None:
            self.chunks_read = 0

        async def stream(self):
            for chunk in (b"12345", b"6789", b"must-not-be-read"):
                self.chunks_read += 1
                yield chunk

    request = ChunkedRequest()

    with pytest.raises(HTTPException) as captured:
        asyncio.run(workspace_transfer_router._read_bounded_body(request))

    assert captured.value.status_code == 413
    assert request.chunks_read == 2


def test_oversized_content_length_is_rejected_without_reading_the_stream(monkeypatch) -> None:
    monkeypatch.setattr(workspace_transfer_router, "MAX_BACKUP_BYTES", 8)

    class ChunkedRequest:
        headers = {"content-length": "9"}

        async def stream(self):
            raise AssertionError("oversized declared body should not be read")
            yield b""  # Keep this an async generator.

    with pytest.raises(HTTPException) as captured:
        asyncio.run(workspace_transfer_router._read_bounded_body(ChunkedRequest()))

    assert captured.value.status_code == 413


def test_body_at_the_limit_is_accepted_across_chunks(monkeypatch) -> None:
    monkeypatch.setattr(workspace_transfer_router, "MAX_BACKUP_BYTES", 8)

    class ChunkedRequest:
        headers = {"content-length": "8"}

        async def stream(self):
            yield b"12345"
            yield b"678"

    assert (
        asyncio.run(workspace_transfer_router._read_bounded_body(ChunkedRequest()))
        == b"12345678"
    )


def test_import_endpoints_reject_oversized_bodies_before_opening_workspace(
    monkeypatch,
    tmp_path,
) -> None:
    _local(monkeypatch, tmp_path)
    monkeypatch.setattr(workspace_transfer_router, "MAX_BACKUP_BYTES", 8)
    headers = {**_headers(), "Content-Type": "application/json"}

    preview = _call(
        "POST",
        "/workspace/imports/preview",
        content="123456789",
        headers=headers,
    )
    imported = _call(
        "POST",
        "/workspace/imports",
        content="123456789",
        headers=headers,
    )

    assert preview.status_code == imported.status_code == 413
    assert not (tmp_path / "workspace.sqlite3").exists()
