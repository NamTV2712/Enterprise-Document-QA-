/** Wire contracts for the private, single-Agent durable workspace. */
export type AgentRunState = "queued" | "running" | "cancelling" | "cancelled" | "succeeded" | "failed" | "interrupted";
export type AgentStatus = "completed" | "invalid_decision" | "policy_denied" | "budget_exhausted" | "unavailable" | "failed" | "cancelled";
export type AgentToolName = "search_documents" | "inspect_retrieval" | "read_document" | "ask_rag";
export type AgentGapCode = "no_evidence" | "below_threshold" | "search_exhausted" | "ledger_full";
export type AgentMetricStatus = "computed" | "unavailable" | "not_applicable";
export type AgentMetricKind = "boolean" | "count" | "ratio";
export type AgentMetricDirection = "higher_is_better" | "lower_is_better" | "neutral";

export interface AgentEvidenceRef { kind: "document_id" | "chunk_id" | "search_id"; value: string }
export interface AgentFailure { domain: "model" | "policy" | "tool" | "system"; code: string }
export interface AgentResearchObjective { objective_id: string; question: string; ticker_scope: string | null }
export interface AgentResearchConfig {
  version: "agent_research_v1";
  objectives: AgentResearchObjective[];
  max_evidence_entries: number;
  max_search_attempts_per_objective: number;
  min_evidence_per_objective: number;
}
export interface AgentResearchEvidence {
  document_id: string | null;
  chunk_id: string;
  ticker: string | null;
  objective_ids: string[];
  first_tool: AgentToolName;
  first_step: number;
}
export interface AgentResearchSummary {
  version: "agent_research_v1";
  objectives: { objective_id: string; coverage: "none" | "some" | "sufficient"; evidence_count: number; search_attempts: number }[];
  evidence: AgentResearchEvidence[];
  gaps: { objective_id: string; code: AgentGapCode }[];
  evidence_capped: boolean;
}
export interface AgentLimits {
  max_steps: number;
  max_tool_calls: number;
  per_tool_calls: Record<AgentToolName, number>;
  max_observations: number;
  max_evidence_per_observation: number;
  max_excerpt_chars: number;
  max_observation_bytes: number;
  max_total_observation_bytes: number;
}
export interface AgentFrozenPlan {
  schema_version: 1;
  protocol: "bounded_single_agent";
  decision_model_id: string;
  decision_provider?: {
    provider: "groq";
    model_id: "openai/gpt-oss-120b" | "openai/gpt-oss-20b";
    adapter_version: "groq_json_schema_v1";
    mechanism: "native_strict_json_schema";
    credential_policy: "pool" | "key5_only";
  } | null;
  goal: string;
  locale: "en" | "vi";
  allowed_tools: AgentToolName[];
  allow_provider_tool_execution: boolean;
  allow_decision_provider_execution: boolean;
  require_observation_for_final: boolean;
  reject_duplicate_calls: boolean;
  limits: AgentLimits;
  research: AgentResearchConfig | null;
}
export interface AgentDurableResult {
  agent_status: AgentStatus;
  answer: string | null;
  evidence_refs: AgentEvidenceRef[];
  step_count: number;
  decision_call_count: number;
  tool_call_count: number;
  per_tool_calls: Record<AgentToolName, number>;
  observation_count: number;
  failure: AgentFailure | null;
  research: AgentResearchSummary | null;
}
export interface AgentRun {
  run_id: string;
  state: AgentRunState;
  revision: number;
  configuration_fingerprint: string;
  frozen: AgentFrozenPlan;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  cancellation_requested_at: string | null;
  progress_current: number | null;
  progress_total: number | null;
  step: { name: "execute_agent"; state: string; revision: number; started_at: string | null; finished_at: string | null };
  result: AgentDurableResult | null;
  failure: { code: string; message: string } | null;
}
export interface AgentRunPage { items: AgentRun[]; total: number; page: number; page_size: number }
export interface AgentRunResult { run_id: string; state: AgentRunState; revision: number; result: AgentDurableResult | null; failure: { code: string; message: string } | null }
export interface AgentEventSummary {
  decision_index: number;
  decision_kind: "tool" | "final" | "invalid";
  tool_name: string | null;
  objective_id: string | null;
  argument_names: string[];
  outcome: "observed" | "completed" | "rejected" | "failed";
  evidence_count: number;
  evidence_refs: AgentEvidenceRef[];
  step_count: number;
  tool_call_count: number;
  failure_code: string | null;
}
export interface AgentEvent {
  run_id: string;
  event_id: string;
  sequence: number;
  event_type: string;
  state: AgentRunState | null;
  reason_code: string | null;
  occurred_at: string;
  summary: AgentEventSummary | null;
}
export interface AgentMetricDefinition {
  metric_id: string;
  metric_version: number;
  label: string;
  description: string;
  value_kind: AgentMetricKind;
  direction: AgentMetricDirection;
  applicability: string;
  numerator: string;
  denominator: string | null;
  source_fields: string[];
  meaning: string;
  non_meaning: string;
  minimum: number;
  maximum: number | null;
}
export interface AgentMetricResult {
  metric_id: string;
  metric_version: number;
  status: AgentMetricStatus;
  value: number | boolean | null;
  numerator: number | null;
  denominator: number | null;
  reason_code: string | null;
}
export interface AgentEvaluationReport {
  protocol: "native-agent-evaluation";
  protocol_version: 1;
  run_id: string;
  metric_definitions: AgentMetricDefinition[];
  metrics: AgentMetricResult[];
  facts: {
    terminal_state: AgentRunState;
    agent_status: AgentStatus | null;
    failure_code: string | null;
    recorded_per_tool_calls: [string, number][];
    rejected_tool_codes: [string, number][];
    gap_counts: [AgentGapCode, number][];
  };
  provenance: {
    configuration_fingerprint: string;
    frozen_plan_sha256: string;
    event_sha256: string;
    result_sha256: string | null;
    run_revision: number;
    agent_protocol: string;
    research_version: string | null;
  };
  digest: string;
}
export interface AgentCreateRequest {
  goal: string;
  locale: "en" | "vi";
  allow_decision_provider_execution?: boolean;
  research?: { version: "agent_research_v1"; objectives: AgentResearchObjective[] };
}
