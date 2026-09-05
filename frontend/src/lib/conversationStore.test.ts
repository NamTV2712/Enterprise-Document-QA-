import { beforeEach, describe, expect, test } from "vitest";
import { Message } from "../types";
import {
  createConversationRecord,
  loadConversationLibrary,
  saveConversationRecord,
} from "./conversationStore";

const messages: Message[] = [
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
];

describe("conversationStore", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("migrates legacy messages into the versioned browser library", async () => {
    localStorage.setItem("sec_qa_session_id", "legacy-session");
    localStorage.setItem("sec_qa_messages", JSON.stringify(messages));

    const state = await loadConversationLibrary(
      "legacy-session",
      "conversation-legacy-session",
    );

    expect(state.storageMode).toBe("localstorage");
    expect(state.conversations).toHaveLength(1);
    expect(state.conversations[0].messages).toEqual(messages);
    expect(localStorage.getItem("sec_qa_conversations_migrated_v1")).toBe("done");
    expect(localStorage.getItem("sec_qa_conversations_v1")).toContain("legacy-session");
  });

  test("preserves source metadata, draft, title, and bookmarks across reload", async () => {
    await loadConversationLibrary("session-1", "conversation-session-1");
    const record = createConversationRecord(
      "conversation-session-1",
      "session-1",
      messages,
      "Follow up",
      ["a-1"],
      100,
    );
    await saveConversationRecord(record);

    const state = await loadConversationLibrary("session-1", "conversation-session-1");

    expect(state.conversations[0]).toMatchObject({
      id: "conversation-session-1",
      title: "What was revenue?",
      draft: "Follow up",
      bookmarkedMessageIds: ["a-1"],
    });
    expect(state.conversations[0].messages[1].sources?.[0].text).toBe(
      "Revenue was $100B in FY2024.",
    );
  });
});
