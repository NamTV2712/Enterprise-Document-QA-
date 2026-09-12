import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ScopeEditor } from "./ScopeEditor";

afterEach(() => document.body.innerHTML = "");

describe("ScopeEditor", () => {
  test("opens details without expanding the composer flow and returns focus on Escape", () => {
    render(
      <ScopeEditor
        scopeLabel="All companies · All sections · Top 5"
        tickers={["AAPL"]}
        sections={["risk_factors"]}
        selectedTicker={null}
        onSelectTicker={vi.fn()}
        selectedSection={null}
        onSelectSection={vi.fn()}
        topK={5}
        onChangeTopK={vi.fn()}
        enableComparative={false}
        onToggleComparative={vi.fn()}
      />,
    );

    const trigger = screen.getByRole("button", { name: /Scope · All companies/ });
    fireEvent.click(trigger);
    expect(screen.getByRole("dialog", { name: "Retrieval scope" })).toBeInTheDocument();
    expect(document.querySelector(".composer-settings__popover")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Retrieval scope" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  test("keeps scope controls controlled inside the popover", () => {
    const onChangeTopK = vi.fn();
    render(
      <ScopeEditor scopeLabel="All companies · All sections · Top 5" tickers={[]} sections={[]} selectedTicker={null} onSelectTicker={vi.fn()} selectedSection={null} onSelectSection={vi.fn()} topK={5} onChangeTopK={onChangeTopK} enableComparative={false} onToggleComparative={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Scope · All companies/ }));
    fireEvent.change(screen.getByRole("slider", { name: "Top K" }), { target: { value: "6" } });
    expect(onChangeTopK).toHaveBeenCalledWith(6);
  });

  test("keeps the scope popover open while a portaled select closes", () => {
    render(
      <ScopeEditor
        scopeLabel="All companies · All sections · Top 5"
        tickers={["AAPL", "MSFT"]}
        sections={[]}
        selectedTicker={null}
        onSelectTicker={vi.fn()}
        selectedSection={null}
        onSelectSection={vi.fn()}
        topK={5}
        onChangeTopK={vi.fn()}
        enableComparative={false}
        onToggleComparative={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Scope · All companies/ }));
    fireEvent.click(screen.getByRole("button", { name: "Company" }));
    const option = screen.getByRole("option", { name: /Apple Inc\. \(AAPL\)/ });
    fireEvent.keyDown(option, { key: "Escape" });

    expect(screen.getByRole("dialog", { name: "Retrieval scope" })).toBeInTheDocument();
    expect(screen.queryByRole("listbox", { name: "Company" })).not.toBeInTheDocument();
  });

  test("supports a controlled open owner for contextual commands", () => {
    const onOpenChange = vi.fn();
    render(
      <ScopeEditor
        open={false}
        onOpenChange={onOpenChange}
        scopeLabel="All companies · All sections · Top 5"
        tickers={[]}
        sections={[]}
        selectedTicker={null}
        onSelectTicker={vi.fn()}
        selectedSection={null}
        onSelectSection={vi.fn()}
        topK={5}
        onChangeTopK={vi.fn()}
        enableComparative={false}
        onToggleComparative={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Scope · All companies/ }));
    expect(onOpenChange).toHaveBeenCalledWith(true);
    expect(screen.queryByRole("dialog", { name: "Retrieval scope" })).not.toBeInTheDocument();
  });
});
