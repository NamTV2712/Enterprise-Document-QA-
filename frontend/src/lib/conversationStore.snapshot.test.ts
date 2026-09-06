import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IDBFactory } from "fake-indexeddb";
import type { MockInstance } from "vitest";
import { Message } from "../types";

type StoreModule = typeof import("./conversationStore");

const V3_KEY = "sec_qa_library_v3";
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

function breakIndexedDbEntirely(): void {
  (globalThis as { indexedDB?: unknown }).indexedDB = undefined;
}

function breakLocalStorageWrites(): MockInstance {
  return vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new DOMException("quota exceeded", "QuotaExceededError");
  });
}

/**
 * Break IndexedDB writes only, on a database that the repository has
 * already opened (so no pending version upgrade interferes).
 */
async function breakIdbWrites(): Promise<MockInstance> {
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DB_NAME);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  const spy = vi.spyOn(Object.getPrototypeOf(db), "transaction").mockImplementation((_names, mode) => {
    if ((mode ?? "readonly") !== "readonly") {
      throw new DOMException("connection closed", "InvalidStateError");
    }
    return vi.fn().call(db.transaction.bind(db), _names, mode ?? "readonly") as never;
  });
  db.close();
  return spy;
}

type BackendMode = "localstorage-only" | "indexeddb-only" | "dual";

/**
 * Prepare one repository instance in the requested backend mode and save
 * two conversations (A and B). Returns everything a chain test needs,
 * including per-mode break/restore handles.
 */
async function setupSavedPair(mode: BackendMode) {
  let setItemSpy: MockInstance | null = null;
  let idbWriteSpy: MockInstance | null = null;
  if (mode === "localstorage-only") breakIndexedDbEntirely();
  if (mode === "indexeddb-only") setItemSpy = breakLocalStorageWrites();

  const store = await freshStore();
  await store.loadConversationLibrary();

  const baseA = store.createConversationRecord("conversation-a", "session-a", [
    userMessage("u1", "Apple original question"),
    assistantMessage("a1", "Apple original answer", {
      sources: [{ citation: "AAPL 10-K", score: 0.9, text_preview: "p", text: "Original evidence." }],
    }),
  ]);
  const baseB = store.createConversationRecord("conversation-b", "session-b", [
    userMessage("u1", "Microsoft original question"),
  ]);
  const savedA = await store.saveConversationRecord(baseA);
  const savedB = await store.saveConversationRecord(baseB);
  expect(savedA.status).toBe("persisted");
  expect(savedB.status).toBe("persisted");

  // Re-open a fresh repository so the saved pair is loaded from durable
  // storage, matching a reload, and apply the per-mode break controls.
  if (mode === "indexeddb-only") idbWriteSpy = await breakIdbWrites();
  return {
    store,
    baseA,
    baseB,
    async breakWritesForNextOperation() {
      if (mode === "localstorage-only") breakIndexedDbEntirely();
      if (mode === "localstorage-only" || mode === "dual") setItemSpy = breakLocalStorageWrites();
      if (mode === "indexeddb-only" || mode === "dual") idbWriteSpy = await breakIdbWrites();
    },
    restoreWrites() {
      setItemSpy?.mockRestore();
      setItemSpy = null;
      idbWriteSpy?.mockRestore();
      idbWriteSpy = null;
    },
    async payloadText(): Promise<string> {
      if (mode === "indexeddb-only") {
        const db = await new Promise<IDBDatabase>((resolve, reject) => {
          const request = indexedDB.open(DB_NAME);
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        });
        const records = await new Promise<unknown[]>((resolve, reject) => {
          const tx = db.transaction("conversations", "readonly");
          const request = tx.objectStore("conversations").getAll();
          request.onsuccess = () => resolve(request.result as unknown[]);
          request.onerror = () => reject(request.error);
        });
        db.close();
        return JSON.stringify(records);
      }
      return window.localStorage.getItem(V3_KEY) ?? "";
    },
  };
}

describe("snapshot preservation across failed updates and other saves", () => {
  beforeEach(() => {
    window.localStorage.clear();
    globalThis.indexedDB = new IDBFactory() as unknown as IDBFactory;
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  for (const mode of ["localstorage-only", "indexeddb-only", "dual"] as const) {
    it(`[${mode}] a failed update of A never removes the persisted A when B saves`, async () => {
      const scenario = await setupSavedPair(mode);

      // Update A: the write fails for this operation only.
      await scenario.breakWritesForNextOperation();
      const updatedA = {
        ...scenario.baseA,
        title: scenario.baseA.title,
        messages: [...scenario.baseA.messages, assistantMessage("a2", "Apple follow-up answer")],
        revision: scenario.baseA.revision,
        updatedAt: Date.now(),
      };
      const failedUpdate = await scenario.store.saveConversationRecord(updatedA);
      expect(failedUpdate.status).toBe("volatile");
      scenario.restoreWrites();

      // Autosave B succeeds right after the failed update.
      const updatedB = {
        ...scenario.baseB,
        messages: [...scenario.baseB.messages, assistantMessage("b2", "Microsoft follow-up")],
        revision: scenario.baseB.revision,
        updatedAt: Date.now(),
      };
      const savedB = await scenario.store.saveConversationRecord(updatedB);
      expect(savedB.status).toBe("persisted");

      // The durable payload must still contain the persisted A.
      const payload = await scenario.payloadText();
      expect(payload).toContain("Apple original answer");
      expect(payload).toContain("Microsoft follow-up");

      // Reload: both conversations exist; A keeps its persisted content.
      const reloaded = await freshStore();
      const state = await reloaded.loadConversationLibrary();
      const persistedA = state.conversations.find((record) => record.id === "conversation-a");
      const persistedB = state.conversations.find((record) => record.id === "conversation-b");
      expect(persistedA?.messages.map((message) => message.text)).toContain(
        "Apple original answer",
      );
      expect(persistedB?.messages.map((message) => message.text)).toContain(
        "Microsoft follow-up",
      );
    });

    it(`[${mode}] a never-persisted pending record is not written by another save`, async () => {
      const scenario = await setupSavedPair(mode);

      // A brand-new conversation whose first save fails stays pending.
      await scenario.breakWritesForNextOperation();
      const pending = scenario.store.createConversationRecord("conversation-pending", "session-pending", [
        userMessage("u1", "Pending question"),
      ]);
      const failed = await scenario.store.saveConversationRecord(pending);
      expect(failed.status).toBe("volatile");
      scenario.restoreWrites();

      // B saves successfully afterwards.
      const updatedB = {
        ...scenario.baseB,
        messages: [...scenario.baseB.messages, assistantMessage("b2", "Microsoft follow-up")],
        revision: scenario.baseB.revision,
        updatedAt: Date.now(),
      };
      const savedB = await scenario.store.saveConversationRecord(updatedB);
      expect(savedB.status).toBe("persisted");

      // The pending record was never admitted into durable storage.
      const payload = await scenario.payloadText();
      expect(payload).not.toContain("Pending question");

      const reloaded = await freshStore();
      const state = await reloaded.loadConversationLibrary();
      expect(state.conversations.some((record) => record.id === "conversation-pending")).toBe(false);
      expect(state.conversations.some((record) => record.id === "conversation-b")).toBe(true);
    });

    it(`[${mode}] retrying a failed update persists it exactly once after recovery`, async () => {
      const scenario = await setupSavedPair(mode);

      await scenario.breakWritesForNextOperation();
      const updatedA = {
        ...scenario.baseA,
        messages: [...scenario.baseA.messages, assistantMessage("a2", "Apple follow-up answer")],
        revision: scenario.baseA.revision,
        updatedAt: Date.now(),
      };
      const failedUpdate = await scenario.store.saveConversationRecord(updatedA);
      expect(failedUpdate.status).toBe("volatile");
      scenario.restoreWrites();

      const retry = await scenario.store.saveConversationRecord(updatedA);
      expect(retry.status).toBe("persisted");

      const payload = await scenario.payloadText();
      // Exactly one persisted A with the follow-up, no duplicate ids.
      const matches = payload.match(/conversation-a/g);
      expect(matches?.length).toBe(1);
      expect(payload).toContain("Apple follow-up answer");

      const reloaded = await freshStore();
      const state = await reloaded.loadConversationLibrary();
      const persistedA = state.conversations.find((record) => record.id === "conversation-a");
      expect(persistedA?.messages).toHaveLength(3);
      expect(persistedA?.bookmarkedMessageIds).toEqual([]);
      expect(persistedA?.title).toBe(scenario.baseA.title);
    });
  }

  it("an over-limit pending update keeps the previous persisted version when another save happens", async () => {
    breakIndexedDbEntirely();
    const store = await freshStore();
    await store.loadConversationLibrary("session-live", "conversation-live");
    const small = store.createConversationRecord("conversation-live", "session-live", [
      userMessage("u1", "Small conversation"),
    ]);
    await store.saveConversationRecord(small);

    const hugeText = "x".repeat(26 * 1024 * 1024);
    const huge = store.buildConversationRecord(small, {
      id: small.id,
      sessionId: small.sessionId,
      messages: [userMessage("u1", "Small conversation"), assistantMessage("a1", hugeText)],
      draft: "",
      bookmarkedMessageIds: [],
      createdAt: small.createdAt,
    });
    const blocked = await store.saveConversationRecord(huge);
    expect(blocked.status).toBe("volatile");

    // Another conversation saves successfully.
    const other = store.createConversationRecord("conversation-other", "session-other", [
      userMessage("u1", "Other conversation"),
    ]);
    const saved = await store.saveConversationRecord(other);
    expect(saved.status).toBe("persisted");

    // The previous persisted version of the oversized record survives.
    const envelope = JSON.parse(window.localStorage.getItem(V3_KEY) ?? "{}");
    const persistedLive = (envelope.records as { id: string; messages: unknown[] }[]).find(
      (record) => record.id === "conversation-live",
    );
    expect(persistedLive?.messages).toHaveLength(1);
    expect(store.listConversations().find((record) => record.id === "conversation-live")?.messages).toHaveLength(2);
  });
});
