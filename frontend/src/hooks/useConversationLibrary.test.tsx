import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SessionHistoryResponse } from "../types";

type StoreModule = typeof import("../lib/conversationStore");
type HookModule = typeof import("./useConversationLibrary");

const apiMocks = vi.hoisted(() => ({
  getSessionHistory: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  ...apiMocks,
  getApiBaseUrl: () => "http://localhost:8000",
}));

const V3_KEY = "sec_qa_library_v3";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function makeRecord(id: string, sessionId: string, messages: unknown[] = []) {
  return {
    schemaVersion: 2,
    id,
    sessionId,
    title: `Conversation ${id}`,
    titleMode: "auto",
    revision: 1,
    createdAt: 1,
    updatedAt: 1,
    messages,
    draft: "",
    bookmarkedMessageIds: [],
  };
}

async function freshHook(onCancel = vi.fn()) {
  vi.resetModules();
  const store: StoreModule = await import("../lib/conversationStore");
  const hook: HookModule = await import("./useConversationLibrary");
  const rendered = renderHook(() => hook.useConversationLibrary({ onCancelActiveRequest: onCancel }));
  await waitFor(() => expect(rendered.result.current.isLibraryReady).toBe(true));
  return { store, hook, rendered, onCancel };
}

describe("useConversationLibrary request isolation", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    apiMocks.getSessionHistory.mockResolvedValue({
      session_id: "test",
      turns: [],
      context: { status: "missing", retained_turns: 0, ttl_remaining_seconds: 0 },
    } satisfies SessionHistoryResponse);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("returns cancelled when the preflight is invalidated by a conversation switch", async () => {
    const { rendered } = await freshHook();

    const identity = rendered.result.current.beginSend("What was revenue?");
    expect(identity).not.toBeNull();

    const historyDeferred = deferred<SessionHistoryResponse>();
    apiMocks.getSessionHistory.mockReturnValueOnce(historyDeferred.promise);

    let outcome: "ok" | "blocked" | "cancelled" | "pending" = "pending";
    void act(() => {
      void rendered.result.current.ensureSendable(identity!).then((value) => {
        outcome = value;
      });
    });

    // Switch conversations while the preflight is still waiting.
    const conversationB = makeRecord("conversation-b", "session-b");
    await act(async () => {
      await rendered.result.current.selectConversation(
        conversationB as unknown as Parameters<
          typeof rendered.result.current.selectConversation
        >[0],
      );
    });

    await act(async () => {
      historyDeferred.resolve({
        session_id: identity!.sessionId,
        turns: [],
        context: { status: "available", retained_turns: 2, ttl_remaining_seconds: 100 },
      });
    });

    await waitFor(() => expect(outcome).toBe("cancelled"));
    // The switched-to conversation's context state was never touched by the
    // cancelled preflight: conversation B has no record and no exchanges, so
    // it is fresh.
    expect(rendered.result.current.activeConversationId).toBe("conversation-b");
    expect(rendered.result.current.sessionContext).toBe("fresh");
    rendered.result.current.finishSend(identity!);
  });

  it("keeps the last selection when A to B to C switches complete out of order", async () => {
    const { store, rendered } = await freshHook();
    const saveSpy = vi.spyOn(store, "saveConversationRecord");

    const conversationB = makeRecord("conversation-b", "session-b");
    const firstSave = deferred<unknown>();
    saveSpy.mockImplementationOnce(() => firstSave.promise as never);

    let selectB: Promise<void> | null = null;
    act(() => {
      selectB = rendered.result.current
        .selectConversation(conversationB as never)
        .then(() => undefined);
    });

    // C is selected while B's old-snapshot save is still pending.
    const conversationC = makeRecord("conversation-c", "session-c");
    await act(async () => {
      await rendered.result.current.selectConversation(
        conversationC as never,
      );
    });
    expect(rendered.result.current.activeConversationId).toBe("conversation-c");

    await act(async () => {
      firstSave.resolve(undefined);
      await selectB;
    });
    // B's slow persist must not pull the UI back to B.
    expect(rendered.result.current.activeConversationId).toBe("conversation-c");
    saveSpy.mockRestore();
  });

  it("aborts the running request and starts a new conversation when the active one is deleted", async () => {
    const { rendered, onCancel } = await freshHook();

    // Simulate a streaming exchange in the active conversation.
    act(() => {
      rendered.result.current.updateMessages((prev) => [
        ...prev,
        { id: "u-1", sender: "user", text: "Question" },
        {
          id: "a-1",
          sender: "assistant",
          text: "Partial",
          isStreaming: true,
          status: "streaming",
        },
      ]);
    });

    await act(async () => {
      await rendered.result.current.deleteConversation(
        rendered.result.current.activeConversationId,
      );
    });

    // The generation request was aborted through the cancel path.
    expect(onCancel).toHaveBeenCalled();
    // A fresh empty conversation replaced the deleted one.
    expect(rendered.result.current.messages).toHaveLength(0);
  });

  it("keeps the conversation open in deletion-pending state when a backend fails", async () => {
    const record = makeRecord("conversation-pending", "session-pending", [
      { id: "u-1", sender: "user", text: "Question" },
      { id: "a-1", sender: "assistant", text: "Answer", status: "completed" },
    ]);
    localStorage.setItem(V3_KEY, JSON.stringify({ envelopeVersion: 3, records: [record], tombstones: [] }));
    localStorage.setItem("sec_qa_session_id", "session-pending");
    localStorage.setItem("sec_qa_active_conversation_id", "conversation-pending");

    const { rendered } = await freshHook();
    await waitFor(() => expect(rendered.result.current.activeConversationId).toBe("conversation-pending"));

    const setItemSpy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("quota exceeded", "QuotaExceededError");
    });

    await act(async () => {
      await rendered.result.current.deleteConversation("conversation-pending");
    });
    setItemSpy.mockRestore();

    // IndexedDB is unavailable in jsdom and localStorage failed, so the
    // deletion could not be completed anywhere: the conversation stays open
    // with its history and the retry warning is visible.
    expect(rendered.result.current.activeConversationId).toBe("conversation-pending");
    expect(rendered.result.current.messages).toHaveLength(2);
    expect(rendered.result.current.storageWarning).toContain("Deletion pending");
    expect(
      rendered.result.current.conversations.some((item) => item.id === "conversation-pending"),
    ).toBe(true);

    // Retry once storage recovers: the deletion completes and a fresh
    // conversation opens.
    await act(async () => {
      await rendered.result.current.deleteConversation("conversation-pending");
    });
    expect(rendered.result.current.activeConversationId).not.toBe("conversation-pending");
    expect(
      rendered.result.current.conversations.some((item) => item.id === "conversation-pending"),
    ).toBe(false);
  });

  it("drops the pending draft save of a deleted conversation", async () => {
    const { rendered } = await freshHook();

    const conversationId = rendered.result.current.activeConversationId;
    act(() => {
      rendered.result.current.setInputText("A draft to be deleted");
      rendered.result.current.updateMessages((prev) => [
        ...prev,
        { id: "u-1", sender: "user", text: "Question" },
      ]);
    });

    await act(async () => {
      await rendered.result.current.deleteConversation(conversationId);
    });

    // Let any surviving debounce fire; the deleted conversation must not be
    // written back into the library.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 1200));
    });
    expect(
      rendered.result.current.conversations.some((item) => item.id === conversationId),
    ).toBe(false);
  });

  it("saves the normalized partial answer of the old conversation when starting a new one", async () => {
    const { rendered } = await freshHook();

    act(() => {
      rendered.result.current.updateMessages((prev) => [
        ...prev,
        { id: "u-1", sender: "user", text: "Question" },
        {
          id: "a-1",
          sender: "assistant",
          text: "Partial answer before switch",
          isStreaming: true,
          status: "streaming",
        },
      ]);
    });

    await act(async () => {
      await rendered.result.current.startNewConversation();
    });

    // The old conversation was saved with the streaming message normalized.
    const saved = rendered.result.current.conversations.find(
      (item) => item.messages.some((message) => message.id === "a-1"),
    );
    expect(saved).toBeDefined();
    const assistantMessage = saved?.messages.find((message) => message.id === "a-1");
    expect(assistantMessage?.isStreaming).toBe(false);
    expect(assistantMessage?.status).toBe("stopped");
    // The new conversation is empty but keeps the draft text.
    expect(rendered.result.current.messages).toHaveLength(0);
    expect(rendered.result.current.inputText).toBe("");
  });
});

describe("non-active deletion isolation", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    apiMocks.getSessionHistory.mockResolvedValue({
      session_id: "test",
      turns: [],
      context: { status: "missing", retained_turns: 0, ttl_remaining_seconds: 0 },
    } satisfies SessionHistoryResponse);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("deleting a background conversation never cancels the active request", async () => {
    const recordA = makeRecord("conversation-active", "session-active", [
      { id: "u-1", sender: "user", text: "Active question" },
      { id: "a-1", sender: "assistant", text: "Active answer", status: "completed" },
    ]);
    const recordB = makeRecord("conversation-background", "session-background", [
      { id: "u-1", sender: "user", text: "Background question" },
    ]);
    localStorage.setItem(
      V3_KEY,
      JSON.stringify({ envelopeVersion: 3, records: [recordA, recordB], tombstones: [] }),
    );
    localStorage.setItem("sec_qa_session_id", "session-active");
    localStorage.setItem("sec_qa_active_conversation_id", "conversation-active");

    const { rendered, onCancel } = await freshHook();
    await waitFor(() =>
      expect(rendered.result.current.activeConversationId).toBe("conversation-active"),
    );

    // A generation is in flight on the active conversation.
    act(() => {
      rendered.result.current.updateMessages((prev) => [
        ...prev,
        {
          id: "a-2",
          sender: "assistant",
          text: "Streaming",
          isStreaming: true,
          status: "streaming",
        },
      ]);
    });

    await act(async () => {
      await rendered.result.current.deleteConversation("conversation-background");
    });

    expect(onCancel).not.toHaveBeenCalled();
    // The active conversation keeps streaming untouched.
    expect(rendered.result.current.activeConversationId).toBe("conversation-active");
    expect(
      rendered.result.current.messages.some((message) => message.id === "a-2" && message.isStreaming),
    ).toBe(true);
    // The background conversation is gone from the library.
    expect(
      rendered.result.current.conversations.some((item) => item.id === "conversation-background"),
    ).toBe(false);
  });
});
