import { describe, expect, test } from "vitest";
import type { Message } from "../types";
import { createConversationRecord, normalizeStoredMessages } from "./conversationStore";
import { conversationToMarkdown, conversationsToJson, parseConversationBackup } from "./conversationExport";
import { createWorkspaceBackup } from "./workspaceBackup";

const reference: Message = { id: "a", sender: "assistant", text: "", assistantExecution: { kind: "agent_research", runId: "agent_alpha", createdAt: 1000 } };
describe("conversation Agent reference boundary", () => {
  test("keeps legacy Quick text, sources, partial status and request snapshots", () => {
    const quick: Message = { id: "q", sender: "assistant", text: "Partial [Source 1]", isStreaming: true, sources: [{ citation: "AAPL", text_preview: "Revenue", score: -2 }], requestSnapshot: { ticker: "AAPL", section: null, topK: 5, enableComparative: true, answerLanguage: "vi" } };
    expect(normalizeStoredMessages([quick])[0]).toMatchObject({ text: quick.text, status: "stopped", sources: quick.sources, requestSnapshot: quick.requestSnapshot });
  });
  test("projects only identity/kind/run ID/time, excluding private payloads and synthetic credentials", () => {
    const poisoned = { ...reference, text: "cached answer", token: "synthetic-secret", state: "succeeded", result: { answer: "hidden" }, events: ["hidden"], execution: { token: "synthetic-secret" }, assistantExecution: { ...reference.assistantExecution, revision: 9, evaluation: "hidden" } };
    expect(normalizeStoredMessages([poisoned as unknown as Message])).toEqual([reference]);
  });
  test.each(["../escape", "https://example.invalid", "agent_", "agent_a/b", "agent_" + "a".repeat(123)])("rejects malformed durable identity %s", (runId) => {
    expect(normalizeStoredMessages([{ ...reference, assistantExecution: { kind: "agent_research", runId, createdAt: 1000 } }])).toEqual([]);
  });
  test("rejects unknown kinds instead of treating them as Quick answers", () => {
    expect(normalizeStoredMessages([{ ...reference, text: "should not become Quick", assistantExecution: { kind: "unknown" } } as unknown as Message])).toEqual([]);
  });
  test("exports a reference and explicit reconnect instruction, never cached results", () => {
    const record = createConversationRecord("conversation-a", "session-a", [{ id: "u", sender: "user", text: "Review filing risks" }, { ...reference, text: "cached private answer", token: "synthetic-secret" } as Message]);
    expect(record.schemaVersion).toBe(5);
    const markdown = conversationToMarkdown(record);
    expect(markdown).toContain("agent_alpha"); expect(markdown).toContain("Reconnect");
    const json = conversationsToJson([record], []);
    expect(json).not.toMatch(/cached private answer|synthetic-secret/);
    const imported = parseConversationBackup(json);
    expect(imported[0].messages[1].assistantExecution).toEqual(reference.assistantExecution);
  });
  test("workspace transfer backup projects the same safe reference", async () => {
    const record = createConversationRecord("conversation-a", "session-a", [reference]);
    record.messages[0] = { ...reference, text: "cached private answer", result: "synthetic-secret" } as Message;
    const backup = await createWorkspaceBackup({ conversations: [record], tombstones: [], collections: [], favoriteCollectionIds: [] });
    expect(backup.conversations[0].payload.messages).toEqual([reference]);
  });
});
