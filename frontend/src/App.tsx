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
import {
  Menu,
  Sun,
  Moon,
  TrendingUp,
  Database,
  GitFork,
  CheckCircle2,
  HelpCircle,
  RefreshCw,
  BookOpen,
  MessageSquare,
  ChevronDown,
  AlertTriangle,
  X,
} from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ChatInput } from "./components/ChatInput";
import { ConnectionStatus } from "./components/ConnectionStatus";
import { Tooltip } from "./components/Tooltip";
import { SampleQuestion } from "./components/SampleQuestionChips";
import { Message, HealthResponse } from "./types";
import {
  checkHealth,
  getSupportedTickers,
  queryDecomposed,
  deleteSession,
  getSessionHistory,
  streamQuery,
} from "./lib/api";

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

  // Theme state
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = safeGetItem("theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

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

  // Apply theme class
  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    safeSetItem("theme", theme);
  }, [theme]);

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
      sid = crypto.randomUUID();
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

  const handleSendMessage = useCallback(async (text: string) => {
    if (!isBackendConnected || !isPipelineReady) return;

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
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    const isComparative = enableComparative && isComparativeQuery(text);
    const assistantMsgId = "assistant-" + Date.now();

    const payload = {
      question: text,
      ticker: selectedTicker,
      section: selectedSection,
      top_k: topK,
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
                  text: `Failed to complete comparative query analysis: ${err?.message || err}`,
                  error: true,
                  isStreaming: false,
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
                          `\n\n[RAG Pipeline Error]: ${event.data}`,
                        isStreaming: false,
                        error: true,
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
                        `\n\n[SSE Connection Failure]: ${error.message}`,
                      isStreaming: false,
                      error: true,
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
                    `\n\n[General Retrieval Error]: ${err?.message || err}`,
                  isStreaming: false,
                  error: true,
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
  const handleRetry = useCallback((text: string) => {
    setInputText(text);
    handleSendMessageRef.current(text);
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
      const newSid = crypto.randomUUID();
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
  }, []);

  const handleCloseSidebar = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  const isStreaming = useMemo(
    () => messages.some((message) => message.isStreaming),
    [messages],
  );

  return (
    <div className="flex w-screen max-w-full h-dvh bg-[#FCFBF8] dark:bg-[#171D2B] font-sans text-slate-800 dark:text-slate-100 overflow-hidden bg-grid-pattern">
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
        <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white/85 dark:bg-[#171D2B]/85 backdrop-blur-md px-4 md:px-6 flex items-center justify-between flex-shrink-0 z-20 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              id="sidebar-toggle"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              aria-controls="control-sidebar"
              aria-expanded={isSidebarOpen}
              aria-label={
                isSidebarOpen ? "Close search controls" : "Open search controls"
              }
              className="min-h-9 min-w-9 p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden text-slate-600 dark:text-slate-300 transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 min-w-0">
              <TrendingUp className="w-5 h-5 text-indigo-600 dark:text-indigo-400 hidden lg:block" />
              <span className="font-semibold text-sm md:text-base text-slate-900 dark:text-white truncate">
                Enterprise Document QA
              </span>
            </div>
            {messages.length > 0 && activeView === "conversation" && (
              <button
                type="button"
                onClick={() => setActiveView("overview")}
                aria-label="Show overview"
                className="lg:hidden min-h-9 inline-flex items-center gap-1.5 px-2 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <BookOpen className="w-4 h-4" />
                <span className="hidden sm:inline">Overview</span>
              </button>
            )}
            <nav
              className="hidden lg:flex items-center gap-1 ml-2 pl-3 border-l border-slate-200 dark:border-slate-700"
              aria-label="Workspace views"
            >
              <button
                type="button"
                onClick={() => setActiveView("overview")}
                aria-pressed={activeView === "overview"}
                  className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  activeView === "overview"
                    ? "bg-brand-indigo/10 text-brand-indigo"
                    : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                Overview
              </button>
              <button
                type="button"
                onClick={() => setActiveView("conversation")}
                disabled={messages.length === 0}
                aria-pressed={activeView === "conversation"}
                  className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
                  activeView === "conversation"
                    ? "bg-brand-indigo/10 text-brand-indigo"
                    : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                } disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Conversation
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-2 md:gap-3">
            <ConnectionStatus
              isBackendConnected={isBackendConnected}
              isPipelineReady={isPipelineReady}
              companyCount={tickers.length || undefined}
            />

            {/* Dark mode switcher */}
            <button
              type="button"
              id="theme-switcher-btn"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-pressed={theme === "dark"}
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
              title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4" />
              ) : (
                <Moon className="w-4 h-4" />
              )}
            </button>

            {/* Quick clean chat */}
            <button
              type="button"
              id="quick-reset-btn"
              disabled={isClearingSession || messages.length === 0}
              aria-busy={isClearingSession}
              onClick={requestNewConversation}
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-rose-500 text-slate-400 dark:text-slate-500 disabled:opacity-50 transition-colors cursor-pointer"
              title="Start a new conversation"
              aria-label="Start a new conversation"
            >
              <RefreshCw
                className={`w-4 h-4 ${isClearingSession ? "animate-spin" : ""}`}
              />
            </button>
          </div>
        </header>

        {/* Content stream area */}
        <main
          aria-label="Research workspace"
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 bg-[#FCFBF8] dark:bg-[#171D2B] relative z-10"
        >
          {activeView === "overview" ? (
            /* Lightweight onboarding splash screen */
            <div
              className="w-full max-w-3xl mx-auto px-5 py-8 md:py-12 space-y-7 relative z-10 font-sans animate-fade-in"
              id="onboarding-panel"
            >
              <div className="space-y-3 text-center">
                {messages.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setActiveView("conversation")}
                    className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-brand-indigo hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors cursor-pointer"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    Return to conversation
                  </button>
                )}
                <p className="mx-auto max-w-lg text-xs font-medium text-slate-500 dark:text-slate-400">
                  Choose an optional company or filing section in the sidebar,
                  then ask your question below. The workspace keeps the source
                  excerpts beside every grounded answer.
                </p>
                <h2 className="max-w-full text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-[#26324A] dark:text-[#FCFBF8] py-1 font-serif break-words">
                  Ask questions. Verify every answer.
                </h2>
                <p className="text-sm md:text-base text-slate-600 dark:text-slate-400 max-w-xl mx-auto leading-relaxed font-sans">
                  Research SEC 10-K filings across {tickers.length || 44} searchable
                  companies with cited evidence and a clear retrieval trail.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-2.5 rounded-xl border border-brand-indigo/15 bg-white/80 dark:bg-[#26324A]/20 p-3.5 shadow-3xs">
                <span className="text-sm font-semibold text-[#26324A] dark:text-[#FCFBF8]">
                  Start with a natural-language question
                </span>
                <span className="hidden sm:inline text-slate-300 dark:text-slate-600">·</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  Press Enter to search, Shift+Enter for a new line
                </span>
              </div>

              {/* Specification parameters info grid */}
              <div
                className="grid grid-cols-1 md:grid-cols-3 gap-4"
                id="features-cards"
              >
                <article className="group p-5 bg-white dark:bg-[#26324A]/20 border border-slate-300 dark:border-slate-800 rounded-lg space-y-2.5 hover:border-brand-indigo/50 dark:hover:border-brand-indigo/50 hover:bg-indigo-500/[0.01] dark:hover:bg-brand-indigo/[0.02] hover:-translate-y-1 hover:shadow-[0_4px_20px_rgba(91,99,211,0.08)] transition-all duration-300 cursor-default shadow-3xs">
                  <Tooltip content="Scans individual 10-K blocks in business descriptions, risk matrices, and financial statements.">
                    <div className="w-8 h-8 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 group-hover:text-brand-indigo group-hover:bg-brand-indigo/15 group-hover:scale-105 transition-all duration-300 cursor-help">
                      <Database className="w-4 h-4" />
                    </div>
                  </Tooltip>
                  <h3 className="text-sm font-bold text-[#26324A] dark:text-[#FCFBF8] font-sans group-hover:text-brand-indigo transition-colors duration-300">
                    Granular Chunk Scan
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300 leading-relaxed font-sans transition-colors duration-300">
                    Scans individual 10-K blocks in business descriptions, risk
                    matrices, and financial statements.
                  </p>
                </article>

                <article className="group p-5 bg-white dark:bg-[#26324A]/20 border border-slate-300 dark:border-slate-800 rounded-lg space-y-2.5 hover:border-brand-indigo/50 dark:hover:border-brand-indigo/50 hover:bg-indigo-500/[0.01] dark:hover:bg-brand-indigo/[0.02] hover:-translate-y-1 hover:shadow-[0_4px_20px_rgba(91,99,211,0.08)] transition-all duration-300 cursor-default shadow-3xs">
                  <Tooltip content="Decomposes comparative requests into focused retrievals and presents the completed execution summary.">
                    <div className="w-8 h-8 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 group-hover:text-brand-indigo group-hover:bg-brand-indigo/15 group-hover:scale-105 transition-all duration-300 cursor-help">
                      <GitFork className="w-4 h-4" />
                    </div>
                  </Tooltip>
                  <h3 className="text-sm font-bold text-[#26324A] dark:text-[#FCFBF8] font-sans group-hover:text-brand-indigo transition-colors duration-300">
                    Multi-Hop Querying
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300 leading-relaxed font-sans transition-colors duration-300">
                    Decomposes comparative requests into focused retrievals and
                    presents a grounded execution summary.
                  </p>
                </article>

                <article className="group p-5 bg-white dark:bg-[#26324A]/20 border border-slate-300 dark:border-slate-800 rounded-lg space-y-2.5 hover:border-brand-indigo/50 dark:hover:border-brand-indigo/50 hover:bg-indigo-500/[0.01] dark:hover:bg-brand-indigo/[0.02] hover:-translate-y-1 hover:shadow-[0_4px_20px_rgba(91,99,211,0.08)] transition-all duration-300 cursor-default shadow-3xs">
                  <Tooltip content="All extracted disclosures are verified with alignment margins, item tags, and exact document indexes.">
                    <div className="w-8 h-8 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 group-hover:text-brand-indigo group-hover:bg-brand-indigo/15 group-hover:scale-105 transition-all duration-300 cursor-help">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  </Tooltip>
                  <h3 className="text-sm font-bold text-[#26324A] dark:text-[#FCFBF8] font-sans group-hover:text-brand-indigo transition-colors duration-300">
                    Verifiable Sources
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300 leading-relaxed font-sans transition-colors duration-300">
                    Every answer keeps the retrieved filing excerpts visible so
                    you can inspect the source text behind each claim.
                  </p>
                </article>
              </div>

              <details className="group rounded-xl border border-brand-indigo/20 bg-brand-indigo/[0.035] dark:bg-brand-indigo/[0.06] p-4 md:p-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-bold text-brand-indigo [&::-webkit-details-marker]:hidden">
                  <span className="flex items-center gap-2">
                    <HelpCircle className="w-4 h-4" />
                    How to read the workspace
                  </span>
                  <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
                </summary>
                <div className="ui-expand-enter grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 text-sm leading-relaxed text-slate-600 dark:text-slate-350">
                  <p>
                    <strong className="block text-slate-800 dark:text-slate-100">1. Choose scope</strong>
                    Select a company and 10-K section, or leave both on All for
                    discovery and comparisons.
                  </p>
                  <p>
                    <strong className="block text-slate-800 dark:text-slate-100">2. Ask naturally</strong>
                    Comparisons can be decomposed into focused sub-queries before
                    a grounded summary is produced.
                  </p>
                  <p>
                    <strong className="block text-slate-800 dark:text-slate-100">3. Verify evidence</strong>
                    Open the evidence panel to read source excerpts. Rank scores
                    order results; they are not confidence percentages.
                  </p>
                </div>
                <p className="md:col-span-3 text-xs text-slate-500 dark:text-slate-400 border-t border-brand-indigo/10 pt-3">
                  Research demo only · Answers may be incomplete and are not
                  financial advice.
                </p>
              </details>
            </div>
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
        <div className="flex-shrink-0 bg-[#FCFBF8] dark:bg-[#171D2B] z-10">
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
