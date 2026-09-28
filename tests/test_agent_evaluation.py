"""AGENT-006 deterministic evaluation of recorded Agent facts only."""

from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import replace

import pytest
from fastapi import HTTPException

from src.agent.durable import AgentDurableService
from src.agent.durable_models import AgentRunCreateRequest, AgentRunFailure
from src.agent.evaluation import (
    canonical_agent_report_bytes, evaluate_agent_case, evaluate_agent_run, evaluate_durable_agent_run,
    parse_agent_evaluation_report,
)
from src.agent.evaluation_models import (
    MAX_REPORT_BYTES, METRIC_DEFINITIONS, AgentEvaluationCase, AgentEvaluationError, CorruptAgentEvaluationReport,
    CorruptAgentSnapshot, validate_metric_definitions,
)
from src.agent.registry import AgentToolRegistry, build_tool_registry
from src.agent.research_models import ResearchObjective
from src.retrieval.canonical_json import canonical_json_bytes
from src.workspace.database import WorkspaceDatabase
from src.workspace.jobs import SQLiteJobRepository
from tests.test_agent_durable import _create, _run, _service
from tests.test_agent_orchestration import (
    CHUNK, DOC, ScriptedDecisionModel, _final, _services, _tool,
)
from tests.test_agent_research import (
    MSFT_CHUNK, MSFT_DOC, _config, _final as _research_final,
    _tool as _research_tool, _two_company_services,
)


def _metric(report, suffix):
    return next(item for item in report.metrics if item.metric_id == f"native_agent.{suffix}")


def _snapshot(tmp_path, decisions=(), *, body=None, text="Safe evidence 🚀", key="evaluation-case"):
    service, _, calls, _, default_body = _service(tmp_path, decisions, text=text)
    created = _create(service, body or default_body, key=key)
    final = _run(service, created.run_id)
    return service, final, service.events(created.run_id, after_sequence=0), calls


def test_metric_registry_is_versioned_unique_ordered_and_semantically_explicit():
    assert len(METRIC_DEFINITIONS) == 21
    assert len({item.metric_id for item in METRIC_DEFINITIONS}) == len(METRIC_DEFINITIONS)
    assert all(item.metric_version == 1 and item.meaning and item.non_meaning
               and item.applicability and item.source_fields for item in METRIC_DEFINITIONS)
    assert [item.metric_id for item in METRIC_DEFINITIONS] == [
        f"native_agent.{suffix}" for suffix in (
            "execution_completed", "recorded_tool_decision_count", "admitted_tool_call_count",
            "tool_admission_fraction", "invalid_tool_attempt_count", "policy_denial_attempt_count",
            "duplicate_rejection_count", "tool_failure_fraction", "tool_unavailable_count",
            "invalid_final_attempt_count", "step_budget_utilization", "tool_budget_utilization",
            "budget_exhausted", "decision_provider_unavailable", "evidence_identity_validity",
            "final_reference_validity", "objective_coverage", "unresolved_gap_fraction",
            "research_evidence_count", "distinct_document_count", "distinct_chunk_count",
        )
    ]
    assert next(item for item in METRIC_DEFINITIONS if item.metric_id.endswith("tool_budget_utilization")).direction == "neutral"
    assert not any("overall" in item.metric_id or "score" in item.metric_id for item in METRIC_DEFINITIONS)
    with pytest.raises(AgentEvaluationError):
        validate_metric_definitions((*METRIC_DEFINITIONS, METRIC_DEFINITIONS[0]))
    with pytest.raises(AgentEvaluationError):
        validate_metric_definitions((replace(METRIC_DEFINITIONS[0], metric_version=0),))


def test_completed_durable_run_has_exact_counts_zero_false_and_digest(tmp_path):
    service, run, events, calls = _snapshot(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Grounded evidence.", ("chunk_id", CHUNK)),
    ))
    before = len(calls)
    before_revision = service.get(run.run_id).revision
    before_events = service.events(run.run_id, after_sequence=0)
    report = evaluate_durable_agent_run(service, run.run_id)
    assert len(calls) == before == 1
    assert service.get(run.run_id).revision == before_revision
    assert service.events(run.run_id, after_sequence=0) == before_events
    assert report.protocol == "native-agent-evaluation" and report.protocol_version == 1
    assert _metric(report, "execution_completed").value is True
    assert _metric(report, "recorded_tool_decision_count").value == 1
    assert _metric(report, "admitted_tool_call_count").value == 1
    assert _metric(report, "tool_admission_fraction").value == 1.0
    assert _metric(report, "tool_failure_fraction").value == 0.0
    assert _metric(report, "invalid_tool_attempt_count").value == 0
    assert _metric(report, "budget_exhausted").value is False
    assert _metric(report, "decision_provider_unavailable").value is False
    assert _metric(report, "step_budget_utilization").value == 0.25
    assert _metric(report, "tool_budget_utilization").value == 0.2
    assert _metric(report, "final_reference_validity").value == 1.0
    assert _metric(report, "evidence_identity_validity").status == "unavailable"
    assert _metric(report, "objective_coverage").status == "not_applicable"
    assert report.facts.recorded_per_tool_calls == (
        ("ask_rag", 0), ("inspect_retrieval", 0), ("read_document", 1), ("search_documents", 0),
    )
    encoded = canonical_agent_report_bytes(report)
    assert parse_agent_evaluation_report(encoded) == report
    assert evaluate_agent_run(run, events) == report
    assert evaluate_agent_case(AgentEvaluationCase(run, events)) == report
    assert b"Grounded evidence" not in encoded and b"Safe evidence" not in encoded


def test_zero_tool_final_is_computed_zero_not_missing(tmp_path):
    body = AgentRunCreateRequest(
        goal="Give a bounded generic answer.", allowed_tools=[],
        require_observation_for_final=False,
    )
    _, run, events, calls = _snapshot(tmp_path, (_final("A generic answer."),), body=body)
    report = evaluate_agent_run(run, events)
    assert run.state == "succeeded" and calls == []
    assert _metric(report, "admitted_tool_call_count").status == "computed"
    assert _metric(report, "admitted_tool_call_count").value == 0
    assert _metric(report, "tool_budget_utilization").value == 0.0
    assert _metric(report, "tool_admission_fraction").status == "not_applicable"
    assert _metric(report, "final_reference_validity").status == "not_applicable"
    assert parse_agent_evaluation_report(canonical_agent_report_bytes(report)) == report


def test_zero_tool_limit_has_not_applicable_utilization(tmp_path):
    body = AgentRunCreateRequest(
        goal="Give a bounded generic answer.", allowed_tools=[],
        require_observation_for_final=False, limits={"max_tool_calls": 0},
    )
    _, run, events, _ = _snapshot(tmp_path, (_final("A generic answer."),), body=body)
    report = evaluate_agent_run(run, events)
    assert _metric(report, "admitted_tool_call_count").value == 0
    assert _metric(report, "tool_budget_utilization").status == "not_applicable"
    assert _metric(report, "tool_budget_utilization").reason_code == "zero_tool_limit"


@pytest.mark.parametrize("decision,expected_invalid,expected_policy", [
    (_tool("delete_database", query="risk"), 1, 0),
    (_tool("read_document", document_id="../../.env"), 1, 0),
    (_tool("ask_rag", question="What is the risk?"), 0, 1),
])
def test_invalid_and_denied_tool_attempts_are_separate(tmp_path, decision, expected_invalid, expected_policy):
    _, run, events, calls = _snapshot(tmp_path, (decision,))
    report = evaluate_agent_run(run, events)
    assert calls == []
    assert _metric(report, "execution_completed").value is False
    assert _metric(report, "recorded_tool_decision_count").value == 1
    assert _metric(report, "admitted_tool_call_count").value == 0
    assert _metric(report, "invalid_tool_attempt_count").value == expected_invalid
    assert _metric(report, "policy_denial_attempt_count").value == expected_policy
    assert _metric(report, "tool_failure_fraction").status == "not_applicable"
    assert _metric(report, "tool_admission_fraction").value == 0.0


def test_exact_duplicate_rejection_is_not_claimed_as_optimality(tmp_path):
    _, run, events, calls = _snapshot(tmp_path, (
        _tool("read_document", document_id=DOC),
        _tool("read_document", document_id=DOC),
    ))
    report = evaluate_agent_run(run, events)
    assert calls == ["read_document"]
    assert _metric(report, "duplicate_rejection_count").value == 1
    assert _metric(report, "tool_admission_fraction").value == 0.5
    assert _metric(report, "admitted_tool_call_count").value == 1


def test_budget_exhaustion_is_terminal_fact_not_utilization_inference(tmp_path):
    body = AgentRunCreateRequest(goal="Read bounded filing evidence.", limits={"max_tool_calls": 1})
    _, run, events, calls = _snapshot(tmp_path, (
        _tool("read_document", document_id=DOC, page=1),
        _tool("read_document", document_id=DOC, page=2),
    ), body=body)
    report = evaluate_agent_run(run, events)
    assert run.result.agent_status == "budget_exhausted" and calls == ["read_document"]
    assert _metric(report, "tool_budget_utilization").value == 1.0
    assert _metric(report, "budget_exhausted").value is True
    assert _metric(report, "policy_denial_attempt_count").value == 1


def test_admitted_tool_failure_is_distinct_from_invalid_selection(tmp_path):
    service, _, calls, _, body = _service(tmp_path, (_tool("read_document", document_id=DOC),))
    original = service.registry_factory
    broken = _services(calls, failure=RuntimeError("synthetic tool failure"))
    service.registry_factory = lambda: build_tool_registry(broken)
    created = _create(service, body)
    run = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, run.run_id)
    assert calls == ["read_document"]
    assert _metric(report, "admitted_tool_call_count").value == 1
    assert _metric(report, "tool_failure_fraction").value == 1.0
    assert _metric(report, "invalid_tool_attempt_count").value == 0
    assert _metric(report, "tool_unavailable_count").value == 0
    service.registry_factory = original


def test_tool_unavailability_is_separate_from_provider_unavailability(tmp_path):
    service, _, calls, _, body = _service(tmp_path, (_tool("read_document", document_id=DOC),))
    service.registry_factory = lambda: build_tool_registry(_services(
        calls, failure=HTTPException(status_code=503, detail="synthetic unavailable"),
    ))
    created = _create(service, body)
    final = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, final.run_id)
    assert final.result.failure.code == "tool_unavailable" and calls == ["read_document"]
    assert _metric(report, "tool_unavailable_count").value == 1
    assert _metric(report, "tool_failure_fraction").value == 1.0
    assert _metric(report, "decision_provider_unavailable").value is False


def test_decision_provider_unavailable_is_availability_not_completion(tmp_path):
    service, _, calls, _, body = _service(tmp_path)
    service.decision_model_factory = None
    created = _create(service, body)
    run = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, run.run_id)
    assert calls == [] and run.result.agent_status == "unavailable"
    assert _metric(report, "decision_provider_unavailable").value is True
    assert _metric(report, "execution_completed").value is False
    assert _metric(report, "recorded_tool_decision_count").value == 0
    assert _metric(report, "tool_admission_fraction").status == "not_applicable"


def test_provider_tool_permission_denial_has_no_admitted_call(tmp_path):
    body = AgentRunCreateRequest(
        goal="Find provider-backed risk evidence.", allowed_tools=["ask_rag"],
        allow_provider_tool_execution=False,
    )
    _, run, events, calls = _snapshot(tmp_path, (
        _tool("ask_rag", question="What is the risk?"),
    ), body=body)
    report = evaluate_agent_run(run, events)
    assert calls == []
    assert _metric(report, "policy_denial_attempt_count").value == 1
    assert _metric(report, "admitted_tool_call_count").value == 0
    assert dict(report.facts.rejected_tool_codes) == {"tool_provider_required": 1}


def test_decision_provider_permission_denial_is_counted_without_a_decision_event(tmp_path):
    model = ScriptedDecisionModel(_final("Unused answer."), requires_provider=True)
    service, _, calls, _, body = _service(
        tmp_path, model_factory=lambda _identity: model,
    )
    created = _create(service, body)
    final = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, final.run_id)
    assert final.result.failure.code == "decision_provider_required"
    assert model.requests == [] and calls == []
    assert _metric(report, "recorded_tool_decision_count").value == 0
    assert _metric(report, "policy_denial_attempt_count").value == 1
    assert _metric(report, "step_budget_utilization").value == 0.0
    assert parse_agent_evaluation_report(canonical_agent_report_bytes(report)) == report


def test_completed_research_uses_frozen_objective_threshold_and_canonical_ledger(tmp_path):
    database = WorkspaceDatabase(tmp_path / "research.sqlite3")
    database.initialize()
    calls = []
    model = ScriptedDecisionModel(
        _research_tool("apple_risk", "read_document", document_id=DOC),
        _research_tool("microsoft_risk", "read_document", document_id=MSFT_DOC),
        _research_final("Both filings provide evidence.", ("chunk_id", CHUNK), ("chunk_id", MSFT_CHUNK)),
    )
    service = AgentDurableService(
        SQLiteJobRepository(database), lambda: build_tool_registry(_two_company_services(calls)),
        decision_model_factory=lambda _identity: model, decision_model_id="scripted_test",
    )
    config = _config(
        ResearchObjective(objective_id="apple_risk", question="Find Apple risk evidence", ticker_scope="AAPL"),
        ResearchObjective(objective_id="microsoft_risk", question="Find Microsoft risk evidence", ticker_scope="MSFT"),
    )
    created = _create(service, AgentRunCreateRequest(goal="Compare bounded risk evidence.", research=config))
    run = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, run.run_id)
    assert run.state == "succeeded" and calls == ["read_document", "read_document"]
    assert _metric(report, "objective_coverage").value == 1.0
    assert _metric(report, "unresolved_gap_fraction").value == 0.0
    assert _metric(report, "evidence_identity_validity").value == 1.0
    assert _metric(report, "research_evidence_count").value == 2
    assert _metric(report, "distinct_document_count").value == 2
    assert _metric(report, "distinct_chunk_count").value == 2
    assert _metric(report, "final_reference_validity").value == 1.0
    assert report.facts.gap_counts == tuple((code, 0) for code in (
        "below_threshold", "ledger_full", "no_evidence", "search_exhausted",
    ))
    assert parse_agent_evaluation_report(canonical_agent_report_bytes(report)) == report


def test_three_objectives_two_sufficient_preserves_exact_denominator(tmp_path):
    database = WorkspaceDatabase(tmp_path / "partial.sqlite3")
    database.initialize()
    calls = []
    model = ScriptedDecisionModel(
        _research_tool("apple_risk", "read_document", document_id=DOC),
        _research_tool("microsoft_risk", "read_document", document_id=MSFT_DOC),
        _research_final("Two filings provide evidence.",
                        ("chunk_id", CHUNK), ("chunk_id", MSFT_CHUNK),
                        unresolved=("third_risk",)),
    )
    service = AgentDurableService(
        SQLiteJobRepository(database), lambda: build_tool_registry(_two_company_services(calls)),
        decision_model_factory=lambda _identity: model, decision_model_id="scripted_test",
    )
    config = _config(
        ResearchObjective(objective_id="apple_risk", question="Find Apple risk evidence", ticker_scope="AAPL"),
        ResearchObjective(objective_id="microsoft_risk", question="Find Microsoft risk evidence", ticker_scope="MSFT"),
        ResearchObjective(objective_id="third_risk", question="Find a third risk source"),
    )
    created = _create(service, AgentRunCreateRequest(goal="Compare three bounded objectives.", research=config))
    final = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, final.run_id)
    coverage = _metric(report, "objective_coverage")
    assert final.state == "succeeded" and calls == ["read_document", "read_document"]
    assert (coverage.numerator, coverage.denominator, coverage.value) == (2, 3, 0.6667)
    unresolved = _metric(report, "unresolved_gap_fraction")
    assert (unresolved.numerator, unresolved.denominator, unresolved.value) == (1, 3, 0.3333)
    assert dict(report.facts.gap_counts)["no_evidence"] == 1


@pytest.mark.parametrize("scenario,expected_gap", [
    ("no_evidence", "no_evidence"),
    ("search_exhausted", "search_exhausted"),
    ("below_threshold", "below_threshold"),
    ("ledger_full", "ledger_full"),
])
def test_research_gap_categories_are_exact(tmp_path, scenario, expected_gap):
    calls = []
    if scenario == "no_evidence":
        decisions = (
            _research_tool("apple_risk", "search_documents", query="risk", ticker="AAPL"),
            _research_final("No evidence.", unresolved=("apple_risk",)),
        )
        config = _config()
        services = _services(calls, size=0)
    elif scenario == "search_exhausted":
        decisions = (
            _research_tool("apple_risk", "search_documents", query="risk one", ticker="AAPL"),
            _research_tool("apple_risk", "search_documents", query="risk two", ticker="AAPL"),
            _research_final("No evidence.", unresolved=("apple_risk",)),
        )
        config = _config()
        services = _services(calls, size=0)
    elif scenario == "below_threshold":
        decisions = (
            _research_tool("apple_risk", "read_document", document_id=DOC),
            _research_final("Partial evidence.", unresolved=("apple_risk",)),
        )
        config = _config(min_evidence_per_objective=2)
        services = _services(calls)
    else:
        decisions = (
            _research_tool("apple_risk", "read_document", document_id=DOC, page_size=2),
            _research_final("Partial evidence.", unresolved=("apple_risk",)),
        )
        config = _config(min_evidence_per_objective=2, max_evidence_entries=1)
        services = _services(calls, size=2)
    database = WorkspaceDatabase(tmp_path / "gaps.sqlite3")
    database.initialize()
    service = AgentDurableService(
        SQLiteJobRepository(database), lambda: build_tool_registry(services),
        decision_model_factory=lambda _identity: ScriptedDecisionModel(*decisions),
        decision_model_id="scripted_test",
    )
    created = _create(service, AgentRunCreateRequest(goal="Research bounded risk evidence.", research=config))
    run = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, run.run_id)
    assert run.result.research.gaps[0].code == expected_gap
    assert dict(report.facts.gap_counts)[expected_gap] == 1
    assert _metric(report, "objective_coverage").value == 0.0
    assert _metric(report, "unresolved_gap_fraction").value == 1.0


def test_cross_run_reference_and_conflicting_source_pair_fail_closed(tmp_path):
    body = AgentRunCreateRequest(goal="Research bounded evidence.", research=_config())
    service, run, events, _ = _snapshot(tmp_path, (
        _research_tool("apple_risk", "read_document", document_id=DOC),
        _research_final("Cited evidence.", ("chunk_id", CHUNK)),
    ), body=body)
    forged_ref = run.result.model_copy(update={
        "evidence_refs": (run.result.evidence_refs[0].model_copy(update={"value": MSFT_CHUNK}),),
    })
    final_event = events[-3]
    forged_summary = final_event.summary.model_copy(update={
        "evidence_refs": [forged_ref.evidence_refs[0]],
    })
    forged_events = (*events[:-3], final_event.model_copy(update={"summary": forged_summary}), *events[-2:])
    with pytest.raises(CorruptAgentSnapshot):
        evaluate_agent_run(run.model_copy(update={"result": forged_ref}), forged_events)
    evidence = run.result.research.evidence[0].model_copy(update={"chunk_id": MSFT_CHUNK})
    forged_research = run.result.research.model_copy(update={"evidence": (evidence,)})
    forged_result = run.result.model_copy(update={"research": forged_research})
    with pytest.raises(CorruptAgentSnapshot):
        evaluate_agent_run(run.model_copy(update={"result": forged_result}), events)
    scoped = evidence.model_copy(update={
        "document_id": MSFT_DOC, "chunk_id": MSFT_CHUNK, "ticker": "MSFT",
    })
    scoped_research = run.result.research.model_copy(update={"evidence": (scoped,)})
    with pytest.raises(CorruptAgentSnapshot):
        evaluate_agent_run(run.model_copy(update={
            "result": run.result.model_copy(update={"research": scoped_research}),
        }), events)
    assert evaluate_durable_agent_run(service, run.run_id).digest


def test_incomplete_generic_observation_projection_reports_unavailable_reference_check(tmp_path):
    service, _, calls, _, body = _service(tmp_path, (
        _tool("read_document", document_id=DOC, page_size=8),
        _final("Grounded filing evidence.", ("document_id", DOC)),
    ))
    service.registry_factory = lambda: build_tool_registry(_services(calls, size=8))
    created = _create(service, body)
    final = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, final.run_id)
    assert final.state == "succeeded" and calls == ["read_document"]
    assert _metric(report, "final_reference_validity").status == "unavailable"
    assert _metric(report, "final_reference_validity").reason_code == "incomplete_observation_refs"


def test_rejected_unseen_final_reference_is_counted_without_fabricating_a_final_score(tmp_path):
    _, run, events, calls = _snapshot(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Unseen citation.", ("chunk_id", MSFT_CHUNK)),
    ))
    report = evaluate_agent_run(run, events)
    assert calls == ["read_document"] and run.result.agent_status == "invalid_decision"
    assert _metric(report, "invalid_final_attempt_count").value == 1
    assert _metric(report, "final_reference_validity").status == "not_applicable"


def test_interrupted_run_retains_recorded_tool_step_lower_bound(tmp_path):
    service, repo, _, _, body = _service(tmp_path)
    created = _create(service, body)
    job = repo.get_job("job_" + created.run_id[6:])
    running = repo.transition_job(job.job_id, expected_revision=job.revision, target_state="running")
    repo.append_agent_decision_event(
        job.job_id, event_key="decision_1",
        payload={
            "decision_index": 1, "decision_kind": "tool", "tool_name": "read_document",
            "argument_names": ["document_id"], "outcome": "observed", "evidence_count": 0,
            "evidence_refs": [], "step_count": 1, "tool_call_count": 1,
            "failure_code": None,
        }, step_count=1, max_steps=8,
    )
    repo.recover_interrupted_jobs()
    report = evaluate_durable_agent_run(service, created.run_id)
    assert report.facts.terminal_state == "interrupted"
    assert _metric(report, "recorded_tool_decision_count").value == 1
    assert _metric(report, "admitted_tool_call_count").value == 1
    assert _metric(report, "tool_admission_fraction").value == 1.0
    assert _metric(report, "step_budget_utilization").status == "unavailable"
    assert _metric(report, "evidence_identity_validity").status == "unavailable"


def test_queued_cancellation_and_restart_interruption_preserve_recorded_facts(tmp_path):
    service, repo, _, _, body = _service(tmp_path)
    queued = _create(service, body, key="cancelled-evaluation")
    cancelled = service.cancel(queued.run_id, expected_revision=queued.revision)
    cancelled_report = evaluate_durable_agent_run(service, cancelled.run_id)
    assert cancelled.state == "cancelled" and cancelled.result is None
    assert _metric(cancelled_report, "execution_completed").value is False
    assert _metric(cancelled_report, "recorded_tool_decision_count").value == 0
    assert _metric(cancelled_report, "step_budget_utilization").status == "unavailable"
    pending = _create(service, body, key="interrupted-evaluation")
    job = repo.get_job("job_" + pending.run_id[6:])
    repo.transition_job(job.job_id, expected_revision=job.revision, target_state="running")
    repo.recover_interrupted_jobs()
    interrupted = service.get(pending.run_id)
    report = evaluate_durable_agent_run(service, pending.run_id)
    assert interrupted.state == "interrupted" and interrupted.result is None
    assert _metric(report, "execution_completed").value is False
    assert _metric(report, "recorded_tool_decision_count").status == "computed"
    assert _metric(report, "budget_exhausted").status == "unavailable"
    assert _metric(report, "final_reference_validity").status == "not_applicable"


def test_midrun_cancellation_keeps_previously_recorded_tool_facts(tmp_path):
    holder = {}

    def request_cancel(_request):
        current = holder["service"].get(holder["run_id"])
        holder["service"].cancel(holder["run_id"], expected_revision=current.revision)
        return _tool("read_document", document_id=DOC, page=2)

    service, _, calls, _, body = _service(tmp_path, (
        _tool("read_document", document_id=DOC), request_cancel,
    ))
    created = _create(service, body)
    holder.update(service=service, run_id=created.run_id)
    final = _run(service, created.run_id)
    report = evaluate_durable_agent_run(service, final.run_id)
    assert final.state == "cancelled" and calls == ["read_document"]
    assert _metric(report, "execution_completed").value is False
    assert _metric(report, "admitted_tool_call_count").value == 1
    assert _metric(report, "tool_failure_fraction").value == 0.0
    assert _metric(report, "final_reference_validity").status == "not_applicable"


def test_corrupt_order_counter_plan_and_nonfinite_report_fail_closed(tmp_path):
    _, run, events, _ = _snapshot(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Grounded evidence.", ("chunk_id", CHUNK)),
    ))
    with pytest.raises(CorruptAgentSnapshot):
        evaluate_agent_run(run, (events[1], events[0], *events[2:]))
    with pytest.raises(CorruptAgentSnapshot):
        evaluate_agent_run(run.model_copy(update={"run_id": "agent_other"}), events)
    with pytest.raises(CorruptAgentSnapshot):
        evaluate_agent_run(run.model_copy(update={
            "failure": AgentRunFailure(code="Bearer synthetic", message="bad"),
        }), events)
    with pytest.raises(CorruptAgentSnapshot):
        evaluate_agent_run(run.model_copy(update={
            "result": run.result.model_copy(update={"tool_call_count": 2}),
        }), events)
    with pytest.raises(CorruptAgentSnapshot):
        evaluate_agent_run(run.model_copy(update={
            "frozen": run.frozen.model_copy(update={"schema_version": 999}),
        }), events)
    report = evaluate_agent_run(run, events)
    payload = json.loads(canonical_agent_report_bytes(report))
    payload["metrics"][3]["metric_version"] = 2
    with pytest.raises(CorruptAgentEvaluationReport):
        parse_agent_evaluation_report(payload)
    with pytest.raises(CorruptAgentEvaluationReport):
        parse_agent_evaluation_report(b" " * (MAX_REPORT_BYTES + 1))
    with pytest.raises(CorruptAgentEvaluationReport):
        parse_agent_evaluation_report('{"protocol":"a","protocol":"b"}')
    payload = json.loads(canonical_agent_report_bytes(report))
    payload["metrics"][3]["value"] = float("nan")
    with pytest.raises(CorruptAgentEvaluationReport):
        parse_agent_evaluation_report(payload)


def test_digest_binds_metric_run_and_provenance_without_text(tmp_path):
    _, run, events, _ = _snapshot(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Grounded evidence.", ("chunk_id", CHUNK)),
    ))
    report = evaluate_agent_run(run, events)
    _, second_run, second_events, _ = _snapshot(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Grounded evidence.", ("chunk_id", CHUNK)),
    ), key="second-evaluation-case")
    second_report = evaluate_agent_run(second_run, second_events)
    assert second_report.run_id != report.run_id and second_report.digest != report.digest
    reordered = json.loads(canonical_agent_report_bytes(report))
    assert parse_agent_evaluation_report(json.dumps(reordered, sort_keys=False)) == report
    for field_name in ("run_id", "metrics", "provenance"):
        altered = json.loads(canonical_agent_report_bytes(report))
        if field_name == "run_id":
            altered["run_id"] = "agent_changed"
        elif field_name == "metrics":
            altered["metrics"][4]["value"] = 1
        else:
            altered["provenance"]["run_revision"] += 1
        with pytest.raises(CorruptAgentEvaluationReport):
            parse_agent_evaluation_report(altered)
    altered = json.loads(canonical_agent_report_bytes(report))
    altered["metrics"][2]["value"] = 2
    altered["metrics"][2]["numerator"] = 2
    altered["digest"] = "sha256:" + hashlib.sha256(canonical_json_bytes({
        key: value for key, value in altered.items() if key != "digest"
    })).hexdigest()
    with pytest.raises(CorruptAgentEvaluationReport):
        parse_agent_evaluation_report(altered)
    assert b"Grounded evidence" not in canonical_agent_report_bytes(report)


def test_evaluation_does_not_invoke_registry_or_network(tmp_path, monkeypatch):
    _, run, events, calls = _snapshot(tmp_path, (
        _tool("read_document", document_id=DOC),
        _final("Grounded evidence.", ("chunk_id", CHUNK)),
    ))
    def forbidden(*_args, **_kwargs):
        raise AssertionError("evaluation tried to execute an Agent capability")
    sentinel = "AGENT_TEST_API_KEY_SECRET_EVAL_9F3C7"
    monkeypatch.setenv("AGENT_TEST_API_KEY", sentinel)
    with monkeypatch.context() as guard:
        guard.setattr(AgentToolRegistry, "invoke", forbidden)
        guard.setattr(socket.socket, "connect", forbidden)
        report = evaluate_agent_run(run, events)
    assert report.digest.startswith("sha256:") and calls == ["read_document"]
    assert sentinel.encode() not in canonical_agent_report_bytes(report)
