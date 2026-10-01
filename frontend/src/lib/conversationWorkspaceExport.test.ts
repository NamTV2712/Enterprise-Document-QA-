import { beforeEach, describe, expect, test, vi } from "vitest";
import { IDBFactory } from "fake-indexeddb";

const KEY = "sec_qa_library_v3";

describe("conversation workspace export snapshot", () => {
  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
    Object.defineProperty(globalThis, "indexedDB", { configurable: true, value: new IDBFactory() });
  });

  test("exports the loaded v4 record and tombstone without mutating browser bytes", async () => {
    const envelope = {
      envelopeVersion: 4,
      records: [{
        schemaVersion: 4,
        id: "conversation-live",
        sessionId: "session-live",
        title: "Loaded record",
        titleMode: "auto",
        revision: 2,
        createdAt: 100,
        updatedAt: 200,
        messages: [{ id: "question-1", sender: "user", text: "Question" }],
        draft: "",
        bookmarkedMessageIds: [],
        notes: [],
        variants: [],
      }],
      tombstones: [{ id: "conversation-deleted", revision: 3, deletedAt: 300 }],
    };
    localStorage.setItem(KEY, JSON.stringify(envelope));
    const store = await import("./conversationStore");
    await store.loadConversationLibrary();
    const before = localStorage.getItem(KEY);

    const snapshot = store.exportConversationWorkspaceSnapshot();

    expect(snapshot.conversations.map((record) => record.id)).toContain("conversation-live");
    expect(snapshot.tombstones).toContainEqual({ id: "conversation-deleted", revision: 3, deletedAt: 300 });
    expect(localStorage.getItem(KEY)).toBe(before);
  });

  test("requires explicit Library loading instead of triggering migration", async () => {
    const store = await import("./conversationStore");
    expect(() => store.exportConversationWorkspaceSnapshot()).toThrow("must be loaded");
    expect(localStorage.length).toBe(0);
  });
});
