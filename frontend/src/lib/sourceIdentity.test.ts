import { describe, expect, test } from "vitest";
import { Source } from "../types";
import { createEvidenceSelection, getSourceKey, sourceMatchesSelection } from "./sourceIdentity";

const source = (overrides: Partial<Source> = {}): Source => ({
  citation: "AAPL 2025 10-K · Risk Factors",
  text_preview: "Stored excerpt",
  chunk_id: "chunk-1",
  document_id: "doc-1",
  ticker: "AAPL",
  section: "item_1a",
  filing_date: "2025-10-31",
  ...overrides,
});

describe("source identity", () => {
  test("prefers chunk identity over mutable display metadata", () => {
    expect(getSourceKey(source())).toBe("chunk:chunk-1");
    expect(getSourceKey(source({ citation: "A different display label" }))).toBe("chunk:chunk-1");
  });

  test("falls back to document metadata and then stored excerpt identity", () => {
    expect(getSourceKey(source({ chunk_id: null }))).toContain("document|doc-1");
    const legacy = source({ chunk_id: null, document_id: null });
    expect(getSourceKey(legacy)).toContain("excerpt|");
    expect(getSourceKey(legacy)).not.toBe(getSourceKey({ ...legacy, text_preview: "A different excerpt" }));
  });

  test("requires the exact citation slot and identity, never a neighboring source", () => {
    const selected = source();
    const selection = createEvidenceSelection("conversation-1", "message-1", 1, selected, "variant-1");

    expect(sourceMatchesSelection(selected, selection, 1)).toBe(true);
    expect(sourceMatchesSelection(selected, selection, 0)).toBe(false);
    expect(sourceMatchesSelection(source({ chunk_id: "chunk-2" }), selection, 1)).toBe(false);
  });
});
