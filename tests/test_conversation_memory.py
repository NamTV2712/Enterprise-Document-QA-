from src.memory.conversation_memory import (
    ConversationMemory,
    ConversationSession,
    Turn,
)


def test_new_session_created_empty() -> None:
    memory = ConversationMemory()

    session = memory.get_or_create("session-a")

    assert session.session_id == "session-a"
    assert session.turns == []


def test_add_turn_persists_in_session() -> None:
    memory = ConversationMemory()

    memory.add_turn(
        "session-a",
        Turn(
            user_message="What are Apple's risks?",
            assistant_message="Apple faces competition...",
        ),
    )

    history = memory.get_history("session-a")
    assert len(history) == 1
    assert history[0].user_message == "What are Apple's risks?"


def test_session_isolation() -> None:
    memory = ConversationMemory()
    memory.add_turn("session-a", Turn(user_message="A1", assistant_message="A1-answer"))
    memory.add_turn("session-b", Turn(user_message="B1", assistant_message="B1-answer"))

    history_a = memory.get_history("session-a")
    history_b = memory.get_history("session-b")

    assert len(history_a) == 1
    assert len(history_b) == 1
    assert history_a[0].user_message == "A1"
    assert history_b[0].user_message == "B1"


def test_max_history_turns_limits_returned_turns() -> None:
    memory = ConversationMemory()
    for i in range(10):
        memory.add_turn("session-a", Turn(user_message=f"Q{i}", assistant_message=f"A{i}"))

    recent = memory.get_history("session-a", n=3)

    assert len(recent) == 3
    assert recent[0].user_message == "Q7"
    assert recent[-1].user_message == "Q9"


def test_session_expires_after_ttl(monkeypatch) -> None:
    memory = ConversationMemory(session_ttl=0.5)
    memory.add_turn("session-a", Turn(user_message="Q", assistant_message="A"))
    memory.get_or_create("session-a").last_active = 0.0

    monkeypatch.setattr("src.memory.conversation_memory.time.monotonic", lambda: 1.0)
    memory.get_or_create("session-b")

    assert memory.get_history("session-a") == []


def test_clear_session_removes_only_target_session() -> None:
    memory = ConversationMemory()
    memory.add_turn("session-a", Turn(user_message="Q", assistant_message="A"))
    memory.add_turn("session-b", Turn(user_message="Q", assistant_message="A"))

    memory.clear_session("session-a")

    assert memory.get_history("session-a") == []
    assert len(memory.get_history("session-b")) == 1


def test_to_llm_messages_format() -> None:
    session = ConversationSession(session_id="s")
    session.add_turn(Turn(user_message="Hi", assistant_message="Hello"))

    messages = session.to_llm_messages()

    assert messages == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]
