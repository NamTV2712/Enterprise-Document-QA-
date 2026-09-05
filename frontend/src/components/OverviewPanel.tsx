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
  Sparkles,
  ArrowRight,
  ShieldAlert,
  PieChart,
  FileSpreadsheet,
  TrendingUp,
} from "lucide-react";
import { Tooltip } from "./Tooltip";
import { SAMPLE_QUESTIONS, SampleQuestion } from "./SampleQuestionChips";

interface OverviewPanelProps {
  hasMessages: boolean;
  companyCount: number;
  onReturnToConversation: () => void;
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  onRetryConnection: () => void;
  onSelectQuestion?: (question: SampleQuestion) => void;
}

const features = [
  {
    title: "Granular Chunk Scan",
    description:
      "Scans individual 10-K blocks in business descriptions, risk matrices, and financial statements.",
    tooltip:
      "Scans individual 10-K blocks in business descriptions, risk matrices, and financial statements.",
    Icon: Database,
    badge: "500-900 Tokens",
    colorClass: "bg-indigo-500/10 text-brand-indigo dark:bg-indigo-400/15 dark:text-indigo-300",
  },
  {
    title: "Multi-Hop Querying",
    description:
      "Decomposes comparative requests into focused retrievals and presents a grounded execution summary.",
    tooltip:
      "Decomposes comparative requests into focused retrievals and presents the completed execution summary.",
    Icon: GitFork,
    badge: "Sub-Query Planner",
    colorClass: "bg-teal-500/10 text-teal-700 dark:bg-teal-400/15 dark:text-teal-300",
  },
  {
    title: "Verifiable Sources",
    description:
      "Every answer keeps the retrieved filing excerpts visible so you can inspect the source text behind each claim.",
    tooltip:
      "Retrieved excerpts remain visible with filing, section, and ranking metadata so you can inspect the evidence behind an answer.",
    Icon: CheckCircle2,
    badge: "Canonical Citations",
    colorClass: "bg-emerald-500/10 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300",
  },
] as const;

const PROMPT_CARDS = [
  {
    topic: "Comparative Risks",
    target: "Apple & Microsoft 10-K disclosures",
    question: SAMPLE_QUESTIONS[0],
    Icon: ShieldAlert,
  },
  {
    topic: "Revenue Segments",
    target: "Alphabet (Google) business lines",
    question: SAMPLE_QUESTIONS[1],
    Icon: PieChart,
  },
  {
    topic: "MD&A Analysis",
    target: "Amazon performance & outlook",
    question: SAMPLE_QUESTIONS[2],
    Icon: FileSpreadsheet,
  },
  {
    topic: "Statement Trends",
    target: "Tesla financial reporting data",
    question: SAMPLE_QUESTIONS[3],
    Icon: TrendingUp,
  },
];

export const OverviewPanel = React.memo<OverviewPanelProps>(
  ({
    hasMessages,
    companyCount,
    onReturnToConversation,
    isBackendConnected,
    isPipelineReady,
    onRetryConnection,
    onSelectQuestion,
  }) => (
    <div className="overview-panel" id="onboarding-panel">
      {/* Header & Hero Section */}
      <div className="space-y-3.5 text-center">
        <div className="flex items-center justify-center gap-2">
          {hasMessages ? (
            <button
              type="button"
              onClick={onReturnToConversation}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider text-brand-indigo bg-brand-indigo/10 hover:bg-brand-indigo/20 dark:bg-brand-indigo/15 dark:hover:bg-brand-indigo/25 transition-all cursor-pointer shadow-4xs"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Return to conversation
            </button>
          ) : (
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-brand-indigo/30 bg-brand-indigo/5 dark:bg-brand-indigo/10 text-brand-indigo text-xs font-semibold shadow-4xs">
              <Sparkles className="w-3.5 h-3.5 animate-pulse" />
              <span>SEC EDGAR Intelligence • 50 Enterprise 10-K Filings</span>
            </div>
          )}
        </div>

        <h2 className="hero-title max-w-full text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight py-1 font-serif break-words">
          Ask questions. Verify every answer.
        </h2>
        <p className="text-sm md:text-base text-slate-600 dark:text-slate-400 max-w-xl mx-auto leading-relaxed font-sans">
          Research SEC 10-K filings across {companyCount || 50} searchable
          companies with cited evidence, deterministic number preservation, and a clear retrieval trail.
        </p>
      </div>

      {/* Backend Connection Status Notice if offline/checking */}
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

      {/* System Telemetry & Capability Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="stat-card">
          <div className="stat-card__value">{companyCount || 50}</div>
          <div className="stat-card__label">Searchable Companies</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__value">10,053</div>
          <div className="stat-card__label">Indexed Chunks</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__value">Hybrid RRF</div>
          <div className="stat-card__label">BM25 + Dense + CE</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__value">100%</div>
          <div className="stat-card__label">Grounded Evidence</div>
        </div>
      </div>

      {/* Interactive Quick-Start Prompts */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
          <span className="flex items-center gap-1.5 font-sans">
            <Sparkles className="w-3.5 h-3.5 text-brand-indigo" />
            Explore sample research queries
          </span>
          <span className="text-[11px] font-normal text-slate-400 dark:text-slate-500">
            Click to load & search
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {PROMPT_CARDS.map(({ topic, target, question, Icon }, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectQuestion?.(question)}
              className="prompt-card group"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-6 h-6 rounded-md bg-brand-indigo/10 dark:bg-brand-indigo/20 text-brand-indigo flex items-center justify-center flex-shrink-0">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate group-hover:text-brand-indigo transition-colors">
                    {topic}
                  </span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-brand-indigo group-hover:translate-x-0.5 transition-all flex-shrink-0" />
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1 leading-relaxed">
                {target}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Feature Architecture Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5" id="features-cards">
        {features.map(({ title, description, tooltip, Icon, badge, colorClass }) => (
          <article className="feature-card" key={title}>
            <div className="flex items-center justify-between mb-2">
              <Tooltip content={tooltip}>
                <div className={`feature-card__icon ${colorClass}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </Tooltip>
              <span className="text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded border border-slate-200/80 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                {badge}
              </span>
            </div>
            <h3 className="feature-card__title">{title}</h3>
            <p className="feature-card__description">{description}</p>
          </article>
        ))}
      </div>

      {/* Workspace Guide Collapsible */}
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
