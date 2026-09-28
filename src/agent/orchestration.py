"""One bounded in-memory Agent state machine over the AGENT-001 registry."""

from __future__ import annotations

import hashlib
import json
import re
from threading import Event

from pydantic import ValidationError

from src.agent.decision import (
    AgentDecisionModel, DecisionExecutionError, DecisionProviderUnavailable,
    FinalDecision, ToolDecision, parse_decision,
)
from src.agent.errors import AgentToolError
from src.agent.observation import ObservationIntegrityError, ObservationLimitError, project_observation
from src.agent.policies import AgentExecutionContext
from src.agent.registry import AgentToolRegistry
from src.agent.state import (
    AgentFailure, AgentGoal, AgentLimits, AgentResult, AgentRunPolicy, AgentState,
    AgentStatus, AgentTraceEntry, DecisionPolicyView, DecisionRequest,
    DecisionToolSpec, EvidenceRef, FailureCode, FailureDomain,
    TOOL_NAMES,
)


_SOURCE_LABEL = re.compile(r"\[Source\s+[1-9][0-9]*\]")
_SEARCH_ID = re.compile(r"\bsearch-[0-9a-f]{16}\b")
_DOCUMENT_ID = re.compile(r"\b[A-Z]{1,5}:[A-Za-z0-9_.-]{4,128}\b")
_CHUNK_ID = re.compile(r"\b[A-Z]{1,5}_[0-9]{8,}_[A-Za-z0-9_]+\b")


def _observed_refs(state: AgentState) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for observation in state.observations:
        if observation.search_id:
            refs.add(("search_id", observation.search_id))
        for record in observation.evidence:
            if record.document_id:
                refs.add(("document_id", record.document_id))
            if record.chunk_id:
                refs.add(("chunk_id", record.chunk_id))
    return refs


def _observation_refs(observation) -> tuple[EvidenceRef, ...]:
    refs: set[tuple[str, str]] = set()
    if observation.search_id:
        refs.add(("search_id", observation.search_id))
    for record in observation.evidence:
        if record.document_id:
            refs.add(("document_id", record.document_id))
        if record.chunk_id:
            refs.add(("chunk_id", record.chunk_id))
    return tuple(EvidenceRef(kind=kind, value=value) for kind, value in sorted(refs))


def _validate_final(state: AgentState, decision: FinalDecision, policy: AgentRunPolicy) -> FailureCode | None:
    if policy.require_observation_for_final and not state.observations:
        return "final_without_observation"
    observed = _observed_refs(state)
    cited = {(ref.kind, ref.value) for ref in decision.evidence_refs}
    if not cited <= observed:
        return "invalid_evidence_reference"

    source_records: dict[str, set[tuple[str | None, str | None]]] = {}
    for observation in state.observations:
        for record in observation.evidence:
            if record.source_label:
                source_records.setdefault(record.source_label, set()).add(
                    (record.document_id, record.chunk_id)
                )
    for label in _SOURCE_LABEL.findall(decision.answer):
        matches = source_records.get(label, set())
        if len(matches) != 1 or not any(
            (kind, value) in cited
            for document_id, chunk_id in matches
            for kind, value in (("chunk_id", chunk_id), ("document_id", document_id))
            if value is not None
        ):
            return "invalid_citation"
    for pattern, kind in (
        (_SEARCH_ID, "search_id"), (_DOCUMENT_ID, "document_id"), (_CHUNK_ID, "chunk_id"),
    ):
        for value in pattern.findall(decision.answer):
            if (kind, value) not in cited:
                return "invalid_citation"
    return None


class AgentOrchestrator:
    """Exactly one decision model chooses one action at a time; no persistence."""

    def __init__(
        self, registry: AgentToolRegistry, decision_model: AgentDecisionModel,
        *, limits: AgentLimits | None = None, policy: AgentRunPolicy | None = None,
    ) -> None:
        if type(decision_model.requires_provider) is not bool:
            raise ValueError("decision model provider classification must be explicit")
        if {tool.name for tool in registry.list()} != TOOL_NAMES:
            raise ValueError("orchestration requires the four canonical Agent tools")
        self.registry = registry
        self.decision_model = decision_model
        self.limits = limits or AgentLimits()
        self._per_tool_limits = dict(self.limits.per_tool_calls)
        self.policy = policy or AgentRunPolicy()

    def _request(self, state: AgentState, context: AgentExecutionContext) -> DecisionRequest:
        available = tuple(
            tool for tool in self.registry.list()
            if tool.name in context.policy.allowed_tools
            and (not tool.provider_execution or context.policy.allow_provider_execution)
        )
        return DecisionRequest(
            system_policy=DecisionPolicyView(
                allowed_tools=tuple(tool.name for tool in available),
                require_observation_for_final=self.policy.require_observation_for_final,
                provider_tool_execution_allowed=context.policy.allow_provider_execution,
                max_steps=self.limits.max_steps, max_tool_calls=self.limits.max_tool_calls,
                per_tool_calls=dict(self._per_tool_limits),
            ),
            user_goal=state.goal.text, locale=state.locale,
            tools=tuple(DecisionToolSpec(
                name=tool.name, description=tool.description,
                input_schema=tool.schema(), provider_execution=tool.provider_execution,
                side_effect=tool.side_effect,
            ) for tool in available),
            observations=tuple(observation.model_copy(deep=True) for observation in state.observations),
            step_count=state.step_count, tool_call_count=state.tool_call_count,
        )

    @staticmethod
    def _result(
        state: AgentState, status: AgentStatus, *,
        domain: FailureDomain | None = None, code: FailureCode | None = None,
        answer: str | None = None, evidence_refs: tuple[EvidenceRef, ...] = (),
    ) -> AgentResult:
        return AgentResult(
            status=status, answer=answer, evidence_refs=evidence_refs,
            step_count=state.step_count, decision_call_count=state.decision_call_count,
            tool_call_count=state.tool_call_count, per_tool_calls=dict(state.per_tool_calls),
            observations=tuple(state.observations), trace=tuple(state.trace),
            failure=AgentFailure(domain=domain, code=code) if domain and code else None,
        )

    @staticmethod
    def _reject_tool(
        state: AgentState, decision: ToolDecision, status: AgentStatus,
        domain: FailureDomain, code: FailureCode,
    ) -> AgentResult:
        state.trace.append(AgentTraceEntry(
            decision_index=state.decision_call_count, kind="tool", tool_name=decision.tool_name,
            argument_names=tuple(sorted(decision.arguments)), outcome="rejected", failure_code=code,
        ))
        return AgentOrchestrator._result(state, status, domain=domain, code=code)

    async def run(
        self, goal: str, context: AgentExecutionContext, *, cancel_event: Event | None = None,
    ) -> AgentResult:
        """One validated decision is one step; only executed tools consume tool budget."""
        state = AgentState(goal=AgentGoal(text=goal), locale=context.locale)
        if self.decision_model.requires_provider and not self.policy.allow_decision_provider_execution:
            return self._result(state, "policy_denied", domain="policy", code="decision_provider_required")

        for _ in range(self.limits.max_steps):
            if cancel_event is not None and cancel_event.is_set():
                return self._result(state, "cancelled", domain="system", code="cancelled")
            state.decision_call_count += 1
            try:
                raw_decision = await self.decision_model.decide(self._request(state, context))
            except DecisionProviderUnavailable:
                return self._result(state, "unavailable", domain="model", code="decision_provider_unavailable")
            except DecisionExecutionError:
                return self._result(state, "failed", domain="model", code="decision_execution_failed")
            except Exception:
                return self._result(state, "failed", domain="system", code="internal_error")
            if cancel_event is not None and cancel_event.is_set():
                return self._result(state, "cancelled", domain="system", code="cancelled")

            try:
                decision = parse_decision(raw_decision)
            except (ValueError, ValidationError, TypeError):
                state.trace.append(AgentTraceEntry(
                    decision_index=state.decision_call_count, kind="invalid",
                    outcome="rejected", failure_code="malformed_decision",
                ))
                return self._result(state, "invalid_decision", domain="model", code="malformed_decision")
            state.step_count += 1

            if isinstance(decision, FinalDecision):
                failure = _validate_final(state, decision, self.policy)
                if failure is not None:
                    state.trace.append(AgentTraceEntry(
                        decision_index=state.decision_call_count, kind="final",
                        outcome="rejected", failure_code=failure,
                    ))
                    return self._result(state, "invalid_decision", domain="policy", code=failure)
                state.trace.append(AgentTraceEntry(
                    decision_index=state.decision_call_count, kind="final", outcome="completed",
                    evidence_refs=decision.evidence_refs,
                ))
                return self._result(state, "completed", answer=decision.answer,
                                    evidence_refs=decision.evidence_refs)

            # Validate the canonical name, policy and typed arguments before any
            # budget is consumed or service called. The registry repeats the gate.
            try:
                tool = self.registry.get(decision.tool_name)
            except AgentToolError:
                return self._reject_tool(state, decision, "invalid_decision", "tool", "unknown_tool")
            if tool.name not in context.policy.allowed_tools:
                return self._reject_tool(state, decision, "policy_denied", "policy", "tool_not_allowed")
            if tool.provider_execution and not context.policy.allow_provider_execution:
                return self._reject_tool(state, decision, "policy_denied", "policy", "tool_provider_required")
            try:
                validated = tool.input_model.model_validate(decision.arguments)
            except (ValidationError, ValueError, TypeError):
                return self._reject_tool(state, decision, "invalid_decision", "tool", "invalid_arguments")

            if state.tool_call_count >= self.limits.max_tool_calls:
                return self._reject_tool(state, decision, "budget_exhausted", "policy", "max_tool_calls")
            if state.per_tool_calls[tool.name] >= self._per_tool_limits[tool.name]:
                return self._reject_tool(state, decision, "budget_exhausted", "policy", "per_tool_limit")
            if len(state.observations) >= self.limits.max_observations:
                return self._reject_tool(state, decision, "budget_exhausted", "policy", "max_observations")

            signature = hashlib.sha256(json.dumps(
                [tool.name, validated.model_dump(mode="json")], sort_keys=True,
                separators=(",", ":"), ensure_ascii=False,
            ).encode("utf-8")).hexdigest()
            if self.policy.reject_duplicate_calls and signature in state.seen_calls:
                return self._reject_tool(state, decision, "invalid_decision", "policy", "duplicate_tool_call")
            if cancel_event is not None and cancel_event.is_set():
                return self._result(state, "cancelled", domain="system", code="cancelled")

            state.seen_calls.add(signature)
            state.tool_call_count += 1
            state.per_tool_calls[tool.name] += 1
            try:
                observation = await self.registry.invoke(tool.name, decision.arguments, context)
            except AgentToolError as error:
                status, domain, code = {
                    "unknown_tool": ("invalid_decision", "tool", "unknown_tool"),
                    "tool_not_allowed": ("policy_denied", "policy", "tool_not_allowed"),
                    "invalid_arguments": ("invalid_decision", "tool", "invalid_arguments"),
                    "unavailable": ("unavailable", "tool", "tool_unavailable"),
                    "execution_failed": ("failed", "tool", "tool_execution_failed"),
                    "provider_required": ("policy_denied", "policy", "tool_provider_required"),
                }[error.code]
                state.trace.append(AgentTraceEntry(
                    decision_index=state.decision_call_count, kind="tool", tool_name=tool.name,
                    argument_names=tuple(sorted(decision.arguments)), outcome="failed", failure_code=code,
                ))
                return self._result(state, status, domain=domain, code=code)
            try:
                projected = project_observation(
                    observation, self.limits,
                    self.limits.max_total_observation_bytes - state.observation_bytes,
                )
            except ObservationLimitError:
                state.trace.append(AgentTraceEntry(
                    decision_index=state.decision_call_count, kind="tool", tool_name=tool.name,
                    outcome="failed", failure_code="observation_bytes",
                ))
                return self._result(state, "budget_exhausted", domain="policy", code="observation_bytes")
            except ObservationIntegrityError:
                state.trace.append(AgentTraceEntry(
                    decision_index=state.decision_call_count, kind="tool", tool_name=tool.name,
                    outcome="failed", failure_code="invalid_observation",
                ))
                return self._result(state, "failed", domain="tool", code="invalid_observation")
            state.observations.append(projected)
            state.observation_bytes += len(projected.model_dump_json().encode("utf-8"))
            refs = _observation_refs(projected)[:20]
            state.trace.append(AgentTraceEntry(
                decision_index=state.decision_call_count, kind="tool", tool_name=tool.name,
                argument_names=tuple(sorted(decision.arguments)), outcome="observed",
                evidence_refs=refs,
            ))

        return self._result(state, "budget_exhausted", domain="policy", code="max_steps")
