"""DATA-002-C focused canonicalization, conflict, and cross-runtime digest tests.

The shared fixture at ``tests/fixtures/workspace_transfer_roundtrip.json``
carries envelopes whose digests were produced by the Python canonical
serializer; the Vitest suite reproduces them with the TypeScript canonicalizer,
so any canonicalization drift between the runtimes fails one of the two sides.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.workspace.database import WorkspaceDatabase
from src.workspace.transfer import (
    _canonical_json,
    _js_number_text,
    WorkspaceTransferError,
    WorkspaceTransferService,
    build_workspace_backup,
    compute_backup_digest,
    stable_legacy_id,
    validate_workspace_backup,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "workspace_transfer_roundtrip.json"
NOW = 1_735_689_600_000

_COUNT_QUERIES = {
    "workspace_records": "SELECT COUNT(*) FROM workspace_records",
    "tombstones": "SELECT COUNT(*) FROM tombstones",
    "workspace_imports": "SELECT COUNT(*) FROM workspace_imports",
}


def _fixtures() -> dict[str, dict]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {entry["id"]: entry["backup"] for entry in data["fixtures"]}


def _conversation(*, legacy_id: str = "conversation-1", revision: int = 2, answer: str = "Newer answer") -> dict:
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
            {"id": "answer-1", "role": "assistant", "content": answer},
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


def _tombstone(*, revision: int = 4) -> dict:
    return {
        "kind": "conversation",
        "legacy_id": "conversation-1",
        "schema_version": 1,
        "revision": revision,
        "deleted_at": NOW + 30,
    }


@pytest.fixture
def service(tmp_path) -> WorkspaceTransferService:
    database = WorkspaceDatabase(tmp_path / "canonical-workspace.sqlite3")
    database.initialize()
    return WorkspaceTransferService(database)


def _count(database: WorkspaceDatabase, table: str) -> int:
    with database.connection() as connection:
        return int(connection.execute(_COUNT_QUERIES[table]).fetchone()[0])


@pytest.mark.parametrize("fixture_id,backup", sorted(_fixtures().items()))
def test_shared_fixture_validates_and_reproduces_the_python_digest(fixture_id: str, backup: dict) -> None:
    validated = validate_workspace_backup(backup)
    assert validated.digest == backup["digest"]
    payload = {key: value for key, value in backup.items() if key not in {"digest", "exported_at"}}
    assert compute_backup_digest(payload) == backup["digest"]


@pytest.mark.parametrize(
    "value,expected",
    [
        (5.0, "5"),
        (-0.0, "0"),
        (1.25, "1.25"),
        (0.001, "0.001"),
        (1e-07, "1e-7"),
        (1e20, "100000000000000000000"),
        (1e21, "1e+21"),
        (1.5e21, "1.5e+21"),
        (123456.789, "123456.789"),
        (-2.5e-7, "-2.5e-7"),
    ],
)
def test_number_serialization_matches_the_ecmascript_contract(value: float, expected: str) -> None:
    assert _js_number_text(value) == expected


def test_integral_floats_and_parsed_integers_share_one_digest() -> None:
    assert compute_backup_digest({"value": 5.0}) == compute_backup_digest({"value": 5})
    assert compute_backup_digest({"value": 1e-07}) == compute_backup_digest(
        json.loads('{"value": 1e-7}')
    )


def test_canonical_json_orders_keys_by_code_point_not_utf16_units() -> None:
    reversed_order = {"\U0001f600-alpha": 1, "\ue000-zone": 2, "ascii": 3}
    canonical = _canonical_json(reversed_order)
    assert (
        canonical.index('"ascii"')
        < canonical.index('"\ue000-zone"')
        < canonical.index('"\U0001f600-alpha"')
    )


def test_record_ordering_uses_code_point_comparison() -> None:
    backup = build_workspace_backup(
        conversations=[
            _conversation(legacy_id="conversation-a"),
            _conversation(legacy_id="conversation-Z"),
        ],
        collections=[],
        evidence_items=[],
        favorites=[],
        tombstones=[],
    )
    assert [record["legacy_id"] for record in backup["conversations"]] == [
        "conversation-Z",
        "conversation-a",
    ]


def test_unpaired_surrogates_fail_closed() -> None:
    with pytest.raises(WorkspaceTransferError, match="unpaired surrogate"):
        compute_backup_digest({"payload": json.loads('"\\ud800"')})

    poisoned = copy.deepcopy(_fixtures()["minimal-valid-backup"])
    poisoned["exported_at"] = "bad\ud800"
    with pytest.raises(WorkspaceTransferError, match="unpaired surrogate"):
        validate_workspace_backup(poisoned)


def test_unsafe_numbers_fail_closed_like_the_frontend_validator() -> None:
    for value in (1.5e21, 2**53):
        poisoned = copy.deepcopy(_fixtures()["unicode-and-numeric-canonicalization"])
        poisoned["conversations"][0]["payload"]["metadata"]["poison"] = value
        with pytest.raises(WorkspaceTransferError, match="safe cross-runtime range"):
            validate_workspace_backup(poisoned)


def test_legacy_id_mapping_is_deterministic_across_independent_databases(tmp_path) -> None:
    backup = _fixtures()["identity-revisions-and-tombstones"]
    receipts = []
    for index in range(2):
        database = WorkspaceDatabase(tmp_path / f"mapping-{index}.sqlite3")
        database.initialize()
        receipts.append(WorkspaceTransferService(database).import_backup(backup, backup["digest"]))

    first = {item["legacy_id"]: item["workspace_id"] for item in receipts[0]["mappings"]}
    second = {item["legacy_id"]: item["workspace_id"] for item in receipts[1]["mappings"]}
    assert first == second
    assert first["conversation-1"] == stable_legacy_id("conversation", "conversation-1")
    assert stable_legacy_id("conversation", "conversation-1") == stable_legacy_id(
        "conversation", "conversation-1"
    )
    assert stable_legacy_id("collection", "conversation-1") != first["conversation-1"]


def test_foreign_record_is_conflict_without_overwrite(service: WorkspaceTransferService) -> None:
    backup = _fixtures()["identity-revisions-and-tombstones"]
    workspace_id = stable_legacy_id("conversation", "conversation-1")
    with service.database.transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO workspace_records("
            "entity_type, entity_id, revision, payload_json, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            (
                "conversation",
                workspace_id,
                7,
                json.dumps({"foreign": True}),
                "2025-01-01T00:00:00Z",
                "2025-01-01T00:00:00Z",
            ),
        )

    preview = service.preview(backup)
    assert preview["potential_conflicts"] == 1
    assert preview["records_to_create"] == 2

    receipt = service.import_backup(backup, backup["digest"])
    assert receipt["potential_conflicts"] == 1
    with service.database.transaction() as connection:
        row = connection.execute(
            "SELECT revision, payload_json FROM workspace_records "
            "WHERE entity_type = ? AND entity_id = ?",
            ("conversation", workspace_id),
        ).fetchone()
    assert row["revision"] == 7
    assert json.loads(row["payload_json"]) == {"foreign": True}


def test_conflicting_import_does_not_regress_a_newer_authoritative_record(
    service: WorkspaceTransferService,
) -> None:
    initial = build_workspace_backup(
        conversations=[_conversation(revision=3, answer="Newer answer")],
        collections=[], evidence_items=[], favorites=[], tombstones=[],
    )
    service.import_backup(initial, initial["digest"])

    older = build_workspace_backup(
        conversations=[_conversation(revision=2, answer="Older answer")],
        collections=[], evidence_items=[], favorites=[], tombstones=[],
    )
    receipt = service.import_backup(older, older["digest"])
    assert receipt["potential_conflicts"] == 1

    exported = validate_workspace_backup(service.export_backup())
    assert exported.conversations[0]["revision"] == 3
    assert exported.conversations[0]["payload"]["messages"][1]["content"] == "Newer answer"


def test_export_accounts_for_non_portable_rows(service: WorkspaceTransferService) -> None:
    backup = _fixtures()["identity-revisions-and-tombstones"]
    service.import_backup(backup, backup["digest"])
    with service.database.transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO workspace_records("
            "entity_type, entity_id, revision, payload_json, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            (
                "note",
                "note-local-1",
                1,
                json.dumps({"private": "row"}),
                "2025-01-01T00:00:00Z",
                "2025-01-01T00:00:00Z",
            ),
        )

    raw_export = service.export_backup()
    exported = validate_workspace_backup(raw_export)
    assert exported.unsupported[0]["source"] == "workspace_records"
    assert exported.unsupported[0]["count"] == 1
    assert raw_export["source_counts"]["unsupported"] == 1
    assert [record["legacy_id"] for record in exported.conversations] == ["conversation-1"]


def test_tombstone_revision_semantics_are_deterministic(service: WorkspaceTransferService) -> None:
    live = build_workspace_backup(
        conversations=[_conversation(revision=5)],
        collections=[], evidence_items=[], favorites=[], tombstones=[],
    )
    service.import_backup(live, live["digest"])

    older_tombstone = build_workspace_backup(
        conversations=[], collections=[], evidence_items=[], favorites=[],
        tombstones=[_tombstone(revision=4)],
    )
    conflict = service.import_backup(older_tombstone, older_tombstone["digest"])
    assert conflict["potential_conflicts"] == 1
    assert _count(service.database, "workspace_records") == 1
    assert _count(service.database, "tombstones") == 0

    newer_tombstone = build_workspace_backup(
        conversations=[], collections=[], evidence_items=[], favorites=[],
        tombstones=[_tombstone(revision=6)],
    )
    service.import_backup(newer_tombstone, newer_tombstone["digest"])
    assert _count(service.database, "workspace_records") == 0
    assert _count(service.database, "tombstones") == 1
    exported = validate_workspace_backup(service.export_backup())
    assert exported.tombstones[0]["revision"] == 6
