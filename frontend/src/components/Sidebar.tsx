/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  SlidersHorizontal,
  RefreshCw,
  TrendingUp,
  FileSpreadsheet,
  X,
  Compass,
  Cpu,
  ChevronDown,
  Check,
  Building2,
  Search,
} from "lucide-react";
import { SampleQuestionChips, SampleQuestion } from "./SampleQuestionChips";
import { HealthResponse } from "../types";
import { Tooltip } from "./Tooltip";

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
  isBackendConnected: boolean | null;
  isOpen: boolean;
  onClose: () => void;
  isClearingSession: boolean;
}

const SECTION_MAP: Record<string, string> = {
  business: "Business",
  risk_factors: "Risk Factors",
  mdna: "MD&A",
  financial_statements: "Financial Statements",
  financial_table: "Financial Table",
};

const SECTIONS_LIST = [
  { value: "business", label: "Business" },
  { value: "risk_factors", label: "Risk Factors" },
  { value: "mdna", label: "MD&A" },
  { value: "financial_statements", label: "Financial Statements" },
  { value: "financial_table", label: "Financial Table" },
];

export const Sidebar: React.FC<SidebarProps> = ({
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
  isBackendConnected,
  isOpen,
  onClose,
  isClearingSession,
}) => {
  const [tickerDropdownOpen, setTickerDropdownOpen] = useState(false);
  const [sectionDropdownOpen, setSectionDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (!tickerDropdownOpen) {
      setSearchQuery("");
    }
  }, [tickerDropdownOpen]);

  const tickerRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLDivElement>(null);

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

  return (
    <>
      {/* Mobile Sidebar Overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-[#1B2430]/20 dark:bg-[#12161C]/50 backdrop-blur-xs z-40 lg:hidden transition-opacity"
        />
      )}

      <aside
        id="control-sidebar"
        className={`fixed inset-y-0 left-0 w-80 bg-[#F7F7F5] dark:bg-[#12161C] text-[#1B2430] dark:text-[#F7F7F5] flex flex-col border-r border-slate-200 dark:border-slate-800 z-45 transition-all duration-300 lg:static lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-[#1B2430]/10">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-[#1B2430] dark:bg-[#F7F7F5]/10 flex items-center justify-center border border-slate-300 dark:border-slate-700">
              <TrendingUp className="w-4 h-4 text-[#F7F7F5] dark:text-slate-300" />
            </div>
            <div>
              <h1 className="text-xs font-black tracking-tight text-[#1B2430] dark:text-[#F7F7F5] uppercase font-serif">
                SEC RAG Engine
              </h1>
              <span className="text-[9px] text-slate-500 dark:text-slate-450 font-mono font-bold uppercase tracking-wider">
                SEC 10-K Research
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close search controls"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filters and Configs Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Controls Title */}
          <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider pb-1 border-b border-slate-200 dark:border-slate-800">
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
            <span>Search Parameters</span>
          </div>

          {/* Ticker Filter */}
          <div className="space-y-2 relative" ref={tickerRef}>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
              <span>Limit to Ticker</span>
              <span className="text-[10px] font-mono font-bold text-slate-400 dark:text-slate-500">
                FastAPI Lookup
              </span>
            </label>

            <button
              type="button"
              id="ticker-select-btn"
              disabled={tickers.length === 0}
              onClick={() => {
                setTickerDropdownOpen(!tickerDropdownOpen);
                setSectionDropdownOpen(false);
              }}
              className={`w-full flex items-center justify-between bg-white dark:bg-[#1B2430]/30 border border-slate-300 dark:border-slate-800 rounded-lg text-xs md:text-sm text-[#1B2430] dark:text-[#F7F7F5] py-2 px-3 outline-none transition-all font-semibold shadow-3xs group ${
                tickers.length === 0
                  ? "opacity-65 cursor-not-allowed bg-slate-50 dark:bg-slate-900/10"
                  : "hover:border-slate-400 dark:hover:border-slate-600 cursor-pointer"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Building2 className="w-4 h-4 text-slate-400 dark:text-slate-500 transition-colors flex-shrink-0" />
                <span className="truncate font-mono">
                  {tickers.length === 0
                    ? "Connect API to load companies"
                    : selectedTicker || "(All companies)"}
                </span>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-slate-400 dark:text-slate-500 transition-all duration-250 flex-shrink-0 ${tickerDropdownOpen ? "rotate-180" : ""}`}
              />
            </button>

            <AnimatePresence>
              {tickerDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 4, scale: 0.98 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute z-55 left-0 right-0 mt-1 bg-white dark:bg-[#12161C] border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg flex flex-col overflow-hidden max-h-64"
                >
                  <div className="p-2 border-b border-slate-100 dark:border-slate-800/40 bg-slate-50/50 dark:bg-slate-900/30 sticky top-0 z-10 flex items-center gap-2">
                    <Search className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
                    <input
                      type="text"
                      placeholder="Search ticker..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-full text-xs font-mono bg-white dark:bg-[#1B2430]/30 border border-slate-200 dark:border-slate-800 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-brand-indigo focus:border-brand-indigo transition-all text-[#1B2430] dark:text-[#F7F7F5]"
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
                    {[...tickers]
                      .sort((a, b) => a.localeCompare(b))
                      .filter((ticker) =>
                        ticker
                          .toLowerCase()
                          .includes(searchQuery.toLowerCase()),
                      )
                      .map((ticker) => {
                        const isSelected = selectedTicker === ticker;
                        return (
                          <button
                            key={ticker}
                            type="button"
                            onClick={() => {
                              onSelectTicker(ticker);
                              setTickerDropdownOpen(false);
                            }}
                            className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors font-mono cursor-pointer ${isSelected ? "text-brand-indigo font-bold bg-brand-indigo/[0.03]" : "text-slate-600 dark:text-slate-300 font-medium"}`}
                          >
                            <span>{ticker}</span>
                            {isSelected && (
                              <Check className="w-3.5 h-3.5 text-brand-indigo flex-shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    {[...tickers].filter((ticker) =>
                      ticker.toLowerCase().includes(searchQuery.toLowerCase()),
                    ).length === 0 &&
                      searchQuery && (
                        <div className="px-3 py-3 text-xs text-center text-slate-400 dark:text-slate-500 font-mono">
                          No matching companies
                        </div>
                      )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Section Filter */}
          <div className="space-y-2 relative" ref={sectionRef}>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
              <span>10-K Section</span>
              <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500">
                Granular Retrieval
              </span>
            </label>

            <button
              type="button"
              id="section-select-btn"
              onClick={() => {
                setSectionDropdownOpen(!sectionDropdownOpen);
                setTickerDropdownOpen(false);
              }}
              className="w-full flex items-center justify-between bg-white dark:bg-[#1B2430]/30 border border-slate-300 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-600 rounded-lg text-xs md:text-sm text-[#1B2430] dark:text-[#F7F7F5] py-2 px-3 outline-none transition-all cursor-pointer font-semibold shadow-3xs group"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileSpreadsheet className="w-4 h-4 text-slate-400 dark:text-slate-500 transition-colors flex-shrink-0" />
                <span className="truncate">
                  {selectedSection
                    ? SECTION_MAP[selectedSection] || selectedSection
                    : "(All sections)"}
                </span>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-slate-400 dark:text-slate-500 transition-all duration-250 flex-shrink-0 ${sectionDropdownOpen ? "rotate-180" : ""}`}
              />
            </button>

            <AnimatePresence>
              {sectionDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 4, scale: 0.98 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute z-55 left-0 right-0 mt-1 bg-white dark:bg-[#12161C] border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg divide-y divide-slate-100 dark:divide-slate-800/40 overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => {
                      onSelectSection(null);
                      setSectionDropdownOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${!selectedSection ? "text-brand-indigo font-bold bg-brand-indigo/[0.03]" : "text-slate-600 dark:text-slate-300 font-medium"}`}
                  >
                    <span>(All sections)</span>
                    {!selectedSection && (
                      <Check className="w-3.5 h-3.5 text-brand-indigo flex-shrink-0" />
                    )}
                  </button>
                  {SECTIONS_LIST.map((sec) => {
                    const isSelected = selectedSection === sec.value;
                    return (
                      <button
                        key={sec.value}
                        type="button"
                        onClick={() => {
                          onSelectSection(sec.value);
                          setSectionDropdownOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${isSelected ? "text-brand-indigo font-bold bg-brand-indigo/[0.03]" : "text-slate-600 dark:text-slate-300 font-medium"}`}
                      >
                        <span>{sec.label}</span>
                        {isSelected && (
                          <Check className="w-3.5 h-3.5 text-brand-indigo flex-shrink-0" />
                        )}
                      </button>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Top_K Slider */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-bold text-slate-700 dark:text-slate-300">
              <span>Context Breadth (Top-K Chunks)</span>
              <span className="font-mono text-slate-950 dark:text-[#F7F7F5] bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-1.5 py-0.5 rounded text-[11px] font-bold">
                {topK}
              </span>
            </div>
            <input
              id="top-k-slider"
              type="range"
              min={1}
              max={10}
              value={topK}
              onChange={(e) => onChangeTopK(parseInt(e.target.value, 10))}
              className="w-full accent-[#1B2430] dark:accent-[#F7F7F5] bg-slate-250 dark:bg-slate-850 h-1.5 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 dark:text-slate-500 font-mono font-semibold">
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
          <div className="space-y-2.5 bg-white dark:bg-[#1B2430]/20 p-3.5 rounded-lg border border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                Query Decomposition
              </span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  id="comparative-toggle"
                  type="checkbox"
                  checked={enableComparative}
                  onChange={(e) => onToggleComparative(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-200 dark:bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 dark:after:border-slate-600 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#1B2430] dark:peer-checked:bg-[#F7F7F5] dark:peer-checked:after:bg-[#1B2430]" />
              </label>
            </div>
            <p className="text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed font-semibold">
              When enabled, complex comparative questions (e.g. vs, compare) are
              automatically decomposed into multiple targeted sub-queries.
            </p>
          </div>

          {/* Sample Chips */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider pb-1 border-b border-slate-200 dark:border-slate-800">
              <Compass className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
              <span>Reference Queries</span>
            </div>
            <SampleQuestionChips onSelect={onSelectSample} />
          </div>
        </div>

        {/* Footer with Pipeline Status / Session Actions */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#12161C] space-y-3 relative overflow-hidden">
          {/* Health Metrics Dashboard */}
          <div className="space-y-2.5 text-xs relative z-10">
            <div className="flex items-center justify-between">
              <span className="text-slate-450 dark:text-slate-500 font-bold tracking-wider text-[10px] uppercase">
                SYSTEM STATS
              </span>

              {/* Verified Green dot for pipeline_ready */}
              <span
                className={`inline-flex items-center gap-1.5 text-[9px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider ${
                  isBackendConnected === null
                    ? "bg-slate-100 dark:bg-slate-900/30 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-800"
                    : isBackendConnected === false
                      ? "bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-100 dark:border-rose-950/30"
                      : healthData?.pipeline_ready
                        ? "bg-verified-green/5 dark:bg-[#1f5d4c]/10 text-verified-green dark:text-[#38a385] border border-verified-green/20 dark:border-[#1f5d4c]/30"
                        : "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-100 dark:border-amber-950/30"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isBackendConnected === null
                      ? "bg-slate-400"
                      : isBackendConnected === false
                        ? "bg-rose-400"
                        : healthData?.pipeline_ready
                          ? "bg-verified-green dark:bg-[#38a385]"
                          : "bg-amber-400"
                  }`}
                />
                {isBackendConnected === null
                  ? "connecting"
                  : isBackendConnected === false
                    ? "offline"
                    : healthData?.pipeline_ready
                      ? "pipeline_ready"
                      : "pipeline_pending"}
              </span>
            </div>

            {healthData?.memory && (
              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono border-t border-slate-200 dark:border-slate-800/80 pt-2.5">
                <div className="bg-[#F7F7F5] dark:bg-[#1B2430]/30 p-2 rounded border border-slate-200 dark:border-slate-800">
                  <div className="text-slate-500 dark:text-slate-450 font-sans font-bold">
                    Active Sessions
                  </div>
                  <div className="text-[#1B2430] dark:text-[#F7F7F5] font-bold mt-1 text-xs font-mono">
                    {healthData.memory.active_sessions}
                  </div>
                </div>
                <div className="bg-[#F7F7F5] dark:bg-[#1B2430]/30 p-2 rounded border border-slate-200 dark:border-slate-800">
                  <div className="text-slate-500 dark:text-slate-450 font-sans font-bold">
                    Total Turns
                  </div>
                  <div className="text-[#1B2430] dark:text-[#F7F7F5] font-bold mt-1 text-xs font-mono">
                    {healthData.memory.total_turns}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* New Conversation Button */}
          <button
            type="button"
            id="new-convo-btn"
            disabled={isClearingSession}
            onClick={onNewConversation}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-[#1B2430] dark:bg-[#F7F7F5] text-[#F7F7F5] dark:text-[#1B2430] hover:opacity-90 disabled:opacity-50 rounded text-xs font-bold transition-all cursor-pointer font-sans uppercase tracking-wider"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isClearingSession ? "animate-spin" : "animate-none"}`}
            />
            <span>
              {isClearingSession ? "Resetting..." : "New conversation"}
            </span>
          </button>
        </div>
      </aside>
    </>
  );
};
