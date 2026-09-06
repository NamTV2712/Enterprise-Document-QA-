/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";

interface HelpDialogProps {
  open: boolean;
  onClose: () => void;
}

const SECTIONS: { title: string; items: string[] }[] = [
  {
    title: "Asking questions",
    items: [
      "Name the company, the metric, and the year when you can — for example: \"What was Apple's total net sales in fiscal year 2024?\"",
      "Questions must be between 5 and 500 characters. Press Enter to send; Shift+Enter adds a new line.",
      "If the filings do not contain the answer, the assistant says so instead of guessing.",
    ],
  },
  {
    title: "Search filters",
    items: [
      "Company limits retrieval to one issuer's filings; leave it on All companies for comparisons.",
      "10-K section limits retrieval to one filing section, such as Risk Factors or MD&A.",
      "Context breadth (Top-K) controls how many filing excerpts are kept after re-ranking.",
      "Query decomposition breaks comparative questions into one focused sub-query per company.",
    ],
  },
  {
    title: "Comparison limits",
    items: [
      "Comparative answers quote each company's own disclosed figures side by side.",
      "The assistant does not calculate rankings, ratios, or percentages that the filings do not state.",
      "Different companies may disclose different measures, so some questions have no like-for-like answer.",
    ],
  },
  {
    title: "Citations and evidence",
    items: [
      "Every factual claim cites a filing excerpt as [Source N]. Select a citation to jump to that excerpt.",
      "Rank score orders excerpts within one answer; it is not a probability or confidence percentage.",
      "Filing dates describe when the document was filed; they are not the fiscal period of a number.",
    ],
  },
  {
    title: "Local storage",
    items: [
      "Conversations are saved in this browser only — up to 100 conversations and 25 MB in total.",
      "The backend keeps only a few recent turns per session and expires them after 30 minutes.",
      "When backend context expires, saved conversations become read-only copies you can still search and export.",
    ],
  },
];

export const HelpDialog: React.FC<HelpDialogProps> = ({ open, onClose }) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
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
    document.addEventListener("keydown", handleKeyDown, true);
    return () => {
      document.removeEventListener("keydown", handleKeyDown, true);
      previouslyFocused?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overlay-backdrop p-4"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-dialog-title"
        className="w-full max-w-lg rounded-2xl surface-raised border-[var(--border-subtle)] p-5 shadow-2xl max-h-[85dvh] overflow-y-auto"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="help-dialog-title" className="text-base font-semibold text-[var(--text-primary)]">
            How to use this research workspace
          </h2>
          <button
            type="button"
            ref={closeRef}
            onClick={onClose}
            aria-label="Close help"
            className="min-h-9 min-w-9 rounded-lg p-2 text-[var(--text-subtle)] hover:surface-muted-hover"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-3 space-y-4">
          {SECTIONS.map((section) => (
            <section key={section.title}>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                {section.title}
              </h3>
              <ul className="mt-1.5 space-y-1.5">
                {section.items.map((item) => (
                  <li
                    key={item}
                    className="text-sm leading-relaxed text-[var(--text-muted)] list-disc pl-4 marker:text-[var(--text-subtle)]"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
};
