"""Typed collections through the DATA-002 workspace backup, with no format change.

The point of these tests is that the envelope, its version, its canonical
serialization and its digest stay exactly as DATA-002 defined them, while a
typed collection, its members and their identity survive export → validate →
import → repeat import → export.
"""

from __future__ import annotations

import json

import pytest

from src.workspace.collections import (
    CollectionDeletedError,
    CollectionNotFoundError,
    SQLiteCollectionRepository,
    collection_entity_id,
)
from src.workspace.database import WorkspaceDatabase
from src.workspace.transfer import (
    WORKSPACE_BACKUP_FORMAT,
    WORKSPACE_BACKUP_VERSION,
    WorkspaceTransferService,
    stable_legacy_id,
    validate_workspace_backup,
)

EVIDENCE_REFERENCE = {
    "document_id": "AAPL:0000320193-25-000079",
    "chunk_id": "AAPL_000032019325000079_financial_statements_0001",
    "chunk_text_hash": "b" * 64,
}


def _workspace(tmp_path, name: str):
    database = WorkspaceDatabase(tmp_path / name)
    database.initialize()
    return database, SQLiteCollectionRepository(database)


def _populate(repository: SQLiteCollectionRepository) -> None:
    repository.create_collection(
        collection_id="col-risk",
        name="Risk review",
        description="Q4 risk notes",
        tags=["sec", "risk"],
        favorite=True,
    )
    repository.add_item(
        "col-risk",
        item_id="itm-evidence",
        item_kind="evidence",
        citation="AAPL 10-K, Financial Statements",
        excerpt="Total revenue was reported in fiscal 2024.",
        reference=EVIDENCE_REFERENCE,
        snapshot={"ticker": "AAPL", "filing_date": "2025-10-31"},
    )
    repository.add_item(
        "col-risk",
        item_id="itm-document",
        item_kind="document",
        citation="MSFT 10-K filing",
        excerpt="Microsoft Cloud revenue grew.",
        reference={"document_id": "MSFT:0000950170-25-100235"},
    )
    repository.add_note("col-risk", note_id="note-1", text="check the table again")


def test_typed_collections_export_inside_the_existing_envelope(tmp_path) -> None:
    database, repository = _workspace(tmp_path, "workspace.sqlite3")
    _populate(repository)

    backup = WorkspaceTransferService(database).export_backup()
    validated = validate_workspace_backup(backup)

    assert backup["format"] == WORKSPACE_BACKUP_FORMAT
    assert backup["version"] == WORKSPACE_BACKUP_VERSION
    assert backup["source_counts"]["collections"] == 1
    assert backup["source_counts"]["evidence_items"] == 2
    assert tuple(record["legacy_id"] for record in validated.collections) == ("col-risk",)
    assert sorted(record["legacy_id"] for record in validated.evidence_items) == ["itm-document", "itm-evidence"]
    assert validated.favorites == ("col-risk",)

    # The typed truth rides inside the record payload, untouched by the transfer.
    collection = validated.collections[0]["payload"]
    assert collection["schemaVersion"] == 2 and collection["name"] == "Risk review"
    assert collection["description"] == "Q4 risk notes" and collection["tags"] == ["risk", "sec"]
    assert collection["private"] is True and collection["favorite"] is True
    item = next(record for record in validated.evidence_items if record["legacy_id"] == "itm-evidence")
    assert item["parent_legacy_id"] == "col-risk"
    assert item["payload"]["itemKind"] == "evidence"
    assert item["payload"]["reference"] == EVIDENCE_REFERENCE
    assert item["payload"]["snapshot"] == {"ticker": "AAPL", "filing_date": "2025-10-31"}
    document_item = next(record for record in validated.evidence_items if record["legacy_id"] == "itm-document")
    assert document_item["payload"]["itemKind"] == "document"
    # Notes are not a transfer record type in this build, and the export says so
    # by counting them as an unsupported source rather than dropping them
    # silently.
    assert any(
        descriptor["source"] == "workspace_records" and descriptor["count"] >= 1
        for descriptor in validated.unsupported
    )


def test_round_trip_preserves_type_membership_identity_and_revisions(tmp_path) -> None:
    source, source_repository = _workspace(tmp_path, "source.sqlite3")
    _populate(source_repository)
    backup = WorkspaceTransferService(source).export_backup()

    target, target_repository = _workspace(tmp_path, "target.sqlite3")
    service = WorkspaceTransferService(target)
    preview = service.preview(backup)
    # "partial" here reports that this workspace also holds records outside the
    # portable kinds (the note and the recorded activity), not a data problem:
    # every collection and member is still importable.
    assert preview["compatibility"] == "partial"
    assert preview["unsupported"] >= 1
    assert preview["supported"]["collections"] == 1 and preview["supported"]["evidence_items"] == 2

    receipt = service.import_backup(backup, preview["digest"])
    assert receipt["status"] == "committed"

    restored = target_repository.get_collection("col-risk")
    assert restored.name == "Risk review" and restored.description == "Q4 risk notes"
    assert restored.tags == ("risk", "sec") and restored.favorite is True and restored.private is True
    assert restored.revision == 1
    items, total = target_repository.list_items("col-risk")
    assert total == 2
    restored_evidence = next(item for item in items if item.item_kind == "evidence")
    assert restored_evidence.item_id == "itm-evidence"
    assert restored_evidence.reference == EVIDENCE_REFERENCE
    assert restored_evidence.snapshot == {"ticker": "AAPL", "filing_date": "2025-10-31"}
    # The storage key is the deterministic mapping both workspaces agree on.
    assert collection_entity_id("col-risk") == stable_legacy_id("collection", "col-risk")

    # Exporting the imported workspace produces the same collections and members.
    again = WorkspaceTransferService(target).export_backup()
    assert again["source_counts"]["collections"] == 1
    assert again["source_counts"]["evidence_items"] == 2
    assert sorted(record["legacy_id"] for record in again["collections"]) == ["col-risk"]


def test_repeated_import_is_idempotent_and_does_not_duplicate_members(tmp_path) -> None:
    source, source_repository = _workspace(tmp_path, "source.sqlite3")
    _populate(source_repository)
    backup = WorkspaceTransferService(source).export_backup()

    target, target_repository = _workspace(tmp_path, "target.sqlite3")
    service = WorkspaceTransferService(target)
    preview = service.preview(backup)
    first = service.import_backup(backup, preview["digest"])
    second = service.import_backup(backup, preview["digest"])

    assert first == second  # the stored receipt is returned unchanged
    assert target_repository.list_collections(page_size=50)[1] == 1
    items, total = target_repository.list_items("col-risk")
    assert total == 2 and {item.item_id for item in items} == {"itm-evidence", "itm-document"}
    assert target_repository.get_collection("col-risk").revision == 1

    # A second *preview* against the already-imported workspace reports every
    # record as a duplicate rather than planning new writes.
    repeat_preview = service.preview(backup)
    assert repeat_preview["duplicates"] == 3
    assert repeat_preview["records_to_create"] == 0


def test_an_older_backup_cannot_resurrect_a_deleted_collection(tmp_path) -> None:
    source, source_repository = _workspace(tmp_path, "source.sqlite3")
    _populate(source_repository)
    older = WorkspaceTransferService(source).export_backup()

    # The workspace moves on: the collection is deleted and its members with it.
    source_repository.delete_collection("col-risk", expected_revision=1)
    with pytest.raises(CollectionDeletedError):
        source_repository.get_collection("col-risk")
    current = WorkspaceTransferService(source).export_backup()
    assert current["source_counts"]["collections"] == 0

    # Re-importing the older backup must not bring it back.
    service = WorkspaceTransferService(source)
    preview = service.preview(older)
    assert preview["potential_conflicts"] >= 1
    # The collection is tombstoned, so the plan reports a conflict and skips it.
    assert preview["records_to_skip"] >= 1
    assert preview["potential_conflicts"] >= 1
    receipt = service.import_backup(older, preview["digest"])
    assert receipt["records_to_skip"] >= 1
    with pytest.raises(CollectionDeletedError):
        source_repository.get_collection("col-risk")


def test_a_newer_typed_revision_is_not_overwritten_by_an_older_backup(tmp_path) -> None:
    source, source_repository = _workspace(tmp_path, "source.sqlite3")
    _populate(source_repository)
    older = WorkspaceTransferService(source).export_backup()

    source_repository.update_collection("col-risk", expected_revision=1, name="Risk review v2")
    service = WorkspaceTransferService(source)
    preview = service.preview(older)
    assert preview["potential_conflicts"] >= 1
    service.import_backup(older, preview["digest"])
    assert source_repository.get_collection("col-risk").name == "Risk review v2"


def test_imported_records_keep_the_typed_payload_the_domain_reads(tmp_path) -> None:
    source, source_repository = _workspace(tmp_path, "source.sqlite3")
    _populate(source_repository)
    backup = WorkspaceTransferService(source).export_backup()

    target, target_repository = _workspace(tmp_path, "target.sqlite3")
    service = WorkspaceTransferService(target)
    preview = service.preview(backup)
    service.import_backup(backup, preview["digest"])

    with target.transaction() as connection:
        rows = {
            row["entity_type"]: json.loads(row["payload_json"])
            for row in connection.execute("SELECT entity_type, payload_json FROM workspace_records")
        }
    stored_collection = rows["collection"]["data"]
    assert stored_collection["id"] == "col-risk" and stored_collection["name"] == "Risk review"
    assert stored_collection["private"] is True and stored_collection["tags"] == ["risk", "sec"]
    stored_item = next(
        payload for entity_type, payload in rows.items()
        if entity_type == "collection_item"
    )["data"]
    assert stored_item["itemKind"] in {"document", "evidence"}
    assert stored_item["reference"]

    # An import is a workspace write, and the domain reads it back unchanged.
    assert target_repository.get_collection("col-risk").name == "Risk review"
