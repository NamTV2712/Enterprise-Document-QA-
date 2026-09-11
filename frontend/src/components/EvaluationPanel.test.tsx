import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { EvaluationPanel } from "./EvaluationPanel";
import { LocaleProvider } from "../lib/i18n";
import { getEvaluationRuns } from "../lib/api";

vi.mock("../lib/api", () => ({
  getEvaluationRuns: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
  getEvaluationRun: vi.fn(),
}));

const getEvaluationRunsMock = vi.mocked(getEvaluationRuns);

describe("EvaluationPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  beforeEach(() => {
    getEvaluationRunsMock.mockReset();
    getEvaluationRunsMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
  });

  test("keeps recorded demo visibly provider-free", async () => {
    render(<LocaleProvider><EvaluationPanel /></LocaleProvider>);
    await waitFor(() => expect(screen.getByText("No published reports yet")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Mode" }));
    fireEvent.click(screen.getByRole("option", { name: "Recorded demo" }));

    expect((await screen.findAllByText("Recorded evaluation contract demo (provider-free)")).length).toBe(2);
    expect(screen.getByText(/Recorded mode only; not an official benchmark/i)).toBeInTheDocument();
    expect(screen.getByText("Recorded demo answer; not a live provider result.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export evaluation JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export evaluation CSV" })).toBeInTheDocument();
  });

  test("shows a recoverable backend error without an empty master-detail grid", async () => {
    getEvaluationRunsMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    render(<LocaleProvider><EvaluationPanel /></LocaleProvider>);

    expect(await screen.findByRole("alert")).toHaveTextContent("The backend could not be reached. Check the connection and try again.");
    expect(screen.queryByLabelText("Evaluation run list")).not.toBeInTheDocument();
    expect(screen.queryByText("Select a run to inspect cases, scores, and evidence.")).not.toBeInTheDocument();
  });
});
