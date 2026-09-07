import { describe, expect, test } from "vitest";
import {
  conversationToMarkdown,
  conversationsToJson,
  parseConversationBackup,
} from "./conversationExport";
import { ConversationRecord } from "./conversationStore";

describe("conversation export", () => {
  test("exports readable evidence without session identifiers or technical details", () => {
    const conversation: ConversationRecord = {
      schemaVersion: 2,
  titleMode: "auto",
  revision: 1,
      id: "conversation-secret-id",
      sessionId: "session-secret-id",
      title: "Revenue review",
      createdAt: 1,
      updatedAt: 1,
      draft: "",
      bookmarkedMessageIds: ["a-1"],
      messages: [
        { id: "u-1", sender: "user", text: "What was revenue?" },
        {
          id: "a-1",
          sender: "assistant",
          text: "Revenue was $100B [Source 1].",
          sources: [
            {
              citation: "MSFT 10-K, Financial Table",
              score: 0.92,
              text_preview: "Revenue was $100B.",
              text: "Revenue was $100B in FY2024.",
            },
          ],
        },
      ],
    };

    const markdown = conversationToMarkdown(conversation);

    expect(markdown).toContain("# Revenue review");
    expect(markdown).toContain("Revenue was $100B in FY2024.");
    expect(markdown).toContain("Rank score: 0.92");
    expect(markdown).not.toContain("session-secret-id");
    expect(markdown).not.toContain("conversation-secret-id");
    expect(markdown).not.toContain("Technical details");
  });

  test("round-trips a backup with fresh local identities", () => {
    const conversation: ConversationRecord = {
      schemaVersion: 2,
      titleMode: "custom",
      revision: 4,
      id: "conversation-original",
      sessionId: "session-original",
      title: "Revenue review",
      createdAt: 1,
      updatedAt: 2,
      draft: "follow up",
      bookmarkedMessageIds: ["a-1"],
      messages: [
        { id: "u-1", sender: "user", text: "What was revenue?" },
        { id: "a-1", sender: "assistant", text: "Revenue was $100B." },
      ],
    };

    const imported = parseConversationBackup(conversationsToJson([conversation]));

    expect(imported).toHaveLength(1);
    expect(imported[0].id).not.toBe(conversation.id);
    expect(imported[0].sessionId).not.toBe(conversation.sessionId);
    expect(imported[0].title).toBe(conversation.title);
    expect(imported[0].bookmarkedMessageIds).toEqual(["a-1"]);
  });

  test("rejects an unsupported or malformed backup", () => {
    expect(() => parseConversationBackup(JSON.stringify({ format: "other", version: 1 }))).toThrow(
      "not supported",
    );
    expect(() => parseConversationBackup(JSON.stringify({
      format: "enterprise-document-qa.conversations",
      version: 1,
      exportedAt: new Date().toISOString(),
      conversations: [{ title: "broken", messages: [{ sender: "robot" }] }],
    }))).toThrow("invalid conversation");
  });
});
