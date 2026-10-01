"""DATA-002 portable backup, preview, transactional import, and export tests."""

from __future__ import annotations

import copy
import json

import pytest

from src.workspace.database import WorkspaceDatabase
from src.workspace.transfer import (
    MAX_BACKUP_BYTES,
    WORKSPACE_BACKUP_VERSION,
    WorkspaceTransferError,
    WorkspaceTransferService,
    build_workspace_backup,
    compute_backup_digest,
    stable_legacy_id,
    validate_workspace_backup,
)


NOW = 1_735_689_600_000


def _conversation(
    *,
    legacy_id: str = "conversation-1",
    revision: int = 2,
    answer: str = "Revenue increased [1].",
) -> dict:
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
            {
                "id": "answer-1",
                "role": "assistant",
                "content": answer,
                "sources": [
                    {
                        "citation": "AAPL 10-K [Source 1]",
                        "chunk_id": "chunk-identity-1",
                        "document_id": "document-identity-1",
                        "document_revision": "doc-revision-7",
                        "source_set_revision": "source-set-3",
                        "chunk_text_hash": "sha256:source-content",
                        "text": "Exact source excerpt",
                        "text_preview": "Exact source excerpt",
                        "score": 0.91,
                    }
                ],
            },
        ],
        "draft": "",
        "bookmarkedMessageIds": ["answer-1"],
        "tags": ["revenue"],
        "notes": [{"id": "note-1", "text": "Compare next year", "createdAt": NOW}],
        "variants": [
            {
                "id": "variant-1",
                "originMessageId": "answer-1",
                "content": "Alternative answer [1].",
                "sources": [
                    {
                        "citation": "AAPL 10-K [Source 1]",
                        "chunk_id": "chunk-identity-1",
                        "document_id": "document-identity-1",
                    }
                ],
            }
        ],
    }
    return {
        "legacy_id": legacy_id,
        "schema_version": 4,
        "revision": revision,
        "created_at": NOW,
        "updated_at": NOW + revision,
        "payload": payload,
    }


def _collection(*, schema_version: int = 2) -> dict:
    payload = {
        "id": "collection-1",
        "name": "Revenue evidence",
        "createdAt": NOW,
        "updatedAt": NOW + 10,
    }
    if schema_version == 2:
        payload["schemaVersion"] = 2
    return {
        "legacy_id": "collection-1",
        "schema_version": schema_version,
        "revision": 1,
        "created_at": NOW,
        "updated_at": NOW + 10,
        "payload": payload,
    }


def _evidence_item(*, schema_version: int = 2) -> dict:
    return {
        "legacy_id": "evidence-1",
        "parent_legacy_id": "collection-1",
        "schema_version": schema_version,
        "revision": 1,
        "created_at": NOW + 5,
        "updated_at": NOW + 5,
        "payload": {
            "id": "evidence-1",
            "citation": "AAPL 10-K [Source 1]",
            "excerpt": "Exact source excerpt",
            "chunkId": "chunk-identity-1",
            "sourceConversationId": "conversation-1",
            "sourceMessageId": "answer-1",
            "documentId": "document-identity-1",
            "documentRevision": "doc-revision-7",
            "sourceSetRevision": "source-set-3",
            "chunkTextHash": "sha256:source-content",
            "note": "Use in the revenue memo",
            "savedAt": NOW + 5,
        },
    }


def _backup(
    *,
    conversations: list[dict] | None = None,
    collections: list[dict] | None = None,
    evidence_items: list[dict] | None = None,
    favorites: list[str] | None = None,
    tombstones: list[dict] | None = None,
) -> dict:
    return build_workspace_backup(
        conversations=[_conversation()] if conversations is None else conversations,
        collections=[_collection()] if collections is None else collections,
        evidence_items=[_evidence_item()] if evidence_items is None else evidence_items,
        favorites=["collection-1"] if favorites is None else favorites,
        tombstones=[] if tombstones is None else tombstones,
        exported_at="2025-01-01T00:00:00Z",
    )


@pytest.fixture
def service(tmp_path) -> WorkspaceTransferService:
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    database.initialize()
    return WorkspaceTransferService(database)


def _count(database: WorkspaceDatabase, table: str) -> int:
    with database.connection() as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def test_backup_schema_digest_and_supported_legacy_research_are_validated() -> None:
    backup = _backup(collections=[_collection(schema_version=1)], evidence_items=[_evidence_item(schema_version=1)])
    validated = validate_workspace_backup(backup)

    assert validated.digest == compute_backup_digest(backup)
    assert backup["version"] == WORKSPACE_BACKUP_VERSION
    assert backup["source_schemas"]["conversations"] == [4]
    assert backup["source_schemas"]["evidence_collections"] == [1]
    assert backup["source_counts"] == {
        "conversations": 1,
        "collections": 1,
        "evidence_items": 1,
        "favorites": 1,
        "tombstones": 0,
        "unsupported": 0,
    }
    assert validated.conversations[0]["payload"]["variants"][0]["id"] == "variant-1"
    assert validated.evidence_items[0]["payload"]["note"] == "Use in the revenue memo"


def test_digest_is_deterministic_and_excludes_only_export_timestamp() -> None:
    first = _backup()
    second = copy.deepcopy(first)
    second["exported_at"] = "2026-02-03T04:05:06Z"

    assert compute_backup_digest(first) == compute_backup_digest(second)
    second["conversations"][0]["payload"]["messages"][1]["content"] = "Changed"
    assert compute_backup_digest(first) != compute_backup_digest(second)


def test_preview_is_non_mutating_and_reports_mappings(service: WorkspaceTransferService) -> None:
    backup = _backup()
    before = {
        table: _count(service.database, table)
        for table in ("workspace_records", "tombstones", "workspace_imports")
    }

    preview = service.preview(backup)

    after = {
        table: _count(service.database, table)
        for table in ("workspace_records", "tombstones", "workspace_imports")
    }
    assert before == after == {"workspace_records": 0, "tombstones": 0, "workspace_imports": 0}
    assert preview["records_to_create"] == 3
    assert preview["mapping_required"] == 3
    assert preview["compatibility"] == "compatible"


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda backup: backup.update(version=2), "version"),
        (lambda backup: backup.update(digest="0" * 64), "digest"),
        (lambda backup: backup["conversations"][0].update(legacy_id="../escape"), "identifier"),
        (lambda backup: backup["source_counts"].update(conversations=99), "counts"),
    ],
)
def test_malformed_and_future_backups_fail_safely(mutator, message: str) -> None:
    backup = _backup()
    mutator(backup)
    with pytest.raises(WorkspaceTransferError, match=message):
        validate_workspace_backup(backup)


def test_import_is_idempotent_and_receipt_mapping_is_stable(service: WorkspaceTransferService) -> None:
    backup = _backup()
    preview = service.preview(backup)
    first = service.import_backup(backup, preview["digest"])
    second = service.import_backup(backup, preview["digest"])

    assert first == second
    assert first["status"] == "committed"
    assert _count(service.database, "workspace_records") == 3
    assert _count(service.database, "workspace_imports") == 1
    mapping = next(item for item in first["mappings"] if item["legacy_id"] == "conversation-1")
    assert mapping["workspace_id"] == stable_legacy_id("conversation", "conversation-1")


def test_transaction_rolls_back_every_record_and_receipt(tmp_path) -> None:
    database = WorkspaceDatabase(tmp_path / "rollback.sqlite3")
    database.initialize()

    def fail(_action: str, applied: int) -> None:
        if applied == 1:
            raise RuntimeError("injected failure")

    service = WorkspaceTransferService(database, failure_injector=fail)
    backup = _backup()
    with pytest.raises(RuntimeError, match="injected failure"):
        service.import_backup(backup, backup["digest"])

    assert _count(database, "workspace_records") == 0
    assert _count(database, "tombstones") == 0
    assert _count(database, "workspace_imports") == 0


def test_duplicates_revision_conflicts_and_newer_source_revision_are_explicit(service: WorkspaceTransferService) -> None:
    initial = _backup(collections=[], evidence_items=[], favorites=[])
    service.import_backup(initial, initial["digest"])

    duplicate = service.preview(initial)
    assert duplicate["duplicates"] == 1
    assert duplicate["records_to_skip"] == 1

    older_changed = _backup(
        conversations=[_conversation(revision=1, answer="Older changed answer")],
        collections=[],
        evidence_items=[],
        favorites=[],
    )
    conflict = service.preview(older_changed)
    assert conflict["potential_conflicts"] == 1
    assert conflict["records_to_skip"] == 1

    newer = _backup(
        conversations=[_conversation(revision=3, answer="Newer answer")],
        collections=[],
        evidence_items=[],
        favorites=[],
    )
    replacement = service.preview(newer)
    assert replacement["records_to_update"] == 1
    service.import_backup(newer, newer["digest"])
    exported = service.export_backup()
    assert exported["conversations"][0]["revision"] == 3
    assert exported["conversations"][0]["payload"]["messages"][1]["content"] == "Newer answer"


def test_tombstones_are_preserved_and_never_resurrected(service: WorkspaceTransferService) -> None:
    deleted = _backup(
        conversations=[],
        collections=[],
        evidence_items=[],
        favorites=[],
        tombstones=[
            {
                "kind": "conversation",
                "legacy_id": "conversation-1",
                "schema_version": 1,
                "revision": 5,
                "deleted_at": NOW + 20,
            }
        ],
    )
    service.import_backup(deleted, deleted["digest"])
    live = _backup(collections=[], evidence_items=[], favorites=[])

    preview = service.preview(live)
    assert preview["potential_conflicts"] == 1
    assert preview["records_to_create"] == 0
    service.import_backup(live, live["digest"])
    assert _count(service.database, "workspace_records") == 0
    assert _count(service.database, "tombstones") == 1
    exported = service.export_backup()
    assert exported["tombstones"][0]["legacy_id"] == "conversation-1"
    assert exported["tombstones"][0]["revision"] == 5


def test_workspace_export_round_trip_preserves_answer_source_and_evidence_identity(service: WorkspaceTransferService, tmp_path) -> None:
    source = _backup()
    service.import_backup(source, source["digest"])
    exported = service.export_backup()
    validated = validate_workspace_backup(exported)

    conversation = validated.conversations[0]["payload"]
    evidence = validated.evidence_items[0]["payload"]
    assert conversation["messages"][1]["id"] == "answer-1"
    assert conversation["messages"][1]["sources"][0]["chunk_id"] == "chunk-identity-1"
    assert conversation["variants"][0]["sources"][0]["document_id"] == "document-identity-1"
    assert evidence["sourceMessageId"] == "answer-1"
    assert evidence["chunkTextHash"] == "sha256:source-content"
    assert validated.favorites == ("collection-1",)

    second_database = WorkspaceDatabase(tmp_path / "roundtrip.sqlite3")
    second_database.initialize()
    second = WorkspaceTransferService(second_database)
    receipt = second.import_backup(exported, exported["digest"])
    assert receipt["records_to_create"] == 3
    assert validate_workspace_backup(second.export_backup()).evidence_items[0]["payload"] == evidence


def test_bounds_and_secret_fields_or_values_are_rejected(monkeypatch) -> None:
    secret = "workspace-secret-value-0123456789"
    monkeypatch.setattr("src.workspace.transfer.settings.local_workspace_token", secret)
    with pytest.raises(WorkspaceTransferError, match="credential value"):
        build_workspace_backup(
            conversations=[_conversation(answer=f"Do not export {secret}")],
            collections=[], evidence_items=[], favorites=[], tombstones=[]
        )

    record = _conversation()
    record["payload"]["api_key"] = "redacted"
    with pytest.raises(WorkspaceTransferError, match="credential field"):
        build_workspace_backup(
            conversations=[record], collections=[], evidence_items=[], favorites=[], tombstones=[]
        )

    oversized = _conversation(answer="x" * (MAX_BACKUP_BYTES + 1))
    with pytest.raises(WorkspaceTransferError, match="size limit|25 MiB"):
        build_workspace_backup(
            conversations=[oversized], collections=[], evidence_items=[], favorites=[], tombstones=[]
        )


def test_preview_digest_is_required_for_commit(service: WorkspaceTransferService) -> None:
    backup = _backup()
    with pytest.raises(WorkspaceTransferError, match="preview digest"):
        service.import_backup(backup, "f" * 64)
    assert _count(service.database, "workspace_imports") == 0


def test_import_receipt_contains_no_research_payload_or_secret(service: WorkspaceTransferService) -> None:
    backup = _backup()
    receipt = service.import_backup(backup, backup["digest"])
    encoded = json.dumps(receipt)
    assert "How did revenue change" not in encoded
    assert "Exact source excerpt" not in encoded
    assert "authorization" not in encoded.casefold()
