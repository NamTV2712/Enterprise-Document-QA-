/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  SlidersHorizontal,
  FileSpreadsheet,
  X,
  Compass,
  ChevronDown,
  Check,
  Building2,
  Search,
  HelpCircle,
  Settings2,
  BookOpen,
} from "lucide-react";
import { SampleQuestionChips, SampleQuestion } from "./SampleQuestionChips";
import { HealthResponse } from "../types";
import { Tooltip } from "./Tooltip";
import { BrandMark } from "./BrandMark";
import { SidebarFooter } from "./SidebarFooter";
import { ConversationLibrary } from "./ConversationLibrary";
import {
  ConversationRecord,
  ConversationStorageMode,
} from "../lib/conversationStore";
import { SaveIndicator } from "../hooks/useConversationLibrary";
import {
  ALL_SECTIONS_DESCRIPTION,
  COMPANY_NAMES,
  formatCompanyLabel,
  SECTION_METADATA,
} from "../lib/displayMetadata";

interface SidebarProps {
  tickers: string[];
  sections: string[];
  selectedTicker: string | null;
  onSelectTicker: (ticker: string | null) => void;
  selectedSection: string | null;
  onSelectSection: (section: string | null) => void;
  topK: number;
  onChangeTopK: (k: number) => void;
  enableComparative: boolean;
  onToggleComparative: (val: boolean) => void;
  onNewConversation: () => void;
  onSelectSample: (question: SampleQuestion) => void;
  healthData: HealthResponse | null;
  isOpen: boolean;
  onClose: () => void;
  isClearingSession: boolean;
  activePanel: "research" | "library";
  onChangePanel: (panel: "research" | "library") => void;
  conversations: ConversationRecord[];
  activeConversationId: string;
  storageMode: ConversationStorageMode;
  storageWarning: string | null;
  saveIndicator?: SaveIndicator;
  onSelectConversation: (conversation: ConversationRecord) => void;
  onOpenMessage?: (conversationId: string, messageId: string) => void;
  onRenameConversation: (conversationId: string, title: string) => void;
  onToggleBookmark: (conversationId: string, messageId: string) => void;
  onDeleteConversation: (conversationId: string) => void;
  onExportConversation: (conversation: ConversationRecord) => void;
}

const SidebarBase: React.FC<SidebarProps> = ({
  tickers,
  sections,
  selectedTicker,
  onSelectTicker,
  selectedSection,
  onSelectSection,
  topK,
  onChangeTopK,
  enableComparative,
  onToggleComparative,
  onNewConversation,
  onSelectSample,
  healthData,
  isOpen,
  onClose,
  isClearingSession,
  activePanel,
  onChangePanel,
  conversations,
  activeConversationId,
  storageMode,
  storageWarning,
  saveIndicator,
  onSelectConversation,
  onOpenMessage,
  onRenameConversation,
  onToggleBookmark,
  onDeleteConversation,
  onExportConversation,
}) => {
  const minSidebarWidth = 280;
  const maxSidebarWidth = 480;
  const [tickerDropdownOpen, setTickerDropdownOpen] = useState(false);
  const [sectionDropdownOpen, setSectionDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    let savedWidth = 0;
    try {
      savedWidth = Number(localStorage.getItem("sec_qa_sidebar_width"));
    } catch {
      savedWidth = 0;
    }
    return Number.isFinite(savedWidth) && savedWidth >= minSidebarWidth
      ? Math.min(savedWidth, maxSidebarWidth)
      : 320;
  });
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    if (!tickerDropdownOpen) {
      setSearchQuery("");
    }
  }, [tickerDropdownOpen]);

  const tickerRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLDivElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const availableSections = useMemo(
    () =>
      Object.entries(SECTION_METADATA).filter(
        ([value]) => sections.length === 0 || sections.includes(value),
      ),
    [sections],
  );
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredTickers = useMemo(
    () =>
      [...tickers]
        .sort((a, b) =>
          (COMPANY_NAMES[a] || a).localeCompare(COMPANY_NAMES[b] || b),
        )
        .filter((ticker) =>
          `${ticker} ${COMPANY_NAMES[ticker] || ""}`
            .toLowerCase()
            .includes(normalizedSearch),
        ),
    [normalizedSearch, tickers],
  );

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        tickerRef.current &&
        !tickerRef.current.contains(event.target as Node)
      ) {
        setTickerDropdownOpen(false);
      }
      if (
        sectionRef.current &&
        !sectionRef.current.contains(event.target as Node)
      ) {
        setSectionDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("sec_qa_sidebar_width", String(sidebarWidth));
    } catch (e) {
      console.warn("Could not persist sidebar width:", e);
    }
  }, [sidebarWidth]);

  useEffect(() => {
    if (!isResizing) return;

    const handlePointerMove = (event: PointerEvent) => {
      const sidebarLeft = sidebarRef.current?.getBoundingClientRect().left ?? 0;
      const nextWidth = Math.min(
        Math.max(event.clientX - sidebarLeft, minSidebarWidth),
        maxSidebarWidth,
      );
      setSidebarWidth(nextWidth);
    };
    const stopResizing = () => setIsResizing(false);

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResizing);
    return () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResizing);
    };
  }, [isResizing]);

  useEffect(() => {
    if (!isOpen) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(
        sidebarRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), [href], [tabindex]:not([tabindex="-1"])',
        ) || [],
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    sidebarRef.current?.querySelector<HTMLElement>("button")?.focus();

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus();
    };
  }, [isOpen, onClose]);

  const resizeWithKeyboard = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const direction = event.key === "ArrowLeft" ? -16 : 16;
    setSidebarWidth((current) =>
      Math.min(Math.max(current + direction, minSidebarWidth), maxSidebarWidth),
    );
  };

  return (
    <>
      {/* Mobile Sidebar Overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          aria-hidden="true"
          className="sidebar-overlay fixed inset-0 z-40 lg:hidden transition-opacity"
        />
      )}

      <aside
        ref={sidebarRef}
        id="control-sidebar"
        aria-labelledby={activePanel === "research" ? "search-controls-heading" : "library-heading"}
        className={`sidebar-shell fixed inset-y-0 left-0 flex flex-col z-45 lg:static lg:translate-x-0 ${
          isResizing ? "transition-none" : "transition-transform duration-300"
        } ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ width: `min(${sidebarWidth}px, calc(100vw - 2rem))` }}
      >
        <div
          role="separator"
          aria-label="Resize search controls"
          aria-orientation="vertical"
          aria-valuemin={minSidebarWidth}
          aria-valuemax={maxSidebarWidth}
          aria-valuenow={sidebarWidth}
          tabIndex={0}
          onPointerDown={() => setIsResizing(true)}
          onKeyDown={resizeWithKeyboard}
          className="hidden lg:flex absolute inset-y-0 -right-1 z-50 w-2 cursor-col-resize items-center justify-center outline-none group"
        >
          <span className="h-12 w-0.5 rounded-full bg-slate-300 dark:bg-slate-700 opacity-0 group-hover:opacity-100 group-focus:opacity-100 group-active:opacity-100 transition-opacity" />
        </div>
        {/* Header */}
        <div className="sidebar-header p-4 md:p-5 flex items-center justify-between backdrop-blur-md">
          <div className="flex items-center gap-2.5">
            <BrandMark size="md" />
            <div>
              <h1 className="sidebar-brand-title text-xs font-black tracking-tight uppercase font-serif">
                SEC RAG Engine
              </h1>
              <span className="sidebar-brand-subtitle text-xs font-medium">
                SEC 10-K Research
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close search controls"
            className="min-h-9 min-w-9 p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <nav className="sidebar-tabs" aria-label="Workspace views" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activePanel === "research"}
            className={`sidebar-tab ${activePanel === "research" ? "is-active" : ""}`}
            onClick={() => onChangePanel("research")}
          >
            <Compass className="h-4 w-4" />
            Research
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activePanel === "library"}
            className={`sidebar-tab ${activePanel === "library" ? "is-active" : ""}`}
            onClick={() => onChangePanel("library")}
          >
            <BookOpen className="h-4 w-4" />
            Library
            {conversations.length > 0 && <span className="sidebar-tab-count">{conversations.length}</span>}
          </button>
        </nav>

        {activePanel === "library" ? (
          <div className="flex-1 overflow-y-auto p-4 md:p-5">
            <ConversationLibrary
              conversations={conversations}
              activeConversationId={activeConversationId}
              storageMode={storageMode}
              storageWarning={storageWarning}
              saveIndicator={saveIndicator}
              onSelect={onSelectConversation}
              onRename={onRenameConversation}
              onToggleBookmark={onToggleBookmark}
              onDelete={onDeleteConversation}
              onExport={onExportConversation}
              onOpenMessage={onOpenMessage}
              onClose={() => onChangePanel("research")}
            />
          </div>
        ) : (
        /* Filters and Configs Area */
        <div className="flex-1 overflow-y-auto p-4 md:p-5 space-y-5">
          {/* Controls Title */}
          <h2 id="search-controls-heading" className="flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300 pb-2 border-b border-slate-200 dark:border-slate-800">
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
            <span>Search Parameters</span>
          </h2>

          {/* Ticker Filter */}
          <div className="space-y-2 relative" ref={tickerRef}>
            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between">
              <span>Company or ticker</span>
              <span className="text-xs font-medium text-slate-400 dark:text-slate-500">
                Optional
              </span>
            </label>

            <button
              type="button"
              id="ticker-select-btn"
              aria-haspopup="listbox"
              aria-expanded={tickerDropdownOpen}
              disabled={tickers.length === 0}
              onClick={() => {
                setTickerDropdownOpen(!tickerDropdownOpen);
                setSectionDropdownOpen(false);
              }}
              className={`w-full min-h-10 flex items-center justify-between bg-white dark:bg-[#26324A]/30 border border-slate-300 dark:border-slate-800 rounded-lg text-xs md:text-sm text-[#26324A] dark:text-[#FCFBF8] py-2 px-3 outline-none transition-all font-semibold shadow-3xs group ${
                tickers.length === 0
                  ? "opacity-65 cursor-not-allowed bg-slate-50 dark:bg-slate-900/10"
                  : "hover:border-slate-400 dark:hover:border-slate-600 cursor-pointer"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Building2 className="w-4 h-4 text-slate-400 dark:text-slate-500 transition-colors flex-shrink-0" />
                <span className="truncate">
                  {tickers.length === 0
                    ? "Connect API to load companies"
                    : selectedTicker
                      ? formatCompanyLabel(selectedTicker)
                      : "All companies"}
                </span>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-slate-400 dark:text-slate-500 transition-all duration-250 flex-shrink-0 ${tickerDropdownOpen ? "rotate-180" : ""}`}
              />
            </button>

            {tickerDropdownOpen && (
                <div className="ui-popover-enter absolute z-55 left-0 right-0 mt-1 bg-white/95 dark:bg-[#0D111C]/95 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl flex flex-col overflow-hidden max-h-64 backdrop-blur-md">
                  <div className="p-2 border-b border-slate-100 dark:border-slate-800/40 bg-slate-50/50 dark:bg-slate-900/30 sticky top-0 z-10 flex items-center gap-2">
                    <Search className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
                    <input
                      type="text"
                      aria-label="Search company or ticker"
                      placeholder="Search company or ticker..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-full text-xs font-mono bg-white dark:bg-[#26324A]/30 border border-slate-200 dark:border-slate-800 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-brand-indigo focus:border-brand-indigo transition-all text-[#26324A] dark:text-[#FCFBF8]"
                      autoFocus
                    />
                  </div>

                  <div className="overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800/40 flex-1">
                    {(!searchQuery ||
                      "(all companies)".includes(
                        searchQuery.toLowerCase(),
                      )) && (
                      <button
                        type="button"
                        onClick={() => {
                          onSelectTicker(null);
                          setTickerDropdownOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${!selectedTicker ? "text-brand-indigo font-bold bg-brand-indigo/[0.03]" : "text-slate-600 dark:text-slate-300 font-medium"}`}
                      >
                        <span>(All companies)</span>
                        {!selectedTicker && (
                          <Check className="w-3.5 h-3.5 text-brand-indigo flex-shrink-0" />
                        )}
                      </button>
                    )}
                    {filteredTickers.map((ticker) => {
                        const isSelected = selectedTicker === ticker;
                        return (
                          <button
                            key={ticker}
                            type="button"
                            onClick={() => {
                              onSelectTicker(ticker);
                              setTickerDropdownOpen(false);
                            }}
                            className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 text-xs text-left hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${isSelected ? "text-brand-indigo font-bold bg-brand-indigo/[0.03]" : "text-slate-600 dark:text-slate-300 font-medium"}`}
                          >
                            <span className="min-w-0">
                              <span className="block truncate font-semibold">
                                {COMPANY_NAMES[ticker] || ticker}
                              </span>
                              <span className="block mt-0.5 font-mono text-[10px] text-slate-400 dark:text-slate-500">
                                {ticker}
                              </span>
                            </span>
                            {isSelected && (
                              <Check className="w-3.5 h-3.5 text-brand-indigo flex-shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    {filteredTickers.length === 0 &&
                      searchQuery && (
                        <div className="px-3 py-3 text-xs text-center text-slate-400 dark:text-slate-500 font-mono">
                          No matching companies
                        </div>
                      )}
                  </div>
                </div>
            )}
          </div>

          {/* Section Filter */}
          <div className="space-y-2 relative" ref={sectionRef}>
            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between gap-2">
              <span className="flex items-center gap-1.5">
                10-K Section
                <Tooltip content="Limit retrieval to one filing section. Leave this on All sections when you are unsure where the answer appears." align="left" placement="bottom">
                  <button type="button" aria-label="Explain 10-K section filter" className="text-slate-400 hover:text-brand-indigo focus:text-brand-indigo outline-none">
                    <HelpCircle className="w-3.5 h-3.5" />
                  </button>
                </Tooltip>
              </span>
              <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500">
                Optional scope
              </span>
            </label>

            <button
              type="button"
              id="section-select-btn"
              aria-haspopup="listbox"
              aria-expanded={sectionDropdownOpen}
              onClick={() => {
                setSectionDropdownOpen(!sectionDropdownOpen);
                setTickerDropdownOpen(false);
              }}
              className="w-full min-h-10 flex items-center justify-between bg-white dark:bg-[#26324A]/30 border border-slate-300 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-600 rounded-lg text-xs md:text-sm text-[#26324A] dark:text-[#FCFBF8] py-2 px-3 outline-none transition-all cursor-pointer font-semibold shadow-3xs group"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileSpreadsheet className="w-4 h-4 text-slate-400 dark:text-slate-500 transition-colors flex-shrink-0" />
                <span className="truncate">
                  {selectedSection
                    ? SECTION_METADATA[selectedSection]?.shortLabel || selectedSection
                    : "All sections"}
                </span>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-slate-400 dark:text-slate-500 transition-all duration-250 flex-shrink-0 ${sectionDropdownOpen ? "rotate-180" : ""}`}
              />
            </button>

            {sectionDropdownOpen && (
                <div className="ui-popover-enter absolute z-55 left-0 right-0 mt-1 bg-white/95 dark:bg-[#0D111C]/95 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl divide-y divide-slate-100 dark:divide-slate-800/40 overflow-y-auto max-h-96 backdrop-blur-md">
                  <button
                    type="button"
                    onClick={() => {
                      onSelectSection(null);
                      setSectionDropdownOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${!selectedSection ? "text-brand-indigo font-bold bg-brand-indigo/[0.03]" : "text-slate-600 dark:text-slate-300 font-medium"}`}
                  >
                    <span className="min-w-0 pr-2">
                      <span className="block">All sections</span>
                      <span className="block mt-0.5 text-[10px] font-normal text-slate-400 dark:text-slate-500 leading-snug">
                        {ALL_SECTIONS_DESCRIPTION}
                      </span>
                    </span>
                    {!selectedSection && (
                      <Check className="w-3.5 h-3.5 text-brand-indigo flex-shrink-0" />
                    )}
                  </button>
                  {availableSections.map(([value, meta]) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => {
                        onSelectSection(value);
                        setSectionDropdownOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${selectedSection === value ? "text-brand-indigo font-bold bg-brand-indigo/[0.03]" : "text-slate-600 dark:text-slate-300 font-medium"}`}
                    >
                      <span className="min-w-0 pr-2">
                        <span className="block">{meta.label}</span>
                        <span className="block mt-0.5 text-[10px] font-normal text-slate-400 dark:text-slate-500 leading-snug">
                          {meta.description}
                        </span>
                      </span>
                      {selectedSection === value && (
                        <Check className="w-3.5 h-3.5 text-brand-indigo flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
            )}
          </div>

          {/* Comparative Analysis Toggle */}
          <details className="group rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-[#26324A]/15">
            <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-3.5 py-3 text-sm font-semibold text-slate-700 dark:text-slate-200 [&::-webkit-details-marker]:hidden">
              <span className="flex items-center gap-2">
                <Settings2 className="h-4 w-4 text-brand-indigo" />
                Advanced retrieval settings
              </span>
              <span className="flex items-center gap-2 text-xs font-normal text-slate-500 dark:text-slate-400">
                Top-K {topK} · {enableComparative ? "decomposition on" : "decomposition off"}
                <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180" />
              </span>
            </summary>
            <div className="ui-expand-enter space-y-4 border-t border-slate-200 px-3.5 pb-3.5 pt-3 dark:border-slate-800">
              {/* Top_K Slider */}
              <div className="space-y-2">
            <div className="flex justify-between items-center text-sm font-semibold text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                Context Breadth (Top-K)
                <Tooltip content="Maximum number of filing excerpts retained after retrieval and re-ranking. More context is not always better." align="left">
                  <button type="button" aria-label="Explain context breadth" className="text-slate-400 hover:text-brand-indigo focus:text-brand-indigo outline-none">
                    <HelpCircle className="w-3.5 h-3.5" />
                  </button>
                </Tooltip>
              </span>
              <span className="font-mono text-slate-950 dark:text-[#FCFBF8] bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-1.5 py-0.5 rounded text-[11px] font-bold">
                {topK}
              </span>
            </div>
            <input
              id="top-k-slider"
              aria-label="Context breadth"
              aria-valuetext={`${topK} filing excerpts`}
              type="range"
              min={1}
              max={10}
              value={topK}
              onChange={(e) => onChangeTopK(parseInt(e.target.value, 10))}
              className="w-full accent-[#26324A] dark:accent-[#FCFBF8] bg-slate-250 dark:bg-slate-850 h-1.5 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-400 dark:text-slate-500 font-medium">
              <Tooltip
                content="Returns fewer, more targeted chunks — best for precise fact lookups (e.g. a specific revenue figure)."
                align="left"
              >
                <span className="cursor-help">1 (High Focus)</span>
              </Tooltip>
              <Tooltip
                content="Returns more chunks for comprehensive answers — best for open-ended or comparative questions."
                align="right"
              >
                <span className="cursor-help">10 (Broad Context)</span>
              </Tooltip>
            </div>
              </div>

          {/* Comparative Analysis Toggle */}
              <div className="space-y-2 bg-slate-50 dark:bg-slate-800/40 p-3.5 rounded-lg border border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Query Decomposition
              </span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  id="comparative-toggle"
                  aria-label="Enable query decomposition"
                  type="checkbox"
                  checked={enableComparative}
                  onChange={(e) => onToggleComparative(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-200 dark:bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 dark:after:border-slate-600 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#26324A] dark:peer-checked:bg-[#FCFBF8] dark:peer-checked:after:bg-[#26324A]" />
              </label>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              When enabled, complex comparative questions (e.g. vs, compare) are
              automatically decomposed into multiple targeted sub-queries.
            </p>
              </div>
            </div>
          </details>

          {/* Sample Chips */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 pb-1 border-b border-slate-200 dark:border-slate-800">
              <Compass className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
              <span>Reference Queries</span>
            </div>
            <SampleQuestionChips onSelect={onSelectSample} />
          </div>
        </div>
        )}

        {activePanel === "research" && (
          <SidebarFooter
            healthData={healthData}
            isClearingSession={isClearingSession}
            onNewConversation={onNewConversation}
          />
        )}
      </aside>
    </>
  );
};

export const Sidebar = React.memo(SidebarBase);
Sidebar.displayName = "Sidebar";
