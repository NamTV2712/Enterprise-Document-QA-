import { describe, expect, test } from "vitest";
import { conversationToMarkdown } from "./conversationExport";
import { ConversationRecord } from "./conversationStore";

describe("conversation export", () => {
  test("exports readable evidence without session identifiers or technical details", () => {
    const conversation: ConversationRecord = {
      schemaVersion: 1,
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
});
