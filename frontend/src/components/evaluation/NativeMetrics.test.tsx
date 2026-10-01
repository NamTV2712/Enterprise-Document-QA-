import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { NativeCases, NativeMetrics, metricValue } from "./NativeMetrics";
import { nativeDefinitions, nativeMetricIds } from "../../test/evaluationFixtures";
import type { NativeAggregateMetric } from "../../lib/evaluationTypes";

afterEach(cleanup);
function aggregate(overrides: Partial<NativeAggregateMetric> = {}): NativeAggregateMetric {
  return { metric_id: nativeMetricIds[0], metric_version: 1, status: "computed", value: 0, total_cases: 5, denominator: 2, unavailable_count: 2, not_applicable_count: 1, ...overrides };
}
describe("native metric semantics", () => {
  test("all six canonical definitions show IDs, version, meanings, range, source and direction", () => {
    render(<NativeMetrics definitions={nativeDefinitions()} />);
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(6);
    expect(screen.getAllByText("Definition · v1")).toHaveLength(6);
    for (const id of nativeMetricIds) expect(screen.getByText(id)).toBeInTheDocument();
    expect(screen.getByText(/not claim support\./)).toBeInTheDocument();
    expect(screen.getByText(/not Recall@K or semantic relevance/)).toBeInTheDocument();
    expect(screen.getAllByText("higher_is_better")).toHaveLength(6);
    expect(screen.getAllByText("ratio · [0, 1]")).toHaveLength(5);
    expect(screen.getByText("boolean · [0, 1]")).toBeInTheDocument();
    expect(screen.getAllByText("Not reported")).toHaveLength(6);
  });
  test.each([
    ["computed", 0, "0.000"], ["computed", false, "False"], ["computed", true, "True"],
    ["unavailable", null, "Unavailable"], ["not_applicable", null, "Not applicable"],
  ] as const)("preserves %s value %s", (status, value, expected) => {
    expect(metricValue({ status, value })).toBe(expected);
  });
  test("shows aggregate denominator/total and both excluded populations without synthetic deltas", () => {
    render(<NativeMetrics definitions={nativeDefinitions()} aggregates={[aggregate()]} />);
    const card = screen.getByRole("heading", { name: "Faithfulness" }).closest("article")!;
    expect(within(card).getByText("0.000")).toBeInTheDocument();
    expect(within(card).getByText("2 / 5")).toBeInTheDocument();
    expect(within(card).getByText("Computed / total")).toBeInTheDocument();
    expect(within(card).getByText("Unavailable")).toBeInTheDocument();
    expect(within(card).getByText("Not applicable")).toBeInTheDocument();
    expect(within(card).queryByText(/winner|confidence|improvement|pass rate/i)).not.toBeInTheDocument();
  });
  test("does not use aggregates from another metric version", () => {
    render(<NativeMetrics definitions={nativeDefinitions()} aggregates={[aggregate({ metric_version: 2, value: 0.9 })]} />);
    expect(screen.queryByText("0.900")).not.toBeInTheDocument();
    expect(screen.getAllByText("Not reported")).toHaveLength(6);
  });
  test("Vietnamese state labels preserve explicit false and null distinctions", () => {
    expect(metricValue({ status: "computed", value: false }, "vi")).toBe("Sai (false)");
    expect(metricValue({ status: "unavailable", value: null }, "vi")).toBe("Không khả dụng");
    expect(metricValue({ status: "not_applicable", value: null }, "vi")).toBe("Không áp dụng");
  });
});
describe("safe case results", () => {
  test("renders computed zero/false and null statuses with actual IDs, versions and hashes only", () => {
    render(<NativeCases items={[{ case_id: "synthetic-case", context_sha256: "synthetic-context-hash", metrics: [
      { metric_id: nativeMetricIds[0], metric_version: 1, status: "computed", value: 0, reason_code: null },
      { metric_id: nativeMetricIds[5], metric_version: 1, status: "computed", value: false, reason_code: null },
      { metric_id: nativeMetricIds[1], metric_version: 1, status: "unavailable", value: null, reason_code: "missing_bound_judge_score" },
      { metric_id: nativeMetricIds[4], metric_version: 1, status: "not_applicable", value: null, reason_code: "missing_required_keywords" },
    ] }]} definitions={nativeDefinitions()} total={1} page={1} pageSize={50} onPage={() => {}} />);
    for (const text of ["synthetic-case", "0.000", "False", "Unavailable", "Not applicable", "synthetic-context-hash"]) expect(screen.getByText(text)).toBeInTheDocument();
    expect(screen.getByText("Fallback correctness · v1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
  });
  test("server page bounds support forward/back and retain empty-result truth", () => {
    const onPage = vi.fn();
    const { rerender } = render(<NativeCases items={[]} definitions={[]} total={51} page={1} pageSize={50} onPage={onPage} />);
    expect(screen.getByText("No durable results on this page yet.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" })); expect(onPage).toHaveBeenCalledWith(2);
    rerender(<NativeCases items={[]} definitions={[]} total={51} page={2} pageSize={50} onPage={onPage} />);
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Previous" })); expect(onPage).toHaveBeenLastCalledWith(1);
  });
});
