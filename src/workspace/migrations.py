"""Deterministic SQLite migrations for the local workspace foundation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        payload = "\0".join(
            (str(self.version), self.name, *self.statements)
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


CORE_FOUNDATION = Migration(
    version=1,
    name="core_workspace_foundation",
    statements=(
        """
        CREATE TABLE workspace_records (
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (entity_type, entity_id)
        )
        """,
        """
        CREATE TABLE tombstones (
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            deleted_at TEXT NOT NULL,
            PRIMARY KEY (entity_type, entity_id)
        )
        """,
        """
        CREATE TABLE workspace_imports (
            import_id TEXT PRIMARY KEY,
            source_digest TEXT NOT NULL UNIQUE,
            source_schema_version INTEGER NOT NULL CHECK (source_schema_version >= 1),
            status TEXT NOT NULL CHECK (status IN ('previewed', 'committed', 'failed')),
            counts_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        """,
        """
        CREATE TABLE workspace_settings (
            setting_key TEXT PRIMARY KEY CHECK (
                setting_key IN ('telemetry_retention_days', 'log_retention_days')
            ),
            value_json TEXT NOT NULL,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            updated_at TEXT NOT NULL
        )
        """,
    ),
)


RESEARCH_DOMAINS = Migration(
    version=2,
    name="research_domain_foundation",
    statements=(
        """
        CREATE TABLE conversations (
            conversation_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            title TEXT NOT NULL,
            content_json TEXT NOT NULL,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE collections (
            collection_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            tags_json TEXT NOT NULL DEFAULT '[]',
            favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE collection_items (
            item_id TEXT PRIMARY KEY,
            collection_id TEXT NOT NULL,
            item_kind TEXT NOT NULL CHECK (
                item_kind IN ('document', 'evidence', 'answer', 'note')
            ),
            reference_json TEXT NOT NULL,
            snapshot_json TEXT,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (collection_id) REFERENCES collections(collection_id)
                ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX collection_items_collection_idx
        ON collection_items (collection_id, created_at, item_id)
        """,
        """
        CREATE TABLE notes (
            note_id TEXT PRIMARY KEY,
            collection_id TEXT NOT NULL,
            note_text TEXT NOT NULL,
            evidence_ref_json TEXT,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (collection_id) REFERENCES collections(collection_id)
                ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX notes_collection_idx
        ON notes (collection_id, created_at, note_id)
        """,
        """
        CREATE TABLE activity_events (
            activity_id TEXT PRIMARY KEY,
            collection_id TEXT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            FOREIGN KEY (collection_id) REFERENCES collections(collection_id)
                ON DELETE SET NULL
        )
        """,
        """
        CREATE INDEX activity_collection_idx
        ON activity_events (collection_id, occurred_at, activity_id)
        """,
    ),
)


OPERATIONS_FOUNDATION = Migration(
    version=3,
    name="operations_foundation",
    statements=(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            namespace TEXT NOT NULL CHECK (namespace IN ('pipeline', 'evaluation', 'model_test')),
            job_type TEXT NOT NULL,
            state TEXT NOT NULL CHECK (
                state IN ('queued', 'running', 'cancelling', 'cancelled', 'succeeded', 'failed', 'interrupted')
            ),
            configuration_fingerprint TEXT NOT NULL,
            artifact_run_id TEXT,
            failure_code TEXT,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT
        )
        """,
        """
        CREATE TABLE job_steps (
            step_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
            step_name TEXT NOT NULL,
            state TEXT NOT NULL CHECK (
                state IN ('pending', 'running', 'cancelled', 'succeeded', 'failed', 'skipped', 'interrupted')
            ),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            started_at TEXT,
            finished_at TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
            UNIQUE (job_id, ordinal)
        )
        """,
        """
        CREATE TABLE job_events (
            event_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            event_type TEXT NOT NULL,
            state TEXT,
            reason_code TEXT,
            progress_current INTEGER,
            progress_total INTEGER,
            occurred_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
            UNIQUE (job_id, sequence)
        )
        """,
        """
        CREATE INDEX job_events_order_idx
        ON job_events (job_id, sequence)
        """,
        """
        CREATE TABLE telemetry_events (
            telemetry_id TEXT PRIMARY KEY,
            event_name TEXT NOT NULL,
            route_template TEXT,
            capability TEXT,
            status TEXT NOT NULL,
            duration_ms REAL CHECK (duration_ms IS NULL OR duration_ms >= 0),
            occurred_at TEXT NOT NULL,
            retention_until TEXT NOT NULL
        )
        """,
        """
        CREATE INDEX telemetry_retention_idx
        ON telemetry_events (retention_until, telemetry_id)
        """,
    ),
)


DURABLE_JOB_CONTRACT = Migration(
    version=4,
    name="durable_job_contract",
    statements=(
        "ALTER TABLE jobs ADD COLUMN record_schema_version INTEGER",
        "ALTER TABLE jobs ADD COLUMN idempotency_key_hash TEXT",
        "ALTER TABLE jobs ADD COLUMN payload_json TEXT",
        "ALTER TABLE jobs ADD COLUMN artifact_references_json TEXT",
        "ALTER TABLE jobs ADD COLUMN progress_stage TEXT",
        "ALTER TABLE jobs ADD COLUMN progress_current INTEGER",
        "ALTER TABLE jobs ADD COLUMN progress_total INTEGER",
        "ALTER TABLE jobs ADD COLUMN result_json TEXT",
        "ALTER TABLE jobs ADD COLUMN failure_message TEXT",
        "ALTER TABLE jobs ADD COLUMN cancellation_requested_at TEXT",
        "ALTER TABLE job_events ADD COLUMN progress_stage TEXT",
        """
        CREATE UNIQUE INDEX jobs_idempotency_idx
        ON jobs (namespace, idempotency_key_hash)
        WHERE idempotency_key_hash IS NOT NULL
        """,
        """
        CREATE INDEX jobs_listing_idx
        ON jobs (namespace, state, created_at DESC, job_id DESC)
        """,
    ),
)


FROZEN_EVALUATION_JOBS = Migration(
    version=5,
    name="frozen_evaluation_jobs",
    statements=(
        """
        CREATE TABLE evaluation_artifacts (
            artifact_digest TEXT PRIMARY KEY,
            content BLOB NOT NULL,
            byte_count INTEGER NOT NULL CHECK (byte_count > 0 AND byte_count <= 16000000)
        )
        """,
        """
        CREATE TABLE evaluation_attempts (
            job_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
            case_id TEXT NOT NULL,
            phase TEXT NOT NULL CHECK (phase IN ('generation', 'correction', 'judging')),
            attempted_at TEXT NOT NULL,
            PRIMARY KEY (job_id, ordinal),
            UNIQUE (job_id, case_id, phase),
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE evaluation_case_results (
            job_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
            case_id TEXT NOT NULL,
            result_json TEXT NOT NULL,
            committed_at TEXT NOT NULL,
            PRIMARY KEY (job_id, case_id),
            UNIQUE (job_id, ordinal),
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE evaluation_reports (
            job_id TEXT PRIMARY KEY,
            report_json BLOB NOT NULL,
            committed_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
        )
        """,
    ),
)


MIGRATIONS: tuple[Migration, ...] = (
    CORE_FOUNDATION,
    RESEARCH_DOMAINS,
    OPERATIONS_FOUNDATION,
    DURABLE_JOB_CONTRACT,
    FROZEN_EVALUATION_JOBS,
)

LATEST_SCHEMA_VERSION = MIGRATIONS[-1].version

EXPECTED_TABLES_BY_VERSION: dict[int, frozenset[str]] = {
    1: frozenset(
        {
            "schema_migrations",
            "workspace_records",
            "tombstones",
            "workspace_imports",
            "workspace_settings",
        }
    ),
    2: frozenset(
        {
            "conversations",
            "collections",
            "collection_items",
            "notes",
            "activity_events",
        }
    ),
    3: frozenset({"jobs", "job_steps", "job_events", "telemetry_events"}),
    4: frozenset(),
    5: frozenset({"evaluation_artifacts", "evaluation_attempts", "evaluation_case_results", "evaluation_reports"}),
}


def validate_migration_sequence(migrations: tuple[Migration, ...]) -> None:
    """Require one deterministic, gap-free migration sequence starting at 1."""
    if not migrations:
        raise ValueError("at least one workspace migration is required")
    versions = [migration.version for migration in migrations]
    if versions != list(range(1, len(migrations) + 1)):
        raise ValueError("workspace migrations must be ordered and contiguous from version 1")
    names = [migration.name for migration in migrations]
    if len(names) != len(set(names)) or any(not name for name in names):
        raise ValueError("workspace migration names must be non-empty and unique")
    if any(not migration.statements for migration in migrations):
        raise ValueError("workspace migrations must contain SQL statements")
