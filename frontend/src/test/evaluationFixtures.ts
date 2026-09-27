/** Synthetic EVAL DTOs for hermetic unit/browser tests; never production data. */
import type { EvaluationJob, NativeBinding, NativeMetricDefinition, NativeMetricId, NativePublishedDetail, NativePublishedSummary, SafeJobResults } from "../lib/evaluationTypes";

export const nativeMetricIds: NativeMetricId[] = ["native.faithfulness", "native.answer_relevancy", "native.context_precision", "native.citation_index_validity", "native.keyword_recall_proxy", "native.fallback_correctness"];
export const syntheticHash = "a".repeat(64);
export function nativeDefinitions(): NativeMetricDefinition[] {
  const labels = ["Faithfulness", "Answer relevancy", "Context precision", "Citation index validity", "Keyword recall proxy", "Fallback correctness"];
  const meanings = [
    "Existing native judge estimate of answer claims supported by the same rendered evidence; not deterministic claim verification.",
    "Existing native judge estimate of how well the answer addresses the question against ground truth.",
    "Existing native judge estimate of the fraction of retrieved chunks useful for the answer.",
    "Fraction of Source N references whose indices exist in the rendered evidence; not claim support.",
    "Fraction of explicit required keywords found in rendered evidence; not Recall@K or semantic relevance.",
    "Whether the answer's existing insufficient-information fallback phrase matches the case expectation.",
  ];
  return nativeMetricIds.map((metric_id, index) => ({
    metric_id, metric_version: 1, label: labels[index], meaning: meanings[index],
    value_kind: index === 5 ? "boolean" : "ratio", aggregate_kind: index === 5 ? "success_rate" : "mean",
    direction: "higher_is_better", source: index < 3 ? "precomputed_native_judge" : "deterministic", minimum: 0, maximum: 1,
    required_inputs: index < 3 ? ["answer", "rendered_context", "ground_truth", "bound_judge_score"]
      : index === 3 ? ["answer", "rendered_context"] : index === 4 ? ["rendered_context", "required_keywords"] : ["answer", "expects_fallback"],
  }));
}
export function nativeBinding(): NativeBinding {
  return {
    engine_id: "native", engine_version: 1, dataset_id: "synthetic-dataset", dataset_version: "fixture-v1", dataset_revision: syntheticHash,
    generator_model_id: "synthetic-generator", generator_model_fingerprint: syntheticHash, generation_prompt_sha256: syntheticHash,
    generation_binding: syntheticHash, retrieval_binding: syntheticHash, retrieval_config_fingerprint: syntheticHash,
    embedding_fingerprint: syntheticHash, reranker_fingerprint: syntheticHash, context_binding: syntheticHash,
    judge_model_id: "synthetic-judge", judge_prompt_sha256: syntheticHash, judge_binding: syntheticHash,
  };
}
export function evaluationJob(id = "job-a", overrides: Partial<EvaluationJob> = {}): EvaluationJob {
  return {
    id, state: "queued", revision: 1, created_at: "2026-09-26T00:00:00Z", updated_at: "2026-09-26T00:00:00Z",
    started_at: null, finished_at: null, cancellation_requested_at: null, configuration_fingerprint: syntheticHash,
    frozen: {
      schema_version: 1, request_fingerprint: syntheticHash, protocol: "native-evaluation", protocol_version: 1,
      engine: "native", engine_version: 1, mode: "provider_backed", metric_versions: Object.fromEntries(nativeMetricIds.map((id) => [id, 1])),
      metric_definitions_digest: syntheticHash, artifact_id: "synthetic-phase1", artifact_digest: syntheticHash,
      retrieval_fingerprints: { top_k: 5 }, case_ids: ["case-a", "case-b"], case_hashes: [syntheticHash, syntheticHash],
      context_hashes: [syntheticHash, syntheticHash], budget_unit: "provider_attempt_slot", budget_limit: 6, maximum_required_attempts: 6,
      binding: nativeBinding(), generation_system_prompt_sha256: syntheticHash, generation_context_builder_fingerprint: syntheticHash,
      answer_completion_fingerprint: syntheticHash, answer_postprocessor_profile_sha256: syntheticHash,
      generation_prompt_template_sha256: syntheticHash, judge_system_prompt_sha256: syntheticHash,
      judge_context_builder_fingerprint: syntheticHash, judge_max_tokens: 256, runtime_code_fingerprints: { engine: syntheticHash },
      runtime_source_digest: syntheticHash, judge_prompt_template_sha256: syntheticHash, snapshot_digest: syntheticHash,
    },
    progress: { stage: null, current: null, total: null },
    steps: ["execute_cases", "aggregate_report"].map((name, index) => ({
      name: name as "execute_cases" | "aggregate_report", step_id: `${id}-step-${index}`, job_id: id,
      ordinal: index + 1, state: "pending", revision: 1, started_at: null, finished_at: null,
    })),
    artifact_references: [], budget_consumed: 0, publication_status: "not_published", report_digest: null,
    result: null, failure: null, ...overrides,
  };
}
export function publishedSummary(id = "native-a", score = 0): NativePublishedSummary {
  return {
    protocol: "native-evaluation", protocol_version: 1, run_id: id, status: "complete",
    published_at: "2026-09-26T00:00:00Z", report_digest: `${id}-${syntheticHash}`, case_count: 5,
    binding: nativeBinding(), aggregates: nativeMetricIds.map((metric_id, index) => ({
      metric_id, metric_version: 1, status: index === 2 ? "unavailable" : index === 4 ? "not_applicable" : "computed",
      value: index === 2 || index === 4 ? null : score, total_cases: 5, denominator: index === 2 || index === 4 ? 0 : 3,
      unavailable_count: index === 2 ? 5 : 1, not_applicable_count: index === 4 ? 5 : 1,
    })),
  };
}
export function publishedDetail(id = "native-a", score = 0): NativePublishedDetail {
  return { ...publishedSummary(id, score), schema_version: 1, metric_definitions: nativeDefinitions() };
}
export function jobResults(id = "job-a"): SafeJobResults {
  return { job_id: id, items: [], total: 0, page: 1, page_size: 50, report_status: null, report_digest: null, metric_definitions: nativeDefinitions(), aggregates: [] };
}
