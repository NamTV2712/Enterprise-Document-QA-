import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { EvaluationPanel } from "./EvaluationPanel";
import { LocaleProvider } from "../lib/i18n";

vi.mock("../lib/api", () => ({
  getEvaluationRuns: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
  getEvaluationRun: vi.fn(),
}));

describe("EvaluationPanel", () => {
  test("keeps recorded demo visibly provider-free", async () => {
    render(<LocaleProvider><EvaluationPanel /></LocaleProvider>);
    await waitFor(() => expect(screen.getByText("No published reports yet")).toBeInTheDocument());

    fireEvent.change(screen.getByRole("combobox", { name: "Evaluation mode" }), { target: { value: "recorded" } });

    expect((await screen.findAllByText("Recorded evaluation contract demo (provider-free)")).length).toBe(2);
    expect(screen.getByText(/Recorded mode only; not an official benchmark/i)).toBeInTheDocument();
    expect(screen.getByText("Recorded demo answer; not a live provider result.")).toBeInTheDocument();
  });
});
