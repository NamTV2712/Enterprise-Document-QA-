import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { getSectionDisplay, SourcesPanel } from "./SourcesPanel";

afterEach(cleanup);

const sources = [
  {
    citation: "AAPL 10-K (filed 2025-10-31), Section: Financial Table",
    score: 6.3033,
    score_kind: "retrieval" as const,
    text_preview: "Total net sales | 416,161 | 391,035 | 383,285",
  },
];

describe("SourcesPanel", () => {
  test("parses API citation labels into ticker, year, and section", () => {
    expect(getSectionDisplay(sources[0].citation)).toEqual({
      ticker: "AAPL",
      year: "2025",
      section: "Structured Financial Tables",
    });
  });

  test("keeps a useful evidence summary visible while collapsed", () => {
    render(<SourcesPanel sources={sources} />);

    const toggle = screen.getByRole("button", {
      name: "Show 1 retrieved filing evidence excerpts",
    });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText(/Apple Inc\. \(AAPL\)/)).toBeInTheDocument();
    expect(screen.queryByText(sources[0].text_preview)).not.toBeInTheDocument();

    fireEvent.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(sources[0].text_preview)).toBeInTheDocument();
    expect(screen.getByText("Score kind")).toBeInTheDocument();
    expect(screen.getByText("retrieval · 6.3033")).toBeInTheDocument();
  });

  test("filters excerpts without renumbering citation order", () => {
    render(<SourcesPanel sources={[
      { citation: "AAPL source 1", score: 1, score_kind: "retrieval", text_preview: "First excerpt" },
      { citation: "AAPL source 2", score: 2, score_kind: "retrieval", text_preview: "Second excerpt" },
    ]} />);

    fireEvent.click(screen.getByRole("button", { name: "Show 2 retrieved filing evidence excerpts" }));
    fireEvent.change(screen.getByRole("searchbox", { name: "Search within these evidence excerpts" }), { target: { value: "Second" } });
    expect(screen.queryByText("First excerpt")).not.toBeInTheDocument();
    expect(screen.getByText("Second excerpt")).toBeInTheDocument();
    expect(document.querySelector('[data-source-index="1"]')).toBeInTheDocument();
  });
});
