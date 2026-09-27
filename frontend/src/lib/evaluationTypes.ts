/** EVAL-001/002 public protocol and EVAL-003 private control DTOs. */
import type { EvaluationRunSummary, PipelineRunState, PipelineStepState } from "../types";

export type NativeMetricId =
  | "native.faithfulness" | "native.answer_relevancy" | "native.context_precision"
  | "native.citation_index_validity" | "native.keyword_recall_proxy" | "native.fallback_correctness";
export type MetricStatus = "computed" | "unavailable" | "not_applicable";
export type ReportStatus = "complete" | "incomplete";
export interface EvaluationPage<T> { items: T[]; total: number; page: number; page_size: number }
export interface NativeMetricDefinition {
  metric_id: NativeMetricId;
  metric_version: number;
  label: string;
  meaning: string;
  value_kind: "ratio" | "boolean";
  aggregate_kind: "mean" | "success_rate";
  direction: "higher_is_better";
  source: "precomputed_native_judge" | "deterministic";
  minimum: number;
  maximum: number;
  required_inputs: string[];
}
export interface EvaluationMetrics {
  protocol: "native-evaluation";
  protocol_version: 1;
  capabilities: { provider_free: true; computes_judge_scores: false; requires_bound_judge_scores: true };
  items: NativeMetricDefinition[];
  total: number;
}
export interface NativeBinding {
  engine_id: "native";
  engine_version: number;
  dataset_id: string;
  dataset_version: string;
  dataset_revision: string;
  generator_model_id: string;
  generator_model_fingerprint: string;
  generation_prompt_sha256: string;
  generation_binding: string;
  retrieval_binding: string;
  retrieval_config_fingerprint: string;
  embedding_fingerprint: string;
  reranker_fingerprint: string;
  context_binding: string;
  judge_model_id: string | null;
  judge_prompt_sha256: string | null;
  judge_binding: string | null;
}
export interface NativeCaseMetric {
  metric_id: NativeMetricId;
  metric_version: number;
  status: MetricStatus;
  value: number | boolean | null;
  reason_code: string | null;
}
export interface NativeAggregateMetric {
  metric_id: NativeMetricId;
  metric_version: number;
  status: MetricStatus;
  value: number | null;
  total_cases: number;
  denominator: number;
  unavailable_count: number;
  not_applicable_count: number;
}
export interface NativeCaseResult { case_id: string; context_sha256: string | null; metrics: NativeCaseMetric[] }
export interface NativePublishedSummary {
  protocol: "native-evaluation";
  protocol_version: 1;
  run_id: string;
  status: ReportStatus;
  published_at: string;
  report_digest: string;
  case_count: number;
  binding: NativeBinding;
  aggregates: NativeAggregateMetric[];
}
export interface NativePublishedDetail extends NativePublishedSummary {
  schema_version: 1;
  metric_definitions: NativeMetricDefinition[];
}
export type PublishedSummary = NativePublishedSummary | EvaluationRunSummary;
export interface SafeLegacyDetail extends EvaluationRunSummary {
  cases: Array<{ case_id: string; status: "OK" | "ERROR" | "MISSING"; scores: Record<string, number> }>;
}
export type PublishedDetail = NativePublishedDetail | SafeLegacyDetail;
export function isNativeReport(report: PublishedDetail): report is NativePublishedDetail;
export function isNativeReport(report: PublishedSummary): report is NativePublishedSummary;
export function isNativeReport(report: PublishedSummary | PublishedDetail): report is NativePublishedSummary {
  return "protocol" in report && report.protocol === "native-evaluation";
}
export interface NativeResultsPage extends EvaluationPage<NativeCaseResult> {
  run_id: string;
  report_digest: string;
  report_status: ReportStatus;
  metric_definitions: NativeMetricDefinition[];
  aggregates: NativeAggregateMetric[];
}
export interface NativeCompareRequest {
  baseline_run_id: string;
  candidate_run_id: string;
  metric_ids?: NativeMetricId[] | null;
  sort?: "case_id_asc";
  page?: number;
  page_size?: number;
}
export type ComparisonStatus = "comparable" | "unavailable" | "not_applicable" | "incompatible";
export interface NativeMetricComparison {
  metric_id: NativeMetricId;
  metric_version: number;
  direction: "higher_is_better" | "lower_is_better";
  baseline: NativeAggregateMetric;
  candidate: NativeAggregateMetric;
  same_computed_case_coverage: boolean;
  status: ComparisonStatus;
  candidate_minus_baseline: number | null;
  reason_code: string | null;
}
export interface NativeCaseComparison {
  case_id: string;
  pairing: "paired" | "baseline_only" | "candidate_only";
  baseline_context_sha256: string | null;
  candidate_context_sha256: string | null;
  metrics: Array<{
    metric_id: NativeMetricId;
    metric_version: number;
    baseline: NativeCaseMetric | null;
    candidate: NativeCaseMetric | null;
    status: ComparisonStatus | "unpaired";
    candidate_minus_baseline: number | null;
    reason_code: string | null;
  }>;
}
export interface NativeComparison {
  baseline_run_id: string;
  candidate_run_id: string;
  baseline_digest: string;
  candidate_digest: string;
  baseline_status: ReportStatus;
  candidate_status: ReportStatus;
  baseline_binding: NativeBinding;
  candidate_binding: NativeBinding;
  same_case_universe: boolean;
  eligible_for_complete_comparison: boolean;
  eligibility_reasons: string[];
  metrics: NativeMetricComparison[];
  cases: NativeCaseComparison[];
  total_cases: number;
  page: number;
  page_size: number;
}
export interface NativeTrendPoint {
  run_id: string;
  report_digest: string;
  published_at: string;
  report_status: ReportStatus;
  aggregate: NativeAggregateMetric;
  generator_model_id: string;
  generation_binding: string;
  retrieval_binding: string;
  judge_binding: string | null;
}
export interface NativeTrends {
  metric_id: NativeMetricId;
  groups: Array<{ binding_group: string; metric_id: NativeMetricId; metric_version: number; points: NativeTrendPoint[] }>;
  total_points: number;
  page: number;
  page_size: number;
}
export type FailureCategory = "fallback_expectation_mismatch" | "invalid_citation_index" | "missing_required_keyword" | "unavailable_prerequisite";
export interface NativeFailureFinding {
  category_id: FailureCategory;
  case_id: string;
  context_sha256: string | null;
  metric_id: NativeMetricId;
  metric_version: number;
  metric_status: "computed" | "unavailable";
  value: number | boolean | null;
  reason_code: string | null;
}
export interface NativeFailures extends EvaluationPage<NativeFailureFinding> {
  run_id: string;
  report_digest: string;
  report_status: ReportStatus;
  category_counts: Array<{ category_id: FailureCategory; count: number }>;
}
export type EvaluationJobState = PipelineRunState;
export interface EvaluationJobProgress { stage: string | null; current: number | null; total: number | null }
export interface FrozenEvaluationSnapshot {
  schema_version: 1;
  request_fingerprint: string;
  protocol: "native-evaluation";
  protocol_version: 1;
  engine: "native";
  engine_version: 1;
  mode: "provider_backed";
  metric_versions: Record<string, number>;
  metric_definitions_digest: string;
  artifact_id: string;
  artifact_digest: string;
  retrieval_fingerprints: Record<string, string | number | null>;
  case_ids: string[];
  case_hashes: string[];
  context_hashes: string[];
  budget_unit: "provider_attempt_slot";
  budget_limit: number;
  maximum_required_attempts: number;
  binding: NativeBinding;
  generation_system_prompt_sha256: string;
  generation_context_builder_fingerprint: string;
  answer_completion_fingerprint: string;
  answer_postprocessor_profile_sha256: string;
  generation_prompt_template_sha256: string;
  judge_system_prompt_sha256: string;
  judge_context_builder_fingerprint: string;
  judge_max_tokens: number;
  runtime_code_fingerprints: Record<string, string>;
  runtime_source_digest: string;
  judge_prompt_template_sha256: string;
  snapshot_digest: string;
}
export interface EvaluationJob {
  id: string;
  state: EvaluationJobState;
  revision: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  cancellation_requested_at: string | null;
  configuration_fingerprint: string;
  frozen: FrozenEvaluationSnapshot;
  progress: EvaluationJobProgress;
  steps: Array<{
    step_id: string; job_id: string; ordinal: number; name: "execute_cases" | "aggregate_report";
    state: PipelineStepState; revision: number; started_at: string | null; finished_at: string | null;
  }>;
  artifact_references: string[];
  budget_consumed: number;
  publication_status: "not_published";
  report_digest: string | null;
  result: { report_digest: string; budget_consumed: number } | null;
  failure: { code: string; message: string } | null;
}
export interface EvaluationJobCreate {
  artifact_id: string;
  engine: "native";
  metrics: NativeMetricId[];
  mode: "provider_backed";
  budget: number;
}
/** Deliberately excludes private question/answer/evidence/ground-truth fields. */
export interface SafeJobCase {
  case_id: string;
  metrics: NativeCaseMetric[];
  generation_context_sha256: string | null;
  judge_context_sha256: string | null;
  judge_prompt_sha256: string;
}
export interface SafeJobResults extends EvaluationPage<SafeJobCase> {
  job_id: string;
  report_status: ReportStatus | null;
  report_digest: string | null;
  metric_definitions: NativeMetricDefinition[];
  aggregates: NativeAggregateMetric[];
}
export interface EvaluationJobEvent {
  event_id: string;
  job_id: string;
  sequence: number;
  event_type: string;
  state: EvaluationJobState | null;
  reason_code: string | null;
  progress: EvaluationJobProgress;
  occurred_at: string;
}
