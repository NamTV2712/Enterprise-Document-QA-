import { act, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { useEvidenceSelection } from "./useEvidenceSelection";
import { createEvidenceSelection } from "../lib/sourceIdentity";

describe("useEvidenceSelection", () => {
  test("clears a source selection when the conversation changes", () => {
    const { result, rerender } = renderHook(
      ({ conversationId }) => useEvidenceSelection(conversationId),
      { initialProps: { conversationId: "conversation-a" } },
    );

    act(() => {
      result.current[1](createEvidenceSelection(
        "conversation-a",
        "answer-a",
        0,
        { citation: "AAPL source", text_preview: "Excerpt", chunk_id: "chunk-1" },
      ));
    });
    expect(result.current[0]).toMatchObject({ conversationId: "conversation-a", messageId: "answer-a", citationIndex: 0, chunkId: "chunk-1" });

    rerender({ conversationId: "conversation-b" });
    expect(result.current[0]).toBeNull();
  });
});
