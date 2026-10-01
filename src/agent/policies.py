"""Invocation policy; orchestration budgets belong to AGENT-002."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


@dataclass(frozen=True)
class ToolPolicy:
    allowed_tools: frozenset[str]
    allow_provider_execution: bool = False

    def __post_init__(self) -> None:
        if type(self.allow_provider_execution) is not bool:
            raise ValueError("invalid provider execution policy")
        if any(not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in self.allowed_tools):
            raise ValueError("invalid Agent tool allowlist")
        object.__setattr__(self, "allowed_tools", frozenset(self.allowed_tools))


@dataclass(frozen=True)
class AgentExecutionContext:
    policy: ToolPolicy
    request_id: str | None = None
    locale: Literal["en", "vi"] = "en"

    def __post_init__(self) -> None:
        if self.locale not in ("en", "vi"):
            raise ValueError("unsupported Agent locale")
        if self.request_id is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", self.request_id):
            raise ValueError("invalid Agent request identity")
