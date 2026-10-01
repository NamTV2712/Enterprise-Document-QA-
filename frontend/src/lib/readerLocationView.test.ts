import { describe, expect, test } from "vitest";
import type { EvidenceLocation, OriginalLocation, Source } from "../types";
import {
  bindSource,
  createResolvingEvidenceBinding,
  getDocumentLocationMessage,
  getDocumentLocationOffsets,
  getDocumentLocationStatus,
  isExactDocumentLocation,
  rejectEvidenceBinding,
  resolveEvidenceBinding,
  toDocumentLocationView,
  validateDocumentLocation,
} from "./readerLocationView";

const structuredLocation: EvidenceLocation = {
  chunk_id: "chunk-1",
  chunk_text_hash: "hash-1",
  document_id: "document-1",
  source_set_revision: "sources-1",
  status: "exact",
  reason_code: "exact",
  reason: null,
  source_document_id: "source-document-1",
  document_revision: "document-revision-1",
  representation_revision: "structured-revision-1",
  ranges: [{
    block_id: "block-1",
    block_index: 0,
    kind: "paragraph",
    start: 4,
    end: 12,
    method: "text_whitespace",
  }],
  match_count: 1,
  match_count_capped: false,
};

const normalizedLocation: OriginalLocation = {
  chunk_id: "chunk-1",
  chunk_text_hash: "hash-1",
  document_id: "document-1",
  source_set_revision: "sources-1",
  matcher_version: "matcher-1",
  status: "ambiguous",
  reason: "The indexed text occurs more than once.",
  match_count: 2,
  match_count_capped: true,
  location: null,
};

const source: Source = {
  citation: "AAPL source 1",
  text_preview: "Evidence excerpt",
  chunk_id: "chunk-1",
  chunk_text_hash: "hash-1",
  document_id: "document-1",
  stored_snapshot: {
    chunk_id: "chunk-1",
    document_revision: "document-revision-1",
    source_set_revision: "sources-1",
    representation: "structured_html",
  },
};

describe("representation-neutral reader locations", () => {
  test("retains the raw structured/normalized response and exposes status/offsets", () => {
    const structured = toDocumentLocationView("structured", structuredLocation);
    const normalized = toDocumentLocationView("normalized", normalizedLocation);

    expect(structured.raw).toBe(structuredLocation);
    expect(getDocumentLocationStatus(structured)).toBe("exact");
    expect(isExactDocumentLocation(structured)).toBe(true);
    expect(getDocumentLocationOffsets(structured)).toEqual({ start: 4, end: 12 });

    expect(normalized.raw).toBe(normalizedLocation);
    expect(getDocumentLocationStatus(normalized)).toBe("ambiguous");
    expect(isExactDocumentLocation(normalized)).toBe(false);
    expect(getDocumentLocationOffsets(normalized)).toBeNull();
  });

  test("binds only source facts already present and keeps missing identity null", () => {
    expect(bindSource(source)).toEqual({
      source,
      chunkId: "chunk-1",
      chunkTextHash: "hash-1",
      documentId: "document-1",
      sourceDocumentId: null,
      sourceSetRevision: "sources-1",
      documentRevision: "document-revision-1",
      representationRevision: null,
    });
  });

  test("accepts an exact location only when every identity and renderable range is present", () => {
    const view = toDocumentLocationView("structured", structuredLocation);
    expect(validateDocumentLocation(view, {
      documentId: "document-1",
      chunkId: "chunk-1",
      chunkTextHash: "hash-1",
      sourceSetRevision: "sources-1",
    })).toEqual({ ok: true, state: "ready", reason: null });

    expect(validateDocumentLocation(view, {
      documentId: "document-1",
      chunkId: "chunk-1",
      chunkTextHash: "different-hash",
      sourceSetRevision: "sources-1",
    })).toMatchObject({ ok: false, state: "stale" });

    expect(validateDocumentLocation(toDocumentLocationView("structured", {
      ...structuredLocation,
      ranges: [],
    }), {
      documentId: "document-1",
      chunkId: "chunk-1",
      chunkTextHash: "hash-1",
      sourceSetRevision: "sources-1",
    })).toMatchObject({ ok: false, state: "unavailable" });
  });

  test("validates normalized exact identity and provides non-empty status copy", () => {
    const exact: OriginalLocation = {
      ...normalizedLocation,
      status: "exact",
      reason: null,
      match_count: 1,
      location: {
        source_document_id: "source-document-1",
        document_revision: "document-revision-1",
        method: "full_text_whitespace",
        start: 4,
        end: 12,
      },
    };
    const view = toDocumentLocationView("normalized", exact);
    expect(validateDocumentLocation(view, {
      documentId: "document-1",
      chunkId: "chunk-1",
      chunkTextHash: "hash-1",
      sourceSetRevision: "sources-1",
      sourceDocumentId: "source-document-1",
      documentRevision: "document-revision-1",
    })).toEqual({ ok: true, state: "ready", reason: null });
    expect(getDocumentLocationMessage(toDocumentLocationView("normalized", normalizedLocation))).toContain("multiple locations");
  });

  test("ignores late location responses and preserves truthful stale/unavailable states", () => {
    const pending = createResolvingEvidenceBinding(2);
    const bound = bindSource(source);
    const ready = resolveEvidenceBinding(pending, 2, bound, toDocumentLocationView("structured", structuredLocation));
    expect(ready).toMatchObject({ state: "ready", source: bound, location: { representation: "structured" } });

    expect(resolveEvidenceBinding(pending, 1, bound)).toBe(pending);
    expect(rejectEvidenceBinding(pending, 1, "stale", "Old source revision")).toBe(pending);
    expect(rejectEvidenceBinding(pending, 2, "stale", "Old source revision")).toEqual({
      state: "stale",
      reason: "Old source revision",
    });

    const unavailable = createResolvingEvidenceBinding(3);
    expect(rejectEvidenceBinding(unavailable, 3, "unavailable", "Normalized text is unavailable")).toEqual({
      state: "unavailable",
      reason: "Normalized text is unavailable",
    });
  });
});
