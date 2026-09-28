"""Versioned, provider-free operational metrics for recorded Agent runs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from src.agent.durable_models import AgentRunEventResponse, AgentRunResponse


PROTOCOL_NAME = "native-agent-evaluation"
PROTOCOL_VERSION = 1
METRIC_VERSION = 1
MAX_REPORT_BYTES = 64 * 1024

MetricStatus = Literal["computed", "unavailable", "not_applicable"]
ValueKind = Literal["boolean", "count", "ratio"]
Direction = Literal["higher_is_better", "lower_is_better", "neutral"]


class AgentEvaluationError(ValueError):
    """An Agent snapshot or evaluation report violates the v1 contract."""


class CorruptAgentSnapshot(AgentEvaluationError):
    """Recorded Agent facts are internally inconsistent or unsafe."""


class CorruptAgentEvaluationReport(AgentEvaluationError):
    """Serialized evaluation results do not match the v1 protocol."""


@dataclass(frozen=True)
class AgentMetricDefinition:
    metric_id: str
    metric_version: int
    label: str
    description: str
    value_kind: ValueKind
    direction: Direction
    applicability: str
    numerator: str
    denominator: str | None
    source_fields: tuple[str, ...]
    meaning: str
    non_meaning: str
    minimum: int
    maximum: int | None


def _definition(
    suffix: str, label: str, kind: ValueKind, direction: Direction,
    applicability: str, numerator: str, denominator: str | None,
    sources: tuple[str, ...], meaning: str, non_meaning: str,
) -> AgentMetricDefinition:
    return AgentMetricDefinition(
        f"native_agent.{suffix}", METRIC_VERSION, label, meaning, kind, direction,
        applicability, numerator, denominator, sources, meaning, non_meaning,
        0, 1 if kind in ("boolean", "ratio") else None,
    )


METRIC_DEFINITIONS: tuple[AgentMetricDefinition, ...] = (
    _definition("execution_completed", "Execution completed", "boolean", "higher_is_better",
                "terminal run", "run.state == succeeded and result.agent_status == completed", "one run",
                ("run.state", "result.agent_status"), "Execution ended with an answer.",
                "Does not establish factual correctness."),
    _definition("recorded_tool_decision_count", "Recorded tool decisions", "count", "neutral",
                "terminal run", "number of tool decision events", None,
                ("events.summary.decision_kind",), "Counts recorded tool choices.",
                "Does not include an action without a committed event."),
    _definition("admitted_tool_call_count", "Recorded admitted tool calls", "count", "neutral",
                "terminal run", "tool events with observed or failed outcome", None,
                ("events.summary.outcome",), "Counts recorded calls admitted to execution.",
                "Does not measure optimal tool use."),
    _definition("tool_admission_fraction", "Tool admission fraction", "ratio", "higher_is_better",
                "at least one recorded tool decision", "admitted tool events", "all tool decision events",
                ("events.summary.decision_kind", "events.summary.outcome"),
                "Fraction of recorded tool choices admitted to execution.",
                "Does not mean that an admitted tool succeeded."),
    _definition("invalid_tool_attempt_count", "Invalid tool attempts", "count", "lower_is_better",
                "terminal run", "rejected tool events with unknown_tool or invalid_arguments", None,
                ("events.summary.failure_code",), "Counts structurally invalid recorded tool choices.",
                "Does not infer malicious intent."),
    _definition("policy_denial_attempt_count", "Policy denial attempts", "count", "lower_is_better",
                "terminal run", "rejected tool policy/research events plus decision_provider_required terminal denial", None,
                ("events.summary.failure_code", "result.failure.code"),
                "Counts recorded actions denied by frozen tool or decision-provider policy.",
                "Does not assign a security score or attacker intent."),
    _definition("duplicate_rejection_count", "Duplicate rejections", "count", "lower_is_better",
                "terminal run", "rejected tool events with duplicate_tool_call", None,
                ("events.summary.failure_code",), "Counts exact repeated work rejected by the loop.",
                "Does not detect every unnecessary call."),
    _definition("tool_failure_fraction", "Tool failure fraction", "ratio", "lower_is_better",
                "at least one admitted tool call", "admitted tool events with failed outcome", "admitted tool events",
                ("events.summary.outcome",), "Fraction of admitted calls ending in a typed failure.",
                "Does not count invalid tool selection as a service failure."),
    _definition("tool_unavailable_count", "Tool unavailable count", "count", "neutral",
                "terminal run", "failed tool events with tool_unavailable", None,
                ("events.summary.failure_code",), "Counts recorded tool availability failures.",
                "Does not measure Agent reasoning quality."),
    _definition("invalid_final_attempt_count", "Invalid final attempts", "count", "lower_is_better",
                "terminal run", "rejected final decision events", None,
                ("events.summary.decision_kind", "events.summary.outcome"),
                "Counts recorded final-contract rejections.", "Does not verify claim truth."),
    _definition("step_budget_utilization", "Step budget utilization", "ratio", "neutral",
                "terminal result present", "result.step_count", "frozen.limits.max_steps",
                ("result.step_count", "frozen.limits.max_steps"), "Fraction of frozen step capacity used.",
                "Neither high nor low use is inherently better."),
    _definition("tool_budget_utilization", "Tool budget utilization", "ratio", "neutral",
                "terminal result and positive tool limit", "result.tool_call_count", "frozen.limits.max_tool_calls",
                ("result.tool_call_count", "frozen.limits.max_tool_calls"),
                "Fraction of frozen tool-call capacity used.", "Neither high nor low use is inherently better."),
    _definition("budget_exhausted", "Budget exhausted", "boolean", "neutral",
                "terminal result present", "result.agent_status == budget_exhausted", "one run",
                ("result.agent_status",), "Reports the actual terminal budget outcome.",
                "Cannot be inferred from utilization alone."),
    _definition("decision_provider_unavailable", "Decision provider unavailable", "boolean", "neutral",
                "terminal result present", "result.failure.code == decision_provider_unavailable", "one run",
                ("result.failure.code",), "Reports a decision-provider availability outcome.",
                "Does not mean the Agent answered incorrectly."),
    _definition("evidence_identity_validity", "Evidence identity validity", "ratio", "higher_is_better",
                "research ledger has evidence entries", "structurally valid ledger entries", "ledger entries",
                ("result.research.evidence",), "Checks canonical document/chunk identity consistency.",
                "Does not establish relevance, source truth or claim support."),
    _definition("final_reference_validity", "Final reference validity", "ratio", "higher_is_better",
                "completed final has refs and complete current-run ID metadata", "current-run structured refs", "final refs",
                ("result.evidence_refs", "result.research.evidence", "events.summary.evidence_refs"),
                "Checks structured final IDs against retained current-run source IDs.",
                "Does not resolve Source labels or verify semantic citation support."),
    _definition("objective_coverage", "Objective coverage", "ratio", "higher_is_better",
                "research result present", "sufficient objective statuses", "configured objectives",
                ("frozen.research.objectives", "result.research.objectives"),
                "Fraction meeting the bounded agent_research_v1 evidence threshold.",
                "Does not prove factual completeness."),
    _definition("unresolved_gap_fraction", "Unresolved gap fraction", "ratio", "lower_is_better",
                "research result present", "typed unresolved gaps", "configured objectives",
                ("result.research.gaps", "frozen.research.objectives"),
                "Fraction of configured objectives with a typed unresolved gap.",
                "Does not prove that the answer is incorrect."),
    _definition("research_evidence_count", "Research evidence entries", "count", "neutral",
                "research result present", "canonical ledger entries", None,
                ("result.research.evidence",), "Counts retained canonical entries.",
                "Does not measure source relevance."),
    _definition("distinct_document_count", "Distinct documents", "count", "neutral",
                "research result present", "distinct non-null document IDs in ledger", None,
                ("result.research.evidence.document_id",), "Counts distinct represented documents.",
                "More documents are not automatically better."),
    _definition("distinct_chunk_count", "Distinct chunks", "count", "neutral",
                "research result present", "distinct chunk IDs in ledger", None,
                ("result.research.evidence.chunk_id",), "Counts distinct represented chunks.",
                "More chunks are not automatically better."),
)


def validate_metric_definitions(definitions: tuple[AgentMetricDefinition, ...]) -> None:
    """Keep metric names, versions, ordering and semantic declarations explicit."""
    if not definitions or len({item.metric_id for item in definitions}) != len(definitions):
        raise AgentEvaluationError("empty or duplicate Agent metric definitions")
    for item in definitions:
        if not re.fullmatch(r"native_agent\.[a-z][a-z0-9_]*", item.metric_id):
            raise AgentEvaluationError("invalid Agent metric ID")
        if type(item.metric_version) is not int or item.metric_version < 1:
            raise AgentEvaluationError("invalid Agent metric version")
        if not all((item.label, item.description, item.applicability, item.numerator,
                    item.source_fields, item.meaning, item.non_meaning)):
            raise AgentEvaluationError("incomplete Agent metric semantics")
        if item.value_kind not in ("boolean", "count", "ratio") or item.direction not in (
            "higher_is_better", "lower_is_better", "neutral",
        ):
            raise AgentEvaluationError("invalid Agent metric kind or direction")
        if item.minimum != 0 or item.maximum != (None if item.value_kind == "count" else 1):
            raise AgentEvaluationError("invalid Agent metric range")
        if item.value_kind == "ratio" and not item.denominator:
            raise AgentEvaluationError("ratio metric needs a denominator")


validate_metric_definitions(METRIC_DEFINITIONS)


@dataclass(frozen=True)
class AgentEvaluationCase:
    """One authoritative durable run and its complete bounded event history."""

    run: AgentRunResponse
    events: tuple[AgentRunEventResponse, ...]


@dataclass(frozen=True)
class AgentMetricResult:
    metric_id: str
    metric_version: int
    status: MetricStatus
    value: float | int | bool | None
    numerator: int | None
    denominator: int | None
    reason_code: str | None


@dataclass(frozen=True)
class AgentEvaluationFacts:
    terminal_state: str
    agent_status: str | None
    failure_code: str | None
    recorded_per_tool_calls: tuple[tuple[str, int], ...]
    rejected_tool_codes: tuple[tuple[str, int], ...]
    gap_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class AgentEvaluationProvenance:
    configuration_fingerprint: str
    frozen_plan_sha256: str
    event_sha256: str
    result_sha256: str | None
    run_revision: int
    agent_protocol: str
    research_version: str | None


@dataclass(frozen=True)
class AgentEvaluationReport:
    protocol: str
    protocol_version: int
    run_id: str
    metric_definitions: tuple[AgentMetricDefinition, ...]
    metrics: tuple[AgentMetricResult, ...]
    facts: AgentEvaluationFacts
    provenance: AgentEvaluationProvenance
    digest: str
