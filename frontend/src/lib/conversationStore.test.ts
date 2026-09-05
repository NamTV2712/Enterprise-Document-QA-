import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IDBFactory } from "fake-indexeddb";
import type { MockInstance } from "vitest";
import { Message } from "../types";

type StoreModule = typeof import("./conversationStore");

const V1_KEY = "sec_qa_conversations_v1";
const V2_KEY = "sec_qa_conversations_v2";
const LEGACY_MESSAGES_KEY = "sec_qa_messages";
const MIGRATION_KEY = "sec_qa_conversations_migrated_v1";
const DB_NAME = "enterprise-document-qa";

async function freshStore(): Promise<StoreModule> {
  vi.resetModules();
  return import("./conversationStore");
}

function userMessage(id: string, text: string): Message {
  return { id, sender: "user", text };
}

function assistantMessage(id: string, text: string, extra: Partial<Message> = {}): Message {
  return { id, sender: "assistant", text, ...extra };
}

function seedLocal(records: unknown[], key = V2_KEY): void {
  window.localStorage.setItem(key, JSON.stringify(records));
}

function seedV1Record(record: Record<string, unknown>): void {
  window.localStorage.setItem(V1_KEY, JSON.stringify([record]));
}

function makeRecord(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    schemaVersion: 2,
    id: "conversation-a",
    sessionId: "session-a",
    title: "First question",
    titleMode: "auto",
    revision: 3,
    createdAt: 1_000,
    updatedAt: 2_000,
    messages: [userMessage("u1", "First question")],
    draft: "",
    bookmarkedMessageIds: [],
    ...overrides,
  };
}

async function openDb(): Promise<IDBDatabase> {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DB_NAME);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function breakIdbTransactions(db: IDBDatabase): MockInstance {
  return vi.spyOn(Object.getPrototypeOf(db), "transaction").mockImplementation(() => {
    throw new DOMException("connection closed", "InvalidStateError");
  });
}

function breakLocalStorageWrites(): MockInstance {
  return vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new DOMException("quota exceeded", "QuotaExceededError");
  });
}

describe("conversation store repository", () => {
  beforeEach(() => {
    window.localStorage.clear();
    globalThis.indexedDB = new IDBFactory() as unknown as IDBFactory;
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("keeps a custom title when autosave rebuilds the record from messages", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-live", "conversation-live");
    const created = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
      assistantMessage("a1", "Apple reported total revenue of $391,035 million."),
    ]);
    await store.saveConversationRecord(created);

    // The user renamed the conversation; autosave later rebuilds the record
    // from the message list and must not resurrect the generated title.
    const renamed = { ...created, title: "FY2024 revenue research", titleMode: "custom" as const };
    const rebuilt = store.buildConversationRecord(renamed, {
      id: created.id,
      sessionId: created.sessionId,
      messages: [
        ...created.messages,
        assistantMessage("a2", "Revenue grew year over year.", { status: "completed" }),
      ],
      draft: "",
      bookmarkedMessageIds: created.bookmarkedMessageIds,
      createdAt: created.createdAt,
    });
    const result = await store.saveConversationRecord(rebuilt);

    expect(result.status).toBe("persisted");
    const reloaded = await store.loadConversationLibrary(created.sessionId, created.id);
    const saved = reloaded.conversations.find((record) => record.id === created.id);
    expect(saved?.title).toBe("FY2024 revenue research");
    expect(saved?.titleMode).toBe("custom");
  });

  it("keeps the auto title until the conversation is renamed", async () => {
    const store = await freshStore();
    const created = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
    ]);
    const rebuilt = store.buildConversationRecord(created, {
      id: created.id,
      sessionId: created.sessionId,
      messages: [userMessage("u1", "Apple total revenue"), assistantMessage("a1", "Answer")],
      draft: "",
      bookmarkedMessageIds: [],
      createdAt: created.createdAt,
    });
    expect(rebuilt.title).toBe("Apple total revenue");
    expect(rebuilt.titleMode).toBe("auto");
  });

  it("preserves source metadata, draft, bookmarks, and request snapshots across reload", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-1", "conversation-session-1");
    const record = store.createConversationRecord(
      "conversation-session-1",
      "session-1",
      [
        userMessage("u-1", "What was revenue?"),
        assistantMessage("a-1", "Revenue was $100B [Source 1].", {
          sources: [
            {
              citation: "MSFT 10-K, Financial Table",
              score: 0.92,
              text_preview: "Revenue was $100B.",
              text: "Revenue was $100B in FY2024.",
            },
          ],
        }),
      ],
      "Follow up",
      ["a-1"],
      100,
    );
    await store.saveConversationRecord(record);

    const state = await store.loadConversationLibrary("session-1", "conversation-session-1");
    const saved = state.conversations[0];
    expect(saved).toMatchObject({
      id: "conversation-session-1",
      title: "What was revenue?",
      draft: "Follow up",
      bookmarkedMessageIds: ["a-1"],
    });
    expect(saved.messages[1].sources?.[0].text).toBe("Revenue was $100B in FY2024.");
  });

  it("merges localStorage fallback records when IndexedDB becomes available again", async () => {
    seedLocal([makeRecord({ id: "conversation-fallback", sessionId: "session-old", revision: 2 })]);
    const { store, state } = await freshStore().then((store) =>
      store.loadConversationLibrary().then((state) => ({ store, state })),
    );
    expect(state.storageMode).toBe("indexeddb");
    expect(state.conversations.map((record) => record.id)).toContain("conversation-fallback");
    expect(store.listConversations().map((record) => record.id)).toContain("conversation-fallback");
  });

  it("merges a version-1 payload and preserves a renamed title as custom", async () => {
    seedV1Record({
      schemaVersion: 1,
      id: "conversation-legacy",
      sessionId: "session-legacy",
      title: "My renamed research",
      createdAt: 500,
      updatedAt: 900,
      messages: [userMessage("u1", "Microsoft risk factors")],
      draft: "",
      bookmarkedMessageIds: ["a1"],
    });
    const store = await freshStore();
    const state = await store.loadConversationLibrary("session-legacy", "conversation-legacy");
    const record = state.conversations.find((item) => item.id === "conversation-legacy");
    expect(record).toBeDefined();
    expect(record?.schemaVersion).toBe(2);
    expect(record?.titleMode).toBe("custom");
    expect(record?.title).toBe("My renamed research");
    expect(record?.bookmarkedMessageIds).toEqual(["a1"]);
  });

  it("imports the legacy single-conversation payload once with a stable id", async () => {
    window.localStorage.setItem(
      LEGACY_MESSAGES_KEY,
      JSON.stringify([userMessage("u1", "Apple risk factors"), assistantMessage("a1", "Risks")]),
    );
    const firstStore = await freshStore();
    const first = await firstStore.loadConversationLibrary("session-legacy", "conversation-legacy");
    expect(first.conversations.map((record) => record.id)).toContain("conversation-legacy");
    expect(window.localStorage.getItem(MIGRATION_KEY)).toBe("done");

    const secondStore = await freshStore();
    const second = await secondStore.loadConversationLibrary("session-legacy", "conversation-legacy");
    const matches = second.conversations.filter((record) => record.id === "conversation-legacy");
    expect(matches).toHaveLength(1);
  });

  it("marks legacy migration complete only after a durable write", async () => {
    window.localStorage.setItem(
      LEGACY_MESSAGES_KEY,
      JSON.stringify([userMessage("u1", "Apple risk factors")]),
    );
    // Break both durable backends before the first load.
    const db = await openDb();
    breakIdbTransactions(db);
    breakLocalStorageWrites();

    const store = await freshStore();
    const state = await store.loadConversationLibrary("session-legacy", "conversation-legacy");
    expect(state.storageMode).toBe("memory");
    expect(state.conversations.some((record) => record.id === "conversation-legacy")).toBe(true);
    // The legacy payload stays unmarked so the next load can retry migration.
    expect(window.localStorage.getItem(MIGRATION_KEY)).toBeNull();
  });

  it("tombstones survive a stale fallback copy so deleted conversations stay deleted", async () => {
    seedLocal([makeRecord({ id: "conversation-gone", sessionId: "session-x", revision: 5 })]);
    const store = await freshStore();
    await store.loadConversationLibrary();
    const result = await store.deleteConversationRecord("conversation-gone");
    expect(result.status).toBe("persisted");

    // Simulate a stale localStorage copy reappearing from old fallback data.
    seedLocal([makeRecord({ id: "conversation-gone", sessionId: "session-x", revision: 5 })]);
    const reloaded = await freshStore().then((store) => store.loadConversationLibrary());
    expect(reloaded.conversations.some((record) => record.id === "conversation-gone")).toBe(false);
  });

  it("reports deletion as not durable when every backend write fails", async () => {
    seedLocal([makeRecord({ id: "conversation-stuck", sessionId: "session-x", revision: 2 })]);
    const db = await openDb();
    const transactionSpy = breakIdbTransactions(db);

    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.storageMode).toBe("localstorage");
    transactionSpy.mockRestore();

    const setItemSpy = breakLocalStorageWrites();
    const result = await store.deleteConversationRecord("conversation-stuck");
    expect(result.status).not.toBe("persisted");
    // The item stays in the Library so the user can retry the deletion.
    expect(store.listConversations().some((record) => record.id === "conversation-stuck")).toBe(true);
    setItemSpy.mockRestore();
  });

  it("does not silently drop conversations at the 100-conversation limit", async () => {
    const existing = Array.from({ length: 100 }, (_, index) =>
      makeRecord({
        id: `conversation-${index}`,
        sessionId: `session-${index}`,
        updatedAt: 1_000 + index,
        revision: 1,
      }),
    );
    seedLocal(existing);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.conversations).toHaveLength(100);

    const overflow = store.createConversationRecord("conversation-overflow", "session-overflow", [
      userMessage("u1", "One more question"),
    ]);
    const result = await store.saveConversationRecord(overflow);
    expect(result.status).toBe("volatile");
    expect(result.warning).toContain("100");

    // Nothing was dropped: all 100 durable conversations remain, and the
    // overflow copy stays usable inside this tab.
    expect(store.listConversations()).toHaveLength(101);
    const reloaded = await store.loadConversationLibrary();
    expect(reloaded.conversations).toHaveLength(100);
    expect(reloaded.conversations.some((record) => record.id === "conversation-overflow")).toBe(false);
  });

  it("keeps an oversized legacy library readable instead of trimming it", async () => {
    const oversized = Array.from({ length: 130 }, (_, index) =>
      makeRecord({
        id: `conversation-${index}`,
        sessionId: `session-${index}`,
        updatedAt: 1_000 + index,
      }),
    );
    seedLocal(oversized);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.conversations).toHaveLength(130);
    expect(state.storageMode).not.toBe("memory");
  });

  it("reports persisted and volatile write outcomes", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-live", "conversation-live");
    const record = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
    ]);
    const persisted = await store.saveConversationRecord(record);
    expect(persisted.status).toBe("persisted");
    expect(persisted.storageMode).toBe("indexeddb");

    // Force every durable write to fail: the record stays in memory and the
    // result says so instead of claiming "Saved".
    const db = await openDb();
    const transactionSpy = breakIdbTransactions(db);
    const setItemSpy = breakLocalStorageWrites();

    const updated = store.buildConversationRecord(
      store.listConversations().find((item) => item.id === record.id) ?? null,
      {
        id: record.id,
        sessionId: record.sessionId,
        messages: [...record.messages, assistantMessage("a1", "Answer")],
        draft: "draft text",
        bookmarkedMessageIds: [],
        createdAt: record.createdAt,
      },
    );
    const volatile = await store.saveConversationRecord(updated);
    expect(volatile.status).toBe("volatile");
    expect(volatile.warning).toBeTruthy();

    setItemSpy.mockRestore();
    transactionSpy.mockRestore();
  });

  it("does not erase loaded records when the active backend fails mid-session", async () => {
    seedLocal([makeRecord({ id: "conversation-seeded", sessionId: "session-seeded", revision: 1 })]);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.conversations).toHaveLength(1);

    const db = await openDb();
    const transactionSpy = breakIdbTransactions(db);
    const setItemSpy = breakLocalStorageWrites();

    const record = store.createConversationRecord("conversation-new", "session-new", [
      userMessage("u1", "New question"),
    ]);
    const result = await store.saveConversationRecord(record);
    expect(result.status).toBe("volatile");

    // Previously loaded records are still present in the in-memory snapshot.
    const ids = store.listConversations().map((item) => item.id);
    expect(ids).toContain("conversation-seeded");
    expect(ids).toContain("conversation-new");
    setItemSpy.mockRestore();
    transactionSpy.mockRestore();
  });

  it("keeps corrupt browser data untouched and warns instead of wiping the library", async () => {
    const corrupt = "{not valid json";
    window.localStorage.setItem(V2_KEY, corrupt);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.warning).toContain("could not be read");
    // The original bytes are still there for recovery tooling.
    expect(window.localStorage.getItem(V2_KEY)).toBe(corrupt);
  });

  it("opens a newer-schema IndexedDB read-only with a warning and preserves its data", async () => {
    // Simulate a future schema by creating the database at version 3.
    const advanced = await new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 3);
      request.onupgradeneeded = () => {
        request.result.createObjectStore("conversations", { keyPath: "id" });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    await new Promise<void>((resolve, reject) => {
      const tx = advanced.transaction("conversations", "readwrite");
      tx.objectStore("conversations").put(makeRecord({ id: "conversation-future" }));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    advanced.close();

    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.storageMode).not.toBe("indexeddb");
    expect(state.warning).toContain("newer");
    expect(state.conversations.some((record) => record.id === "conversation-future")).toBe(false);

    // The future database was not touched.
    const reopened = await openDbVersion3();
    expect(reopened).toBe(true);

    async function openDbVersion3(): Promise<boolean> {
      return new Promise<boolean>((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, 3);
        request.onsuccess = () => {
          const tx = request.result.transaction("conversations", "readonly");
          const getAll = tx.objectStore("conversations").getAll();
          getAll.onsuccess = () => {
            request.result.close();
            resolve((getAll.result as unknown[]).some((item) => (item as { id: string }).id === "conversation-future"));
          };
          getAll.onerror = () => reject(getAll.error);
        };
        request.onerror = () => reject(request.error);
      });
    }
  });

  it("normalizes a persisted streaming message into a stopped answer", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-live", "conversation-live");
    const record = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
      assistantMessage("a1", "Apple reported total", {
        isStreaming: true,
        status: "streaming",
      }),
    ]);
    await store.saveConversationRecord(record);
    const saved = store.listConversations().find((item) => item.id === record.id);
    expect(saved?.messages[1].isStreaming).toBe(false);
    expect(saved?.messages[1].status).toBe("stopped");
    expect(saved?.messages[1].text).toBe("Apple reported total");

    const reloaded = await store.loadConversationLibrary(record.sessionId, record.id);
    const reloadedRecord = reloaded.conversations.find((item) => item.id === record.id);
    expect(reloadedRecord?.messages[1].status).toBe("stopped");
  });

  it("resolves conflicting copies with equal revision and updatedAt into a recovery entry", async () => {
    seedLocal([
      makeRecord({ revision: 4, updatedAt: 5_000 }),
      makeRecord({ revision: 4, updatedAt: 5_000, draft: "different draft" }),
    ]);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    const primary = state.conversations.find((record) => record.id === "conversation-a");
    const recovery = state.conversations.find((record) => record.id === "conversation-a#recovered");
    expect(primary).toBeDefined();
    expect(recovery).toBeDefined();
    expect(recovery?.draft).toBe("different draft");
    expect(state.warning).toContain("recovered");
  });

  it("removes a conversation from every backend when deletion succeeds", async () => {
    seedLocal([makeRecord({ id: "conversation-both", sessionId: "session-both", revision: 2 })]);
    const store = await freshStore();
    await store.loadConversationLibrary();
    const result = await store.deleteConversationRecord("conversation-both");
    expect(result.status).toBe("persisted");
    expect(store.listConversations().some((record) => record.id === "conversation-both")).toBe(false);

    const reloaded = await store.loadConversationLibrary();
    expect(reloaded.conversations.some((record) => record.id === "conversation-both")).toBe(false);
    expect(window.localStorage.getItem(V2_KEY)).not.toContain("conversation-both");
  });
});
