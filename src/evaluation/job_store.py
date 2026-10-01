"""Private frozen evaluation data inside the DATA-004 workspace database.

Jobs, revisions, lifecycle, and events remain owned by SQLiteJobRepository.
These tables hold only immutable evidence, attempted-call receipts, case
results, and a validated private report linked to those durable jobs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from src.evaluation.native_protocol import MAX_REPORT_BYTES, NativeReport, _unique_object, canonical_report_bytes, parse_native_report
from src.retrieval.canonical_json import canonical_json_bytes
from src.workspace.database import WorkspaceDatabase
from src.workspace.jobs import _configured_secret_values, _validate_safe_tree


MAX_ARTIFACT_BYTES = 16_000_000
MAX_CASE_RESULT_BYTES = 1_200_000


class EvaluationStoreError(ValueError):
    """The immutable private evaluation data is missing or inconsistent."""


class EvaluationBudgetExhausted(EvaluationStoreError):
    """No more provider transport attempts may begin."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvaluationJobStore:
    def __init__(self, database: WorkspaceDatabase) -> None:
        self.database = database

    def register_artifact(self, content: bytes) -> str:
        if not content or len(content) > MAX_ARTIFACT_BYTES:
            raise EvaluationStoreError("frozen artifact is empty or too large")
        try:
            _validate_safe_tree(json.loads(content, object_pairs_hook=_unique_object), _configured_secret_values())
        except (ValueError, UnicodeDecodeError) as error:
            raise EvaluationStoreError("frozen artifact contains unsafe private data") from error
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        with self.database.transaction(write=True) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO evaluation_artifacts(artifact_digest, content, byte_count) VALUES (?, ?, ?)",
                (digest, content, len(content)),
            )
            stored = connection.execute(
                "SELECT content, byte_count FROM evaluation_artifacts WHERE artifact_digest = ?", (digest,)
            ).fetchone()
            if stored is None or bytes(stored["content"]) != content or stored["byte_count"] != len(content):
                raise EvaluationStoreError("frozen artifact digest collision or corruption")
        return digest

    def artifact(self, digest: str) -> bytes:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT content FROM evaluation_artifacts WHERE artifact_digest = ?", (digest,)
            ).fetchone()
        if row is None:
            raise EvaluationStoreError("frozen artifact is unavailable")
        content = bytes(row["content"])
        if "sha256:" + hashlib.sha256(content).hexdigest() != digest:
            raise EvaluationStoreError("frozen artifact digest mismatch")
        return content

    def reserve_attempt(self, job_id: str, case_id: str, phase: str) -> int:
        """Consume one frozen attempt slot before transport in one transaction."""
        if phase not in {"generation", "correction", "judging"}:
            raise ValueError("invalid provider attempt reservation")
        with self.database.transaction(write=True) as connection:
            job = connection.execute(
                "SELECT namespace, state, payload_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if job is None or job["namespace"] != "evaluation" or job["state"] != "running":
                raise EvaluationStoreError("evaluation job is not executing")
            snapshot = json.loads(job["payload_json"])
            limit = snapshot.get("budget_limit")
            if type(limit) is not int or not 1 <= limit <= 15000 or case_id not in snapshot.get("case_ids", []):
                raise EvaluationStoreError("provider attempt does not match the frozen job")
            used = int(connection.execute(
                "SELECT COUNT(*) FROM evaluation_attempts WHERE job_id = ?", (job_id,)
            ).fetchone()[0])
            if used >= limit:
                raise EvaluationBudgetExhausted("frozen provider attempt budget exhausted")
            if connection.execute(
                "SELECT 1 FROM evaluation_attempts WHERE job_id = ? AND case_id = ? AND phase = ?",
                (job_id, case_id, phase),
            ).fetchone() is not None:
                raise EvaluationStoreError("provider attempt was already reserved")
            ordinal = used + 1
            connection.execute(
                "INSERT INTO evaluation_attempts(job_id, ordinal, case_id, phase, attempted_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, ordinal, case_id, phase, _now()),
            )
            return ordinal

    def attempted_count(self, job_id: str) -> int:
        with self.database.transaction() as connection:
            return int(connection.execute(
                "SELECT COUNT(*) FROM evaluation_attempts WHERE job_id = ?", (job_id,)
            ).fetchone()[0])

    def commit_case(self, job_id: str, ordinal: int, case_id: str, result: dict[str, Any]) -> None:
        encoded = canonical_json_bytes(result)
        if len(encoded) > MAX_CASE_RESULT_BYTES:
            raise EvaluationStoreError("private case result is too large")
        try:
            _validate_safe_tree(result, _configured_secret_values())
        except ValueError as error:
            raise EvaluationStoreError("private case result contains unsafe private data") from error
        with self.database.transaction(write=True) as connection:
            job = connection.execute(
                "SELECT namespace, state, payload_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if job is None or job["namespace"] != "evaluation" or job["state"] not in {"running", "cancelling"}:
                raise EvaluationStoreError("evaluation job cannot commit a case")
            identifiers = json.loads(job["payload_json"]).get("case_ids", [])
            if not 0 <= ordinal < len(identifiers) or identifiers[ordinal] != case_id or result.get("case_id") != case_id:
                raise EvaluationStoreError("case result does not match the frozen job")
            existing = connection.execute(
                "SELECT ordinal, result_json FROM evaluation_case_results WHERE job_id = ? AND case_id = ?",
                (job_id, case_id),
            ).fetchone()
            if existing is not None:
                if existing["ordinal"] == ordinal and existing["result_json"] == encoded.decode("utf-8"):
                    return
                raise EvaluationStoreError("evaluation case result conflict")
            connection.execute(
                "INSERT INTO evaluation_case_results(job_id, ordinal, case_id, result_json, committed_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (job_id, ordinal, case_id, encoded.decode("utf-8"), _now()),
            )

    def list_cases(self, job_id: str, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("invalid evaluation case page")
        with self.database.transaction() as connection:
            total = int(connection.execute(
                "SELECT COUNT(*) FROM evaluation_case_results WHERE job_id = ?", (job_id,)
            ).fetchone()[0])
            rows = connection.execute(
                "SELECT result_json FROM evaluation_case_results WHERE job_id = ? ORDER BY ordinal LIMIT ? OFFSET ?",
                (job_id, limit, offset),
            ).fetchall()
        return [json.loads(row["result_json"]) for row in rows], total

    def all_cases(self, job_id: str) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT result_json FROM evaluation_case_results WHERE job_id = ? ORDER BY ordinal", (job_id,)
            ).fetchall()
        return [json.loads(row["result_json"]) for row in rows]

    def commit_report(self, job_id: str, report: NativeReport) -> None:
        content = canonical_report_bytes(report)
        if len(content) > MAX_REPORT_BYTES or parse_native_report(content) != report:
            raise EvaluationStoreError("native report did not validate")
        with self.database.transaction(write=True) as connection:
            job = connection.execute(
                "SELECT namespace, state, payload_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if job is None or job["namespace"] != "evaluation" or job["state"] not in {"running", "cancelling"}:
                raise EvaluationStoreError("evaluation job cannot commit a report")
            snapshot = json.loads(job["payload_json"])
            if (report.run_id != job_id or len(report.cases) != len(snapshot["case_ids"])
                    or set(case.case_id for case in report.cases) != set(snapshot["case_ids"])
                    or canonical_json_bytes(report.binding.__dict__) != canonical_json_bytes(snapshot["binding"])):
                raise EvaluationStoreError("native report does not match the frozen job")
            row = connection.execute("SELECT report_json FROM evaluation_reports WHERE job_id = ?", (job_id,)).fetchone()
            if row is not None:
                if bytes(row["report_json"]) == content:
                    return
                raise EvaluationStoreError("private report conflict")
            connection.execute(
                "INSERT INTO evaluation_reports(job_id, report_json, committed_at) VALUES (?, ?, ?)",
                (job_id, content, _now()),
            )

    def report(self, job_id: str) -> NativeReport | None:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT report_json FROM evaluation_reports WHERE job_id = ?", (job_id,)).fetchone()
        return parse_native_report(bytes(row["report_json"])) if row is not None else None
