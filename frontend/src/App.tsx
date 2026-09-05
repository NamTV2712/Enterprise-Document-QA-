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
import { AlertTriangle, ChevronDown, X } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ChatInput } from "./components/ChatInput";
import { SampleQuestion } from "./components/SampleQuestionChips";
import { OverviewPanel } from "./components/OverviewPanel";
import { WorkspaceHeader } from "./components/WorkspaceHeader";
import {
  Message,
  HealthResponse,
  RequestSnapshot,
  ThemePreference,
} from "./types";
import {
  checkHealth,
  getSupportedTickers,
  queryDecomposed,
  deleteSession,
  getSessionHistory,
  streamQuery,
} from "./lib/api";
import { formatCompanyLabel, SECTION_METADATA } from "./lib/displayMetadata";

const STREAM_FLUSH_INTERVAL_MS = 80;
const MAX_PERSISTED_MESSAGES = 50;
const MESSAGE_PERSIST_DEBOUNCE_MS = 180;
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

function isComparativeQuery(question: string): boolean {
  const lower = question.toLowerCase();
  return COMPARATIVE_KEYWORDS.some((keyword) => lower.includes(keyword));
}

// localStorage can throw in private browsing or when quota is exceeded;
// persistence failures must never crash the UI.
function safeSetItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    console.warn(`Could not persist "${key}" to localStorage:`, e);
  }
}

function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch (e) {
    console.warn(`Could not read "${key}" from localStorage:`, e);
    return null;
  }
}

function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    console.warn(`Could not remove "${key}" from localStorage:`, e);
  }
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

function getSystemTheme(): "light" | "dark" {
  return typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export default function App() {
  const [sessionId, setSessionId] = useState<string>("");
  const [tickers, setTickers] = useState<string[]>([]);
  const [sections, setSections] = useState<string[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [topK, setTopK] = useState<number>(5);
  const [enableComparative, setEnableComparative] = useState<boolean>(true);

  const [inputText, setInputText] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = safeGetItem("sec_qa_messages");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.slice(-MAX_PERSISTED_MESSAGES);
        }
      } catch {
        safeRemoveItem("sec_qa_messages");
      }
    }
    return [];
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
  const [activeView, setActiveView] = useState<"overview" | "conversation">(
    "overview",
  );

  // Theme state. Keep the preference separate from the resolved color so a
  // system preference can follow OS changes without overwriting user choice.
  const [themePreference, setThemePreference] = useState<ThemePreference>(() => {
    const saved = safeGetItem("theme");
    if (saved === "system" || saved === "light" || saved === "dark") {
      return saved;
    }
    return "system";
  });
  const [systemTheme, setSystemTheme] = useState<"light" | "dark">(
    getSystemTheme,
  );
  const resolvedTheme = themePreference === "system" ? systemTheme : themePreference;

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const requestAbortRef = useRef<AbortController | null>(null);
  const resetCancelRef = useRef<HTMLButtonElement>(null);
  const healthRequestRef = useRef<Promise<HealthResponse> | null>(null);
  const lastHealthRefreshRef = useRef(0);
  const [showScrollButton, setShowScrollButton] = useState<boolean>(false);

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
    safeSetItem("theme", themePreference);
  }, [resolvedTheme, themePreference]);

  // Persist messages to localStorage with size limit and cleanup
  useEffect(() => {
    // Streaming updates arrive every 80ms. Persist once the response finishes
    // (or is stopped) instead of serializing the full history for every flush.
    if (messages.some((message) => message.isStreaming)) return;

    const timeoutId = window.setTimeout(() => {
      if (messages.length === 0) {
        safeRemoveItem("sec_qa_messages");
        return;
      }
      const messagesToSave = messages.slice(-MAX_PERSISTED_MESSAGES);
      try {
        localStorage.setItem("sec_qa_messages", JSON.stringify(messagesToSave));
      } catch (e) {
        console.warn("Failed to save messages to localStorage:", e);
        // If storage full, clear old messages
        safeRemoveItem("sec_qa_messages");
      }
    }, MESSAGE_PERSIST_DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [messages]);

  // Handle initialization on first load
  useEffect(() => {
    const controller = new AbortController();

    // 1. Session ID creation/restoration
    let sid = safeGetItem("sec_qa_session_id");
    if (!sid) {
      sid = createSessionId();
      safeSetItem("sec_qa_session_id", sid);
    }
    setSessionId(sid);

    const initData = async () => {
      try {
        const health = await checkHealth(controller.signal);
        applyHealth(health);

        // Supported metadata and history are independent after readiness is
        // known, so avoid paying for their network latency serially.
        const [supportResult, historyResult] = await Promise.allSettled([
          getSupportedTickers(controller.signal),
          getSessionHistory(sid, controller.signal),
        ]);

        if (supportResult.status === "rejected") {
          throw supportResult.reason;
        }
        setTickers(supportResult.value.tickers || []);
        setSections(supportResult.value.sections || []);

        if (historyResult.status === "rejected") {
          const histError = historyResult.reason;
          if (
            histError instanceof DOMException &&
            histError.name === "AbortError"
          ) {
            return;
          }
          console.warn("Could not retrieve session history. Starting fresh.");
        } else {
          const history = historyResult.value;
          if (history?.turns?.length > 0) {
            const loadedMessages: Message[] = [];
            history.turns.forEach((turn, idx) => {
              loadedMessages.push({
                id: `u-${idx}-${Date.now()}`,
                sender: "user",
                text: turn.user,
              });
              loadedMessages.push({
                id: `a-${idx}-${Date.now()}`,
                sender: "assistant",
                text: turn.assistant,
                rewritten_query: turn.rewritten_query,
              });
            });
            setMessages(loadedMessages);
            setActiveView("conversation");
          }
        }
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

  // Scroll to bottom helper
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (activeView !== "conversation") return;

    // Repeated smooth-scroll animations overlap while tokens arrive every
    // 80ms. Batch the layout read/write to the next animation frame.
    const scroll = () => {
      messagesEndRef.current?.scrollIntoView({
        behavior: isLoading ? "auto" : "smooth",
      });
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
  }, [activeView, isLoading, messages]);

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

    const requestSnapshot: RequestSnapshot = snapshot ?? {
      ticker: selectedTicker,
      section: selectedSection,
      topK,
      enableComparative,
    };

    setActiveView("conversation");
    requestAbortRef.current?.abort();
    const controller = new AbortController();
    requestAbortRef.current = controller;
    const isCurrentRequest = () =>
      requestAbortRef.current === controller && !controller.signal.aborted;

    // Add user message to chat list
    const userMsgId = "user-" + Date.now();
    const userMessage: Message = {
      id: userMsgId,
      sender: "user",
      text: text,
      requestSnapshot,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    const isComparative =
      requestSnapshot.enableComparative && isComparativeQuery(text);
    const assistantMsgId = "assistant-" + Date.now();

    const payload = {
      question: text,
      ticker: requestSnapshot.ticker,
      section: requestSnapshot.section,
      top_k: requestSnapshot.topK,
      session_id: sessionId,
    };

    if (isComparative) {
      // Create initial loading/placeholder message for Decomposed POST
      const placeholder: Message = {
        id: assistantMsgId,
        sender: "assistant",
        text: "",
        subQueries: [],
        wasDecomposed: true,
        isStreaming: true,
        status: "streaming",
        requestSnapshot,
      };
      setMessages((prev) => [...prev, placeholder]);

      try {
        const response = await queryDecomposed(payload, controller.signal);
        if (!isCurrentRequest()) return;
        setMessages((prev) =>
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
                  isStreaming: false,
                  status: "completed",
                }
              : m,
          ),
        );
      } catch (err: any) {
        if (!isCurrentRequest()) return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  text: "We couldn't complete this comparison. Check the connection and try again.",
                  error: true,
                  isStreaming: false,
                  status: "error",
                  errorDetail: err?.message || String(err),
                  retryText: text,
                }
              : m,
          ),
        );
      } finally {
        if (requestAbortRef.current === controller) {
          requestAbortRef.current = null;
          setIsLoading(false);
        }
      }
    } else {
      // Streamed query over POST EventStream
      const placeholder: Message = {
        id: assistantMsgId,
        sender: "assistant",
        text: "",
        isStreaming: true,
        status: "streaming",
        requestSnapshot,
      };
      setMessages((prev) => [...prev, placeholder]);

      let streamingText = "";
      let sourcesList: any[] = [];
      let pendingFlush: ReturnType<typeof setTimeout> | null = null;

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
            setMessages((prev) =>
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
              sourcesList = event.data || [];
              setMessages((prev) =>
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
              scheduleStreamingFlush();
            } else if (event.type === "done") {
              cancelPendingFlush();
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        text: streamingText,
                        isStreaming: false,
                        status: "completed",
                      }
                    : m,
                ),
              );
              setIsLoading(false);
            } else if (event.type === "error") {
              cancelPendingFlush();
              setMessages((prev) =>
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
                        status: "error",
                        errorDetail: event.data,
                        retryText: text,
                      }
                    : m,
                ),
              );
              setIsLoading(false);
            }
          },
          (error) => {
            if (!isCurrentRequest()) return;
            cancelPendingFlush();
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                        text:
                          streamingText +
                          (streamingText ? "\n\n" : "") +
                          "The connection closed before the answer finished. Please try again.",
                      isStreaming: false,
                      error: true,
                      status: "error",
                      errorDetail: error.message,
                      retryText: text,
                    }
                  : m,
              ),
            );
            setIsLoading(false);
          },
          controller.signal,
        );
      } catch (err: any) {
        if (!isCurrentRequest()) return;
        cancelPendingFlush();
        setMessages((prev) =>
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
                    status: "error",
                    errorDetail: err?.message || String(err),
                    retryText: text,
                  }
              : m,
          ),
        );
        setIsLoading(false);
      } finally {
        cancelPendingFlush();
        if (requestAbortRef.current === controller) {
          requestAbortRef.current = null;
          setIsLoading(false);
        }
      }
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
    enableComparative,
    isBackendConnected,
    isPipelineReady,
    selectedSection,
    selectedTicker,
    sessionId,
    topK,
    refreshHealth,
  ]);

  // Stable retry callback so memoized ChatMessage items skip re-renders;
  // the ref indirection keeps access to the latest send handler.
  const handleSendMessageRef = useRef(handleSendMessage);
  handleSendMessageRef.current = handleSendMessage;
  const handleRetry = useCallback((text: string, snapshot?: RequestSnapshot) => {
    setInputText(text);
    handleSendMessageRef.current(text, snapshot);
  }, []);

  const handleNewConversation = useCallback(async () => {
    requestAbortRef.current?.abort();
    requestAbortRef.current = null;
    setIsLoading(false);
    setIsClearingSession(true);
    try {
      if (sessionId) {
        await deleteSession(sessionId).catch((e) =>
          console.warn("Could not delete session on backend:", e),
        );
      }
    } catch (err) {
      console.error("Session clearance exception:", err);
    } finally {
      const newSid = createSessionId();
      safeSetItem("sec_qa_session_id", newSid);
      setSessionId(newSid);
      setMessages([]);
      safeRemoveItem("sec_qa_messages");
      setActiveView("overview");
      setIsClearingSession(false);
      setSelectedTicker(null);
      setSelectedSection(null);

      // Refresh health, sharing any in-flight request and avoiding duplicate
      // checks during rapid resets.
      try {
        await refreshHealth(true);
      } catch (e) {
        setIsBackendConnected(false);
        setIsPipelineReady(false);
      }
    }
  }, [refreshHealth, sessionId]);

  const requestNewConversation = useCallback(() => {
    if (messages.length === 0) {
      void handleNewConversation();
      return;
    }
    setShowResetDialog(true);
  }, [handleNewConversation, messages.length]);

  const confirmNewConversation = useCallback(async () => {
    setShowResetDialog(false);
    await handleNewConversation();
  }, [handleNewConversation]);

  useEffect(() => {
    if (!showResetDialog) return;
    const handleDialogKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowResetDialog(false);
    };
    document.addEventListener("keydown", handleDialogKeyDown);
    resetCancelRef.current?.focus();
    return () => document.removeEventListener("keydown", handleDialogKeyDown);
  }, [showResetDialog]);

  const handleStopGenerating = useCallback(() => {
    const controller = requestAbortRef.current;
    if (!controller) return;

    requestAbortRef.current = null;
    controller.abort();
    setIsLoading(false);
    setMessages((prev) =>
      prev.map((message) =>
        message.isStreaming
          ? {
              ...message,
              text: message.text || "Generation stopped.",
              isStreaming: false,
              status: "stopped",
            }
          : message,
      ),
    );
  }, []);

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
  }, []);

  const handleCloseSidebar = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  const handleToggleSidebar = useCallback(() => {
    setIsSidebarOpen((open) => !open);
  }, []);

  const handleToggleTheme = useCallback(() => {
    setThemePreference((current) =>
      current === "system" ? "light" : current === "light" ? "dark" : "system",
    );
  }, []);

  const handleReturnToConversation = useCallback(() => {
    setActiveView("conversation");
  }, []);

  const handleRetryConnection = useCallback(async () => {
    try {
      await refreshHealth(true);
    } catch {
      setIsBackendConnected(false);
      setIsPipelineReady(false);
    }
  }, [refreshHealth]);

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
      />

      {/* Main chat window area */}
      <div className="w-0 flex-1 min-w-0 max-w-full flex flex-col h-full overflow-hidden">
        {/* Header toolbar */}
        <WorkspaceHeader
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={handleToggleSidebar}
          activeView={activeView}
          onSelectView={setActiveView}
          hasMessages={messages.length > 0}
          isBackendConnected={isBackendConnected}
          isPipelineReady={isPipelineReady}
          companyCount={tickers.length || undefined}
          theme={themePreference}
          resolvedTheme={resolvedTheme}
          onToggleTheme={handleToggleTheme}
          isClearingSession={isClearingSession}
          onReset={requestNewConversation}
        />
        {/* Content stream area */}
        <main
          aria-label="Research workspace"
          ref={scrollContainerRef}
          className="workspace-scroll flex-1 overflow-y-auto overflow-x-hidden min-h-0 relative z-10"
        >
          {activeView === "overview" ? (
            <OverviewPanel
              hasMessages={messages.length > 0}
              companyCount={tickers.length}
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
                    onRetry={handleRetry}
                  />
                ))}
              </Suspense>
              <div ref={messagesEndRef} />

              {/* Scroll to bottom button */}
              {showScrollButton && (
                <button
                  type="button"
                  onClick={scrollToBottom}
                  className="ui-message-enter fixed bottom-32 right-6 md:right-8 min-h-10 min-w-10 p-2.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors cursor-pointer z-30"
                  aria-label="Scroll to bottom"
                >
                  <ChevronDown className="w-5 h-5" />
                </button>
              )}
            </div>
          )}
        </main>

        {/* The composer is a flex sibling, so it never overlays response evidence. */}
        <div className="composer-shell flex-shrink-0 z-10">
          <ChatInput
            inputText={inputText}
            setInputText={setInputText}
            onSendMessage={handleSendMessage}
            onStopGenerating={handleStopGenerating}
            isLoading={isLoading}
            isStreaming={isStreaming}
            isBackendConnected={isBackendConnected}
            isPipelineReady={isPipelineReady}
            showBanner={activeView === "conversation" && messages.length > 0}
            scopeLabel={scopeLabel || undefined}
          />
        </div>
      </div>

      {showResetDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#26324A]/30 p-4 backdrop-blur-sm dark:bg-black/50"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShowResetDialog(false);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="reset-dialog-title"
            className="w-full max-w-md rounded-2xl border border-slate-200 bg-[#FCFBF8] p-5 shadow-2xl dark:border-slate-700 dark:bg-[#1E2738]"
          >
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <h2 id="reset-dialog-title" className="text-base font-semibold text-[#26324A] dark:text-[#FCFBF8]">
                    Start a new conversation?
                  </h2>
                  <button
                    type="button"
                    aria-label="Close confirmation dialog"
                    onClick={() => setShowResetDialog(false)}
                    className="min-h-9 min-w-9 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                  This clears the current messages and starts a fresh session.
                  Your backend history for this conversation will also be removed.
                </p>
                <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <button
                    type="button"
                    ref={resetCancelRef}
                    onClick={() => setShowResetDialog(false)}
                    className="min-h-10 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Keep conversation
                  </button>
                  <button
                    type="button"
                    onClick={confirmNewConversation}
                    className="min-h-10 rounded-lg bg-[#26324A] px-4 py-2 text-sm font-semibold text-[#FCFBF8] hover:opacity-90 dark:bg-[#FCFBF8] dark:text-[#26324A]"
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
