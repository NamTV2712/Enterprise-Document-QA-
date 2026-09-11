import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { DocumentExplorerPanel } from "./DocumentExplorerPanel";
import { LocaleProvider } from "../lib/i18n";
import { getDocumentChunks, getDocuments } from "../lib/api";

vi.mock("../lib/api", () => ({ getDocuments: vi.fn(), getDocumentChunks: vi.fn() }));

const getDocumentsMock = vi.mocked(getDocuments);
const getChunksMock = vi.mocked(getDocumentChunks);

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
        source_url: "https://www.sec.gov/Archives/0001",
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
        source_url: "https://www.sec.gov/Archives/0001",
      }],
      total: 1,
      page: 1,
      page_size: 8,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  test("loads filings and opens read-only source excerpts", async () => {
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);
    expect(await screen.findByText("AAPL · 2024-11-01")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /AAPL · 2024-11-01/i }));
    await waitFor(() => expect(getChunksMock).toHaveBeenCalledWith("AAPL:0001", expect.any(Object), expect.any(AbortSignal)));
    expect(await screen.findByText("Revenue was $100B.")).toBeInTheDocument();
  });

  test("opens the selected filing in the document workspace with stable identity", async () => {
    const onOpenSource = vi.fn();
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} onOpenSource={onOpenSource} /></LocaleProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /AAPL · 2024-11-01/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Open document workspace" }));
    expect(onOpenSource).toHaveBeenCalledWith(expect.objectContaining({
      document_id: "AAPL:0001",
      ticker: "AAPL",
      filing_date: "2024-11-01",
    }));
  });

  test("separates an empty search result from an empty catalog", async () => {
    getDocumentsMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 12 });
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);

    expect(await screen.findByText("No documents")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Search documents" }), { target: { value: "MSFT" } });
    expect(await screen.findByText("No matching documents.")).toBeInTheDocument();
  });

  test("keeps the error state distinct and retries without losing the list", async () => {
    getDocumentsMock.mockRejectedValueOnce(Object.assign(new Error("server unavailable"), { status: 503 }));
    render(<LocaleProvider><DocumentExplorerPanel tickers={["AAPL"]} sections={["financial_table"]} /></LocaleProvider>);

    expect(await screen.findByRole("alert")).toHaveTextContent("research service is temporarily unavailable");
    expect(screen.queryByText("No documents")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("AAPL · 2024-11-01")).toBeInTheDocument();
  });
});
