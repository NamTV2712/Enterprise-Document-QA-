"""Durable request accounting for a single bounded evaluation campaign.

The caller disables SDK retries. A reserved slot is never refunded, including
when the process exits between sending a request and recording its result.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Any

from src.evaluation.evidence_provenance import read_jsonl


class CampaignIncomplete(RuntimeError):
    """The campaign cannot make progress without exceeding its protocol."""


class ProviderOperationError(RuntimeError):
    """Safe provider error carrying redacted transport metadata for the ledger."""

    def __init__(self, error_type: str, status_code: int | None, metadata: dict[str, Any] | None = None):
        super().__init__(f"provider operation failed: {error_type}")
        self.provider_error_type = error_type
        self.status_code = status_code
        self.provider_metadata = {
            key: value
            for key, value in (metadata or {}).items()
            if key in {"key_alias", "pool_size", "transport_attempt", "status", "status_code", "retry_after", "provider_error_type"}
            and isinstance(value, (str, int, float, bool, type(None)))
        }
        self.provider_metadata["provider_error_type"] = error_type


def append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows, errors = read_jsonl(path)
    if errors:
        raise ValueError("; ".join(errors))
    return rows


class RequestLedger:
    """Single-writer ledger; every transport attempt consumes one slot."""

    def __init__(self, path: Path, campaign_id: str, limit: int = 60):
        if type(limit) is not int or not 1 <= limit <= 60:
            raise ValueError("request limit must be an integer in [1, 60]")
        self.path, self.campaign_id, self.limit = path, campaign_id, limit
        self._read()

    def _read(self) -> list[dict]:
        try:
            rows = read_records(self.path)
        except (OSError, ValueError) as error:
            raise CampaignIncomplete(f"invalid request ledger: {error}") from error
        if any(row.get("campaign_id") != self.campaign_id or row.get("limit") != self.limit for row in rows):
            raise CampaignIncomplete("ledger belongs to another campaign or budget")
        reserves = [row for row in rows if row.get("event") == "reserved"]
        if [row.get("slot") for row in reserves] != list(range(1, len(reserves) + 1)) or len(reserves) > self.limit:
            raise CampaignIncomplete("invalid ledger slot sequence")
        for reserve in reserves:
            if (
                not isinstance(reserve.get("operation"), str)
                or not isinstance(reserve.get("run_id"), str)
                or not isinstance(reserve.get("request_sha256"), str)
                or reserve.get("attempt") not in {1, 2}
            ):
                raise CampaignIncomplete("invalid request reservation identity")
        completed: set[int] = set()
        for row in rows:
            if row.get("event") not in {"reserved", "completed", "error"}:
                raise CampaignIncomplete("invalid ledger event")
            if row["event"] != "reserved":
                slot = row.get("slot")
                if type(slot) is not int or slot < 1 or slot > len(reserves) or slot in completed:
                    raise CampaignIncomplete("invalid ledger completion")
                original = reserves[slot - 1]
                if any(row.get(key) != original.get(key) for key in ("operation", "run_id", "request_sha256", "attempt")):
                    raise CampaignIncomplete("ledger completion identity mismatch")
                completed.add(slot)
        return rows

    @property
    def used(self) -> int:
        return sum(row["event"] == "reserved" for row in self._read())

    def call(self, operation: str, run_id: str, request_sha256: str,
             send: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            raise CampaignIncomplete("ledger is locked; inspect the previous writer before resuming") from error
        try:
            os.close(descriptor)
            return self._call_locked(operation, run_id, request_sha256, send)
        finally:
            lock.unlink()

    def _call_locked(self, operation: str, run_id: str, request_sha256: str,
                     send: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        rows = self._read()
        matching = [row for row in rows if row.get("operation") == operation]
        if any(row.get("run_id") != run_id or row.get("request_sha256") != request_sha256 for row in matching):
            raise CampaignIncomplete("operation inputs changed; refusing resume")
        completed = [row for row in matching if row["event"] == "completed"]
        if completed:
            return completed[-1]["response"]
        reserves = [row for row in matching if row["event"] == "reserved"]
        errors = [row for row in matching if row["event"] == "error"]
        if len(reserves) != len(errors):
            raise CampaignIncomplete("request outcome is unknown; reserved slot retained")
        if errors and (not errors[-1].get("retryable") or len(errors) >= 2):
            raise CampaignIncomplete("operation exhausted its retry protocol")
        for attempt in range(len(reserves) + 1, 3):
            if self.used >= self.limit:
                raise CampaignIncomplete("campaign request budget exhausted")
            identity = {"campaign_id": self.campaign_id, "limit": self.limit,
                        "operation": operation, "run_id": run_id,
                        "request_sha256": request_sha256, "slot": self.used + 1,
                        "attempt": attempt}
            append_record(self.path, {**identity, "event": "reserved"})
            try:
                response = send()
            except Exception as error:
                status = getattr(error, "status_code", None)
                retryable = status in {408, 429, 500, 502, 503, 504} or isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in {"APITimeoutError", "APIConnectionError"}
                error_record = {
                    **identity,
                    "event": "error",
                    "error_type": getattr(error, "provider_error_type", type(error).__name__),
                    "status_code": status,
                    "retryable": retryable,
                }
                provider_metadata = getattr(error, "provider_metadata", None)
                if isinstance(provider_metadata, dict):
                    error_record["provider"] = {
                        key: value
                        for key, value in provider_metadata.items()
                        if key in {"key_alias", "pool_size", "transport_attempt", "status", "status_code", "retry_after", "provider_error_type"}
                        and isinstance(value, (str, int, float, bool, type(None)))
                    }
                append_record(self.path, error_record)
                if not retryable or attempt == 2:
                    raise CampaignIncomplete(
                        str(error)
                        if isinstance(error, ProviderOperationError)
                        else "provider operation failed: " + type(error).__name__
                    ) from error
            else:
                append_record(self.path, {**identity, "event": "completed", "response": response})
                return response
        raise CampaignIncomplete("operation exhausted its retry protocol")
