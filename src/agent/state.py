"""Bounded request-local state and safe operational results for one Agent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.agent.research_models import ResearchSummary, ResearchView


TOOL_NAMES = frozenset({"search_documents", "inspect_retrieval", "read_document", "ask_rag"})
_CREDENTIAL = re.compile(
    r"(?i)(?:\bauthorization\s*:|\bbearer\s+\S+|\b(?:groq_)?api[_-]?key\d*\s*[:=]|"
    r"\blocal_workspace_token\s*[:=]|\bsk-[A-Za-z0-9_-]{8,})"
)
_MACHINE_PATH = re.compile(r"(?i)(?:\b[A-Z]:[\\/]|/home/|/Users/|file://)")


def contains_sensitive_text(value: str) -> bool:
    return bool(_CREDENTIAL.search(value) or _MACHINE_PATH.search(value))


class AgentGoal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    text: str = Field(min_length=5, max_length=500)

    @field_validator("text")
    @classmethod
    def safe_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5 or contains_sensitive_text(value) or any(ord(ch) < 32 and ch not in "\t\n" for ch in value):
            raise ValueError("unsafe or empty Agent goal")
        return value


class AgentLimits(BaseModel):
    """All configurable limits have hard schema ceilings."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    max_steps: int = Field(default=8, ge=1, le=20)
    max_tool_calls: int = Field(default=5, ge=0, le=10)
    per_tool_calls: dict[str, int] = Field(default_factory=lambda: {
        "search_documents": 2,
        "inspect_retrieval": 2,
        "read_document": 3,
        "ask_rag": 1,
    })
    max_observations: int = Field(default=5, ge=0, le=10)
    max_evidence_per_observation: int = Field(default=8, ge=0, le=20)
    max_excerpt_chars: int = Field(default=160, ge=0, le=500)
    max_observation_bytes: int = Field(default=4096, ge=256, le=32768)
    max_total_observation_bytes: int = Field(default=16384, ge=256, le=65536)

    @field_validator("per_tool_calls")
    @classmethod
    def validate_per_tool_calls(cls, value: dict[str, int]) -> dict[str, int]:
        if set(value) != TOOL_NAMES or any(type(limit) is not int or not 0 <= limit <= 10 for limit in value.values()):
            raise ValueError("per-tool limits must cover the four registered tools and be between 0 and 10")
        return value


class AgentRunPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    allow_decision_provider_execution: bool = False
    require_observation_for_final: bool = True
    reject_duplicate_calls: bool = True


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    kind: Literal["document_id", "chunk_id", "search_id"]
    value: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def canonical_shape(self) -> "EvidenceRef":
        pattern = r"search-[0-9a-f]{16}" if self.kind == "search_id" else r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}"
        if not re.fullmatch(pattern, self.value):
            raise ValueError("invalid canonical evidence identity")
        return self


class EvidenceRecord(BaseModel):
    """One retained source; score field names retain their existing meanings."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    document_id: str | None = None
    chunk_id: str | None = None
    source_label: str | None = None
    citation: str | None = None
    score_kind: str | None = None
    scores: dict[str, float | None] = Field(default_factory=dict)
    excerpt: str = ""


class StageFact(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    name: str
    status: Literal["executed", "skipped", "not_executed"]
    elapsed_ms: float | None = None


class AgentObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    tool_name: str
    content_trust: Literal["untrusted_data"] = "untrusted_data"
    search_id: str | None = None
    evidence: tuple[EvidenceRecord, ...] = ()
    stages: tuple[StageFact, ...] = ()
    reported_items: int = 0
    truncated: bool = False


FailureDomain = Literal["model", "policy", "tool", "system"]
FailureCode = Literal[
    "decision_provider_required", "decision_provider_unavailable", "decision_execution_failed",
    "malformed_decision", "unknown_tool", "tool_not_allowed", "tool_provider_required",
    "invalid_arguments", "tool_unavailable", "tool_execution_failed", "final_without_observation",
    "invalid_evidence_reference", "invalid_citation", "duplicate_tool_call", "max_steps",
    "max_tool_calls", "per_tool_limit", "max_observations", "observation_bytes",
    "cancelled", "internal_error", "invalid_observation",
    "research_objective_required", "research_scope_mismatch", "research_search_limit",
    "research_unresolved_mismatch", "research_objective_uncited", "research_answer_too_long",
    "research_reference_limit",
]
AgentStatus = Literal[
    "completed", "invalid_decision", "policy_denied", "budget_exhausted",
    "unavailable", "failed", "cancelled",
]


class AgentFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    domain: FailureDomain
    code: FailureCode


class AgentTraceEntry(BaseModel):
    """Operational facts only; no model reasoning or raw provider output."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    decision_index: int
    kind: Literal["tool", "final", "invalid"]
    tool_name: str | None = None
    objective_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,31}$")
    argument_names: tuple[str, ...] = ()
    outcome: Literal["observed", "completed", "rejected", "failed"]
    evidence_refs: tuple[EvidenceRef, ...] = ()
    failure_code: FailureCode | None = None


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    status: AgentStatus
    answer: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    step_count: int
    decision_call_count: int
    tool_call_count: int
    per_tool_calls: dict[str, int]
    observations: tuple[AgentObservation, ...]
    trace: tuple[AgentTraceEntry, ...]
    failure: AgentFailure | None = None
    research: ResearchSummary | None = None


class DecisionToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    name: str
    description: str
    input_schema: dict[str, Any]
    provider_execution: bool
    side_effect: str


class DecisionPolicyView(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    allowed_tools: tuple[str, ...]
    require_observation_for_final: bool
    provider_tool_execution_allowed: bool
    max_steps: int
    max_tool_calls: int
    per_tool_calls: dict[str, int]
    observation_trust: Literal["untrusted_data"] = "untrusted_data"


class DecisionRequest(BaseModel):
    """Separate policy, user goal and untrusted observations for model adapters."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    system_policy: DecisionPolicyView
    user_goal: str
    locale: Literal["en", "vi"]
    tools: tuple[DecisionToolSpec, ...]
    observations: tuple[AgentObservation, ...]
    step_count: int
    tool_call_count: int
    research: ResearchView | None = None


@dataclass
class AgentState:
    goal: AgentGoal
    locale: Literal["en", "vi"]
    step_count: int = 0
    decision_call_count: int = 0
    tool_call_count: int = 0
    per_tool_calls: dict[str, int] = field(default_factory=lambda: {name: 0 for name in sorted(TOOL_NAMES)})
    observations: list[AgentObservation] = field(default_factory=list)
    trace: list[AgentTraceEntry] = field(default_factory=list)
    seen_calls: set[str] = field(default_factory=set)
    observation_bytes: int = 0
    research_view: ResearchView | None = None
    research_summary: ResearchSummary | None = None
