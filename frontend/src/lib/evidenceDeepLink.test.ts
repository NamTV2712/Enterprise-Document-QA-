import { describe, expect, test } from "vitest";
import {
  buildEvidenceDeepLink,
  buildEvidenceDeepLinkForSelection,
  evidenceDeepLinkFromSelection,
  parseEvidenceDeepLink,
} from "./evidenceDeepLink";

describe("evidence deep links", () => {
  test("parses the legacy message/citation hash without inventing variant identity", () => {
    expect(parseEvidenceDeepLink("#evidence=assistant-answer-0")).toEqual({
      messageId: "assistant-answer",
      citationIndex: 0,
      variantId: null,
      conversationId: null,
      sourceKey: null,
    });
  });

  test("round-trips variant, conversation, and source identity in the V5 form", () => {
    const hash = buildEvidenceDeepLink({
      messageId: "assistant/answer 7",
      citationIndex: 12,
      variantId: "variant/2",
      conversationId: "conversation A",
      sourceKey: "chunk:abc|document:def",
    });

    expect(hash).toContain("#evidence=assistant%2Fanswer%207-12?");
    expect(parseEvidenceDeepLink(hash!)).toEqual({
      messageId: "assistant/answer 7",
      citationIndex: 12,
      variantId: "variant/2",
      conversationId: "conversation A",
      sourceKey: "chunk:abc|document:def",
    });
  });

  test("accepts short query aliases from early copied V5 links", () => {
    expect(parseEvidenceDeepLink(
      "#evidence=assistant-1-2?conversation=conversation-1&variant=variant-3&source=chunk%3A4",
    )).toMatchObject({
      messageId: "assistant-1",
      citationIndex: 2,
      conversationId: "conversation-1",
      variantId: "variant-3",
      sourceKey: "chunk:4",
    });
  });

  test("preserves exact selection identity when building a link", () => {
    const selection = {
      conversationId: "conversation-1",
      messageId: "message-1",
      variantId: "variant-1",
      citationIndex: 0,
      sourceKey: "chunk:1",
      chunkId: "chunk-1",
      documentId: "document-1",
    } as const;

    expect(evidenceDeepLinkFromSelection(selection)).toEqual({
      messageId: "message-1",
      citationIndex: 0,
      variantId: "variant-1",
      conversationId: "conversation-1",
      sourceKey: "chunk:1",
    });
    expect(parseEvidenceDeepLink(buildEvidenceDeepLinkForSelection(selection)!))
      .toMatchObject({ messageId: "message-1", citationIndex: 0, variantId: "variant-1" });
  });

  test("rejects malformed hashes and invalid builder inputs", () => {
    expect(parseEvidenceDeepLink("#evidence=message-no-index")).toBeNull();
    expect(parseEvidenceDeepLink("#evidence=%E0%A4%A-0")).toBeNull();
    expect(buildEvidenceDeepLink({ messageId: "", citationIndex: 0 })).toBeNull();
    expect(buildEvidenceDeepLink({ messageId: "message", citationIndex: -1 })).toBeNull();
    expect(buildEvidenceDeepLink({ messageId: "message", citationIndex: Number.MAX_SAFE_INTEGER + 1 })).toBeNull();
  });
});
