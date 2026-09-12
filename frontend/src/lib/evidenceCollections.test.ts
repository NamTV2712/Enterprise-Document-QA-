import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { createEvidenceCollection, exportEvidenceCollections, getEvidenceStorageStatus, importEvidenceCollections, listEvidenceCollections, mergeEvidenceCollections, preflightEvidenceCollectionsImport, saveEvidence, snapshotProvenanceFromSource, updateEvidenceNote } from "./evidenceCollections";

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

  test("migrates a readable v1 collection without inventing provenance", () => {
    localStorage.setItem("sec_qa_evidence_collections_v1", JSON.stringify([{
      id: "legacy-collection",
      name: "Legacy",
      items: [{ id: "legacy-item", citation: "AAPL 10-K", excerpt: "Legacy excerpt", ticker: "AAPL", savedAt: 10 }],
      createdAt: 10,
      updatedAt: 10,
    }]));

    const migrated = listEvidenceCollections();
    expect(migrated[0]).not.toHaveProperty("schemaVersion");
    expect(migrated[0].items[0]).toMatchObject({ citation: "AAPL 10-K", ticker: "AAPL" });
    expect(migrated[0].items[0]).not.toHaveProperty("documentRevision");

    saveEvidence(source);
    expect(JSON.parse(localStorage.getItem("sec_qa_evidence_collections_v2") ?? "[]")[0].schemaVersion).toBe(2);
    expect(localStorage.getItem("sec_qa_evidence_collections_v1")).toBeTruthy();
  });

  test("stores only supplied reader provenance and labels the item as a captured snapshot", () => {
    const collection = createEvidenceCollection("Provenance");
    saveEvidence(source, {
      collectionId: collection.id,
      provenance: { documentId: "AAPL:filing", documentRevision: "rev-1", locationStatus: "exact", coverageStatus: "complete", representation: "structured_html" },
    });
    expect(listEvidenceCollections()[0].items[0]).toMatchObject({
      documentId: "AAPL:filing",
      documentRevision: "rev-1",
      locationStatus: "exact",
      coverageStatus: "complete",
      representation: "structured_html",
      snapshotState: "captured",
    });
    expect(listEvidenceCollections()[0].items[0]).not.toHaveProperty("sourceSetRevision");
  });

  test("preserves transient reader identity facts when capturing a snapshot", () => {
    const collection = createEvidenceCollection("Reader snapshot");
    saveEvidence({
      ...source,
      stored_snapshot: {
        chunk_id: "chunk-1",
        document_revision: "doc-rev-2",
        source_set_revision: "set-rev-3",
        representation: "structured_html",
        coverage_status: "complete",
        location_status: "exact",
        snapshot_state: "captured",
      },
    }, { collectionId: collection.id, provenance: snapshotProvenanceFromSource({
      ...source,
      stored_snapshot: {
        chunk_id: "chunk-1",
        document_revision: "doc-rev-2",
        source_set_revision: "set-rev-3",
        representation: "structured_html",
        coverage_status: "complete",
        location_status: "exact",
        snapshot_state: "captured",
      },
    }) });

    expect(listEvidenceCollections()[0].items[0]).toMatchObject({
      documentRevision: "doc-rev-2",
      sourceSetRevision: "set-rev-3",
      representation: "structured_html",
      coverageStatus: "complete",
      locationStatus: "exact",
      snapshotState: "captured",
    });
  });

  test("does not infer a representation when the source has no stored reader representation", () => {
    expect(snapshotProvenanceFromSource(source)).not.toHaveProperty("representation");
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
