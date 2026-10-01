import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { RESEARCH_TEMPLATES } from "../lib/researchTemplates";
import { TemplateQuestionDialog } from "./TemplateQuestionDialog";

afterEach(() => cleanup());

describe("TemplateQuestionDialog", () => {
  const template = RESEARCH_TEMPLATES.find((candidate) => candidate.id === "revenue-fact")!;

  test("does not apply an incomplete template and reports required fields", () => {
    const onApply = vi.fn();
    render(<TemplateQuestionDialog open template={template} tickers={["AAPL"]} onClose={vi.fn()} onApply={onApply} />);

    fireEvent.click(screen.getByRole("button", { name: "Use in question" }));

    expect(onApply).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Company" })).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: "Company" })).toHaveAttribute("aria-describedby", "template-error-company");
    expect(screen.getAllByRole("alert").map((node) => node.textContent)).toEqual(expect.arrayContaining([
      "Company is required.",
      "Fiscal year is required.",
    ]));
  });

  test("applies a validated question without sending it", () => {
    const onApply = vi.fn();
    render(<TemplateQuestionDialog open template={template} tickers={["AAPL"]} onClose={vi.fn()} onApply={onApply} />);

    fireEvent.click(screen.getByRole("button", { name: "Company" }));
    fireEvent.click(screen.getByRole("option", { name: "Apple Inc. (AAPL)" }));
    fireEvent.change(screen.getByLabelText("Fiscal year"), { target: { value: "2024" } });
    fireEvent.click(screen.getByRole("button", { name: "Use in question" }));

    expect(onApply).toHaveBeenCalledWith({
      templateId: "revenue-fact",
      locale: "en",
      question: "What total revenue did AAPL report in 2024?",
      scope: { ticker: "AAPL", section: "financial_table", topK: 5, enableComparative: false },
      values: { company: "AAPL", year: "2024" },
    });
  });

  test("cancels through the shared modal contract", () => {
    const onClose = vi.fn();
    render(<TemplateQuestionDialog open template={template} tickers={["AAPL"]} onClose={onClose} onApply={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
