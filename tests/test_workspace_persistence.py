"""Hermetic DATA-001 SQLite migration and repository foundation tests."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest
from pydantic import ValidationError

from configs.settings import Settings
from src.workspace.database import (
    WorkspaceBusyError,
    WorkspaceDatabase,
    WorkspaceDatabaseStateError,
    WorkspaceDisabledError,
    WorkspaceMigrationError,
)
from src.workspace.migrations import MIGRATIONS, Migration
from src.workspace.repository import (
    RecordConflictError,
    RecordDeletedError,
    RecordNotFoundError,
    SQLiteVersionedRecordRepository,
)


@pytest.fixture
def database(tmp_path: Path) -> WorkspaceDatabase:
    configured = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    assert configured.initialize() == 6
    return configured


def _tables(database: WorkspaceDatabase) -> set[str]:
    with database.connection() as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }


def test_fresh_database_creation_builds_all_foundation_domains(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    database = WorkspaceDatabase(path)

    version = database.initialize()

    assert version == 6
    assert path.is_file()
    assert {
        "schema_migrations",
        "workspace_records",
        "tombstones",
        "workspace_imports",
        "workspace_settings",
        "conversations",
        "collections",
        "collection_items",
        "notes",
        "activity_events",
        "jobs",
        "job_steps",
        "job_events",
        "telemetry_events",
        "evaluation_artifacts",
        "evaluation_attempts",
        "evaluation_case_results",
        "evaluation_reports",
    }.issubset(_tables(database))


def test_schema_version_receipts_match_deterministic_migration_order(
    database: WorkspaceDatabase,
) -> None:
    with database.connection() as connection:
        rows = list(
            connection.execute(
                "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
            )
        )

    assert [row["version"] for row in rows] == [1, 2, 3, 4, 5, 6]
    assert [row["name"] for row in rows] == [item.name for item in MIGRATIONS]
    assert [row["checksum"] for row in rows] == [item.checksum for item in MIGRATIONS]


def test_repeat_migration_is_idempotent(database: WorkspaceDatabase) -> None:
    with database.connection() as connection:
        before = list(
            connection.execute(
                "SELECT version, name, checksum, applied_at "
                "FROM schema_migrations ORDER BY version"
            )
        )

    assert database.initialize() == 6

    with database.connection() as connection:
        after = list(
            connection.execute(
                "SELECT version, name, checksum, applied_at "
                "FROM schema_migrations ORDER BY version"
            )
        )
    assert [tuple(row) for row in after] == [tuple(row) for row in before]


@pytest.mark.parametrize("upgrade", [False, True], ids=["fresh", "upgrade"])
def test_concurrent_initializers_share_the_complete_migration_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, upgrade: bool,
) -> None:
    path = tmp_path / "workspace.sqlite3"
    if upgrade:
        WorkspaceDatabase(path, migrations=MIGRATIONS[:1]).initialize()
    first = WorkspaceDatabase(path)
    second = WorkspaceDatabase(path.parent / "." / path.name)
    first_read = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    second_read = threading.Event()
    results: list[int] = []
    errors: list[BaseException] = []
    original_first_read = first._read_and_validate_migration_receipts
    original_second_read = second._read_and_validate_migration_receipts

    def paused_read() -> list[sqlite3.Row]:
        rows = original_first_read()
        first_read.set()
        assert release_first.wait(5), "test did not release the first initializer"
        return rows

    def observed_read() -> list[sqlite3.Row]:
        second_read.set()
        return original_second_read()

    monkeypatch.setattr(first, "_read_and_validate_migration_receipts", paused_read)
    monkeypatch.setattr(second, "_read_and_validate_migration_receipts", observed_read)

    def initialize(instance: WorkspaceDatabase, started: threading.Event | None = None) -> None:
        if started is not None:
            started.set()
        try:
            results.append(instance.initialize())
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=initialize, args=(first,)),
               threading.Thread(target=initialize, args=(second, second_started))]
    threads[0].start()
    try:
        assert first_read.wait(5)
        threads[1].start()
        assert second_started.wait(5)
        # The first caller still owns an unapplied receipt snapshot. A second
        # instance must not inspect that snapshot until the upgrade completes.
        inspected_pending_receipts = second_read.wait(0.2)
    finally:
        release_first.set()
        for thread in threads:
            if thread.ident is not None:
                thread.join(5)
    assert not any(thread.is_alive() for thread in threads)
    assert not inspected_pending_receipts
    assert errors == []
    assert sorted(results) == [6, 6]
    with second.connection() as connection:
        receipts = connection.execute(
            "SELECT version, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
    assert [tuple(row) for row in receipts] == [(item.version, item.checksum) for item in MIGRATIONS]


def test_migration_sequence_must_be_ordered_and_contiguous(tmp_path: Path) -> None:
    migration = Migration(2, "out_of_order", ("CREATE TABLE example(id TEXT)",))

    with pytest.raises(ValueError, match="ordered and contiguous"):
        WorkspaceDatabase(tmp_path / "workspace.sqlite3", migrations=(migration,))


def test_failed_migration_rolls_back_schema_and_version_receipt(tmp_path: Path) -> None:
    migrations = (
        Migration(1, "baseline", ("CREATE TABLE baseline(id TEXT PRIMARY KEY)",)),
        Migration(
            2,
            "broken",
            (
                "CREATE TABLE should_rollback(id TEXT PRIMARY KEY)",
                "THIS IS NOT VALID SQL",
            ),
        ),
    )
    path = tmp_path / "workspace.sqlite3"
    database = WorkspaceDatabase(path, migrations=migrations)

    with pytest.raises(WorkspaceMigrationError, match="migration 2 failed"):
        database.initialize()

    connection = sqlite3.connect(path)
    try:
        versions = [
            row[0]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        connection.close()
    assert versions == [1]
    assert "baseline" in tables
    assert "should_rollback" not in tables


def test_future_schema_version_fails_closed(database: WorkspaceDatabase) -> None:
    with database.transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
            "VALUES (7, 'future', 'future-checksum', '2026-01-01T00:00:00Z')"
        )

    with pytest.raises(WorkspaceDatabaseStateError, match="newer"):
        database.initialize()


def test_foreign_keys_are_enabled_and_enforced(database: WorkspaceDatabase) -> None:
    with database.connection() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction(write=True) as connection:
            connection.execute(
                "INSERT INTO collection_items("
                "item_id, collection_id, item_kind, reference_json, revision, created_at, updated_at"
                ") VALUES ('item_1', 'missing', 'document', '{}', 1, 'now', 'now')"
            )


def test_transaction_rolls_back_on_failure(database: WorkspaceDatabase) -> None:
    with pytest.raises(RuntimeError, match="abort"):
        with database.transaction(write=True) as connection:
            connection.execute(
                "INSERT INTO collections("
                "collection_id, name, revision, created_at, updated_at"
                ") VALUES ('collection_1', 'Example', 1, 'now', 'now')"
            )
            raise RuntimeError("abort")

    with database.connection() as connection:
        count = connection.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
    assert count == 0


def test_repository_revision_updates_are_atomic_and_conflicts_deterministic(
    database: WorkspaceDatabase,
) -> None:
    repository = SQLiteVersionedRecordRepository(
        database,
        clock=lambda: "2026-09-16T00:00:00.000000Z",
    )
    created = repository.create("conversation", "conversation_1", {"title": "First"})

    with pytest.raises(RecordConflictError, match="revision conflict"):
        repository.replace(
            "conversation",
            "conversation_1",
            {"title": "Stale"},
            expected_revision=2,
        )

    current = repository.get("conversation", "conversation_1")
    assert current == created
    updated = repository.replace(
        "conversation",
        "conversation_1",
        {"title": "Second"},
        expected_revision=1,
    )
    assert updated.revision == 2
    assert updated.payload == {"title": "Second"}


def test_repository_create_conflict_and_missing_record_are_explicit(
    database: WorkspaceDatabase,
) -> None:
    repository = SQLiteVersionedRecordRepository(database)
    repository.create("collection", "collection_1", {"name": "First"})

    with pytest.raises(RecordConflictError, match="already exists"):
        repository.create("collection", "collection_1", {"name": "Duplicate"})
    with pytest.raises(RecordNotFoundError, match="does not exist"):
        repository.replace(
            "collection",
            "missing",
            {"name": "Missing"},
            expected_revision=1,
        )


def test_tombstone_prevents_silent_resurrection(database: WorkspaceDatabase) -> None:
    repository = SQLiteVersionedRecordRepository(
        database,
        clock=lambda: "2026-09-16T00:00:00.000000Z",
    )
    repository.create("note", "note_1", {"text": "Research note"})

    tombstone = repository.delete("note", "note_1", expected_revision=1)

    assert tombstone.revision == 2
    assert repository.get("note", "note_1") is None
    assert repository.get_tombstone("note", "note_1") == tombstone
    with pytest.raises(RecordDeletedError, match="deleted"):
        repository.create("note", "note_1", {"text": "Resurrected"})
    with pytest.raises(RecordDeletedError, match="deleted"):
        repository.delete("note", "note_1", expected_revision=2)


def test_bounded_busy_timeout_rejects_competing_writer(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    first = WorkspaceDatabase(path, busy_timeout_ms=100)
    second = WorkspaceDatabase(path, busy_timeout_ms=100)
    first.initialize()
    second.initialize()

    with first.transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO workspace_settings(setting_key, value_json, revision, updated_at) "
            "VALUES ('log_retention_days', '7', 1, 'now')"
        )
        with pytest.raises(WorkspaceBusyError, match="busy"):
            with second.transaction(write=True):
                pass


def test_write_lock_is_shared_across_instances_in_one_process(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    first = WorkspaceDatabase(path)
    second = WorkspaceDatabase(path)
    first.initialize()
    acquired = threading.Event()

    def second_writer() -> None:
        with second.transaction(write=True):
            acquired.set()

    with first.transaction(write=True):
        thread = threading.Thread(target=second_writer)
        thread.start()
        assert not acquired.wait(0.05)
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert acquired.is_set()


def test_public_settings_do_not_create_or_open_workspace_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    configured = Settings(_env_file=None)

    with pytest.raises(WorkspaceDisabledError, match="unavailable"):
        WorkspaceDatabase.from_settings(configured)

    assert not (tmp_path / ".local").exists()


def test_explicit_local_settings_construct_database_without_eager_write(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private" / "workspace.sqlite3"
    configured = Settings(
        _env_file=None,
        workspace_mode="local",
        local_workspace_token="local-test-token-0123456789-abcdef",
        workspace_db_path=path,
        workspace_runs_dir=tmp_path / "private" / "runs",
    )

    database = WorkspaceDatabase.from_settings(configured)

    assert database.path == path.resolve()
    assert not path.exists()
    assert database.initialize() == 6


def test_database_path_rejects_canonical_data_and_relative_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()

    with pytest.raises(ValueError, match="canonical data"):
        WorkspaceDatabase(Path("data/workspace.sqlite3"))
    with pytest.raises(ValidationError, match="must remain under .local"):
        Settings(_env_file=None, workspace_db_path="../workspace.sqlite3")

    assert list((tmp_path / "data").iterdir()) == []


def test_database_writes_remain_isolated_to_configured_directory(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    database = WorkspaceDatabase(workspace_dir / "workspace.sqlite3")

    database.initialize()

    files = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert files
    assert all(workspace_dir in path.parents for path in files)


def test_reopening_existing_database_preserves_records(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    first = WorkspaceDatabase(path)
    first.initialize()
    SQLiteVersionedRecordRepository(first).create(
        "conversation",
        "conversation_1",
        {"title": "Persistent"},
    )

    reopened = WorkspaceDatabase(path)
    assert reopened.initialize() == 6

    record = SQLiteVersionedRecordRepository(reopened).get(
        "conversation",
        "conversation_1",
    )
    assert record is not None
    assert record.payload == {"title": "Persistent"}


def test_malformed_migration_metadata_fails_safely(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY)")
    connection.commit()
    connection.close()

    with pytest.raises(WorkspaceDatabaseStateError, match="metadata is incompatible"):
        WorkspaceDatabase(path).initialize()


def test_missing_required_schema_object_fails_safely(database: WorkspaceDatabase) -> None:
    with database.transaction(write=True) as connection:
        connection.execute("DROP TABLE telemetry_events")

    with pytest.raises(WorkspaceDatabaseStateError, match="missing required"):
        database.initialize()


def test_corrupt_database_file_fails_safely(tmp_path: Path) -> None:
    path = tmp_path / "workspace.sqlite3"
    path.write_bytes(b"not-a-sqlite-database")

    with pytest.raises(WorkspaceDatabaseStateError):
        WorkspaceDatabase(path).initialize()


def test_workspace_setting_allowlist_rejects_secret_keys(
    database: WorkspaceDatabase,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction(write=True) as connection:
            connection.execute(
                "INSERT INTO workspace_settings("
                "setting_key, value_json, revision, updated_at"
                ") VALUES (?, ?, 1, 'now')",
                ("local_workspace_token", '"redacted"'),
            )


@pytest.mark.parametrize(
    "payload",
    [
        {"local_workspace_token": "forbidden"},
        {"nested": {"groq_api_key": "forbidden"}},
        {"provider": [{"authorization": "forbidden"}]},
    ],
)
def test_repository_rejects_credential_fields(
    database: WorkspaceDatabase,
    payload: dict[str, object],
) -> None:
    repository = SQLiteVersionedRecordRepository(database)

    with pytest.raises(ValueError, match="credential fields"):
        repository.create("conversation", "conversation_1", payload)
    assert repository.get("conversation", "conversation_1") is None


def test_repository_rejects_configured_secret_values(database: WorkspaceDatabase) -> None:
    repository = SQLiteVersionedRecordRepository(
        database,
        forbidden_secret_values=("dedicated-local-secret-value",),
    )

    with pytest.raises(ValueError, match="credential values"):
        repository.create(
            "conversation",
            "conversation_1",
            {"text": "prefix dedicated-local-secret-value suffix"},
        )
    assert repository.get("conversation", "conversation_1") is None


@pytest.mark.parametrize("entity_id", ["../escape", "folder/item", "", ".hidden"])
def test_repository_requires_opaque_ids(
    database: WorkspaceDatabase,
    entity_id: str,
) -> None:
    repository = SQLiteVersionedRecordRepository(database)

    with pytest.raises(ValueError, match="opaque"):
        repository.create("conversation", entity_id, {"title": "Example"})


def test_telemetry_schema_has_no_research_content_or_generic_payload_columns(
    database: WorkspaceDatabase,
) -> None:
    with database.connection() as connection:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(telemetry_events)")
        }

    assert not columns.intersection(
        {"content", "payload", "query", "question", "answer", "prompt", "headers"}
    )
    assert {
        "event_name",
        "status",
        "duration_ms",
        "retention_until",
        "record_schema_version",
        "subsystem",
        "severity",
        "correlation_id",
        "domain_id",
        "error_code",
        "metadata_json",
    }.issubset(columns)


def test_sqlite_pragmas_use_wal_and_bounded_busy_timeout(
    database: WorkspaceDatabase,
) -> None:
    with database.connection() as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
