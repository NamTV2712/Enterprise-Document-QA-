import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { OriginalDocumentReader } from "./OriginalDocumentReader";
import { LocaleProvider } from "../lib/i18n";
import { getOriginalContent, getOriginalLocation, getOriginalManifest, searchOriginal } from "../lib/api";

vi.mock("../lib/api", () => ({
  getOriginalContent: vi.fn(),
  getOriginalLocation: vi.fn(),
  getOriginalManifest: vi.fn(),
  searchOriginal: vi.fn(),
}));

const manifestMock = vi.mocked(getOriginalManifest);
const contentMock = vi.mocked(getOriginalContent);
const locationMock = vi.mocked(getOriginalLocation);
const searchMock = vi.mocked(searchOriginal);

describe("OriginalDocumentReader", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  test("renders a bounded normalized window and literal search marks", async () => {
    locationMock.mockResolvedValue({ status: "not_found", reason: "Not found", match_count: 0, match_count_capped: false, location: null, chunk_id: "chunk-1", chunk_text_hash: "hash", document_id: "AAPL:0000320193-25-000079", source_set_revision: "set-1", matcher_version: "sec-viewer-location-v1" });
    manifestMock.mockResolvedValue({
      document_id: "AAPL:0000320193-25-000079",
      status: "available",
      reason: null,
      normalizer_version: "sec-viewer-text-v1",
      source_set_revision: "set-1",
      sources: [{ source_document_id: "source-1", role: "primary_filing", label: "Primary filing", status: "available", reason: null, document_revision: "doc-1", text_length: 30 }],
    });
    contentMock.mockResolvedValue({
      document_id: "AAPL:0000320193-25-000079", source_document_id: "source-1", source_set_revision: "set-1", document_revision: "doc-1",
      start: 0, end: 30, total_length: 30, previous_start: null, next_start: null,
      segments: [{ text: "Revenue ", evidence: false, search: false }, { text: "$100", evidence: false, search: true }],
    });
    searchMock.mockResolvedValue({
      document_id: "AAPL:0000320193-25-000079", source_document_id: "source-1", source_set_revision: "set-1", document_revision: "doc-1", query: "100",
      matches: [{ start: 8, end: 12, preview: "Revenue $100" }], next_cursor: null,
    });

    render(<LocaleProvider><OriginalDocumentReader documentId="AAPL:0000320193-25-000079" onBack={vi.fn()} /></LocaleProvider>);

    expect(await screen.findByText("Original source — normalized text")).toBeInTheDocument();
    expect(await screen.findByText("$100")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Find in original source" }), { target: { value: "100" } });
    fireEvent.click(screen.getByRole("button", { name: "Find" }));
    await waitFor(() => expect(searchMock).toHaveBeenCalledWith("AAPL:0000320193-25-000079", expect.objectContaining({ q: "100" }), expect.any(AbortSignal)));
  });

  test("keeps indexed fallback available when the original is unavailable", async () => {
    manifestMock.mockResolvedValue({
      document_id: "AAPL:missing", status: "unavailable", reason: "No usable local original source is available.", normalizer_version: "sec-viewer-text-v1", source_set_revision: "set-2", sources: [],
    });
    const onBack = vi.fn();
    render(<LocaleProvider><OriginalDocumentReader documentId="AAPL:missing" onBack={onBack} /></LocaleProvider>);

    expect(await screen.findByText(/indexed excerpt remains available/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back to indexed excerpt" }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  test("switches to the exact normalized source and preserves the evidence mark", async () => {
    manifestMock.mockResolvedValue({
      document_id: "AAPL:fixture",
      status: "available",
      reason: null,
      normalizer_version: "sec-viewer-text-v1",
      source_set_revision: "set-1",
      sources: [{ source_document_id: "source-1", role: "primary_filing", label: "Primary filing", status: "available", reason: null, document_revision: "doc-1", text_length: 40 }],
    });
    locationMock.mockResolvedValue({
      chunk_id: "chunk-1",
      chunk_text_hash: "hash-1",
      document_id: "AAPL:fixture",
      source_set_revision: "set-1",
      matcher_version: "sec-viewer-location-v1",
      status: "exact",
      reason: null,
      match_count: 1,
      match_count_capped: false,
      location: { source_document_id: "source-1", document_revision: "doc-1", method: "full_text_whitespace", start: 0, end: 8 },
    });
    contentMock.mockResolvedValue({
      document_id: "AAPL:fixture",
      source_document_id: "source-1",
      source_set_revision: "set-1",
      document_revision: "doc-1",
      start: 0,
      end: 8,
      total_length: 8,
      previous_start: null,
      next_start: null,
      segments: [{ text: "Risk text", evidence: true, search: false }],
    });
    const onLocationEvent = vi.fn();

    render(<LocaleProvider><OriginalDocumentReader documentId="AAPL:fixture" indexedSource={{ citation: "AAPL source", text_preview: "Risk text", document_id: "AAPL:fixture", chunk_id: "chunk-1", chunk_text_hash: "hash-1" }} onBack={vi.fn()} onLocationEvent={onLocationEvent} /></LocaleProvider>);

    expect(await screen.findByText("Evidence correspondence verified in this document representation.", { exact: true })).toBeInTheDocument();
    expect(document.querySelector(".original-reader__evidence-match")).toBeInTheDocument();
    expect(onLocationEvent).toHaveBeenCalledWith(expect.objectContaining({ state: "resolved" }));
  });

  test("shows a stale lookup error without clearing the selected reader context", async () => {
    manifestMock.mockResolvedValue({
      document_id: "AAPL:fixture",
      status: "available",
      reason: null,
      normalizer_version: "sec-viewer-text-v1",
      source_set_revision: "set-1",
      sources: [{ source_document_id: "source-1", role: "primary_filing", label: "Primary filing", status: "available", reason: null, document_revision: "doc-1", text_length: 40 }],
    });
    locationMock.mockRejectedValue({ status: 409, code: "source_changed", message: "The original source set changed." });
    contentMock.mockResolvedValue({
      document_id: "AAPL:fixture", source_document_id: "source-1", source_set_revision: "set-1", document_revision: "doc-1", start: 0, end: 8, total_length: 8, previous_start: null, next_start: null,
      segments: [{ text: "Risk text", evidence: false, search: false }],
    });
    const onLocationEvent = vi.fn();

    render(<LocaleProvider><OriginalDocumentReader documentId="AAPL:fixture" indexedSource={{ citation: "AAPL source", text_preview: "Risk text", document_id: "AAPL:fixture", chunk_id: "chunk-1", chunk_text_hash: "hash-1" }} onBack={vi.fn()} onLocationEvent={onLocationEvent} /></LocaleProvider>);

    expect(await screen.findByText("The source revision changed; the source remains selected but is not highlighted.", { exact: true })).toBeInTheDocument();
    expect(screen.getByText("Risk text")).toBeInTheDocument();
    expect(onLocationEvent).toHaveBeenCalledWith(expect.objectContaining({ state: "stale" }));
  });
});
