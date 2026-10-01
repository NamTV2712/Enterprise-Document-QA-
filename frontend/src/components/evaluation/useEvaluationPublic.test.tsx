import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { evaluationApi, EvaluationApiError } from "../../lib/evaluationApi";
import { nativeDefinitions, publishedDetail, publishedSummary } from "../../test/evaluationFixtures";
import type { NativeComparison, NativeFailures, NativeTrends, PublishedDetail } from "../../lib/evaluationTypes";
import { useEvaluationCatalog, useEvaluationCompare, useEvaluationFailures, useEvaluationTrends } from "./useEvaluationPublic";

function deferred<T>() { let resolve!: (value: T) => void; let reject!: (error: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
const metrics = { protocol: "native-evaluation" as const, protocol_version: 1 as const, capabilities: { provider_free: true as const, computes_judge_scores: false as const, requires_bound_judge_scores: true as const }, items: nativeDefinitions(), total: 6 };
const comparison = (baseline: string, candidate: string): NativeComparison => ({ baseline_run_id: baseline, candidate_run_id: candidate, baseline_digest: "base", candidate_digest: "candidate", baseline_status: "complete", candidate_status: "complete", baseline_binding: publishedSummary().binding, candidate_binding: publishedSummary().binding, same_case_universe: true, eligible_for_complete_comparison: true, eligibility_reasons: [], metrics: [], cases: [], total_cases: 0, page: 1, page_size: 50 });
const trend = (id: string): NativeTrends => ({ metric_id: "native.faithfulness", groups: [], total_points: id === "old" ? 9 : 0, page: 1, page_size: 50 });
const failure = (id: string): NativeFailures => ({ run_id: id, report_digest: "digest", report_status: "complete", category_counts: [], items: [], total: 0, page: 1, page_size: 50 });
function Harness() {
  const [run, setRun] = useState<string | null>("a");
  const catalog = useEvaluationCatalog(run); const compare = useEvaluationCompare(); const trends = useEvaluationTrends(); const failures = useEvaluationFailures();
  return <><button onClick={() => setRun("a")}>A</button><button onClick={() => setRun("b")}>B</button><button onClick={() => compare.compare("base-old", "candidate-old")}>Compare old</button><button onClick={() => compare.compare("base-new", "candidate-new")}>Compare new</button><button onClick={() => trends.load("native.faithfulness")}>Trend old</button><button onClick={() => trends.load("native.answer_relevancy")}>Trend new</button><button onClick={() => failures.load("old")}>Failure old</button><button onClick={() => failures.load("new")}>Failure new</button><output data-testid="value">{JSON.stringify({ detail: catalog.detail, results: catalog.results, detailError: catalog.detailErrorStatus, compare: compare.comparison, compareError: compare.errorStatus, trends: trends.trends, trendError: trends.errorStatus, failures: failures.failures, failureError: failures.errorStatus })}</output></>;
}
const value = () => JSON.parse(screen.getByTestId("value").textContent ?? "{}");
beforeEach(() => {
  vi.spyOn(evaluationApi, "getMetrics").mockResolvedValue(metrics);
  vi.spyOn(evaluationApi, "listReports").mockResolvedValue({ items: [publishedSummary("a"), publishedSummary("b")], total: 2, page: 1, page_size: 20 });
  vi.spyOn(evaluationApi, "getReport").mockImplementation(async (id) => publishedDetail(id));
  vi.spyOn(evaluationApi, "getResults").mockImplementation(async (id) => ({ run_id: id, report_digest: "digest", report_status: "complete", metric_definitions: nativeDefinitions(), aggregates: [], items: [], total: 0, page: 1, page_size: 50 }));
  vi.spyOn(evaluationApi, "compare").mockImplementation(async ({ baseline_run_id, candidate_run_id }) => comparison(baseline_run_id, candidate_run_id));
  vi.spyOn(evaluationApi, "getTrends").mockResolvedValue(trend("new"));
  vi.spyOn(evaluationApi, "getFailures").mockImplementation(async ({ run_id }) => failure(run_id));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("public evaluation request lifetimes", () => {
  test("detail/results stay bound to selected report and abort predecessor", async () => {
    const old = deferred<PublishedDetail>();
    vi.mocked(evaluationApi.getReport).mockImplementation(async (id) => id === "a" ? old.promise : publishedDetail("b"));
    render(<Harness />); await waitFor(() => expect(evaluationApi.getReport).toHaveBeenCalledTimes(1));
    const oldSignal = vi.mocked(evaluationApi.getReport).mock.calls[0][1];
    fireEvent.click(screen.getByText("B")); await waitFor(() => expect(value().detail?.run_id).toBe("b"));
    await act(async () => old.resolve(publishedDetail("a")));
    expect(oldSignal?.aborted).toBe(true); expect(value().detail.run_id).toBe("b"); expect(value().results.run_id).toBe("b");
  });
  test("late selected-report failure cannot overwrite current success", async () => {
    const old = deferred<PublishedDetail>(); vi.mocked(evaluationApi.getReport).mockImplementation(async (id) => id === "a" ? old.promise : publishedDetail("b"));
    render(<Harness />); await waitFor(() => expect(evaluationApi.getReport).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByText("B")); await waitFor(() => expect(value().detail?.run_id).toBe("b"));
    await act(async () => old.reject(new EvaluationApiError(503)));
    expect(value().detail.run_id).toBe("b"); expect(value().detailError).toBeNull();
  });
  test("late results cannot attach to successor detail", async () => {
    const old = deferred<ReturnType<typeof publishedResults>>();
    function publishedResults() { return { run_id: "a", report_digest: "digest", report_status: "complete" as const, metric_definitions: nativeDefinitions(), aggregates: [], items: [], total: 99, page: 1, page_size: 50 }; }
    vi.mocked(evaluationApi.getResults).mockImplementation(async (id) => id === "a" ? old.promise : { ...publishedResults(), run_id: "b", total: 0 });
    render(<Harness />); await waitFor(() => expect(evaluationApi.getResults).toHaveBeenCalledWith("a", { page: 1 }, expect.any(AbortSignal)));
    fireEvent.click(screen.getByText("B")); await waitFor(() => expect(value().results?.run_id).toBe("b"));
    await act(async () => old.resolve(publishedResults()));
    expect(value().results.run_id).toBe("b"); expect(value().results.total).toBe(0);
  });
  test("compare successor ignores stale success and stale error", async () => {
    const old = deferred<NativeComparison>();
    vi.mocked(evaluationApi.compare).mockImplementation(async ({ baseline_run_id, candidate_run_id }) => baseline_run_id === "base-old" ? old.promise : comparison(baseline_run_id, candidate_run_id));
    render(<Harness />); fireEvent.click(screen.getByText("Compare old")); fireEvent.click(screen.getByText("Compare new"));
    await waitFor(() => expect(value().compare?.baseline_run_id).toBe("base-new"));
    await act(async () => old.resolve(comparison("base-old", "candidate-old")));
    expect(value().compare.baseline_run_id).toBe("base-new"); expect(value().compareError).toBeNull();
  });
  test("trend filter successor ignores stale observations", async () => {
    const old = deferred<NativeTrends>(); let call = 0;
    vi.mocked(evaluationApi.getTrends).mockImplementation(async () => ++call === 1 ? old.promise : trend("new"));
    render(<Harness />); fireEvent.click(screen.getByText("Trend old")); fireEvent.click(screen.getByText("Trend new"));
    await waitFor(() => expect(value().trends?.total_points).toBe(0));
    await act(async () => old.resolve(trend("old")));
    expect(value().trends.total_points).toBe(0); expect(value().trendError).toBeNull();
  });
  test("failure selection successor ignores stale categories", async () => {
    const old = deferred<NativeFailures>();
    vi.mocked(evaluationApi.getFailures).mockImplementation(async ({ run_id }) => run_id === "old" ? old.promise : failure(run_id));
    render(<Harness />); fireEvent.click(screen.getByText("Failure old")); fireEvent.click(screen.getByText("Failure new"));
    await waitFor(() => expect(value().failures?.run_id).toBe("new"));
    await act(async () => old.resolve(failure("old")));
    expect(value().failures.run_id).toBe("new"); expect(value().failureError).toBeNull();
  });
});
