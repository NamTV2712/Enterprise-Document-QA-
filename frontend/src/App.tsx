/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Menu,
  Sun,
  Moon,
  TrendingUp,
  Database,
  Layers,
  Sparkles,
  ChevronRight,
  GitFork,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RefreshCw,
} from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ChatMessage } from "./components/ChatMessage";
import { ChatInput, ConnectionBanner } from "./components/ChatInput";
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
  getApiBaseUrl,
} from "./lib/api";

export default function App() {
  const [sessionId, setSessionId] = useState<string>("");
  const [tickers, setTickers] = useState<string[]>([]);
  const [sections, setSections] = useState<string[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [topK, setTopK] = useState<number>(5);
  const [enableComparative, setEnableComparative] = useState<boolean>(true);

  const [inputText, setInputText] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(
    null,
  );
  const [isPipelineReady, setIsPipelineReady] = useState<boolean | null>(null);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isClearingSession, setIsClearingSession] = useState<boolean>(false);

  // Theme state
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const requestAbortRef = useRef<AbortController | null>(null);

  // Apply theme class
  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Handle initialization on first load
  useEffect(() => {
    // 1. Session ID creation/restoration
    let sid = localStorage.getItem("sec_qa_session_id");
    if (!sid) {
      sid = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      });
      localStorage.setItem("sec_qa_session_id", sid);
    }
    setSessionId(sid);

    const initData = async () => {
      try {
        const health = await checkHealth();
        setHealthData(health);
        setIsBackendConnected(true);
        setIsPipelineReady(health.pipeline_ready);

        const support = await getSupportedTickers();
        setTickers(support.tickers || []);
        setSections(support.sections || []);

        // 3. Load historical chat turns if session exists
        if (sid) {
          try {
            const history = await getSessionHistory(sid);
            if (history && history.turns && history.turns.length > 0) {
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
            }
          } catch (histError) {
            console.warn("Could not retrieve session history. Starting fresh.");
          }
        }
      } catch (err) {
        console.warn("FastAPI initialization check failed:", err);
        setIsBackendConnected(false);
        setIsPipelineReady(false);
      }
    };

    initData();
  }, []);

  useEffect(() => {
    return () => {
      const controller = requestAbortRef.current;
      requestAbortRef.current = null;
      controller?.abort();
    };
  }, []);

  // Scroll to bottom helper
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Helper to determine if query is comparative
  const isComparativeQuery = (question: string): boolean => {
    const keywords = [
      "compare",
      "vs",
      "versus",
      "both",
      "which company",
      "between",
    ];
    const lower = question.toLowerCase();
    return keywords.some((keyword) => lower.includes(keyword));
  };

  const handleSendMessage = async (text: string) => {
    if (!isBackendConnected || !isPipelineReady) return;

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
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        text: streamingText,
                      }
                    : m,
                ),
              );
            } else if (event.type === "done") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        isStreaming: false,
                      }
                    : m,
                ),
              );
              setIsLoading(false);
            } else if (event.type === "error") {
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
        if (requestAbortRef.current === controller) {
          requestAbortRef.current = null;
          setIsLoading(false);
        }
      }
    }

    if (controller.signal.aborted) return;

    // Refresh health details to get updated total turn counters, active sessions, etc.
    try {
      const health = await checkHealth();
      setHealthData(health);
    } catch (e) {
      console.warn("Could not refresh health data:", e);
    }
  };

  const handleNewConversation = async () => {
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
      const newSid = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
        /[xy]/g,
        (c) => {
          const r = (Math.random() * 16) | 0;
          const v = c === "x" ? r : (r & 0x3) | 0x8;
          return v.toString(16);
        },
      );
      localStorage.setItem("sec_qa_session_id", newSid);
      setSessionId(newSid);
      setMessages([]);
      setIsClearingSession(false);
      setSelectedTicker(null);
      setSelectedSection(null);

      // Refresh health
      try {
        const health = await checkHealth();
        setHealthData(health);
        setIsBackendConnected(true);
        setIsPipelineReady(health.pipeline_ready);
      } catch (e) {
        setIsBackendConnected(false);
      }
    }
  };

  const handleSelectSample = (sample: SampleQuestion) => {
    if (sample.ticker !== undefined) {
      setSelectedTicker(sample.ticker || null);
    }
    if (sample.section !== undefined) {
      setSelectedSection(sample.section || null);
    }
    setInputText(sample.text);
    setIsSidebarOpen(false); // Close sidebar on mobile if clicked
  };

  return (
    <div className="flex h-dvh bg-slate-50 dark:bg-slate-950 font-sans text-slate-800 dark:text-slate-100 overflow-hidden bg-grid-pattern">
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
        onNewConversation={handleNewConversation}
        onSelectSample={handleSelectSample}
        healthData={healthData}
        isBackendConnected={isBackendConnected}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        isClearingSession={isClearingSession}
      />

      {/* Main chat window area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Header toolbar */}
        <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white/85 dark:bg-[#12161C]/85 backdrop-blur-md px-4 md:px-6 flex items-center justify-between flex-shrink-0 z-20 shadow-xs">
          <div className="flex items-center gap-3">
            <button
              type="button"
              id="sidebar-toggle"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              aria-label={
                isSidebarOpen ? "Close search controls" : "Open search controls"
              }
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden text-slate-600 dark:text-slate-300 transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-600 dark:text-indigo-400 hidden lg:block" />
              <div className="flex flex-col lg:flex-row lg:items-center gap-0 lg:gap-2">
                <span className="font-semibold text-sm md:text-base text-slate-900 dark:text-white">
                  Enterprise Document QA
                </span>
                <span className="hidden lg:inline text-slate-300 dark:text-slate-700">
                  |
                </span>
                <span className="text-[10px] md:text-xs font-medium text-slate-500 dark:text-slate-400 font-mono">
                  API: {getApiBaseUrl()}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 md:gap-3">
            {/* Connection badge */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono font-medium">
              <span
                className={`w-2 h-2 rounded-full ${
                  isBackendConnected === null || isPipelineReady === null
                    ? "bg-slate-400"
                    : isBackendConnected && isPipelineReady
                      ? "bg-emerald-500"
                      : isBackendConnected
                        ? "bg-amber-500"
                        : "bg-rose-500"
                }`}
              />
              <span className="hidden sm:inline text-slate-600 dark:text-slate-300">
                {isBackendConnected === null || isPipelineReady === null
                  ? "Connecting..."
                  : isBackendConnected
                    ? isPipelineReady
                      ? "Pipeline: Ready"
                      : "Pipeline: Pending"
                    : "API: Offline"}
              </span>
            </div>

            {/* Dark mode switcher */}
            <button
              type="button"
              id="theme-switcher-btn"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
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
              onClick={handleNewConversation}
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-rose-500 text-slate-400 dark:text-slate-500 disabled:opacity-50 transition-colors cursor-pointer"
              title="Reset Conversation"
              aria-label="Reset conversation"
            >
              <RefreshCw
                className={`w-4 h-4 ${isClearingSession ? "animate-spin" : ""}`}
              />
            </button>
          </div>
        </header>

        {/* Content stream area */}
        <div className="flex-1 overflow-y-auto min-h-0 bg-[#F7F7F5] dark:bg-[#12161C] relative z-10">
          {messages.length === 0 ? (
            /* Onboarding splash screen with Framer Motion animations */
            <div
              className="max-w-3xl mx-auto px-5 pt-12 pb-56 md:pt-16 md:pb-72 space-y-8 relative z-10 font-sans animate-fade-in"
              id="onboarding-panel"
            >
              <div className="space-y-3 text-center">
                {isBackendConnected === null || isPipelineReady === null ? (
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-900/30 text-slate-600 dark:text-slate-400 font-mono text-[10px] font-bold uppercase tracking-wider">
                    <span>[STATUS: CONNECTING TO BACKEND]</span>
                  </div>
                ) : !isBackendConnected ? (
                  <Tooltip
                    content={`${getApiBaseUrl()} — Start the FastAPI backend and refresh to connect.`}
                  >
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded border border-red-300 dark:border-red-900 bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-rose-400 font-mono text-[10px] font-bold uppercase tracking-wider cursor-help">
                      <span>[STATUS: BACKEND UNREACHABLE]</span>
                    </div>
                  </Tooltip>
                ) : !isPipelineReady ? (
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded border border-amber-300 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400 font-mono text-[10px] font-bold uppercase tracking-wider">
                    <span>[STATUS: PIPELINE INITIALIZING]</span>
                  </div>
                ) : (
                  <Tooltip
                    content={`${getApiBaseUrl()} — Start the FastAPI backend and refresh to connect.`}
                  >
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded border border-verified-green/20 dark:border-[#1f5d4c]/30 bg-verified-green/5 dark:bg-[#1f5d4c]/10 text-verified-green dark:text-[#38a385] font-mono text-[10px] font-bold uppercase tracking-wider cursor-help">
                      <span>
                        [STATUS: LIVE — {tickers.length} COMPANIES INDEXED]
                      </span>
                    </div>
                  </Tooltip>
                )}
                <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-[#1B2430] dark:text-[#F7F7F5] py-1 font-serif">
                  SEC 10-K RAG Engine
                </h2>
                <p className="text-xs md:text-sm text-slate-550 dark:text-slate-400 max-w-xl mx-auto leading-relaxed font-mono">
                  Multi-entity vector indexing with grounded decomposition
                  summaries. Select or compose an SEC disclosure request to
                  begin.
                </p>
              </div>

              {/* Specification parameters info grid */}
              <div
                className="grid grid-cols-1 md:grid-cols-3 gap-4"
                id="features-cards"
              >
                <div className="group p-5 bg-white dark:bg-[#1B2430]/20 border border-slate-300 dark:border-slate-800 rounded-lg space-y-2.5 hover:border-brand-indigo/50 dark:hover:border-brand-indigo/50 hover:bg-indigo-500/[0.01] dark:hover:bg-brand-indigo/[0.02] hover:-translate-y-1 hover:shadow-[0_4px_20px_rgba(99,102,241,0.08)] transition-all duration-300 cursor-default shadow-3xs">
                  <Tooltip content="Scans individual 10-K blocks in business descriptions, risk matrices, and financial statements.">
                    <div className="w-8 h-8 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 group-hover:text-brand-indigo group-hover:bg-brand-indigo/15 group-hover:scale-105 transition-all duration-300 cursor-help">
                      <Database className="w-4 h-4" />
                    </div>
                  </Tooltip>
                  <h3 className="text-xs font-bold text-[#1B2430] dark:text-[#F7F7F5] uppercase tracking-wider font-sans group-hover:text-brand-indigo transition-colors duration-300">
                    Granular Chunk Scan
                  </h3>
                  <p className="text-[11px] text-slate-550 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300 leading-relaxed font-mono transition-colors duration-300">
                    Scans individual 10-K blocks in business descriptions, risk
                    matrices, and financial statements.
                  </p>
                </div>

                <div className="group p-5 bg-white dark:bg-[#1B2430]/20 border border-slate-300 dark:border-slate-800 rounded-lg space-y-2.5 hover:border-brand-indigo/50 dark:hover:border-brand-indigo/50 hover:bg-indigo-500/[0.01] dark:hover:bg-brand-indigo/[0.02] hover:-translate-y-1 hover:shadow-[0_4px_20px_rgba(99,102,241,0.08)] transition-all duration-300 cursor-default shadow-3xs">
                  <Tooltip content="Decomposes comparative requests into focused retrievals and presents the completed execution summary.">
                    <div className="w-8 h-8 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 group-hover:text-brand-indigo group-hover:bg-brand-indigo/15 group-hover:scale-105 transition-all duration-300 cursor-help">
                      <GitFork className="w-4 h-4" />
                    </div>
                  </Tooltip>
                  <h3 className="text-xs font-bold text-[#1B2430] dark:text-[#F7F7F5] uppercase tracking-wider font-sans group-hover:text-brand-indigo transition-colors duration-300">
                    Multi-Hop Querying
                  </h3>
                  <p className="text-[11px] text-slate-550 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300 leading-relaxed font-mono transition-colors duration-300">
                    Decomposes comparative requests into focused retrievals and
                    presents a grounded execution summary.
                  </p>
                </div>

                <div className="group p-5 bg-white dark:bg-[#1B2430]/20 border border-slate-300 dark:border-slate-800 rounded-lg space-y-2.5 hover:border-brand-indigo/50 dark:hover:border-brand-indigo/50 hover:bg-indigo-500/[0.01] dark:hover:bg-brand-indigo/[0.02] hover:-translate-y-1 hover:shadow-[0_4px_20px_rgba(99,102,241,0.08)] transition-all duration-300 cursor-default shadow-3xs">
                  <Tooltip content="All extracted disclosures are verified with alignment margins, item tags, and exact document indexes.">
                    <div className="w-8 h-8 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 group-hover:text-brand-indigo group-hover:bg-brand-indigo/15 group-hover:scale-105 transition-all duration-300 cursor-help">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  </Tooltip>
                  <h3 className="text-xs font-bold text-[#1B2430] dark:text-[#F7F7F5] uppercase tracking-wider font-sans group-hover:text-brand-indigo transition-colors duration-300">
                    Verifiable Sources
                  </h3>
                  <p className="text-[11px] text-slate-550 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300 leading-relaxed font-mono transition-colors duration-300">
                    All extracted disclosures are verified with alignment
                    margins, item tags, and exact document indexes.
                  </p>
                </div>
              </div>

              {/* ConnectionBanner in normal document flow BELOW the cards */}
              <div className="pt-4 max-w-2xl mx-auto">
                <ConnectionBanner
                  isBackendConnected={isBackendConnected}
                  isPipelineReady={isPipelineReady}
                />
              </div>
            </div>
          ) : (
            /* Active Chat Stream */
            <div className="flex flex-col w-full h-full divide-y divide-slate-200/50 dark:divide-slate-900/40 pb-36">
              {messages.map((msg, index) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  isLatest={index === messages.length - 1}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input anchor zone */}
        <div className="absolute bottom-0 inset-x-0 bg-transparent z-10 pointer-events-none">
          <div className="pointer-events-auto">
            <ChatInput
              inputText={inputText}
              setInputText={setInputText}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              isBackendConnected={isBackendConnected}
              isPipelineReady={isPipelineReady}
              showBanner={messages.length > 0}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
