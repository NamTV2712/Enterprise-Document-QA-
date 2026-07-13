"""
Module: conversation_memory.py
Stores conversation history per session.
The interface is designed for easy backend switching
(in-memory to SQLite or Redis) without modifying the calling code.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 5       # Number of turns retained to pass to LLM
SESSION_TTL_SECONDS = 1800  # Sessions expire after 30 minutes of inactivity


@dataclass
class Turn:
    """One turn is one user/assistant exchange."""
    user_message: str
    assistant_message: str
    timestamp: float = field(default_factory=time.monotonic)
    rewritten_query: str | None = None   # Rewritten query for debugging.


@dataclass
class ConversationSession:
    session_id: str
    turns: list[Turn] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)
    last_active: float = field(default_factory=time.monotonic)

    def add_turn(self, turn: Turn) -> None:
        self.turns.append(turn)
        self.last_active = time.monotonic()

    def get_recent_turns(self, n: int = MAX_HISTORY_TURNS) -> list[Turn]:
        return self.turns[-n:]

    def is_expired(self, ttl: float = SESSION_TTL_SECONDS) -> bool:
        return (time.monotonic() - self.last_active) > ttl

    def to_llm_messages(self, n: int = MAX_HISTORY_TURNS) -> list[dict]:
        """Format history into OpenAI-style messages for the LLM."""
        messages = []
        for turn in self.get_recent_turns(n):
            messages.append({"role": "user", "content": turn.user_message})
            messages.append({"role": "assistant", "content": turn.assistant_message})
        return messages


class ConversationMemory:
    """In-memory session store with TTL-based cleanup.

    To switch to SQLite, implement the same interface in a SQLite backend.
    Calling code should not need to change.
    """

    def __init__(self, session_ttl: float = SESSION_TTL_SECONDS):
        self._sessions: dict[str, ConversationSession] = {}
        self._ttl = session_ttl
        self._lock = threading.RLock()

    def get_or_create(self, session_id: str) -> ConversationSession:
        with self._lock:
            self._cleanup_expired()
            if session_id not in self._sessions:
                self._sessions[session_id] = ConversationSession(session_id=session_id)
                logger.info("New session: %s", session_id)
            return self._sessions[session_id]

    def add_turn(self, session_id: str, turn: Turn) -> None:
        with self._lock:
            session = self.get_or_create(session_id)
            session.add_turn(turn)

    def get_history(
        self, session_id: str, n: int = MAX_HISTORY_TURNS
    ) -> list[Turn]:
        with self._lock:
            if session_id not in self._sessions:
                return []
            return list(self._sessions[session_id].get_recent_turns(n))

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            logger.info("Cleared session: %s", session_id)

    def _cleanup_expired(self) -> None:
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired(self._ttl)
        ]
        for sid in expired:
            del self._sessions[sid]
            logger.debug("Expired session cleaned up: %s", sid)

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "active_sessions": len(self._sessions),
                "total_turns": sum(
                    len(s.turns) for s in self._sessions.values()
                ),
            }
