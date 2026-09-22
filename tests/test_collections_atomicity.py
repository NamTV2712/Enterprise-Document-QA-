"""R1 — one logical collection mutation is one SQLite write transaction.

The regression these tests pin down: collection deletion used to tombstone its
members and notes through independently committing repository calls *before* the
parent revision was ever checked, so a stale delete removed children and then
failed on the parent. Everything here is deterministic — interleavings are
forced through injected seams and bounded events, never through sleeps.
"""

from __future__ import annotations

import json
import sqlite3
import threading

import pytest

from src.workspace import collections as collections_module
from src.workspace.collections import (
    COLLECTION_ENTITY_TYPE,
    ITEM_ENTITY_TYPE,
    NOTE_ENTITY_TYPE,
    CollectionConflictError,
    CollectionDeletedError,
    CollectionError,
    CollectionLimitError,
    CollectionNotFoundError,
    SQLiteCollectionRepository,
    collection_entity_id,
    item_entity_id,
)
from src.workspace.database import WorkspaceDatabase
from src.workspace.repository import SQLiteVersionedRecordRepository
from src.workspace.transfer import WorkspaceTransferService, validate_workspace_backup

EVIDENCE_REFERENCE = {
    "document_id": "AAPL:0000320193-25-000079",
    "chunk_id": "AAPL_000032019325000079_financial_statements_0001",
}


@pytest.fixture
def workspace(tmp_path):
    path = tmp_path / "workspace.sqlite3"
    database = WorkspaceDatabase(path)
    database.initialize()
    yield path, database, SQLiteCollectionRepository(database)


def _live_records(path, entity_type: str) -> list[sqlite3.Row]:
    """Read the store directly, so a test never asks the code under test."""
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        return list(
            connection.execute(
                "SELECT entity_id, revision, payload_json FROM workspace_records "
                "WHERE entity_type = ? ORDER BY entity_id",
                (entity_type,),
            )
        )


def _tombstones(path, entity_type: str) -> list[str]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        return [str(row["entity_id"]) for row in connection.execute(
            "SELECT entity_id FROM tombstones WHERE entity_type = ? ORDER BY entity_id",
            (entity_type,),
        )]


def _live_members_of(path, collection_id: str) -> list[str]:
    members: list[str] = []
    for entity_type in (ITEM_ENTITY_TYPE, NOTE_ENTITY_TYPE):
        for row in _live_records(path, entity_type):
            payload = json.loads(str(row["payload_json"]))
            data = payload.get("data") if isinstance(payload, dict) else None
            owner = data.get("collectionId") if isinstance(data, dict) else None
            if owner == collection_id:
                # Items carry the transfer's deterministic storage key; notes
                # keep their own identifier.
                stored = str(row["entity_id"])
                member_id = data.get("id") if isinstance(data, dict) else stored
                members.append(f"{entity_type}:{member_id or stored}")
    return sorted(members)


def _populated(workspace, *, revision: int = 2) -> tuple[str, str]:
    """One collection holding an evidence member and a note, at ``revision``."""
    _path, _database, repository = workspace
    repository.create_collection(collection_id="col-1", name="Doomed", description="temporary")
    item = repository.add_item(
        "col-1",
        item_id="itm-1",
        item_kind="evidence",
        citation="AAPL 10-K, Financial Statements",
        excerpt="Total revenue was reported in fiscal 2024.",
        reference=EVIDENCE_REFERENCE,
    )
    note = repository.add_note("col-1", note_id="note-1", text="check the table again")
    if revision == 2:
        repository.update_collection("col-1", expected_revision=1, name="Doomed (renamed)")
    return item.item_id, note.note_id


# 1 — stale deletion preserves parent AND every child -------------------------


def test_a_stale_delete_leaves_the_parent_and_every_member_intact(workspace) -> None:
    path, _database, repository = workspace
    item_id, note_id = _populated(workspace)

    with pytest.raises(CollectionConflictError):
        repository.delete_collection("col-1", expected_revision=1)

    parent = repository.get_collection("col-1")
    assert parent.revision == 2 and parent.name == "Doomed (renamed)"
    assert repository.get_item(item_id).item_id == item_id
    assert repository.get_item(note_id).item_id == note_id
    # And the store itself still holds every record: nothing was half-deleted.
    assert set(_live_members_of(path, "col-1")) == {f"{ITEM_ENTITY_TYPE}:itm-1", f"{NOTE_ENTITY_TYPE}:note-1"}
    assert _tombstones(path, COLLECTION_ENTITY_TYPE) == []
    assert _tombstones(path, ITEM_ENTITY_TYPE) == []
    assert _tombstones(path, NOTE_ENTITY_TYPE) == []


# 2 — stale deletion preserves notes (separate store, separate guarantee) -----


def test_a_stale_delete_leaves_notes_readable_and_untombstoned(workspace) -> None:
    path, _database, repository = workspace
    _populated(workspace)

    with pytest.raises(CollectionConflictError):
        repository.delete_collection("col-1", expected_revision=1)

    notes, total = repository.list_notes("col-1")
    assert total == 1 and notes[0].text == "check the table again"
    assert _tombstones(path, NOTE_ENTITY_TYPE) == []


# 3 — a refused delete records nothing misleading ----------------------------


def test_a_stale_delete_records_no_deletion_activity(workspace) -> None:
    _path, _database, repository = workspace
    _populated(workspace)

    with pytest.raises(CollectionConflictError):
        repository.delete_collection("col-1", expected_revision=1)

    events, _total = repository.list_activity("col-1", page_size=100)
    assert [event.event_type for event in events] == ["collection_updated", "note_added", "item_added", "collection_created"]
    assert "collection_deleted" not in [event.event_type for event in events]


# 4 — a successful delete cascades and says so -------------------------------


def test_a_successful_delete_cascades_atomically_and_records_the_activity(workspace) -> None:
    path, _database, repository = workspace
    item_id, note_id = _populated(workspace)

    receipt = repository.delete_collection("col-1", expected_revision=2)

    assert receipt.operation == "delete_collection" and receipt.revision == 3
    assert _live_members_of(path, "col-1") == []
    assert _tombstones(path, COLLECTION_ENTITY_TYPE) == [collection_entity_id("col-1")]
    assert _tombstones(path, ITEM_ENTITY_TYPE) == [item_entity_id(item_id)]
    assert _tombstones(path, NOTE_ENTITY_TYPE) == [note_id]
    with pytest.raises(CollectionDeletedError):
        repository.get_collection("col-1")
    # Deleting twice is not a conflict: the record is already gone.
    with pytest.raises(CollectionDeletedError):
        repository.delete_collection("col-1", expected_revision=2)
    assert repository.list_activity("col-1", page_size=100)[0][0].event_type == "collection_deleted"


# 5 — a failure in the middle of the cascade rolls everything back -----------


def test_a_failure_during_the_cascade_rolls_everything_back(workspace, monkeypatch) -> None:
    path, _database, repository = workspace
    item_id, note_id = _populated(workspace)

    original_delete_in = SQLiteVersionedRecordRepository.delete_in

    def exploding_delete_in(
        self,
        connection,
        entity_type,
        entity_id,
        *,
        expected_revision,
        timestamp,
    ):
        # The parent tombstone is the last write of the logical operation: make
        # it fail and prove the already-written children do not survive alone.
        if entity_type == COLLECTION_ENTITY_TYPE:
            raise RuntimeError("injected failure before the parent tombstone")
        return original_delete_in(
            self,
            connection,
            entity_type,
            entity_id,
            expected_revision=expected_revision,
            timestamp=timestamp,
        )

    monkeypatch.setattr(SQLiteVersionedRecordRepository, "delete_in", exploding_delete_in)

    with pytest.raises(RuntimeError):
        repository.delete_collection("col-1", expected_revision=2)

    monkeypatch.undo()
    assert repository.get_collection("col-1").revision == 2
    assert repository.get_item(item_id).item_id == item_id
    assert repository.get_item(note_id).item_id == note_id
    assert _live_members_of(path, "col-1") == [f"{ITEM_ENTITY_TYPE}:itm-1", f"{NOTE_ENTITY_TYPE}:note-1"]
    assert _tombstones(path, COLLECTION_ENTITY_TYPE) == []
    assert _tombstones(path, ITEM_ENTITY_TYPE) == []
    assert _tombstones(path, NOTE_ENTITY_TYPE) == []


# 6 — no member can become live under a tombstoned parent --------------------


def test_a_member_cannot_be_created_under_a_tombstoned_parent(workspace, monkeypatch) -> None:
    path, _database, repository = workspace
    repository.create_collection(collection_id="col-1", name="Doomed")
    stale_snapshot = repository.get_collection("col-1")
    repository.delete_collection("col-1", expected_revision=1)

    # Simulate the interleaving: the parent was read while it was live, and the
    # tombstone landed before the member was written.
    monkeypatch.setattr(SQLiteCollectionRepository, "get_collection", lambda self, collection_id: stale_snapshot)

    with pytest.raises(CollectionDeletedError):
        repository.add_item("col-1", item_kind="document", citation="MSFT", excerpt="x", reference={"document_id": "MSFT:1"})
    with pytest.raises(CollectionDeletedError):
        repository.add_note("col-1", text="too late")

    monkeypatch.undo()
    assert _live_members_of(path, "col-1") == []


# 7 — a concurrent delete can never leave a live orphan ----------------------


def test_a_concurrent_delete_cannot_leave_a_live_orphan(workspace, monkeypatch) -> None:
    path, _database, repository = workspace
    repository.create_collection(collection_id="col-1", name="Doomed")

    original_create_in = SQLiteCollectionRepository._create_in
    insert_reached = threading.Event()
    delete_started = threading.Event()
    release_insert = threading.Event()
    errors: list[BaseException] = []

    def gated_create_in(self, connection, entity_type, entity_id, payload, *, timestamp_ms):
        if entity_type == ITEM_ENTITY_TYPE and threading.current_thread().name == "adder":
            insert_reached.set()
            assert release_insert.wait(timeout=5)
        return original_create_in(
            self,
            connection,
            entity_type,
            entity_id,
            payload,
            timestamp_ms=timestamp_ms,
        )

    monkeypatch.setattr(SQLiteCollectionRepository, "_create_in", gated_create_in)

    def add_member() -> None:
        try:
            repository.add_item("col-1", item_kind="document", citation="AAPL", excerpt="x", reference={"document_id": "AAPL:1"})
        except CollectionError as error:
            errors.append(error)

    def delete_collection() -> None:
        assert insert_reached.wait(timeout=5)
        delete_started.set()
        try:
            repository.delete_collection("col-1", expected_revision=1)
        except CollectionError as error:
            errors.append(error)

    adder = threading.Thread(target=add_member, name="adder")
    deleter = threading.Thread(target=delete_collection, name="deleter")
    adder.start()
    deleter.start()
    assert insert_reached.wait(timeout=5)
    assert delete_started.wait(timeout=5)
    release_insert.set()
    adder.join(timeout=20)
    deleter.join(timeout=20)
    assert not adder.is_alive() and not deleter.is_alive()

    monkeypatch.undo()
    # The invariant holds in both orders: either the member was refused, or it
    # was written before the delete and the cascade removed it with the parent.
    with pytest.raises(CollectionDeletedError):
        repository.get_collection("col-1")
    assert _live_members_of(path, "col-1") == []
    assert all(isinstance(error, CollectionError) for error in errors)


# 8 — capacity is decided inside the same transaction as the insert ----------


def test_concurrent_capacity_checks_cannot_exceed_the_limit(workspace, monkeypatch) -> None:
    path, _database, repository = workspace
    repository.create_collection(collection_id="col-1", name="Full")
    monkeypatch.setattr(collections_module, "MAX_ITEMS_PER_COLLECTION", 1)
    start = threading.Barrier(3)
    successes: list[str] = []
    errors: list[BaseException] = []

    def add_member(item_id: str) -> None:
        start.wait(timeout=5)
        try:
            repository.add_item(
                "col-1",
                item_id=item_id,
                item_kind="document",
                citation=item_id,
                excerpt="x",
                reference={"document_id": f"{item_id}:1"},
            )
            successes.append(item_id)
        except CollectionError as error:
            errors.append(error)

    first = threading.Thread(target=add_member, args=("AAPL",), name="capacity-a")
    second = threading.Thread(target=add_member, args=("MSFT",), name="capacity-b")
    first.start()
    second.start()
    start.wait(timeout=5)
    first.join(timeout=20)
    second.join(timeout=20)

    assert not first.is_alive() and not second.is_alive()
    assert len(successes) == 1
    assert len(errors) == 1 and isinstance(errors[0], CollectionLimitError)
    assert len(_live_members_of(path, "col-1")) == 1


# 9 — the committed result is durable after a reopen -------------------------


def test_an_atomic_delete_survives_a_reopen(tmp_path) -> None:
    path = tmp_path / "workspace.sqlite3"
    database = WorkspaceDatabase(path)
    database.initialize()
    repository = SQLiteCollectionRepository(database)
    repository.create_collection(collection_id="col-1", name="Doomed")
    repository.add_item("col-1", item_id="itm-1", item_kind="document", citation="AAPL", excerpt="x", reference={"document_id": "AAPL:1"})
    with pytest.raises(CollectionConflictError):
        repository.delete_collection("col-1", expected_revision=9)
    repository.delete_collection("col-1", expected_revision=1)

    reopened = SQLiteCollectionRepository(WorkspaceDatabase(path))
    with pytest.raises(CollectionDeletedError):
        reopened.get_collection("col-1")
    assert _live_members_of(path, "col-1") == []
    assert _tombstones(path, COLLECTION_ENTITY_TYPE) == [collection_entity_id("col-1")]


# 10 — revisions keep the documented contract --------------------------------


def test_revisions_still_follow_the_documented_contract(workspace) -> None:
    _path, _database, repository = workspace
    created = repository.create_collection(collection_id="col-1", name="Revisions")
    assert created.revision == 1
    updated = repository.update_collection("col-1", expected_revision=1, name="Revisions 2")
    assert updated.revision == 2
    item = repository.add_item("col-1", item_kind="document", citation="AAPL", excerpt="x", reference={"document_id": "AAPL:1"})
    assert item.revision == 1
    replaced = repository.update_collection("col-1", expected_revision=2, description="now with a description")
    assert replaced.revision == 3
    # Each tombstone advances the record it removes, and nothing else.
    with pytest.raises(CollectionConflictError):
        repository.delete_item("col-1", item.item_id, expected_revision=2)
    receipt = repository.delete_item("col-1", item.item_id, expected_revision=1)
    assert receipt.revision == 2
    tombstoned = repository.delete_collection("col-1", expected_revision=3)
    assert tombstoned.revision == 4


# 11 — transfer compatibility is unchanged ----------------------------------


def test_export_and_import_compatibility_is_unchanged(tmp_path) -> None:
    source_path = tmp_path / "source.sqlite3"
    source = WorkspaceDatabase(source_path)
    source.initialize()
    repository = SQLiteCollectionRepository(source)
    _populated((source_path, source, repository), revision=1)

    backup = WorkspaceTransferService(source).export_backup()
    validated = validate_workspace_backup(backup)
    assert validated.collections[0]["legacy_id"] == "col-1"
    # The envelope's portable kinds are unchanged: members ride as evidence
    # items, and notes stay outside the transfer (reported as unsupported).
    assert [record["legacy_id"] for record in validated.evidence_items] == ["itm-1"]

    target_path = tmp_path / "target.sqlite3"
    target = WorkspaceDatabase(target_path)
    target.initialize()
    service = WorkspaceTransferService(target)
    preview = service.preview(backup)
    assert preview["compatibility"] == "partial" and preview["unsupported"] >= 1
    service.import_backup(backup, preview_digest=preview["digest"])
    imported = SQLiteCollectionRepository(target)
    collection = imported.get_collection("col-1")
    assert collection.revision == 1 and collection.item_count == 1
    assert imported.get_item("itm-1").citation == "AAPL 10-K, Financial Statements"
    with pytest.raises(CollectionNotFoundError):
        imported.get_item("note-1")
