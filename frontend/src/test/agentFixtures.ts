import type { AgentEvaluationReport, AgentEvent, AgentRun, AgentRunPage } from "../lib/agentTypes";

export const AGENT_RUN_ID = "agent_alpha";
export const AGENT_PROVIDER_RUN_ID = "agent_provider";
export const AGENT_RUNNING_RUN_ID = "agent_running";
const NOW = "2026-09-30T02:00:00Z";

export const agentResearchRun: AgentRun = {
  run_id: AGENT_RUN_ID, state: "succeeded", revision: 9,
  configuration_fingerprint: "a".repeat(64), created_at: NOW, updated_at: NOW, started_at: NOW, finished_at: NOW,
  cancellation_requested_at: null, progress_current: null, progress_total: null,
  step: { name: "execute_agent", state: "succeeded", revision: 2, started_at: NOW, finished_at: NOW },
  frozen: {
    schema_version: 1, protocol: "bounded_single_agent", decision_model_id: "scripted_fixture",
    goal: "Compare Microsoft and Alphabet AI risks.", locale: "en", allowed_tools: ["search_documents", "read_document"],
    allow_provider_tool_execution: false, allow_decision_provider_execution: false,
    require_observation_for_final: true, reject_duplicate_calls: true,
    limits: {
      max_steps: 8, max_tool_calls: 5, per_tool_calls: { search_documents: 2, inspect_retrieval: 2, read_document: 3, ask_rag: 1 },
      max_observations: 5, max_evidence_per_observation: 8, max_excerpt_chars: 160,
      max_observation_bytes: 4096, max_total_observation_bytes: 16384,
    },
    research: { version: "agent_research_v1", objectives: [
      { objective_id: "microsoft_risk", question: "Find Microsoft's AI risk evidence", ticker_scope: "MSFT" },
      { objective_id: "alphabet_risk", question: "Find Alphabet's AI risk evidence", ticker_scope: "GOOGL" },
    ], max_evidence_entries: 6, max_search_attempts_per_objective: 2, min_evidence_per_objective: 1 },
  },
  result: {
    agent_status: "completed", answer: "Microsoft evidence was recorded; Alphabet evidence remains unresolved.",
    evidence_refs: [{ kind: "document_id", value: "MSFT:10-K:2025" }], step_count: 4, decision_call_count: 4,
    tool_call_count: 3, per_tool_calls: { search_documents: 2, inspect_retrieval: 0, read_document: 1, ask_rag: 0 },
    observation_count: 3, failure: null,
    research: { version: "agent_research_v1", objectives: [
      { objective_id: "microsoft_risk", coverage: "sufficient", evidence_count: 1, search_attempts: 0 },
      { objective_id: "alphabet_risk", coverage: "none", evidence_count: 0, search_attempts: 2 },
    ], evidence: [{ document_id: "MSFT:10-K:2025", chunk_id: "MSFT:10-K:2025:chunk-1", ticker: "MSFT", objective_ids: ["microsoft_risk"], first_tool: "read_document", first_step: 1 }],
    gaps: [{ objective_id: "alphabet_risk", code: "search_exhausted" }], evidence_capped: false },
  }, failure: null,
};

export const agentProviderRun: AgentRun = {
  ...agentResearchRun, run_id: AGENT_PROVIDER_RUN_ID, state: "failed", revision: 4,
  frozen: { ...agentResearchRun.frozen, goal: "Review recorded Agent availability.", decision_model_id: "unconfigured", research: null },
  result: { ...agentResearchRun.result!, agent_status: "unavailable", answer: null, evidence_refs: [], step_count: 0,
    decision_call_count: 0, tool_call_count: 0, per_tool_calls: { search_documents: 0, inspect_retrieval: 0, read_document: 0, ask_rag: 0 },
    observation_count: 0, failure: { domain: "model", code: "decision_provider_unavailable" }, research: null },
  failure: { code: "decision_provider_unavailable", message: "Agent execution ended without a completed answer." },
};

export const agentRunningRun: AgentRun = {
  ...agentProviderRun, run_id: AGENT_RUNNING_RUN_ID, state: "running", revision: 3,
  frozen: { ...agentProviderRun.frozen, goal: "Inspect current filings." },
  step: { ...agentProviderRun.step, state: "running", finished_at: null },
  result: null, failure: null, finished_at: null,
};

export const agentRunPage: AgentRunPage = {
  items: [agentResearchRun, agentProviderRun, agentRunningRun], total: 3, page: 1, page_size: 25,
};

export const agentEvents: AgentEvent[] = [
  { run_id: AGENT_RUN_ID, event_id: "event_1", sequence: 1, event_type: "created", state: "queued", reason_code: null, occurred_at: NOW, summary: null },
  { run_id: AGENT_RUN_ID, event_id: "event_2", sequence: 2, event_type: "state_changed", state: "running", reason_code: null, occurred_at: NOW, summary: null },
  { run_id: AGENT_RUN_ID, event_id: "event_3", sequence: 3, event_type: "step_changed", state: "running", reason_code: null, occurred_at: NOW, summary: null },
  { run_id: AGENT_RUN_ID, event_id: "event_4", sequence: 4, event_type: "agent_decision", state: "running", reason_code: null, occurred_at: NOW,
    summary: { decision_index: 1, decision_kind: "tool", tool_name: "read_document", objective_id: "microsoft_risk", argument_names: ["document_id"], outcome: "observed", evidence_count: 1,
      evidence_refs: [{ kind: "document_id", value: "MSFT:10-K:2025" }], step_count: 1, tool_call_count: 1, failure_code: null } },
  { run_id: AGENT_RUN_ID, event_id: "event_5", sequence: 5, event_type: "agent_decision", state: "running", reason_code: null, occurred_at: NOW,
    summary: { decision_index: 2, decision_kind: "tool", tool_name: "search_documents", objective_id: "alphabet_risk", argument_names: ["query"], outcome: "observed", evidence_count: 0,
      evidence_refs: [], step_count: 2, tool_call_count: 2, failure_code: null } },
  { run_id: AGENT_RUN_ID, event_id: "event_6", sequence: 6, event_type: "agent_decision", state: "running", reason_code: null, occurred_at: NOW,
    summary: { decision_index: 3, decision_kind: "tool", tool_name: "search_documents", objective_id: "alphabet_risk", argument_names: ["query"], outcome: "observed", evidence_count: 0,
      evidence_refs: [], step_count: 3, tool_call_count: 3, failure_code: null } },
  { run_id: AGENT_RUN_ID, event_id: "event_7", sequence: 7, event_type: "agent_decision", state: "running", reason_code: null, occurred_at: NOW,
    summary: { decision_index: 4, decision_kind: "final", tool_name: null, objective_id: null, argument_names: [], outcome: "completed", evidence_count: 1,
      evidence_refs: [{ kind: "document_id", value: "MSFT:10-K:2025" }], step_count: 4, tool_call_count: 3, failure_code: null } },
  { run_id: AGENT_RUN_ID, event_id: "event_8", sequence: 8, event_type: "step_changed", state: "running", reason_code: null, occurred_at: NOW, summary: null },
  { run_id: AGENT_RUN_ID, event_id: "event_9", sequence: 9, event_type: "state_changed", state: "succeeded", reason_code: null, occurred_at: NOW, summary: null },
];

const METRICS = [
  "execution_completed", "recorded_tool_decision_count", "admitted_tool_call_count", "tool_admission_fraction",
  "invalid_tool_attempt_count", "policy_denial_attempt_count", "duplicate_rejection_count", "tool_failure_fraction",
  "tool_unavailable_count", "invalid_final_attempt_count", "step_budget_utilization", "tool_budget_utilization",
  "budget_exhausted", "decision_provider_unavailable", "evidence_identity_validity", "final_reference_validity",
  "objective_coverage", "unresolved_gap_fraction", "research_evidence_count", "distinct_document_count", "distinct_chunk_count",
] as const;

export const agentEvaluation: AgentEvaluationReport = {
  protocol: "native-agent-evaluation", protocol_version: 1, run_id: AGENT_RUN_ID,
  metric_definitions: METRICS.map((name) => ({
    metric_id: `native_agent.${name}`, metric_version: 1, label: name.replace(/_/g, " "), description: name,
    value_kind: (["execution_completed", "budget_exhausted", "decision_provider_unavailable"] as string[]).includes(name) ? "boolean" :
      name.includes("fraction") || name.includes("utilization") || name.includes("validity") || name === "objective_coverage" ? "ratio" : "count",
    direction: "neutral", applicability: "terminal run", numerator: "recorded facts", denominator: null,
    source_fields: ["run.state"], meaning: "Recorded structural outcome.", non_meaning: "Not factual correctness.", minimum: 0, maximum: null,
  })),
  metrics: METRICS.map((name) => {
    const value = name === "execution_completed" ? true : name === "tool_budget_utilization" ? 0.6 :
      name === "objective_coverage" ? 0.5 : name === "evidence_identity_validity" ? 1 : 0;
    if (name === "final_reference_validity") return { metric_id: `native_agent.${name}`, metric_version: 1, status: "unavailable", value: null, numerator: null, denominator: null, reason_code: "incomplete_observation_refs" };
    return { metric_id: `native_agent.${name}`, metric_version: 1, status: "computed", value,
      numerator: typeof value === "boolean" ? Number(value) : name === "tool_budget_utilization" ? 3 : name === "objective_coverage" ? 1 : Number(value),
      denominator: name === "tool_budget_utilization" ? 5 : name === "objective_coverage" ? 2 : typeof value === "boolean" ? 1 : null, reason_code: null };
  }),
  facts: { terminal_state: "succeeded", agent_status: "completed", failure_code: null, recorded_per_tool_calls: [], rejected_tool_codes: [], gap_counts: [] },
  provenance: { configuration_fingerprint: "a".repeat(64), frozen_plan_sha256: `sha256:${"a".repeat(64)}`,
    event_sha256: `sha256:${"b".repeat(64)}`, result_sha256: `sha256:${"c".repeat(64)}`, run_revision: 9,
    agent_protocol: "bounded_single_agent", research_version: "agent_research_v1" },
  digest: `sha256:${"d".repeat(64)}`,
};
