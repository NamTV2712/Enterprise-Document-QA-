import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnswerVariant, ConversationNote, DisplayedAnswerContext, Message, MessageFeedback, RequestSnapshot, SaveAnswerVersionStatus, SessionHistoryResponse } from "../types";
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
  mutateConversationRecord,
  saveConversationRecord,
  ConversationWriteResult,
  subscribeConversationLibrary,
  getWriterStatus,
  requestWriterOwnership,
  subscribeConversationWriter,
  WriterStatus,
} from "../lib/conversationStore";

const DRAFT_PERSIST_DEBOUNCE_MS = 1000;

export type SessionContextStatus =
  | "fresh"
  | "checking"
  | "available"
  | "missing"
  | "unknown"
  | "cancelled";
export type SaveIndicator = "idle" | "saved" | "volatile";

export interface SaveAnswerVersionResult {
  status: Exclude<SaveAnswerVersionStatus, "idle" | "saving">;
  variantId?: string;
  storageMode: ConversationStorageMode;
  warning: string | null;
}

export interface ConversationImportResult {
  imported: number;
  persisted: number;
  volatile: number;
  failed: number;
  evidencePersisted?: number;
  evidenceFailed?: number;
  evidenceWarning?: string | null;
}

/**
 * Identity of one send operation: captured before the context preflight and
 * carried through message creation, the provider request, buffering,
 * completion, and the final save. After every await the caller must confirm
 * the identity is still active before touching state.
 */
export interface SendIdentity {
  conversationId: string;
  sessionId: string;
  epoch: number;
}

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

function stableIdentityValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableIdentityValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value as Record<string, unknown>)
        .sort()
        .filter((key) => (value as Record<string, unknown>)[key] !== undefined)
        .map((key) => [key, stableIdentityValue((value as Record<string, unknown>)[key])]),
    );
  }
  return value;
}

function answerVersionFingerprint(variant: Pick<AnswerVariant, "originMessageId" | "text" | "sources" | "requestSnapshot" | "answerLanguage" | "status">): string {
  // The storage normalizer intentionally drops transient source fields such
  // as chunk_text_hash and stored_snapshot. Fingerprinting the durable shape
  // keeps repeat saves idempotent across a browser-storage round trip.
  const durableSources = variant.sources.map(({ chunk_text_hash: _chunkTextHash, stored_snapshot: _storedSnapshot, ...source }) => source);
  return JSON.stringify({
    originMessageId: variant.originMessageId,
    text: variant.text,
    sources: durableSources,
    requestSnapshot: variant.requestSnapshot,
    answerLanguage: variant.answerLanguage,
    status: variant.status,
  }, (_key, value) => stableIdentityValue(value));
}

function createAnswerVariantId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `variant-${globalThis.crypto.randomUUID()}`;
  }
  return `variant-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
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
  /** True while a send preflight is running; duplicate sends are blocked. */
  isPreflightRunning: boolean;
  setInputText: (text: string) => void;
  updateMessages: (updater: (prev: Message[]) => Message[]) => void;
  /**
   * Capture the send identity and mark the preflight in flight. Returns
   * null when another send is still running for this conversation.
   */
  beginSend: (text: string) => SendIdentity | null;
  /**
   * Run the backend-context preflight for an identity. Returns "ok" when
   * the question may be sent, "blocked" when the context is missing or
   * unknown (state already updated for this conversation), and "cancelled"
   * when the identity was invalidated while waiting — in which case no
   * state belonging to a newer conversation is touched.
   */
  ensureSendable: (identity: SendIdentity) => Promise<"ok" | "blocked" | "cancelled">;
  /** Release the preflight slot after the send attempt finished. */
  finishSend: (identity: SendIdentity) => void;
  /** True when the identity still matches the active operation epoch. */
  isIdentityActive: (identity: SendIdentity) => boolean;
  registerBackendExchange: () => void;
  /** Abort the active request, normalize partial answers, persist, then return. */
  cancelAndPersistActive: () => Promise<void>;
  recheckSessionContext: () => Promise<SessionContextStatus>;
  selectConversation: (conversation: ConversationRecord) => Promise<void>;
  /** Start a new session while keeping the draft text and current filters. */
  startNewConversation: () => Promise<void>;
  renameConversation: (conversationId: string, title: string) => void;
  toggleAnswerBookmark: (messageId: string) => Promise<ConversationWriteResult>;
  toggleConversationBookmark: (conversationId: string, messageId: string) => Promise<ConversationWriteResult>;
  deleteConversation: (conversationId: string) => Promise<void>;
  /** Import already validated records without overwriting existing IDs. */
  importConversationRecords: (records: ConversationRecord[]) => Promise<ConversationImportResult>;
  writerStatus: WriterStatus;
  requestLibraryWriter: () => Promise<WriterStatus>;
  updateConversationMetadata: (conversationId: string, patch: { tags?: string[]; notes?: ConversationNote[]; variants?: AnswerVariant[] }) => Promise<ConversationWriteResult>;
  saveMessageNote: (messageId: string, note: string) => Promise<ConversationWriteResult>;
  saveMessageFeedback: (messageId: string, feedback: MessageFeedback | undefined) => Promise<ConversationWriteResult>;
  saveAnswerVersion: (target: DisplayedAnswerContext) => Promise<SaveAnswerVersionResult>;
}

interface UseConversationLibraryOptions {
  /** Called when the hook must abort the active streaming request. */
  onCancelActiveRequest: () => void;
}

/**
 * Owns the local conversation library: hydration, autosave lifecycle,
 * operation epochs, and the backend session-context state machine. Every
 * asynchronous step re-checks its operation epoch before touching state, so
 * a late response can never mutate a conversation the user already left.
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
  const [isPreflightRunning, setIsPreflightRunning] = useState(false);
  const [writerStatus, setWriterStatus] = useState<WriterStatus>(() => getWriterStatus());

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
  const isLibraryReadyRef = useRef(false);
  isLibraryReadyRef.current = isLibraryReady;

  const conversationCreatedAtRef = useRef(Date.now());
  // One global operation epoch: bumping it instantly invalidates every
  // captured identity (sends, preflights, selections, saves).
  const epochRef = useRef(0);
  const activeContextCheckRef = useRef<AbortController | null>(null);
  const sendInFlightRef = useRef<SendIdentity | null>(null);
  const draftTimerRef = useRef<number | null>(null);
  const lastSavedSignatureRef = useRef<string>("");
  const skipNextDraftPersistRef = useRef(false);

  const bumpEpoch = useCallback((): number => {
    epochRef.current += 1;
    return epochRef.current;
  }, []);

  const isIdentityActive = useCallback(
    (identity: SendIdentity): boolean =>
      epochRef.current === identity.epoch &&
      activeIdRef.current === identity.conversationId,
    [],
  );

  const syncConversationsFromRepository = useCallback(() => {
    // The repository snapshot is the source of truth for revisions.
    setConversations(listConversations());
  }, []);

  const persistConversation = useCallback(
    async (
      conversationId: string,
      reason: "draft" | "exchange" | "switch",
      snapshot: {
        messages: Message[];
        draft: string;
        sessionId: string;
        bookmarks: string[];
        createdAt: number;
      },
      identityEpoch: number,
    ): Promise<void> => {
      if (!isLibraryReadyRef.current) return;
      // The caller captures the snapshot at schedule time so a pending save
      // can never write one conversation's content under another's id, and
      // it never reads live refs after an await.
      // Draft saves intentionally omit the in-flight assistant message. A
      // next question must be recoverable without turning a partial answer
      // into durable conversation history.
      const persistedMessages = reason === "draft"
        ? normalizeStoredMessages(snapshot.messages.filter((message) => !message.isStreaming))
        : snapshot.messages;
      const hasContent =
        persistedMessages.length > 0 || snapshot.draft.trim().length > 0;
      if (!hasContent && reason !== "switch") return;
      if (epochRef.current !== identityEpoch) return;

      const existing = conversationsRef.current.find(
        (record) => record.id === conversationId,
      );
      // A record pending deletion rejects saves by design; do not attempt
      // one (and do not flip the saved indicator) from its own autosave.
      if (existing?.deletionPending) return;
      const record = buildConversationRecord(existing ?? null, {
        id: conversationId,
        sessionId: snapshot.sessionId,
        messages: persistedMessages,
        draft: snapshot.draft,
        bookmarkedMessageIds: snapshot.bookmarks,
        createdAt: snapshot.createdAt,
      });
      const hasRepositoryRecord = listConversations().some((item) => item.id === conversationId);
      const result = hasRepositoryRecord
        ? await mutateConversationRecord(conversationId, (latest) => buildConversationRecord(latest, {
            id: conversationId,
            sessionId: snapshot.sessionId,
            messages: persistedMessages,
            draft: snapshot.draft,
            bookmarkedMessageIds: snapshot.bookmarks,
            createdAt: snapshot.createdAt,
          }))
        : await saveConversationRecord(record);
      if (epochRef.current !== identityEpoch) return;
      applyWriteResult(result, { setStorageMode, setStorageWarning });
      // A rejected save (for example a pending-deletion record) is not a
      // storage problem: keep the previous indicator instead of claiming
      // the data is only in this tab.
      if (result.status !== "failed") {
        setSaveIndicator(result.status === "persisted" ? "saved" : "volatile");
      }
      syncConversationsFromRepository();
    },
    [syncConversationsFromRepository],
  );

  const saveAnswerVersion = useCallback(
    async (target: DisplayedAnswerContext): Promise<SaveAnswerVersionResult> => {
      const failed = (warning: string): SaveAnswerVersionResult => ({
        status: "failed",
        storageMode,
        warning,
      });
      if (target.conversationId !== activeIdRef.current) {
        return failed("The displayed answer belongs to a different conversation.");
      }

      const message = messagesRef.current.find((candidate) => candidate.id === target.messageId);
      if (!message || message.sender !== "assistant" || message.isStreaming || message.error || message.status === "error" || !message.text.trim()) {
        return failed("The displayed answer is no longer available to save.");
      }

      const latest = listConversations().find((conversation) => conversation.id === target.conversationId) ??
        conversationsRef.current.find((conversation) => conversation.id === target.conversationId);
      if (!latest) return failed("Conversation not found.");

      if (target.variantId) {
        const selected = latest.variants?.find((variant) =>
          variant.id === target.variantId && variant.originMessageId === target.messageId,
        );
        if (!selected) return failed("The selected answer version is no longer available.");
        return {
          status: "already_saved",
          variantId: selected.id,
          storageMode,
          warning: null,
        };
      }

      const now = Date.now();
      const candidate: AnswerVariant = {
        id: createAnswerVariantId(),
        originMessageId: message.id,
        text: message.text,
        sources: (message.sources ?? []).map((source) => ({ ...source })),
        requestSnapshot: message.requestSnapshot ? { ...message.requestSnapshot } : undefined,
        answerLanguage: message.requestSnapshot?.answerLanguage ?? "en",
        status: message.status === "stopped" ? "stopped" : "completed",
        execution: message.execution,
        visualAnswer: message.visualAnswer,
        createdAt: now,
        updatedAt: now,
      };
      const fingerprint = answerVersionFingerprint(candidate);
      let duplicateId: string | undefined;
      const writeResult = await mutateConversationRecord(target.conversationId, (current) => {
        const duplicate = (current.variants ?? []).find((variant) =>
          answerVersionFingerprint(variant) === fingerprint,
        );
        if (duplicate) {
          duplicateId = duplicate.id;
          return null;
        }
        return { ...current, variants: [...(current.variants ?? []), candidate] };
      });
      applyWriteResult(writeResult, { setStorageMode, setStorageWarning });
      if (writeResult.status !== "failed") {
        setSaveIndicator(writeResult.status === "persisted" ? "saved" : "volatile");
      }
      syncConversationsFromRepository();
      if (duplicateId) {
        return {
          status: "already_saved",
          variantId: duplicateId,
          storageMode: writeResult.storageMode,
          warning: writeResult.warning,
        };
      }
      return {
        status: writeResult.status === "persisted" ? "saved" : writeResult.status === "volatile" ? "volatile" : "failed",
        variantId: writeResult.status === "persisted" || writeResult.status === "volatile" ? candidate.id : undefined,
        storageMode: writeResult.storageMode,
        warning: writeResult.warning,
      };
    },
    [storageMode, syncConversationsFromRepository],
  );

  const saveMessageNote = useCallback(
    async (messageId: string, note: string): Promise<ConversationWriteResult> => {
      skipNextDraftPersistRef.current = true;
      setMessages((previous) => previous.map((message) =>
        message.id === messageId ? { ...message, note: note || undefined } : message,
      ));
      const result = await mutateConversationRecord(activeIdRef.current, (latest) => {
        if (!latest.messages.some((message) => message.id === messageId)) return null;
        return {
          ...latest,
          messages: latest.messages.map((message) =>
            message.id === messageId ? { ...message, note: note || undefined } : message,
          ),
          updatedAt: Date.now(),
        };
      });
      applyWriteResult(result, { setStorageMode, setStorageWarning });
      syncConversationsFromRepository();
      return result;
    },
    [syncConversationsFromRepository],
  );

  const saveMessageFeedback = useCallback(
    async (messageId: string, feedback: MessageFeedback | undefined): Promise<ConversationWriteResult> => {
      const conversationId = activeIdRef.current;
      const epoch = epochRef.current;
      const failed = (warning: string): ConversationWriteResult => ({ status: "failed", storageMode, warning });
      if (feedback?.category === "other" && !feedback.otherText?.trim()) {
        return failed("Other feedback requires a short explanation.");
      }
      skipNextDraftPersistRef.current = true;
      setMessages((previous) => previous.map((message) => {
        if (message.id !== messageId) return message;
        if (!feedback) {
          const { feedback: _ignored, ...withoutFeedback } = message;
          return withoutFeedback;
        }
        return { ...message, feedback };
      }));
      const result = await mutateConversationRecord(conversationId, (latest) => {
        if (!latest.messages.some((message) => message.id === messageId)) return null;
        return {
          ...latest,
          messages: latest.messages.map((message) => {
            if (message.id !== messageId) return message;
            if (!feedback) {
              const { feedback: _ignored, ...withoutFeedback } = message;
              return withoutFeedback;
            }
            return { ...message, feedback };
          }),
          updatedAt: Date.now(),
        };
      });
      applyWriteResult(result, { setStorageMode, setStorageWarning });
      if (epochRef.current === epoch && activeIdRef.current === conversationId) syncConversationsFromRepository();
      return result;
    },
    [storageMode, syncConversationsFromRepository],
  );

  // Hydrate the local library first; backend history is only consulted for
  // context status after the local state is authoritative.
  useEffect(() => {
    let cancelled = false;
    const hydrationEpoch = epochRef.current;
    void (async () => {
      try {
        const library: ConversationLibraryState = await loadConversationLibrary(
          sessionId,
          activeConversationId,
        );
        if (cancelled || epochRef.current !== hydrationEpoch) return;
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

  useEffect(() => subscribeConversationWriter(() => setWriterStatus(getWriterStatus())), []);

  useEffect(() => {
    const unsubscribe = subscribeConversationLibrary(() => {
      // Never overwrite an in-flight send or a draft that is waiting for its
      // debounced save. The next repository sync will observe the newer
      // revision after the local operation completes.
      // A draft save may finish while the answer is still streaming. Do not
      // reload that intermediate repository snapshot over newer local input.
      if (
        sendInFlightRef.current ||
        draftTimerRef.current !== null ||
        messagesRef.current.some((message) => message.isStreaming)
      ) return;
      void loadConversationLibrary(sessionIdRef.current, activeIdRef.current).then((library) => {
        setConversations(library.conversations);
        setStorageMode(library.storageMode);
        setStorageWarning(library.warning);
        const current = library.conversations.find(
          (conversation) => conversation.id === activeIdRef.current,
        );
        if (current) {
          conversationCreatedAtRef.current = current.createdAt;
          setMessages(current.messages);
          setInputText(current.draft);
          setBookmarkedMessageIds(current.bookmarkedMessageIds);
        }
      });
    });
    return unsubscribe;
  }, []);

  const fetchSessionContext = useCallback(
    async (
      targetSessionId: string,
      signal?: AbortSignal,
    ): Promise<SessionHistoryResponse | null> => {
      try {
        return await getSessionHistory(targetSessionId, signal);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return null;
        throw error;
      }
    },
    [],
  );

  const statusFromHistory = useCallback((history: SessionHistoryResponse): SessionContextStatus => {
    const context = history.context;
    if (context) {
      return context.status === "available" ? "available" : "missing";
    }
    // Backward compatibility with a backend that does not send context.
    return history.turns.length > 0 ? "available" : "missing";
  }, []);

  const recheckSessionContext = useCallback(async (): Promise<SessionContextStatus> => {
    const conversationId = activeIdRef.current;
    const epoch = bumpEpoch();
    const controller = new AbortController();
    activeContextCheckRef.current = controller;
    setSessionContext("checking");
    try {
      const history = await fetchSessionContext(sessionIdRef.current, controller.signal);
      if (epochRef.current !== epoch) return "cancelled";
      if (history === null) {
        // Aborted checks never become a connection error.
        return "cancelled";
      }
      const status = statusFromHistory(history);
      setSessionContext(status);
      return status;
    } catch {
      if (epochRef.current !== epoch) return "cancelled";
      setSessionContext("unknown");
      return "unknown";
    }
  }, [bumpEpoch, fetchSessionContext, statusFromHistory]);

  /**
   * Preflight for one send identity. A cancelled identity must not report a
   * usable context and must not change the active conversation's state.
   */
  const ensureSendable = useCallback(
    async (identity: SendIdentity): Promise<"ok" | "blocked" | "cancelled"> => {
      setSessionContext("checking");
      try {
        const history = await fetchSessionContext(identity.sessionId);
        if (!isIdentityActive(identity)) return "cancelled";
        const status = statusFromHistory(history);
        setSessionContext(status);
        return status === "available" ? "ok" : "blocked";
      } catch {
        if (!isIdentityActive(identity)) return "cancelled";
        setSessionContext("unknown");
        return "blocked";
      }
    },
    [fetchSessionContext, isIdentityActive, statusFromHistory],
  );

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
    const epoch = epochRef.current;
    const controller = new AbortController();
    activeContextCheckRef.current = controller;
    void (async () => {
      setSessionContext("checking");
      try {
        const history = await getSessionHistory(sessionIdRef.current, controller.signal);
        if (cancelled || epochRef.current !== epoch) return;
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
            draft: inputTextRef.current,
            sessionId: sessionIdRef.current,
            bookmarks: bookmarksRef.current,
            createdAt: conversationCreatedAtRef.current,
          }, epochRef.current);
        } else {
          // The backend does not know this session: it behaves as a fresh
          // conversation and the first question creates it.
          setSessionContext("fresh");
        }
      } catch (error) {
        if (cancelled || controller.signal.aborted) return;
        setSessionContext(
          error instanceof DOMException && error.name === "AbortError" ? "fresh" : "unknown",
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
    const snapshot = {
      messages,
      draft: inputTextRef.current,
      sessionId: sessionIdRef.current,
      bookmarks: bookmarksRef.current,
      createdAt: conversationCreatedAtRef.current,
    };
    const epoch = epochRef.current;
    lastSavedSignatureRef.current = signature;
    // Persist completed exchanges immediately. Drafts remain debounced, but
    // an answer must be durable before a user can reasonably reload or open
    // the Library immediately after it appears.
    void persistConversation(conversationId, "exchange", snapshot, epoch);
  }, [messages, isLibraryReady, persistConversation]);

  // Debounced draft persistence; cleared on every switch so a pending draft
  // save can never write into a different conversation. Streaming assistant
  // messages are omitted so the draft save never becomes partial history.
  useEffect(() => {
    if (!isLibraryReady) return;
    if (skipNextDraftPersistRef.current) {
      skipNextDraftPersistRef.current = false;
      return;
    }
    const conversationId = activeIdRef.current;
    const persistedMessages = normalizeStoredMessages(
      messages.filter((message) => !message.isStreaming),
    );
    const snapshot = {
      messages: persistedMessages,
      draft: inputText,
      sessionId: sessionIdRef.current,
      bookmarks: bookmarksRef.current,
      createdAt: conversationCreatedAtRef.current,
    };
    const epoch = epochRef.current;
    if (draftTimerRef.current !== null) window.clearTimeout(draftTimerRef.current);
    draftTimerRef.current = window.setTimeout(() => {
      draftTimerRef.current = null;
      void persistConversation(conversationId, "draft", snapshot, epoch);
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
      void persistConversation(activeIdRef.current, "draft", {
        messages: normalizeStoredMessages(
          messagesRef.current.filter((message) => !message.isStreaming),
        ),
        draft: inputTextRef.current,
        sessionId: sessionIdRef.current,
        bookmarks: bookmarksRef.current,
        createdAt: conversationCreatedAtRef.current,
      }, epochRef.current);
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

  /**
   * The single invalidation procedure: bump the epoch so every captured
   * identity loses effect, abort the context preflight and the generation
   * request, and drop pending save timers. Buffered partial answers are
   * normalized by the caller before the old snapshot is persisted.
   */
  const invalidateActiveOperation = useCallback((): number => {
    const epoch = bumpEpoch();
    activeContextCheckRef.current?.abort();
    activeContextCheckRef.current = null;
    onCancelActiveRequest();
    if (draftTimerRef.current !== null) {
      window.clearTimeout(draftTimerRef.current);
      draftTimerRef.current = null;
    }
    sendInFlightRef.current = null;
    setIsPreflightRunning(false);
    return epoch;
  }, [bumpEpoch, onCancelActiveRequest]);

  const cancelAndPersistActive = useCallback(async () => {
    const epoch = invalidateActiveOperation();
    const conversationId = activeIdRef.current;
    const normalized = normalizeStoredMessages(messagesRef.current);
    setMessages(normalized);
    await persistConversation(conversationId, "switch", {
      messages: normalized,
      draft: inputTextRef.current,
      sessionId: sessionIdRef.current,
      bookmarks: bookmarksRef.current,
      createdAt: conversationCreatedAtRef.current,
    }, epoch);
  }, [invalidateActiveOperation, persistConversation]);

  const selectConversation = useCallback(
    async (conversation: ConversationRecord) => {
      if (conversation.id === activeIdRef.current) return;
      // Navigation epoch: the last selection wins. A slow persist of a
      // previously selected conversation can never pull the UI back.
      const navigationEpoch = invalidateActiveOperation();
      const previousSnapshot = {
        messages: normalizeStoredMessages(messagesRef.current),
        draft: inputTextRef.current,
        sessionId: sessionIdRef.current,
        bookmarks: bookmarksRef.current,
        createdAt: conversationCreatedAtRef.current,
      };
      const previousConversationId = activeIdRef.current;
      setMessages(previousSnapshot.messages);
      await persistConversation(previousConversationId, "switch", previousSnapshot, navigationEpoch);
      if (epochRef.current !== navigationEpoch) return;
      beginOperationSwitch(conversation.id);
      await switchToConversation(
        conversation.sessionId,
        conversation.id,
        conversation.messages,
        conversation.draft,
        conversation.bookmarkedMessageIds,
        conversation.createdAt,
      );
    },
    // beginOperationSwitch is defined below; it only bumps a marker for the
    // switched-to conversation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [invalidateActiveOperation, persistConversation, switchToConversation],
  );

  /** Marker bump so effects re-run for the conversation just activated. */
  function beginOperationSwitch(conversationId: string): void {
    // The switch itself bumps no epoch: the navigation epoch already
    // invalidated older work. Recording the id keeps debug tooling simple.
    void conversationId;
  }

  const startNewConversation = useCallback(async () => {
    const epoch = invalidateActiveOperation();
    const previousSnapshot = {
      messages: normalizeStoredMessages(messagesRef.current),
      draft: inputTextRef.current,
      sessionId: sessionIdRef.current,
      bookmarks: bookmarksRef.current,
      createdAt: conversationCreatedAtRef.current,
    };
    setMessages(previousSnapshot.messages);
    await persistConversation(activeIdRef.current, "switch", previousSnapshot, epoch);
    if (epochRef.current !== epoch) return;
    const newSessionId = createSessionId();
    const newConversationId = createConversationId(newSessionId);
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
  }, [invalidateActiveOperation, persistConversation, switchToConversation]);

  const renameConversation = useCallback(
    (conversationId: string, title: string) => {
      const trimmed = title.trim().replace(/\s+/g, " ").slice(0, 80);
      if (!trimmed) return;
      void mutateConversationRecord(conversationId, (latest) => {
        if (latest.deletionPending) return null;
        return { ...latest, title: trimmed, titleMode: "custom", updatedAt: Date.now() };
      }).then((result) => {
        applyWriteResult(result, { setStorageMode, setStorageWarning });
        syncConversationsFromRepository();
      });
    },
    [syncConversationsFromRepository],
  );

  const toggleConversationBookmark = useCallback(
    async (conversationId: string, messageId: string): Promise<ConversationWriteResult> => {
      const unavailable = (warning: string): ConversationWriteResult => ({
        status: "failed",
        storageMode,
        warning,
      });
      const conversation = conversationsRef.current.find((item) => item.id === conversationId);
      if (!conversation) return unavailable("Conversation not found.");
      if (conversation.deletionPending) return unavailable("This conversation is pending deletion.");
      const currentBookmarks = conversationId === activeIdRef.current
        ? bookmarksRef.current
        : conversation.bookmarkedMessageIds;
      const bookmarked = currentBookmarks.includes(messageId);
      const next = bookmarked
        ? currentBookmarks.filter((id) => id !== messageId)
        : [...currentBookmarks, messageId];
      if (conversationId === activeIdRef.current) setBookmarkedMessageIds(next);
      const updated: ConversationRecord = { ...conversation, bookmarkedMessageIds: next, updatedAt: Date.now() };
      // Keep Library filters responsive while the durable write completes.
      // The repository sync below remains authoritative and rolls the
      // optimistic record back if persistence fails.
      const optimisticConversations = conversationsRef.current.map((record) =>
        record.id === conversationId ? updated : record,
      );
      conversationsRef.current = optimisticConversations;
      setConversations(optimisticConversations);
      const result = await mutateConversationRecord(conversationId, (latest) => {
        if (latest.deletionPending) return null;
        const isBookmarked = latest.bookmarkedMessageIds.includes(messageId);
        const nextBookmarks = isBookmarked
          ? latest.bookmarkedMessageIds.filter((id) => id !== messageId)
          : [...latest.bookmarkedMessageIds, messageId];
        return { ...latest, bookmarkedMessageIds: nextBookmarks, updatedAt: Date.now() };
      });
      applyWriteResult(result, { setStorageMode, setStorageWarning });
      syncConversationsFromRepository();
      if (conversationId === activeIdRef.current && result.status === "failed") {
        const durable = listConversations().find((item) => item.id === conversationId);
        if (durable) setBookmarkedMessageIds(durable.bookmarkedMessageIds);
      }
      return result;
    },
    [storageMode, syncConversationsFromRepository],
  );

  const deleteConversation = useCallback(
    async (conversationId: string) => {
      // Only deleting the ACTIVE conversation may invalidate its running
      // requests and preflight; deleting a background Library item must
      // never cancel the user's in-flight work.
      const isActive = conversationId === activeIdRef.current;
      const epoch = isActive ? invalidateActiveOperation() : epochRef.current;
      const result = await deleteConversationRecord(conversationId);
      applyWriteResult(result, { setStorageMode, setStorageWarning });
      syncConversationsFromRepository();
      // The deletion is only complete when the record is gone from the
      // repository list. A pending tombstone (one backend failed) or a
      // failed deletion (no backend updated) keeps the item visible with
      // its warning so it can be retried and exported.
      const stillListed = listConversations().some(
        (record) => record.id === conversationId,
      );
      if (stillListed) {
        return;
      }
      if (isActive && epochRef.current === epoch) {
        const newSessionId = createSessionId();
        const newConversationId = createConversationId(newSessionId);
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
    [invalidateActiveOperation, switchToConversation, syncConversationsFromRepository],
  );

  const importConversationRecords = useCallback(
    async (records: ConversationRecord[]): Promise<ConversationImportResult> => {
      const result: ConversationImportResult = {
        imported: 0,
        persisted: 0,
        volatile: 0,
        failed: 0,
      };
      for (const record of records) {
        const writeResult = await saveConversationRecord(record);
        applyWriteResult(writeResult, { setStorageMode, setStorageWarning });
        if (writeResult.status === "persisted") {
          result.imported += 1;
          result.persisted += 1;
        } else if (writeResult.status === "volatile") {
          result.imported += 1;
          result.volatile += 1;
        } else {
          result.failed += 1;
        }
      }
      syncConversationsFromRepository();
      return result;
    },
    [syncConversationsFromRepository],
  );

  const toggleAnswerBookmark = useCallback(
    (messageId: string) => toggleConversationBookmark(activeIdRef.current, messageId),
    [toggleConversationBookmark],
  );

  const updateConversationMetadata = useCallback(
    async (
      conversationId: string,
      patch: { tags?: string[]; notes?: ConversationNote[]; variants?: AnswerVariant[] },
    ): Promise<ConversationWriteResult> => {
      const result = await mutateConversationRecord(conversationId, (latest) => ({
        ...latest,
        ...(patch.tags !== undefined ? { tags: patch.tags } : {}),
        ...(patch.notes !== undefined ? { notes: patch.notes } : {}),
        ...(patch.variants !== undefined ? { variants: patch.variants } : {}),
        updatedAt: Date.now(),
      }));
      applyWriteResult(result, { setStorageMode, setStorageWarning });
      syncConversationsFromRepository();
      return result;
    },
    [storageMode, syncConversationsFromRepository],
  );

  const requestLibraryWriter = useCallback(async (): Promise<WriterStatus> => {
    const next = await requestWriterOwnership();
    setWriterStatus(next);
    if (next.owned) {
      const library = await loadConversationLibrary(sessionIdRef.current, activeIdRef.current);
      setConversations(library.conversations);
      setStorageMode(library.storageMode);
      setStorageWarning(library.warning);
    }
    return next;
  }, []);

  const beginSend = useCallback(
    (_text: string): SendIdentity | null => {
      if (sendInFlightRef.current) return null;
      const identity: SendIdentity = {
        conversationId: activeIdRef.current,
        sessionId: sessionIdRef.current,
        epoch: epochRef.current,
      };
      sendInFlightRef.current = identity;
      setIsPreflightRunning(true);
      return identity;
    },
    [],
  );

  const finishSend = useCallback((identity: SendIdentity) => {
    if (sendInFlightRef.current?.epoch === identity.epoch) {
      sendInFlightRef.current = null;
      setIsPreflightRunning(false);
    }
  }, []);

  const registerBackendExchange = useCallback(() => {
    setSessionContext("available");
  }, []);

  const activeRecord = useMemo(
    () => conversations.find((record) => record.id === activeConversationId) ?? null,
    [activeConversationId, conversations],
  );

  // Read-only saved conversations and conversations pending deletion lock
  // sending; the composer still accepts a draft for the next conversation.
  const isReadOnly =
    sessionContext === "missing" ||
    sessionContext === "unknown" ||
    (activeRecord?.deletionPending ?? false);

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
    isReadOnly,
    isPreflightRunning,
    setInputText,
    updateMessages: setMessages,
    beginSend,
    ensureSendable,
    finishSend,
    isIdentityActive,
    registerBackendExchange,
    cancelAndPersistActive,
    recheckSessionContext,
    selectConversation,
    startNewConversation,
    renameConversation,
    toggleAnswerBookmark,
    toggleConversationBookmark,
    deleteConversation,
    importConversationRecords,
    writerStatus,
    requestLibraryWriter,
    updateConversationMetadata,
    saveMessageNote,
    saveMessageFeedback,
    saveAnswerVersion,
  };
}
