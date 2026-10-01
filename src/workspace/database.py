"""Safe SQLite lifecycle and transaction handling for the local workspace."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from configs.settings import Settings
from src.workspace.migrations import (
    EXPECTED_TABLES_BY_VERSION,
    MIGRATIONS,
    Migration,
    validate_migration_sequence,
)


_WRITE_LOCKS_GUARD = threading.Lock()
_WRITE_LOCKS: dict[Path, threading.RLock] = {}


def _write_lock_for(path: Path) -> threading.RLock:
    with _WRITE_LOCKS_GUARD:
        lock = _WRITE_LOCKS.get(path)
        if lock is None:
            lock = threading.RLock()
            _WRITE_LOCKS[path] = lock
        return lock


class WorkspaceDatabaseError(RuntimeError):
    """Base error for workspace persistence failures."""


class WorkspaceDisabledError(WorkspaceDatabaseError):
    """Raised when local persistence is requested outside explicit local mode."""


class WorkspaceDatabaseStateError(WorkspaceDatabaseError):
    """Raised for corrupt or incompatible database state."""


class WorkspaceMigrationError(WorkspaceDatabaseError):
    """Raised when a migration fails or its receipt is inconsistent."""


class WorkspaceBusyError(WorkspaceDatabaseError):
    """Raised when the bounded SQLite busy timeout expires."""


@dataclass(frozen=True)
class WorkspaceStorageConfig:
    database_path: Path
    runs_directory: Path
    busy_timeout_ms: int

    @classmethod
    def from_settings(cls, configured: Settings) -> "WorkspaceStorageConfig":
        if configured.workspace_mode != "local":
            raise WorkspaceDisabledError("local workspace persistence is unavailable")
        return cls(
            database_path=configured.workspace_db_path,
            runs_directory=configured.workspace_runs_dir,
            busy_timeout_ms=configured.workspace_sqlite_busy_timeout_ms,
        )


def _validate_database_path(path: Path) -> Path:
    raw = str(path)
    if raw.casefold() == ":memory:" or raw.casefold().startswith("file:"):
        raise ValueError("workspace database must use a filesystem path")
    if path.suffix.casefold() != ".sqlite3":
        raise ValueError("workspace database path must end in .sqlite3")
    resolved = path.resolve()
    canonical_data = Path("data").resolve()
    if resolved == canonical_data or canonical_data in resolved.parents:
        raise ValueError("workspace database must not use canonical data storage")
    if not path.is_absolute() and (
        ".." in path.parts or not path.parts or path.parts[0] != ".local"
    ):
        raise ValueError("relative workspace database paths must remain under .local")

    if resolved.exists() and resolved.is_dir():
        raise ValueError("workspace database path points to a directory")
    return resolved


class WorkspaceDatabase:
    """Connection factory, migration runner and serialized write boundary."""

    _MIGRATION_COLUMNS = (
        "version",
        "name",
        "checksum",
        "applied_at",
    )

    def __init__(
        self,
        path: Path,
        *,
        busy_timeout_ms: int = 5000,
        migrations: tuple[Migration, ...] = MIGRATIONS,
    ) -> None:
        if not 100 <= busy_timeout_ms <= 30_000:
            raise ValueError("busy timeout must be between 100 and 30000 milliseconds")
        validate_migration_sequence(migrations)
        self.path = _validate_database_path(Path(path))
        self.busy_timeout_ms = busy_timeout_ms
        self.migrations = migrations
        self._write_lock = _write_lock_for(self.path)

    @classmethod
    def from_settings(cls, configured: Settings) -> "WorkspaceDatabase":
        storage = WorkspaceStorageConfig.from_settings(configured)
        return cls(
            storage.database_path,
            busy_timeout_ms=storage.busy_timeout_ms,
        )

    @property
    def latest_schema_version(self) -> int:
        return self.migrations[-1].version

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self.path,
                timeout=self.busy_timeout_ms / 1000,
                isolation_level=None,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.execute("PRAGMA trusted_schema = OFF")
            return connection
        except sqlite3.OperationalError as error:
            if self._is_busy(error):
                raise WorkspaceBusyError("workspace database is busy") from error
            raise WorkspaceDatabaseStateError("workspace database could not be opened") from error
        except sqlite3.DatabaseError as error:
            raise WorkspaceDatabaseStateError("workspace database is invalid") from error

    @staticmethod
    def _is_busy(error: BaseException) -> bool:
        message = str(error).casefold()
        return "locked" in message or "busy" in message

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        lock = self._write_lock if write else nullcontext()
        with lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield connection
                connection.commit()
            except sqlite3.OperationalError as error:
                connection.rollback()
                if self._is_busy(error):
                    raise WorkspaceBusyError("workspace database is busy") from error
                raise
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.close()

    def initialize(self) -> int:
        """Create and migrate the configured database, safely and repeatably."""
        # The receipt snapshot and all pending migrations form one operation.
        # Locking only individual migration transactions lets another instance
        # apply the same pending list between inspection and application. The
        # shared reentrant lock also permits nested write transactions below.
        with self._write_lock:
            return self._initialize_locked()

    def _initialize_locked(self) -> int:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise WorkspaceDatabaseStateError(
                "workspace database directory could not be created"
            ) from error

        self._check_integrity()
        self._ensure_migration_table()
        applied = self._read_and_validate_migration_receipts()
        for migration in self.migrations[len(applied) :]:
            self._apply_migration(migration)
        self._validate_schema_shape()
        return self.current_schema_version()

    def _check_integrity(self) -> None:
        try:
            with self.connection() as connection:
                row = connection.execute("PRAGMA quick_check(1)").fetchone()
                if row is None or row[0] != "ok":
                    raise WorkspaceDatabaseStateError(
                        "workspace database failed its integrity check"
                    )
        except sqlite3.DatabaseError as error:
            raise WorkspaceDatabaseStateError(
                "workspace database failed its integrity check"
            ) from error

    def _ensure_migration_table(self) -> None:
        with self.connection() as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
        if "schema_migrations" not in tables and tables:
            raise WorkspaceDatabaseStateError(
                "workspace database has unversioned application tables"
            )
        if "schema_migrations" not in tables:
            with self.transaction(write=True) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        checksum TEXT NOT NULL,
                        applied_at TEXT NOT NULL
                    )
                    """
                )

        with self.connection() as connection:
            columns = tuple(
                str(row[1])
                for row in connection.execute("PRAGMA table_info(schema_migrations)")
            )
        if columns != self._MIGRATION_COLUMNS:
            raise WorkspaceDatabaseStateError(
                "workspace migration metadata is incompatible"
            )

    def _read_and_validate_migration_receipts(self) -> list[sqlite3.Row]:
        with self.connection() as connection:
            rows = list(
                connection.execute(
                    "SELECT version, name, checksum, applied_at "
                    "FROM schema_migrations ORDER BY version"
                )
            )
        versions = [int(row["version"]) for row in rows]
        if versions and versions[-1] > self.latest_schema_version:
            raise WorkspaceDatabaseStateError(
                "workspace database schema is newer than this application"
            )
        if versions != list(range(1, len(versions) + 1)):
            raise WorkspaceDatabaseStateError(
                "workspace migration metadata contains a version gap"
            )
        for row, migration in zip(rows, self.migrations):
            if row["name"] != migration.name or row["checksum"] != migration.checksum:
                raise WorkspaceDatabaseStateError(
                    "workspace migration metadata does not match this application"
                )
        return rows

    def _apply_migration(self, migration: Migration) -> None:
        try:
            with self.transaction(write=True) as connection:
                for statement in migration.statements:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        migration.version,
                        migration.name,
                        migration.checksum,
                        datetime.now(timezone.utc)
                        .isoformat(timespec="microseconds")
                        .replace("+00:00", "Z"),
                    ),
                )
        except WorkspaceBusyError:
            raise
        except sqlite3.DatabaseError as error:
            raise WorkspaceMigrationError(
                f"workspace migration {migration.version} failed"
            ) from error

    def _validate_schema_shape(self) -> None:
        if self.migrations != MIGRATIONS:
            return
        required: set[str] = set()
        for version in range(1, self.latest_schema_version + 1):
            required.update(EXPECTED_TABLES_BY_VERSION[version])
        with self.connection() as connection:
            present = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        missing = sorted(required - present)
        if missing:
            raise WorkspaceDatabaseStateError(
                "workspace database is missing required schema objects"
            )

    def current_schema_version(self) -> int:
        try:
            with self.connection() as connection:
                row = connection.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
                ).fetchone()
        except sqlite3.DatabaseError as error:
            raise WorkspaceDatabaseStateError(
                "workspace migration metadata could not be read"
            ) from error
        return int(row[0]) if row else 0
