/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import {
  CheckCircle2,
  ChevronDown,
  Database,
  GitFork,
  HelpCircle,
  AlertTriangle,
  Loader2,
  MessageSquare,
  RefreshCw,
} from "lucide-react";
import { Tooltip } from "./Tooltip";

interface OverviewPanelProps {
  hasMessages: boolean;
  companyCount: number;
  onReturnToConversation: () => void;
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  onRetryConnection: () => void;
}

const features = [
  {
    title: "Granular Chunk Scan",
    description:
      "Scans individual 10-K blocks in business descriptions, risk matrices, and financial statements.",
    tooltip:
      "Scans individual 10-K blocks in business descriptions, risk matrices, and financial statements.",
    Icon: Database,
  },
  {
    title: "Multi-Hop Querying",
    description:
      "Decomposes comparative requests into focused retrievals and presents a grounded execution summary.",
    tooltip:
      "Decomposes comparative requests into focused retrievals and presents the completed execution summary.",
    Icon: GitFork,
  },
  {
    title: "Verifiable Sources",
    description:
      "Every answer keeps the retrieved filing excerpts visible so you can inspect the source text behind each claim.",
    tooltip:
      "All extracted disclosures are verified with alignment margins, item tags, and exact document indexes.",
    Icon: CheckCircle2,
  },
] as const;

export const OverviewPanel = React.memo<OverviewPanelProps>(
  ({
    hasMessages,
    companyCount,
    onReturnToConversation,
    isBackendConnected,
    isPipelineReady,
    onRetryConnection,
  }) => (
    <div className="overview-panel" id="onboarding-panel">
      <div className="space-y-3 text-center">
        {hasMessages && (
          <button
            type="button"
            onClick={onReturnToConversation}
            className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-brand-indigo hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors cursor-pointer"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Return to conversation
          </button>
        )}
        <p className="mx-auto max-w-lg text-xs font-medium text-slate-500 dark:text-slate-400">
          Choose an optional company or filing section in the sidebar, then ask
          your question below. The workspace keeps the source excerpts beside
          every grounded answer.
        </p>
        <h2 className="max-w-full text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-[#26324A] dark:text-[#FCFBF8] py-1 font-serif break-words">
          Ask questions. Verify every answer.
        </h2>
        <p className="text-sm md:text-base text-slate-600 dark:text-slate-400 max-w-xl mx-auto leading-relaxed font-sans">
          Research SEC 10-K filings across {companyCount || 44} searchable
          companies with cited evidence and a clear retrieval trail.
        </p>
      </div>

      {isBackendConnected !== true || isPipelineReady !== true ? (
        <div
          className={`backend-notice ${
            isBackendConnected === false
              ? "backend-notice--offline"
              : "backend-notice--checking"
          }`}
          role={isBackendConnected === false ? "alert" : "status"}
          aria-live="polite"
        >
          <span className="backend-notice__icon" aria-hidden="true">
            {isBackendConnected === null || isPipelineReady === null ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <AlertTriangle className="w-4 h-4" />
            )}
          </span>
          <span className="min-w-0 flex-1">
            {isBackendConnected === null || isPipelineReady === null
              ? "Connecting to the research service…"
              : isBackendConnected === false
                ? "The research service is offline. Connect the FastAPI backend to start asking questions."
                : "The document index is still loading. Questions will be available shortly."}
          </span>
          {isBackendConnected === false && (
            <button
              type="button"
              onClick={onRetryConnection}
              className="backend-notice__retry"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          )}
        </div>
      ) : null}

      <div className="overview-callout">
        <span className="text-sm font-semibold text-[#26324A] dark:text-[#FCFBF8]">
          Start with a natural-language question
        </span>
        <span className="hidden sm:inline text-slate-300 dark:text-slate-600">
          ·
        </span>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Press Enter to search, Shift+Enter for a new line
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4" id="features-cards">
        {features.map(({ title, description, tooltip, Icon }) => (
          <article className="feature-card" key={title}>
            <Tooltip content={tooltip}>
              <div className="feature-card__icon">
                <Icon className="w-4 h-4" />
              </div>
            </Tooltip>
            <h3 className="feature-card__title">{title}</h3>
            <p className="feature-card__description">{description}</p>
          </article>
        ))}
      </div>

      <details className="workspace-guide group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-bold text-brand-indigo [&::-webkit-details-marker]:hidden">
          <span className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4" />
            How to read the workspace
          </span>
          <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
        </summary>
        <div className="ui-expand-enter grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 text-sm leading-relaxed text-slate-600 dark:text-slate-350">
          <p>
            <strong className="block text-slate-800 dark:text-slate-100">
              1. Choose scope
            </strong>
            Select a company and 10-K section, or leave both on All for
            discovery and comparisons.
          </p>
          <p>
            <strong className="block text-slate-800 dark:text-slate-100">
              2. Ask naturally
            </strong>
            Comparisons can be decomposed into focused sub-queries before a
            grounded summary is produced.
          </p>
          <p>
            <strong className="block text-slate-800 dark:text-slate-100">
              3. Verify evidence
            </strong>
            Open the evidence panel to read source excerpts. Rank scores order
            results; they are not confidence percentages.
          </p>
        </div>
        <p className="md:col-span-3 text-xs text-slate-500 dark:text-slate-400 border-t border-brand-indigo/10 pt-3">
          Research demo only · Answers may be incomplete and are not financial
          advice.
        </p>
      </details>
    </div>
  ),
);

OverviewPanel.displayName = "OverviewPanel";
