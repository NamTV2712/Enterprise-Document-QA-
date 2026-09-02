/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useId, useState, useEffect } from "react";
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
import { formatCompanyLabel } from "../lib/displayMetadata";

interface SubQueriesPanelProps {
  subQueries: SubQuery[];
  isLatest?: boolean;
}

const sectionMap: Record<string, string> = {
  business: "Business Overview",
  risk_factors: "Risk Factors",
  "risk factors": "Risk Factors",
  unresolved_comments: "Unresolved Staff Comments",
  properties: "Properties",
  legal_proceedings: "Legal Proceedings",
  mine_safety: "Mine Safety Disclosures",
  market_matters: "Market and Shareholder Matters",
  selected_financial_data: "Selected Financial Data",
  mdna: "Management Discussion & Analysis (MD&A)",
  mda: "Management Discussion & Analysis (MD&A)",
  market_risk: "Market Risk Disclosures",
  financial_statements: "Financial Statements & Notes",
  accountant_disagreements: "Accountant Disagreements",
  controls_procedures: "Controls and Procedures",
  other_information: "Other Information",
  directors_officers: "Directors & Officers",
  executive_compensation: "Executive Compensation",
  security_ownership: "Security Ownership",
  related_transactions: "Related Transactions",
  accountant_fees: "Accountant Fees & Services",
  exhibits_schedules: "Exhibits & Schedules",
};

export const SubQueriesPanel: React.FC<SubQueriesPanelProps> = ({
  subQueries = [],
  isLatest = false,
}) => {
  const [isOpen, setIsOpen] = useState(isLatest);
  const [visibleCount, setVisibleCount] = useState<number>(0);
  const [hasAnimated, setHasAnimated] = useState<boolean>(false);
  const panelId = `subqueries-panel-${useId().replace(/:/g, "")}`;

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
      }
    }, 120); // Keep the trace readable without delaying the answer.

    return () => {
      clearInterval(interval);
    };
  }, [subQueries, isLatest, prefersReduced, hasAnimated]);

  const isFullyDone =
    subQueries.length > 0 && visibleCount >= subQueries.length;

  useEffect(() => {
    // Keep the active execution visible while it is running, then let the
    // completed trace stay compact so the answer remains the focus.
    if (!isLatest && isFullyDone) setIsOpen(false);
  }, [isFullyDone, isLatest]);

  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-[#FCFBF8] dark:bg-[#171D2B] overflow-hidden my-4 shadow-3xs transition-all font-sans">
      <button
        type="button"
        id={`${panelId}-toggle`}
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={() => setIsOpen(!isOpen)}
        className="w-full min-h-11 flex items-center justify-between gap-3 p-3.5 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100/50 dark:hover:bg-slate-850/50 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <GitFork className="w-4 h-4 text-brand-indigo rotate-180" />
          <span className="text-left">
            Query breakdown{" "}
            {subQueries.length > 0 ? `(${subQueries.length})` : ""}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!isFullyDone && (
              <span className="text-xs font-medium text-brand-indigo animate-pulse px-1.5 py-0.5 bg-brand-indigo/5 border border-brand-indigo/10 rounded-sm">
              Preparing
            </span>
          )}
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {isOpen && (
          <div id={panelId} className="ui-expand-enter overflow-hidden border-t border-slate-200 dark:border-slate-800 bg-[#F3F5FA] dark:bg-[#101625]">
            <div className="p-3.5 space-y-3 text-sm">
              <div className="text-slate-500 dark:text-slate-400 font-medium border-b border-slate-250 dark:border-slate-800 pb-2 flex items-center justify-between" role="status" aria-live="polite">
                <span>
                  {subQueries.length > 0
                    ? "Focused retrievals are ready"
                    : "Preparing focused retrievals"}
                </span>
                <Cpu className="w-3.5 h-3.5" />
              </div>

              <div className="space-y-3">
                {subQueries.length === 0 ? (
                  <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800/60 bg-white/50 dark:bg-[#171D2B]/30 text-slate-500 dark:text-slate-400 flex items-center gap-2.5 animate-pulse">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-indigo flex-shrink-0" />
                    <span>Preparing the focused retrieval summary…</span>
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
                      <div
                        key={index}
                        className={`ui-stagger-enter p-3 rounded-lg border transition-all ${
                          isLastRow && !isFullyDone
                            ? "border-brand-indigo/40 bg-brand-indigo/5 text-slate-900 dark:text-white shadow-3xs"
                            : "border-slate-200 dark:border-slate-800 bg-white dark:bg-[#171D2B]/60 text-slate-700 dark:text-slate-300"
                        }`}
                        id={`subquery-item-${index}`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5 font-sans">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`text-xs font-semibold ${
                                isLastRow && !isFullyDone
                                  ? "text-brand-indigo"
                                  : "text-slate-500"
                              }`}
                            >
                              Sub-query {index + 1}
                            </span>

                            {sub.ticker && (
                              <span className="font-mono text-[10px] font-bold bg-slate-200/50 dark:bg-slate-800/80 px-1.5 py-0.5 rounded text-slate-700 dark:text-slate-300">
                                {formatCompanyLabel(sub.ticker)}
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
                            <span className="text-xs text-brand-indigo flex items-center gap-1 animate-pulse font-semibold">
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                <span>Preparing result…</span>
                              </span>
                            ) : (
                              <span className="text-verified-green dark:text-[#53B89A] flex items-center gap-1 font-bold">
                                <Check className="w-3.5 h-3.5" />
                                <span>Ready</span>
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Monospace Query statement */}
                        <p className="text-sm italic leading-relaxed text-slate-600 dark:text-slate-400 font-mono pl-3 border-l border-slate-200 dark:border-slate-800">
                          "{sub.query}"
                        </p>

                        {(index < visibleCount - 1 || isFullyDone) && (
                          <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800/50 flex items-center justify-between text-xs text-slate-400">
                            <span>Retrieval complete</span>
                            <span className="text-verified-green dark:text-[#53B89A] font-bold flex items-center gap-0.5">
                              <Hash className="w-3 h-3" />
                              {sub.num_chunks} chunks indexed
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
      )}
    </div>
  );
};
