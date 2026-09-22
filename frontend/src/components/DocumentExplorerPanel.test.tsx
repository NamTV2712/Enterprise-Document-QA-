import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { DocumentExplorerPanel } from "./DocumentExplorerPanel";
import { LocaleProvider } from "../lib/i18n";
import { getDocumentChunks, getDocumentFacets, getDocuments, getDocumentStats, getReaderManifest } from "../lib/api";

vi.mock("../lib/api", () => ({
  getDocuments: vi.fn(),
  getDocumentChunks: vi.fn(),
  getDocumentFacets: vi.fn(),
  getDocumentStats: vi.fn(),
  getReaderManifest: vi.fn(),
}));

const getDocumentsMock = vi.mocked(getDocuments);
const getChunksMock = vi.mocked(getDocumentChunks);
const getFacetsMock = vi.mocked(getDocumentFacets);
const getStatsMock = vi.mocked(getDocumentStats);
const getReaderManifestMock = vi.mocked(getReaderManifest);

describe("DocumentExplorerPanel", () => {
  beforeEach(() => {
    getDocumentsMock.mockResolvedValue({
      items: [{
        document_id: "AAPL:0001",
        ticker: "AAPL",
        filing_date: "2024-11-01",
        accession_number: "0001",
        sections: ["financial_table"],
        chunk_count: 2,
        source_url: "https://www.sec.gov/Archives/edgar/data/320193/0001/filing.htm",
      }],
      total: 1,
      page: 1,
      page_size: 12,
    });
    getChunksMock.mockResolvedValue({
      items: [{
        chunk_id: "chunk-1",
        ticker: "AAPL",
        section: "financial_table",
        filing_date: "2024-11-01",
        accession_number: "0001",
        text_preview: "Revenue was $100B.",
        text_length: 18,
        source_url: "https://www.sec.gov/Archives/edgar/data/320193/0001/filing.htm",
      }],
      total: 1,
      page: 1,
      page_size: 8,
    });
    getReaderManifestMock.mockResolvedValue({
      schema_version: "sec-reader-v4",
      document_id: "AAPL:0001",
      status: "available",
      reason_code: "available",
      reason: null,
      identity: { ticker: "AAPL", cik: 320193, accession_number: "0001", filing_date: "2024-11-01", report_date: "2024-09-28", status: "verified", reason_code: "verified" },
      source_set_revision: "rev-1",
      sources: [],
      representations: [
        { kind: "structured", status: "partial", reason_code: "structured_representation_unavailable", reason: "Unsupported visible content", coverage_status: "partial", coverage_reason: "Unsupported visible content", coverage_reason_code: "unsupported_visible_content" },
        { kind: "normalized_text", status: "available", reason_code: "available", reason: null, coverage_status: "complete" },
        { kind: "pdf", status: "unavailable", reason_code: "pdf_representation_unavailable", reason: "Not in scope" },
      ],
    });
    // API-003 payloads: the stored artifacts record no form type, so the
    // dimension is published as unknown with the reason the panel repeats.
    getStatsMock.mockResolvedValue({
      generated_at: "2024-11-02T00:00:00Z",
      documents: 50,
      companies: 12,
      chunks: 10053,
      configured_companies: 40,
      configured_companies_without_documents: ["ZZZZ"],
      configured_companies_with_documents: ["AAPL"],
      filing_dates: { availability: "recorded", reason: null, earliest: 2024, latest: 2025, documents_without_value: 0 },
      report_dates: { availability: "unknown", reason: "No loaded document records a report date.", documents_with_value: 0 },
      sections: { availability: "recorded", reason: null, documents_without_value: 0, values: [{ value: "financial_table", count: 50 }] },
      filing_type: { availability: "unknown", reason: "Stored filing artifacts record no per-filing form type.", value: null },
    });
    getFacetsMock.mockResolvedValue({
      generated_at: "2024-11-02T00:00:00Z",
      count_basis: "all_filters_except_own_dimension",
      scope: { ticker: null, section: null, year: null, filing_date: null, search: null, documents: 50 },
      facets: [
        { dimension: "company", availability: "recorded", reason: null, values: [{ value: "AAPL", count: 1 }] },
        { dimension: "section", availability: "recorded", reason: null, values: [{ value: "financial_table", count: 1 }] },
        { dimension: "year", availability: "recorded", reason: null, values: [{ value: 2024, count: 1 }] },
      ],
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const selectRow = async () => {
    fireEvent.click(await screen.findByText("Apple Inc. (AAPL)"));
    await waitFor(() => expect(getChunksMock).toHaveBeenCalledWith("AAPL:0001", expect.any(Object), expect.any(AbortSignal)));
  };

  test("loads filings and opens read-only source excerpts", async () => {
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);
    expect(await screen.findByText("Apple Inc. (AAPL)")).toBeInTheDocument();
    await selectRow();
    fireEvent.click(await screen.findByRole("tab", { name: /Sections \(1\)/i }));
    expect(await screen.findByText("Revenue was $100B.")).toBeInTheDocument();
  });

  test("opens the selected filing in the document workspace with stable identity", async () => {
    const onOpenDocument = vi.fn();
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} onOpenDocument={onOpenDocument} /></LocaleProvider>);
    fireEvent.click(await screen.findByText("Apple Inc. (AAPL)"));
    fireEvent.click(await screen.findByRole("button", { name: "Open document workspace" }));
    expect(onOpenDocument).toHaveBeenCalledWith(expect.objectContaining({
      kind: "catalog",
      documentId: "AAPL:0001",
      ticker: "AAPL",
      filingDate: "2024-11-01",
      returnView: "documents",
      returnFocusId: "document-workspace-AAPL-0001",
    }));

    // The excerpt handoff keeps the chunk-level focus identity.
    fireEvent.click(await screen.findByRole("tab", { name: /Sections \(1\)/i }));
    fireEvent.click(await screen.findByRole("button", { name: /chunk-1 · 18 chars/i }));
    expect(onOpenDocument).toHaveBeenLastCalledWith(expect.objectContaining({
      kind: "catalog",
      documentId: "AAPL:0001",
      initialTab: "excerpt",
      returnFocusId: "document-workspace-AAPL-0001-excerpt-chunk-1",
    }));
  });

  test("reports representation availability for the selected document", async () => {
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);
    fireEvent.click(await screen.findByText("Apple Inc. (AAPL)"));
    fireEvent.click(await screen.findByRole("tab", { name: /Representations/i }));
    expect(await screen.findByText("Normalized")).toBeInTheDocument();
    expect(screen.getByText("Structured")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
  });

  test("separates an empty search result from an empty catalog", async () => {
    getDocumentsMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 12 });
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);

    expect(await screen.findByText("No documents")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Search filings" }), { target: { value: "MSFT" } });
    expect(await screen.findByText("No matching documents")).toBeInTheDocument();
    expect(screen.getByText("No documents match the filters")).toBeInTheDocument();
  });

  test("keeps the error state distinct and retries without losing the list", async () => {
    getDocumentsMock.mockRejectedValueOnce(Object.assign(new Error("server unavailable"), { status: 503 }));
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);

    expect(await screen.findByRole("alert")).toHaveTextContent("research service is temporarily unavailable");
    expect(screen.queryByText("No documents")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Apple Inc. (AAPL)")).toBeInTheDocument();
  });

  test("reports catalog totals from API-003 statistics and the unknown form type", async () => {
    const { container } = render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);

    expect(await screen.findByText("10,053")).toBeInTheDocument();
    expect(screen.getByText("Total Documents")).toBeInTheDocument();
    expect(screen.getByText("Filing years 2024–2025")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();

    // The stored artifacts record no form type, so the panel repeats API-003's
    // unknown state instead of naming a form type of its own.
    expect(screen.getAllByText("Unknown").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Stored filing artifacts record no per-filing form type.").length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("10-K");
  });

  test("offers only the facet dimensions API-003 records", async () => {
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);
    await screen.findByText("Apple Inc. (AAPL)");

    // Company and section carry their own counts; the year list appears only
    // because the facet reports the dimension as recorded.
    fireEvent.click(screen.getByRole("button", { name: "Company / Ticker" }));
    expect(screen.getByRole("option", { name: "Apple Inc. (AAPL) (1)" })).toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole("option", { name: "Apple Inc. (AAPL) (1)" }), { key: "Escape" });

    fireEvent.click(screen.getByRole("button", { name: "Year" }));
    fireEvent.click(screen.getByRole("option", { name: "2024 (1)" }));

    await waitFor(() => expect(getDocumentsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ year: 2024, page: 1 }),
      expect.any(AbortSignal),
    ));
    await waitFor(() => expect(getFacetsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ year: 2024 }),
      expect.any(AbortSignal),
    ));
  });

  test("applies sort and page size through the catalog query", async () => {
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);
    await screen.findByText("Apple Inc. (AAPL)");
    expect(getDocumentsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ page_size: 10, sort: "filing_date", direction: "desc" }),
      expect.any(AbortSignal),
    );

    fireEvent.click(screen.getByRole("button", { name: "Sort by" }));
    fireEvent.click(screen.getByRole("option", { name: "Chunks (most)" }));
    await waitFor(() => expect(getDocumentsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: "chunk_count", direction: "desc", page: 1 }),
      expect.any(AbortSignal),
    ));

    fireEvent.click(screen.getByRole("button", { name: "Rows per page" }));
    fireEvent.click(screen.getByRole("option", { name: "20 per page" }));
    await waitFor(() => expect(getDocumentsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ page_size: 20 }),
      expect.any(AbortSignal),
    ));
    // The card subtitle and the footer report the same page range.
    expect((await screen.findAllByText("Showing 1–1 of 1 documents")).length).toBe(2);
  });

  test("clears every filter in one action", async () => {
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);
    await screen.findByText("Apple Inc. (AAPL)");
    fireEvent.change(screen.getByRole("textbox", { name: "Search filings" }), { target: { value: "AAPL" } });
    await waitFor(() => expect(getDocumentsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "AAPL" }),
      expect.any(AbortSignal),
    ));

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByRole("textbox", { name: "Search filings" })).toHaveValue("");
    // The filter row follows the debounced term, so it clears a beat later.
    await waitFor(() => expect(screen.queryByRole("button", { name: "Clear filters" })).not.toBeInTheDocument());
    // Facets are never cached, so they are the request that proves the scope
    // really went back to unfiltered.
    await waitFor(() => expect(getFacetsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: undefined, ticker: null, section: null, year: null }),
      expect.any(AbortSignal),
    ));
  });

  test("falls back to the provided counts when API-003 statistics are unavailable", async () => {
    getStatsMock.mockRejectedValueOnce(new Error("catalog not ready"));
    render(
      <LocaleProvider>
        <DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} companyCount={3} chunkCount={7} />
      </LocaleProvider>,
    );

    expect(await screen.findByText("Apple Inc. (AAPL)")).toBeInTheDocument();
    expect(await screen.findByText("Catalog statistics unavailable")).toBeInTheDocument();
    // A failed statistics read never turns into a fabricated zero.
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
