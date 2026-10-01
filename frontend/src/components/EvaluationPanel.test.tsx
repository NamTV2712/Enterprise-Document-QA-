import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { EvaluationPanel } from "./EvaluationPanel";
import { LocaleProvider } from "../lib/i18n";
import { LocalWorkspaceSessionProvider } from "../lib/localWorkspaceSession";
import { evaluationApi } from "../lib/evaluationApi";
import { pipelineApi } from "../lib/pipelineApi";
import { evaluationJob, jobResults, nativeDefinitions, nativeMetricIds, publishedDetail, publishedSummary, syntheticHash } from "../test/evaluationFixtures";
import type { NativeComparison, NativeFailures, NativeTrends } from "../lib/evaluationTypes";

const metrics = { protocol: "native-evaluation" as const, protocol_version: 1 as const, capabilities: { provider_free: true as const, computes_judge_scores: false as const, requires_bound_judge_scores: true as const }, items: nativeDefinitions(), total: 6 };
function results(id: string) { return { run_id: id, report_digest: syntheticHash, report_status: "complete" as const, metric_definitions: nativeDefinitions(), aggregates: publishedSummary(id).aggregates, items: [{ case_id: "safe-case-id", context_sha256: "safe-context-hash", metrics: [{ metric_id: nativeMetricIds[0], metric_version: 1, status: "computed" as const, value: 0, reason_code: null }, { metric_id: nativeMetricIds[5], metric_version: 1, status: "computed" as const, value: false, reason_code: null }] }], total: 1, page: 1, page_size: 50 }; }
function comparison(): NativeComparison {
  const baseline = publishedSummary("base", 0.4).aggregates;
  const candidate = publishedSummary("candidate", 0.4).aggregates;
  const deltas: Array<number | null> = [0, .1, -.2, null, null, 0];
  return { baseline_run_id: "base", candidate_run_id: "candidate", baseline_digest: "base-digest", candidate_digest: "candidate-digest", baseline_status: "complete", candidate_status: "incomplete", baseline_binding: publishedSummary().binding, candidate_binding: publishedSummary().binding, same_case_universe: false, eligible_for_complete_comparison: false, eligibility_reasons: ["dataset_revision_mismatch", "computed_case_coverage_mismatch"], metrics: nativeMetricIds.map((metric_id, index) => ({ metric_id, metric_version: 1, direction: "higher_is_better", baseline: baseline[index], candidate: candidate[index], same_computed_case_coverage: index !== 2, status: index === 3 ? "incompatible" : index === 4 ? "not_applicable" : index === 2 ? "unavailable" : "comparable", candidate_minus_baseline: deltas[index], reason_code: index === 3 ? "context_binding_mismatch" : null })), cases: [], total_cases: 5, page: 1, page_size: 50 };
}
function trends(real = false): NativeTrends {
  const aggregate = publishedSummary("point", .5).aggregates[0];
  return { metric_id: nativeMetricIds[0], total_points: real ? 3 : 0, page: 1, page_size: 50, groups: real ? [
    { binding_group: `sha256:${"a".repeat(64)}`, metric_id: nativeMetricIds[0], metric_version: 1, points: [{ run_id: "run-1", report_digest: "d1", published_at: "2026-09-01T00:00:00Z", report_status: "complete", aggregate: { ...aggregate, value: .25 }, generator_model_id: "model-a", generation_binding: "g-a", retrieval_binding: "r-a", judge_binding: "j-a" }, { run_id: "run-3", report_digest: "d3", published_at: "2026-09-03T00:00:00Z", report_status: "complete", aggregate: { ...aggregate, value: .75 }, generator_model_id: "model-a", generation_binding: "g-a", retrieval_binding: "r-a", judge_binding: "j-a" }] },
    { binding_group: `sha256:${"b".repeat(64)}`, metric_id: nativeMetricIds[0], metric_version: 1, points: [{ run_id: "run-2", report_digest: "d2", published_at: "2026-09-02T00:00:00Z", report_status: "incomplete", aggregate: { ...aggregate, status: "unavailable", value: null, denominator: 0, unavailable_count: 5 }, generator_model_id: "model-b", generation_binding: "g-b", retrieval_binding: "r-b", judge_binding: null }] },
  ] : [] };
}
function failures(): NativeFailures {
  const categories = ["fallback_expectation_mismatch", "invalid_citation_index", "missing_required_keyword", "unavailable_prerequisite"] as const;
  return { run_id: "base", report_digest: "digest", report_status: "complete", category_counts: categories.map((category_id) => ({ category_id, count: 1 })), items: categories.map((category_id, index) => ({ category_id, case_id: `safe-case-${index}`, context_sha256: `safe-hash-${index}`, metric_id: nativeMetricIds[index], metric_version: 1, metric_status: index === 3 ? "unavailable" : "computed", value: index === 3 ? null : index === 0 ? false : 0, reason_code: category_id })), total: 4, page: 1, page_size: 50 };
}
function renderPanel(props: React.ComponentProps<typeof EvaluationPanel> = {}) { return render(<LocaleProvider><LocalWorkspaceSessionProvider><EvaluationPanel {...props} /></LocalWorkspaceSessionProvider></LocaleProvider>); }
beforeEach(() => {
  vi.spyOn(evaluationApi, "getMetrics").mockResolvedValue(metrics);
  vi.spyOn(evaluationApi, "listReports").mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
  vi.spyOn(evaluationApi, "getReport").mockImplementation(async (id) => publishedDetail(id));
  vi.spyOn(evaluationApi, "getResults").mockImplementation(async (id) => results(id));
  vi.spyOn(evaluationApi, "compare").mockResolvedValue(comparison());
  vi.spyOn(evaluationApi, "getTrends").mockResolvedValue(trends());
  vi.spyOn(evaluationApi, "getFailures").mockResolvedValue(failures());
  vi.spyOn(evaluationApi, "listJobs").mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 });
  vi.spyOn(evaluationApi, "getJob").mockResolvedValue(evaluationJob("job-a", { state: "interrupted" }));
  vi.spyOn(evaluationApi, "getJobResults").mockResolvedValue(jobResults("job-a"));
  vi.spyOn(evaluationApi, "getJobEvents").mockResolvedValue([]);
  vi.spyOn(evaluationApi, "createJob").mockResolvedValue(evaluationJob("server-canonical-id"));
  vi.spyOn(evaluationApi, "cancelJob").mockResolvedValue(evaluationJob("job-a", { state: "cancelling", revision: 2 }));
  vi.spyOn(pipelineApi, "verifyLocalWorkspaceToken").mockResolvedValue({ deployment_mode: "local", capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: true } });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Evaluation workspace metric and publication truth", () => {
  test("section tabs expose selection and arrow-key navigation", async () => {
    renderPanel(); await screen.findByText("No published reports yet");
    const reports = screen.getByRole("tab", { name: "Reports" });
    reports.focus(); fireEvent.keyDown(reports, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Compare" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Compare" })).toBeInTheDocument();
  });
  test("renders exactly the six backend definitions without screenshot-only metrics", async () => {
    renderPanel(); await screen.findByText("No published reports yet");
    expect(screen.getAllByRole("heading", { level: 2 }).filter((node) => nativeDefinitions().some((definition) => definition.label === node.textContent))).toHaveLength(6);
    expect(screen.getByText("native.citation_index_validity")).toBeInTheDocument();
    expect(screen.getByText("native.keyword_recall_proxy")).toBeInTheDocument();
    expect(screen.queryByText(/latency \(p95\)|benchmark score|groundedness/i)).not.toBeInTheDocument();
    expect(screen.getByText(/No substitute data, demo trends or inferred scores/)).toBeInTheDocument();
  });
  test("selected native report preserves zero/unavailable/not-applicable denominators and safe cases", async () => {
    vi.mocked(evaluationApi.listReports).mockResolvedValue({ items: [publishedSummary("native-zero", 0)], total: 1, page: 1, page_size: 20 });
    renderPanel({ selectedId: "native-zero", selectedSource: "report" });
    await screen.findByRole("heading", { name: "native-zero", level: 2 });
    expect(screen.getAllByText("0.000").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not applicable").length).toBeGreaterThan(0);
    expect(screen.getByText("safe-case-id")).toBeInTheDocument(); expect(screen.getByText("False")).toBeInTheDocument();
    expect(screen.getAllByText("3 / 5").length).toBeGreaterThan(0);
    expect(document.body.textContent).not.toMatch(/HIDDEN_QUESTION|HIDDEN_ANSWER|HIDDEN_EVIDENCE|ground truth text/i);
  });
  test("report selection hands canonical ID to route owner", async () => {
    const onSelectReport = vi.fn(); vi.mocked(evaluationApi.listReports).mockResolvedValue({ items: [publishedSummary("canonical run")], total: 1, page: 1, page_size: 20 });
    renderPanel({ onSelectReport });
    fireEvent.click(await screen.findByRole("button", { name: /canonical run/ })); expect(onSelectReport).toHaveBeenCalledWith("canonical run");
  });
  test("legacy reports remain metadata-only and do not expose stored text", async () => {
    const legacy = { run_id: "legacy-a", title: "Legacy report", status: "historical" as const, created_at: "2026-09-01T00:00:00Z", provenance: { binding: "safe" }, aggregate: { faithfulness: 0 }, case_count: 1 };
    vi.mocked(evaluationApi.listReports).mockResolvedValue({ items: [legacy], total: 1, page: 1, page_size: 20 });
    vi.mocked(evaluationApi.getReport).mockResolvedValue({ ...legacy, cases: [{ case_id: "safe-id", status: "OK", scores: { faithfulness: 0 } }] });
    renderPanel({ selectedId: "legacy-a" });
    expect(await screen.findByText(/legacy compatibility report is shown as safe metadata only/i)).toBeInTheDocument();
    expect(screen.queryByText("safe-id")).not.toBeInTheDocument(); expect(evaluationApi.getResults).not.toHaveBeenCalled();
  });
});
describe("backend-owned analytics", () => {
  beforeEach(() => { vi.mocked(evaluationApi.listReports).mockResolvedValue({ items: [publishedSummary("base", .4), publishedSummary("candidate", .5)], total: 2, page: 1, page_size: 20 }); });
  test("compare shows zero, positive, negative and null deltas plus compatibility and counts", async () => {
    renderPanel(); await screen.findByRole("button", { name: /base/ }); fireEvent.click(screen.getByRole("tab", { name: "Compare" }));
    fireEvent.click(screen.getByRole("button", { name: /^Compare$/ }));
    expect(await screen.findByText("Not fully compatible")).toBeInTheDocument();
    for (const value of ["0.000", "+0.100", "-0.200", "Not reported", "dataset_revision_mismatch", "computed_case_coverage_mismatch", "context_binding_mismatch"]) expect(screen.getAllByText(value).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/candidate − baseline/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/3 \/ 5/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/^winner$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/confidence interval/i)).not.toBeInTheDocument();
  });
  test("empty trends are truthful and contain no SVG observations", async () => {
    renderPanel(); await screen.findByRole("button", { name: /base/ }); fireEvent.click(screen.getByRole("tab", { name: "Trends" }));
    expect(await screen.findByText("No published native trend history")).toBeInTheDocument();
    expect(screen.getByText(/No demo or interpolated observations/)).toBeInTheDocument();
    expect(document.querySelector(".evaluation-trend-groups")).toBeNull();
  });
  test("real trend points remain in separate groups, fixed [0,1], without interpolation paths", async () => {
    vi.mocked(evaluationApi.getTrends).mockResolvedValue(trends(true));
    renderPanel(); await screen.findByRole("button", { name: /base/ }); fireEvent.click(screen.getByRole("tab", { name: "Trends" }));
    await screen.findByText(/3 backend observations/);
    expect(document.querySelectorAll(".evaluation-trend-groups article")).toHaveLength(2);
    expect(document.querySelectorAll(".evaluation-trend-groups circle")).toHaveLength(2);
    expect(document.querySelectorAll(".evaluation-trend-groups polyline, .evaluation-trend-groups path")).toHaveLength(0);
    expect(screen.getByText(/Missing points are not connected, smoothed, or forecast/)).toBeInTheDocument();
  });
  test("failures use exactly four categories, preserve false/zero/unavailable and expose no case text", async () => {
    renderPanel(); await screen.findByRole("button", { name: /base/ }); fireEvent.click(screen.getByRole("tab", { name: "Failures" }));
    expect(await screen.findByText(/4 backend-classified findings/)).toBeInTheDocument();
    for (const label of ["Fallback expectation mismatch", "Invalid citation indices", "Missing required keywords", "Unavailable prerequisites"]) expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    expect(screen.getByText("False")).toBeInTheDocument(); expect(screen.getAllByText("0.000").length).toBeGreaterThan(0); expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.getByText(/not automatically a model failure/i)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/hallucination|bad answer|poor quality|HIDDEN_/i);
  });
});
describe("private job UI", () => {
  test("public workspace remains useful while private execution is disconnected", async () => {
    renderPanel(); await screen.findByText("No published reports yet"); fireEvent.click(screen.getByRole("tab", { name: "Private jobs" }));
    expect(screen.getByRole("heading", { name: "Connect the local workspace" })).toBeInTheDocument();
    expect(screen.getByText(/token stays in memory and is sent only to private routes/i)).toBeInTheDocument();
    expect(evaluationApi.listJobs).not.toHaveBeenCalled();
  });
  test("reuses shared connection, creates one canonical queued job, and keeps token out of DOM", async () => {
    const onSelectJob = vi.fn(); renderPanel({ onSelectJob }); await screen.findByText("No published reports yet");
    fireEvent.click(screen.getByRole("tab", { name: "Private jobs" }));
    fireEvent.change(screen.getByLabelText("Local workspace token"), { target: { value: "secret-synthetic-token" } }); fireEvent.click(screen.getByRole("button", { name: "Connect" }));
    await screen.findByText("No evaluation jobs yet"); expect(screen.getByText("Connected · execution enabled")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("secret-synthetic-token");
    fireEvent.click(screen.getByRole("button", { name: "New evaluation" }));
    fireEvent.change(screen.getByLabelText("Registered artifact ID"), { target: { value: "synthetic-phase1" } }); fireEvent.change(screen.getByLabelText("Provider attempt slot budget"), { target: { value: "6" } });
    fireEvent.click(screen.getByRole("button", { name: "Freeze and queue" }));
    await waitFor(() => expect(evaluationApi.createJob).toHaveBeenCalledTimes(1));
    expect(onSelectJob).toHaveBeenCalledWith("server-canonical-id");
    const [, body] = vi.mocked(evaluationApi.createJob).mock.calls[0]; expect(body.budget).toBe(6); expect(body.metrics).toEqual(nativeMetricIds);
    expect(document.body.textContent).not.toMatch(/USD|credits|tokens/);
  });
  test("interrupted deep-link shows exact steps, frozen budget and no unsupported action", async () => {
    vi.mocked(evaluationApi.listJobs).mockResolvedValue({ items: [evaluationJob("job-a", { state: "interrupted" })], total: 1, page: 1, page_size: 25 });
    renderPanel({ selectedId: "job-a", selectedSource: "job" });
    fireEvent.change(await screen.findByLabelText("Local workspace token"), { target: { value: "synthetic-token" } }); fireEvent.click(screen.getByRole("button", { name: "Connect" }));
    expect(await screen.findByText("execute_cases")).toBeInTheDocument(); expect(screen.getByText("aggregate_report")).toBeInTheDocument();
    expect(screen.getByText("0 / 6 provider_attempt_slot")).toBeInTheDocument(); expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.getByText(/Interrupted is terminal/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /resume|retry|restart/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request cancellation" })).toBeDisabled();
  });
  test("budget exhaustion is named separately while durable results remain visible", async () => {
    vi.mocked(evaluationApi.getJob).mockResolvedValue(evaluationJob("job-a", { state: "failed", budget_consumed: 6, failure: { code: "budget_exhausted", message: "Provider attempt slot budget exhausted" } }));
    vi.mocked(evaluationApi.getJobResults).mockResolvedValue({ ...jobResults("job-a"), total: 1, items: [{ case_id: "completed-safe-case", metrics: [], generation_context_sha256: syntheticHash, judge_context_sha256: syntheticHash, judge_prompt_sha256: syntheticHash }] });
    renderPanel({ selectedId: "job-a", selectedSource: "job" }); fireEvent.change(await screen.findByLabelText("Local workspace token"), { target: { value: "synthetic-token" } }); fireEvent.click(screen.getByRole("button", { name: "Connect" }));
    expect(await screen.findByText("budget_exhausted")).toBeInTheDocument(); expect(screen.getByText(/not a zero score or generic model failure/)).toBeInTheDocument(); expect(screen.getByText("completed-safe-case")).toBeInTheDocument();
  });
});
