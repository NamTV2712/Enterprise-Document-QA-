"""Append-only accounting for a multi-campaign provider budget.

``RequestLedger`` protects one campaign's protocol (historically 60 slots).
This ledger protects the improvement round across fresh campaigns and counts
every actual transport attempt, including retries.  A reservation without a
terminal event is intentionally unrecoverable: the provider outcome is
unknown and the slot remains consumed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from src.evaluation.request_ledger import CampaignIncomplete, append_record, read_records


class ProviderBudgetLedger:
    """Single-writer, append-only budget shared by provider campaigns."""

    def __init__(self, path: Path, round_id: str, limit: int = 2_000):
        if type(limit) is not int or not 1 <= limit <= 2_000:
            raise ValueError("provider round limit must be an integer in [1, 2000]")
        self.path = path
        self.round_id = round_id
        self.limit = limit
        self._read()

    def _read(self) -> list[dict[str, Any]]:
        try:
            rows = read_records(self.path)
        except (OSError, ValueError) as error:
            raise CampaignIncomplete(f"invalid provider round ledger: {error}") from error
        reserves = [row for row in rows if row.get("event") == "reserved"]
        if any(
            row.get("round_id") != self.round_id or row.get("limit") != self.limit
            for row in rows
        ):
            raise CampaignIncomplete("provider round ledger belongs to another budget")
        if [row.get("slot") for row in reserves] != list(range(1, len(reserves) + 1)):
            raise CampaignIncomplete("invalid provider round slot sequence")
        if len(reserves) > self.limit:
            raise CampaignIncomplete("provider round budget exhausted")
        completed: set[int] = set()
        for row in rows:
            if row.get("event") not in {"reserved", "completed", "error"}:
                raise CampaignIncomplete("invalid provider round event")
            if row.get("event") == "reserved":
                if not isinstance(row.get("campaign_id"), str) or not isinstance(
                    row.get("operation"), str
                ):
                    raise CampaignIncomplete("invalid provider round reservation")
                continue
            slot = row.get("slot")
            if type(slot) is not int or not 1 <= slot <= len(reserves) or slot in completed:
                raise CampaignIncomplete("invalid provider round completion")
            original = reserves[slot - 1]
            for key in ("campaign_id", "operation", "request_sha256"):
                if row.get(key) != original.get(key):
                    raise CampaignIncomplete("provider round completion identity mismatch")
            completed.add(slot)
        return rows

    @property
    def used(self) -> int:
        return sum(row.get("event") == "reserved" for row in self._read())

    def _lock(self) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            return os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            raise CampaignIncomplete(
                "provider round ledger is locked; inspect the previous writer before resuming"
            ) from error

    def reserve(
        self,
        *,
        campaign_id: str,
        operation: str,
        request_sha256: str,
    ) -> int:
        """Reserve one actual provider attempt and return its immutable slot."""
        descriptor = self._lock()
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            rows = self._read()
            matching = [
                row
                for row in rows
                if row.get("campaign_id") == campaign_id
                and row.get("operation") == operation
            ]
            if any(row.get("request_sha256") != request_sha256 for row in matching):
                raise CampaignIncomplete("provider round operation inputs changed")
            reserved_slots = {
                row.get("slot") for row in matching if row.get("event") == "reserved"
            }
            terminal_by_slot = {
                row.get("slot"): row.get("event")
                for row in matching
                if row.get("event") in {"completed", "error"}
            }
            if any(slot not in terminal_by_slot for slot in reserved_slots):
                raise CampaignIncomplete("provider round outcome is unknown; slot retained")
            if any(event == "completed" for event in terminal_by_slot.values()):
                raise CampaignIncomplete("provider round operation already completed")
            used = len([row for row in rows if row.get("event") == "reserved"])
            if used >= self.limit:
                raise CampaignIncomplete("provider round budget exhausted")
            slot = used + 1
            append_record(
                self.path,
                {
                    "event": "reserved",
                    "round_id": self.round_id,
                    "limit": self.limit,
                    "slot": slot,
                    "campaign_id": campaign_id,
                    "operation": operation,
                    "request_sha256": request_sha256,
                },
            )
            return slot
        finally:
            os.close(descriptor)
            lock.unlink()

    def finish(
        self,
        *,
        slot: int,
        campaign_id: str,
        operation: str,
        request_sha256: str,
        event: str = "completed",
        error_type: str | None = None,
    ) -> None:
        if event not in {"completed", "error"}:
            raise ValueError("provider round terminal event must be completed or error")
        descriptor = self._lock()
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            rows = self._read()
            reserve = next(
                (
                    row
                    for row in rows
                    if row.get("event") == "reserved" and row.get("slot") == slot
                ),
                None,
            )
            if reserve is None or any(
                reserve.get(key) != value
                for key, value in {
                    "campaign_id": campaign_id,
                    "operation": operation,
                    "request_sha256": request_sha256,
                }.items()
            ):
                raise CampaignIncomplete("provider round completion identity mismatch")
            if any(row.get("slot") == slot and row.get("event") != "reserved" for row in rows):
                raise CampaignIncomplete("provider round slot already completed")
            record: dict[str, Any] = {
                "event": event,
                "round_id": self.round_id,
                "limit": self.limit,
                "slot": slot,
                "campaign_id": campaign_id,
                "operation": operation,
                "request_sha256": request_sha256,
            }
            if error_type:
                record["error_type"] = error_type
            append_record(self.path, record)
        finally:
            os.close(descriptor)
            lock.unlink()

    def call(
        self,
        *,
        campaign_id: str,
        operation: str,
        request_sha256: str,
        send: Callable[[], Any],
    ) -> Any:
        """Account one provider attempt around ``send``; never refund slots."""
        slot = self.reserve(
            campaign_id=campaign_id,
            operation=operation,
            request_sha256=request_sha256,
        )
        try:
            result = send()
        except Exception as error:
            self.finish(
                slot=slot,
                campaign_id=campaign_id,
                operation=operation,
                request_sha256=request_sha256,
                event="error",
                error_type=type(error).__name__,
            )
            raise
        self.finish(
            slot=slot,
            campaign_id=campaign_id,
            operation=operation,
            request_sha256=request_sha256,
        )
        return result
