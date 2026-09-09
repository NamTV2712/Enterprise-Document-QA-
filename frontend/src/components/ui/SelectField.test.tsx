import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { SelectField } from "./SelectField";

afterEach(() => document.body.innerHTML = "");

describe("SelectField", () => {
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
  });
});
