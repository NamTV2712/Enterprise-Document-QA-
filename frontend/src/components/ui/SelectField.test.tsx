import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { SelectField } from "./SelectField";

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("SelectField", () => {
  test("closing a selection cannot steal focus from the next form field", () => {
    const pendingFrames: FrameRequestCallback[] = [];
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      pendingFrames.push(callback);
      return pendingFrames.length;
    });
    render(<>
      <SelectField label="Company" value="aapl" onValueChange={vi.fn()} options={[
        { value: "aapl", label: "Apple Inc. (AAPL)" },
      ]} />
      <input aria-label="Fiscal year" />
    </>);
    fireEvent.click(screen.getByRole("button", { name: "Company" }));
    fireEvent.click(screen.getByRole("option", { name: "Apple Inc. (AAPL)" }));
    const year = screen.getByRole("textbox", { name: "Fiscal year" });
    year.focus();
    act(() => pendingFrames.forEach(callback => callback(0)));
    expect(year).toHaveFocus();
  });

  test("renders its listbox in the document overlay root and supports keyboard type-ahead", async () => {
    render(
      <div data-testid="host">
        <SelectField label="Company" value="aapl" onValueChange={vi.fn()} options={[
          { value: "aapl", label: "Apple Inc. (AAPL)" },
          { value: "msft", label: "Microsoft Corporation (MSFT)" },
        ]} />
      </div>,
    );

    const trigger = screen.getByRole("button", { name: "Company" });
    fireEvent.click(trigger);
    const listbox = screen.getByRole("listbox", { name: "Company" });
    expect(document.querySelector('[data-testid="host"]')).not.toContainElement(listbox);
    expect(listbox).toHaveStyle({ position: "fixed", zIndex: "70" });
    await waitFor(() => expect(screen.getByRole("option", { name: "Apple Inc. (AAPL)" })).toHaveFocus());

    fireEvent.keyDown(screen.getByRole("option", { name: "Apple Inc. (AAPL)" }), { key: "m" });
    expect(screen.getByRole("option", { name: "Microsoft Corporation (MSFT)" })).toHaveFocus();
    fireEvent.keyDown(screen.getByRole("option", { name: "Microsoft Corporation (MSFT)" }), { key: "Escape" });
    expect(trigger).toHaveFocus();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
