import { beforeEach, describe, expect, test } from "vitest";
import { createEvidenceCollection, listEvidenceCollections, saveEvidence } from "./evidenceCollections";

const source = { citation: "AAPL 10-K [Source 1]", text_preview: "Revenue excerpt", text: "Revenue excerpt", chunk_id: "chunk-1", ticker: "AAPL", section: "financial_table", filing_date: "2025-10-31", score: 1 };

describe("evidenceCollections", () => {
  beforeEach(() => localStorage.clear());

  test("creates a local collection and deduplicates the same evidence", () => {
    const collection = createEvidenceCollection("Revenue review");
    saveEvidence(source, { collectionId: collection.id, messageId: "message-1" });
    saveEvidence(source, { collectionId: collection.id, messageId: "message-1" });

    expect(listEvidenceCollections()).toHaveLength(1);
    expect(listEvidenceCollections()[0].items).toHaveLength(1);
    expect(listEvidenceCollections()[0].items[0].citation).toContain("AAPL");
  });
});
