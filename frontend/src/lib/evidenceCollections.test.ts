import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { createEvidenceCollection, exportEvidenceCollections, getEvidenceStorageStatus, importEvidenceCollections, listEvidenceCollections, mergeEvidenceCollections, preflightEvidenceCollectionsImport, saveEvidence, updateEvidenceNote } from "./evidenceCollections";

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

  test("fails closed and preserves malformed storage bytes", () => {
    const malformed = "{not-json";
    localStorage.setItem("sec_qa_evidence_collections_v1", malformed);

    expect(listEvidenceCollections()).toEqual([]);
    expect(getEvidenceStorageStatus()).toMatchObject({ readOnly: true });
    expect(() => createEvidenceCollection("Should not overwrite")).toThrow("left untouched");
    expect(localStorage.getItem("sec_qa_evidence_collections_v1")).toBe(malformed);
  });

  test("preserves changed snapshots and rejects an invalid collection id", () => {
    const collection = createEvidenceCollection("Versioned evidence");
    saveEvidence(source, { collectionId: collection.id });
    saveEvidence({ ...source, text: "Updated revenue excerpt", text_preview: "Updated revenue excerpt" }, { collectionId: collection.id });

    expect(listEvidenceCollections()[0].items).toHaveLength(2);
    expect(() => saveEvidence(source, { collectionId: "missing-collection" })).toThrow("does not exist");
  });

  test("stores an evidence note without changing the immutable snapshot lineage", () => {
    const collection = createEvidenceCollection("Noted evidence");
    saveEvidence(source, { collectionId: collection.id, conversationId: "conversation-1", messageId: "message-1" });
    const saved = listEvidenceCollections()[0].items[0];
    updateEvidenceNote(collection.id, saved.id, "Check this number against the filing.");

    expect(listEvidenceCollections()[0].items[0]).toMatchObject({
      excerpt: "Revenue excerpt",
      chunkId: "chunk-1",
      sourceConversationId: "conversation-1",
      sourceMessageId: "message-1",
      note: "Check this number against the filing.",
    });
  });

  test("rejects collection overflow without evicting existing collections", () => {
    const imported = Array.from({ length: 51 }, (_, index) => ({
      id: `collection-${index}`,
      name: `Collection ${index}`,
      items: [],
      createdAt: index + 1,
      updatedAt: index + 1,
    }));

    expect(() => mergeEvidenceCollections(imported)).toThrow("No collections were changed");
    expect(listEvidenceCollections()).toEqual([]);
  });

  test("preflights collection capacity before a multi-store backup import", () => {
    createEvidenceCollection("Existing");
    const imported = Array.from({ length: 50 }, (_, index) => ({
      id: `collection-${index}`,
      name: `Imported ${index}`,
      items: [],
      createdAt: index + 1,
      updatedAt: index + 1,
    }));

    expect(() => preflightEvidenceCollectionsImport(imported)).toThrow("No collections were changed");
    expect(listEvidenceCollections()).toHaveLength(1);
  });
});
