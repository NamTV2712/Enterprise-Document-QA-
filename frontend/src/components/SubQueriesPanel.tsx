/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronDown,
  ChevronUp,
  GitFork,
  Check,
  Hash,
  Cpu,
  RefreshCw,
} from "lucide-react";
import { SubQuery } from "../types";

interface SubQueriesPanelProps {
  subQueries: SubQuery[];
  isLatest?: boolean;
  onTraceComplete?: () => void;
}

const sectionMap: Record<string, string> = {
  business: "Item 1 · Business",
  risk_factors: "Item 1A · Risk Factors",
  "risk factors": "Item 1A · Risk Factors",
  unresolved_comments: "Item 1B · Unresolved Staff Comments",
  properties: "Item 2 · Properties",
  legal_proceedings: "Item 3 · Legal Proceedings",
  mine_safety: "Item 4 · Mine Safety Disclosures",
  market_matters: "Item 5 · Market, Shareholder Matters",
  selected_financial_data: "Item 6 · Selected Financial Data",
  mdna: "Item 7 · Management's Discussion & Analysis (MD&A)",
  mda: "Item 7 · Management's Discussion & Analysis (MD&A)",
  market_risk: "Item 7A · Market Risk Disclosures",
  financial_statements: "Item 8 · Financial Statements",
  accountant_disagreements: "Item 9 · Accountant Disagreements",
  controls_procedures: "Item 9A · Controls and Procedures",
  other_information: "Item 9B · Other Information",
  directors_officers: "Item 10 · Directors & Officers",
  executive_compensation: "Item 11 · Executive Compensation",
  security_ownership: "Item 12 · Security Ownership",
  related_transactions: "Item 13 · Related Transactions",
  accountant_fees: "Item 14 · Accountant Fees & Services",
  exhibits_schedules: "Item 15 · Exhibits & Schedules",
};

export const SubQueriesPanel: React.FC<SubQueriesPanelProps> = ({
  subQueries = [],
  isLatest = false,
  onTraceComplete,
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [visibleCount, setVisibleCount] = useState<number>(0);
  const [hasAnimated, setHasAnimated] = useState<boolean>(false);

  // Check if user prefers reduced motion
  const prefersReduced =
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;

  useEffect(() => {
    // If subQueries is empty (initial trace container immediately after submit)
    if (!subQueries || subQueries.length === 0) {
      setVisibleCount(0);
      return;
    }

    // If it's not the latest message or user prefers reduced motion or has already animated, show all immediately
    if (!isLatest || prefersReduced || hasAnimated) {
      setVisibleCount(subQueries.length);
      if (onTraceComplete) onTraceComplete();
      return;
    }

    // Reset and begin sequential stagger
    setVisibleCount(0);
    let count = 0;

    const interval = setInterval(() => {
      count += 1;
      if (count <= subQueries.length) {
        setVisibleCount(count);
      } else {
        clearInterval(interval);
        setHasAnimated(true);
        // Call complete after a tiny delay to let the last item fade-in/slide-up
        const timeout = setTimeout(() => {
          if (onTraceComplete) onTraceComplete();
        }, 150);
        return () => clearTimeout(timeout);
      }
    }, 200); // 200ms stagger interval

    return () => clearInterval(interval);
  }, [subQueries, isLatest, prefersReduced, hasAnimated]);

  const isFullyDone =
    subQueries.length > 0 && visibleCount >= subQueries.length;

  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-[#F7F7F5] dark:bg-[#12161C] overflow-hidden my-4 shadow-3xs transition-all font-sans">
      <button
        type="button"
        id="subqueries-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3.5 text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-100/50 dark:hover:bg-slate-850/50 transition-colors cursor-pointer uppercase tracking-wider"
      >
        <div className="flex items-center gap-2">
          <GitFork className="w-4 h-4 text-brand-indigo rotate-180" />
          <span>
            Multi-hop Query Decomposition Trace{" "}
            {subQueries.length > 0 ? `(${subQueries.length})` : ""}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!isFullyDone && (
            <span className="text-[10px] font-mono lowercase text-brand-indigo animate-pulse px-1.5 py-0.5 bg-brand-indigo/5 border border-brand-indigo/10 rounded-sm">
              tracing...
            </span>
          )}
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="overflow-hidden border-t border-slate-200 dark:border-slate-800 bg-[#F1F1EF] dark:bg-[#0E1116]"
          >
            <div className="p-3.5 space-y-3 font-mono text-[11px] md:text-xs">
              <div className="text-slate-400 dark:text-slate-500 uppercase font-bold border-b border-slate-250 dark:border-slate-800 pb-1 flex items-center justify-between">
                <span>
                  [EXECUTION LOG] STAGE:{" "}
                  {subQueries.length > 0
                    ? "VECTOR RETRIEVAL"
                    : "DECOMPOSING QUERY"}
                </span>
                <Cpu className="w-3.5 h-3.5" />
              </div>

              <div className="space-y-3">
                {subQueries.length === 0 ? (
                  <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800/60 bg-white/50 dark:bg-[#12161C]/30 text-slate-450 dark:text-slate-550 flex items-center gap-2.5 font-mono animate-pulse">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-indigo flex-shrink-0" />
                    <span>Planning multi-hop query decomposition trace...</span>
                  </div>
                ) : (
                  subQueries.slice(0, visibleCount).map((sub, index) => {
                    const isLastRow = index === visibleCount - 1;

                    const rawSection = sub.section || "";
                    const cleanSecKey = rawSection
                      .toLowerCase()
                      .replace(/_/g, " ")
                      .trim();
                    const displaySection =
                      sectionMap[cleanSecKey] ||
                      (rawSection
                        ? rawSection.toUpperCase().replace(/_/g, " ")
                        : "General Document");

                    return (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.15, ease: "easeOut" }}
                        className={`p-3 rounded-lg border transition-all ${
                          isLastRow && !isFullyDone
                            ? "border-brand-indigo/40 bg-brand-indigo/5 text-slate-900 dark:text-white shadow-3xs"
                            : "border-slate-200 dark:border-slate-800 bg-white dark:bg-[#12161C]/60 text-slate-700 dark:text-slate-300"
                        }`}
                        id={`subquery-item-${index}`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5 font-sans">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`text-[10px] font-bold uppercase tracking-wider ${
                                isLastRow && !isFullyDone
                                  ? "text-brand-indigo"
                                  : "text-slate-500"
                              }`}
                            >
                              Sub-query {index + 1}
                            </span>

                            {sub.ticker && (
                              <span className="font-mono text-[10px] font-bold bg-slate-200/50 dark:bg-slate-800/80 px-1.5 py-0.5 rounded text-slate-700 dark:text-slate-300">
                                {sub.ticker}
                              </span>
                            )}

                            {sub.section && (
                              <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
                                {displaySection}
                              </span>
                            )}
                          </div>

                          {/* Status label */}
                          <div className="flex items-center gap-1 font-mono text-[10px]">
                            {isLastRow && !isFullyDone ? (
                              <span className="text-brand-indigo flex items-center gap-1 animate-pulse font-bold">
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                <span>scanning vectors...</span>
                              </span>
                            ) : (
                              <span className="text-verified-green dark:text-[#38a385] flex items-center gap-1 font-bold">
                                <Check className="w-3.5 h-3.5" />
                                <span>matched</span>
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Monospace Query statement */}
                        <p className="text-xs italic leading-relaxed text-slate-600 dark:text-slate-400 font-mono pl-2 border-l border-slate-200 dark:border-slate-800">
                          "{sub.query}"
                        </p>

                        {(index < visibleCount - 1 || isFullyDone) && (
                          <div className="mt-2 pt-1.5 border-t border-slate-100 dark:border-slate-800/50 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                            <span>
                              AGENT SCHEDULER RESPONSE: RETRIEVAL COMPLETE
                            </span>
                            <span className="text-verified-green dark:text-[#38a385] font-bold flex items-center gap-0.5">
                              <Hash className="w-3 h-3" />
                              {sub.num_chunks} chunks indexed
                            </span>
                          </div>
                        )}
                      </motion.div>
                    );
                  })
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
