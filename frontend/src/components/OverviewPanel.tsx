/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import {
  ChevronDown,
  Database,
  HelpCircle,
  AlertTriangle,
  Loader2,
  MessageSquare,
  RefreshCw,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { Tooltip } from "./Tooltip";
import { useLocale } from "../lib/i18n";
import { RESEARCH_TEMPLATES, getResearchTemplateCopy, type ResearchTemplate } from "../lib/researchTemplates";
import type { ConversationRecord } from "../lib/conversationStore";
import { getSemanticIcon } from "../lib/semanticIcons";
import type { SemanticIconKey } from "../lib/semanticIcons";

interface OverviewPanelProps {
  hasMessages: boolean;
  companyCount: number | null;
  indexedChunkCount?: number | null;
  onReturnToConversation: () => void;
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  onRetryConnection: () => void;
  scopeLabel: string;
  recentConversations: ConversationRecord[];
  onSelectTemplate?: (template: ResearchTemplate) => void;
  onSelectConversation?: (conversation: ConversationRecord) => void;
}

const features: Array<{
  title: string;
  description: string;
  tooltip: string;
  iconKey: SemanticIconKey;
  accentFamily: "documents" | "retrieval" | "evidence";
  badge: string;
}> = [
  {
    title: "Granular Chunk Scan",
    description:
      "Scans individual 10-K blocks in business descriptions, risk matrices, and financial statements.",
    tooltip:
      "Scans individual 10-K blocks in business descriptions, risk matrices, and financial statements.",
    iconKey: "reader",
    accentFamily: "documents",
    badge: "500-900 Tokens",
  },
  {
    title: "Multi-Hop Querying",
    description:
      "Decomposes comparative requests into focused retrievals and presents a grounded execution summary.",
    tooltip:
      "Decomposes comparative requests into focused retrievals and presents the completed execution summary.",
    iconKey: "execution",
    accentFamily: "retrieval",
    badge: "Sub-Query Planner",
  },
  {
    title: "Verifiable Sources",
    description:
      "Every answer keeps the retrieved filing excerpts visible so you can inspect the source text behind each claim.",
    tooltip:
      "Retrieved excerpts remain visible with filing, section, and ranking metadata so you can inspect the evidence behind an answer.",
    iconKey: "sources",
    accentFamily: "evidence",
    badge: "Canonical Citations",
  },
] as const;

export const OverviewPanel = React.memo<OverviewPanelProps>(
  ({
    hasMessages,
    companyCount,
    indexedChunkCount,
    onReturnToConversation,
    isBackendConnected,
    isPipelineReady,
    onRetryConnection,
    scopeLabel,
    recentConversations,
    onSelectTemplate,
    onSelectConversation,
  }) => {
    const { locale } = useLocale();
    const vi = locale === "vi";
    return (
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
              {vi ? "Quay lại cuộc trò chuyện" : "Return to conversation"}
            </button>
          ) : (
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-brand-indigo/30 bg-brand-indigo/5 dark:bg-brand-indigo/10 text-brand-indigo text-xs font-semibold shadow-4xs">
              <Sparkles className="w-3.5 h-3.5 animate-pulse" />
              <span>
                {vi ? "SEC EDGAR Intelligence · nghiên cứu filing" : "SEC EDGAR Intelligence · filing research"}
              </span>
            </div>
          )}
        </div>

        <h2 className="hero-title max-w-full text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight py-1 font-serif break-words">
          {vi ? "Đặt câu hỏi. Kiểm chứng mọi câu trả lời." : "Ask questions. Verify every answer."}
        </h2>
        <p className="mx-auto max-w-xl text-sm leading-relaxed text-[var(--text-muted)] font-sans md:text-base">
          {vi
            ? "Nghiên cứu filing SEC 10-K với bằng chứng có trích dẫn và dấu vết truy xuất rõ ràng."
            : "Research SEC 10-K filings with cited evidence and a clear retrieval trail."}
        </p>
      </div>

      <section className="overview-corpus-summary" aria-label={vi ? "Thông tin kho dữ liệu" : "Corpus summary"}>
        <div className="overview-corpus-summary__heading">
          <span className="overview-corpus-summary__title">
            <Database className="h-4 w-4" aria-hidden="true" />
            {vi ? "Kho dữ liệu hiện có" : "Available corpus"}
          </span>
          <span>{vi ? "Chỉ hiển thị metadata do dịch vụ báo cáo" : "Only service-reported metadata is shown"}</span>
        </div>
        {companyCount !== null || indexedChunkCount != null ? (
          <div className="overview-corpus-summary__facts">
            {companyCount !== null && (
              <span><strong>{companyCount}</strong> {vi ? "công ty có thể tìm kiếm" : "searchable companies"}</span>
            )}
            {indexedChunkCount != null && (
              <span><strong>{indexedChunkCount}</strong> {vi ? "đoạn đã lập chỉ mục" : "indexed chunks"}</span>
            )}
          </div>
        ) : (
          <p className="overview-corpus-summary__empty">
            {isBackendConnected === false
              ? vi ? "Metadata kho dữ liệu không khả dụng khi dịch vụ offline." : "Corpus metadata is unavailable while the service is offline."
              : vi ? "Chưa có metadata kho dữ liệu từ dịch vụ nghiên cứu." : "No corpus metadata has been reported by the research service yet."}
          </p>
        )}
      </section>

      <div className="overview-scope" aria-label={vi ? `Phạm vi hiện tại: ${scopeLabel}` : `Current scope: ${scopeLabel}`}>
        <span>{vi ? "Phạm vi hiện tại" : "Current scope"}</span>
        <strong>{scopeLabel}</strong>
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
              ? vi ? "Đang kết nối tới dịch vụ nghiên cứu…" : "Connecting to the research service…"
              : isBackendConnected === false
                ? vi ? "Dịch vụ nghiên cứu đang offline. Hãy kết nối backend FastAPI để bắt đầu hỏi." : "The research service is offline. Connect the FastAPI backend to start asking questions."
                : vi ? "Dịch vụ nghiên cứu đã kết nối nhưng chỉ mục tài liệu chưa sẵn sàng." : "The research service is connected, but the document index is not ready yet."}
          </span>
          {isBackendConnected === false && (
            <button
              type="button"
              onClick={onRetryConnection}
              className="backend-notice__retry"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {vi ? "Thử lại" : "Retry"}
            </button>
          )}
        </div>
      ) : null}

      {/* Interactive Quick-Start Prompts */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-primary)]">
          <span className="flex items-center gap-1.5 font-sans">
            <Sparkles className="w-3.5 h-3.5 text-brand-indigo" />
            {vi ? "Khám phá câu hỏi mẫu" : "Explore sample research queries"}
          </span>
          <span className="text-[11px] font-normal text-[var(--text-subtle)]">
            {vi ? "Nhấn để nạp và tìm kiếm" : "Click to load & search"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {RESEARCH_TEMPLATES.slice(0, 4).map((template) => {
            const copy = getResearchTemplateCopy(template, locale);
            return (
            <button
              key={template.id}
              type="button"
              onClick={() => onSelectTemplate?.(template)}
              className="prompt-card group"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="prompt-card__icon">
                    {React.createElement(getSemanticIcon(template.iconKey), { className: "w-3.5 h-3.5", "aria-hidden": true })}
                  </div>
                  <span className="text-xs font-bold text-[var(--text-primary)] truncate group-hover:text-[var(--accent-text)] transition-colors">
                    {copy.label}
                  </span>
                </div>
                <ArrowRight className="h-3.5 w-3.5 flex-shrink-0 text-[var(--text-subtle)] transition-[color,transform] duration-150 group-hover:translate-x-0.5 group-hover:text-[var(--accent-text)]" aria-hidden="true" />
              </div>
              <p className="line-clamp-2 text-xs leading-relaxed text-[var(--text-muted)]">
                {copy.description}
              </p>
            </button>
            );
          })}
        </div>
      </div>

      {recentConversations.length > 0 && (
        <section className="overview-recent" aria-labelledby="recent-conversations-title">
          <div className="overview-section-heading">
            <span className="flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5" />
              <span id="recent-conversations-title">{vi ? "Cuộc trò chuyện gần đây" : "Recent conversations"}</span>
            </span>
            <span>{vi ? "Từ thư viện trên thiết bị" : "From your local library"}</span>
          </div>
          <div className="overview-recent__list">
            {recentConversations.slice(0, 3).map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                className="overview-recent__item"
                onClick={() => onSelectConversation?.(conversation)}
              >
                <span className="overview-recent__title">{conversation.title}</span>
                <span className="overview-recent__meta">
                  {conversation.messages.length} {vi ? "tin nhắn" : "messages"} · {new Intl.DateTimeFormat(locale, { month: "short", day: "numeric" }).format(conversation.updatedAt)}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Feature Architecture Cards */}
      <details className="overview-capabilities">
        <summary>{vi ? "Cách hệ thống truy xuất bằng chứng" : "How the evidence workflow works"}</summary>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5" id="features-cards">
          {features.map(({ title, description, tooltip, iconKey, accentFamily, badge }) => (
            <article className="feature-card" key={title}>
              <div className="flex items-center justify-between mb-2">
                <Tooltip content={tooltip}>
                  <div className="feature-card__icon" data-feature={accentFamily}>
                    {React.createElement(getSemanticIcon(iconKey), { className: "w-4 h-4", "aria-hidden": true })}
                  </div>
                </Tooltip>
                <span className="rounded border border-[var(--border-subtle)] px-2 py-0.5 font-mono text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                  {badge}
                </span>
              </div>
              <h3 className="feature-card__title">{title}</h3>
              <p className="feature-card__description">{description}</p>
            </article>
          ))}
        </div>
      </details>

      {/* Workspace Guide Collapsible */}
      <details className="workspace-guide group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-bold text-brand-indigo [&::-webkit-details-marker]:hidden">
          <span className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4" />
            {vi ? "Cách đọc workspace" : "How to read the workspace"}
          </span>
          <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
        </summary>
        <div className="ui-expand-enter grid grid-cols-1 gap-4 pt-4 text-sm leading-relaxed text-[var(--text-muted)] md:grid-cols-3">
          <p>
            <strong className="block text-[var(--text-primary)]">
              {vi ? "1. Chọn phạm vi" : "1. Choose scope"}
            </strong>
            {vi ? "Chọn công ty và mục 10-K, hoặc để Tất cả để khám phá và so sánh." : "Select a company and 10-K section, or leave both on All for discovery and comparisons."}
          </p>
          <p>
            <strong className="block text-[var(--text-primary)]">
              {vi ? "2. Hỏi tự nhiên" : "2. Ask naturally"}
            </strong>
            {vi ? "Câu hỏi so sánh có thể được tách thành các truy vấn tập trung trước khi tạo tóm tắt có căn cứ." : "Comparisons can be decomposed into focused sub-queries before a grounded summary is produced."}
          </p>
          <p>
            <strong className="block text-[var(--text-primary)]">
              {vi ? "3. Kiểm chứng bằng chứng" : "3. Verify evidence"}
            </strong>
            {vi ? "Mở bảng bằng chứng để đọc đoạn nguồn. Điểm rank chỉ sắp xếp kết quả, không phải phần trăm tin cậy." : "Open the evidence panel to read source excerpts. Rank scores order results; they are not confidence percentages."}
          </p>
        </div>
        <p className="border-t border-[var(--border-subtle)] pt-3 text-xs text-[var(--text-muted)] md:col-span-3">
          {vi ? "Chỉ dành cho demo nghiên cứu · Câu trả lời có thể chưa đầy đủ và không phải tư vấn tài chính." : "Research demo only · Answers may be incomplete and are not financial advice."}
        </p>
      </details>
    </div>
    );
  },
);

OverviewPanel.displayName = "OverviewPanel";
