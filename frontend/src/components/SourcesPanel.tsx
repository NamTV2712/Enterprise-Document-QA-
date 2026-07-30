/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useId, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronDown,
  ChevronUp,
  FileText,
  ArrowUpRight,
} from "lucide-react";
import { Source } from "../types";
import { formatCompanyLabel, SECTION_METADATA } from "../lib/displayMetadata";

interface SourcesPanelProps {
  sources: Source[];
}

export function getSectionDisplay(
  citation: string,
  sectionField?: string,
): { section: string; ticker: string; year: string } {
  const citationLower = citation.toLowerCase();

  const tickerMatch = citation.match(/^([A-Z]{1,5}(?:-[A-Z])?)(?:\s|_)/i);
  const ticker = tickerMatch?.[1]?.toUpperCase() || "SEC";

  // Extract year (4 digit number)
  const yearMatch =
    citation.match(/_(20\d{2})_/) ||
    citation.match(/_(19\d{2})_/) ||
    citation.match(/\b(20\d{2})\b/) ||
    citation.match(/\b(19\d{2})\b/);
  const year = yearMatch ? yearMatch[1] : "";

  // Extract Section Item
  let matchedItem = sectionField || "";
  const explicitSection = citation.match(/Section:\s*([^,]+)/i)?.[1]?.trim();
  if (!matchedItem && explicitSection) {
    const normalizedSection = explicitSection.toLowerCase().replace(/\s+/g, "_");
    if (SECTION_METADATA[normalizedSection]) {
      matchedItem = normalizedSection;
    }
  }
  if (!matchedItem) {
    const itemMatch =
      citationLower.match(/item_(\d+[a-z]?)/) ||
      citationLower.match(/item\s+(\d+[a-z]?)/);
    if (itemMatch) {
      matchedItem = `item_${itemMatch[1]}`;
    }
  }

  if (!matchedItem) {
    const items = [
      "item_1a",
      "item_1b",
      "item_7a",
      "item_9a",
      "item_9b",
      "item_1",
      "item_2",
      "item_3",
      "item_4",
      "item_5",
      "item_6",
      "item_7",
      "item_8",
      "item_9",
      "item_10",
      "item_11",
      "item_12",
      "item_13",
      "item_14",
      "item_15",
    ];
    for (const it of items) {
      if (
        citationLower.includes(it) ||
        citationLower.includes(it.replace("_", " "))
      ) {
        matchedItem = it;
        break;
      }
    }
  }

  if (SECTION_METADATA[matchedItem]) {
    return {
      section: SECTION_METADATA[matchedItem].label,
      ticker,
      year,
    };
  }

  const cleanItem = matchedItem.toLowerCase().replace(/_/g, " ").trim();

  const secMap: Record<string, string> = {
    "item 1": "Business Overview",
    "item 1a": "Risk Factors",
    "item 1b": "Unresolved Staff Comments",
    "item 2": "Properties",
    "item 3": "Legal Proceedings",
    "item 4": "Mine Safety Disclosures",
    "item 5": "Market and Shareholder Matters",
    "item 6": "Selected Financial Data",
    "item 7": "Management Discussion & Analysis (MD&A)",
    "item 7a": "Market Risk Disclosures",
    "item 8": "Financial Statements & Supplementary Data",
    "item 9": "Accountant Disagreements",
    "item 9a": "Controls and Procedures",
    "item 9b": "Other Information",
    "item 10": "Directors & Officers",
    "item 11": "Executive Compensation",
    "item 12": "Security Ownership",
    "item 13": "Related Transactions",
    "item 14": "Accountant Fees & Services",
    "item 15": "Exhibits & Schedules",
  };

  const sectionName =
    secMap[cleanItem] ||
    (cleanItem ? cleanItem.toUpperCase() : "General Document");
  return { section: sectionName, ticker, year };
}

export const SourcesPanel: React.FC<SourcesPanelProps> = ({ sources }) => {
  const [isOpen, setIsOpen] = useState(false);
  const panelId = `sources-panel-${useId().replace(/:/g, "")}`;

  if (!sources || sources.length === 0) return null;

  const sourceTickers = Array.from(
    new Set(sources.map((source) => getSectionDisplay(source.citation).ticker)),
  );
  const companySummary = sourceTickers
    .slice(0, 2)
    .map(formatCompanyLabel)
    .join(" · ");
  const remainingCompanies = Math.max(0, sourceTickers.length - 2);

  return (
    <div className="border border-slate-200/80 dark:border-slate-800 rounded-xl bg-slate-50 dark:bg-slate-900/40 overflow-hidden my-4 shadow-3xs hover:shadow-2xs transition-all">
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={`${isOpen ? "Hide" : "Show"} ${sources.length} retrieved filing evidence excerpts`}
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between gap-3 p-3.5 text-left text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-100/50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
      >
        <div className="flex items-start gap-2 min-w-0">
          <FileText className="w-4 h-4 mt-0.5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
          <span className="min-w-0">
            <span className="block font-sans uppercase tracking-wider">
              Retrieved Filing Evidence · {sources.length} excerpts
            </span>
            <span className="block mt-1 text-[10px] font-normal text-slate-500 dark:text-slate-400 normal-case tracking-normal truncate">
              {companySummary}
              {remainingCompanies > 0 ? ` · +${remainingCompanies} more` : ""}
              {" · "}{isOpen ? "Hide source text" : "Open source text and ranking details"}
            </span>
          </span>
        </div>
        <span className="flex items-center gap-1.5 flex-shrink-0 text-[10px] uppercase tracking-wider text-brand-indigo">
          {isOpen ? "Hide" : "View"}
          {isOpen ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            id={panelId}
            className="overflow-hidden border-t border-slate-200/60 dark:border-slate-800/80"
          >
            <div className="px-3.5 py-2.5 bg-brand-indigo/[0.03] border-b border-slate-200/60 dark:border-slate-800/80 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">
              These are the filing excerpts used to ground the answer. Rank score
              orders excerpts within this result set; it is not a probability or
              confidence percentage.
            </div>
            <div className="p-3.5 divide-y divide-slate-200/50 dark:divide-slate-800/40 max-h-[min(28rem,55vh)] overflow-y-auto bg-slate-50/30 dark:bg-slate-950/20">
              {sources.map((source, index) => {
                const { section, ticker, year } = getSectionDisplay(
                  source.citation,
                );
                const displayScore =
                  typeof source.score === "number"
                    ? source.score.toFixed(4)
                    : source.score;

                return (
                  <div
                    key={index}
                    className="py-3 first:pt-0 last:pb-0"
                    id={`source-item-${index}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        {/* Exhibit Amber Citation Tag */}
                        <span className="text-[10px] md:text-xs font-bold text-brand-indigo border border-brand-indigo/30 bg-brand-indigo/5 px-2 py-0.5 rounded shadow-3xs flex items-center gap-1 font-sans">
                          <ArrowUpRight className="w-3.5 h-3.5" />
                          <span>
                            {formatCompanyLabel(ticker)} {year ? `'${year.slice(-2)}` : ""} ·{" "}
                            {section}
                          </span>
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5 font-mono">
                        <span className="text-[9px] text-slate-400 dark:text-slate-500 uppercase tracking-wider font-bold">
                          Rank score
                        </span>
                        <span className="text-xs font-bold text-brand-indigo bg-brand-indigo/5 border border-brand-indigo/20 px-1.5 py-0.5 rounded shadow-3xs">
                          {displayScore}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-slate-650 dark:text-slate-350 leading-relaxed bg-white dark:bg-slate-900/50 p-3 rounded-lg border border-slate-200/50 dark:border-slate-800/40 whitespace-pre-wrap select-all font-mono shadow-4xs">
                      {source.text_preview}
                    </p>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
