/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, ChevronUp, FileText, ArrowUpRight } from "lucide-react";
import { Source } from "../types";

interface SourcesPanelProps {
  sources: Source[];
}

export function getSectionDisplay(
  citation: string,
  sectionField?: string,
): { section: string; ticker: string; year: string } {
  const citationLower = citation.toLowerCase();

  // Extract ticker (first alphanumeric word before underscore)
  const firstPart = citation.split("_")[0] || "";
  const ticker = firstPart.toUpperCase();

  // Extract year (4 digit number)
  const yearMatch =
    citation.match(/_(20\d{2})_/) ||
    citation.match(/_(19\d{2})_/) ||
    citation.match(/\b(20\d{2})\b/) ||
    citation.match(/\b(19\d{2})\b/);
  const year = yearMatch ? yearMatch[1] : "";

  // Extract Section Item
  let matchedItem = sectionField || "";
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

  const cleanItem = matchedItem.toLowerCase().replace(/_/g, " ").trim();

  const secMap: Record<string, string> = {
    "item 1": "Item 1 · Business",
    "item 1a": "Item 1A · Risk Factors",
    "item 1b": "Item 1B · Unresolved Staff Comments",
    "item 2": "Item 2 · Properties",
    "item 3": "Item 3 · Legal Proceedings",
    "item 4": "Item 4 · Mine Safety Disclosures",
    "item 5": "Item 5 · Market, Shareholder Matters",
    "item 6": "Item 6 · Selected Financial Data",
    "item 7": "Item 7 · Management's Discussion and Analysis (MD&A)",
    "item 7a": "Item 7A · Quantitative and Qualitative Market Risk",
    "item 8": "Item 8 · Financial Statements and Supplementary Data",
    "item 9": "Item 9 · Accountant Disagreements",
    "item 9a": "Item 9A · Controls and Procedures",
    "item 9b": "Item 9B · Other Information",
    "item 10": "Item 10 · Directors & Officers",
    "item 11": "Item 11 · Executive Compensation",
    "item 12": "Item 12 · Security Ownership",
    "item 13": "Item 13 · Related Transactions",
    "item 14": "Item 14 · Accountant Fees & Services",
    "item 15": "Item 15 · Exhibits & Schedules",
  };

  const sectionName =
    secMap[cleanItem] ||
    (cleanItem ? cleanItem.toUpperCase() : "General Document");
  return { section: sectionName, ticker, year };
}

export const SourcesPanel: React.FC<SourcesPanelProps> = ({ sources }) => {
  const [isOpen, setIsOpen] = useState(true);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="border border-slate-200/80 dark:border-slate-800 rounded-xl bg-slate-50 dark:bg-slate-900/40 overflow-hidden my-4 shadow-3xs hover:shadow-2xs transition-all">
      <button
        type="button"
        id="sources-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3.5 text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-100/50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer uppercase tracking-wider"
      >
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-slate-400 dark:text-slate-500" />
          <span className="font-sans">
            Retrieved Filing Evidence ({sources.length})
          </span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="overflow-hidden border-t border-slate-200/60 dark:border-slate-800/80"
          >
            <div className="p-3.5 divide-y divide-slate-200/50 dark:divide-slate-800/40 max-h-96 overflow-y-auto bg-slate-50/30 dark:bg-slate-950/20">
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
                            {ticker} {year ? `'${year.slice(-2)}` : ""} ·{" "}
                            {section}
                          </span>
                        </span>
                      </div>

                      {/* Verified Green for Confidence Relevance Scores */}
                      <div className="flex items-center gap-1.5 font-mono">
                        <span className="text-[9px] text-slate-400 dark:text-slate-500 uppercase tracking-wider font-bold">
                          Relevance
                        </span>
                        <span className="text-xs font-bold text-verified-green dark:text-[#38a385] bg-verified-green/5 dark:bg-[#1f5d4c]/10 border border-verified-green/20 dark:border-[#1f5d4c]/30 px-1.5 py-0.5 rounded shadow-3xs">
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
