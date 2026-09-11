import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { StructuredDocumentReader } from "./StructuredDocumentReader";
import { LocaleProvider } from "../lib/i18n";
import { getReaderContent, getReaderLocation, getReaderManifest, getReaderOutline, getReaderSectionExportUrl, searchReader } from "../lib/api";

vi.mock("../lib/api", () => ({
  getReaderContent: vi.fn(),
  getReaderLocation: vi.fn(),
  getReaderManifest: vi.fn(),
  getReaderOutline: vi.fn(),
  getReaderSectionExportUrl: vi.fn(() => "http://localhost/structured-section.html"),
  searchReader: vi.fn(),
}));

const manifestMock = vi.mocked(getReaderManifest);
const outlineMock = vi.mocked(getReaderOutline);
const contentMock = vi.mocked(getReaderContent);
const locationMock = vi.mocked(getReaderLocation);
const searchMock = vi.mocked(searchReader);

const manifest = {
  schema_version: "sec-reader-v4" as const,
  document_id: "AAPL:0000320193-25-000079",
  status: "available" as const,
  reason_code: "available" as const,
  reason: null,
  identity: {
    ticker: "AAPL",
    cik: 320193,
    accession_number: "0000320193-25-000079",
    filing_date: "2025-10-31",
    report_date: "2025-09-27",
    status: "verified" as const,
    reason_code: "verified" as const,
  },
  source_set_revision: "set-1",
  sources: [{
    source_document_id: "source-1",
    role: "primary_filing" as const,
    label: "Primary filing",
    status: "available" as const,
    reason_code: "available" as const,
    reason: null,
    canonical_url: "https://www.sec.gov/Archives/fixture",
    media_type: "text/html" as const,
    document_revision: "doc-1",
    text_length: 120,
  }],
  representations: [
    { kind: "normalized_text" as const, status: "available" as const, reason_code: "available" as const, reason: null },
    { kind: "structured" as const, status: "available" as const, reason_code: "available" as const, reason: null },
    { kind: "pdf" as const, status: "unavailable" as const, reason_code: "pdf_representation_unavailable" as const, reason: "PDF is not available." },
  ],
};

describe("StructuredDocumentReader", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  test("renders semantic content and keeps literal search revision-bound", async () => {
    manifestMock.mockResolvedValue(manifest);
    outlineMock.mockResolvedValue({
      document_id: manifest.document_id,
      source_document_id: "source-1",
      source_set_revision: "set-1",
      document_revision: "doc-1",
      items: [{ block_id: "heading-1", label: "Risk factors", level: 1, anchor: "risk-factors" }],
      next_cursor: null,
      complete: true,
      limitations: [],
    });
    contentMock.mockResolvedValue({
      document_id: manifest.document_id,
      source_document_id: "source-1",
      source_set_revision: "set-1",
      document_revision: "doc-1",
      blocks: [
        { block_id: "heading-1", kind: "heading", text: "Risk factors", runs: [], level: 1, anchor: "risk-factors", items: [], caption: null, columns: [], rows: [] },
        { block_id: "paragraph-1", kind: "paragraph", text: "Competition remains intense.", runs: [{ text: "Competition remains intense.", emphasis: false, strong: false, superscript: false, subscript: false }], level: null, anchor: null, items: [], caption: null, columns: [], rows: [] },
        { block_id: "table-1", kind: "table", text: "", runs: [], level: null, anchor: null, items: [], caption: "Revenue", columns: ["Metric", "FY2025"], rows: [[{ text: "Total sales", rowspan: 1, colspan: 1, header: false }, { text: "416,161", rowspan: 1, colspan: 1, header: false }]] },
      ],
      previous_cursor: null,
      next_cursor: null,
      complete: true,
      limitations: [],
    });
    locationMock.mockResolvedValue({
      chunk_id: "chunk-1",
      chunk_text_hash: "1111111111111111111111111111111111111111111111111111111111111111",
      document_id: manifest.document_id,
      source_set_revision: "set-1",
      status: "exact",
      reason_code: "exact",
      reason: null,
      source_document_id: "source-1",
      document_revision: "doc-1",
      representation_revision: "structured-1",
      ranges: [{ block_id: "paragraph-1", block_index: 1, kind: "paragraph", start: 0, end: 11, method: "text_whitespace" }],
      match_count: 1,
      match_count_capped: false,
    });
    searchMock.mockResolvedValue({
      document_id: manifest.document_id,
      source_document_id: "source-1",
      source_set_revision: "set-1",
      document_revision: "doc-1",
      query: "competition",
      matches: [{ block_id: "paragraph-1", block_index: 1, start: 0, end: 11, quote: "Competition remains intense." }],
      total: 1,
      next_cursor: null,
      complete: true,
    });

    render(<LocaleProvider><StructuredDocumentReader documentId={manifest.document_id} indexedSource={{ citation: "AAPL source", text_preview: "Competition remains intense.", document_id: manifest.document_id, chunk_id: "chunk-1", chunk_text_hash: "1111111111111111111111111111111111111111111111111111111111111111" }} onBack={vi.fn()} /></LocaleProvider>);

    expect(await screen.findByText("Structured document", { exact: true })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Risk factors" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveTextContent("416,161");
    expect(await screen.findByText("Evidence correspondence verified in the structured document.", { exact: true })).toBeInTheDocument();
    expect(screen.getByRole("article")).toHaveTextContent("Competition remains intense.");
    fireEvent.change(screen.getByRole("textbox", { name: "Find in document" }), { target: { value: "competition" } });
    fireEvent.click(screen.getByRole("button", { name: "Find" }));
    await waitFor(() => expect(searchMock).toHaveBeenCalledWith(manifest.document_id, expect.objectContaining({ q: "competition", source_set_revision: "set-1", document_revision: "doc-1" }), expect.any(AbortSignal)));
    expect(screen.getByText("1 matches")).toBeInTheDocument();
  });
});
