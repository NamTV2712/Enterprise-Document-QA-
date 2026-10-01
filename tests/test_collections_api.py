"""Protected DATA-003 HTTP contract: typed collections over the local workspace.

The access class is ``L``: reads are protected too, because a collection holds
private research. These tests drive the real ASGI app with a real SQLite
workspace and assert the status each domain outcome maps to, plus the bounds and
the access boundary itself.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from pydantic import SecretStr

from src.api import access
from src.api import app as app_module


TOKEN = "collections-token-0123456789abcdef"
ORIGIN = "http://localhost:3000"

EVIDENCE_REFERENCE = {
    "document_id": "AAPL:0000320193-25-000079",
    "chunk_id": "AAPL_000032019325000079_financial_statements_0001",
}


async def _request(method: str, path: str, *, json: object | None = None, peer: str = "127.0.0.1", headers: dict[str, str] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app_module.app, client=(peer, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        return await client.request(method, path, json=json, headers=headers)


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


CREATE_BODY = {"name": "Risk review", "description": "Q4", "tags": ["sec"], "favorite": True, "collection_id": "col-http"}


def test_collections_require_local_workspace_access(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "public")
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr(""))
    monkeypatch.setattr(access.settings, "workspace_db_path", tmp_path / "must-not-exist.sqlite3")

    listed = _call("GET", "/collections", headers=_headers())
    created = _call("POST", "/collections", json=CREATE_BODY, headers=_headers())

    # Public mode answers 404 and never opens the private database.
    assert listed.status_code == 404 and created.status_code == 404
    assert not (tmp_path / "must-not-exist.sqlite3").exists()


def test_reads_are_protected_too_and_loopback_is_required(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    assert _call("GET", "/collections", headers=_headers(token=None)).status_code == 401
    assert _call("GET", "/collections", headers=_headers(), peer="203.0.113.7").status_code == 403
    assert _call("GET", "/collections", headers=_headers()).status_code == 200


def test_collection_lifecycle_over_http(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    created = _call("POST", "/collections", json=CREATE_BODY, headers=_headers())
    assert created.status_code == 200
    body = created.json()
    assert body["collection_id"] == "col-http" and body["revision"] == 1
    assert body["tags"] == ["sec"] and body["favorite"] is True and body["private"] is True
    assert body["item_count"] == 0

    fetched = _call("GET", "/collections/col-http", headers=_headers())
    assert fetched.status_code == 200 and fetched.json()["name"] == "Risk review"

    updated = _call("PATCH", "/collections/col-http", json={"revision": 1, "name": "Risk review v2"}, headers=_headers())
    assert updated.status_code == 200 and updated.json()["revision"] == 2

    stale = _call("PATCH", "/collections/col-http", json={"revision": 1, "name": "Stale"}, headers=_headers())
    assert stale.status_code == 409

    listed = _call("GET", "/collections?sort=name&direction=asc", headers=_headers())
    assert listed.status_code == 200
    assert listed.json()["total"] == 1 and listed.json()["items"][0]["name"] == "Risk review v2"

    with_kind = _call("GET", "/collections?tags=sec&favorite=true", headers=_headers())
    assert with_kind.json()["total"] == 1
    without = _call("GET", "/collections?favorite=false", headers=_headers())
    assert without.json()["total"] == 0


def test_items_and_notes_over_http_with_real_statuses(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    _call("POST", "/collections", json=CREATE_BODY, headers=_headers())

    added = _call(
        "POST",
        "/collections/col-http/items",
        json={
            "item_id": "itm-http",
            "item_kind": "evidence",
            "citation": "AAPL 10-K, Financial Statements",
            "excerpt": "Total revenue was reported in fiscal 2024.",
            "reference": EVIDENCE_REFERENCE,
            "snapshot": {"ticker": "AAPL"},
        },
        headers=_headers(),
    )
    assert added.status_code == 200
    assert added.json()["item_kind"] == "evidence" and added.json()["reference"] == EVIDENCE_REFERENCE

    # An incompatible reference is refused, never coerced into another kind.
    refused = _call(
        "POST",
        "/collections/col-http/items",
        json={"item_kind": "document", "citation": "x", "excerpt": "y", "reference": {"ticker": "AAPL"}},
        headers=_headers(),
    )
    assert refused.status_code == 422 and "document_id" in refused.json()["detail"]
    unsupported = _call(
        "POST",
        "/collections/col-http/items",
        json={"item_kind": "spreadsheet", "citation": "x", "excerpt": "y", "reference": {}},
        headers=_headers(),
    )
    assert unsupported.status_code == 422

    items = _call("GET", "/collections/col-http/items?kind=evidence", headers=_headers())
    assert items.json()["total"] == 1
    bad_kind = _call("GET", "/collections/col-http/items?kind=spreadsheet", headers=_headers())
    assert bad_kind.status_code == 422
    over_page = _call("GET", "/collections/col-http/items?page_size=101", headers=_headers())
    assert over_page.status_code == 422

    note = _call(
        "POST",
        "/collections/col-http/notes",
        json={"text": "check the table", "evidence_ref": EVIDENCE_REFERENCE},
        headers=_headers(),
    )
    assert note.status_code == 200 and note.json()["evidence_ref"] == EVIDENCE_REFERENCE
    edited = _call(
        "PATCH",
        f"/collections/col-http/notes/{note.json()['note_id']}",
        json={"revision": 1, "text": "checked"},
        headers=_headers(),
    )
    assert edited.status_code == 200 and edited.json()["revision"] == 2
    conflict = _call(
        "PATCH",
        f"/collections/col-http/notes/{note.json()['note_id']}",
        json={"revision": 1, "text": "stale"},
        headers=_headers(),
    )
    assert conflict.status_code == 409

    # A note is an item of kind note for the mixed-asset listing.
    notes_as_items = _call("GET", "/collections/col-http/items?kind=note", headers=_headers())
    assert notes_as_items.json()["total"] == 1

    deleted = _call("DELETE", "/collections/col-http/items/itm-http?revision=1", headers=_headers())
    assert deleted.status_code == 200 and deleted.json()["operation"] == "delete_item"
    # Removing it again reports it as gone rather than inventing a conflict.
    again = _call("DELETE", "/collections/col-http/items/itm-http?revision=2", headers=_headers())
    assert again.status_code == 410


def test_parent_ownership_and_unknown_ids_over_http(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    _call("POST", "/collections", json=CREATE_BODY, headers=_headers())
    _call("POST", "/collections", json={"name": "Other", "collection_id": "col-other"}, headers=_headers())
    added = _call(
        "POST",
        "/collections/col-http/items",
        json={"item_kind": "document", "citation": "MSFT 10-K", "excerpt": "x", "reference": {"document_id": "MSFT:1"}},
        headers=_headers(),
    )

    misplaced = _call("DELETE", f"/collections/col-other/items/{added.json()['item_id']}?revision=1", headers=_headers())
    assert misplaced.status_code == 404

    unknown = _call("GET", "/collections/col-nope", headers=_headers())
    assert unknown.status_code == 404
    unknown_items = _call("GET", "/collections/col-nope/items", headers=_headers())
    assert unknown_items.status_code == 404


def test_activity_and_export_over_http(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    _call("POST", "/collections", json=CREATE_BODY, headers=_headers())
    _call(
        "POST",
        "/collections/col-http/items",
        json={"item_kind": "evidence", "citation": "AAPL 10-K", "excerpt": "excerpt", "reference": EVIDENCE_REFERENCE},
        headers=_headers(),
    )
    _call("PATCH", "/collections/col-http", json={"revision": 1, "favorite": False}, headers=_headers())

    activity = _call("GET", "/collections/col-http/activity", headers=_headers())
    assert activity.status_code == 200
    events = [item["event_type"] for item in activity.json()["items"]]
    assert events == ["collection_updated", "item_added", "collection_created"]

    exported = _call("GET", "/collections/col-http/export", headers=_headers())
    payload = exported.json()
    assert payload["id"] == "col-http" and payload["favorite"] is False
    assert payload["items"][0]["reference"] == EVIDENCE_REFERENCE

    markdown = _call("GET", "/collections/col-http/export?format=markdown", headers=_headers())
    assert markdown.status_code == 200 and markdown.json()["format"] == "markdown"
    assert markdown.json()["content"].startswith("# Risk review")

    bad_format = _call("GET", "/collections/col-http/export?format=pdf", headers=_headers())
    assert bad_format.status_code == 422

    # Export is a read: it changes neither the revision nor the activity.
    assert _call("GET", "/collections/col-http", headers=_headers()).json()["revision"] == 2
    assert _call("GET", "/collections/col-http/activity", headers=_headers()).json()["total"] == 3


def test_unsupported_sort_and_malformed_bodies_are_rejected(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    assert _call("GET", "/collections?sort=owner", headers=_headers()).status_code == 422
    assert _call("GET", "/collections?direction=sideways", headers=_headers()).status_code == 422
    # A missing name, an over-long description and malformed ids are refused by
    # the request model before any workspace write happens.
    assert _call("POST", "/collections", json={"description": "no name"}, headers=_headers()).status_code == 422
    assert _call("POST", "/collections", json={"name": "x" * 300}, headers=_headers()).status_code == 422
    assert _call("POST", "/collections", json={"name": "ok", "collection_id": "../etc/passwd"}, headers=_headers()).status_code == 422


def test_a_deleted_collection_is_gone_over_http(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    _call("POST", "/collections", json=CREATE_BODY, headers=_headers())
    receipt = _call("DELETE", "/collections/col-http?revision=1", headers=_headers())
    assert receipt.status_code == 200 and receipt.json()["revision"] == 2

    assert _call("GET", "/collections/col-http", headers=_headers()).status_code == 410
    resurrect = _call("POST", "/collections", json=CREATE_BODY, headers=_headers())
    assert resurrect.status_code == 410
    assert _call("GET", "/collections", headers=_headers()).json()["total"] == 0


@pytest.mark.parametrize("path", ["/collections", "/collections/col-1/items", "/collections/col-1/notes", "/collections/col-1/activity"])
def test_every_collection_route_refuses_a_public_deployment(monkeypatch, tmp_path, path) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "public")
    monkeypatch.setattr(access.settings, "local_workspace_token", SecretStr(""))
    monkeypatch.setattr(access.settings, "workspace_db_path", tmp_path / "never.sqlite3")
    assert _call("GET", path, headers=_headers()).status_code in (404, 401)
