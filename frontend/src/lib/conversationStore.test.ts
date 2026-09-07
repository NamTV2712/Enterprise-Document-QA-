import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IDBFactory } from "fake-indexeddb";
import type { MockInstance } from "vitest";
import { Message } from "../types";
import type { ConversationRecord } from "./conversationStore";

type StoreModule = typeof import("./conversationStore");

const V1_KEY = "sec_qa_conversations_v1";
const V2_KEY = "sec_qa_conversations_v2";
const V3_KEY = "sec_qa_library_v3";
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

function seedLocal(records: unknown[], key = V3_KEY, extra?: Record<string, unknown>): void {
  const envelope = { envelopeVersion: 3, records, tombstones: [], ...extra };
  window.localStorage.setItem(key, JSON.stringify(envelope));
}

function seedRaw(key: string, raw: string): void {
  window.localStorage.setItem(key, raw);
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

function longConversation(id: string, messageCount: number): Record<string, unknown> {
  const messages: Message[] = [];
  for (let index = 0; index < messageCount; index += 1) {
    messages.push(userMessage(`u-${index}`, `Question ${index}?`));
    messages.push(
      assistantMessage(`a-${index}`, `Answer ${index} with citation [Source 1].`, {
        sources: [
          {
            citation: `AAPL 10-K (filed 2025-10-31), Section: Risk Factors excerpt ${index}`,
            score: 0.5,
            text_preview: `Preview ${index}`,
            text: `Full evidence text for exchange ${index}.`,
          },
        ],
      }),
    );
  }
  return makeRecord({
    id,
    sessionId: `session-${id}`,
    title: `Conversation ${id}`,
    messages,
    bookmarkedMessageIds: ["a-0", `a-${messageCount - 1}`],
  });
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

function breakIndexedDbEntirely(): void {
  // The module reads the global at open time; a clean undefined keeps the
  // deterministic "IndexedDB is unavailable" path without touching
  // fake-indexeddb internals.
  (globalThis as { indexedDB?: unknown }).indexedDB = undefined;
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

  // --- Title and metadata preservation -----------------------------------

  it("keeps a custom title when autosave rebuilds the record from messages", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-live", "conversation-live");
    const created = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
      assistantMessage("a1", "Apple reported total revenue of $391,035 million."),
    ]);
    await store.saveConversationRecord(created);

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

  // --- M1-A: unreadable data protection ----------------------------------

  it("keeps corrupt localStorage bytes untouched across later operations and keeps the warning", async () => {
    const corrupt = '{"envelopeVersion":3,"records":[{"id":"x"';
    seedRaw(V3_KEY, corrupt);
    breakIndexedDbEntirely();
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.warning).toContain("could not be read");
    expect(window.localStorage.getItem(V3_KEY)).toBe(corrupt);

    // A save of a different conversation must not overwrite the unreadable
    // payload, must not clear the warning, and cannot persist anywhere in
    // this test because IndexedDB is unavailable too.
    const record = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
    ]);
    const result = await store.saveConversationRecord(record);
    expect(result.status).toBe("volatile");
    expect(window.localStorage.getItem(V3_KEY)).toBe(corrupt);
    expect(store.getStorageStatus().warning).toContain("could not be read");

    // Deleting an unrelated record loaded from the untouched v2 backup
    // still works: the tombstone is durable in IndexedDB, which
    // permanently suppresses the legacy-only copy. The corrupt payload
    // bytes are never rewritten and the sticky warning remains.
    seedRaw(
      V2_KEY,
      JSON.stringify([makeRecord({ id: "conversation-old", sessionId: "session-old" })]),
    );
    const reload = await store.loadConversationLibrary();
    expect(reload.conversations.some((item) => item.id === "conversation-old")).toBe(true);
    const deletion = await store.deleteConversationRecord("conversation-old");
    // No writable backend means the tombstone cannot become durable yet, so
    // the deletion is reported as not complete and the corrupt bytes stay.
    expect(deletion.status).toBe("volatile");
    expect(deletion.warning).toContain("Deletion pending");
    expect(window.localStorage.getItem(V3_KEY)).toBe(corrupt);
    expect(store.getStorageStatus().warning).toContain("could not be read");
  });

  it("locks localStorage writes when it holds a future-schema record and preserves the payload", async () => {
    seedLocal([makeRecord({ id: "conversation-now", schemaVersion: 5, revision: 9 })]);
    const rawBefore = window.localStorage.getItem(V3_KEY);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.warning).toContain("newer");
    expect(state.conversations.some((item) => item.id === "conversation-now")).toBe(false);

    const record = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
    ]);
    const result = await store.saveConversationRecord(record);
    // IndexedDB is still writable, so the save persists there.
    expect(result.status).toBe("persisted");
    expect(result.storageMode).toBe("indexeddb");
    // The future-schema payload was never rewritten.
    expect(window.localStorage.getItem(V3_KEY)).toBe(rawBefore);
    expect(store.getStorageStatus().warning).toContain("newer");
  });

  it("locks IndexedDB writes when it holds a future-schema record and preserves its data", async () => {
    const db = await new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 2);
      request.onupgradeneeded = () => {
        request.result.createObjectStore("conversations", { keyPath: "id" });
        request.result.createObjectStore("tombstones", { keyPath: "id" });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(["conversations", "tombstones"], "readwrite");
      tx.objectStore("conversations").put(
        makeRecord({ id: "conversation-future", schemaVersion: 5, revision: 9 }),
      );
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();

    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.warning).toContain("newer");

    const record = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
    ]);
    const result = await store.saveConversationRecord(record);
    expect(result.status).toBe("persisted");
    expect(result.storageMode).toBe("localstorage");

    // The future record still exists inside IndexedDB, untouched.
    const reopened = await openDb();
    const stored = await new Promise<unknown[]>((resolve, reject) => {
      const tx = reopened.transaction("conversations", "readonly");
      const request = tx.objectStore("conversations").getAll();
      request.onsuccess = () => resolve(request.result as unknown[]);
      request.onerror = () => reject(request.error);
    });
    reopened.close();
    expect(
      stored.some((item) => (item as { id: string }).id === "conversation-future"),
    ).toBe(true);
    expect(store.getStorageStatus().warning).toContain("newer");
  });

  it("does not mark legacy migration complete when the durable write fails", async () => {
    window.localStorage.setItem(
      LEGACY_MESSAGES_KEY,
      JSON.stringify([userMessage("u1", "Apple risk factors")]),
    );
    breakIndexedDbEntirely();
    breakLocalStorageWrites();

    const store = await freshStore();
    const state = await store.loadConversationLibrary("session-legacy", "conversation-legacy");
    expect(state.storageMode).toBe("memory");
    expect(state.conversations.some((record) => record.id === "conversation-legacy")).toBe(true);
    expect(window.localStorage.getItem(MIGRATION_KEY)).toBeNull();
  });

  // --- M1-B: no silent history truncation --------------------------------

  it("keeps 202 and 500 message conversations intact through save and reload", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-big", "conversation-big");
    for (const count of [202, 500]) {
      const id = `conversation-big-${count}`;
      const record = store.createConversationRecord(id, `session-big-${count}`, []);
      const built = store.buildConversationRecord(record, {
        id,
        sessionId: `session-big-${count}`,
        messages: longConversation(id, count).messages as Message[],
        draft: "",
        bookmarkedMessageIds: ["a-0", `a-${count - 1}`],
        createdAt: 1,
      });
      const result = await store.saveConversationRecord(built);
      expect(result.status).toBe("persisted");
    }

    const reloaded = await store.loadConversationLibrary();
    for (const count of [202, 500]) {
      const saved = reloaded.conversations.find((item) => item.id === `conversation-big-${count}`);
      expect(saved?.messages).toHaveLength(count * 2);
      expect(saved?.messages[0]).toMatchObject({ id: "u-0", text: "Question 0?" });
      const lastMessage = saved?.messages[(saved?.messages.length ?? 0) - 1];
      expect(lastMessage?.text).toContain(`Answer ${count - 1} with citation [Source 1].`);
      expect(lastMessage?.sources?.[0]?.text).toContain(
        `Full evidence text for exchange ${count - 1}.`,
      );
      expect(saved?.messages[1].sources?.[0].text).toContain("exchange 0");
      expect(saved?.bookmarkedMessageIds).toEqual(["a-0", `a-${count - 1}`]);
    }
  });

  it("preserves full history through the v1 migration path", async () => {
    const big = longConversation("conversation-legacy-big", 250);
    window.localStorage.setItem(
      V1_KEY,
      JSON.stringify([{ ...big, schemaVersion: 1, revision: undefined }]),
    );
    const store = await freshStore();
    const state = await store.loadConversationLibrary(
      "session-conversation-legacy-big",
      "conversation-legacy-big",
    );
    const saved = state.conversations.find((item) => item.id === "conversation-legacy-big");
    expect(saved?.messages).toHaveLength(500);
    expect(saved?.messages[0].id).toBe("u-0");
    expect(saved?.messages[499].id).toBe("a-249");
    expect(saved?.bookmarkedMessageIds).toEqual(["a-0", "a-249"]);
  });

  it("normalizes only streaming messages and never rewrites completed ones", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-live", "conversation-live");
    const record = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Apple total revenue"),
      assistantMessage("a1", "Completed answer", { status: "completed" }),
      assistantMessage("a2", "Partial streaming text", {
        isStreaming: true,
        status: "streaming",
      }),
    ]);
    await store.saveConversationRecord(record);
    const saved = store.listConversations().find((item) => item.id === record.id);
    expect(saved?.messages[1]).toMatchObject({ text: "Completed answer", status: "completed" });
    expect(saved?.messages[2]).toMatchObject({ text: "Partial streaming text", status: "stopped" });
    expect(saved?.messages).toHaveLength(3);
  });

  // --- M1-C: durable tombstone deletion ----------------------------------

  it("keeps a deleted conversation deleted when a stale fallback copy reappears", async () => {
    seedLocal([makeRecord({ id: "conversation-gone", sessionId: "session-x", revision: 5 })]);
    const store = await freshStore();
    await store.loadConversationLibrary();
    const result = await store.deleteConversationRecord("conversation-gone");
    expect(result.status).toBe("persisted");

    // A stale pre-delete fallback copy resurfaces: the durable tombstone
    // keeps it suppressed as deletion-pending, never resurrected normally.
    seedLocal([makeRecord({ id: "conversation-gone", sessionId: "session-x", revision: 5 })]);
    const reloaded = await store.loadConversationLibrary();
    const revived = reloaded.conversations.find((record) => record.id === "conversation-gone");
    expect(revived?.deletionPending).toBe(true);

    // Retrying the deletion clears it again once backends accept the write.
    const retry = await store.deleteConversationRecord("conversation-gone");
    expect(retry.status).toBe("persisted");
    const afterRetry = await store.loadConversationLibrary();
    expect(afterRetry.conversations.some((record) => record.id === "conversation-gone")).toBe(false);
  });

  it("reports deletion as pending when IndexedDB succeeds but localStorage fails", async () => {
    seedLocal([makeRecord({ id: "conversation-partial", sessionId: "session-x", revision: 2 })]);
    const store = await freshStore();
    await store.loadConversationLibrary();

    const setItemSpy = breakLocalStorageWrites();
    const result = await store.deleteConversationRecord("conversation-partial");
    setItemSpy.mockRestore();

    expect(result.status).toBe("volatile");
    expect(result.warning).toContain("Deletion pending");
    const pending = store
      .listConversations()
      .find((record) => record.id === "conversation-partial");
    expect(pending?.deletionPending).toBe(true);

    // Retry after storage recovers completes the deletion.
    const retry = await store.deleteConversationRecord("conversation-partial");
    expect(retry.status).toBe("persisted");
    expect(store.listConversations().some((record) => record.id === "conversation-partial")).toBe(false);
    const reloaded = await store.loadConversationLibrary();
    expect(reloaded.conversations.some((record) => record.id === "conversation-partial")).toBe(false);
  });

  it("reports deletion as pending when localStorage succeeds but IndexedDB fails", async () => {
    seedLocal([makeRecord({ id: "conversation-partial-2", sessionId: "session-x", revision: 2 })]);
    const store = await freshStore();
    await store.loadConversationLibrary();

    const db = await openDb();
    const transactionSpy = breakIdbTransactions(db);
    const result = await store.deleteConversationRecord("conversation-partial-2");
    transactionSpy.mockRestore();

    expect(result.status).toBe("volatile");
    expect(result.warning).toContain("Deletion pending");
    const pending = store
      .listConversations()
      .find((record) => record.id === "conversation-partial-2");
    expect(pending?.deletionPending).toBe(true);

    // After reload, the durable tombstone from localStorage still marks the
    // IndexedDB copy as pending, never as a normal conversation.
    const reloaded = await store.loadConversationLibrary();
    const revived = reloaded.conversations.find((record) => record.id === "conversation-partial-2");
    expect(revived?.deletionPending).toBe(true);
  });

  it("does not report success when a deletion write fails in both backends", async () => {
    seedLocal([makeRecord({ id: "conversation-abort", sessionId: "session-x", revision: 2 })]);
    const store = await freshStore();
    await store.loadConversationLibrary();

    const db = await openDb();
    const transactionSpy = breakIdbTransactions(db);
    const setItemSpy = breakLocalStorageWrites();
    const result = await store.deleteConversationRecord("conversation-abort");
    setItemSpy.mockRestore();
    transactionSpy.mockRestore();

    expect(result.status).toBe("volatile");
    expect(result.warning).not.toContain("removed");
    const stillThere = store
      .listConversations()
      .find((record) => record.id === "conversation-abort");
    expect(stillThere).toBeDefined();
    expect(stillThere?.deletionPending).toBeFalsy();
  });

  it("keeps a recovered copy when its base conversation is deleted", async () => {
    seedLocal([
      makeRecord({ revision: 4, updatedAt: 5_000 }),
      makeRecord({ revision: 4, updatedAt: 5_000, draft: "different draft" }),
    ]);
    const store = await freshStore();
    await store.loadConversationLibrary();
    const result = await store.deleteConversationRecord("conversation-a");
    expect(result.status).toBe("persisted");

    const reloaded = await store.loadConversationLibrary();
    expect(reloaded.conversations.some((record) => record.id === "conversation-a")).toBe(false);
    const recovery = reloaded.conversations.find(
      (record) => record.id === "conversation-a#recovered",
    );
    expect(recovery).toBeDefined();
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
    const envelope = JSON.parse(window.localStorage.getItem(V3_KEY) ?? "{}");
    expect(
      (envelope.records as { id: string }[]).some((record) => record.id === "conversation-both"),
    ).toBe(false);
    expect(
      (envelope.tombstones as { id: string }[]).some((tombstone) => tombstone.id === "conversation-both"),
    ).toBe(true);
  });

  it("deletes memory-only conversations for this tab as volatile", async () => {
    breakIndexedDbEntirely();
    const store = await freshStore();
    const setItemSpy = breakLocalStorageWrites();
    const state = await store.loadConversationLibrary();
    expect(state.storageMode).toBe("memory");

    // Saves stay volatile while storage is unavailable, and the deletion of
    // a memory-only record works for this tab without a durable tombstone.
    const record = store.createConversationRecord("conversation-mem", "session-mem", [
      userMessage("u1", "Only in memory"),
    ]);
    const saved = await store.saveConversationRecord(record);
    expect(saved.status).toBe("volatile");
    const result = await store.deleteConversationRecord("conversation-mem");
    expect(result.status).toBe("volatile");
    expect(result.warning).toContain("this tab only");
    expect(store.listConversations().some((item) => item.id === "conversation-mem")).toBe(false);
    setItemSpy.mockRestore();
  });

  // --- M1-D: admission limits on every write ------------------------------

  it("keeps the 101st conversation volatile until space is freed, then admits it on retry", async () => {
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
    const first = await store.saveConversationRecord(overflow);
    expect(first.status).toBe("volatile");
    expect(first.warning).toContain("100");
    expect(store.listConversations()).toHaveLength(101);
    // Repeated autosaves of the same pending record stay volatile.
    const again = await store.saveConversationRecord({ ...overflow, revision: 2 });
    expect(again.status).toBe("volatile");
    const reloaded = await store.loadConversationLibrary();
    expect(reloaded.conversations).toHaveLength(100);

    // Free one slot, retry, and the pending record is admitted.
    await store.deleteConversationRecord("conversation-0");
    const retry = await store.saveConversationRecord({ ...overflow, revision: 3 });
    expect(retry.status).toBe("persisted");
    const afterRetry = await store.loadConversationLibrary();
    expect(
      afterRetry.conversations.some((record) => record.id === "conversation-overflow"),
    ).toBe(true);
  });

  it("never admits pending records through other conversations' autosaves", async () => {
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
    await store.loadConversationLibrary();

    const overflow = store.createConversationRecord("conversation-overflow", "session-overflow", [
      userMessage("u1", "Pending question"),
    ]);
    await store.saveConversationRecord(overflow);

    // Another conversation's autosave must persist only durable records and
    // its own change, never the pending one.
    const other = store.buildConversationRecord(
      store.listConversations().find((item) => item.id === "conversation-1") ?? null,
      {
        id: "conversation-1",
        sessionId: "session-1",
        messages: [userMessage("u1", "First question"), assistantMessage("a1", "Answer")],
        draft: "",
        bookmarkedMessageIds: [],
        createdAt: 1_000,
      },
    );
    const result = await store.saveConversationRecord(other);
    expect(result.status).toBe("persisted");

    const reloaded = await store.loadConversationLibrary();
    expect(reloaded.conversations).toHaveLength(100);
    expect(reloaded.conversations.some((record) => record.id === "conversation-overflow")).toBe(false);
    expect(reloaded.conversations.find((record) => record.id === "conversation-1")?.messages).toHaveLength(2);
  });

  it("keeps an oversized update volatile while the previous version stays durable", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-live", "conversation-live");
    const small = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Small conversation"),
    ]);
    await store.saveConversationRecord(small);

    // A single conversation near the whole-library limit cannot be admitted;
    // the previous durable version remains authoritative on reload.
    const hugeText = "x".repeat(26 * 1024 * 1024);
    const huge = store.buildConversationRecord(small, {
      id: small.id,
      sessionId: small.sessionId,
      messages: [userMessage("u1", "Small conversation"), assistantMessage("a1", hugeText)],
      draft: "",
      bookmarkedMessageIds: [],
      createdAt: small.createdAt,
    });
    const result = await store.saveConversationRecord(huge);
    expect(result.status).toBe("volatile");
    // The oversized copy stays readable and exportable in this tab.
    expect(
      store.listConversations().find((record) => record.id === small.id)?.messages,
    ).toHaveLength(2);

    // It was never admitted to durable storage, so a reload brings back the
    // last persisted version.
    const reloaded = await store.loadConversationLibrary();
    const durable = reloaded.conversations.find((record) => record.id === small.id);
    expect(durable?.messages).toHaveLength(1);
    expect(durable?.messages[0].text).toBe("Small conversation");
  });

  it("measures the limit in UTF-8 bytes, not JavaScript characters", async () => {
    const store = await freshStore();
    await store.loadConversationLibrary("session-uni", "conversation-uni");
    // ~8.4M emoji stay under 25M JavaScript characters but exceed 25 MiB of
    // UTF-8 bytes.
    const emojiText = "\u{1F600}".repeat(8_500_000);
    const record = store.createConversationRecord("conversation-uni", "session-uni", [
      userMessage("u1", "Unicode"),
      assistantMessage("a1", emojiText),
    ]);
    const result = await store.saveConversationRecord(record);
    expect(result.status).toBe("volatile");
    expect(result.warning).toContain("25 MB");
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

    // New-content writes stay locked while over the limit; deletions work.
    const extra = store.createConversationRecord("conversation-extra", "session-extra", [
      userMessage("u1", "Extra"),
    ]);
    const blocked = await store.saveConversationRecord(extra);
    expect(blocked.status).toBe("volatile");
    const removed = await store.deleteConversationRecord("conversation-0");
    expect(removed.status).toBe("persisted");
  });

  // --- Merge, migration, and backend behavior ----------------------------

  it("merges localStorage fallback records when IndexedDB becomes available again", async () => {
    // The v2 key holds a bare record array, not the v3 envelope.
    window.localStorage.setItem(
      V2_KEY,
      JSON.stringify([makeRecord({ id: "conversation-fallback", sessionId: "session-old", revision: 2 })]),
    );
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.storageMode).toBe("indexeddb");
    expect(state.conversations.map((record) => record.id)).toContain("conversation-fallback");
    expect(store.listConversations().map((record) => record.id)).toContain("conversation-fallback");
  });

  it("merges a version-1 payload and preserves a renamed title as custom", async () => {
    seedRaw(
      V1_KEY,
      JSON.stringify([
        {
          schemaVersion: 1,
          id: "conversation-legacy",
          sessionId: "session-legacy",
          title: "My renamed research",
          createdAt: 500,
          updatedAt: 900,
          messages: [userMessage("u1", "Microsoft risk factors")],
          draft: "",
          bookmarkedMessageIds: ["a1"],
        },
      ]),
    );
    const store = await freshStore();
    const state = await store.loadConversationLibrary("session-legacy", "conversation-legacy");
    const record = state.conversations.find((item) => item.id === "conversation-legacy");
    expect(record?.schemaVersion).toBe(4);
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
    expect(second.conversations.filter((record) => record.id === "conversation-legacy")).toHaveLength(1);
  });

  it("opens a newer-schema IndexedDB read-only with a warning and preserves its data", async () => {
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
            resolve(
              (getAll.result as unknown[]).some(
                (item) => (item as { id: string }).id === "conversation-future",
              ),
            );
          };
          getAll.onerror = () => reject(getAll.error);
        };
        request.onerror = () => reject(request.error);
      });
    }
  });

  it("resolves conflicting copies with equal revision and updatedAt into a recovery entry", async () => {
    seedLocal([
      makeRecord({ revision: 4, updatedAt: 5_000 }),
      makeRecord({ revision: 4, updatedAt: 5_000, draft: "different draft" }),
    ]);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.conversations.find((record) => record.id === "conversation-a")).toBeDefined();
    const recovery = state.conversations.find(
      (record) => record.id === "conversation-a#recovered",
    );
    expect(recovery?.draft).toBe("different draft");
    expect(state.warning).toContain("recovered");
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

    const ids = store.listConversations().map((item) => item.id);
    expect(ids).toContain("conversation-seeded");
    expect(ids).toContain("conversation-new");
    setItemSpy.mockRestore();
    transactionSpy.mockRestore();
  });

  it("reports deletion as not durable when every backend write fails", async () => {
    seedLocal([makeRecord({ id: "conversation-stuck", sessionId: "session-x", revision: 2 })]);
    breakIndexedDbEntirely();

    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.storageMode).toBe("localstorage");

    const setItemSpy = breakLocalStorageWrites();
    const result = await store.deleteConversationRecord("conversation-stuck");
    expect(result.status).not.toBe("persisted");
    expect(store.listConversations().some((record) => record.id === "conversation-stuck")).toBe(true);
    setItemSpy.mockRestore();
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

  it("serializes writes so a save issued during load is not lost", async () => {
    const loadPromise = freshStore().then((store) =>
      store.loadConversationLibrary().then((state) => ({ store, state })),
    );
    const recordPromise = loadPromise.then(({ store }) =>
      store.saveConversationRecord(
        store.createConversationRecord("conversation-race", "session-race", [
          userMessage("u1", "Question during load"),
        ]),
      ),
    );
    const [{ store }, result] = await Promise.all([loadPromise, recordPromise]);
    expect(result.status).toBe("persisted");
    expect(store.listConversations().some((record) => record.id === "conversation-race")).toBe(true);
    const reloaded = await store.loadConversationLibrary();
    expect(reloaded.conversations.some((record) => record.id === "conversation-race")).toBe(true);
  });
});

describe("tombstone and envelope validation", () => {
  beforeEach(() => {
    window.localStorage.clear();
    globalThis.indexedDB = new IDBFactory() as unknown as IDBFactory;
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function seedEnvelope(envelope: Record<string, unknown>): void {
    window.localStorage.setItem(V3_KEY, JSON.stringify(envelope));
  }

  it("accepts an envelope without a tombstones key", async () => {
    seedEnvelope({ envelopeVersion: 3, records: [makeRecord()] });
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.conversations).toHaveLength(1);
    expect(state.warning).toBeNull();
  });

  it("write-locks the backend when tombstones is not an array and preserves the bytes", async () => {
    const raw = JSON.stringify({
      envelopeVersion: 3,
      records: [makeRecord()],
      tombstones: "not-an-array",
    });
    window.localStorage.setItem(V3_KEY, raw);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.warning).toContain("unexpected structure");
    expect(state.storageMode).not.toBe("localstorage");

    // Operations in this session cannot rewrite the malformed payload.
    const record = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Question"),
    ]);
    await store.saveConversationRecord(record);
    await store.deleteConversationRecord(makeRecord().id as string).catch(() => undefined);
    expect(window.localStorage.getItem(V3_KEY)).toBe(raw);
  });

  it.each([
    ["revision zero", { id: "x", revision: 0, deletedAt: 1 }],
    ["negative revision", { id: "x", revision: -1, deletedAt: 1 }],
    ["fractional revision", { id: "x", revision: 1.5, deletedAt: 1 }],
    ["string revision", { id: "x", revision: "3", deletedAt: 1 }],
    ["missing revision", { id: "x", deletedAt: 1 }],
    ["string deletedAt", { id: "x", revision: 1, deletedAt: "later" }],
    ["numeric id", { id: 5, revision: 1, deletedAt: 1 }],
    ["null entry", null],
    ["string entry", "tombstone"],
  ])("treats %s as unreadable and locks writes", async (_label, badTombstone) => {
    seedEnvelope({
      envelopeVersion: 3,
      records: [makeRecord()],
      tombstones: [badTombstone, { id: "conversation-a", revision: 9, deletedAt: 5 }],
    });
    const rawBefore = window.localStorage.getItem(V3_KEY);
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    expect(state.warning).toContain("deletion state");
    expect(state.storageMode).not.toBe("localstorage");

    // The malformed payload is preserved byte-for-byte through operations.
    const record = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Question"),
    ]);
    await store.saveConversationRecord(record);
    expect(window.localStorage.getItem(V3_KEY)).toBe(rawBefore);
    expect(store.getStorageStatus().warning).toContain("deletion state");
  });

  it("locks the envelope when the container version is unsupported or missing", async () => {
    for (const envelope of [
      { envelopeVersion: 5, records: [], tombstones: [] },
      { envelopeVersion: "3", records: [], tombstones: [] },
      { records: [], tombstones: [] },
    ]) {
      window.localStorage.clear();
      const raw = JSON.stringify(envelope);
      window.localStorage.setItem(V3_KEY, raw);
      const store = await freshStore();
      const state = await store.loadConversationLibrary();
      expect(state.warning).toBeTruthy();
      expect(window.localStorage.getItem(V3_KEY)).toBe(raw);
    }
  });

  it("rejects saving, renaming, or bookmarking a record pending deletion", async () => {
    seedEnvelope({
      envelopeVersion: 3,
      records: [makeRecord({ revision: 2 })],
      tombstones: [{ id: "conversation-a", revision: 2, deletedAt: 5 }],
    });
    const store = await freshStore();
    const state = await store.loadConversationLibrary();
    const pending = state.conversations.find((record) => record.id === "conversation-a");
    expect(pending?.deletionPending).toBe(true);

    // A direct save — even with a much higher revision — cannot resurrect it.
    const attempt = await store.saveConversationRecord({
      ...(pending as unknown as ConversationRecord),
      revision: 999,
      title: "Resurrected",
      titleMode: "custom",
    });
    expect(attempt.status).toBe("failed");
    expect(attempt.warning).toContain("pending deletion");
    expect(store.listConversations().find((record) => record.id === "conversation-a")?.title).toBe(
      "First question",
    );

    const reloaded = await store.loadConversationLibrary();
    const stillPending = reloaded.conversations.find((record) => record.id === "conversation-a");
    expect(stillPending?.deletionPending).toBe(true);
    expect(stillPending?.title).toBe("First question");
  });

  it("never persists a deletion intent through another conversation's autosave", async () => {
    seedLocal([makeRecord({ id: "conversation-a", sessionId: "session-a", revision: 2 })]);
    const store = await freshStore();
    await store.loadConversationLibrary();

    // Both backends fail for this deletion (IDB via a write-broken spy,
    // localStorage via a quota error): the tombstone stays an intent.
    const db = await openDb();
    const transactionSpy = breakIdbTransactions(db);
    const setItemSpy = breakLocalStorageWrites();
    const result = await store.deleteConversationRecord("conversation-a");
    setItemSpy.mockRestore();
    transactionSpy.mockRestore();
    expect(result.status).not.toBe("persisted");

    // B's successful autosave must not harden the deletion intent.
    const other = store.createConversationRecord("conversation-b", "session-b", [
      userMessage("u1", "Other conversation"),
    ]);
    const saved = await store.saveConversationRecord(other);
    expect(saved.status).toBe("persisted");
    const envelope = JSON.parse(window.localStorage.getItem(V3_KEY) ?? "{}");
    expect(
      (envelope.tombstones as { id: string }[]).some((tombstone) => tombstone.id === "conversation-a"),
    ).toBe(false);
    // The record itself stays fully intact.
    expect(
      (envelope.records as { id: string }[]).some((record) => record.id === "conversation-a"),
    ).toBe(true);
  });
});
