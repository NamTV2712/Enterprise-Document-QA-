import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { EvaluationPanel } from "./EvaluationPanel";
import { LocaleProvider } from "../lib/i18n";
import { getEvaluationRun, getEvaluationRuns } from "../lib/api";
import type { EvaluationRun } from "../types";

vi.mock("../lib/api", () => ({
  getEvaluationRuns: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
  getEvaluationRun: vi.fn(),
}));

const getEvaluationRunsMock = vi.mocked(getEvaluationRuns);
const getEvaluationRunMock = vi.mocked(getEvaluationRun);

function makeRun(runId: string, title: string): EvaluationRun {
  return {
    run_id: runId,
    title,
    status: "official",
    created_at: "2026-09-14T00:00:00.000Z",
    provenance: { binding: "fixture-v1" },
    aggregate: { overall: 0.9 },
    cases: [],
    notes: [],
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("EvaluationPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    getEvaluationRunsMock.mockReset();
    getEvaluationRunMock.mockReset();
    getEvaluationRunsMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
  });

  test("shows an honest empty state when no public report exists", async () => {
    render(<LocaleProvider><EvaluationPanel /></LocaleProvider>);
    await waitFor(() => expect(screen.getByText("No published reports yet")).toBeInTheDocument());
    expect(screen.getByText(/No substitute metrics are shown/i)).toBeInTheDocument();
    expect(screen.queryByText(/Recorded demo/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Export evaluation JSON" })).not.toBeInTheDocument();
  });

  test("shows a recoverable backend error without an empty master-detail grid", async () => {
    getEvaluationRunsMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    render(<LocaleProvider><EvaluationPanel /></LocaleProvider>);

    expect(await screen.findByRole("alert")).toHaveTextContent("The backend could not be reached. Check the connection and try again.");
    expect(screen.queryByLabelText("Evaluation run list")).not.toBeInTheDocument();
    expect(screen.queryByText("Select a run to inspect cases, scores, and evidence.")).not.toBeInTheDocument();
  });

  test("distinguishes an empty status filter from a globally empty report catalog", async () => {
    const published = makeRun("run-official", "Official run");
    getEvaluationRunsMock.mockImplementation(({ status } = {}) => Promise.resolve(status
      ? { items: [], total: 0, page: 1, page_size: 20 }
      : { items: [{ ...published, case_count: 0 }], total: 1, page: 1, page_size: 20 }));
    getEvaluationRunMock.mockResolvedValue(published);

    render(<LocaleProvider><EvaluationPanel /></LocaleProvider>);
    await screen.findByRole("button", { name: "Export evaluation JSON" });

    fireEvent.click(screen.getByRole("button", { name: "Status" }));
    fireEvent.click(await screen.findByRole("option", { name: "Candidate" }));
    await waitFor(() => expect(screen.getByText("No reports match this filter")).toBeInTheDocument());
    expect(screen.queryByText("No published reports yet")).not.toBeInTheDocument();
  });

  test("keeps a selected-run response valid when a comparison request starts in the same update", async () => {
    const first = makeRun("run-a", "Run A");
    const selected = makeRun("run-b", "Run B");
    const comparison = makeRun("run-c", "Run C");
    const selectedRequest = deferred<EvaluationRun>();
    const comparisonRequest = deferred<EvaluationRun>();
    const runs = [first, selected, comparison];
    getEvaluationRunsMock.mockResolvedValue({
      items: runs.map(({ cases, notes, ...run }) => ({ ...run, case_count: cases.length })),
      total: runs.length,
      page: 1,
      page_size: 20,
    });
    getEvaluationRunMock.mockImplementation((runId) => {
      if (runId === selected.run_id) return selectedRequest.promise;
      if (runId === comparison.run_id) return comparisonRequest.promise;
      return Promise.resolve(first);
    });

    render(<LocaleProvider><EvaluationPanel /></LocaleProvider>);
    await screen.findByRole("button", { name: "Export evaluation JSON" });

    fireEvent.click(screen.getByText("Paired experiment comparison"));
    fireEvent.click(screen.getByRole("button", { name: "Comparison run" }));
    const comparisonOption = await screen.findByRole("option", { name: "Run C" });

    act(() => {
      comparisonOption.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      screen.getByRole("row", { name: /Run B/ }).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    await waitFor(() => expect(getEvaluationRunMock.mock.calls.map(([runId]) => runId)).toContain("run-c"));
    await act(async () => { selectedRequest.resolve(selected); });

    expect(screen.getByRole("heading", { level: 3, name: "Run B" })).toBeInTheDocument();
  });
});
