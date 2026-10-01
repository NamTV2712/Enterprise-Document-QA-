"""Typed collection persistence: revisions, conflicts, tombstones, membership.

Everything here runs against a real SQLite workspace database, including a
reopen, so "restart" means the same thing the application means by it.
"""

from __future__ import annotations

import json

import pytest

from src.workspace.collections import (
    ACTIVITY_ENTITY_TYPE,
    COLLECTION_ENTITY_TYPE,
    ITEM_ENTITY_TYPE,
    NOTE_ENTITY_TYPE,
    MAX_ACTIVITY_PER_COLLECTION,
    MAX_COLLECTIONS,
    MAX_ITEMS_PER_COLLECTION,
    MAX_NOTES_PER_COLLECTION,
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

EVIDENCE_REFERENCE = {
    "document_id": "AAPL:0000320193-25-000079",
    "chunk_id": "AAPL_000032019325000079_financial_statements_0001",
}


@pytest.fixture
def workspace(tmp_path):
    path = tmp_path / "workspace.sqlite3"
    database = WorkspaceDatabase(path)
    database.initialize()
    yield path, SQLiteCollectionRepository(database)


@pytest.fixture
def repository(workspace) -> SQLiteCollectionRepository:
    return workspace[1]


def test_create_read_update_and_readback_after_reopen(workspace) -> None:
    path, repository = workspace
    created = repository.create_collection(
        collection_id="col-risk",
        name="Risk review",
        description="Q4 risk notes",
        tags=["sec", "risk"],
        favorite=True,
    )
    assert (created.collection_id, created.revision, created.item_count) == ("col-risk", 1, 0)
    assert created.private is True and created.tags == ("risk", "sec")

    updated = repository.update_collection("col-risk", expected_revision=1, name="Risk review (final)", favorite=False)
    assert (updated.revision, updated.name, updated.favorite) == (2, "Risk review (final)", False)

    # A fresh repository over the same file sees the committed state.
    reopened = SQLiteCollectionRepository(WorkspaceDatabase(path))
    again = reopened.get_collection("col-risk")
    assert (again.revision, again.name, again.description) == (2, "Risk review (final)", "Q4 risk notes")
    assert again.tags == ("risk", "sec")


def test_a_stale_revision_is_a_conflict_and_never_overwrites(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="First")
    repository.update_collection("col-1", expected_revision=1, name="Second")

    with pytest.raises(CollectionConflictError):
        repository.update_collection("col-1", expected_revision=1, name="Stale write")
    assert repository.get_collection("col-1").name == "Second"

    with pytest.raises(CollectionConflictError):
        repository.update_collection("col-1", expected_revision=9, name="Ahead of the store")
    assert repository.get_collection("col-1").name == "Second"


def test_missing_and_deleted_records_are_distinguishable(workspace) -> None:
    _path, repository = workspace
    with pytest.raises(CollectionNotFoundError):
        repository.get_collection("col-missing")

    repository.create_collection(collection_id="col-1", name="Doomed")
    receipt = repository.delete_collection("col-1", expected_revision=1)
    assert receipt.operation == "delete_collection" and receipt.revision == 2 and receipt.deleted_at
    with pytest.raises(CollectionDeletedError):
        repository.get_collection("col-1")
    with pytest.raises(CollectionDeletedError):
        repository.update_collection("col-1", expected_revision=2, name="Resurrect")
    with pytest.raises(CollectionDeletedError):
        repository.delete_collection("col-1", expected_revision=1)


def test_item_membership_is_validated_and_identity_is_caller_owned(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="Evidence")

    item = repository.add_item(
        "col-1",
        item_id="itm-evidence",
        item_kind="evidence",
        citation="AAPL 10-K, Financial Statements",
        excerpt="Total revenue was reported in fiscal 2024.",
        reference=EVIDENCE_REFERENCE,
        snapshot={"ticker": "AAPL", "filing_date": "2025-10-31"},
    )
    assert item.item_id == "itm-evidence" and item.item_kind == "evidence" and item.revision == 1
    assert item.reference == EVIDENCE_REFERENCE and item.snapshot == {"ticker": "AAPL", "filing_date": "2025-10-31"}

    document = repository.add_item(
        "col-1",
        item_kind="document",
        citation="MSFT 10-K filing",
        excerpt="Microsoft Cloud revenue grew.",
        reference={"document_id": "MSFT:0000950170-25-100235"},
    )
    assert document.item_kind == "document" and document.reference == {"document_id": "MSFT:0000950170-25-100235"}

    with pytest.raises(CollectionError, match="must reference a document_id"):
        repository.add_item("col-1", item_kind="document", citation="x", excerpt="y", reference={"chunk_id": "c"})
    with pytest.raises(CollectionError, match="must carry at least one identity"):
        repository.add_item("col-1", item_kind="evidence", citation="x", excerpt="y", reference={})
    with pytest.raises(CollectionError, match="citation must not be empty"):
        repository.add_item("col-1", item_kind="evidence", citation="  ", excerpt="y", reference=EVIDENCE_REFERENCE)
    with pytest.raises(CollectionError, match="unsupported collection item kind"):
        repository.add_item("col-1", item_kind="model", citation="x", excerpt="y", reference=EVIDENCE_REFERENCE)

    # The collection's own count sees mixed kinds.
    items, total = repository.list_items("col-1")
    assert total == 2 and {entry.item_kind for entry in items} == {"document", "evidence"}
    filtered, filtered_total = repository.list_items("col-1", kind="document")
    assert filtered_total == 1 and filtered[0].item_id == document.item_id
    with pytest.raises(CollectionError, match="unsupported item kind"):
        repository.list_items("col-1", kind="spreadsheet")
    assert repository.get_collection("col-1").item_count == 2


def test_item_deletion_requires_parent_ownership_and_tombstones(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="One")
    repository.create_collection(collection_id="col-2", name="Two")
    item = repository.add_item(
        "col-1",
        item_kind="evidence",
        citation="AAPL 10-K",
        excerpt="excerpt",
        reference=EVIDENCE_REFERENCE,
    )

    with pytest.raises(CollectionNotFoundError, match="does not belong to this collection"):
        repository.delete_item("col-2", item.item_id, expected_revision=1)

    receipt = repository.delete_item("col-1", item.item_id, expected_revision=1)
    assert receipt.operation == "delete_item" and receipt.revision == 2
    with pytest.raises(CollectionDeletedError):
        repository.get_item(item.item_id)
    # A deleted member is never re-added by reusing its identity.
    with pytest.raises(CollectionDeletedError):
        repository.add_item(
            "col-1",
            item_id=item.item_id,
            item_kind="evidence",
            citation="AAPL 10-K",
            excerpt="excerpt",
            reference=EVIDENCE_REFERENCE,
        )


def test_deleting_a_collection_tombstones_its_members_and_notes(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="Doomed")
    item = repository.add_item("col-1", item_kind="document", citation="AAPL", excerpt="x", reference={"document_id": "AAPL:1"})
    note = repository.add_note("col-1", text="remember this")

    repository.delete_collection("col-1", expected_revision=1)
    for entity_id in (item.item_id, note.note_id):
        with pytest.raises(CollectionDeletedError):
            repository.get_item(entity_id)
    assert repository.list_activity("col-1")[1] >= 3


def test_notes_are_editable_bound_or_unbound_and_revision_guarded(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="Notes")

    unbound = repository.add_note("col-1", text="first thought")
    assert unbound.note_id.startswith("note-") and unbound.evidence_ref is None and unbound.revision == 1
    bound = repository.add_note("col-1", note_id="note-bound", text="checked", evidence_ref=EVIDENCE_REFERENCE)
    assert bound.evidence_ref == EVIDENCE_REFERENCE

    with pytest.raises(CollectionError, match="must carry at least one identity"):
        repository.add_note("col-1", text="bad ref", evidence_ref={"ticker": "AAPL"})

    updated = repository.update_note("col-1", unbound.note_id, expected_revision=1, text="second thought")
    assert (updated.revision, updated.text) == (2, "second thought")
    with pytest.raises(CollectionConflictError):
        repository.update_note("col-1", unbound.note_id, expected_revision=1, text="stale")

    notes, total = repository.list_notes("col-1")
    assert total == 2
    items, item_total = repository.list_items("col-1", kind="note")
    assert item_total == 2 and {entry.item_id for entry in items} == {unbound.note_id, "note-bound"}

    with pytest.raises(CollectionNotFoundError, match="does not belong to this collection"):
        repository.update_note("col-missing", "note-bound", expected_revision=1, text="x")


def test_listing_filters_sort_and_page_bounds(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-a", name="Alpha filings", tags=["sec"], favorite=True)
    repository.create_collection(collection_id="col-b", name="Beta review", description="risk notes")
    repository.add_item("col-b", item_kind="document", citation="AAPL", excerpt="x", reference={"document_id": "AAPL:1"})

    by_name, total = repository.list_collections(sort="name", direction="asc")
    assert total == 2 and [item.name for item in by_name] == ["Alpha filings", "Beta review"]
    favorites, favorite_total = repository.list_collections(favorite=True)
    assert favorite_total == 1 and favorites[0].collection_id == "col-a"
    tagged, tagged_total = repository.list_collections(tags=["sec"])
    assert tagged_total == 1 and tagged[0].collection_id == "col-a"
    searched, search_total = repository.list_collections(search="risk")
    assert search_total == 1 and searched[0].collection_id == "col-b"
    by_count, _ = repository.list_collections(sort="item_count", direction="desc")
    assert by_count[0].collection_id == "col-b" and by_count[0].item_count == 1

    page, _ = repository.list_collections(page=2, page_size=1, sort="name", direction="asc")
    assert [item.collection_id for item in page] == ["col-b"]
    with pytest.raises(CollectionError, match="unsupported sort field"):
        repository.list_collections(sort="owner")
    with pytest.raises(CollectionError, match="direction must be asc or desc"):
        repository.list_collections(direction="sideways")
    with pytest.raises(CollectionError, match="page must be a positive integer"):
        repository.list_collections(page=0)
    with pytest.raises(CollectionLimitError, match="page_size must not exceed"):
        repository.list_collections(page_size=101)


def test_collection_and_member_bounds_are_enforced(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="Full")
    for index in range(MAX_ITEMS_PER_COLLECTION):
        repository.add_item("col-1", item_kind="document", citation=f"doc {index}", excerpt="x", reference={"document_id": f"AAPL:{index}"})
    # Notes share the item bound, so their own bound is proved on a collection
    # that has not already filled its member list.
    repository.create_collection(collection_id="col-notes", name="Notes")
    for index in range(MAX_NOTES_PER_COLLECTION):
        repository.add_note("col-notes", text=f"note {index}")
    with pytest.raises(CollectionLimitError, match=f"at most {MAX_NOTES_PER_COLLECTION} notes"):
        repository.add_note("col-notes", text="one more")
    with pytest.raises(CollectionLimitError, match=f"at most {MAX_ITEMS_PER_COLLECTION} items"):
        repository.add_item("col-1", item_kind="document", citation="one more", excerpt="x", reference={"document_id": "AAPL:extra"})

    existing = repository.list_collections(page_size=MAX_COLLECTIONS)[1]
    for index in range(MAX_COLLECTIONS - existing):
        repository.create_collection(collection_id=f"col-extra-{index}", name=f"Extra {index}")
    with pytest.raises(CollectionLimitError, match=f"at most {MAX_COLLECTIONS} collections"):
        repository.create_collection(collection_id="col-overflow", name="Overflow")


def test_duplicate_identifiers_are_conflicts_not_silent_merges(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="One")
    with pytest.raises(CollectionConflictError, match="already exists"):
        repository.create_collection(collection_id="col-1", name="One again")

    repository.add_note("col-1", note_id="note-1", text="first")
    with pytest.raises(CollectionConflictError, match="already exists"):
        repository.add_note("col-1", note_id="note-1", text="second")


def test_activity_records_real_operations_and_stays_bounded(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="History")
    item = repository.add_item("col-1", item_kind="evidence", citation="AAPL", excerpt="x", reference=EVIDENCE_REFERENCE)
    repository.update_collection("col-1", expected_revision=1, name="History (renamed)")
    repository.delete_item("col-1", item.item_id, expected_revision=1)

    events, total = repository.list_activity("col-1")
    assert total == 4
    assert [event.event_type for event in events] == ["item_removed", "collection_updated", "item_added", "collection_created"]
    assert all(event.collection_id == "col-1" for event in events)

    for index in range(MAX_ACTIVITY_PER_COLLECTION + 5):
        repository.record_activity(collection_id="col-1", event_type="item_added", entity_type=ITEM_ENTITY_TYPE, entity_id=f"itm-{index}")
    _events, bounded_total = repository.list_activity("col-1", page_size=100)
    assert bounded_total <= MAX_ACTIVITY_PER_COLLECTION
    with pytest.raises(CollectionError, match="unsupported activity event"):
        repository.record_activity(collection_id="col-1", event_type="item_exploded", entity_type=ITEM_ENTITY_TYPE, entity_id="itm-1")


def test_export_carries_the_truth_for_members_notes_and_tags(workspace) -> None:
    _path, repository = workspace
    repository.create_collection(collection_id="col-1", name="Export me", description="desc", tags=["sec"], favorite=True)
    repository.add_item(
        "col-1",
        item_id="itm-1",
        item_kind="evidence",
        citation="AAPL 10-K, Financial Statements",
        excerpt="Total revenue was reported in fiscal 2024.",
        reference=EVIDENCE_REFERENCE,
        snapshot={"ticker": "AAPL"},
    )
    repository.add_note("col-1", note_id="note-1", text="checked the figure")

    payload = repository.export_collection("col-1")
    assert payload["id"] == "col-1" and payload["favorite"] is True and payload["tags"] == ["sec"]
    assert payload["revision"] == 1
    assert payload["items"] == [
        {
            "id": "itm-1",
            "kind": "evidence",
            "citation": "AAPL 10-K, Financial Statements",
            "excerpt": "Total revenue was reported in fiscal 2024.",
            "reference": EVIDENCE_REFERENCE,
            "snapshot": {"ticker": "AAPL"},
            "created_at": payload["items"][0]["created_at"],
        }
    ]
    assert payload["notes"][0]["id"] == "note-1" and payload["notes"][0]["revision"] == 1

    markdown = repository.export_collection("col-1", format="markdown")
    assert markdown.startswith("# Export me")
    assert "AAPL 10-K, Financial Statements" in markdown and "checked the figure" in markdown
    with pytest.raises(CollectionError, match="export format must be json or markdown"):
        repository.export_collection("col-1", format="pdf")


def test_records_carry_the_transfer_keys_the_export_path_reads(workspace) -> None:
    path, repository = workspace
    repository.create_collection(collection_id="col-1", name="Spine")
    repository.add_item("col-1", item_id="itm-1", item_kind="document", citation="AAPL", excerpt="x", reference={"document_id": "AAPL:1"})

    with WorkspaceDatabase(path).transaction() as connection:
        rows = {
            row["entity_type"]: (row["entity_id"], json.loads(row["payload_json"]))
            for row in connection.execute("SELECT entity_type, entity_id, payload_json FROM workspace_records")
        }
    assert set(rows) >= {COLLECTION_ENTITY_TYPE, ITEM_ENTITY_TYPE, ACTIVITY_ENTITY_TYPE}
    collection_storage_id, collection_payload = rows[COLLECTION_ENTITY_TYPE]
    assert collection_storage_id == collection_entity_id("col-1")
    assert collection_payload["legacy_id"] == "col-1" and collection_payload["source_kind"] == "collection"
    assert collection_payload["source_schema_version"] == 2 and collection_payload["favorite"] is False
    item_storage_id, item_payload = rows[ITEM_ENTITY_TYPE]
    assert item_storage_id == item_entity_id("itm-1")
    assert item_payload["parent_legacy_id"] == "col-1" and item_payload["source_kind"] == "evidence_item"
    activity_storage_id, activity_payload = rows[ACTIVITY_ENTITY_TYPE]
    assert activity_storage_id.startswith("act-")
    # Activity stays out of the portable transfer kinds on purpose.
    assert "workspace_transfer_version" not in activity_payload
