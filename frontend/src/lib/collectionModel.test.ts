import { describe, expect, test } from "vitest";

import { ApiError } from "./api";
import type { CollectionItemRecord, CollectionRecord, Source } from "../types";
import {
  collectionAccent,
  collectionItemKindLabel,
  activityEventLabel,
  collectionSubtitle,
  describeCollectionFailure,
  documentReference,
  evidenceReferenceFromSource,
  exportFileName,
  formatAbsoluteDate,
  formatRelativeTime,
  isWorkspaceAvailabilityFailure,
  itemCeilingNote,
  itemOpenTarget,
  itemProvenanceLine,
  listUnavailableFailure,
  memberCountLabel,
  privacySummary,
  snapshotFromSource,
  visibleTags,
  COLLECTION_ITEM_KINDS,
} from "./collectionModel";

const NOW = Date.parse("2026-09-22T12:00:00Z");

function collection(overrides: Partial<CollectionRecord> = {}): CollectionRecord {
  return {
    collection_id: "col-risk",
    name: "Risk review",
    description: "Q4 risk notes",
    tags: ["risk", "sec"],
    favorite: false,
    private: true,
    revision: 3,
    created_at: "2026-09-20T08:00:00Z",
    updated_at: "2026-09-22T09:00:00Z",
    item_count: 2,
    ...overrides,
  };
}

function item(overrides: Partial<CollectionItemRecord> = {}): CollectionItemRecord {
  return {
    item_id: "itm-1",
    collection_id: "col-risk",
    item_kind: "evidence",
    citation: "AAPL indexed excerpt · financial_statements",
    excerpt: "Total net sales were $391 billion.",
    reference: { document_id: "AAPL-2024", chunk_id: "AAPL_0", ticker: "AAPL", section: "financial_statements" },
    revision: 1,
    created_at: "2026-09-22T09:30:00Z",
    updated_at: "2026-09-22T09:30:00Z",
    ...overrides,
  };
}

describe("collection kinds and labels", () => {
  test("the four kinds are the DATA-003 contract and nothing else", () => {
    expect([...COLLECTION_ITEM_KINDS]).toEqual(["document", "evidence", "answer", "note"]);
  });

  test("kind and activity labels are bilingual", () => {
    expect(collectionItemKindLabel("document", false)).toBe("Document");
    expect(collectionItemKindLabel("document", true)).toBe("Tài liệu");
    expect(activityEventLabel("item_added", false)).toBe("Item added");
    expect(activityEventLabel("note_updated", true)).toBe("Đã sửa ghi chú");
    // An unknown event is echoed rather than invented.
    expect(activityEventLabel("something_new", false)).toBe("something_new");
  });

  test("counts are pluralised honestly in both locales", () => {
    expect(memberCountLabel(0, false)).toBe("0 items");
    expect(memberCountLabel(1, false)).toBe("1 item");
    expect(memberCountLabel(2, false)).toBe("2 items");
    expect(memberCountLabel(1, true)).toBe("1 mục");
  });
});

describe("failure mapping", () => {
  test("each DATA-003 status maps to its own state", () => {
    expect(describeCollectionFailure(new ApiError("gone", 410), false).kind).toBe("gone");
    expect(describeCollectionFailure(new ApiError("conflict", 409), false).kind).toBe("conflict");
    expect(describeCollectionFailure(new ApiError("refused", 422), false).kind).toBe("validation");
    expect(describeCollectionFailure(new ApiError("missing", 404), false).kind).toBe("not_found");
    expect(describeCollectionFailure(new ApiError("token", 401), false).kind).toBe("auth_required");
    expect(describeCollectionFailure(new ApiError("remote", 403), false).kind).toBe("restricted");
    expect(describeCollectionFailure(new ApiError("boom", 503), false).kind).toBe("server");
    expect(describeCollectionFailure(new Error("network"), false).kind).toBe("offline");
  });

  test("a conflict explains that the view is stale and keeps the server detail", () => {
    const failure = describeCollectionFailure(new ApiError("Collection revision is stale", 409), false);
    expect(failure.message).toContain("stale");
    expect(failure.detail).toBe("Collection revision is stale");
    expect(failure.status).toBe(409);
  });

  test("only boundary failures are page-level availability states", () => {
    expect(isWorkspaceAvailabilityFailure(listUnavailableFailure(false))).toBe(true);
    expect(isWorkspaceAvailabilityFailure(describeCollectionFailure(new ApiError("missing", 404), false))).toBe(false);
    expect(isWorkspaceAvailabilityFailure(describeCollectionFailure(new ApiError("conflict", 409), false))).toBe(false);
  });

  test("the unavailable state does not pretend the workspace is empty", () => {
    const failure = listUnavailableFailure(true);
    expect(failure.kind).toBe("unavailable");
    expect(failure.message).toContain("cục bộ");
  });
});

describe("presentation derivations", () => {
  test("relative time is honest about age and about missing timestamps", () => {
    expect(formatRelativeTime("2026-09-22T11:30:00Z", false, NOW)).toBe("30 minutes ago");
    expect(formatRelativeTime("2026-09-22T10:00:00Z", false, NOW)).toBe("2 hours ago");
    expect(formatRelativeTime("2026-09-20T12:00:00Z", false, NOW)).toBe("2 days ago");
    expect(formatRelativeTime("2025-01-05T12:00:00Z", false, NOW)).toBe(formatAbsoluteDate("2025-01-05T12:00:00Z", false));
    expect(formatRelativeTime(null, false, NOW)).toBeNull();
    expect(formatRelativeTime("not-a-date", true, NOW)).toBeNull();
  });

  test("the card subtitle never claims an update time the API did not report", () => {
    expect(collectionSubtitle(collection(), false, NOW)).toBe("Updated 3 hours ago");
    expect(collectionSubtitle(collection({ updated_at: "" }), false, NOW)).toBe("No update time recorded");
  });

  test("privacy restates the flag rather than inventing sharing", () => {
    expect(privacySummary(true, false)).toEqual({ label: "Private", detail: "Local workspace only" });
    expect(privacySummary(false, true)).toEqual({ label: "Không đặt riêng tư", detail: "Cờ riêng tư đang tắt" });
  });

  test("tags collapse into a +N chip and drop blanks", () => {
    expect(visibleTags(["a", "", "b", "c", "d"])).toEqual({ shown: ["a", "b", "c"], hiddenCount: 1 });
    expect(visibleTags(["a", "b"], 3)).toEqual({ shown: ["a", "b"], hiddenCount: 0 });
  });

  test("accents are deterministic per identity and bounded", () => {
    expect(collectionAccent("col-risk")).toBe(collectionAccent("col-risk"));
    expect(collectionAccent("col-risk")).toBeGreaterThanOrEqual(0);
    expect(collectionAccent("col-risk")).toBeLessThan(6);
  });

  test("the ceiling note only appears when the list is actually truncated", () => {
    expect(itemCeilingNote(3, 3, false)).toBeNull();
    expect(itemCeilingNote(2, 5, false)).toBe("Showing 2 of 5 items.");
    expect(itemCeilingNote(2, 5, true)).toBe("Đang hiển thị 2/5 mục.");
  });

  test("provenance lines only use fields the member carries", () => {
    expect(itemProvenanceLine(item(), false)).toBe("Apple Inc. (AAPL) · Financial Statements & Notes");
    const bare = item({ reference: {} });
    expect(itemProvenanceLine(bare, false)).toBe("");
  });

  test("export file names come from the collection identity", () => {
    expect(exportFileName(collection(), "json")).toBe("risk-review-col-risk.json");
    expect(exportFileName(collection({ name: "  " }), "markdown")).toBe("collection-col-risk.md");
  });
});

describe("member opening", () => {
  test("a document member opens by its canonical document_id", () => {
    const target = itemOpenTarget(
      item({
        item_kind: "document",
        reference: { document_id: "AAPL-2024", ticker: "AAPL", filing_date: "2025-10-31" },
      }),
      false,
    );
    expect(target.kind).toBe("document");
    if (target.kind !== "document") throw new Error("expected a document target");
    expect(target.documentId).toBe("AAPL-2024");
    expect(target.filingDate).toBe("2025-10-31");
  });

  test("a document member without an identity reports why it cannot open", () => {
    const target = itemOpenTarget(item({ item_kind: "document", reference: {} }), false);
    expect(target.kind).toBe("unavailable");
    if (target.kind !== "unavailable") throw new Error("expected an unavailable target");
    expect(target.reason).toContain("document_id");
  });

  test("an evidence member opens the stored snapshot without inventing fields", () => {
    const target = itemOpenTarget(
      item({
        reference: { document_id: "AAPL-2024", chunk_id: "AAPL_0", ticker: "AAPL", document_revision: "rev-7" },
        snapshot: { representation: "normalized_text", coverage_status: "exact" },
      }),
      false,
    );
    expect(target.kind).toBe("evidence");
    if (target.kind !== "evidence") throw new Error("expected an evidence target");
    expect(target.source.chunk_id).toBe("AAPL_0");
    expect(target.source.document_id).toBe("AAPL-2024");
    expect(target.source.stored_snapshot?.document_revision).toBe("rev-7");
    expect(target.source.stored_snapshot?.representation).toBe("normalized_text");
    // No score, rank or provider is ever fabricated for a stored member.
    expect(target.source.score).toBeUndefined();
    expect(target.source.rank).toBeUndefined();
  });

  test("an answer member opens its originating conversation message", () => {
    const target = itemOpenTarget(item({ item_kind: "answer", reference: { conversation_id: "c-1", message_id: "m-2" } }), false);
    expect(target).toEqual({ kind: "answer", conversationId: "c-1", messageId: "m-2" });
  });

  test("an answer member without conversation or message identity is unavailable", () => {
    const target = itemOpenTarget(item({ item_kind: "answer", reference: {} }), false);
    expect(target.kind).toBe("unavailable");
  });

  test("an evidence member with no identity at all is unavailable", () => {
    const target = itemOpenTarget(item({ reference: {} }), false);
    expect(target.kind).toBe("unavailable");
  });

  test("a note member points at the Notes tab instead of faking a reader", () => {
    const target = itemOpenTarget(item({ item_kind: "note", reference: {} }), false);
    expect(target.kind).toBe("unavailable");
    if (target.kind !== "unavailable") throw new Error("expected an unavailable target");
    expect(target.reason).toContain("Notes");
  });
});

describe("reference builders", () => {
  test("an evidence reference copies only identities the source carries", () => {
    const source: Source = {
      citation: "AAPL · financial_statements",
      text_preview: "preview",
      chunk_id: "AAPL_0",
      document_id: "AAPL-2024",
      ticker: "AAPL",
      section: "financial_statements",
      filing_date: "2025-10-31",
      chunk_text_hash: "hash-1",
      stored_snapshot: { chunk_id: "AAPL_0", document_revision: "rev-7", representation: "indexed_excerpt" },
    };
    const reference = evidenceReferenceFromSource(source);
    expect(reference.document_id).toBe("AAPL-2024");
    expect(reference.chunk_id).toBe("AAPL_0");
    expect(reference.document_revision).toBe("rev-7");
    expect(reference.representation).toBe("indexed_excerpt");
    expect(reference.chunk_text_hash).toBe("hash-1");
    // A source without an identity yields no identity key at all, so DATA-003
    // refuses it instead of the UI coercing one into existence.
    const empty = evidenceReferenceFromSource({ citation: "c", text_preview: "p" });
    expect(empty).toEqual({});
  });

  test("a document reference always carries the canonical identity", () => {
    expect(documentReference("AAPL-2024")).toEqual({ document_id: "AAPL-2024" });
    expect(documentReference("AAPL-2024", { ticker: "AAPL", filingDate: "2025-10-31" })).toEqual({
      document_id: "AAPL-2024",
      ticker: "AAPL",
      filing_date: "2025-10-31",
    });
  });

  test("a snapshot keeps the capture and never a retrieved score", () => {
    const snapshot = snapshotFromSource({
      citation: "c",
      text_preview: "p",
      chunk_id: "AAPL_0",
      document_id: "AAPL-2024",
      score: 0.87,
      rank: 2,
      stored_snapshot: { chunk_id: "AAPL_0", source_set_revision: "set-1" },
    });
    expect(snapshot).toEqual({
      document_id: "AAPL-2024",
      chunk_id: "AAPL_0",
      source_set_revision: "set-1",
    });
    expect(snapshotFromSource({ citation: "c", text_preview: "p" })).toBeNull();
  });
});
