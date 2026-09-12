"""Fail-closed publisher and reader for public evaluation summaries.

The public API must never browse arbitrary files under ``data``.  Reports are
published through this module into one fixed directory and are reduced to a
small allowlisted schema before they become visible to the frontend.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PUBLIC_REPORT_SCHEMA_VERSION = 1
PUBLIC_REPORTS_DIR = Path(
    os.environ.get("PUBLIC_EVALUATION_DIR", "data/public_evaluations")
)
REPORT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
STATUSES = frozenset({"official", "candidate", "historical", "incomplete"})

_PROVENANCE_KEYS = (
    "dataset_version",
    "corpus_fingerprint",
    "model_fingerprint",
    "profile_fingerprint",
    "rubric_fingerprint",
    "source_artifact_sha256",
)
_AGGREGATE_KEYS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "recall",
    "precision",
    "hit_rate",
    "mrr",
    "latency_ms",
    "sample_count",
)
_CASE_KEYS = (
    "case_id",
    "question",
    "language",
    "intent",
    "ticker",
    "status",
    "answer",
    "scores",
    "gates",
    "reasons",
    "evidence",
)


class PublicReportError(ValueError):
    """Raised when a report cannot be safely published or read."""


def _finite_number(value: Any, *, label: str) -> float | int:
    if type(value) not in (int, float) or value != value:
        raise PublicReportError(f"{label} must be a finite number")
    if isinstance(value, float) and (value == float("inf") or value == float("-inf")):
        raise PublicReportError(f"{label} must be a finite number")
    return value


def _string(value: Any, *, label: str, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise PublicReportError(f"{label} must be a non-empty string")
    return value.strip()


def _report_path(run_id: str, root: Path = PUBLIC_REPORTS_DIR) -> Path:
    if not isinstance(run_id, str) or not REPORT_ID_RE.fullmatch(run_id):
        raise PublicReportError("run_id contains unsupported characters")
    base = root.resolve()
    path = (base / f"{run_id}.json").resolve()
    if path.parent != base:
        raise PublicReportError("report path escapes the public report directory")
    return path


def _safe_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PublicReportError(f"{label} must be an object with string keys")
    return value


def _normalize_scores(value: Any, *, label: str) -> dict[str, float]:
    scores = _safe_mapping(value, label=label)
    output: dict[str, float] = {}
    for key, raw in scores.items():
        number = float(_finite_number(raw, label=f"{label}.{key}"))
        if not 0 <= number <= 1:
            raise PublicReportError(f"{label}.{key} must be between 0 and 1")
        output[key] = round(number, 6)
    return output


def _normalize_evidence(value: Any, *, label: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PublicReportError(f"{label} must be a list")
    output: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise PublicReportError(f"{label}[{index}] must be an object")
        citation = _string(item.get("citation"), label=f"{label}[{index}].citation", required=True)
        excerpt = _string(item.get("excerpt"), label=f"{label}[{index}].excerpt", required=True)
        output.append({"citation": citation or "", "excerpt": excerpt or ""})
    return output


def normalize_public_report(payload: Any, *, run_id: str | None = None) -> dict[str, Any]:
    """Validate and reduce one report to the public schema.

    Unknown top-level and case fields are deliberately ignored only after the
    required shape has been validated.  The publisher therefore cannot leak a
    full provider prompt, checkpoint binding inputs, or local file paths.
    """

    if not isinstance(payload, dict):
        raise PublicReportError("report must be an object")
    actual_run_id = _string(payload.get("run_id"), label="run_id", required=True)
    if run_id is not None and actual_run_id != run_id:
        raise PublicReportError("run_id does not match the requested output")
    assert actual_run_id is not None
    _report_path(actual_run_id)
    schema_version = payload.get("schema_version")
    if schema_version != PUBLIC_REPORT_SCHEMA_VERSION:
        raise PublicReportError("unsupported public report schema_version")
    status = _string(payload.get("status"), label="status", required=True)
    if status not in STATUSES:
        raise PublicReportError(f"unsupported report status: {status}")
    title = _string(payload.get("title"), label="title", required=True)
    created_at = _string(payload.get("created_at"), label="created_at", required=True)
    try:
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise PublicReportError("created_at must be an ISO-8601 timestamp") from error

    provenance = _safe_mapping(payload.get("provenance"), label="provenance")
    missing_provenance = [key for key in _PROVENANCE_KEYS if not _string(provenance.get(key), label=f"provenance.{key}")]
    if missing_provenance:
        raise PublicReportError(f"missing provenance bindings: {', '.join(missing_provenance)}")

    aggregate = _safe_mapping(payload.get("aggregate"), label="aggregate")
    public_aggregate: dict[str, float | int] = {}
    for key in _AGGREGATE_KEYS:
        if key not in aggregate:
            continue
        value = _finite_number(aggregate[key], label=f"aggregate.{key}")
        if key in {"faithfulness", "answer_relevancy", "context_precision", "recall", "precision", "hit_rate", "mrr"} and not 0 <= float(value) <= 1:
            raise PublicReportError(f"aggregate.{key} must be between 0 and 1")
        public_aggregate[key] = round(float(value), 6) if isinstance(value, float) else value

    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise PublicReportError("cases must be a non-empty list")
    cases: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    for index, raw_case in enumerate(raw_cases):
        if not isinstance(raw_case, dict):
            raise PublicReportError(f"cases[{index}] must be an object")
        case_id = _string(raw_case.get("case_id"), label=f"cases[{index}].case_id", required=True)
        question = _string(raw_case.get("question"), label=f"cases[{index}].question", required=True)
        if case_id in case_ids:
            raise PublicReportError(f"duplicate case_id: {case_id}")
        case_ids.add(case_id)
        language = _string(raw_case.get("language"), label=f"cases[{index}].language", required=True)
        if language not in {"en", "vi"}:
            raise PublicReportError(f"unsupported case language: {language}")
        case_status = _string(raw_case.get("status"), label=f"cases[{index}].status", required=True)
        if case_status not in {"OK", "ERROR", "MISSING"}:
            raise PublicReportError(f"unsupported case status: {case_status}")
        answer = _string(raw_case.get("answer"), label=f"cases[{index}].answer")
        reasons = raw_case.get("reasons", [])
        if not isinstance(reasons, list) or any(not isinstance(reason, str) for reason in reasons):
            raise PublicReportError(f"cases[{index}].reasons must be a string list")
        cases.append({
            "case_id": case_id,
            "question": question,
            "language": language,
            "intent": _string(raw_case.get("intent"), label=f"cases[{index}].intent"),
            "ticker": _string(raw_case.get("ticker"), label=f"cases[{index}].ticker"),
            "status": case_status,
            "answer": answer,
            "scores": _normalize_scores(raw_case.get("scores", {}), label=f"cases[{index}].scores"),
            "gates": _safe_mapping(raw_case.get("gates", {}), label=f"cases[{index}].gates"),
            "reasons": list(reasons),
            "evidence": _normalize_evidence(raw_case.get("evidence", []), label=f"cases[{index}].evidence"),
        })

    return {
        "schema_version": PUBLIC_REPORT_SCHEMA_VERSION,
        "run_id": actual_run_id,
        "title": title,
        "status": status,
        "created_at": created_at,
        "provenance": {key: str(provenance[key]) for key in _PROVENANCE_KEYS},
        "aggregate": public_aggregate,
        "cases": cases,
        "notes": [str(note) for note in payload.get("notes", []) if isinstance(note, str)],
    }


def publish_public_report(
    payload: Any,
    *,
    root: Path = PUBLIC_REPORTS_DIR,
    overwrite: bool = False,
) -> Path:
    """Validate and atomically publish a public report under ``root``."""

    normalized = normalize_public_report(payload)
    path = _report_path(normalized["run_id"], root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise PublicReportError(f"public report already exists: {path}")
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def list_public_reports(*, root: Path = PUBLIC_REPORTS_DIR) -> list[dict[str, Any]]:
    """Return validated summaries; malformed files are omitted fail-closed."""

    if not root.exists() or not root.is_dir():
        return []
    summaries: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            report = normalize_public_report(payload)
        except (OSError, json.JSONDecodeError, PublicReportError):
            continue
        summaries.append({
            key: report[key]
            for key in ("run_id", "title", "status", "created_at", "provenance", "aggregate")
        } | {"case_count": len(report["cases"])})
    return summaries


def get_public_report(run_id: str, *, root: Path = PUBLIC_REPORTS_DIR) -> dict[str, Any] | None:
    try:
        path = _report_path(run_id, root)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return normalize_public_report(payload, run_id=run_id)
    except (OSError, json.JSONDecodeError, PublicReportError):
        return None


def example_report(run_id: str = "recorded-demo-v1") -> dict[str, Any]:
    """Return a clearly labelled provider-free report for contract tests/UI demos."""

    return {
        "schema_version": 1,
        "run_id": run_id,
        "title": "Recorded evaluation contract demo (provider-free)",
        "status": "historical",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {key: f"demo-{key}" for key in _PROVENANCE_KEYS},
        "aggregate": {"faithfulness": 1.0, "answer_relevancy": 1.0, "context_precision": 1.0, "sample_count": 2},
        "cases": [
            {
                "case_id": "demo-en-fact",
                "question": "What revenue did the filing report?",
                "language": "en",
                "intent": "fact",
                "ticker": "AAPL",
                "status": "OK",
                "answer": "Recorded demo answer; not a live provider result.",
                "scores": {"faithfulness": 1.0, "answer_relevancy": 1.0, "context_precision": 1.0},
                "gates": {"contract": True},
                "reasons": [],
                "evidence": [{"citation": "Recorded fixture [Source 1]", "excerpt": "Curated demo excerpt."}],
            },
            {
                "case_id": "demo-vi-fact",
                "question": "Doanh thu được nêu trong hồ sơ là bao nhiêu?",
                "language": "vi",
                "intent": "fact",
                "ticker": "AAPL",
                "status": "OK",
                "answer": "Câu trả lời demo đã ghi sẵn; không phải kết quả provider trực tiếp.",
                "scores": {"faithfulness": 1.0, "answer_relevancy": 1.0, "context_precision": 1.0},
                "gates": {"contract": True},
                "reasons": [],
                "evidence": [{"citation": "Recorded fixture [Source 1]", "excerpt": "Đoạn trích demo được tuyển chọn."}],
            },
        ],
        "notes": ["Recorded mode only; this fixture must not be presented as an official benchmark."],
    }
