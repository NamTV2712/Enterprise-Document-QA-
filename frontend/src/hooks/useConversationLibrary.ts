import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Message, RequestSnapshot, SessionHistoryResponse } from "../types";
import { getSessionHistory } from "../lib/api";
import {
  buildConversationRecord,
  ConversationLibraryState,
  ConversationRecord,
  ConversationStorageMode,
  deleteConversationRecord,
  listConversations,
  loadConversationLibrary,
  normalizeStoredMessages,
  saveConversationRecord,
  ConversationWriteResult,
} from "../lib/conversationStore";

const DRAFT_PERSIST_DEBOUNCE_MS = 1000;
const COMPLETION_SAVE_DELAY_MS = 150;

export type SessionContextStatus = "fresh" | "checking" | "available" | "missing" | "unknown";
export type SaveIndicator = "idle" | "saved" | "volatile";

function createSessionId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  // Some embedded browsers and non-secure LAN previews do not expose
  // crypto.randomUUID. Keep session creation resilient without adding a
  // dependency or changing the backend contract.
  const randomPart = Math.random().toString(36).slice(2, 10);
  return `session-${Date.now().toString(36)}-${randomPart}`;
}

function createConversationId(sessionId: string): string {
  return `conversation-${sessionId}`;
}

function safeSetItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch (error) {
    console.warn(`Could not persist "${key}" to localStorage:`, error);
  }
}

function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch (error) {
    console.warn(`Could not read "${key}" from localStorage:`, error);
    return null;
  }
}

function applyWriteResult(
  result: ConversationWriteResult,
  setters: {
    setStorageMode: (mode: ConversationStorageMode) => void;
    setStorageWarning: (warning: string | null) => void;
  },
): void {
  setters.setStorageMode(result.storageMode);
  setters.setStorageWarning(result.warning);
}

export interface ConversationLibraryController {
  sessionId: string;
  activeConversationId: string;
  conversations: ConversationRecord[];
  activeRecord: ConversationRecord | null;
  messages: Message[];
  inputText: string;
  bookmarkedMessageIds: string[];
  storageMode: ConversationStorageMode;
  storageWarning: string | null;
  isLibraryReady: boolean;
  saveIndicator: SaveIndicator;
  sessionContext: SessionContextStatus;
  /** True when follow-up questions must not be sent for this conversation. */
  isReadOnly: boolean;
  setInputText: (text: string) => void;
  updateMessages: (updater: (prev: Message[]) => Message[]) => void;
  beginSend: (text: string) => void;
  registerBackendExchange: () => void;
  /** Abort the active request, normalize partial answers, persist, then return. */
  cancelAndPersistActive: () => Promise<void>;
  /** Re-check backend context and return the resolved status. */
  recheckSessionContext: () => Promise<SessionContextStatus>;
  selectConversation: (conversation: ConversationRecord) => Promise<void>;
  /** Start a new session while keeping the draft text and current filters. */
  startNewConversation: () => Promise<void>;
  renameConversation: (conversationId: string, title: string) => void;
  toggleAnswerBookmark: (messageId: string) => void;
  deleteConversation: (conversationId: string) => Promise<void>;
}

interface UseConversationLibraryOptions {
  /** Called when the hook must abort the active streaming request. */
  onCancelActiveRequest: () => void;
}

/**
 * Owns the local conversation library: hydration, autosave lifecycle,
 * per-conversation operation tokens, and the backend session-context state
 * machine. Streaming request state stays in App; this hook coordinates the
 * persistence and switching semantics around it.
 */
export function useConversationLibrary(
  options: UseConversationLibraryOptions,
): ConversationLibraryController {
  const { onCancelActiveRequest } = options;

  const [sessionId, setSessionId] = useState<string>(() => {
    const stored = safeGetItem("sec_qa_session_id");
    const next = stored || createSessionId();
    if (!stored) safeSetItem("sec_qa_session_id", next);
    return next;
  });
  const [activeConversationId, setActiveConversationId] = useState<string>(() => {
    const stored = safeGetItem("sec_qa_active_conversation_id");
    return stored || createConversationId(safeGetItem("sec_qa_session_id") || "pending");
  });
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [storageMode, setStorageMode] = useState<ConversationStorageMode>("memory");
  const [storageWarning, setStorageWarning] = useState<string | null>(null);
  const [isLibraryReady, setIsLibraryReady] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState<string>("");
  const [bookmarkedMessageIds, setBookmarkedMessageIds] = useState<string[]>([]);
  const [saveIndicator, setSaveIndicator] = useState<SaveIndicator>("idle");
  const [sessionContext, setSessionContext] = useState<SessionContextStatus>("fresh");

  const messagesRef = useRef<Message[]>([]);
  messagesRef.current = messages;
  const inputTextRef = useRef(inputText);
  inputTextRef.current = inputText;
  const bookmarksRef = useRef(bookmarkedMessageIds);
  bookmarksRef.current = bookmarkedMessageIds;
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const activeIdRef = useRef(activeConversationId);
  activeIdRef.current = activeConversationId;
  const conversationsRef = useRef(conversations);
  conversationsRef.current = conversations;

  const conversationCreatedAtRef = useRef(Date.now());
  // Abortable context checks so unmount or conversation switches do not
  // leave backend history requests running.
  const activeContextCheckRef = useRef<AbortController | null>(null);
  const sessionContextRef = useRef<SessionContextStatus>("fresh");
  sessionContextRef.current = sessionContext;
  // Every load/send/save is stamped with the conversation it belongs to so a
  // late response can never mutate a different conversation's state.
  const operationTokenRef = useRef(new Map<string, number>());
  const draftTimerRef = useRef<number | null>(null);
  const completionTimerRef = useRef<number | null>(null);
  const lastSavedSignatureRef = useRef<string>("");

  const beginOperation = useCallback((conversationId: string): number => {
    const next = (operationTokenRef.current.get(conversationId) ?? 0) + 1;
    operationTokenRef.current.set(conversationId, next);
    return next;
  }, []);

  const isCurrentOperation = useCallback((conversationId: string, token: number): boolean => {
    return operationTokenRef.current.get(conversationId) === token;
  }, []);

  const syncConversationsFromRepository = useCallback(() => {
    // The repository snapshot is the source of truth for revisions.
    setConversations(listConversations());
  }, []);

  const persistConversation = useCallback(
    async (
      conversationId: string,
      reason: "draft" | "exchange" | "switch",
      overrides?: { messages?: Message[]; draft?: string; sessionId?: string },
    ) => {
      if (!isLibraryReady) return;
      // Snapshot values must be captured by the caller at schedule time so a
      // pending save can never write one conversation's content under
      // another's id.
      const conversationMessages = overrides?.messages ?? messagesRef.current;
      const draft = overrides?.draft ?? inputTextRef.current;
      const hasContent = conversationMessages.length > 0 || draft.trim().length > 0;
      if (!hasContent && reason !== "switch") return;

      const existing = conversationsRef.current.find((record) => record.id === conversationId) ?? null;
      const record = buildConversationRecord(existing, {
        id: conversationId,
        sessionId: overrides?.sessionId ?? sessionIdRef.current,
        messages: conversationMessages,
        draft,
        bookmarkedMessageIds: bookmarksRef.current,
        createdAt: conversationCreatedAtRef.current,
      });
      const result = await saveConversationRecord(record);
      applyWriteResult(result, { setStorageMode, setStorageWarning });
      setSaveIndicator(result.status === "persisted" ? "saved" : "volatile");
      syncConversationsFromRepository();
    },
    [isLibraryReady, syncConversationsFromRepository],
  );

  // Hydrate the local library first; backend history is only consulted for
  // context status after the local state is authoritative.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const library: ConversationLibraryState = await loadConversationLibrary(
          sessionId,
          activeConversationId,
        );
        if (cancelled) return;
        setConversations(library.conversations);
        setStorageMode(library.storageMode);
        setStorageWarning(library.warning);
        const current =
          library.conversations.find((conversation) => conversation.id === activeConversationId) ||
          library.conversations.find((conversation) => conversation.sessionId === sessionId);
        if (current) {
          conversationCreatedAtRef.current = current.createdAt;
          setActiveConversationId(current.id);
          setSessionId(current.sessionId);
          setMessages(current.messages);
          setInputText(current.draft);
          setBookmarkedMessageIds(current.bookmarkedMessageIds);
          safeSetItem("sec_qa_session_id", current.sessionId);
          safeSetItem("sec_qa_active_conversation_id", current.id);
        }
        setIsLibraryReady(true);
      } catch (error) {
        if (cancelled) return;
        setStorageWarning(
          "Conversation library could not be loaded; this session will continue in memory.",
        );
        setIsLibraryReady(true);
        console.warn("Could not load conversation library:", error);
      }
    })();
    return () => {
      cancelled = true;
    };
    // Run once on mount; hydration must complete before backend fallbacks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkBackendContext = useCallback(
    async (
      targetSessionId: string,
      signal?: AbortSignal,
    ): Promise<SessionContextStatus> => {
      try {
        const history: SessionHistoryResponse = await getSessionHistory(
          targetSessionId,
          signal,
        );
        const context = history.context;
        if (context) {
          return context.status === "available" ? "available" : "missing";
        }
        // Backward compatibility with a backend that does not send context.
        return history.turns.length > 0 ? "available" : "missing";
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          // An aborted check must not be reported as an unreachable backend.
          return sessionContextRef.current === "fresh" ? "fresh" : "unknown";
        }
        return "unknown";
      }
    },
    [],
  );

  const recheckSessionContext = useCallback(async (): Promise<SessionContextStatus> => {
    const conversationId = activeIdRef.current;
    const token = beginOperation(conversationId);
    const controller = new AbortController();
    activeContextCheckRef.current = controller;
    setSessionContext("checking");
    const status = await checkBackendContext(sessionIdRef.current, controller.signal);
    if (isCurrentOperation(conversationId, token)) {
      setSessionContext(status);
    }
    return status;
  }, [beginOperation, checkBackendContext, isCurrentOperation]);

  // Decide the backend context once hydration completed:
  // - conversations with local exchanges re-check the backend session;
  // - conversations with a local record but no exchanges are fresh;
  // - conversations with no local record adopt backend history when the
  //   server still holds the session (reload of an unrecorded conversation).
  useEffect(() => {
    if (!isLibraryReady) return;
    if (messages.length > 0) {
      void recheckSessionContext();
      return;
    }
    const hasRecord = conversations.some(
      (record) => record.id === activeConversationId,
    );
    if (hasRecord) {
      setSessionContext("fresh");
      return;
    }
    let cancelled = false;
    const controller = new AbortController();
    activeContextCheckRef.current = controller;
    void (async () => {
      setSessionContext("checking");
      try {
        const history = await getSessionHistory(sessionIdRef.current, controller.signal);
        if (cancelled) return;
        const turns = history.turns ?? [];
        if (turns.length > 0) {
          const adopted: Message[] = [];
          turns.forEach((turn, index) => {
            adopted.push({
              id: `u-${index}-${sessionIdRef.current}`,
              sender: "user",
              text: turn.user,
            });
            adopted.push({
              id: `a-${index}-${sessionIdRef.current}`,
              sender: "assistant",
              text: turn.assistant,
              rewritten_query: turn.rewritten_query,
              status: "completed",
            });
          });
          setMessages(adopted);
          setSessionContext("available");
          // Persist the adopted exchange so the local library holds the
          // richer copy (backend history has no evidence metadata).
          await persistConversation(activeIdRef.current, "exchange", {
            messages: adopted,
            sessionId: sessionIdRef.current,
          });
        } else {
          // The backend does not know this session: it behaves as a fresh
          // conversation and the first question creates it.
          setSessionContext("fresh");
        }
      } catch (error) {
        if (cancelled || controller.signal.aborted) return;
        setSessionContext(
          error instanceof DOMException && error.name === "AbortError"
            ? "fresh"
            : "unknown",
        );
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLibraryReady, activeConversationId]);

  // Immediate save when an answer completes or stops; drafts keep the
  // debounced path below. Snapshot values are captured at schedule time.
  useEffect(() => {
    if (!isLibraryReady) return;
    if (messages.some((message) => message.isStreaming)) return;
    const last = messages[messages.length - 1];
    const exchangeFinished =
      last !== undefined && last.sender === "assistant" && !last.isStreaming;
    if (!exchangeFinished) return;
    const signature = `${activeIdRef.current}:${messages.length}:${last.id}:${last.text.length}`;
    if (signature === lastSavedSignatureRef.current) return;
    const conversationId = activeIdRef.current;
    const snapshot = { messages };
    if (completionTimerRef.current !== null) window.clearTimeout(completionTimerRef.current);
    completionTimerRef.current = window.setTimeout(() => {
      completionTimerRef.current = null;
      lastSavedSignatureRef.current = signature;
      void persistConversation(conversationId, "exchange", snapshot);
    }, COMPLETION_SAVE_DELAY_MS);
    return () => {
      if (completionTimerRef.current !== null) {
        window.clearTimeout(completionTimerRef.current);
        completionTimerRef.current = null;
      }
    };
  }, [messages, isLibraryReady, persistConversation]);

  // Debounced draft persistence; cleared on every switch so a pending draft
  // save can never write into a different conversation.
  useEffect(() => {
    if (!isLibraryReady) return;
    if (messages.some((message) => message.isStreaming)) return;
    const conversationId = activeIdRef.current;
    const snapshot = { messages, draft: inputText };
    if (draftTimerRef.current !== null) window.clearTimeout(draftTimerRef.current);
    draftTimerRef.current = window.setTimeout(() => {
      draftTimerRef.current = null;
      void persistConversation(conversationId, "draft", snapshot);
    }, DRAFT_PERSIST_DEBOUNCE_MS);
    return () => {
      if (draftTimerRef.current !== null) {
        window.clearTimeout(draftTimerRef.current);
        draftTimerRef.current = null;
      }
    };
  }, [inputText, messages, isLibraryReady, persistConversation]);

  // Best-effort flush when the tab is hidden. A forced browser close can
  // still lose the last debounce window; the UI never promises otherwise.
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState !== "hidden") return;
      if (messagesRef.current.some((message) => message.isStreaming)) return;
      void persistConversation(activeIdRef.current, "draft");
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [persistConversation]);

  const switchToConversation = useCallback(
    async (
      nextSessionId: string,
      nextConversationId: string,
      nextMessages: Message[],
      nextDraft: string,
      nextBookmarks: string[],
      createdAt: number,
    ) => {
      conversationCreatedAtRef.current = createdAt;
      setSessionId(nextSessionId);
      setActiveConversationId(nextConversationId);
      setMessages(nextMessages);
      setInputText(nextDraft);
      setBookmarkedMessageIds(nextBookmarks);
      lastSavedSignatureRef.current = "";
      safeSetItem("sec_qa_session_id", nextSessionId);
      safeSetItem("sec_qa_active_conversation_id", nextConversationId);
      syncConversationsFromRepository();
    },
    [syncConversationsFromRepository],
  );

  const cancelAndPersistActive = useCallback(async () => {
    onCancelActiveRequest();
    const conversationId = activeIdRef.current;
    beginOperation(conversationId);
    const normalized = normalizeStoredMessages(messagesRef.current);
    setMessages(normalized);
    await persistConversation(conversationId, "switch", { messages: normalized });
  }, [beginOperation, onCancelActiveRequest, persistConversation]);

  const selectConversation = useCallback(
    async (conversation: ConversationRecord) => {
      if (conversation.id === activeIdRef.current) return;
      await cancelAndPersistActive();
      beginOperation(conversation.id);
      await switchToConversation(
        conversation.sessionId,
        conversation.id,
        conversation.messages,
        conversation.draft,
        conversation.bookmarkedMessageIds,
        conversation.createdAt,
      );
    },
    [beginOperation, cancelAndPersistActive, switchToConversation],
  );

  const startNewConversation = useCallback(async () => {
    await cancelAndPersistActive();
    const newSessionId = createSessionId();
    const newConversationId = createConversationId(newSessionId);
    beginOperation(newConversationId);
    conversationCreatedAtRef.current = Date.now();
    // Keep the draft text and filters so the user can edit and resend them;
    // the new session deliberately does not inherit backend context.
    await switchToConversation(
      newSessionId,
      newConversationId,
      [],
      inputTextRef.current,
      [],
      conversationCreatedAtRef.current,
    );
    setSessionContext("fresh");
  }, [beginOperation, cancelAndPersistActive, switchToConversation]);

  const renameConversation = useCallback(
    (conversationId: string, title: string) => {
      const conversation = conversationsRef.current.find((item) => item.id === conversationId);
      if (!conversation) return;
      const trimmed = title.trim().replace(/\s+/g, " ").slice(0, 80);
      if (!trimmed) return;
      const updated: ConversationRecord = {
        ...conversation,
        title: trimmed,
        titleMode: "custom",
        updatedAt: Date.now(),
      };
      void saveConversationRecord(updated).then((result) => {
        applyWriteResult(result, { setStorageMode, setStorageWarning });
        syncConversationsFromRepository();
      });
    },
    [syncConversationsFromRepository],
  );

  const toggleAnswerBookmark = useCallback(
    (messageId: string) => {
      const conversationId = activeIdRef.current;
      const conversation = conversationsRef.current.find((item) => item.id === conversationId);
      if (!conversation) return;
      const bookmarked = bookmarksRef.current.includes(messageId);
      const next = bookmarked
        ? bookmarksRef.current.filter((id) => id !== messageId)
        : [...bookmarksRef.current, messageId];
      setBookmarkedMessageIds(next);
      const updated: ConversationRecord = {
        ...conversation,
        bookmarkedMessageIds: next,
        updatedAt: Date.now(),
      };
      void saveConversationRecord(updated).then((result) => {
        applyWriteResult(result, { setStorageMode, setStorageWarning });
        syncConversationsFromRepository();
      });
    },
    [syncConversationsFromRepository],
  );

  const deleteConversation = useCallback(
    async (conversationId: string) => {
      // Invalidate pending autosaves for the deleted conversation first.
      beginOperation(conversationId);
      const result = await deleteConversationRecord(conversationId);
      applyWriteResult(result, { setStorageMode, setStorageWarning });
      syncConversationsFromRepository();
      const stillPresent = listConversations().some((record) => record.id === conversationId);
      if (stillPresent) {
        // A durable-backend failure kept the record; the UI keeps it visible
        // with the warning so the user can retry the deletion.
        return;
      }
      if (conversationId === activeIdRef.current) {
        const newSessionId = createSessionId();
        const newConversationId = createConversationId(newSessionId);
        beginOperation(newConversationId);
        conversationCreatedAtRef.current = Date.now();
        await switchToConversation(
          newSessionId,
          newConversationId,
          [],
          inputTextRef.current,
          [],
          conversationCreatedAtRef.current,
        );
        setSessionContext("fresh");
      }
    },
    [beginOperation, switchToConversation, syncConversationsFromRepository],
  );

  const beginSend = useCallback(
    (_text: string) => {
      const conversationId = activeIdRef.current;
      beginOperation(conversationId);
    },
    [beginOperation],
  );

  const registerBackendExchange = useCallback(() => {
    setSessionContext("available");
  }, []);

  const activeRecord = useMemo(
    () => conversations.find((record) => record.id === activeConversationId) ?? null,
    [activeConversationId, conversations],
  );

  const isReadOnly = sessionContext === "missing" || sessionContext === "unknown";

  return {
    sessionId,
    activeConversationId,
    conversations,
    activeRecord,
    messages,
    inputText,
    bookmarkedMessageIds,
    storageMode,
    storageWarning,
    isLibraryReady,
    saveIndicator,
    sessionContext,
    setInputText,
    updateMessages: setMessages,
    isReadOnly,
    beginSend,
    registerBackendExchange,
    cancelAndPersistActive,
    recheckSessionContext,
    selectConversation,
    startNewConversation,
    renameConversation,
    toggleAnswerBookmark,
    deleteConversation,
  };
}
