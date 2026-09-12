import { describe, expect, test } from "vitest";
import { ConversationRecord } from "./conversationStore";
import { searchConversationRecords } from "./conversationSearch";

function fixture(): ConversationRecord[] {
  return Array.from({ length: 100 }, (_, conversationIndex) => ({
    schemaVersion: 4,
    id: `conversation-${conversationIndex}`,
    sessionId: `session-${conversationIndex}`,
    title: `Research conversation ${conversationIndex}`,
    titleMode: "auto" as const,
    revision: 1,
    createdAt: conversationIndex,
    updatedAt: conversationIndex,
    draft: "",
    tags: conversationIndex === 73 ? ["cybersecurity", "risk-review"] : ["revenue"],
    notes: [],
    variants: [],
    bookmarkedMessageIds: [],
    messages: Array.from({ length: 100 }, (_, messageIndex) => ({
      id: `message-${conversationIndex}-${messageIndex}`,
      sender: "user" as const,
      text: `Question ${messageIndex} about annual filing evidence`,
    })),
  }));
}

describe("conversation Library search", () => {
  test("searches tags and accentless Vietnamese text", () => {
    const records = fixture();
    records[73].messages[0].text = "Rủi ro an ninh mạng của Microsoft";
    expect(searchConversationRecords(records, "cybersecurity").map((item) => item.id)).toEqual(["conversation-73"]);
    expect(searchConversationRecords(records, "rui ro").map((item) => item.id)).toEqual(["conversation-73"]);
  });

  test("keeps the warmed 100x100 search operation below the product budget", () => {
    const records = fixture();
    for (let index = 0; index < 10; index += 1) searchConversationRecords(records, "filing evidence");
    const samples: number[] = [];
    for (let index = 0; index < 100; index += 1) {
      const start = performance.now();
      expect(searchConversationRecords(records, index % 2 ? "revenue" : "filing evidence").length).toBeGreaterThan(0);
      samples.push(performance.now() - start);
    }
    samples.sort((a, b) => a - b);
    const p95 = samples[Math.ceil(samples.length * 0.95) - 1];
    expect(p95).toBeLessThan(200);
  });
});
