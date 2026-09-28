"""Strict structured decisions and a provider-independent model protocol."""

from __future__ import annotations

import math
import re
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from src.agent.state import DecisionRequest, EvidenceRef, contains_sensitive_text


DecisionScalar = str | int | float | bool | None


class ToolDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    kind: Literal["tool"]
    tool_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    arguments: dict[str, DecisionScalar]
    objective_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,31}$")

    @field_validator("arguments")
    @classmethod
    def bounded_arguments(cls, value: dict[str, DecisionScalar]) -> dict[str, DecisionScalar]:
        if len(value) > 16:
            raise ValueError("too many tool arguments")
        for key, item in value.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key):
                raise ValueError("invalid tool argument name")
            if isinstance(item, str) and (len(item) > 500 or contains_sensitive_text(item)):
                raise ValueError("unsafe tool argument")
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("non-finite tool argument")
        return value


class FinalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    kind: Literal["final"]
    answer: str = Field(min_length=1, max_length=4000)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default=(), max_length=20)
    unresolved_objective_ids: tuple[str, ...] = Field(default=(), max_length=6)

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def json_array_refs(cls, value: object) -> object:
        # JSON has arrays, not tuples. Keep every nested item strictly validated.
        return tuple(value) if isinstance(value, list) else value

    @field_validator("unresolved_objective_ids", mode="before")
    @classmethod
    def json_unresolved_ids(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("unresolved_objective_ids")
    @classmethod
    def bounded_unresolved_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", item) for item in value):
            raise ValueError("invalid unresolved objective ID")
        return value

    @field_validator("answer")
    @classmethod
    def safe_answer(cls, value: str) -> str:
        if not value.strip() or contains_sensitive_text(value):
            raise ValueError("unsafe or empty final answer")
        return value.strip()

    @model_validator(mode="after")
    def unique_refs(self) -> "FinalDecision":
        keys = [(ref.kind, ref.value) for ref in self.evidence_refs]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate evidence reference")
        return self


AgentDecision = Annotated[ToolDecision | FinalDecision, Field(discriminator="kind")]
DECISION_ADAPTER = TypeAdapter(AgentDecision)


def parse_decision(value: Any) -> ToolDecision | FinalDecision:
    """Accept only a structured object; never extract instructions from prose."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if not isinstance(value, dict):
        raise ValueError("decision must be a structured object")
    return DECISION_ADAPTER.validate_python(value, strict=True)


class DecisionProviderUnavailable(Exception):
    """A decision-model provider is unavailable; no raw response is retained."""


class DecisionExecutionError(Exception):
    """A decision model failed before returning a structured decision."""


class AgentDecisionModel(Protocol):
    """One decision per call. Provider adapters must preserve request trust roles."""

    requires_provider: bool

    async def decide(self, request: DecisionRequest) -> object: ...
