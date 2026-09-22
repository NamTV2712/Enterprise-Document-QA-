"""Existing in-memory conversation session routes."""

import re
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException


SESSION_ID_MAX_LENGTH = 100
SESSION_ID_PATTERN = re.compile(rf"^[A-Za-z0-9_-]{{1,{SESSION_ID_MAX_LENGTH}}}$")


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise HTTPException(
            status_code=400,
            detail=(
                "Session ID may only contain letters, digits, hyphens, "
                f"and underscores (max {SESSION_ID_MAX_LENGTH} characters)"
            ),
        )


def create_session_router(get_pipeline: Callable[[], Any]) -> APIRouter:
    router = APIRouter()

    @router.delete("/session/{session_id}")
    async def clear_session(session_id: str) -> dict:
        """Clear one conversation session."""
        _validate_session_id(session_id)
        pipeline = get_pipeline()
        pipeline.memory.clear_session(session_id)
        return {"cleared": session_id}

    @router.get("/session/{session_id}/history")
    async def get_session_history(session_id: str) -> dict:
        """Return conversation history for debugging and UI rendering.

        The optional ``context`` block reports backend session state without
        creating or refreshing the session: ``available`` with the TTL budget
        that remains, or ``missing`` when the session expired or never existed.
        """
        _validate_session_id(session_id)
        pipeline = get_pipeline()
        snapshot = pipeline.memory.get_history_snapshot(session_id)
        return {
            "session_id": session_id,
            "turns": [
                {
                    "user": turn.user_message,
                    "assistant": turn.assistant_message,
                    "rewritten_query": turn.rewritten_query,
                }
                for turn in snapshot.turns
            ],
            "context": {
                "status": snapshot.status,
                "retained_turns": snapshot.retained_turns,
                "ttl_remaining_seconds": snapshot.ttl_remaining_seconds,
            },
        }

    return router
