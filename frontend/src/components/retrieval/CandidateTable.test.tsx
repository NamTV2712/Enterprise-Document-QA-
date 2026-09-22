import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { CandidateTable } from "./CandidateTable";
import { LocaleProvider } from "../../lib/i18n";
import { formatScoreForFamily, type ResultOrderKey } from "../../lib/traceModel";
import type { RetrievalCandidate, RetrievalScoreKey } from "../../types";

afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
});

function makeCandidate(overrides: Partial<RetrievalCandidate> & { chunk_id: string }): RetrievalCandidate {
  return {
    citation: `${overrides.chunk_id} citation`,
    text_preview: `${overrides.chunk_id} preview text`,
    final_rank: 1,
    selected: false,
    dropped_reason: null,
    ...overrides,
  };
}

const orderOptionsList: Array<{ value: ResultOrderKey; label: string }> = [
  { value: "trace_order", label: "Trace order" },
  { value: "bm25_score", label: "BM25 (score)" },
];

interface Overrides {
  candidates?: RetrievalCandidate[];
  totalCandidates?: number;
  page?: number;
  pageSize?: number;
  order?: ResultOrderKey;
  orderScoreKey?: RetrievalScoreKey;
  orderScoreLabel?: string;
  orderScoreNote?: string | null;
  selectedChunkId?: string | null;
  onSelect?: (candidate: RetrievalCandidate) => void;
  onOpenDocument?: (candidate: RetrievalCandidate) => void;
  onOpenSource?: (candidate: RetrievalCandidate) => void;
  onSaveEvidence?: (candidate: RetrievalCandidate) => void;
  vi?: boolean;
  isBusy?: boolean;
}

function renderTable(overrides: Overrides = {}) {
  const candidates = overrides.candidates ?? [
    makeCandidate({ chunk_id: "chunk-1", citation: "AAPL 10-K p. 1", section: "Risk Factors", filing_date: "2024-10-31", bm25_score: 12.345678, final_rank: 1, selected: true }),
    makeCandidate({ chunk_id: "chunk-2", citation: "AAPL 10-K p. 2", section: "MD&A", bm25_score: 9.5, final_rank: 2, selected: false, dropped_reason: null }),
  ];
  const handlers = {
    onSelect: overrides.onSelect ?? vi.fn(),
    onOpenDocument: overrides.onOpenDocument ?? vi.fn(),
    onOpenSource: overrides.onOpenSource ?? vi.fn(),
    onSaveEvidence: overrides.onSaveEvidence ?? vi.fn(),
    onOrderChange: vi.fn(),
    onPageSizeChange: vi.fn(),
    onPageChange: vi.fn(),
  };
  const view = render(
    <LocaleProvider>
      <CandidateTable
        candidates={candidates}
        totalCandidates={overrides.totalCandidates ?? candidates.length}
        page={overrides.page ?? 1}
        pageSize={overrides.pageSize ?? 10}
        order={overrides.order ?? "trace_order"}
        orderOptionsList={orderOptionsList}
        onOrderChange={handlers.onOrderChange}
        onPageSizeChange={handlers.onPageSizeChange}
        onPageChange={handlers.onPageChange}
        orderScoreKey={overrides.orderScoreKey ?? "bm25_score"}
        orderScoreLabel={overrides.orderScoreLabel ?? "BM25"}
        orderScoreNote={overrides.orderScoreNote ?? null}
        selectedChunkId={overrides.selectedChunkId ?? null}
        onSelect={handlers.onSelect}
        onOpenDocument={overrides.onOpenDocument === undefined ? handlers.onOpenDocument : overrides.onOpenDocument}
        onOpenSource={overrides.onOpenSource === undefined ? handlers.onOpenSource : overrides.onOpenSource}
        onSaveEvidence={overrides.onSaveEvidence === undefined ? handlers.onSaveEvidence : overrides.onSaveEvidence}
        vi={overrides.vi ?? false}
        isBusy={overrides.isBusy}
        focusIdFor={(candidate) => `candidate-${candidate.chunk_id}`}
      />
    </LocaleProvider>,
  );
  return { candidates, handlers, view };
}

describe("CandidateTable", () => {
  test("renders the citation, section chip, status label, and exact score of the requested family", () => {
    const { candidates } = renderTable();
    const first = candidates[0]!;
    expect(screen.getByText("AAPL 10-K p. 1")).toBeInTheDocument();
    expect(screen.getByText("Risk Factors")).toBeInTheDocument();
    expect(screen.getByText("Selected")).toBeInTheDocument();
    const expected = formatScoreForFamily("bm25_score", first.bm25_score, false);
    expect(expected).toBe("12.3457");
    expect(screen.getByText(expected)).toBeInTheDocument();
    // The score pill follows the displayed rank, not the score value.
    expect(screen.getByText(expected).closest(".console-pill")).toHaveClass("console-pill--high");
    expect(screen.getByText("2024-10-31")).toBeInTheDocument();
  });

  test("a candidate with a missing score shows the family Not reported text and never a zero", () => {
    renderTable({
      candidates: [
        makeCandidate({ chunk_id: "chunk-missing", citation: "Missing score citation", section: "Notes", final_rank: 1, selected: false, dropped_reason: null }),
      ],
      totalCandidates: 1,
    });
    expect(screen.getByText("Missing score citation")).toBeInTheDocument();
    expect(screen.getByText("Not reported")).toBeInTheDocument();
    expect(screen.queryByText("0", { exact: true })).not.toBeInTheDocument();
  });

  test("dropped reasons use the traceModel label and a null reason reads Not selected", () => {
    renderTable({
      candidates: [
        makeCandidate({ chunk_id: "chunk-drop", citation: "Dropped citation", section: "Notes", bm25_score: 3.25, final_rank: 4, selected: false, dropped_reason: "ranked_below_top_k" }),
        makeCandidate({ chunk_id: "chunk-idle", citation: "Idle citation", section: "Notes", bm25_score: 2.5, final_rank: 5, selected: false, dropped_reason: null }),
      ],
      totalCandidates: 2,
    });
    expect(screen.getByText("Ranked below the selected top-k")).toBeInTheDocument();
    expect(screen.getByText("Not selected")).toBeInTheDocument();
  });

  test("clicking a row selects by chunk identity and Enter on a focused row does the same", () => {
    const onSelect = vi.fn();
    const { candidates } = renderTable({ onSelect });
    fireEvent.click(screen.getByText("AAPL 10-K p. 2"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0]?.[0]).toMatchObject({ chunk_id: "chunk-2" });
    expect(onSelect.mock.calls[0]?.[0]).toBe(candidates[1]);

    const row = screen.getByText("AAPL 10-K p. 1").closest("tr")!;
    fireEvent.keyDown(row, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledTimes(2);
    expect(onSelect.mock.calls[1]?.[0]).toMatchObject({ chunk_id: "chunk-1" });

    fireEvent.keyDown(row, { key: " " });
    expect(onSelect).toHaveBeenCalledTimes(3);
    expect(onSelect.mock.calls[2]?.[0]).toMatchObject({ chunk_id: "chunk-1" });
  });

  test("action buttons call their own handler with the clicked candidate and never trigger onSelect", () => {
    const onSelect = vi.fn();
    const onOpenDocument = vi.fn();
    const onOpenSource = vi.fn();
    const onSaveEvidence = vi.fn();
    renderTable({ onSelect, onOpenDocument, onOpenSource, onSaveEvidence });

    fireEvent.click(screen.getAllByRole("button", { name: "Open document workspace" })[1]!);
    expect(onOpenDocument).toHaveBeenCalledTimes(1);
    expect(onOpenDocument.mock.calls[0]?.[0]).toMatchObject({ chunk_id: "chunk-2" });

    fireEvent.click(screen.getAllByRole("button", { name: "Open indexed source" })[0]!);
    expect(onOpenSource).toHaveBeenCalledTimes(1);
    expect(onOpenSource.mock.calls[0]?.[0]).toMatchObject({ chunk_id: "chunk-1" });

    fireEvent.click(screen.getAllByRole("button", { name: "Save evidence" })[0]!);
    expect(onSaveEvidence).toHaveBeenCalledTimes(1);
    expect(onSaveEvidence.mock.calls[0]?.[0]).toMatchObject({ chunk_id: "chunk-1" });

    expect(onSelect).not.toHaveBeenCalled();
  });

  test("pager disables Previous on page 1 and Next on the last page, and forwards chosen values", () => {
    const first = renderTable({ totalCandidates: 25, page: 1, pageSize: 10 });
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next page" })).not.toBeDisabled();
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getByText("Showing 1–10 of 25 candidates")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(first.handlers.onPageChange).toHaveBeenCalledWith(2);

    // Rows-per-page forwards the numeric value.
    fireEvent.click(screen.getByRole("button", { name: "Rows per page" }));
    fireEvent.click(screen.getByRole("option", { name: "20 per page" }));
    expect(first.handlers.onPageSizeChange).toHaveBeenCalledWith(20);

    // Order forwards the chosen order key.
    fireEvent.click(screen.getByRole("button", { name: "Order" }));
    fireEvent.click(screen.getByRole("option", { name: "BM25 (score)" }));
    expect(first.handlers.onOrderChange).toHaveBeenCalledWith("bm25_score");
    first.view.unmount();
    cleanup();

    renderTable({ totalCandidates: 25, page: 3, pageSize: 10 });
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous page" })).not.toBeDisabled();
    expect(screen.getByText("3 / 3")).toBeInTheDocument();
  });

  test("an empty candidate list renders the empty state and no data rows", () => {
    renderTable({ candidates: [], totalCandidates: 0 });
    expect(screen.getByText("No candidates")).toBeInTheDocument();
    expect(
      screen.getByText("This trace returned no candidates in the submitted scope."),
    ).toBeInTheDocument();
    const bodyRows = within(screen.getByRole("table")).getAllByRole("row");
    // Header row plus the single empty-state row.
    expect(bodyRows).toHaveLength(2);
    expect(screen.queryByText("AAPL 10-K p. 1")).not.toBeInTheDocument();
  });

  test("renders no forbidden score vocabulary", () => {
    renderTable({ orderScoreNote: "Scores are family-specific values from the submitted trace." });
    const text = document.body.textContent ?? "";
    expect(text).not.toContain("%");
    expect(text.toLowerCase()).not.toContain("confidence");
    expect(text.toLowerCase()).not.toContain("probability");
  });
});
