/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  lazy,
  Suspense,
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import { AlertTriangle, BookMarked, ChevronDown, RefreshCw, X } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ChatInput } from "./components/ChatInput";
import { SampleQuestion } from "./components/SampleQuestionChips";
import { OverviewPanel } from "./components/OverviewPanel";
import { WorkspaceHeader } from "./components/WorkspaceHeader";
import { HelpDialog } from "./components/HelpDialog";
import { CommandPalette, PaletteView } from "./components/CommandPalette";
import { EvidenceWorkspaceRail } from "./components/EvidenceWorkspaceRail";
import {
  HealthResponse,
  RequestSnapshot,
  ThemePreference,
  AnswerLanguage,
  AnswerVariant,
  Message,
  MessageFeedback,
} from "./types";
import {
  checkHealth,
  getSupportedTickers,
  queryDecomposed,
  streamQuery,
} from "./lib/api";
import { formatCompanyLabel, SECTION_METADATA } from "./lib/displayMetadata";
import { ConversationRecord } from "./lib/conversationStore";
import { saveConversationRecord } from "./lib/conversationStore";
import {
  downloadConversationBackup,
  downloadConversationMarkdown,
} from "./lib/conversationExport";
import type { ConversationBackupBundle } from "./lib/conversationExport";
import { useConversationLibrary, SessionContextStatus } from "./hooks/useConversationLibrary";
import { useLocale } from "./lib/i18n";
import { recordAnalyticsEvent } from "./lib/analyticsStore";
import { ResearchTemplate } from "./lib/researchTemplates";
import { mergeEvidenceCollections } from "./lib/evidenceCollections";

const STREAM_FLUSH_INTERVAL_MS = 80;
const HEALTH_REFRESH_INTERVAL_MS = 15_000;
const COMPARATIVE_KEYWORDS = [
  "compare",
  "vs",
  "versus",
  "both",
  "which company",
  "between",
];

const ChatMessage = lazy(() =>
  import("./components/ChatMessage").then(({ ChatMessage }) => ({
    default: ChatMessage,
  })),
);

// Secondary workspaces are route-level panels. Keep the initial chat shell
// small and load diagnostics only when the user opens that workspace.
const RetrievalLabPanel = lazy(() =>
  import("./components/RetrievalLabPanel").then(({ RetrievalLabPanel }) => ({ default: RetrievalLabPanel })),
);
const DocumentExplorerPanel = lazy(() =>
  import("./components/DocumentExplorerPanel").then(({ DocumentExplorerPanel }) => ({ default: DocumentExplorerPanel })),
);
const SystemInfoPanel = lazy(() =>
  import("./components/SystemInfoPanel").then(({ SystemInfoPanel }) => ({ default: SystemInfoPanel })),
);
const EvaluationPanel = lazy(() =>
  import("./components/EvaluationPanel").then(({ EvaluationPanel }) => ({ default: EvaluationPanel })),
);
const AnalyticsPanel = lazy(() =>
  import("./components/AnalyticsPanel").then(({ AnalyticsPanel }) => ({ default: AnalyticsPanel })),
);

function WorkspacePanelFallback() {
  return (
    <div className="mx-auto flex w-full max-w-6xl items-center gap-2 px-3 py-8 text-sm text-[var(--text-muted)] md:px-6" role="status">
      <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]" />
      Loading workspace…
    </div>
  );
}

function isComparativeQuery(question: string): boolean {
  const lower = question.toLowerCase();
  return COMPARATIVE_KEYWORDS.some((keyword) => lower.includes(keyword));
}

function describeRequestError(
  error: unknown,
  fallback: string,
): { message: string; detail: string } {
  const detail = error instanceof Error ? error.message : String(error);
  const candidateStatus =
    error && typeof error === "object" && "status" in error
      ? (error as { status?: unknown }).status
      : null;
  const status = typeof candidateStatus === "number" ? candidateStatus : null;
  const candidateCode =
    error && typeof error === "object" && "code" in error
      ? (error as { code?: unknown }).code
      : null;
  const code = typeof candidateCode === "string" ? candidateCode : null;
  if (status === 429) {
    if (code === "client_rate_limited") {
      return { message: "Too many requests from this client. Please wait and try again.", detail };
    }
    return {
      message: "The provider is temporarily out of quota. Please wait and try again later.",
      detail,
    };
  }
  if (status === 408 || status === 504) {
    return { message: "The request timed out. Try a narrower question or try again.", detail };
  }
  if (status !== null && status >= 500) {
    return { message: "The research service is temporarily unavailable. Please try again.", detail };
  }
  if (error instanceof TypeError) {
    return { message: "The backend could not be reached. Check the connection and try again.", detail };
  }
  return { message: fallback, detail };
}

function getSystemTheme(): "light" | "dark" {
  return typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

type WorkspaceView = "overview" | "conversation" | "retrieval" | "documents" | "evaluation" | "analytics" | "system";

function initialWorkspaceView(): WorkspaceView {
  if (typeof window === "undefined") return "overview";
  if (import.meta.env.MODE === "test") return "overview";
  const value = new URLSearchParams(window.location.search).get("view");
  return ["overview", "conversation", "retrieval", "documents", "evaluation", "analytics", "system"].includes(value ?? "")
    ? (value as WorkspaceView)
    : "overview";
}

export default function App() {
  const { locale } = useLocale();
  const [tickers, setTickers] = useState<string[]>([]);
  const [sections, setSections] = useState<string[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [topK, setTopK] = useState<number>(5);
  const [enableComparative, setEnableComparative] = useState<boolean>(true);
  const [answerLanguage, setAnswerLanguage] = useState<AnswerLanguage>(() => {
    try {
      const saved = localStorage.getItem("sec_qa_answer_language");
      if (saved === "en" || saved === "vi") return saved;
    } catch {
      // Use English when preferences are unavailable.
    }
    return typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("vi")
      ? "vi"
      : "en";
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(
    null,
  );
  const [isPipelineReady, setIsPipelineReady] = useState<boolean | null>(null);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isClearingSession, setIsClearingSession] = useState<boolean>(false);
  const [showResetDialog, setShowResetDialog] = useState<boolean>(false);
  const [isHelpOpen, setIsHelpOpen] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [activeView, setActiveView] = useState<WorkspaceView>(initialWorkspaceView);
  const [pendingFocusMessageId, setPendingFocusMessageId] = useState<string | null>(null);
  const [activeSidebarPanel, setActiveSidebarPanel] = useState<"research" | "library">("research");

  // Theme state. Keep the preference separate from the resolved color so a
  // system preference can follow OS changes without overwriting user choice.
  const [themePreference, setThemePreference] = useState<ThemePreference>(() => {
    try {
      const saved = localStorage.getItem("theme");
      if (saved === "system" || saved === "light" || saved === "dark") {
        return saved;
      }
    } catch {
      // Storage may be unavailable; fall back to system.
    }
    return "system";
  });
  const [systemTheme, setSystemTheme] = useState<"light" | "dark">(
    getSystemTheme,
  );
  const resolvedTheme = themePreference === "system" ? systemTheme : themePreference;

  useEffect(() => {
    const handlePopState = () => setActiveView(initialWorkspaceView());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (import.meta.env.MODE === "test") return;
    const url = new URL(window.location.href);
    if (activeView === "overview") url.searchParams.delete("view");
    else url.searchParams.set("view", activeView);
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  }, [activeView]);

  useEffect(() => {
    try {
      localStorage.setItem("sec_qa_answer_language", answerLanguage);
    } catch {
      // The selection remains active for this tab.
    }
  }, [answerLanguage]);

  useEffect(() => {
    try {
      if (!localStorage.getItem("sec_qa_answer_language")) {
        setAnswerLanguage(locale === "vi" ? "vi" : "en");
      }
    } catch {
      setAnswerLanguage(locale === "vi" ? "vi" : "en");
    }
  }, [locale]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const requestAbortRef = useRef<AbortController | null>(null);
  // Buffered SSE text that has not been flushed to the message yet. The
  // cancel path flushes it so switching conversations never loses the last
  // buffered tokens of a partial answer.
  const streamingBufferRef = useRef<{ messageId: string; text: string } | null>(null);
  const resetCancelRef = useRef<HTMLButtonElement>(null);
  const healthRequestRef = useRef<Promise<HealthResponse> | null>(null);
  const lastHealthRefreshRef = useRef(0);
  const [showScrollButton, setShowScrollButton] = useState<boolean>(false);

  // Indirection so the library hook can trigger the cancel path (which
  // needs updateMessages) before that function is declared below.
  const cancelActiveRequestRef = useRef<() => void>(() => {});

  const library = useConversationLibrary({
    onCancelActiveRequest: () => cancelActiveRequestRef.current(),
  });
  const {
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
    setInputText,
    updateMessages,
    beginSend,
    ensureSendable,
    finishSend,
    isIdentityActive,
    registerBackendExchange,
    selectConversation,
    startNewConversation,
    renameConversation,
    toggleAnswerBookmark,
    deleteConversation,
    importConversationRecords,
    recheckSessionContext,
    writerStatus,
    requestLibraryWriter,
    updateConversationMetadata,
  } = library;
  const activeConversationId = library.activeConversationId;

  const cancelActiveRequest = useCallback(() => {
    const buffer = streamingBufferRef.current;
    if (buffer && buffer.text) {
      updateMessages((prev) =>
        prev.map((message) =>
          message.id === buffer.messageId && message.isStreaming
            ? { ...message, text: buffer.text }
            : message,
        ),
      );
    }
    streamingBufferRef.current = null;
    const controller = requestAbortRef.current;
    requestAbortRef.current = null;
    controller?.abort();
    setIsLoading(false);
  }, [updateMessages]);
  cancelActiveRequestRef.current = cancelActiveRequest;

  const applyHealth = useCallback((health: HealthResponse) => {
    lastHealthRefreshRef.current = Date.now();
    setHealthData(health);
    setIsBackendConnected(true);
    setIsPipelineReady(health.pipeline_ready);
  }, []);

  const refreshHealth = useCallback(
    async (force = false, signal?: AbortSignal): Promise<HealthResponse | null> => {
      const now = Date.now();
      if (
        !force &&
        lastHealthRefreshRef.current > 0 &&
        now - lastHealthRefreshRef.current < HEALTH_REFRESH_INTERVAL_MS
      ) {
        return null;
      }

      if (healthRequestRef.current) return healthRequestRef.current;

      const request = checkHealth(signal)
        .then((health) => {
          applyHealth(health);
          return health;
        })
        .finally(() => {
          healthRequestRef.current = null;
        });
      healthRequestRef.current = request;
      return request;
    },
    [applyHealth],
  );

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const updateSystemTheme = (event?: MediaQueryListEvent) => {
      setSystemTheme(event ? (event.matches ? "dark" : "light") : getSystemTheme());
    };
    updateSystemTheme();
    media.addEventListener?.("change", updateSystemTheme);
    return () => media.removeEventListener?.("change", updateSystemTheme);
  }, []);

  // Apply the resolved theme class and persist the preference.
  useEffect(() => {
    if (resolvedTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    try {
      localStorage.setItem("theme", themePreference);
    } catch {
      // Storage may be unavailable; theme still applies for this session.
    }
  }, [resolvedTheme, themePreference]);

  // Initialization: health and supported metadata only. Session context is
  // owned by the library hook after local hydration completes.
  useEffect(() => {
    const controller = new AbortController();

    const initData = async () => {
      try {
        const health = await checkHealth(controller.signal);
        applyHealth(health);
        const support = await getSupportedTickers(controller.signal);
        setTickers(support.tickers || []);
        setSections(support.sections || []);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        console.warn("FastAPI initialization check failed:", err);
        setIsBackendConnected(false);
        setIsPipelineReady(false);
      }
    };

    initData();
    return () => controller.abort();
  }, [applyHealth]);

  useEffect(() => {
    return () => {
      const controller = requestAbortRef.current;
      requestAbortRef.current = null;
      controller?.abort();
    };
  }, []);

  // Adopted backend history moves the user into the conversation view once.
  const historyAdoptedRef = useRef(false);
  useEffect(() => {
    if (!historyAdoptedRef.current && messages.length > 0 && isLibraryReady) {
      historyAdoptedRef.current = true;
      setActiveView("conversation");
    }
  }, [messages.length, isLibraryReady]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const reduced = prefersReducedMotion();
    messagesEndRef.current?.scrollIntoView({
      behavior: reduced ? "auto" : behavior,
    });
  }, []);

  useEffect(() => {
    if (activeView !== "conversation") return;

    // Repeated smooth-scroll animations overlap while tokens arrive every
    // 80ms. Batch the layout read/write to the next animation frame.
    const scroll = () => {
      scrollToBottom(isLoading ? "auto" : "smooth");
    };
    const frame =
      typeof requestAnimationFrame === "function"
        ? requestAnimationFrame(scroll)
        : window.setTimeout(scroll, 0);
    return () => {
      if (typeof cancelAnimationFrame === "function") {
        cancelAnimationFrame(frame);
      } else {
        window.clearTimeout(frame);
      }
    };
  }, [activeView, isLoading, messages, scrollToBottom]);

  // Focus a bookmarked message opened from the Library.
  useEffect(() => {
    if (!pendingFocusMessageId) return;
    const frame = window.requestAnimationFrame(() => {
      const target = document.getElementById(`message-${pendingFocusMessageId}`);
      target?.scrollIntoView({
        behavior: prefersReducedMotion() ? "auto" : "smooth",
        block: "start",
      });
      target?.focus({ preventScroll: true });
      setPendingFocusMessageId(null);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [pendingFocusMessageId, activeView, messages.length]);

  // Detect scroll position to show/hide scroll-to-bottom button
  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (!scrollContainer) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShowScrollButton(!isNearBottom && messages.length > 0);
    };

    scrollContainer.addEventListener("scroll", handleScroll, { passive: true });
    return () => scrollContainer.removeEventListener("scroll", handleScroll);
  }, [activeView, messages.length]);

  const handleSendMessage = useCallback(async (text: string, snapshot?: RequestSnapshot) => {
    if (!isBackendConnected || !isPipelineReady) return;
    if (isReadOnly) return;

    const requestSnapshot: RequestSnapshot = snapshot
      ? { ...snapshot, answerLanguage: snapshot.answerLanguage ?? answerLanguage }
      : {
          ticker: selectedTicker,
          section: selectedSection,
          topK,
          enableComparative,
          answerLanguage,
        };

    // One identity is captured before the preflight and carried through
    // message creation, the provider request, buffering, completion, and
    // the final save. Duplicate sends are blocked while one is in flight.
    const identity = beginSend(text);
    if (!identity) return;
    const analyticsStartedAt = Date.now();
    recordAnalyticsEvent({
      kind: "query_started",
      ticker: requestSnapshot.ticker,
      language: requestSnapshot.answerLanguage,
    });

    // Re-check a saved conversation's backend session before spending the
    // question; the session can expire while the user is reading. A
    // cancelled preflight (conversation switched meanwhile) never reports a
    // usable context and never touches the newer conversation's state.
    if (sessionContext !== "fresh") {
      const outcome = await ensureSendable(identity);
      if (outcome !== "ok") {
        finishSend(identity);
        return;
      }
    }
    if (!isIdentityActive(identity)) {
      finishSend(identity);
      return;
    }

    setActiveView("conversation");
    requestAbortRef.current?.abort();
    const controller = new AbortController();
    requestAbortRef.current = controller;
    const isCurrentRequest = () =>
      requestAbortRef.current === controller && !controller.signal.aborted;

    const userMessage = {
      id: "user-" + Date.now(),
      sender: "user" as const,
      text: text,
      requestSnapshot,
    };

    updateMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    const isComparative =
      requestSnapshot.enableComparative && isComparativeQuery(text);
    const assistantMsgId = "assistant-" + Date.now();

    // The payload uses the session id captured with the identity, so a
    // session from an older conversation can never be combined with the
    // messages of a newer one.
    const payload = {
      question: text,
      ticker: requestSnapshot.ticker,
      section: requestSnapshot.section,
      top_k: requestSnapshot.topK,
      session_id: identity.sessionId,
      answer_language: requestSnapshot.answerLanguage,
    };

    try {
    if (isComparative) {
      // Create initial loading/placeholder message for Decomposed POST
      const placeholder = {
        id: assistantMsgId,
        sender: "assistant" as const,
        text: "",
        subQueries: [],
        wasDecomposed: true,
        isStreaming: true,
        status: "streaming" as const,
        requestSnapshot,
      };
      updateMessages((prev) => [...prev, placeholder]);

      try {
        const response = await queryDecomposed(payload, controller.signal);
        if (!isCurrentRequest()) return;
        updateMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  text: response.answer,
                  model_used: response.model_used,
                  sources: response.sources,
                  subQueries: response.sub_queries,
                  wasDecomposed: response.was_decomposed,
                  numChunks: response.num_total_chunks,
                  queryInterpretation: response.query_interpretation,
                  isStreaming: false,
                  status: "completed" as const,
                }
              : m,
          ),
        );
        registerBackendExchange();
        recordAnalyticsEvent({
          kind: "query_completed",
          ticker: requestSnapshot.ticker,
          language: requestSnapshot.answerLanguage,
          durationMs: Date.now() - analyticsStartedAt,
          status: "completed",
        });
      } catch (err: any) {
        if (!isCurrentRequest()) return;
        const requestError = describeRequestError(
          err,
          "We couldn't complete this comparison. Check the connection and try again.",
        );
        updateMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  text: requestError.message,
                  error: true,
                  isStreaming: false,
                  status: "error" as const,
                  errorDetail: requestError.detail,
                  retryText: text,
                }
              : m,
          ),
        );
        recordAnalyticsEvent({
          kind: "query_error",
          ticker: requestSnapshot.ticker,
          language: requestSnapshot.answerLanguage,
          durationMs: Date.now() - analyticsStartedAt,
          status: "error",
        });
      } finally {
        if (requestAbortRef.current === controller) {
          requestAbortRef.current = null;
          setIsLoading(false);
        }
      }
    } else {
      // Streamed query over POST EventStream
      const placeholder = {
        id: assistantMsgId,
        sender: "assistant" as const,
        text: "",
        isStreaming: true,
        status: "streaming" as const,
        requestSnapshot,
      };
      updateMessages((prev) => [...prev, placeholder]);

      let streamingText = "";
      let pendingFlush: ReturnType<typeof setTimeout> | null = null;
      streamingBufferRef.current = { messageId: assistantMsgId, text: "" };

      const cancelPendingFlush = () => {
        if (pendingFlush !== null) {
          clearTimeout(pendingFlush);
          pendingFlush = null;
        }
      };

      const scheduleStreamingFlush = () => {
        if (pendingFlush === null) {
          pendingFlush = setTimeout(() => {
            pendingFlush = null;
            updateMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, text: streamingText } : m,
              ),
            );
          }, STREAM_FLUSH_INTERVAL_MS);
        }
      };

      try {
        await streamQuery(
          payload,
          (event) => {
            if (!isCurrentRequest()) return;
            if (event.type === "sources") {
              const sourcesList = event.data || [];
              updateMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        sources: sourcesList,
                      }
                    : m,
                ),
              );
            } else if (event.type === "token") {
              streamingText += event.data;
              streamingBufferRef.current = { messageId: assistantMsgId, text: streamingText };
              scheduleStreamingFlush();
            } else if (event.type === "done") {
              cancelPendingFlush();
              streamingBufferRef.current = null;
              updateMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        text: streamingText,
                        queryInterpretation: event.data?.query_interpretation,
                        isStreaming: false,
                        status: "completed" as const,
                      }
                    : m,
                ),
              );
              registerBackendExchange();
              recordAnalyticsEvent({
                kind: "query_completed",
                ticker: requestSnapshot.ticker,
                language: requestSnapshot.answerLanguage,
                durationMs: Date.now() - analyticsStartedAt,
                status: "completed",
              });
              setIsLoading(false);
            } else if (event.type === "error") {
              cancelPendingFlush();
              streamingBufferRef.current = null;
              updateMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        text:
                          streamingText +
                          (streamingText ? "\n\n" : "") +
                          "We couldn't complete this answer. Please try again.",
                        isStreaming: false,
                        error: true,
                        status: "error" as const,
                        errorDetail: event.data,
                        retryText: text,
                      }
                    : m,
                ),
              );
              setIsLoading(false);
              recordAnalyticsEvent({
                kind: "query_error",
                ticker: requestSnapshot.ticker,
                language: requestSnapshot.answerLanguage,
                durationMs: Date.now() - analyticsStartedAt,
                status: "error",
              });
            }
          },
          (error) => {
            if (!isCurrentRequest()) return;
            const requestError = describeRequestError(
              error,
              "The connection closed before the answer finished. Please try again.",
            );
            cancelPendingFlush();
            streamingBufferRef.current = null;
            updateMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                        text: streamingText + (streamingText ? "\n\n" : "") + requestError.message,
                      isStreaming: false,
                      error: true,
                      status: "error" as const,
                      errorDetail: requestError.detail,
                      retryText: text,
                    }
                  : m,
              ),
            );
            setIsLoading(false);
            recordAnalyticsEvent({
              kind: "query_error",
              ticker: requestSnapshot.ticker,
              language: requestSnapshot.answerLanguage,
              durationMs: Date.now() - analyticsStartedAt,
              status: "connection_closed",
            });
          },
          controller.signal,
        );
      } catch (err: any) {
        if (!isCurrentRequest()) return;
        const requestError = describeRequestError(
          err,
          "We couldn't complete this answer. Please try again.",
        );
        cancelPendingFlush();
        streamingBufferRef.current = null;
        updateMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                    text: streamingText + (streamingText ? "\n\n" : "") + requestError.message,
                  isStreaming: false,
                  error: true,
                  status: "error" as const,
                  errorDetail: requestError.detail,
                  retryText: text,
                }
              : m,
          ),
        );
        setIsLoading(false);
        recordAnalyticsEvent({
          kind: "query_error",
          ticker: requestSnapshot.ticker,
          language: requestSnapshot.answerLanguage,
          durationMs: Date.now() - analyticsStartedAt,
          status: "error",
        });
      } finally {
        cancelPendingFlush();
        if (requestAbortRef.current === controller) {
          requestAbortRef.current = null;
          setIsLoading(false);
        }
      }

      // The connection closed. If the server never sent a done or error
      // event, flush the buffered partial answer and normalize it to a
      // stopped state; a dropped stream must never remain "streaming".
      if (!isCurrentRequest() && isIdentityActive(identity)) {
        streamingBufferRef.current = null;
        updateMessages((prev) =>
          prev.map((m) => {
            if (m.id !== assistantMsgId || !m.isStreaming) return m;
            if (streamingText) {
              return { ...m, text: streamingText, isStreaming: false, status: "stopped" as const };
            }
            return {
              ...m,
              text: "The connection closed before the answer finished. Please try again.",
              isStreaming: false,
              error: true,
              status: "error" as const,
              retryText: text,
            };
          }),
        );
      }
    }
    } finally {
      streamingBufferRef.current = null;
      finishSend(identity);
    }

    if (controller.signal.aborted) return;

    // Refresh health details to get updated total turn counters, active sessions, etc.
    try {
      await refreshHealth(false, controller.signal);
    } catch (e) {
      if (!controller.signal.aborted) {
        console.warn("Could not refresh health data:", e);
      }
    }
  }, [
    answerLanguage,
    beginSend,
    enableComparative,
    ensureSendable,
    finishSend,
    isBackendConnected,
    isIdentityActive,
    isPipelineReady,
    isReadOnly,
    registerBackendExchange,
    selectedSection,
    selectedTicker,
    sessionContext,
    topK,
    refreshHealth,
    updateMessages,
  ]);

  // Stable retry callback so memoized ChatMessage items skip re-renders;
  // the ref indirection keeps access to the latest send handler.
  const handleSendMessageRef = useRef(handleSendMessage);
  handleSendMessageRef.current = handleSendMessage;
  const handleRetry = useCallback((text: string, snapshot?: RequestSnapshot) => {
    if (isReadOnly) return;
    setInputText(text);
    handleSendMessageRef.current(text, snapshot);
  }, [isReadOnly, setInputText]);

  const confirmNewConversation = useCallback(async () => {
    setShowResetDialog(false);
    await startNewConversation();
    setActiveView("overview");
    setActiveSidebarPanel("research");
    try {
      await refreshHealth(true);
    } catch (e) {
      setIsBackendConnected(false);
      setIsPipelineReady(false);
    }
  }, [refreshHealth, startNewConversation]);

  const requestNewConversation = useCallback(() => {
    if (messages.length === 0) {
      void confirmNewConversation();
      return;
    }
    setShowResetDialog(true);
  }, [confirmNewConversation, messages.length]);

  const handleSelectConversation = useCallback(
    async (conversation: ConversationRecord) => {
      setActiveView(conversation.messages.length ? "conversation" : "overview");
      if (conversation.id === activeConversationId) return;
      await selectConversation(conversation);
    },
    [activeConversationId, selectConversation],
  );

  // Open the exact bookmarked answer inside its conversation.
  const handleOpenMessage = useCallback(
    async (conversationId: string, messageId: string) => {
      const conversation = conversations.find((item) => item.id === conversationId);
      if (!conversation) return;
      if (conversation.id !== activeConversationId) {
        await selectConversation(conversation);
      }
      setPendingFocusMessageId(messageId);
      setActiveView("conversation");
    },
    [activeConversationId, conversations, selectConversation],
  );

  const handleExportConversation = useCallback((conversation: ConversationRecord) => {
    downloadConversationMarkdown(conversation);
  }, []);

  const handleExportBackup = useCallback(() => {
    downloadConversationBackup(conversations);
  }, [conversations]);

  const handleImportBackup = useCallback(
    async (bundle: ConversationBackupBundle) => {
      const result = await importConversationRecords(bundle.conversations);
      mergeEvidenceCollections(bundle.collections);
      if (result.imported === 0) throw new Error("No conversation could be imported into storage.");
      return result;
    },
    [importConversationRecords],
  );

  // Bookmark toggle that works from Library cards for any conversation,
  // not only the one currently open.
  const handleSidebarToggleBookmark = useCallback(
    (conversationId: string, messageId: string) => {
      const conversation = conversations.find((item) => item.id === conversationId);
      if (!conversation) return;
      if (conversationId === activeConversationId) {
        toggleAnswerBookmark(messageId);
        return;
      }
      const bookmarked = conversation.bookmarkedMessageIds.includes(messageId);
      const next = bookmarked
        ? conversation.bookmarkedMessageIds.filter((id) => id !== messageId)
        : [...conversation.bookmarkedMessageIds, messageId];
      void saveConversationRecord({
        ...conversation,
        bookmarkedMessageIds: next,
        updatedAt: Date.now(),
      });
    },
    [activeConversationId, conversations, toggleAnswerBookmark],
  );

  const handleSaveMessageNote = useCallback((messageId: string, note: string) => {
    updateMessages((prev) => prev.map((message) => message.id === messageId ? { ...message, note: note || undefined } : message));
  }, [updateMessages]);

  const handleMessageFeedback = useCallback((messageId: string, feedback: MessageFeedback | undefined) => {
    updateMessages((prev) => prev.map((message) =>
      message.id === messageId ? { ...message, feedback } : message,
    ));
    recordAnalyticsEvent({
      kind: "feedback",
      status: feedback
        ? `${feedback.rating}${feedback.category ? `:${feedback.category}` : ""}`
        : "cleared",
    });
  }, [updateMessages]);

  const handleSaveAnswerVariant = useCallback((message: Message) => {
    if (!activeRecord || message.sender !== "assistant" || !message.text) return;
    const now = Date.now();
    const variant: AnswerVariant = {
      id: `variant-${now}-${Math.random().toString(36).slice(2, 8)}`,
      originMessageId: message.id,
      text: message.text,
      sources: (message.sources ?? []).map((source) => ({ ...source })),
      requestSnapshot: message.requestSnapshot,
      answerLanguage: message.requestSnapshot?.answerLanguage ?? answerLanguage,
      status: message.status === "error" ? "error" : message.status === "stopped" ? "stopped" : "completed",
      createdAt: now,
      updatedAt: now,
    };
    void updateConversationMetadata(activeRecord.id, {
      variants: [...(activeRecord.variants ?? []), variant],
    });
  }, [activeRecord, answerLanguage, updateConversationMetadata]);

  useEffect(() => {
    if (!showResetDialog) return;
    const handleDialogKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowResetDialog(false);
    };
    document.addEventListener("keydown", handleDialogKeyDown);
    resetCancelRef.current?.focus();
    return () => document.removeEventListener("keydown", handleDialogKeyDown);
  }, [showResetDialog]);

  // Global shortcuts: Ctrl/Cmd+K opens the Library with search focused;
  // Escape closes the topmost overlay layer.
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setActiveSidebarPanel("library");
        setIsSidebarOpen(true);
        window.requestAnimationFrame(() => {
          document.getElementById("library-search-input")?.focus();
        });
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "p") {
        event.preventDefault();
        setIsCommandPaletteOpen(true);
        return;
      }
      if (event.key === "Escape") {
        if (isCommandPaletteOpen) {
          setIsCommandPaletteOpen(false);
          return;
        }
        if (isHelpOpen) {
          setIsHelpOpen(false);
          return;
        }
        if (showResetDialog) {
          setShowResetDialog(false);
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isCommandPaletteOpen, isHelpOpen, showResetDialog]);

  const handleStopGenerating = useCallback(() => {
    const controller = requestAbortRef.current;
    if (!controller) return;

    requestAbortRef.current = null;
    controller.abort();
    setIsLoading(false);
    updateMessages((prev) =>
      prev.map((message) =>
        message.isStreaming
          ? {
              ...message,
              text: message.text || "Generation stopped.",
              isStreaming: false,
              status: "stopped" as const,
            }
          : message,
      ),
    );
  }, [updateMessages]);

  const handleSelectSample = useCallback((sample: SampleQuestion) => {
    if (sample.ticker !== undefined) {
      setSelectedTicker(sample.ticker || null);
    }
    if (sample.section !== undefined) {
      setSelectedSection(sample.section || null);
    }
    setInputText(sample.text);
    setIsSidebarOpen(false); // Close sidebar on mobile if clicked
    window.requestAnimationFrame(() => {
      document.getElementById("chat-textarea")?.focus();
    });
  }, [setInputText]);

  const handleCloseSidebar = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  const handleToggleSidebar = useCallback(() => {
    setIsSidebarOpen((open) => !open);
  }, []);

  const handleSelectTheme = useCallback((nextTheme: ThemePreference) => {
    setThemePreference(nextTheme);
  }, []);

  const handleReturnToConversation = useCallback(() => {
    setActiveView("conversation");
  }, []);

  const handleUseRetrievalQuestion = useCallback((question: string) => {
    setInputText(question);
    setActiveView("conversation");
    window.requestAnimationFrame(() => {
      document.getElementById("chat-textarea")?.focus();
    });
  }, [setInputText]);

  const handlePaletteNavigate = useCallback((view: PaletteView) => {
    setActiveView(view);
    if (view === "conversation") {
      window.requestAnimationFrame(() => document.getElementById("chat-textarea")?.focus());
    }
  }, []);

  const handlePaletteTemplate = useCallback((template: ResearchTemplate) => {
    setInputText(template.question);
    if (template.section) setSelectedSection(template.section);
    setAnswerLanguage(template.language);
    setActiveView("conversation");
    window.requestAnimationFrame(() => document.getElementById("chat-textarea")?.focus());
  }, [setInputText]);

  const handleRetryConnection = useCallback(async () => {
    try {
      await refreshHealth(true);
      // A recovered backend may also have recovered the session context.
      if (sessionContext === "unknown" || sessionContext === "missing") {
        void recheckSessionContext();
      }
    } catch {
      setIsBackendConnected(false);
      setIsPipelineReady(false);
    }
  }, [refreshHealth, recheckSessionContext, sessionContext]);

  const isStreaming = useMemo(
    () => messages.some((message) => message.isStreaming),
    [messages],
  );
  const scopeLabel = useMemo(() => {
    const labels: string[] = [];
    if (selectedTicker) labels.push(`Company: ${formatCompanyLabel(selectedTicker)}`);
    if (selectedSection) {
      labels.push(SECTION_METADATA[selectedSection]?.shortLabel || selectedSection);
    }
    return labels.join(" · ");
  }, [selectedSection, selectedTicker]);

  const hasExchanges = messages.length > 0;
  const latestEvidenceSources = useMemo(
    () => [...messages].reverse().find((message) => message.sender === "assistant" && message.sources?.length)?.sources ?? [],
    [messages],
  );
  const showContextBanner =
    activeView === "conversation" && hasExchanges &&
    (sessionContext === "checking" || isReadOnly);

  return (
    <div className="app-shell flex w-screen max-w-full h-dvh font-sans text-[var(--text-primary)] overflow-hidden bg-grid-pattern">
      {/* Collapsible Sidebar */}
      <Sidebar
        tickers={tickers}
        sections={sections}
        selectedTicker={selectedTicker}
        onSelectTicker={setSelectedTicker}
        selectedSection={selectedSection}
        onSelectSection={setSelectedSection}
        topK={topK}
        onChangeTopK={setTopK}
        enableComparative={enableComparative}
        onToggleComparative={setEnableComparative}
        onNewConversation={requestNewConversation}
        onSelectSample={handleSelectSample}
        healthData={healthData}
        isOpen={isSidebarOpen}
        onClose={handleCloseSidebar}
        isClearingSession={isClearingSession}
        activePanel={activeSidebarPanel}
        onChangePanel={setActiveSidebarPanel}
        conversations={conversations}
        activeConversationId={activeConversationId}
        storageMode={storageMode}
        storageWarning={storageWarning}
        saveIndicator={saveIndicator}
        onSelectConversation={handleSelectConversation}
        onOpenMessage={handleOpenMessage}
        onRenameConversation={renameConversation}
        onToggleBookmark={handleSidebarToggleBookmark}
        onDeleteConversation={(conversationId) => {
          void deleteConversation(conversationId);
        }}
        onExportConversation={handleExportConversation}
        onExportBackup={handleExportBackup}
        onImportBackup={handleImportBackup}
        onUpdateMetadata={updateConversationMetadata}
        writerStatus={writerStatus}
        onRequestWriter={requestLibraryWriter}
      />

      {/* Main chat window area */}
      <div className="w-0 flex-1 min-w-0 max-w-full flex flex-col h-full overflow-hidden">
        {/* Header toolbar */}
        <WorkspaceHeader
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={handleToggleSidebar}
          activeView={activeView}
          onSelectView={setActiveView}
          hasMessages={hasExchanges}
          isBackendConnected={isBackendConnected}
          isPipelineReady={isPipelineReady}
          companyCount={healthData?.corpus?.searchable_company_count ?? (tickers.length || undefined)}
          theme={themePreference}
          resolvedTheme={resolvedTheme}
          onSelectTheme={handleSelectTheme}
          isClearingSession={isClearingSession}
          onReset={requestNewConversation}
          onOpenHelp={() => setIsHelpOpen(true)}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        />
        {/* Content stream area */}
        <main
          aria-label="Research workspace"
          ref={scrollContainerRef}
          className="workspace-scroll flex-1 overflow-y-auto overflow-x-hidden min-h-0 relative z-10"
        >
          {showContextBanner && (
            <SessionContextBanner
              status={sessionContext}
              onRecheck={() => void recheckSessionContext()}
              onNewConversation={requestNewConversation}
            />
          )}
          <div className="workspace-main-grid">
            <div className="workspace-primary-column">
              <Suspense fallback={<WorkspacePanelFallback />}>
                {activeView === "retrieval" ? (
              <RetrievalLabPanel
                tickers={tickers}
                sections={sections}
                selectedTicker={selectedTicker}
                selectedSection={selectedSection}
                isBackendConnected={isBackendConnected}
                onUseQuestion={handleUseRetrievalQuestion}
              />
                ) : activeView === "documents" ? (
              <DocumentExplorerPanel tickers={tickers} sections={sections} />
                ) : activeView === "system" ? (
              <SystemInfoPanel />
                ) : activeView === "evaluation" ? (
              <EvaluationPanel />
                ) : activeView === "analytics" ? (
              <AnalyticsPanel />
                ) : activeView === "overview" ? (
              <OverviewPanel
                hasMessages={hasExchanges}
                companyCount={healthData?.corpus?.searchable_company_count ?? (tickers.length || null)}
                indexedChunkCount={healthData?.corpus?.indexed_chunk_count ?? null}
                onReturnToConversation={handleReturnToConversation}
                isBackendConnected={isBackendConnected}
                isPipelineReady={isPipelineReady}
                onRetryConnection={handleRetryConnection}
                onSelectQuestion={handleSelectSample}
              />
                ) : (
            /* Active Chat Stream */
            <div className="flex flex-col w-full min-h-full py-4 md:py-5 pb-6 relative">
              <Suspense
                fallback={
                  <div className="flex items-center gap-2 max-w-4xl mx-auto w-full px-3 py-4 text-sm text-slate-500 dark:text-slate-400" role="status">
                    <span className="w-2 h-2 rounded-full bg-brand-indigo animate-pulse" />
                    Loading response renderer…
                  </div>
                }
              >
                {messages.map((msg, index) => (
                  <ChatMessage
                    key={msg.id}
                    message={msg}
                    messageId={msg.id}
                    isLatest={index === messages.length - 1}
                    onRetry={isReadOnly ? undefined : handleRetry}
                    bookmarked={bookmarkedMessageIds.includes(msg.id)}
                    onToggleBookmark={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? () => toggleAnswerBookmark(msg.id)
                        : undefined
                    }
                    onSaveNote={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? (note) => handleSaveMessageNote(msg.id, note)
                        : undefined
                    }
                    onFeedback={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? (feedback) => handleMessageFeedback(msg.id, feedback)
                        : undefined
                    }
                    variants={activeRecord?.variants?.filter((variant) => variant.originMessageId === msg.id)}
                    onSaveVariant={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? () => handleSaveAnswerVariant(msg)
                        : undefined
                    }
                    tabIndex={0}
                  />
                ))}
              </Suspense>
              <div ref={messagesEndRef} />

              {/* Scroll to bottom button */}
              {showScrollButton && (
                <button
                  type="button"
                  onClick={() => scrollToBottom()}
                  className="ui-message-enter fixed bottom-32 right-6 md:right-8 min-h-10 min-w-10 p-2.5 rounded-full surface-raised border-[var(--border-subtle)] shadow-lg text-[var(--text-muted)] transition-colors cursor-pointer z-30"
                  aria-label="Scroll to bottom"
                >
                  <ChevronDown className="w-5 h-5" />
                </button>
              )}
            </div>
                )}
              </Suspense>
            </div>
            {activeView === "conversation" && latestEvidenceSources.length > 0 && (
              <EvidenceWorkspaceRail sources={latestEvidenceSources} />
            )}
          </div>
        </main>

        {/* The composer is a flex sibling, so it never overlays response evidence. */}
        {activeView !== "retrieval" && activeView !== "documents" && activeView !== "evaluation" && activeView !== "analytics" && activeView !== "system" && <div className="composer-shell flex-shrink-0 z-10">
          <ChatInput
            inputText={inputText}
            setInputText={setInputText}
            onSendMessage={handleSendMessage}
            onStopGenerating={handleStopGenerating}
            isLoading={isLoading}
            isStreaming={isStreaming}
            isBackendConnected={isBackendConnected}
            isPipelineReady={isPipelineReady}
            isReadOnly={isReadOnly && hasExchanges}
            readOnlyMessage={
              sessionContext === "missing"
                ? "The backend session for this saved conversation has expired. Start a new conversation to ask follow-up questions."
                : "The backend could not be reached. Check the connection again before asking follow-up questions."
            }
            answerLanguage={answerLanguage}
            onAnswerLanguageChange={setAnswerLanguage}
            showBanner={activeView === "conversation" && hasExchanges}
            scopeLabel={scopeLabel || undefined}
          />
        </div>}
      </div>

      <HelpDialog open={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
      <CommandPalette
        open={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onNavigate={handlePaletteNavigate}
        onTemplate={handlePaletteTemplate}
        onHelp={() => setIsHelpOpen(true)}
        onNewConversation={requestNewConversation}
      />

      {showResetDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overlay-backdrop p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShowResetDialog(false);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="reset-dialog-title"
            className="w-full max-w-md rounded-2xl surface-raised border-[var(--border-subtle)] p-5 shadow-2xl"
          >
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full state-warning-surface">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <h2 id="reset-dialog-title" className="text-base font-semibold text-[var(--text-primary)]">
                    Start a new conversation?
                  </h2>
                  <button
                    type="button"
                    aria-label="Close confirmation dialog"
                    onClick={() => setShowResetDialog(false)}
                    className="min-h-9 min-w-9 rounded-lg p-2 text-[var(--text-subtle)] hover:surface-muted-hover"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
                  This saves the current conversation to your local Library and
                  starts a fresh session. The new conversation does not carry
                  over the previous backend context. Your draft text and
                  filters are kept so you can edit and resend them.
                </p>
                <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <button
                    type="button"
                    ref={resetCancelRef}
                    onClick={() => setShowResetDialog(false)}
                    className="min-h-10 rounded-lg border-[var(--border-strong)] px-4 py-2 text-sm font-semibold text-[var(--text-primary)] hover:surface-muted-hover"
                  >
                    Keep conversation
                  </button>
                  <button
                    type="button"
                    onClick={() => void confirmNewConversation()}
                    className="min-h-10 rounded-lg primary-action-button px-4 py-2 text-sm font-semibold"
                  >
                    Start new conversation
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Backend session context banner. It explains that the local copy is
 * authoritative for reading while the backend memory is unavailable — it
 * never implies that local history was restored on the server.
 */
function SessionContextBanner({
  status,
  onRecheck,
  onNewConversation,
}: {
  status: SessionContextStatus;
  onRecheck: () => void;
  onNewConversation: () => void;
}) {
  if (status === "fresh" || status === "available") return null;
  if (status === "checking") {
    return (
      <div className="session-notice session-notice--checking" role="status" aria-live="polite">
        <RefreshCw className="h-4 w-4 animate-spin flex-shrink-0" aria-hidden="true" />
        <span className="min-w-0 flex-1">Checking whether the backend still holds this conversation's context…</span>
      </div>
    );
  }
  if (status === "missing") {
    return (
      <div className="session-notice session-notice--missing" role="status" aria-live="polite">
        <BookMarked className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
        <span className="min-w-0 flex-1">
          The backend session for this saved conversation has expired. You can
          still read, search, bookmark, and export the local copy below.
        </span>
        <button type="button" onClick={onNewConversation}>
          Start new conversation
        </button>
      </div>
    );
  }
  return (
    <div className="session-notice session-notice--unknown" role="status" aria-live="polite">
      <AlertTriangle className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
      <span className="min-w-0 flex-1">
        The backend could not be reached, so this conversation's context is
        unknown. Follow-up questions are paused until the connection is
        checked.
      </span>
      <button type="button" onClick={onRecheck}>
        Check connection again
      </button>
    </div>
  );
}
