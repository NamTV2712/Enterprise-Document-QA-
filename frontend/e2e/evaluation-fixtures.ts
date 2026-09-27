import type { Page, Route } from "@playwright/test";

import { API_ORIGIN, installApiFixtures } from "./fixtures";
import {
  evaluationJob,
  nativeDefinitions,
  nativeMetricIds,
  publishedDetail,
  publishedSummary,
  syntheticHash,
} from "../src/test/evaluationFixtures";
import type {
  EvaluationJob,
  EvaluationJobEvent,
  EvaluationJobState,
  NativeAggregateMetric,
  NativeComparison,
  NativeFailures,
  NativeResultsPage,
  NativeTrends,
} from "../src/lib/evaluationTypes";

export const EVALUATION_FIXTURE_TOKEN = "ui011-memory-only-fixture-token";
const CORS = {
  "access-control-allow-origin": "http://localhost:4173",
  "access-control-allow-headers": "Authorization, Content-Type, Idempotency-Key, If-Match, Last-Event-ID",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-expose-headers": "ETag",
};

function aggregate(score: number, metricIndex: number): NativeAggregateMetric {
  const unavailable = metricIndex === 2;
  const notApplicable = metricIndex === 4;
  return {
    metric_id: nativeMetricIds[metricIndex], metric_version: 1,
    status: unavailable ? "unavailable" : notApplicable ? "not_applicable" : "computed",
    value: unavailable || notApplicable ? null : score,
    total_cases: 5, denominator: unavailable || notApplicable ? 0 : 3,
    unavailable_count: unavailable ? 5 : 1, not_applicable_count: notApplicable ? 5 : 1,
  };
}

export function evaluationResults(runId: string, page = 1): NativeResultsPage {
  return {
    run_id: runId, report_digest: `${runId}-${syntheticHash}`, report_status: "complete",
    metric_definitions: nativeDefinitions(), aggregates: nativeMetricIds.map((_, index) => aggregate(index ? 0.5 : 0, index)),
    items: [{
      case_id: `safe-case-${page}`, context_sha256: syntheticHash,
      metrics: [
        { metric_id: "native.faithfulness", metric_version: 1, status: "computed", value: 0, reason_code: null },
        { metric_id: "native.fallback_correctness", metric_version: 1, status: "computed", value: false, reason_code: "fallback_expectation_mismatch" },
        { metric_id: "native.context_precision", metric_version: 1, status: "unavailable", value: null, reason_code: "unavailable_prerequisite" },
        { metric_id: "native.keyword_recall_proxy", metric_version: 1, status: "not_applicable", value: null, reason_code: null },
      ],
    }],
    total: 51, page, page_size: 50,
  };
}

export function populatedJob(id: string, state: EvaluationJobState = "queued", overrides: Partial<EvaluationJob> = {}): EvaluationJob {
  const running = state === "running";
  const terminal = ["cancelled", "succeeded", "failed", "interrupted"].includes(state);
  return evaluationJob(id, {
    state, revision: running || terminal ? 2 : 1,
    started_at: running || terminal ? "2026-09-26T00:01:00Z" : null,
    finished_at: terminal ? "2026-09-26T00:02:00Z" : null,
    progress: running ? { stage: "execute_cases", current: 1, total: 2 } : terminal ? { stage: "aggregate_report", current: 2, total: 2 } : { stage: null, current: null, total: null },
    steps: ["execute_cases", "aggregate_report"].map((name, index) => ({
      name: name as "execute_cases" | "aggregate_report", step_id: `${id}-step-${index + 1}`, job_id: id,
      ordinal: index + 1, state: terminal ? "succeeded" : running && index === 0 ? "running" : "pending",
      revision: running || terminal ? 2 : 1, started_at: running || terminal ? "2026-09-26T00:01:00Z" : null,
      finished_at: terminal ? "2026-09-26T00:02:00Z" : null,
    })),
    budget_consumed: running ? 2 : terminal ? 4 : 0,
    ...overrides,
  });
}

interface Options { mode?: "local" | "public"; executionEnabled?: boolean; jobs?: EvaluationJob[]; reports?: string[]; realTrends?: boolean }
export interface EvaluationFixture {
  jobs: Map<string, EvaluationJob>;
  calls: Array<{ method: string; path: string; authorization: string | null; lastEventId: string | null; ifMatch: string | null }>;
  createCount: () => number;
  cancelCount: () => number;
  emitState: (id: string, state: EvaluationJobState) => void;
  forceConflictOnce: () => void;
}

async function json(route: Route, status: number, body: unknown, headers: Record<string, string> = {}) {
  await route.fulfill({ status, headers: { ...CORS, "content-type": "application/json", ...headers }, body: JSON.stringify(body) });
}

function event(job: EvaluationJob, sequence: number): EvaluationJobEvent {
  return { event_id: `${job.id}-event-${sequence}`, job_id: job.id, sequence, event_type: sequence === 1 ? "created" : "state_changed", state: job.state, reason_code: null, progress: job.progress, occurred_at: job.updated_at };
}

export async function installEvaluationFixture(page: Page, options: Options = {}): Promise<EvaluationFixture> {
  await installApiFixtures(page);
  const mode = options.mode ?? "local";
  const executionEnabled = options.executionEnabled ?? true;
  const reportIds = options.reports ?? ["baseline-native", "candidate-native"];
  const jobs = new Map((options.jobs ?? []).map((job) => [job.id, job]));
  const events = new Map<string, EvaluationJobEvent[]>();
  for (const job of jobs.values()) events.set(job.id, [event(job, 1)]);
  const calls: EvaluationFixture["calls"] = [];
  let creates = 0; let cancels = 0; let conflict = false;

  const privateAccess = async (route: Route) => {
    if (mode !== "local") { await json(route, 404, { detail: "Local workspace capability is unavailable" }); return false; }
    if (route.request().headers().authorization !== `Bearer ${EVALUATION_FIXTURE_TOKEN}`) { await json(route, 401, { detail: "Local workspace authentication required" }); return false; }
    return true;
  };

  await page.route(`${API_ORIGIN}/system/configuration-status`, async (route) => {
    if (route.request().method() === "OPTIONS") { await route.fulfill({ status: 204, headers: CORS }); return; }
    if (!await privateAccess(route)) return;
    await json(route, 200, { deployment_mode: "local", capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: executionEnabled } });
  });

  await page.route(`${API_ORIGIN}/evaluation/**`, async (route) => {
    const request = route.request(); const url = new URL(request.url()); const path = decodeURIComponent(url.pathname); const method = request.method();
    if (method === "OPTIONS") { await route.fulfill({ status: 204, headers: CORS }); return; }
    calls.push({ method, path, authorization: request.headers().authorization ?? null, lastEventId: request.headers()["last-event-id"] ?? null, ifMatch: request.headers()["if-match"] ?? null });
    if (path === "/evaluation/metrics" && method === "GET") {
      await json(route, 200, { protocol: "native-evaluation", protocol_version: 1, capabilities: { provider_free: true, computes_judge_scores: false, requires_bound_judge_scores: true }, items: nativeDefinitions(), total: 6 }); return;
    }
    if (path === "/evaluation/runs" && method === "GET") {
      await json(route, 200, { items: reportIds.map((id, index) => publishedSummary(id, index ? 0.75 : 0.25)), total: reportIds.length, page: 1, page_size: 20 }); return;
    }
    const resultMatch = path.match(/^\/evaluation\/runs\/([^/]+)\/results$/);
    if (resultMatch && method === "GET") { await json(route, 200, evaluationResults(resultMatch[1], Number(url.searchParams.get("page") ?? 1))); return; }
    const reportMatch = path.match(/^\/evaluation\/runs\/([^/]+)$/);
    if (reportMatch && method === "GET") { await json(route, 200, publishedDetail(reportMatch[1], reportMatch[1].startsWith("candidate") ? 0.75 : 0.25)); return; }
    if (path === "/evaluation/compare" && method === "POST") {
      const body = request.postDataJSON() as { baseline_run_id: string; candidate_run_id: string };
      const baseline = publishedSummary(body.baseline_run_id, .25); const candidate = publishedSummary(body.candidate_run_id, .75);
      const comparison: NativeComparison = {
        baseline_run_id: body.baseline_run_id, candidate_run_id: body.candidate_run_id,
        baseline_digest: baseline.report_digest, candidate_digest: candidate.report_digest,
        baseline_status: "complete", candidate_status: "incomplete", baseline_binding: baseline.binding,
        candidate_binding: { ...candidate.binding, context_binding: `different-${syntheticHash}` }, same_case_universe: false,
        eligible_for_complete_comparison: false, eligibility_reasons: ["context_binding_mismatch", "computed_case_coverage_mismatch"],
        metrics: nativeMetricIds.map((metric_id, index) => ({
          metric_id, metric_version: 1, direction: "higher_is_better", baseline: aggregate(.25, index), candidate: aggregate(.75, index),
          same_computed_case_coverage: index !== 0, status: index === 0 ? "incompatible" : index === 2 ? "unavailable" : index === 4 ? "not_applicable" : "comparable",
          candidate_minus_baseline: index === 0 || index === 2 || index === 4 ? null : .5, reason_code: index === 0 ? "context_binding_mismatch" : null,
        })), cases: [], total_cases: 5, page: 1, page_size: 50,
      };
      await json(route, 200, comparison); return;
    }
    if (path === "/evaluation/metrics/trends" && method === "GET") {
      const real = options.realTrends ?? false;
      const trends: NativeTrends = { metric_id: "native.faithfulness", total_points: real ? 2 : 0, page: 1, page_size: 50, groups: real ? [{ binding_group: "real-fixture", metric_id: "native.faithfulness", metric_version: 1, points: reportIds.map((run_id, index) => ({ run_id, report_digest: `${run_id}-${syntheticHash}`, published_at: `2026-09-2${index + 1}T00:00:00Z`, report_status: "complete", aggregate: aggregate(index ? .75 : .25, 0), generator_model_id: "synthetic-generator", generation_binding: syntheticHash, retrieval_binding: syntheticHash, judge_binding: syntheticHash })) }] : [] };
      await json(route, 200, trends); return;
    }
    if (path === "/evaluation/failures" && method === "GET") {
      const categories = ["fallback_expectation_mismatch", "invalid_citation_index", "missing_required_keyword", "unavailable_prerequisite"] as const;
      const failures: NativeFailures = { run_id: url.searchParams.get("run_id") ?? reportIds[0], report_digest: syntheticHash, report_status: "complete", category_counts: categories.map((category_id) => ({ category_id, count: 1 })), items: categories.map((category_id, index) => ({ category_id, case_id: `safe-failure-${index + 1}`, context_sha256: syntheticHash, metric_id: nativeMetricIds[index + 2 > 5 ? 5 : index + 2], metric_version: 1, metric_status: category_id === "unavailable_prerequisite" ? "unavailable" : "computed", value: category_id === "unavailable_prerequisite" ? null : index === 0 ? false : 0, reason_code: category_id })), total: 4, page: 1, page_size: 50 };
      await json(route, 200, failures); return;
    }
    if (!path.startsWith("/evaluation/jobs")) { await json(route, 404, { detail: "Not found" }); return; }
    if (!await privateAccess(route)) return;
    if (path === "/evaluation/jobs" && method === "GET") { const list = [...jobs.values()].sort((a, b) => b.created_at.localeCompare(a.created_at)); await json(route, 200, { items: list, total: list.length, page: 1, page_size: 25 }); return; }
    if (path === "/evaluation/jobs" && method === "POST") {
      creates += 1; const created = populatedJob(`job-canonical-${creates}`); jobs.set(created.id, created); events.set(created.id, [event(created, 1)]); await json(route, 201, created, { ETag: '"1"' }); return;
    }
    const jobMatch = path.match(/^\/evaluation\/jobs\/([^/]+)(?:\/(results|cancel|events))?$/);
    if (!jobMatch) { await json(route, 404, { detail: "Job not found" }); return; }
    const id = jobMatch[1]; const action = jobMatch[2] ?? "detail"; const job = jobs.get(id);
    if (!job) { await json(route, 404, { detail: "Job not found" }); return; }
    if (action === "detail" && method === "GET") { await json(route, 200, job, { ETag: `"${job.revision}"` }); return; }
    if (action === "results" && method === "GET") {
      const rawPrivate = { job_id: id, report_status: job.state === "succeeded" ? "complete" : null, report_digest: job.report_digest, metric_definitions: nativeDefinitions(), aggregates: [], items: [{ case_id: "safe-private-case", question: "HIDDEN_QUESTION_UI011", answer: "HIDDEN_ANSWER_UI011", ground_truth: "HIDDEN_GROUND_TRUTH_UI011", evidence: ["HIDDEN_EVIDENCE_UI011"], input: { generation_context_sha256: syntheticHash, judge_context_sha256: syntheticHash }, judge_prompt_sha256: syntheticHash, metrics: [{ metric_id: "native.fallback_correctness", metric_version: 1, status: "computed", value: false, reason_code: null }] }], total: 1, page: 1, page_size: 50 };
      await json(route, 200, rawPrivate); return;
    }
    if (action === "events" && method === "GET") {
      const after = Number(request.headers()["last-event-id"] ?? 0); const body = (events.get(id) ?? []).filter((item) => item.sequence > after).map((item) => `id: ${item.sequence}\ndata: ${JSON.stringify(item)}\n\n`).join("");
      await route.fulfill({ status: 200, headers: { ...CORS, "content-type": "text/event-stream" }, body }); return;
    }
    if (action === "cancel" && method === "POST") {
      cancels += 1;
      if (conflict) { conflict = false; await json(route, 409, { detail: "Revision conflict" }); return; }
      const next = { ...job, state: "cancelling" as const, revision: job.revision + 1, cancellation_requested_at: "2026-09-26T00:03:00Z", updated_at: "2026-09-26T00:03:00Z" };
      jobs.set(id, next); await json(route, 200, next, { ETag: `"${next.revision}"` }); return;
    }
    await json(route, 405, { detail: "Method not allowed" });
  });

  return {
    jobs, calls, createCount: () => creates, cancelCount: () => cancels,
    forceConflictOnce: () => { conflict = true; },
    emitState: (id, state) => {
      const current = jobs.get(id); if (!current) throw new Error(`Unknown job ${id}`);
      const next = populatedJob(id, state, { revision: current.revision + 1, updated_at: "2026-09-26T00:04:00Z" });
      jobs.set(id, next); const history = events.get(id) ?? []; history.push(event(next, history.length + 1)); events.set(id, history);
    },
  };
}
