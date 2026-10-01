import { act, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { AnswerWorkspaceTarget, CatalogWorkspaceTarget, Source } from "../types";
import { bindSource, toDocumentLocationView } from "../lib/readerLocationView";
import { useWorkbenchController } from "./useWorkbenchController";

const source: Source = {
  citation: "AAPL source 1",
  text_preview: "Evidence excerpt",
  chunk_id: "chunk-1",
  chunk_text_hash: "hash-1",
  document_id: "document-1",
};

const target: AnswerWorkspaceTarget = {
  kind: "answer",
  selection: {
    conversationId: "conversation-1",
    messageId: "message-1",
    variantId: "variant-1",
    citationIndex: 0,
    chunkId: "chunk-1",
    documentId: "document-1",
    sourceKey: "chunk:chunk-1",
  },
  source,
};

const catalogTarget: CatalogWorkspaceTarget = {
  kind: "catalog",
  documentId: "document-2",
  initialTab: "metadata",
  returnView: "documents",
  returnFocusId: "document-2-row",
};

describe("useWorkbenchController", () => {
  test("coordinates presentation state without changing the identity-bearing target", () => {
    const { result } = renderHook(() => useWorkbenchController({
      initialTarget: target,
      initialLayoutMode: "context-dock",
      initialActivePane: "document",
      initialDocumentFindQuery: "risk",
    }));

    expect(result.current.state).toMatchObject({
      layoutMode: "context-dock",
      target,
      activePane: "document",
      documentFindQuery: "risk",
      activeRepresentation: "structured",
      sourceFilter: "all",
      documentContextTab: "evidence",
    });

    act(() => {
      result.current.setActivePane("sources");
      result.current.setSourceFilter("cited");
      result.current.setDocumentContextTab("metadata");
      result.current.setDocumentFindQuery("revenue");
      result.current.rememberFocus("citation-message-1-source-0");
      result.current.setRepresentation("normalized");
    });

    expect(result.current.state).toMatchObject({
      target,
      activePane: "sources",
      activeRepresentation: "normalized",
      sourceFilter: "cited",
      documentContextTab: "metadata",
      documentFindQuery: "revenue",
      focusReturnId: "citation-message-1-source-0",
      evidenceBinding: { state: "idle" },
    });
  });

  test("guards late source binding results by generation and keeps focus restoration explicit", () => {
    const { result } = renderHook(() => useWorkbenchController());
    const bound = bindSource(source);
    const location = toDocumentLocationView("structured", {
      chunk_id: "chunk-1",
      chunk_text_hash: "hash-1",
      document_id: "document-1",
      source_set_revision: "sources-1",
      status: "exact",
      reason_code: "exact",
      reason: null,
      source_document_id: "source-document-1",
      document_revision: "revision-1",
      representation_revision: "structured-1",
      ranges: [],
      match_count: 1,
      match_count_capped: false,
    });

    act(() => result.current.beginEvidenceResolution(7));
    act(() => result.current.resolveEvidence(6, bound, location));
    expect(result.current.state.evidenceBinding).toEqual({ state: "resolving", generation: 7 });

    act(() => result.current.resolveEvidence(7, bound, location));
    expect(result.current.state.evidenceBinding).toMatchObject({ state: "ready", source: bound, location });

    act(() => result.current.beginEvidenceResolution(8));
    act(() => result.current.rejectEvidence(7, "stale", "Late old response"));
    expect(result.current.state.evidenceBinding).toEqual({ state: "resolving", generation: 8 });
    act(() => result.current.rejectEvidence(8, "unavailable", "Reader unavailable"));
    expect(result.current.state.evidenceBinding).toEqual({ state: "unavailable", reason: "Reader unavailable" });

    act(() => result.current.rememberFocus(null));
    expect(result.current.state.focusReturnId).toBeNull();
  });

  test("resets reader-local presentation only when the opened document changes", () => {
    const { result } = renderHook(() => useWorkbenchController({ initialTarget: target }));

    act(() => {
      result.current.setRepresentation("pdf");
      result.current.setDocumentContextTab("notes");
      result.current.setDocumentFindQuery("risk factors");
      result.current.setTarget(catalogTarget);
    });

    expect(result.current.state).toMatchObject({
      target: catalogTarget,
      activeRepresentation: "structured",
      documentContextTab: "metadata",
      documentFindQuery: "",
    });

    act(() => {
      result.current.setRepresentation("normalized");
      result.current.setDocumentContextTab("evidence");
      result.current.setDocumentFindQuery("liquidity");
      // Route objects may be recreated during a responsive remount. This is
      // still the same document and must retain its reader-local state.
      result.current.setTarget({ ...catalogTarget, title: "Updated title" });
    });

    expect(result.current.state).toMatchObject({
      activeRepresentation: "normalized",
      documentContextTab: "evidence",
      documentFindQuery: "liquidity",
    });
  });

  test("clears a route document target without dereferencing the closed target", () => {
    const { result } = renderHook(() => useWorkbenchController({ initialTarget: catalogTarget }));

    act(() => result.current.setTarget(null));

    expect(result.current.state).toMatchObject({
      target: null,
      activeRepresentation: "structured",
      documentContextTab: "evidence",
      documentFindQuery: "",
    });
  });
});
