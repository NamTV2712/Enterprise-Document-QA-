"""Deterministic read-only evaluation of already recorded Agent runs."""

from __future__ import annotations
from src.workspace.attribution import timed

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, fields, replace
from typing import Any, Mapping, Sequence, get_args

from pydantic import ValidationError

from src.agent.durable import AgentDurableService
from src.agent.durable_models import AgentRunEventResponse, AgentRunResponse
from src.agent.evaluation_models import (
    MAX_REPORT_BYTES, METRIC_DEFINITIONS, METRIC_VERSION, PROTOCOL_NAME,
    PROTOCOL_VERSION, AgentEvaluationCase, AgentEvaluationFacts, AgentEvaluationProvenance,
    AgentEvaluationReport, AgentMetricDefinition, AgentMetricResult,
    CorruptAgentEvaluationReport, CorruptAgentSnapshot,
)
from src.agent.observation import ObservationIntegrityError, _validate_source_pair
from src.agent.research import _ticker
from src.agent.research_models import ResearchSummary
from src.agent.state import AgentStatus, EvidenceRef, FailureCode, TOOL_NAMES
from src.retrieval.canonical_json import canonical_json_bytes
from src.workspace.jobs import TERMINAL_JOB_STATES


_FINGERPRINT = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
_RUN_ID = re.compile(r"^agent_[A-Za-z0-9_-]{1,122}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_POLICY_DENIAL_CODES = frozenset({
    "tool_not_allowed", "tool_provider_required", "max_steps", "max_tool_calls",
    "per_tool_limit", "max_observations", "observation_bytes",
    "research_objective_required", "research_scope_mismatch", "research_search_limit",
})
_INVALID_TOOL_CODES = frozenset({"unknown_tool", "invalid_arguments"})
_TOOL_FAILURE_CODES = frozenset({
    "tool_unavailable", "tool_execution_failed", "invalid_observation", "observation_bytes",
})
_GAP_CODES = ("below_threshold", "ledger_full", "no_evidence", "search_exhausted")
_MISSING_REASONS = frozenset({
    "no_tool_decisions", "no_admitted_tools", "no_terminal_result", "zero_tool_limit",
    "nonresearch", "no_evidence", "no_final", "no_final_refs",
    "source_pairs_not_persisted", "incomplete_observation_refs",
})
_MAX_EVENTS = 40


def _sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _count(suffix: str, value: int) -> AgentMetricResult:
    if type(value) is not int or value < 0:
        raise CorruptAgentSnapshot("invalid Agent count")
    return AgentMetricResult(f"native_agent.{suffix}", METRIC_VERSION, "computed", value, value, None, None)


def _boolean(suffix: str, value: bool) -> AgentMetricResult:
    if type(value) is not bool:
        raise CorruptAgentSnapshot("invalid Agent boolean")
    return AgentMetricResult(f"native_agent.{suffix}", METRIC_VERSION, "computed", value, int(value), 1, None)


def _ratio(suffix: str, numerator: int, denominator: int) -> AgentMetricResult:
    if (type(numerator) is not int or type(denominator) is not int or
            denominator <= 0 or not 0 <= numerator <= denominator):
        raise CorruptAgentSnapshot("invalid Agent ratio inputs")
    return AgentMetricResult(
        f"native_agent.{suffix}", METRIC_VERSION, "computed",
        round(numerator / denominator, 4), numerator, denominator, None,
    )


def _missing(suffix: str, status: str, reason: str) -> AgentMetricResult:
    if status not in ("unavailable", "not_applicable") or reason not in _MISSING_REASONS:
        raise CorruptAgentSnapshot("invalid Agent metric applicability")
    return AgentMetricResult(f"native_agent.{suffix}", METRIC_VERSION, status, None, None, None, reason)


def _validate_snapshot(
    run: AgentRunResponse, events: Sequence[AgentRunEventResponse],
) -> tuple[AgentRunResponse, tuple[AgentRunEventResponse, ...]]:
    """Revalidate even model_copy-built fixtures before deriving any metric."""
    try:
        run = AgentRunResponse.model_validate(run.model_dump(mode="python"))
        events = tuple(AgentRunEventResponse.model_validate(item.model_dump(mode="python")) for item in events)
        if not _RUN_ID.fullmatch(run.run_id) or run.state not in TERMINAL_JOB_STATES:
            raise ValueError("evaluation requires a terminal Agent run")
        if not 2 <= len(events) <= _MAX_EVENTS or run.revision != len(events):
            raise ValueError("incomplete or oversized Agent event sequence")
        if [item.sequence for item in events] != list(range(1, len(events) + 1)):
            raise ValueError("Agent events are not contiguous")
        if any(item.run_id != run.run_id for item in events):
            raise ValueError("Agent event run identity mismatch")
        if len({item.event_id for item in events}) != len(events):
            raise ValueError("duplicate Agent event identity")
        if run.failure is not None and not _SAFE_CODE.fullmatch(run.failure.code):
            raise ValueError("unsafe Agent job failure code")
        if any(
            not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", item.event_id)
            or not _SAFE_CODE.fullmatch(item.event_type)
            or item.reason_code is not None and not _SAFE_CODE.fullmatch(item.reason_code)
            for item in events
        ):
            raise ValueError("unsafe Agent event metadata")
        if events[0].event_type != "created" or events[0].state != "queued":
            raise ValueError("Agent create event is missing")
        if events[-1].state != run.state:
            raise ValueError("Agent terminal event disagrees with job state")
        if run.state in ("succeeded", "failed") and events[-1].event_type != "state_changed":
            raise ValueError("Agent terminal transition event is invalid")
        if run.state == "interrupted" and events[-1].event_type != "interrupted":
            raise ValueError("Agent interruption event is invalid")
        plan_json = run.frozen.model_dump(mode="json", exclude_none=True)
        if not re.fullmatch(r"[0-9a-f]{64}", run.configuration_fingerprint):
            raise ValueError("invalid frozen plan fingerprint")
        if hashlib.sha256(canonical_json_bytes(plan_json)).hexdigest() != run.configuration_fingerprint:
            raise ValueError("frozen Agent plan fingerprint mismatch")
        if run.state == "succeeded" and (run.result is None or run.result.agent_status != "completed"):
            raise ValueError("successful job lacks completed Agent result")
        if run.state != "succeeded" and run.result is not None and run.result.agent_status == "completed":
            raise ValueError("non-successful job carries completed Agent result")
        if run.state == "interrupted" and run.result is not None:
            raise ValueError("interrupted Agent job cannot carry a completed result")
        if run.result is not None:
            result = run.result
            limits = run.frozen.limits
            if (result.step_count > limits.max_steps or result.decision_call_count > limits.max_steps or
                    result.tool_call_count > limits.max_tool_calls or
                    result.observation_count > limits.max_observations or
                    result.step_count > result.decision_call_count):
                raise ValueError("Agent result exceeds frozen budget")
            if any(result.per_tool_calls[name] > limits.per_tool_calls[name] for name in TOOL_NAMES):
                raise ValueError("Agent per-tool counter exceeds frozen budget")
            if any(result.per_tool_calls[name] and name not in run.frozen.allowed_tools for name in TOOL_NAMES):
                raise ValueError("Agent result includes disallowed tool execution")
            if (run.frozen.research is None) != (result.research is None):
                raise ValueError("Agent research result disagrees with frozen plan")
            if result.agent_status == "completed" and result.failure is not None:
                raise ValueError("completed Agent result has a failure")
            if run.failure is not None and result.failure is not None and run.failure.code != result.failure.code:
                raise ValueError("job and Agent failure codes disagree")
        return run, events
    except (AttributeError, TypeError, ValidationError, ValueError, OverflowError) as error:
        raise CorruptAgentSnapshot("Agent evaluation snapshot is invalid") from error


def _decision_events(
    run: AgentRunResponse, events: tuple[AgentRunEventResponse, ...],
) -> tuple[AgentRunEventResponse, ...]:
    decisions: list[AgentRunEventResponse] = []
    last_step = last_tool_count = 0
    for item in events:
        summary = item.summary
        if item.event_type != "agent_decision":
            if summary is not None:
                raise CorruptAgentSnapshot("non-decision event has Agent summary")
            continue
        if summary is None or item.state != "running":
            raise CorruptAgentSnapshot("Agent decision event lacks a running summary")
        if summary.decision_index != len(decisions) + 1:
            raise CorruptAgentSnapshot("Agent decision indexes are not ordered")
        if (summary.step_count < last_step or summary.tool_call_count < last_tool_count or
                summary.step_count > run.frozen.limits.max_steps or
                summary.tool_call_count > run.frozen.limits.max_tool_calls):
            raise CorruptAgentSnapshot("Agent decision counters are inconsistent")
        expected_step = last_step if summary.decision_kind == "invalid" else last_step + 1
        expected_tools = last_tool_count + int(
            summary.decision_kind == "tool" and summary.outcome in ("observed", "failed")
        )
        if summary.step_count != expected_step or summary.tool_call_count != expected_tools:
            raise CorruptAgentSnapshot("Agent decision counters do not match action outcome")
        last_step, last_tool_count = summary.step_count, summary.tool_call_count
        if summary.evidence_count < len(summary.evidence_refs) or (
            len(summary.evidence_refs) != min(summary.evidence_count, 8)
        ):
            raise CorruptAgentSnapshot("Agent event evidence projection is inconsistent")
        if summary.outcome in ("observed", "completed") and summary.failure_code is not None:
            raise CorruptAgentSnapshot("successful decision has failure code")
        if summary.outcome in ("rejected", "failed") and summary.failure_code not in get_args(FailureCode):
            raise CorruptAgentSnapshot("failed decision lacks typed failure code")
        if summary.decision_kind == "tool":
            if not summary.tool_name or not _SAFE_CODE.fullmatch(summary.tool_name):
                raise CorruptAgentSnapshot("tool decision name is unsafe")
            if summary.outcome not in ("observed", "failed", "rejected"):
                raise CorruptAgentSnapshot("tool decision outcome is invalid")
            if summary.outcome == "failed" and summary.failure_code not in _TOOL_FAILURE_CODES:
                raise CorruptAgentSnapshot("tool failure category is invalid")
            if summary.outcome == "rejected" and summary.failure_code not in (
                _POLICY_DENIAL_CODES | _INVALID_TOOL_CODES | {"duplicate_tool_call"}
            ):
                raise CorruptAgentSnapshot("rejected tool category is invalid")
            if summary.outcome in ("observed", "failed") and (
                summary.tool_name not in TOOL_NAMES or summary.tool_name not in run.frozen.allowed_tools
            ):
                raise CorruptAgentSnapshot("unregistered or denied tool was recorded as admitted")
        elif summary.decision_kind == "final":
            if summary.tool_name is not None or summary.outcome not in ("completed", "rejected"):
                raise CorruptAgentSnapshot("final decision event is invalid")
        elif summary.tool_name is not None or summary.outcome != "rejected":
            raise CorruptAgentSnapshot("invalid decision event is malformed")
        decisions.append(item)
    if run.result is not None:
        result = run.result
        if (len(decisions) > result.decision_call_count or last_step > result.step_count or
                last_tool_count > result.tool_call_count):
            raise CorruptAgentSnapshot("Agent events exceed terminal counters")
        admitted = [item.summary for item in decisions if item.summary and item.summary.decision_kind == "tool"
                    and item.summary.outcome in ("observed", "failed")]
        observed = [item for item in admitted if item.outcome == "observed"]
        if len(admitted) != result.tool_call_count or len(observed) != result.observation_count:
            raise CorruptAgentSnapshot("Agent tool counters disagree with events")
        actual_by_tool = Counter(item.tool_name for item in admitted)
        if any(actual_by_tool[name] != result.per_tool_calls[name] for name in TOOL_NAMES):
            raise CorruptAgentSnapshot("Agent per-tool counters disagree with events")
        finals = [item.summary for item in decisions if item.summary and item.summary.decision_kind == "final"
                  and item.summary.outcome == "completed"]
        if result.agent_status == "completed":
            if len(finals) != 1 or finals[0].evidence_count != len(result.evidence_refs) or (
                finals[0].evidence_refs != list(result.evidence_refs[:8])
            ):
                raise CorruptAgentSnapshot("completed final references disagree with event")
        elif finals:
            raise CorruptAgentSnapshot("non-completed Agent result has completed final event")
    return tuple(decisions)


def _validate_research(run: AgentRunResponse, events: tuple[AgentRunEventResponse, ...]) -> ResearchSummary | None:
    if run.result is None or run.result.research is None:
        return None
    config = run.frozen.research
    summary = run.result.research
    if config is None or tuple(item.objective_id for item in summary.objectives) != tuple(
        item.objective_id for item in config.objectives
    ):
        raise CorruptAgentSnapshot("research objectives disagree with frozen plan")
    gap_by_id = {gap.objective_id: gap.code for gap in summary.gaps}
    if summary.evidence_capped and len(summary.evidence) != config.max_evidence_entries:
        raise CorruptAgentSnapshot("capped research ledger has impossible size")
    for status in summary.objectives:
        expected_coverage = (
            "none" if status.evidence_count == 0 else
            "some" if status.evidence_count < config.min_evidence_per_objective else "sufficient"
        )
        if status.coverage != expected_coverage or status.search_attempts > config.max_search_attempts_per_objective:
            raise CorruptAgentSnapshot("research objective status is inconsistent")
        expected_gap = None if expected_coverage == "sufficient" else (
            "ledger_full" if summary.evidence_capped else
            "search_exhausted" if status.search_attempts >= config.max_search_attempts_per_objective else
            "no_evidence" if status.evidence_count == 0 else "below_threshold"
        )
        if gap_by_id.get(status.objective_id) != expected_gap:
            raise CorruptAgentSnapshot("research gap category is inconsistent")
        observed_searches = sum(
            event.summary is not None and event.summary.decision_kind == "tool"
            and event.summary.tool_name == "search_documents"
            and event.summary.objective_id == status.objective_id
            and event.summary.outcome in ("observed", "failed")
            for event in events
        )
        if status.search_attempts != observed_searches:
            raise CorruptAgentSnapshot("research search attempts disagree with events")
    for item in summary.evidence:
        try:
            EvidenceRef(kind="chunk_id", value=item.chunk_id)
            if item.document_id is not None:
                EvidenceRef(kind="document_id", value=item.document_id)
            _validate_source_pair(item.document_id, item.chunk_id)
        except (ObservationIntegrityError, ValidationError) as error:
            raise CorruptAgentSnapshot("research evidence identity is inconsistent") from error
        if item.ticker != _ticker(item.document_id):
            raise CorruptAgentSnapshot("research evidence ticker is inconsistent")
        if any(
            objective.ticker_scope and objective.ticker_scope != item.ticker
            for objective in config.objectives if objective.objective_id in item.objective_ids
        ):
            raise CorruptAgentSnapshot("research evidence violates objective scope")
        if not any(
            event.summary and event.summary.decision_kind == "tool"
            and event.summary.outcome == "observed"
            and event.summary.step_count == item.first_step
            and event.summary.tool_name == item.first_tool
            and event.summary.objective_id in item.objective_ids
            for event in events
        ):
            raise CorruptAgentSnapshot("research evidence lacks its first recorded tool step")
    return summary


def _final_reference_metric(
    run: AgentRunResponse, decisions: tuple[AgentRunEventResponse, ...],
    research: ResearchSummary | None,
) -> AgentMetricResult:
    result = run.result
    if result is None or result.agent_status != "completed":
        return _missing("final_reference_validity", "not_applicable", "no_final")
    if not result.evidence_refs:
        return _missing("final_reference_validity", "not_applicable", "no_final_refs")
    if research is not None:
        observed = {
            (kind, value)
            for entry in research.evidence
            for kind, value in (("document_id", entry.document_id), ("chunk_id", entry.chunk_id))
            if value is not None
        }
    else:
        observed = {
            (ref.kind, ref.value)
            for item in decisions if item.summary and item.summary.decision_kind == "tool"
            and item.summary.outcome == "observed"
            for ref in item.summary.evidence_refs
        }
    missing = [ref for ref in result.evidence_refs if (ref.kind, ref.value) not in observed]
    if missing:
        incomplete = research is None and any(
            item.summary and item.summary.decision_kind == "tool"
            and item.summary.outcome == "observed" and item.summary.evidence_count > 8
            for item in decisions
        )
        if incomplete:
            return _missing("final_reference_validity", "unavailable", "incomplete_observation_refs")
        raise CorruptAgentSnapshot("final reference is absent from current-run evidence")
    return _ratio("final_reference_validity", len(result.evidence_refs), len(result.evidence_refs))


@timed("evaluation.compute")
def evaluate_agent_run(
    run: AgentRunResponse, events: Sequence[AgentRunEventResponse],
) -> AgentEvaluationReport:
    """Evaluate a terminal durable snapshot without tool, provider or storage writes."""
    run, events = _validate_snapshot(run, events)
    decisions = _decision_events(run, events)
    research = _validate_research(run, decisions)
    tool_decisions = [item.summary for item in decisions if item.summary and item.summary.decision_kind == "tool"]
    admitted = [item for item in tool_decisions if item.outcome in ("observed", "failed")]
    rejected = [item for item in tool_decisions if item.outcome == "rejected"]
    failures = [item for item in admitted if item.outcome == "failed"]
    rejected_codes = Counter(item.failure_code for item in rejected)
    per_tool = Counter(item.tool_name for item in admitted)
    final_rejections = sum(
        item.summary is not None and item.summary.decision_kind == "final"
        and item.summary.outcome == "rejected" for item in decisions
    )
    metrics: dict[str, AgentMetricResult] = {}

    def add(result: AgentMetricResult) -> None:
        metrics[result.metric_id] = result

    add(_boolean("execution_completed", run.state == "succeeded"))
    add(_count("recorded_tool_decision_count", len(tool_decisions)))
    add(_count("admitted_tool_call_count", len(admitted)))
    add(_ratio("tool_admission_fraction", len(admitted), len(tool_decisions)) if tool_decisions else
        _missing("tool_admission_fraction", "not_applicable", "no_tool_decisions"))
    add(_count("invalid_tool_attempt_count", sum(item.failure_code in _INVALID_TOOL_CODES for item in rejected)))
    add(_count("policy_denial_attempt_count", sum(item.failure_code in _POLICY_DENIAL_CODES for item in rejected)
               + int(bool(run.result and run.result.failure and
                          run.result.failure.code == "decision_provider_required"))))
    add(_count("duplicate_rejection_count", rejected_codes["duplicate_tool_call"]))
    add(_ratio("tool_failure_fraction", len(failures), len(admitted)) if admitted else
        _missing("tool_failure_fraction", "not_applicable", "no_admitted_tools"))
    add(_count("tool_unavailable_count", sum(item.failure_code == "tool_unavailable" for item in failures)))
    add(_count("invalid_final_attempt_count", final_rejections))
    if run.result is None:
        for suffix in ("step_budget_utilization", "tool_budget_utilization",
                       "budget_exhausted", "decision_provider_unavailable"):
            add(_missing(suffix, "unavailable", "no_terminal_result"))
    else:
        result = run.result
        add(_ratio("step_budget_utilization", result.step_count, run.frozen.limits.max_steps))
        add(_ratio("tool_budget_utilization", result.tool_call_count, run.frozen.limits.max_tool_calls)
            if run.frozen.limits.max_tool_calls else
            _missing("tool_budget_utilization", "not_applicable", "zero_tool_limit"))
        add(_boolean("budget_exhausted", result.agent_status == "budget_exhausted"))
        add(_boolean("decision_provider_unavailable", bool(
            result.failure and result.failure.code == "decision_provider_unavailable"
        )))
    if run.frozen.research is None:
        if (run.result is not None and run.result.observation_count) or any(
            item.summary and item.summary.decision_kind == "tool"
            and item.summary.outcome == "observed" for item in decisions
        ):
            add(_missing("evidence_identity_validity", "unavailable", "source_pairs_not_persisted"))
        else:
            add(_missing("evidence_identity_validity", "not_applicable", "no_evidence"))
        for suffix in ("objective_coverage", "unresolved_gap_fraction", "research_evidence_count",
                       "distinct_document_count", "distinct_chunk_count"):
            add(_missing(suffix, "not_applicable", "nonresearch"))
    elif research is None:
        for suffix in ("evidence_identity_validity", "objective_coverage", "unresolved_gap_fraction",
                       "research_evidence_count", "distinct_document_count", "distinct_chunk_count"):
            add(_missing(suffix, "unavailable", "no_terminal_result"))
    else:
        add(_ratio("evidence_identity_validity", len(research.evidence), len(research.evidence))
            if research.evidence else _missing("evidence_identity_validity", "not_applicable", "no_evidence"))
        objective_count = len(run.frozen.research.objectives)
        add(_ratio("objective_coverage", sum(item.coverage == "sufficient" for item in research.objectives),
                   objective_count))
        add(_ratio("unresolved_gap_fraction", len(research.gaps), objective_count))
        add(_count("research_evidence_count", len(research.evidence)))
        add(_count("distinct_document_count", len({item.document_id for item in research.evidence
                                                    if item.document_id is not None})))
        add(_count("distinct_chunk_count", len({item.chunk_id for item in research.evidence})))
    add(_final_reference_metric(run, decisions, research))
    ordered = tuple(metrics[item.metric_id] for item in METRIC_DEFINITIONS)
    event_payload = [{
        "event_id": item.event_id, "sequence": item.sequence,
        "event_type": item.event_type, "state": item.state,
        "reason_code": item.reason_code,
        "summary": item.summary.model_dump(mode="json") if item.summary else None,
    } for item in events]
    facts = AgentEvaluationFacts(
        run.state, run.result.agent_status if run.result else None,
        run.result.failure.code if run.result and run.result.failure else
        (run.failure.code if run.failure else None),
        tuple((name, per_tool[name]) for name in sorted(TOOL_NAMES)),
        tuple(sorted(rejected_codes.items())),
        tuple((code, sum(gap.code == code for gap in research.gaps)) for code in _GAP_CODES)
        if research else (),
    )
    provenance = AgentEvaluationProvenance(
        run.configuration_fingerprint,
        _sha(run.frozen.model_dump(mode="json", exclude_none=True)),
        _sha(event_payload),
        _sha(run.result.model_dump(mode="json", exclude_none=True)) if run.result else None,
        run.revision, run.frozen.protocol,
        run.frozen.research.version if run.frozen.research else None,
    )
    report = AgentEvaluationReport(
        PROTOCOL_NAME, PROTOCOL_VERSION, run.run_id, METRIC_DEFINITIONS,
        ordered, facts, provenance, "",
    )
    report = replace(report, digest=_report_digest(report))
    if len(canonical_agent_report_bytes(report)) > MAX_REPORT_BYTES:
        raise CorruptAgentSnapshot("Agent evaluation report exceeds byte bound")
    return report


def evaluate_durable_agent_run(service: AgentDurableService, run_id: str) -> AgentEvaluationReport:
    """Read one persisted run and its bounded events; never resume it."""
    return evaluate_agent_run(service.get(run_id), service.events(run_id, after_sequence=0))


def evaluate_agent_case(case: AgentEvaluationCase) -> AgentEvaluationReport:
    """Evaluate an explicitly bound case without consulting external state."""
    if not isinstance(case, AgentEvaluationCase):
        raise CorruptAgentSnapshot("Agent evaluation case is not typed")
    return evaluate_agent_run(case.run, case.events)


def _report_payload(report: AgentEvaluationReport, *, include_digest: bool) -> dict[str, Any]:
    payload = asdict(report)
    if not include_digest:
        payload.pop("digest")
    return payload


def _report_digest(report: AgentEvaluationReport) -> str:
    return _sha(_report_payload(report, include_digest=False))


def canonical_agent_report_bytes(report: AgentEvaluationReport) -> bytes:
    """Use the same sorted-key, finite UTF-8 JSON convention as native EVAL."""
    return canonical_json_bytes(_report_payload(report, include_digest=True))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise CorruptAgentEvaluationReport("duplicate evaluation JSON key")
        output[key] = value
    return output


def _reject_nonfinite(_value: str) -> None:
    raise CorruptAgentEvaluationReport("non-finite evaluation number")


def _exact(value: Any, cls: type, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {field.name for field in fields(cls)}:
        raise CorruptAgentEvaluationReport(f"{label} has invalid fields")
    return value


def _parse_metric(raw: Any, definition: AgentMetricDefinition) -> AgentMetricResult:
    data = _exact(raw, AgentMetricResult, "Agent metric")
    if data["metric_id"] != definition.metric_id or type(data["metric_version"]) is not int or (
        data["metric_version"] != definition.metric_version
    ):
        raise CorruptAgentEvaluationReport("Agent metric ID/version mismatch")
    status, value = data["status"], data["value"]
    numerator, denominator, reason = data["numerator"], data["denominator"], data["reason_code"]
    if status == "computed":
        if reason is not None or type(numerator) is not int or numerator < 0:
            raise CorruptAgentEvaluationReport("computed Agent metric is malformed")
        if definition.value_kind == "boolean":
            if type(value) is not bool or denominator != 1 or numerator != int(value):
                raise CorruptAgentEvaluationReport("Agent boolean is malformed")
        elif definition.value_kind == "count":
            if type(value) is not int or value != numerator or value > 20 or denominator is not None:
                raise CorruptAgentEvaluationReport("Agent count is malformed")
        elif (type(value) is not float or not math.isfinite(value) or
              type(denominator) is not int or not 0 < denominator <= 20 or numerator > denominator or
              value != round(numerator / denominator, 4)):
            raise CorruptAgentEvaluationReport("Agent ratio is malformed")
    elif status in ("unavailable", "not_applicable"):
        if (value is not None or numerator is not None or denominator is not None or
                reason not in _MISSING_REASONS):
            raise CorruptAgentEvaluationReport("missing Agent metric is malformed")
    else:
        raise CorruptAgentEvaluationReport("unknown Agent metric status")
    return AgentMetricResult(**data)


def parse_agent_evaluation_report(raw: bytes | str | Mapping[str, Any]) -> AgentEvaluationReport:
    """Fail closed on unsupported versions, altered definitions and corrupt digests."""
    try:
        if isinstance(raw, Mapping):
            encoded = canonical_json_bytes(dict(raw))
        elif isinstance(raw, str):
            encoded = raw.encode("utf-8")
        elif isinstance(raw, bytes):
            encoded = raw
        else:
            raise CorruptAgentEvaluationReport("Agent report must be JSON or an object")
        if len(encoded) > MAX_REPORT_BYTES:
            raise CorruptAgentEvaluationReport("Agent report exceeds byte bound")
        data = json.loads(encoded, object_pairs_hook=_unique_object, parse_constant=_reject_nonfinite)
        data = _exact(data, AgentEvaluationReport, "Agent report")
        if data["protocol"] != PROTOCOL_NAME or type(data["protocol_version"]) is not int or (
            data["protocol_version"] != PROTOCOL_VERSION
        ):
            raise CorruptAgentEvaluationReport("unsupported Agent evaluation protocol")
        if not isinstance(data["run_id"], str) or not _RUN_ID.fullmatch(data["run_id"]):
            raise CorruptAgentEvaluationReport("invalid Agent report run ID")
        definitions = json.loads(canonical_json_bytes([asdict(item) for item in METRIC_DEFINITIONS]))
        if data["metric_definitions"] != definitions:
            raise CorruptAgentEvaluationReport("Agent metric definitions or versions changed")
        if not isinstance(data["metrics"], list) or len(data["metrics"]) != len(METRIC_DEFINITIONS):
            raise CorruptAgentEvaluationReport("Agent metric vector is incomplete")
        metrics = tuple(_parse_metric(item, definition) for item, definition in zip(
            data["metrics"], METRIC_DEFINITIONS,
        ))
        raw_facts = _exact(data["facts"], AgentEvaluationFacts, "Agent facts")
        raw_provenance = _exact(data["provenance"], AgentEvaluationProvenance, "Agent provenance")
        for field_name in ("configuration_fingerprint", "frozen_plan_sha256", "event_sha256"):
            if not isinstance(raw_provenance[field_name], str) or not _FINGERPRINT.fullmatch(
                raw_provenance[field_name]
            ):
                raise CorruptAgentEvaluationReport("Agent provenance fingerprint is invalid")
        if raw_provenance["result_sha256"] is not None and (
            not isinstance(raw_provenance["result_sha256"], str) or
            not _FINGERPRINT.fullmatch(raw_provenance["result_sha256"])
        ):
            raise CorruptAgentEvaluationReport("Agent result fingerprint is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", raw_provenance["configuration_fingerprint"]):
            raise CorruptAgentEvaluationReport("Agent plan fingerprint format is invalid")
        for field_name in ("frozen_plan_sha256", "event_sha256", "result_sha256"):
            value = raw_provenance[field_name]
            if value is not None and not value.startswith("sha256:"):
                raise CorruptAgentEvaluationReport("Agent provenance hash format is invalid")
        if (type(raw_provenance["run_revision"]) is not int or
                not 2 <= raw_provenance["run_revision"] <= _MAX_EVENTS or
                raw_provenance["agent_protocol"] != "bounded_single_agent" or
                raw_provenance["research_version"] not in (None, "agent_research_v1")):
            raise CorruptAgentEvaluationReport("Agent provenance binding is invalid")
        if (raw_facts["terminal_state"] not in TERMINAL_JOB_STATES or
                raw_facts["agent_status"] is not None and raw_facts["agent_status"] not in get_args(AgentStatus) or
                raw_facts["failure_code"] is not None and (
                    not isinstance(raw_facts["failure_code"], str)
                    or not _SAFE_CODE.fullmatch(raw_facts["failure_code"])
                )):
            raise CorruptAgentEvaluationReport("Agent terminal facts are invalid")
        if (raw_facts["agent_status"] is None) != (raw_provenance["result_sha256"] is None):
            raise CorruptAgentEvaluationReport("Agent result provenance and terminal facts disagree")
        if (raw_facts["terminal_state"] == "succeeded") != (
            raw_facts["agent_status"] == "completed"
        ):
            raise CorruptAgentEvaluationReport("Agent execution completion is inconsistent")
        for field_name in ("recorded_per_tool_calls", "rejected_tool_codes", "gap_counts"):
            rows = raw_facts[field_name]
            if (not isinstance(rows, list) or any(not isinstance(row, list) or len(row) != 2 or
                not isinstance(row[0], str) or type(row[1]) is not int or row[1] < 0 for row in rows)):
                raise CorruptAgentEvaluationReport("Agent fact counters are malformed")
            if rows != sorted(rows, key=lambda row: row[0]) or len({row[0] for row in rows}) != len(rows):
                raise CorruptAgentEvaluationReport("Agent fact counters are unordered or duplicate")
        if [row[0] for row in raw_facts["recorded_per_tool_calls"]] != sorted(TOOL_NAMES):
            raise CorruptAgentEvaluationReport("Agent per-tool facts are incomplete")
        if any(row[1] > 10 for row in raw_facts["recorded_per_tool_calls"]):
            raise CorruptAgentEvaluationReport("Agent per-tool facts exceed a hard bound")
        if any(row[0] not in get_args(FailureCode) or row[1] > 20
               for row in raw_facts["rejected_tool_codes"]):
            raise CorruptAgentEvaluationReport("Agent rejection facts are invalid")
        if raw_facts["gap_counts"] and [row[0] for row in raw_facts["gap_counts"]] != sorted(_GAP_CODES):
            raise CorruptAgentEvaluationReport("Agent gap facts are incomplete")
        if any(row[1] > 6 for row in raw_facts["gap_counts"]):
            raise CorruptAgentEvaluationReport("Agent gap facts exceed a hard bound")
        by_id = {item.metric_id.rsplit(".", 1)[1]: item for item in metrics}
        recorded_tools = by_id["recorded_tool_decision_count"]
        admitted_tools = by_id["admitted_tool_call_count"]
        if (recorded_tools.status != "computed" or admitted_tools.status != "computed" or
                admitted_tools.value != sum(row[1] for row in raw_facts["recorded_per_tool_calls"]) or
                recorded_tools.value != admitted_tools.value + sum(
                    row[1] for row in raw_facts["rejected_tool_codes"]
                ) or recorded_tools.value > 20):
            raise CorruptAgentEvaluationReport("Agent tool facts disagree with metric counts")
        expected_rejections = {
            "invalid_tool_attempt_count": sum(row[1] for row in raw_facts["rejected_tool_codes"]
                                              if row[0] in _INVALID_TOOL_CODES),
            "policy_denial_attempt_count": sum(row[1] for row in raw_facts["rejected_tool_codes"]
                                               if row[0] in _POLICY_DENIAL_CODES)
            + int(raw_facts["failure_code"] == "decision_provider_required"),
            "duplicate_rejection_count": dict(raw_facts["rejected_tool_codes"]).get("duplicate_tool_call", 0),
        }
        if any(by_id[name].status != "computed" or by_id[name].value != expected
               for name, expected in expected_rejections.items()):
            raise CorruptAgentEvaluationReport("Agent rejection metrics disagree with facts")
        admission = by_id["tool_admission_fraction"]
        if recorded_tools.value == 0:
            if admission.status != "not_applicable" or admission.reason_code != "no_tool_decisions":
                raise CorruptAgentEvaluationReport("zero-decision admission metric is invalid")
        elif (admission.status != "computed" or admission.numerator != admitted_tools.value or
              admission.denominator != recorded_tools.value):
            raise CorruptAgentEvaluationReport("Agent admission denominator is invalid")
        tool_failure = by_id["tool_failure_fraction"]
        if admitted_tools.value == 0:
            if tool_failure.status != "not_applicable" or tool_failure.reason_code != "no_admitted_tools":
                raise CorruptAgentEvaluationReport("zero-admission failure metric is invalid")
        elif tool_failure.status != "computed" or tool_failure.denominator != admitted_tools.value:
            raise CorruptAgentEvaluationReport("Agent tool failure denominator is invalid")
        completion = by_id["execution_completed"]
        if completion.status != "computed" or completion.value != (raw_facts["terminal_state"] == "succeeded"):
            raise CorruptAgentEvaluationReport("Agent completion metric disagrees with terminal state")
        if raw_provenance["result_sha256"] is None:
            if any(by_id[name].status != "unavailable" for name in (
                "step_budget_utilization", "tool_budget_utilization", "budget_exhausted",
                "decision_provider_unavailable",
            )):
                raise CorruptAgentEvaluationReport("result-dependent metrics lack a terminal result")
        if raw_provenance["research_version"] is None:
            if raw_facts["gap_counts"] or any(by_id[name].status != "not_applicable" for name in (
                "objective_coverage", "unresolved_gap_fraction", "research_evidence_count",
                "distinct_document_count", "distinct_chunk_count",
            )):
                raise CorruptAgentEvaluationReport("generic Agent report contains research metrics")
        elif raw_provenance["result_sha256"] is not None:
            if len(raw_facts["gap_counts"]) != len(_GAP_CODES):
                raise CorruptAgentEvaluationReport("research gap counts are incomplete")
            coverage = by_id["objective_coverage"]
            gaps = by_id["unresolved_gap_fraction"]
            if (coverage.status != "computed" or gaps.status != "computed" or
                    coverage.denominator != gaps.denominator or
                    coverage.numerator + gaps.numerator != coverage.denominator or
                    gaps.numerator != sum(row[1] for row in raw_facts["gap_counts"])):
                raise CorruptAgentEvaluationReport("research objective denominators disagree")
        facts = AgentEvaluationFacts(
            raw_facts["terminal_state"], raw_facts["agent_status"], raw_facts["failure_code"],
            tuple(tuple(row) for row in raw_facts["recorded_per_tool_calls"]),
            tuple(tuple(row) for row in raw_facts["rejected_tool_codes"]),
            tuple(tuple(row) for row in raw_facts["gap_counts"]),
        )
        provenance = AgentEvaluationProvenance(**raw_provenance)
        report = AgentEvaluationReport(
            PROTOCOL_NAME, PROTOCOL_VERSION, data["run_id"], METRIC_DEFINITIONS,
            metrics, facts, provenance, data["digest"],
        )
        if not isinstance(report.digest, str) or not _FINGERPRINT.fullmatch(report.digest) or (
            report.digest != _report_digest(report)
        ):
            raise CorruptAgentEvaluationReport("Agent report digest mismatch")
        return report
    except CorruptAgentEvaluationReport:
        raise
    except (UnicodeError, TypeError, ValueError, OverflowError, json.JSONDecodeError) as error:
        raise CorruptAgentEvaluationReport("Agent evaluation report is malformed") from error
