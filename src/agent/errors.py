"""Content-free error categories for future operational traces."""

from __future__ import annotations

from typing import Literal

ToolErrorCode = Literal[
    "unknown_tool", "tool_not_allowed", "invalid_arguments", "unavailable",
    "execution_failed", "provider_required",
]


class AgentToolError(Exception):
    def __init__(self, code: ToolErrorCode):
        self.code = code
        super().__init__(code)
