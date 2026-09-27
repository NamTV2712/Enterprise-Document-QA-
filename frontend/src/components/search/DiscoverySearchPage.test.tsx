import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { DiscoverySearchPage } from "./DiscoverySearchPage";
import { LocaleProvider } from "../../lib/i18n";
import { ApiError, createDiscoverySearch, getDiscoverySnapshot } from "../../lib/api";
import type { CatalogFacet, DiscoveryGroup, DiscoveryHit, DiscoverySnapshotResponse, Source } from "../../types";

vi.mock("../../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/api")>();
  return { ...actual, createDiscoverySearch: vi.fn(), getDiscoverySnapshot: vi.fn() };
});

const createSearchMock = vi.mocked(createDiscoverySearch);
const readSnapshotMock = vi.mocked(getDiscoverySnapshot);

const FACETS: CatalogFacet[] = [
  { dimension: "company", availability: "recorded", reason: null, values: [{ value: "AAPL", count: 1 }, { value: "MSFT", count: 1 }] },
  { dimension: "year", availability: "recorded", reason: null, values: [{ value: 2025, count: 8 }, { value: 2026, count: 42 }] },
  {
    dimension: "section",
    availability: "recorded",
    reason: null,
    values: [{ value: "business", count: 50 }, { value: "risk_factors", count: 50 }],
  },
];

const HITS: DiscoveryHit[] = [
  {
    chunk_id: "MSFT_1_mdna_0005",
    document_id: "MSFT:0001",
    ticker: "MSFT",
    section: "mdna",
    filing_date: "2025-07-30",
    report_date: "2025-06-30",
    chunk_index: 5,
    score: 10.703384,
    snippet: { text: "Microsoft Cloud revenue grew on Azure demand.", ranges: [[0, 9]], truncated: true },
  },
  {
    chunk_id: "ORCL_1_mdna_0076",
    document_id: "ORCL:0002",
    ticker: "ORCL",
    section: "mdna",
    filing_date: "2026-06-22",
    report_date: "2026-05-31",
    chunk_index: 76,
    score: 9.230227,
    snippet: { text: "Our cloud and software business represented 87% of revenues.", ranges: [[4, 9]], truncated: true },
  },
];

const GROUPS: DiscoveryGroup[] = [
  {
    document_id: "MSFT:0001",
    ticker: "MSFT",
    filing_date: "2025-07-30",
    report_date: "2025-06-30",
    sections: ["mdna", "financial_statements"],
    best_score: 10.703384,
    hit_count: 43,
    hits: [HITS[0]],
  },
  {
    document_id: "ORCL:0002",
    ticker: "ORCL",
    filing_date: "2026-06-22",
    report_date: "2026-05-31",
    sections: ["mdna"],
    best_score: 9.230227,
    hit_count: 7,
    hits: [HITS[1]],
  },
];

function snapshot(overrides: Partial<DiscoverySnapshotResponse> = {}): DiscoverySnapshotResponse {
  return {
    search_id: "search-0123456789abcdef",
    query: { text: "cloud revenue", normalized: "cloud revenue", mode: "keyword" },
    grouping: { group_by: "document", group_count: 45, hit_count: 200 },
    engine: {
      key: "bm25_lexical",
      version: "v1",
      definition: "Chunks that contain at least one query term match; BM25 lexical score orders them.",
    },
    scope: {
      ticker: null,
      section: null,
      year: null,
      filing_date: null,
      documents: 50,
      count_scope: "bounded_candidates",
      candidate_ceiling: 200,
      limited_by_ceiling: true,
      matched_documents: 15,
      matched_chunks: 200,
    },
    items: GROUPS,
    total: 45,
    page: 1,
    page_size: 20,
    facets: FACETS,
    created_at: "2026-09-22T00:00:00Z",
    expires_at: "2026-09-22T00:15:00Z",
    ttl_seconds: 900,
    ...overrides,
  };
}

function renderPage(overrides: Partial<React.ComponentProps<typeof DiscoverySearchPage>> = {}) {
  return render(
    <LocaleProvider>
      <DiscoverySearchPage tickers={["AAPL", "MSFT"]} sections={["business", "risk_factors", "mdna"]} isBackendConnected={true} onUseQuestion={vi.fn()} {...overrides} />
    </LocaleProvider>,
  );
}

async function submitQuery(query = "cloud revenue") {
  fireEvent.change(screen.getByLabelText("Search Query"), { target: { value: query } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(createSearchMock).toHaveBeenCalledTimes(1));
}

describe("DiscoverySearchPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    createSearchMock.mockResolvedValue(snapshot());
    readSnapshotMock.mockResolvedValue(snapshot({ page: 2 }));
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  test("typing never searches: only an explicit submit creates one snapshot", async () => {
    renderPage();
    const input = screen.getByLabelText("Search Query");
    fireEvent.change(input, { target: { value: "cloud" } });
    fireEvent.change(input, { target: { value: "cloud revenue" } });
    expect(createSearchMock).not.toHaveBeenCalled();

    fireEvent.submit(input.closest("form") as HTMLFormElement);
    await waitFor(() => expect(createSearchMock).toHaveBeenCalledTimes(1));
    expect(createSearchMock).toHaveBeenCalledWith(
      expect.objectContaining({ query: "cloud revenue", group_by: "document", page: 1 }),
      expect.any(AbortSignal),
    );
    expect(await screen.findByRole("heading", { name: /Results for/ })).toBeInTheDocument();
  });

  test("a too-short draft cannot be submitted", async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Search Query"), { target: { value: "a" } });
    expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
    expect(screen.getByText(/At least 2 characters/)).toBeInTheDocument();
    expect(createSearchMock).not.toHaveBeenCalled();
  });

  test("paging reads the same snapshot instead of searching again", async () => {
    renderPage();
    await submitQuery();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));

    await waitFor(() => expect(readSnapshotMock).toHaveBeenCalledTimes(1));
    expect(readSnapshotMock).toHaveBeenCalledWith("search-0123456789abcdef", { page: 2, page_size: 20 }, expect.any(AbortSignal));
    expect(createSearchMock).toHaveBeenCalledTimes(1);
  });

  test("page size changes reuse the snapshot and reset to page one", async () => {
    renderPage();
    await submitQuery();
    fireEvent.click(screen.getByRole("button", { name: "Rows per page" }));
    fireEvent.click(screen.getByRole("option", { name: "50 per page" }));

    await waitFor(() => expect(readSnapshotMock).toHaveBeenCalledWith("search-0123456789abcdef", { page: 1, page_size: 50 }, expect.any(AbortSignal)));
    expect(createSearchMock).toHaveBeenCalledTimes(1);
  });

  test("editing the draft never relabels the results on screen", async () => {
    renderPage();
    await submitQuery();
    expect(await screen.findByRole("heading", { name: "Results for “cloud revenue”" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search Query"), { target: { value: "risk factors" } });
    expect(screen.getByRole("heading", { name: "Results for “cloud revenue”" })).toBeInTheDocument();
    expect(screen.getByText(/draft differs from the results on screen/i)).toBeInTheDocument();
    expect(createSearchMock).toHaveBeenCalledTimes(1);
  });

  test("a committed filter change creates a new snapshot, a draft filter does not", async () => {
    renderPage();
    await submitQuery();

    // The rail repeats the same filters as the query card, exactly like the
    // reference, so the rail region is addressed explicitly here.
    const rail = within(screen.getByRole("complementary", { name: "Search overview" }));
    fireEvent.click(rail.getByRole("button", { name: "Company" }));
    fireEvent.click(screen.getByRole("option", { name: "Microsoft Corporation (MSFT)" }));
    expect(createSearchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/New filters apply on the next search/)).toBeInTheDocument();

    createSearchMock.mockResolvedValue(snapshot({
      search_id: "search-fedcba9876543210",
      scope: { ...snapshot().scope, ticker: "MSFT", documents: 1, matched_documents: 1 },
    }));
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(createSearchMock).toHaveBeenCalledTimes(2));
    expect(createSearchMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: "cloud revenue", ticker: "MSFT" }),
      expect.any(AbortSignal),
    );
  });

  test("changing grouping is a committed change that searches again", async () => {
    renderPage();
    await submitQuery();

    createSearchMock.mockResolvedValue(snapshot({
      search_id: "search-chunk0000000000",
      grouping: { group_by: "chunk", group_count: 33, hit_count: 200 },
      items: HITS,
      total: 200,
      // Real corpus shape for "supply chain" in chunk mode.
      scope: { ...snapshot().scope, matched_documents: 33, matched_chunks: 200 },
    }));
    fireEvent.click(screen.getByLabelText("Group by filing"));

    await waitFor(() => expect(createSearchMock).toHaveBeenCalledTimes(2));
    expect(createSearchMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ group_by: "chunk", query: "cloud revenue" }),
      expect.any(AbortSignal),
    );
    // Chunk grouping pages excerpts; the toolbar and the footer agree on it.
    expect((await screen.findAllByText(/Showing 1–20 of 200 excerpts/)).length).toBe(2);
    expect(screen.getByText("Across 33 filings")).toBeInTheDocument();
  });

  test("a stale response never replaces a newer submission", async () => {
    renderPage();
    const form = () => screen.getByLabelText("Search Query").closest("form") as HTMLFormElement;
    let resolveFirst: ((value: DiscoverySnapshotResponse) => void) | null = null;
    createSearchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }));
    fireEvent.change(screen.getByLabelText("Search Query"), { target: { value: "cloud revenue" } });
    fireEvent.submit(form());

    createSearchMock.mockResolvedValueOnce(snapshot({ search_id: "search-second00000000", query: { text: "supply chain", normalized: "supply chain", mode: "keyword" } }));
    fireEvent.change(screen.getByLabelText("Search Query"), { target: { value: "supply chain" } });
    fireEvent.submit(form());
    await waitFor(() => expect(screen.getByRole("heading", { name: "Results for “supply chain”" })).toBeInTheDocument());

    resolveFirst?.(snapshot({ search_id: "search-first000000000" }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.getByRole("heading", { name: "Results for “supply chain”" })).toBeInTheDocument();
  });

  test.each(["success", "error"])("a late old page %s cannot affect a new search", async (completion) => {
    let resolvePage!: (value: DiscoverySnapshotResponse) => void;
    let rejectPage!: (reason: unknown) => void;
    readSnapshotMock.mockImplementationOnce(() => new Promise((resolve, reject) => {
      resolvePage = resolve;
      rejectPage = reject;
    }));
    renderPage();
    await submitQuery();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    await waitFor(() => expect(readSnapshotMock).toHaveBeenCalledTimes(1));
    const pageSignal = readSnapshotMock.mock.calls[0][2];
    createSearchMock.mockResolvedValueOnce(snapshot({
      search_id: "search-fedcba9876543210",
      query: { text: "supply chain", normalized: "supply chain", mode: "keyword" },
    }));
    fireEvent.change(screen.getByLabelText("Search Query"), { target: { value: "supply chain" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await screen.findByRole("heading", { name: "Results for “supply chain”" });
    expect(pageSignal?.aborted).toBe(true);
    await act(async () => {
      if (completion === "success") resolvePage(snapshot({ page: 2 }));
      else rejectPage(new ApiError("snapshot expired", 410));
    });
    expect(screen.getByRole("heading", { name: "Results for “supply chain”" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(createSearchMock).toHaveBeenCalledTimes(2);
  });

  test("old snapshot paging cannot start while a new search is pending", async () => {
    renderPage();
    await submitQuery();
    let completeSearch!: (value: DiscoverySnapshotResponse) => void;
    createSearchMock.mockImplementationOnce(() => new Promise(resolve => { completeSearch = resolve; }));
    fireEvent.change(screen.getByLabelText("Search Query"), { target: { value: "supply chain" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(readSnapshotMock).not.toHaveBeenCalled();
    await act(async () => completeSearch(snapshot({
      search_id: "search-fedcba9876543210",
      query: { text: "supply chain", normalized: "supply chain", mode: "keyword" },
    })));
    expect(screen.getByRole("button", { name: "Next page" })).toBeEnabled();
  });

  test("keeps real result identity, snippet highlights, and the honest score label", async () => {
    const onOpenDocument = vi.fn();
    const onSaveEvidence = vi.fn<(source: Source) => void>();
    renderPage({ onOpenDocument, onSaveEvidence });
    await submitQuery();

    const cards = screen.getAllByRole("article");
    expect(cards).toHaveLength(2);
    const first = within(cards[0]);
    expect(first.getByText("Microsoft Corporation (MSFT)")).toBeInTheDocument();
    expect(first.getByText("43 matching excerpts")).toBeInTheDocument();
    expect(first.getByText("10.703")).toBeInTheDocument();
    expect(first.getByText("BM25")).toBeInTheDocument();
    // The API's ranges become real highlight marks, not re-derived matches.
    const mark = first.getByText("Microsoft");
    expect(mark.tagName).toBe("MARK");

    fireEvent.click(first.getByRole("button", { name: "Open document workspace" }));
    expect(onOpenDocument).toHaveBeenCalledWith(expect.objectContaining({
      kind: "search",
      documentId: "MSFT:0001",
      returnView: "search",
      returnFocusId: "search-document-workspace-MSFT_1_mdna_0005",
      selectedSource: expect.objectContaining({ chunk_id: "MSFT_1_mdna_0005", document_id: "MSFT:0001", ticker: "MSFT" }),
    }));
    expect(createSearchMock).toHaveBeenCalledTimes(1);

    fireEvent.click(first.getByRole("button", { name: "Save evidence" }));
    expect(onSaveEvidence).toHaveBeenCalledWith(expect.objectContaining({
      chunk_id: "MSFT_1_mdna_0005",
      document_id: "MSFT:0001",
      text_preview: "Microsoft Cloud revenue grew on Azure demand.",
    }));
  });

  test("represents bounded counts as bounded, never as a corpus total", async () => {
    renderPage();
    await submitQuery();

    expect(await screen.findByText(/bounded discovery count rather than a corpus total/)).toBeInTheDocument();
    expect(screen.getByText(/Showing 1–20 of 45 filings · scope: The whole indexed catalog/)).toBeInTheDocument();
    expect(screen.getByText("200")).toBeInTheDocument();
    expect(screen.queryByText(/10,053/)).not.toBeInTheDocument();
  });

  test("renders a legitimate no-match snapshot without sample results", async () => {
    createSearchMock.mockResolvedValue(snapshot({
      items: [],
      total: 0,
      query: { text: "zzqqxx nonexistentterm", normalized: "zzqqxx nonexistentterm", mode: "keyword" },
      scope: { ...snapshot().scope, count_scope: "no_matches", matched_documents: 0, matched_chunks: 0, limited_by_ceiling: false },
    }));
    renderPage();
    await submitQuery("zzqqxx nonexistentterm");

    expect(await screen.findByText("No matches for “zzqqxx nonexistentterm”")).toBeInTheDocument();
    expect(screen.getByText(/Searched 50 filings in scope/)).toBeInTheDocument();
    expect(screen.queryAllByRole("article")).toHaveLength(0);
  });

  test("distinguishes an expired snapshot from an unknown one and offers a rerun", async () => {
    renderPage();
    await submitQuery();

    readSnapshotMock.mockRejectedValueOnce(new ApiError("snapshot expired", 410));
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText(/snapshot expired\. Run the search again/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run the search again" })).toBeInTheDocument();
    // The expired page never turns into an empty result list.
    expect(screen.getByRole("heading", { name: "Results for “cloud revenue”" })).toBeInTheDocument();

    readSnapshotMock.mockRejectedValueOnce(new ApiError("not found", 404));
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText(/not known any more/i)).toBeInTheDocument();
    expect(createSearchMock).toHaveBeenCalledTimes(1);
  });

  test("reports a rate limit once, without retrying in a loop", async () => {
    createSearchMock.mockRejectedValue(new ApiError("rate limited", 429, null, 12));
    renderPage();
    await submitQuery();

    expect(await screen.findByRole("alert")).toHaveTextContent(/rate limit was reached \(12s\)/i);
    expect(createSearchMock).toHaveBeenCalledTimes(1);
  });

  test("rail quick filters are drafts that only apply on the next search", async () => {
    renderPage();
    await submitQuery();

    const chip = screen.getByRole("button", { name: /Risk Factors/ });
    fireEvent.click(chip);
    expect(chip).toHaveAttribute("aria-pressed", "true");
    expect(createSearchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/New filters apply on the next search/)).toBeInTheDocument();
  });

  test("records a submitted query locally and can rerun it", async () => {
    renderPage();
    await submitQuery();
    const recent = await screen.findByRole("button", { name: /cloud revenue/ });
    expect(within(recent).getByText(/45 filings/)).toBeInTheDocument();

    createSearchMock.mockResolvedValue(snapshot({ search_id: "search-rerun0000000000" }));
    fireEvent.click(recent);
    await waitFor(() => expect(createSearchMock).toHaveBeenCalledTimes(2));
    expect(window.localStorage.getItem("sec_qa_search_history_v1")).toContain("cloud revenue");
  });
});
