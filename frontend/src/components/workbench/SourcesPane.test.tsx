import React, { type ReactNode, useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Source } from "../../types";
import { useWorkbenchController } from "../../hooks/useWorkbenchController";
import { useWorkbenchPreferences } from "../../hooks/useWorkbenchPreferences";
import { LocaleProvider } from "../../lib/i18n";
import { WorkbenchContextProvider } from "./WorkbenchContext";
import { SourcesPane } from "./SourcesPane";

afterEach(cleanup);

beforeEach(() => {
  localStorage.clear();
});

const sources: Source[] = [
  {
    citation: "AAPL 2025 10-K · Risk Factors",
    ticker: "AAPL",
    filing_type: "10-K",
    filing_date: "2025-10-31",
    section: "risk_factors",
    chunk_id: "risk-1",
    text_preview: "The company faces competition risks.",
  },
  {
    citation: "AAPL saved risk excerpt",
    ticker: "AAPL",
    filing_type: "10-K",
    filing_date: "2025-10-31",
    section: "risk_factors",
    chunk_id: "risk-2",
    text_preview: "Saved snapshot from an earlier corpus revision.",
    text: "Saved snapshot from an earlier corpus revision.",
    stored_snapshot: {
      chunk_id: "risk-2",
      snapshot_state: "stale",
    },
  },
  {
    citation: "MSFT 2025 10-K · Business",
    ticker: "MSFT",
    filing_type: "10-K",
    filing_date: "2025-10-31",
    section: "business",
    chunk_id: "business-1",
    text_preview: "Microsoft Cloud revenue increased.",
  },
];

function WorkbenchHarness({ children }: { children: ReactNode }) {
  const controller = useWorkbenchController();
  const preferences = useWorkbenchPreferences();
  return (
    <WorkbenchContextProvider value={{ controller, preferences }}>
      {children}
    </WorkbenchContextProvider>
  );
}

function renderPane(
  props: Partial<React.ComponentProps<typeof SourcesPane>> = {},
) {
  return render(
    <LocaleProvider>
      <WorkbenchHarness>
        <SourcesPane
          sources={sources}
          selectedIndex={0}
          onSelectIndex={vi.fn()}
          {...props}
        />
      </WorkbenchHarness>
    </LocaleProvider>,
  );
}

describe("SourcesPane", () => {
  test("does not manufacture pages or a Risk Factors section for unlocated excerpts", () => {
    renderPane({ sources: [{ citation: "Unclassified excerpt", text_preview: "Indexed text without page or section metadata." }] });
    expect(screen.queryByText(/^p\.\s*\d+$/)).not.toBeInTheDocument();
    expect(screen.queryByText("Risk Factors")).not.toBeInTheDocument();
    expect(screen.getByText("Section unavailable")).toBeInTheDocument();
  });

  test("renders one source stack with honest saved and stale states", () => {
    renderPane();

    expect(screen.getByRole("region", { name: "Retrieved sources" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getAllByText("Cited in answer")).toHaveLength(3);
    expect(screen.getByText("Stale snapshot · still readable")).toBeInTheDocument();
    expect(screen.getByText("Saved evidence")).toBeInTheDocument();
    const savedStaleCard = screen.getAllByRole("article")[1];
    expect(savedStaleCard).toHaveAttribute("data-source-saved", "true");
    expect(savedStaleCard).toHaveAttribute("data-source-stale", "true");
    expect(savedStaleCard).toHaveAttribute("data-source-citation-linked", "true");
    expect(screen.getByRole("button", { name: "Open document for source 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save evidence source 1" })).toBeInTheDocument();
  });

  test("uses the workbench controller for All/Cited/Saved policy", async () => {
    renderPane({ citedIndexes: [0, 2] });

    const allFilter = screen.getByRole("button", { name: "All" });
    expect(allFilter).toHaveAttribute("aria-pressed", "true");
    expect(allFilter.closest(".sources-pane__controls")).not.toHaveClass("sr-only");
    expect(screen.getByRole("button", { name: /^Saved$/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cited" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.queryByText("Saved snapshot from an earlier corpus revision.")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^Saved$/ }));
    await waitFor(() => {
      expect(screen.getAllByRole("listitem")).toHaveLength(1);
    });
    expect(screen.getByText("AAPL saved risk excerpt")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Saved$/ })).toHaveAttribute("aria-pressed", "true");
  });

  test("does not expose presentation-only source controls or generic Apple follow-ups", () => {
    renderPane();

    expect(screen.queryByRole("button", { name: "Relevance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Filter sources" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "View all 3 sources" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
    expect(screen.queryByText("How does Apple manage supply chain risks?")).not.toBeInTheDocument();
    expect(screen.queryByText("What are the regulatory challenges for Apple?")).not.toBeInTheDocument();
  });

  test("moves selection with list keyboard controls and Enter", () => {
    function ControlledPane() {
      const [selectedIndex, setSelectedIndex] = useState(0);
      return (
        <SourcesPane
          sources={sources}
          selectedIndex={selectedIndex}
          onSelectIndex={setSelectedIndex}
        />
      );
    }

    render(
      <LocaleProvider>
        <WorkbenchHarness>
          <ControlledPane />
        </WorkbenchHarness>
      </LocaleProvider>,
    );

    const list = screen.getByRole("list", { name: "Source evidence list" });
    list.focus();
    fireEvent.keyDown(list, { key: "ArrowDown" });
    expect(screen.getByRole("button", { name: /Open source excerpt 2:/ })).toHaveAttribute("aria-pressed", "true");
    fireEvent.keyDown(list, { key: "End" });
    expect(screen.getByRole("button", { name: /Open source excerpt 3:/ })).toHaveAttribute("aria-pressed", "true");
    fireEvent.keyDown(list, { key: "Enter" });
    expect(screen.getByRole("button", { name: /Open source excerpt 3:/ })).toHaveAttribute("aria-pressed", "true");
  });

  test("keeps answer-only filters off for catalog/search origins", () => {
    renderPane({ origin: "search" });

    expect(screen.queryByRole("group", { name: "Source filters" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  test("reports unavailable selection without substituting a neighboring source", () => {
    renderPane({
      sources: [sources[0]],
      selectedIndex: 0,
      unavailable: true,
      unavailableReason: "The selected answer variant is unavailable.",
    });

    expect(screen.getByRole("status")).toHaveTextContent("selected answer variant is unavailable");
    expect(screen.getByRole("article")).toHaveAttribute("data-source-state", "unavailable");
    expect(screen.getAllByText("The selected answer variant is unavailable.")).toHaveLength(2);
  });

  test("uses the existing save writer callback and updates the card indicator", async () => {
    const onSaveSource = vi.fn().mockResolvedValue(undefined);
    renderPane({ onSaveSource });

    fireEvent.click(screen.getByRole("button", { name: "Save evidence source 1" }));
    await waitFor(() => expect(onSaveSource).toHaveBeenCalledWith(sources[0], 0));
    expect(await screen.findByRole("button", { name: "Evidence saved for source 1" })).toBeDisabled();
  });

  test("copies an excerpt with its citation and filing identity", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    renderPane();
    fireEvent.click(screen.getByRole("button", { name: "Copy excerpt 1 with citation" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining("[Source 1] AAPL 2025 10-K · Risk Factors")));
    expect(writeText.mock.calls[0][0]).toContain("Company: Apple Inc. (AAPL)");
    expect(writeText.mock.calls[0][0]).toContain("Filed: 2025-10-31");
    expect(await screen.findByRole("button", { name: "Copied excerpt 1" })).toBeInTheDocument();
  });
});
