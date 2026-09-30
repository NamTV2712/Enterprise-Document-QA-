"""Private, bounded AGENT-003 run and event contracts."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.agent.research import validate_research_limits
from src.agent.provider_models import DecisionProviderIdentity
from src.agent.research_models import ResearchConfig, ResearchSummary
from src.agent.state import (
    AgentFailure, AgentGoal, AgentLimits, AgentStatus, EvidenceRef, TOOL_NAMES,
)
from src.workspace.jobs import JobState, JobStepState


class AgentRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    goal: str = Field(min_length=5, max_length=500)
    locale: Literal["en", "vi"] = "en"
    allowed_tools: list[Literal["search_documents", "inspect_retrieval", "read_document", "ask_rag"]] = Field(
        default_factory=lambda: ["search_documents", "inspect_retrieval", "read_document"],
        max_length=4,
    )
    allow_provider_tool_execution: bool = False
    allow_decision_provider_execution: bool = False
    require_observation_for_final: bool = True
    reject_duplicate_calls: bool = True
    limits: AgentLimits = Field(default_factory=AgentLimits)
    research: ResearchConfig | None = None

    @model_validator(mode="after")
    def safe_request(self) -> "AgentRunCreateRequest":
        AgentGoal(text=self.goal)
        if any(ord(character) < 32 or ord(character) == 127 for character in self.goal):
            raise ValueError("durable Agent goals cannot contain control characters")
        if len(set(self.allowed_tools)) != len(self.allowed_tools):
            raise ValueError("allowed tools must be unique")
        if self.research is not None:
            validate_research_limits(self.research, self.limits)
        return self


class FrozenAgentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal[1] = 1
    protocol: Literal["bounded_single_agent"] = "bounded_single_agent"
    decision_model_id: str = Field(min_length=1, max_length=64)
    decision_provider: DecisionProviderIdentity | None = None
    goal: str = Field(min_length=5, max_length=500)
    locale: Literal["en", "vi"]
    allowed_tools: tuple[str, ...] = Field(max_length=4)
    allow_provider_tool_execution: bool
    allow_decision_provider_execution: bool
    require_observation_for_final: bool
    reject_duplicate_calls: bool
    limits: AgentLimits
    research: ResearchConfig | None = None

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def json_tools(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def safe_plan(self) -> "FrozenAgentPlan":
        AgentGoal(text=self.goal)
        if any(ord(character) < 32 or ord(character) == 127 for character in self.goal):
            raise ValueError("frozen Agent goal contains controls")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.decision_model_id):
            raise ValueError("decision model identity is invalid")
        if self.decision_provider is not None and self.decision_model_id != self.decision_provider.binding_id:
            raise ValueError("decision provider binding is inconsistent")
        if len(set(self.allowed_tools)) != len(self.allowed_tools) or not set(self.allowed_tools) <= TOOL_NAMES:
            raise ValueError("frozen tool allowlist is invalid")
        if self.research is not None:
            validate_research_limits(self.research, self.limits)
        return self


class AgentDurableResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    agent_status: AgentStatus
    answer: str | None = Field(default=None, max_length=4000)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default=(), max_length=20)
    step_count: int = Field(ge=0, le=20)
    decision_call_count: int = Field(ge=0, le=20)
    tool_call_count: int = Field(ge=0, le=10)
    per_tool_calls: dict[str, int]
    observation_count: int = Field(ge=0, le=10)
    failure: AgentFailure | None = None
    research: ResearchSummary | None = None

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def json_refs(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def coherent_result(self) -> "AgentDurableResult":
        if set(self.per_tool_calls) != TOOL_NAMES or any(
            type(value) is not int or not 0 <= value <= 10 for value in self.per_tool_calls.values()
        ) or sum(self.per_tool_calls.values()) != self.tool_call_count:
            raise ValueError("durable tool counters are inconsistent")
        if self.agent_status == "completed":
            if self.answer is None or self.failure is not None:
                raise ValueError("completed Agent result needs an answer without failure")
        elif self.answer is not None:
            raise ValueError("non-completed Agent result cannot carry an answer")
        return self


class AgentRunStep(BaseModel):
    name: Literal["execute_agent"]
    state: JobStepState
    revision: int
    started_at: str | None
    finished_at: str | None


class AgentRunFailure(BaseModel):
    code: str
    message: str


class AgentRunResponse(BaseModel):
    run_id: str
    state: JobState
    revision: int
    configuration_fingerprint: str
    frozen: FrozenAgentPlan
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None
    cancellation_requested_at: str | None
    progress_current: int | None
    progress_total: int | None
    step: AgentRunStep
    result: AgentDurableResult | None
    failure: AgentRunFailure | None


class AgentRunPage(BaseModel):
    items: list[AgentRunResponse]
    total: int
    page: int
    page_size: int


class AgentRunResultResponse(BaseModel):
    run_id: str
    state: JobState
    revision: int
    result: AgentDurableResult | None
    failure: AgentRunFailure | None


class AgentEventSummary(BaseModel):
    decision_index: int = Field(ge=1, le=20)
    decision_kind: Literal["tool", "final", "invalid"]
    tool_name: str | None = None
    objective_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,31}$")
    argument_names: list[str] = Field(default_factory=list, max_length=16)
    outcome: Literal["observed", "completed", "rejected", "failed"]
    evidence_count: int = Field(ge=0, le=20)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list, max_length=8)
    step_count: int = Field(ge=0, le=20)
    tool_call_count: int = Field(ge=0, le=10)
    failure_code: str | None = None


class AgentRunEventResponse(BaseModel):
    run_id: str
    event_id: str
    sequence: int
    event_type: str
    state: JobState | None
    reason_code: str | None
    occurred_at: str
    summary: AgentEventSummary | None = None
