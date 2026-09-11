import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { EvidenceWorkspaceRail } from "./EvidenceWorkspaceRail";
import { LocaleProvider } from "../lib/i18n";
import { getChunkDetail, getDocumentChunks } from "../lib/api";
import { clearDocumentCache } from "../lib/documentCache";

vi.mock("../lib/api", () => ({ getApiBaseUrl: () => "http://localhost:8000", getChunkDetail: vi.fn(), getDocumentChunks: vi.fn() }));

const getChunkDetailMock = vi.mocked(getChunkDetail);
const getDocumentChunksMock = vi.mocked(getDocumentChunks);

describe("EvidenceWorkspaceRail", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    clearDocumentCache();
  });

  test("keeps the stored excerpt visible and offers retry when source loading fails", async () => {
    getChunkDetailMock.mockRejectedValueOnce(new TypeError("offline"));
    getChunkDetailMock.mockResolvedValueOnce({
      chunk_id: "chunk-1", document_id: "doc-1", ticker: "AAPL", section: "risk_factors", filing_date: null,
      accession_number: null, text_preview: "Stored excerpt", text_length: 15, source_url: null, text: "Full source text",
    });
    const onSelectIndex = vi.fn();

    render(<LocaleProvider><EvidenceWorkspaceRail sources={[{ citation: "AAPL 10-K", chunk_id: "chunk-1", score: 0.8, text_preview: "Stored excerpt" }]} selectedIndex={0} onSelectIndex={onSelectIndex} /></LocaleProvider>);

    expect(await screen.findByRole("alert")).toHaveTextContent("saved excerpt");
    expect(screen.getAllByText("Stored excerpt").length).toBeGreaterThan(1);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(screen.getByText("Full source text")).toBeInTheDocument());
  });

  test("shows a saved snapshot first and requires an explicit current-index access", () => {
    const onOpenCurrentSource = vi.fn();
    render(
      <LocaleProvider>
        <EvidenceWorkspaceRail
          sources={[{
            citation: "AAPL saved evidence",
            chunk_id: "chunk-1",
            text_preview: "Saved snapshot",
            text: "Saved snapshot captured earlier",
            stored_snapshot: { chunk_id: "chunk-1" },
          }]}
          selectedIndex={0}
          onSelectIndex={vi.fn()}
          onOpenCurrentSource={onOpenCurrentSource}
        />
      </LocaleProvider>,
    );

    expect(screen.getByText("Saved snapshot captured earlier")).toBeInTheDocument();
    expect(screen.getByText(/not replaced automatically/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Inspect current indexed excerpt" }));
    expect(onOpenCurrentSource).toHaveBeenCalledWith(expect.objectContaining({ chunk_id: "chunk-1", stored_snapshot: undefined }));
    expect(getChunkDetailMock).not.toHaveBeenCalled();
  });

  test("reports the original source index to the controlled evidence selection", () => {
    const onSelectIndex = vi.fn();
    render(
      <LocaleProvider>
        <EvidenceWorkspaceRail
          sources={[
            { citation: "AAPL 10-K p. 12", score: 0.8, text_preview: "First excerpt", text: "First source" },
            { citation: "AAPL 10-K p. 28", score: 0.7, text_preview: "Second excerpt", text: "Second source" },
          ]}
          selectedIndex={0}
          onSelectIndex={onSelectIndex}
        />
      </LocaleProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /AAPL 10-K p\. 28/i }));

    expect(onSelectIndex).toHaveBeenCalledWith(1);
  });

  test("shows an explicit unavailable state instead of substituting another source", () => {
    render(
      <LocaleProvider>
        <EvidenceWorkspaceRail sources={[]} selectedIndex={-1} unavailable onSelectIndex={vi.fn()} />
      </LocaleProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent("selected source is unavailable");
  });

  test("keeps reader state when the inspector moves from inline to drawer and exposes Close", async () => {
    getDocumentChunksMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 8 });
    const onClose = vi.fn();
    const source = { citation: "AAPL source", document_id: "doc-1", text_preview: "Excerpt" };
    const view = render(
      <LocaleProvider>
        <EvidenceWorkspaceRail
          sources={[source]}
          selectedIndex={0}
          onSelectIndex={vi.fn()}
          presentation="inline"
          onClose={onClose}
        />
      </LocaleProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Increase text size" }));
    fireEvent.change(screen.getByPlaceholderText("Search chunks…"), { target: { value: "risk" } });
    expect(screen.getByText("110%")).toBeInTheDocument();

    view.rerender(
      <LocaleProvider>
        <EvidenceWorkspaceRail
          sources={[source]}
          selectedIndex={0}
          onSelectIndex={vi.fn()}
          presentation="drawer"
          onClose={onClose}
        />
      </LocaleProvider>,
    );

    const dialog = await screen.findByRole("dialog", { name: "Evidence inspector" });
    expect(dialog).toBeVisible();
    expect(screen.getByDisplayValue("risk")).toBeInTheDocument();
    expect(screen.getByText("110%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close evidence inspector" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test("ignores a late reader response after the selected source changes", async () => {
    let resolveFirst: (value: { text: string }) => void = () => undefined;
    let resolveSecond: (value: { text: string }) => void = () => undefined;
    const first = new Promise<{ text: string }>((resolve) => { resolveFirst = resolve; });
    const second = new Promise<{ text: string }>((resolve) => { resolveSecond = resolve; });
    getChunkDetailMock.mockReturnValueOnce(first as ReturnType<typeof getChunkDetail>).mockReturnValueOnce(second as ReturnType<typeof getChunkDetail>);
    const { rerender } = render(
      <LocaleProvider>
        <EvidenceWorkspaceRail sources={[{ citation: "AAPL source 1", chunk_id: "chunk-1", text_preview: "Stored 1" }]} selectedIndex={0} onSelectIndex={vi.fn()} />
      </LocaleProvider>,
    );

    rerender(
      <LocaleProvider>
        <EvidenceWorkspaceRail sources={[{ citation: "AAPL source 2", chunk_id: "chunk-2", text_preview: "Stored 2" }]} selectedIndex={0} onSelectIndex={vi.fn()} />
      </LocaleProvider>,
    );
    await act(async () => { resolveFirst({ text: "Stale full source" }); });
    expect(screen.queryByText("Stale full source")).not.toBeInTheDocument();
    await act(async () => { resolveSecond({ text: "Current full source" }); });
    expect(await screen.findByText("Current full source")).toBeInTheDocument();
  });

  test("ignores a late neighbor response after the reader unmounts", async () => {
    let resolveNeighbor: (value: { text: string }) => void = () => undefined;
    const neighbor = new Promise<{ text: string }>((resolve) => { resolveNeighbor = resolve; });
    getChunkDetailMock
      .mockResolvedValueOnce({ text: "Current full source" } as never)
      .mockReturnValueOnce(neighbor as ReturnType<typeof getChunkDetail>);
    getDocumentChunksMock.mockResolvedValue({
      items: [{ chunk_id: "chunk-2", ticker: "AAPL", section: "risk_factors", filing_date: null, accession_number: null, chunk_index: 2, text_preview: "Neighbor excerpt", text_length: 15, source_url: null }],
      total: 1,
      page: 1,
      page_size: 8,
    });
    const view = render(
      <LocaleProvider>
        <EvidenceWorkspaceRail
          sources={[{ citation: "AAPL source", chunk_id: "chunk-1", document_id: "doc-1", text_preview: "Current excerpt" }]}
          selectedIndex={0}
          onSelectIndex={vi.fn()}
        />
      </LocaleProvider>,
    );

    fireEvent.click(await screen.findByRole("button", { name: /Neighbor excerpt/i }));
    view.unmount();
    await act(async () => { resolveNeighbor({ text: "Stale neighbor content" }); });
    expect(screen.queryByText("Stale neighbor content")).not.toBeInTheDocument();
  });

  test("renders indexed metadata, highlights the exact excerpt, and paginates document chunks", async () => {
    getChunkDetailMock.mockResolvedValue({
      chunk_id: "chunk-1", document_id: "doc-1", ticker: "AAPL", section: "risk_factors", filing_date: "2025-10-31",
      accession_number: "0001", text_preview: "Macro conditions", text_length: 45, source_url: "https://www.sec.gov/Archives/edgar/data/1/0001.htm", text: "Macro conditions may affect demand and supply.",
    });
    getDocumentChunksMock.mockResolvedValue({
      items: [
        { chunk_id: "chunk-1", ticker: "AAPL", section: "risk_factors", filing_date: "2025-10-31", accession_number: "0001", chunk_index: 1, text_preview: "Macro conditions", text_length: 15, source_url: "https://www.sec.gov/Archives/edgar/data/1/0001.htm" },
        { chunk_id: "chunk-2", ticker: "AAPL", section: "risk_factors", filing_date: "2025-10-31", accession_number: "0001", chunk_index: 2, text_preview: "Supply chain", text_length: 12, source_url: "https://www.sec.gov/Archives/edgar/data/1/0001.htm" },
      ],
      total: 16,
      page: 1,
      page_size: 8,
    });

    render(
      <LocaleProvider>
        <EvidenceWorkspaceRail
          sources={[{
            citation: "AAPL 2025 10-K · Risk Factors",
            chunk_id: "chunk-1",
            document_id: "doc-1",
            ticker: "AAPL",
            section: "risk_factors",
            source_url: "https://www.sec.gov/Archives/edgar/data/1/0001.htm",
            text_preview: "Macro conditions",
            text: "Macro conditions",
          }]}
          selectedIndex={0}
          onSelectIndex={vi.fn()}
        />
      </LocaleProvider>,
    );

    expect(await screen.findByText("Indexed excerpts")).toBeInTheDocument();
    expect(await screen.findByText(/may affect demand and supply/)).toBeInTheDocument();
    expect(document.querySelector("mark")).toHaveTextContent("Macro conditions");
    expect(screen.getByRole("link", { name: "Open SEC" })).toHaveAttribute("href", "https://www.sec.gov/Archives/edgar/data/1/0001.htm");
    expect(screen.getByText("1 / 2")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Search chunks…"), { target: { value: "supply" } });
    await waitFor(() => expect(getDocumentChunksMock).toHaveBeenLastCalledWith(
      "doc-1",
      { search: "supply", page: 1, page_size: 8 },
      expect.any(AbortSignal),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    await waitFor(() => expect(getDocumentChunksMock).toHaveBeenLastCalledWith(
      "doc-1",
      { search: "supply", page: 2, page_size: 8 },
      expect.any(AbortSignal),
    ));
  });

  test("keeps evidence panel width bounded and keyboard-resizable", () => {
    const onRailWidthChange = vi.fn();
    render(
      <LocaleProvider>
        <EvidenceWorkspaceRail
          sources={[{ citation: "AAPL source", score: 0.8, text_preview: "Excerpt" }]}
          selectedIndex={0}
          onSelectIndex={vi.fn()}
          railWidth={384}
          onRailWidthChange={onRailWidthChange}
        />
      </LocaleProvider>,
    );

    const separator = screen.getByRole("separator", { name: "Resize evidence panel" });
    expect(separator).toHaveAttribute("aria-valuemin", "360");
    expect(separator).toHaveAttribute("aria-valuemax", "560");
    fireEvent.keyDown(separator, { key: "ArrowLeft" });
    fireEvent.keyDown(separator, { key: "End" });
    expect(onRailWidthChange).toHaveBeenNthCalledWith(1, 400);
    expect(onRailWidthChange).toHaveBeenNthCalledWith(2, 560);
  });
});
