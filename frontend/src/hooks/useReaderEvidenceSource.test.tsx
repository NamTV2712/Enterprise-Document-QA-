import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { Source } from "../types";
import { getCachedChunkDetail } from "../lib/documentCache";
import { useReaderEvidenceSource } from "./useReaderEvidenceSource";

vi.mock("../lib/documentCache", () => ({
  getCachedChunkDetail: vi.fn(),
}));

const detailMock = vi.mocked(getCachedChunkDetail);

describe("useReaderEvidenceSource", () => {
  afterEach(() => vi.clearAllMocks());

  test("resolves a live chunk hash before a reader location request", async () => {
    detailMock.mockResolvedValue({
      chunk_id: "chunk-1",
      document_id: "document-1",
      ticker: "AAPL",
      section: "Risk Factors",
      filing_date: "2025-10-31",
      accession_number: "accession-1",
      text_preview: "Risk text",
      text_length: 9,
      source_url: null,
      text: "Risk text",
      chunk_text_hash: "hash-1",
    });
    const source: Source = { citation: "AAPL source", text_preview: "Risk text", chunk_id: "chunk-1", document_id: "document-1" };

    const { result } = renderHook(() => useReaderEvidenceSource("document-1", source));

    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(result.current.source?.chunk_text_hash).toBe("hash-1");
    expect(detailMock).toHaveBeenCalledWith("chunk-1", expect.any(AbortSignal));
  });

  test("does not rebind a saved snapshot without an exact hash", async () => {
    const source: Source = {
      citation: "Saved source",
      text_preview: "Historical text",
      chunk_id: "chunk-1",
      document_id: "document-1",
      stored_snapshot: { chunk_id: "chunk-1", snapshot_state: "captured" },
    };

    const { result } = renderHook(() => useReaderEvidenceSource("document-1", source));

    await waitFor(() => expect(result.current.state).toBe("unavailable"));
    expect(detailMock).not.toHaveBeenCalled();
    expect(result.current.source).toBe(source);
  });
});
