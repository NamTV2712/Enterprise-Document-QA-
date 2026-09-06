"""Backend session-history context metadata and TTL correctness tests."""

from __future__ import annotations

import pytest

from src.memory.conversation_memory import ConversationMemory, Turn


@pytest.fixture()
def memory(monkeypatch: pytest.MonkeyPatch) -> tuple[ConversationMemory, list[float]]:
    """A memory whose monotonic clock is driven by a mutable list."""
    clock = [1000.0]
    monkeypatch.setattr(
        "src.memory.conversation_memory.time.monotonic", lambda: clock[0]
    )
    return ConversationMemory(session_ttl=1800.0), clock


def test_missing_session_reports_missing_context(memory) -> None:
    instance, _ = memory
    snapshot = instance.get_history_snapshot("unknown")
    assert snapshot.status == "missing"
    assert snapshot.turns == []
    assert snapshot.retained_turns == 0
    assert snapshot.ttl_remaining_seconds == 0.0


def test_available_session_reports_remaining_ttl(memory) -> None:
    instance, clock = memory
    instance.add_turn("s1", Turn(user_message="q", assistant_message="a"))
    clock[0] += 600.0
    snapshot = instance.get_history_snapshot("s1")
    assert snapshot.status == "available"
    assert snapshot.retained_turns == 1
    assert snapshot.ttl_remaining_seconds == pytest.approx(1200.0)


def test_reading_history_does_not_extend_ttl(memory) -> None:
    instance, clock = memory
    instance.add_turn("s1", Turn(user_message="q", assistant_message="a"))
    clock[0] += 1000.0
    first = instance.get_history_snapshot("s1")
    assert first.status == "available"
    clock[0] += 100.0
    second = instance.get_history_snapshot("s1")
    assert second.status == "available"
    # TTL keeps decreasing across reads instead of resetting to the full 1800.
    assert second.ttl_remaining_seconds == pytest.approx(
        first.ttl_remaining_seconds - 100.0
    )


def test_expired_session_reports_missing_with_zero_ttl(memory) -> None:
    instance, clock = memory
    instance.add_turn("s1", Turn(user_message="q", assistant_message="a"))
    clock[0] += 1801.0
    snapshot = instance.get_history_snapshot("s1")
    assert snapshot.status == "missing"
    assert snapshot.turns == []
    assert snapshot.retained_turns == 0
    assert snapshot.ttl_remaining_seconds == 0.0


def test_history_and_metadata_come_from_one_snapshot(memory) -> None:
    instance, _ = memory
    for index in range(7):
        instance.add_turn("s1", Turn(user_message=f"q{index}", assistant_message=f"a{index}"))
    snapshot = instance.get_history_snapshot("s1")
    assert snapshot.status == "available"
    assert snapshot.retained_turns == 5
    assert [turn.user_message for turn in snapshot.turns] == [
        "q2",
        "q3",
        "q4",
        "q5",
        "q6",
    ]


def test_history_read_does_not_create_session(memory) -> None:
    instance, clock = memory
    instance.get_history_snapshot("ghost")
    clock[0] += 10.0
    # The unknown session must not have been created by the read.
    assert instance.get_stats()["active_sessions"] == 0
