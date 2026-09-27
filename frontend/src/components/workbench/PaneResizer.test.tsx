import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "../../lib/i18n";
import { PaneResizer } from "./PaneResizer";

describe("PaneResizer independent accessible controls", () => {
  it("keeps menu controls outside the focusable separator and preserves resize/collapse", () => {
    const commit = vi.fn(), reset = vi.fn(), collapse = vi.fn();
    render(<LocaleProvider><PaneResizer pane="sources" width={332} collapsed={false} onCommit={commit} onReset={reset} onCollapsedChange={collapse} /></LocaleProvider>);
    const separator = screen.getByRole("separator", { name: "Resize Sources pane" });
    expect(separator.querySelector("button, summary, [tabindex]")).toBeNull();
    expect(separator).toHaveAttribute("aria-valuenow", "332");
    fireEvent.keyDown(separator, { key: "ArrowLeft" });
    expect(commit).toHaveBeenLastCalledWith(348);
    fireEvent.keyDown(separator, { key: "Enter" });
    expect(collapse).toHaveBeenLastCalledWith(true);
    fireEvent.click(screen.getByLabelText("Open Sources pane size controls"));
    const group = screen.getByRole("group", { name: "Sources pane size controls" });
    fireEvent.click(within(group).getByRole("button", { name: "Narrower" }));
    expect(commit).toHaveBeenLastCalledWith(316);
    fireEvent.keyDown(within(group).getByRole("button", { name: "Reset" }), { key: "ArrowLeft" });
    expect(commit).toHaveBeenCalledTimes(2);
    fireEvent.click(within(group).getByRole("button", { name: "Reset" }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
