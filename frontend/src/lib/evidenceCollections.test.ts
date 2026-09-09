import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { createEvidenceCollection, exportEvidenceCollections, importEvidenceCollections, listEvidenceCollections, saveEvidence } from "./evidenceCollections";

const source = { citation: "AAPL 10-K [Source 1]", text_preview: "Revenue excerpt", text: "Revenue excerpt", chunk_id: "chunk-1", ticker: "AAPL", section: "financial_table", filing_date: "2025-10-31", score: 1 };

describe("evidenceCollections", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  test("creates a local collection and deduplicates the same evidence", () => {
    const collection = createEvidenceCollection("Revenue review");
    saveEvidence(source, { collectionId: collection.id, messageId: "message-1" });
    saveEvidence(source, { collectionId: collection.id, messageId: "message-1" });

    expect(listEvidenceCollections()).toHaveLength(1);
    expect(listEvidenceCollections()[0].items).toHaveLength(1);
    expect(listEvidenceCollections()[0].items[0].citation).toContain("AAPL");
  });

  test("round-trips conversation and message provenance for saved evidence", () => {
    const collection = createEvidenceCollection("Audit evidence");
    saveEvidence(source, { collectionId: collection.id, conversationId: "conversation-1", messageId: "message-1" });
    const imported = importEvidenceCollections(exportEvidenceCollections());

    expect(imported[0].items[0]).toMatchObject({
      sourceConversationId: "conversation-1",
      sourceMessageId: "message-1",
    });
  });

  test("does not report a successful evidence save when storage rejects the write", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("quota exceeded", "QuotaExceededError");
    });

    expect(() => createEvidenceCollection("Unavailable")).toThrow("was not saved");
  });
});
