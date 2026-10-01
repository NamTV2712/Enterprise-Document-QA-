"""OBS-001 timing contract; fake clocks and deterministic boundaries, no network."""
import asyncio
import json

import pytest
from pydantic import ValidationError

from src.workspace.attribution import (
    MAX_API_SPANS, PHASES, PROTOCOL, TimingSpan, TimingSummary,
    capture, defer_database_observations, record_interval, span, timed,
)


def test_monotonic_zero_and_nested_union_remainder():
    ticks = iter([0, 1_000_000, 2_000_000, 2_000_000, 4_000_000, 10_000_000])
    with capture("api", clock=lambda: next(ticks)) as trace:
        with span("api.total"):
            with span("api.access"):
                with span("api.validation"):
                    pass
    root, child, grandchild = sorted(trace.records, key=lambda item: item.ordinal)
    assert root.duration_ms == 10 and child.duration_ms == 3 and grandchild.duration_ms == 0
    assert child.parent == root.ordinal and grandchild.parent == child.ordinal
    summary = trace.summary()
    assert summary.remainder_ms == 7  # Union; the nested zero interval is not added.
    assert TimingSummary.model_validate_json(summary.model_dump_json()) == summary
    assert summary.protocol == PROTOCOL


@pytest.mark.parametrize("changes", [
    {"phase": "user.goal"}, {"operation": "SELECT * FROM private"},
    {"outcome": "arbitrary"}, {"start_ns": -1}, {"end_ns": -1},
    {"start_ns": 2, "end_ns": 1}, {"start_ns": float("nan")},
    {"end_ns": float("inf")}, {"metadata": {"goal": "untrusted text"}},
    {"ordinal": True}, {"parent": 1},
])
def test_closed_timing_shape_rejects_unsafe_or_nonfinite_values(changes):
    values = {"phase": "api.total", "ordinal": 1, "start_ns": 0, "end_ns": 1}
    with pytest.raises(ValidationError):
        TimingSpan.model_validate({**values, **changes})


def test_unknown_phase_fails_closed_even_when_disabled():
    with pytest.raises(ValueError, match="unsupported attribution phase"):
        with span("injected.tool"):
            pytest.fail("unknown phase admitted")
    assert len(PHASES) == 32


def test_exception_cleanup_and_no_exception_body_capture():
    sentinel = "SECRET_BODY_synthetic_only"
    with capture("api") as trace:
        with pytest.raises(RuntimeError):
            with span("api.access"):
                raise RuntimeError(sentinel)
        with span("api.validation"):
            pass
    assert {record.outcome for record in trace.records} == {"failed", "completed"}
    assert sentinel not in trace.summary().model_dump_json()
    with span("api.access"):
        pass
    assert len(trace.records) == 2


def test_async_cancellation_records_category_and_resets_context():
    @timed("agent.decision")
    async def cancelled():
        raise asyncio.CancelledError
    async def run():
        with capture("worker") as trace:
            with pytest.raises(asyncio.CancelledError):
                await cancelled()
        assert trace.records[0].outcome == "cancelled"
        return trace
    assert asyncio.run(run()).summary().phases[0].cancelled == 1


def test_span_and_deferred_budgets_are_hard_bounds():
    with capture("api") as trace:
        with defer_database_observations():
            for _ in range(1000):
                record_interval("workspace.transaction", 0, 1)
    assert len(trace.records) == MAX_API_SPANS
    assert trace.dropped == 1000 - MAX_API_SPANS
    assert trace.summary().remainder_ms is None
    assert len(trace.summary().model_dump_json().encode()) < 16384


def test_deferred_nested_parent_ordinals_are_preserved():
    with capture("api") as trace:
        with span("api.total"):
            with defer_database_observations():
                with span("workspace.initialize"):
                    with span("workspace.transaction"):
                        pass
    ordered = sorted(trace.records, key=lambda row: row.ordinal)
    assert [row.parent for row in ordered] == [None, 1, 2]
    assert json.loads(trace.summary().model_dump_json())["span_count"] == 3
