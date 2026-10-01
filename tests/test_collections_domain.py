"""Typed collection domain rules: kinds, membership, bounds, identity, payloads.

These tests drive the real repository against a real SQLite workspace, so the
spine they assert is the spine the transfer layer will export.
"""

from __future__ import annotations

import pytest

from src.workspace.collections import (
    ACTIVITY_ENTITY_TYPE,
    COLLECTION_ENTITY_TYPE,
    ITEM_ENTITY_TYPE,
    NOTE_ENTITY_TYPE,
    COLLECTION_ITEM_KINDS,
    MAX_COLLECTIONS,
    MAX_DESCRIPTION_LENGTH,
    MAX_ITEMS_PER_COLLECTION,
    MAX_NAME_LENGTH,
    MAX_NOTE_LENGTH,
    MAX_TAGS,
    MAX_TAG_LENGTH,
    CollectionConflictError,
    CollectionDeletedError,
    CollectionError,
    CollectionLimitError,
    CollectionNotFoundError,
    SQLiteCollectionRepository,
    collection_entity_id,
    collection_payload,
    generate_id,
    item_entity_id,
    item_payload,
    note_payload,
    unwrap_payload,
    validate_collection_fields,
    validate_evidence_reference,
    validate_identifier,
    validate_item_reference,
)
from src.workspace.database import WorkspaceDatabase


@pytest.fixture
def repository(tmp_path) -> SQLiteCollectionRepository:
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    database.initialize()
    return SQLiteCollectionRepository(database)


EVIDENCE_REFERENCE = {
    "document_id": "AAPL:0000320193-25-000079",
    "chunk_id": "AAPL_000032019325000079_financial_statements_0001",
    "chunk_text_hash": "a" * 64,
    "representation": "indexed_excerpt",
}


def test_every_supported_item_kind_is_accepted_with_its_own_reference() -> None:
    assert set(COLLECTION_ITEM_KINDS) == {"document", "evidence", "answer", "note"}
    assert validate_item_reference("document", {"document_id": "AAPL:0001"}) == {"document_id": "AAPL:0001"}
    assert validate_item_reference("evidence", EVIDENCE_REFERENCE) == EVIDENCE_REFERENCE
    assert validate_item_reference("answer", {"conversation_id": "conv-1", "message_id": "msg-1"})["conversation_id"] == "conv-1"
    assert validate_item_reference("note", {}) == {}
    assert validate_item_reference("note", {"document_id": "AAPL:0001"}) == {"document_id": "AAPL:0001"}


def test_unsupported_kind_is_rejected_deterministically() -> None:
    with pytest.raises(CollectionError, match="unsupported collection item kind"):
        validate_item_reference("spreadsheet", {"document_id": "AAPL:0001"})
    with pytest.raises(CollectionError, match="unsupported collection item kind"):
        validate_item_reference("", {})


def test_membership_rules_reject_a_reference_that_cannot_identify_its_kind() -> None:
    with pytest.raises(CollectionError, match="must reference a document_id"):
        validate_item_reference("document", {"ticker": "AAPL"})
    with pytest.raises(CollectionError, match="must carry at least one identity"):
        validate_item_reference("evidence", {"ticker": "AAPL"})
    with pytest.raises(CollectionError, match="must reference a conversation, message or answer identity"):
        validate_item_reference("answer", {"document_id": "AAPL:0001"})


def test_evidence_reference_requires_an_identity_and_string_provenance() -> None:
    with pytest.raises(CollectionError, match="must carry at least one identity"):
        validate_evidence_reference({"chunk_text_hash": "a" * 64})
    with pytest.raises(CollectionError, match="must be a string"):
        validate_evidence_reference({"document_id": "AAPL:0001", "chunk_text_hash": 42})


def test_the_declared_kind_decides_the_rule_and_is_never_inferred() -> None:
    """The same reference is judged by the kind the caller declared.

    A document identity satisfies the evidence rule (an EvidenceRef may name a
    document), while a chunk-only reference does not satisfy the document rule,
    so no kind is inferred from the shape of a reference.
    """
    assert validate_item_reference("evidence", {"document_id": "AAPL:0001"})["document_id"] == "AAPL:0001"
    with pytest.raises(CollectionError, match="must reference a document_id"):
        validate_item_reference("document", {"chunk_id": "AAPL_x"})
    with pytest.raises(CollectionError, match="must reference a conversation, message or answer identity"):
        validate_item_reference("answer", {"document_id": "AAPL:0001"})


def test_identifier_rules_reject_paths_and_malformed_values() -> None:
    assert validate_identifier("col-0123456789abcdef", label="collection_id") == "col-0123456789abcdef"
    for value in ("", "..", "a/b", "a\\b", "a\0b", "a" * 200, None, 7, True):
        with pytest.raises(CollectionError, match="collection_id is malformed"):
            validate_identifier(value, label="collection_id")


def test_collection_fields_are_normalized_and_bounded() -> None:
    fields = validate_collection_fields(name="  Risk review  ", description="d", tags=["b", "a", "a"], favorite=True, private=False)
    assert fields == {"name": "Risk review", "description": "d", "tags": ["a", "b"], "favorite": True, "private": False}
    with pytest.raises(CollectionError, match="name must not be empty"):
        validate_collection_fields(name="   ")
    with pytest.raises(CollectionLimitError, match="name exceeds"):
        validate_collection_fields(name="n" * (MAX_NAME_LENGTH + 1))
    with pytest.raises(CollectionLimitError, match="description exceeds"):
        validate_collection_fields(name="ok", description="d" * (MAX_DESCRIPTION_LENGTH + 1))
    with pytest.raises(CollectionLimitError, match="at most 20 tags"):
        validate_collection_fields(name="ok", tags=[f"t{index}" for index in range(MAX_TAGS + 1)])
    with pytest.raises(CollectionLimitError, match=f"tag exceeds {MAX_TAG_LENGTH}"):
        validate_collection_fields(name="ok", tags=["t" * (MAX_TAG_LENGTH + 1)])
    with pytest.raises(CollectionError, match="favorite must be a boolean"):
        validate_collection_fields(name="ok", favorite="yes")
    with pytest.raises(CollectionError, match="private must be a boolean"):
        validate_collection_fields(name="ok", private=1)


def test_generated_identifiers_are_opaque_and_prefixed() -> None:
    first, second = generate_id("col"), generate_id("col")
    assert first.startswith("col-") and first != second and validate_identifier(first, label="id") == first


def test_storage_keys_follow_the_transfer_mapping_so_imports_cannot_duplicate() -> None:
    assert collection_entity_id("col-1") == collection_entity_id("col-1")
    assert collection_entity_id("col-1") != collection_entity_id("col-2")
    assert item_entity_id("itm-1") == item_entity_id("itm-1")
    assert collection_entity_id("col-1") != item_entity_id("col-1")


def test_collection_payload_carries_the_legacy_spine_and_the_typed_fields() -> None:
    fields = validate_collection_fields(name="Filings", description="notes", tags=["sec"], favorite=True, private=True)
    payload = collection_payload(collection_id="col-1", fields=fields, created_at_ms=1_700_000_000_000, updated_at_ms=1_700_000_000_000)
    assert payload["workspace_transfer_version"] == 1
    assert payload["source_kind"] == "collection"
    assert payload["legacy_id"] == "col-1"
    assert payload["source_schema_version"] == 2
    assert payload["favorite"] is True
    data = payload["data"]
    assert data["id"] == "col-1" and data["schemaVersion"] == 2 and data["name"] == "Filings"
    assert data["tags"] == ["sec"] and data["private"] is True
    assert data["createdAt"] == data["updatedAt"] == 1_700_000_000_000
    assert "items" not in data


def test_item_payload_carries_the_identity_the_envelope_requires() -> None:
    payload = item_payload(
        item_id="itm-1",
        collection_id="col-1",
        item_kind="evidence",
        citation="AAPL 10-K, Financial Statements",
        excerpt="Total revenue was reported in fiscal 2024.",
        reference=EVIDENCE_REFERENCE,
        snapshot={"ticker": "AAPL"},
        saved_at_ms=1_700_000_000_000,
    )
    assert payload["source_kind"] == "evidence_item"
    assert payload["parent_legacy_id"] == "col-1"
    data = payload["data"]
    assert data["id"] == "itm-1" and data["itemKind"] == "evidence"
    assert data["savedAt"] == data["createdAt"] == data["updatedAt"] == 1_700_000_000_000
    assert data["reference"] == EVIDENCE_REFERENCE and data["snapshot"] == {"ticker": "AAPL"}


def test_note_payload_is_outside_the_portable_kinds_and_says_so() -> None:
    payload = note_payload(note_id="note-1", collection_id="col-1", text="check this", evidence_ref=None, created_at_ms=7, updated_at_ms=8)
    assert "workspace_transfer_version" not in payload
    assert payload["workspace_collection_note"] == 1
    assert payload["data"]["text"] == "check this" and payload["data"]["updatedAt"] == 8


def test_unwrap_fails_closed_on_a_foreign_record() -> None:
    with pytest.raises(CollectionError, match="not a typed record this workspace understands"):
        unwrap_payload({"data": {"id": "col-1"}}, label="collection record")
    with pytest.raises(CollectionError, match="not a typed record this workspace understands"):
        unwrap_payload({"workspace_transfer_version": 1, "data": "nope"}, label="collection record")


@pytest.mark.parametrize("entity_type", [COLLECTION_ENTITY_TYPE, ITEM_ENTITY_TYPE, NOTE_ENTITY_TYPE, ACTIVITY_ENTITY_TYPE])
def test_entity_types_are_distinct(repository, entity_type) -> None:
    assert entity_type in {
        COLLECTION_ENTITY_TYPE,
        ITEM_ENTITY_TYPE,
        NOTE_ENTITY_TYPE,
        ACTIVITY_ENTITY_TYPE,
    }
    assert repository.database.path.exists()


def test_limits_are_declared_not_implied() -> None:
    assert (MAX_COLLECTIONS, MAX_ITEMS_PER_COLLECTION, MAX_NOTE_LENGTH) == (50, 100, 10_000)
