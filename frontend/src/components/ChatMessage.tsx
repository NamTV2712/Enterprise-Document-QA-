/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  User,
  Cpu,
  AlertCircle,
  Loader2,
  RefreshCw,
  ChevronDown,
  Copy,
  Check,
  FileText,
  Bookmark,
  BookmarkCheck,
  StickyNote,
  ThumbsDown,
  ThumbsUp,
  Layers2,
  BarChart3,
} from "lucide-react";
import {
  AnswerVariant,
  EvidenceSelection,
  FeedbackCategory,
  Message,
  MessageFeedback,
  RequestSnapshot,
  StageEvent,
} from "../types";
import { SourcesPanel } from "./SourcesPanel";
import { SubQueriesPanel } from "./SubQueriesPanel";
import { useLocale } from "../lib/i18n";
import { formatCompanyLabel, SECTION_METADATA } from "../lib/displayMetadata";
import { getSourceKey } from "../lib/sourceIdentity";
import { PipelineExecution } from "./PipelineExecution";

interface ChatMessageProps {
  message: Message;
  messageId?: string;
  isLatest?: boolean;
  onRetry?: (text: string, snapshot?: RequestSnapshot) => void;
  /** Bookmarked answers can be reopened from the Library filter. */
  bookmarked?: boolean;
  onToggleBookmark?: () => void;
  onSaveNote?: (note: string) => void;
  onFeedback?: (feedback: MessageFeedback | undefined) => void;
  variants?: AnswerVariant[];
  onSaveVariant?: () => void;
  /** The article container is focusable so Library links can land on it. */
  tabIndex?: number;
  onInspectSource?: (selection: Omit<EvidenceSelection, "conversationId">) => void;
  /** Publishes answer identity only on focus, pointer interaction, or variant changes. */
  onDisplayedAnswerContext?: (context: { messageId: string; variantId: string | null }) => void;
  pipelineStages?: StageEvent[];
}

// Tickers rendered with the monospace ticker chip styling
const COMMON_TICKERS = [
  "AAPL",
  "MSFT",
  "GOOGL",
  "AMZN",
  "META",
  "NVDA",
  "TSLA",
  "NFLX",
  "AMD",
  "INTC",
  "SEC",
  "EDGAR",
  "RAG",
];

const FEEDBACK_CATEGORIES: Array<{
  value: FeedbackCategory;
  en: string;
  vi: string;
}> = [
  { value: "inaccurate", en: "Inaccurate", vi: "Không chính xác" },
  { value: "incomplete", en: "Incomplete", vi: "Thiếu ý" },
  { value: "irrelevant", en: "Not relevant", vi: "Không liên quan" },
  { value: "citation_issue", en: "Citation issue", vi: "Vấn đề trích dẫn" },
  { value: "other", en: "Other", vi: "Khác" },
];

// Inline content helper to parse and wrap citations, tickers, and numbers in monospace font
const formatMonospaceInline = (
  text: any,
  onCitation?: (index: number) => void,
  sourceCount = 0,
): React.ReactNode => {
  if (typeof text !== "string") return text;

  // Match citations like [Source 1], tickers of 3-5 uppercase letters, scores, currencies, percentages, and numbers
  const regex =
    /(\[Source\s+\d+\]|\b[A-Z]{3,5}\b|\b\d+\.\d+%?|\b\d+,\d+(?:,\d+)*(?:\.\d+)?%?|\b\d+%|\$\d+(?:\.\d+)?[BMK]?)/g;
  const tokens = text.split(regex);

  return (
    <>
      {tokens.map((token, idx) => {
        // [Source N] citation badge
        if (/^\[Source\s+\d+\]$/i.test(token)) {
          const sourceIndex = Number(token.match(/\d+/)?.[0] || 0) - 1;
          const isAvailable = sourceIndex >= 0 && sourceIndex < sourceCount;
          if (onCitation) {
            return isAvailable ? (
              <button
                key={idx}
                type="button"
                className="citation-button"
                onClick={() => onCitation(sourceIndex)}
                aria-label={`Open source ${sourceIndex + 1}`}
              >
                {token}
              </button>
            ) : (
              <span key={idx} className="citation-button citation-button--unavailable">
                {token}
              </span>
            );
          }
          return (
            <span
              key={idx}
              className="inline-flex items-center font-mono font-bold px-1.5 py-0.5 bg-brand-indigo/10 text-[var(--accent-text)] dark:bg-brand-indigo/20 dark:text-indigo-300 rounded text-xs select-all border border-brand-indigo/30 shadow-4xs mx-0.5"
            >
              {token}
            </span>
          );
        }
        // Tickers
        if (/^[A-Z]{3,5}$/.test(token)) {
          if (COMMON_TICKERS.includes(token)) {
            return (
              <span
                key={idx}
                className="font-mono font-bold px-1 py-0.5 bg-slate-100 dark:bg-slate-800 text-[var(--text-primary)] rounded text-xs select-all border border-slate-200/50 dark:border-slate-700/50"
              >
                {token}
              </span>
            );
          }
        }
        // Numbers, scores, percentages, currencies
        if (
          /^\d+\.\d+%?$/.test(token) ||
          /^\d+,\d+/.test(token) ||
          /^\d+%$/.test(token) ||
          /^\$\d+/.test(token)
        ) {
          return (
            <span
              key={idx}
              className="font-mono font-semibold text-[var(--text-primary)] bg-[var(--surface)] border border-slate-200/40 dark:border-slate-800/60 px-1 py-0.5 rounded text-xs"
            >
              {token}
            </span>
          );
        }
        return token;
      })}
    </>
  );
};

// Recursive node formatter for ReactMarkdown children
const renderFormattedChildren = (
  children: React.ReactNode,
  onCitation?: (index: number) => void,
  sourceCount = 0,
): React.ReactNode => {
  return React.Children.map(children, (child) => {
    if (typeof child === "string") {
      return formatMonospaceInline(child, onCitation, sourceCount);
    }
    if (React.isValidElement(child)) {
      // Do not place citation buttons inside links or code blocks.
      if (child.type === "a" || child.type === "code" || child.type === "pre") {
        return child;
      }
      // If the child is an element, recursively map its children
      const element = child as React.ReactElement<any>;
      if (element.props && element.props.children) {
        return React.cloneElement(element, {
          ...element.props,
          children: renderFormattedChildren(
            element.props.children,
            onCitation,
            sourceCount,
          ),
        });
      }
    }
    return child;
  });
};

const ChatMessageBase: React.FC<ChatMessageProps> = ({
  message,
  messageId = message.id,
  isLatest = false,
  onRetry,
  bookmarked = false,
  onToggleBookmark,
  onSaveNote,
  onFeedback,
  variants = [],
  onSaveVariant,
  tabIndex,
  onInspectSource,
  onDisplayedAnswerContext,
  pipelineStages,
}) => {
  const { locale, t } = useLocale();
  const isUser = message.sender === "user";
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [focusSourceIndex, setFocusSourceIndex] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(message.feedback?.rating ?? null);
  const [feedbackCategory, setFeedbackCategory] = useState<FeedbackCategory | null>(message.feedback?.category ?? null);
  const [isNoteOpen, setIsNoteOpen] = useState(false);
  const [isSecondaryActionsOpen, setIsSecondaryActionsOpen] = useState(false);
  const [noteDraft, setNoteDraft] = useState(message.note ?? "");
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const selectedVariant = variants.find((variant) => variant.id === selectedVariantId) ?? null;
  const displayedText = selectedVariant?.text ?? message.text;
  const displayedSources = selectedVariant?.sources ?? message.sources;
  const displayedExecution = selectedVariant?.execution ?? message.execution;
  const displayedVisualAnswer = selectedVariant?.visualAnswer ?? message.visualAnswer;
  const selectedVariantIndex = selectedVariant ? variants.findIndex((variant) => variant.id === selectedVariant.id) + 1 : 0;
  const reportDisplayedAnswerContext = (variantId = selectedVariant?.id ?? null) => {
    if (
      isUser ||
      message.isStreaming ||
      message.error ||
      message.status === "error" ||
      !displayedText.trim()
    ) {
      return;
    }
    onDisplayedAnswerContext?.({ messageId, variantId });
  };
  const hasSecondaryActions = Boolean(
    (onToggleBookmark && message.status !== "error") ||
    (onFeedback && message.status !== "error") ||
    (onSaveVariant && message.status !== "error" && !message.isStreaming && message.text) ||
    (onSaveNote && message.status !== "error"),
  );
  const scopeSnapshot = message.requestSnapshot
    ? [
        message.requestSnapshot.ticker
          ? formatCompanyLabel(message.requestSnapshot.ticker)
          : locale === "vi" ? "Tất cả công ty" : "All companies",
        message.requestSnapshot.section
          ? SECTION_METADATA[message.requestSnapshot.section]?.shortLabel || message.requestSnapshot.section
          : locale === "vi" ? "Tất cả mục" : "All sections",
        `Top ${message.requestSnapshot.topK}`,
        ...(message.requestSnapshot.enableComparative ? [locale === "vi" ? "So sánh" : "Comparison"] : []),
      ].join(" · ")
    : null;
  const inspectCitation = (citationIndex: number, fallbackSource?: { citation: string; text_preview: string; chunk_id?: string; document_id?: string }) => {
    const source = displayedSources?.[citationIndex] ?? fallbackSource;
    if (!source) return;
    onInspectSource?.({
      messageId,
      ...(selectedVariant?.id ? { variantId: selectedVariant.id } : {}),
      citationIndex,
      ...(source.chunk_id ? { chunkId: source.chunk_id } : {}),
      ...(source.document_id ? { documentId: source.document_id } : {}),
      sourceKey: getSourceKey(source),
    });
    // The workspace evidence inspector owns focus when it is present. Avoid
    // scheduling a second focus target in the legacy message-level source
    // panel, which could steal focus back after the inspector closes.
    if (!onInspectSource) setFocusSourceIndex(citationIndex);
  };

  useEffect(() => {
    setFeedback(message.feedback?.rating ?? null);
    setFeedbackCategory(message.feedback?.category ?? null);
  }, [message.feedback, message.id]);

  const updateFeedback = (rating: "up" | "down") => {
    if (feedback === rating) {
      setFeedback(null);
      setFeedbackCategory(null);
      onFeedback?.(undefined);
      return;
    }
    setFeedback(rating);
    const category = rating === "down" ? feedbackCategory ?? undefined : undefined;
    if (rating === "up") setFeedbackCategory(null);
    onFeedback?.({ rating, ...(category ? { category } : {}), at: Date.now() });
  };

  const updateFeedbackCategory = (category: FeedbackCategory) => {
    setFeedback("down");
    setFeedbackCategory(category);
    onFeedback?.({ rating: "down", category, at: Date.now() });
  };

  const handleCopy = async () => {
    if (!displayedText) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(displayedText);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 2000);
    } catch {
      setCopyState("error");
      window.setTimeout(() => setCopyState("idle"), 2500);
    }
  };

  return (
    <div
      className="ui-message-enter w-full px-3 py-2 md:px-5 md:py-2.5"
      id={`message-${message.id}`}
      role="article"
      aria-label={isUser ? (locale === "vi" ? "Câu hỏi của bạn" : "Your question") : locale === "vi" ? "Câu trả lời của trợ lý nghiên cứu" : "Research assistant response"}
      tabIndex={tabIndex}
      onFocus={(event) => {
        // Do not rerender while a nested citation/action is receiving focus;
        // that could replace the node before its click event is dispatched.
        if (event.target === event.currentTarget) reportDisplayedAnswerContext();
      }}
    >
      <div
        className={`max-w-4xl mx-auto w-full flex gap-3 md:gap-4 ${
          isUser
            ? "flex-row-reverse items-start py-2"
            : "chat-message-assistant items-start rounded-2xl p-4 md:p-5"
        }`}
      >
        <div className="flex-shrink-0">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-3xs border ${
              isUser
                ? "bg-brand-indigo/10 text-brand-indigo border-brand-indigo/20"
                : message.error
                  ? "bg-rose-100 text-rose-600 dark:bg-rose-950/50 dark:text-rose-400 border-rose-200 dark:border-rose-900"
                  : "bg-slate-100 text-[var(--text-primary)] dark:bg-slate-850 border-slate-200 dark:border-slate-700"
            }`}
          >
            {isUser ? (
              <User className="w-4 h-4" />
            ) : message.error ? (
              <AlertCircle className="w-4 h-4" />
            ) : (
              <Cpu className="w-4 h-4" />
            )}
          </div>
        </div>

        <div
          className={`${isUser ? "flex-none w-fit max-w-[82%] md:max-w-2xl" : "flex-1"} space-y-3 overflow-hidden`}
        >
          <div className={`flex flex-wrap items-center justify-between gap-2 ${isUser ? "justify-end" : ""}`}>
            <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[var(--text-muted)] font-sans">
                {isUser ? (locale === "vi" ? "Câu hỏi của bạn" : "Your question") : locale === "vi" ? "Trợ lý nghiên cứu filing SEC" : "SEC Filing Research Assistant"}
              </span>
              {!isUser && message.model_used && (
                <span className="text-xs font-mono font-medium bg-slate-50 dark:bg-[var(--surface)] border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 px-1.5 py-0.5 rounded shadow-4xs">
                  {message.model_used}
                </span>
              )}
            </div>

          </div>

          {isUser && scopeSnapshot && (
            <div className="message-scope-snapshot" aria-label={locale === "vi" ? `Phạm vi câu hỏi: ${scopeSnapshot}` : `Question scope: ${scopeSnapshot}`}>
              <span>{locale === "vi" ? "Phạm vi câu hỏi" : "Question scope"}</span>
              <strong>{scopeSnapshot}</strong>
            </div>
          )}

          <div className={isUser ? "message-answer-layout" : "assistant-evidence-layout"}>
          <div className="assistant-answer-column">
          {/* Keep the answer visually primary; execution details follow it. */}
          <div
            className={`ui-answer-enter prose prose-slate dark:prose-invert max-w-none text-[var(--text-primary)] text-sm md:text-base leading-relaxed font-sans ${
              isUser
                ? "rounded-2xl rounded-tr-md border border-brand-indigo/20 bg-brand-indigo/[0.06] dark:bg-brand-indigo/[0.10] px-4 py-3 shadow-3xs"
                : ""
            }`}
            onClick={() => reportDisplayedAnswerContext()}
          >
                {isUser ? (
                  <p className="!m-0 whitespace-pre-wrap select-text font-sans text-[var(--text-primary)]">
                    {message.text}
                  </p>
                ) : message.error ? (
                  <div className="space-y-2">
                    <div className="p-3 bg-rose-50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-950/50 rounded-lg text-rose-850 dark:text-rose-300 flex items-start gap-2 font-sans">
                      <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <p className="text-xs md:text-sm font-medium">
                        {message.text}
                      </p>
                    </div>
                    {message.errorDetail && (
                      <details className="error-details rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-muted)] text-xs">
                        <summary className="cursor-pointer px-3 py-2 font-semibold text-[var(--text-muted)]">
                          Technical details
                        </summary>
                        <pre className="overflow-x-auto border-t border-[var(--border-subtle)] px-3 py-2 font-mono text-[11px] leading-relaxed text-[var(--text-subtle)] whitespace-pre-wrap">
                          {message.errorDetail}
                        </pre>
                      </details>
                    )}
                    {onRetry && (
                      <button
                        type="button"
                        onClick={() => onRetry(message.retryText || message.text, message.requestSnapshot)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900 rounded-lg hover:bg-rose-100 dark:hover:bg-rose-950/40 transition-colors cursor-pointer"
                      >
                        <RefreshCw className="w-3 h-3" />
                        Retry
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="markdown-body select-text">
                    {displayedText ? (
                      message.isStreaming ? (
                          <p className="whitespace-pre-wrap text-sm md:text-base leading-relaxed text-[var(--text-primary)]">
                          {displayedText}
                        </p>
                      ) : (
                        <ReactMarkdown
                          components={{
                          table: ({ ...props }) => (
                            <div className="overflow-x-auto my-4 border border-slate-200/90 dark:border-slate-800 rounded-xl shadow-4xs bg-white dark:bg-[var(--surface)]/80">
                              <table
                                className="w-full text-xs text-left border-collapse"
                                {...props}
                              />
                            </div>
                          ),
                          thead: ({ ...props }) => (
                            <thead
                              className="bg-[var(--surface-muted)] text-[var(--text-primary)] border-b border-[var(--border-subtle)]"
                              {...props}
                            />
                          ),
                          th: ({ ...props }) => (
                            <th
                              className="px-3 py-2.5 font-bold text-xs tracking-wider uppercase font-sans border-r last:border-r-0 border-slate-200/50 dark:border-slate-800/60"
                              {...props}
                            />
                          ),
                          tbody: ({ ...props }) => (
                            <tbody
                              className="divide-y divide-slate-100 dark:divide-slate-800/50 bg-white dark:bg-transparent"
                              {...props}
                            />
                          ),
                          td: ({ ...props }) => (
                            <td
                              className="px-3 py-2.5 font-mono text-xs text-[var(--text-primary)] border-r last:border-r-0 border-slate-100 dark:border-slate-800/40"
                              {...props}
                            />
                          ),
                          p: ({ children }) => (
                            <p className="mb-3.5 last:mb-0 text-sm md:text-base leading-relaxed text-[var(--text-primary)]">
                              {renderFormattedChildren(children, inspectCitation, displayedSources?.length || 0)}
                            </p>
                          ),
                          ul: ({ children }) => (
                            <ul className="list-disc pl-5 mb-3 text-sm space-y-1.5 text-[var(--text-primary)]">
                              {renderFormattedChildren(children, inspectCitation, displayedSources?.length || 0)}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="list-decimal pl-5 mb-3 text-sm space-y-1.5 text-[var(--text-primary)]">
                              {renderFormattedChildren(children, inspectCitation, displayedSources?.length || 0)}
                            </ol>
                          ),
                          li: ({ children }) => (
                            <li className="text-sm md:text-base leading-relaxed">
                              {renderFormattedChildren(children, inspectCitation, displayedSources?.length || 0)}
                            </li>
                          ),
                          strong: ({ children, ...props }) => (
                            <strong
                              className="font-bold text-[var(--text-primary)] font-sans"
                              {...props}
                            >
                              {renderFormattedChildren(children, inspectCitation, displayedSources?.length || 0)}
                            </strong>
                          ),
                          em: ({ children, ...props }) => (
                            <em className="italic" {...props}>
                              {renderFormattedChildren(children, inspectCitation, displayedSources?.length || 0)}
                            </em>
                          ),
                          }}
                        >
                          {displayedText}
                        </ReactMarkdown>
                      )
                    ) : (
                      <div className="flex items-center gap-2 text-slate-400 py-1 font-mono">
                        <Loader2 className="w-4 h-4 animate-spin text-brand-indigo" />
                        <span className="text-sm font-medium">
                          Retrieving filing evidence and preparing an answer…
                        </span>
                      </div>
                    )}
                  </div>
                )}
          </div>

          {!isUser && displayedVisualAnswer && (
            <section className="rounded-lg border border-[var(--border-subtle)] surface-muted p-3" aria-label={locale === "vi" ? "Dữ liệu được kiểm chứng" : "Verified filing metric"}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2 text-xs font-semibold text-[var(--text-muted)]">
                  <BarChart3 className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{displayedVisualAnswer.label}</span>
                </div>
                <span className="shrink-0 text-xs text-[var(--text-subtle)]">FY {displayedVisualAnswer.period}</span>
              </div>
              <p className="mt-2 text-xl font-semibold tabular-nums text-[var(--text-primary)]">{displayedVisualAnswer.display_value}</p>
              <p className="mt-1 text-xs leading-relaxed text-[var(--text-muted)]">{displayedVisualAnswer.evidence_quote}</p>
              {onInspectSource && (
                <button
                  type="button"
                  className="mt-2 text-xs font-semibold text-[var(--focus-ring)] hover:underline"
                  onClick={() => inspectCitation(displayedVisualAnswer.source_index, {
                    citation: displayedVisualAnswer.citation,
                    text_preview: displayedVisualAnswer.evidence_quote,
                    chunk_id: displayedVisualAnswer.source_chunk_id,
                  })}
                >
                  {locale === "vi" ? "Mở bằng chứng" : "Open evidence"}
                </button>
              )}
            </section>
          )}

          {!isUser && message.isStreaming && (
            <div className="inline-flex items-center ml-1" aria-label="Answer is streaming">
              <span className="inline-block w-2 h-4 bg-brand-indigo animate-pulse rounded-xs" />
            </div>
          )}

          {!isUser && (displayedSources?.length || selectedVariant || displayedExecution?.elapsed_ms !== undefined) && (
            <div className="message-answer-meta" aria-label={locale === "vi" ? "Siêu dữ liệu câu trả lời" : "Answer metadata"}>
              {displayedSources && displayedSources.length > 0 && (
                <span><FileText className="h-3.5 w-3.5" aria-hidden="true" />{displayedSources.length} {locale === "vi" ? "nguồn" : "sources"}</span>
              )}
              <span>{selectedVariant ? (locale === "vi" ? `Bản ${selectedVariantIndex}` : `Variant ${selectedVariantIndex}`) : (locale === "vi" ? "Bản gốc" : "Original answer")}</span>
              {typeof displayedExecution?.elapsed_ms === "number" && <span>{displayedExecution.elapsed_ms.toFixed(0)} ms</span>}
            </div>
          )}

          {!isUser && !message.isStreaming && (displayedText || displayedSources?.length) && (
            <div className="message-action-row" aria-label={locale === "vi" ? "Hành động chính của câu trả lời" : "Primary answer actions"} onClick={() => reportDisplayedAnswerContext()}>
              {displayedText && (
                <button
                  type="button"
                  onClick={handleCopy}
                  aria-label={copyState === "copied" ? (locale === "vi" ? "Đã sao chép câu trả lời" : "Copied answer") : (locale === "vi" ? "Sao chép câu trả lời" : "Copy answer")}
                  className="message-primary-action"
                >
                  {copyState === "copied" ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : copyState === "error" ? <AlertCircle className="h-3.5 w-3.5 text-rose-500" /> : <Copy className="h-3.5 w-3.5" />}
                  <span>{copyState === "copied" ? t("common.copied") : copyState === "error" ? (locale === "vi" ? "Không thể sao chép" : "Copy unavailable") : t("common.copy")}</span>
                </button>
              )}
              {onInspectSource && displayedSources && displayedSources.length > 0 && (
                <button
                  type="button"
                  onClick={() => inspectCitation(0)}
                  aria-label={locale === "vi" ? `Mở ${displayedSources.length} nguồn` : `Open ${displayedSources.length} sources`}
                  className="message-primary-action message-primary-action--sources"
                >
                  <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>{locale === "vi" ? "Nguồn" : "Sources"}</span>
                  <span className="message-primary-action__count">{displayedSources.length}</span>
                </button>
              )}
              {hasSecondaryActions && (
                <details
                  className="message-secondary-actions"
                  open={isSecondaryActionsOpen || feedback === "down" || isNoteOpen}
                  onToggle={(event) => setIsSecondaryActionsOpen(event.currentTarget.open)}
                >
                  <summary>
                    <span>{locale === "vi" ? "Thao tác khác" : "More actions"}</span>
                    <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                  </summary>
                  <div className="message-secondary-actions__body">
                    {onToggleBookmark && message.status !== "error" && (
                      <button
                        type="button"
                        onClick={onToggleBookmark}
                        aria-label={bookmarked ? "Remove bookmark from this answer" : "Bookmark this answer"}
                        aria-pressed={bookmarked}
                        title={bookmarked ? "Remove bookmark" : "Bookmark answer"}
                        className={`message-secondary-action ${bookmarked ? "is-active" : ""}`}
                      >
                        {bookmarked ? <BookmarkCheck className="h-3.5 w-3.5" /> : <Bookmark className="h-3.5 w-3.5" />}
                        <span>{bookmarked ? (locale === "vi" ? "Đã đánh dấu" : "Bookmarked") : (locale === "vi" ? "Đánh dấu" : "Bookmark")}</span>
                      </button>
                    )}
                    {onFeedback && message.status !== "error" && (
                      <div className="message-feedback-actions" role="group" aria-label={locale === "vi" ? "Đánh giá câu trả lời" : "Rate this answer"}>
                        <button type="button" onClick={() => updateFeedback("up")} aria-label={locale === "vi" ? "Câu trả lời hữu ích" : "Helpful answer"} aria-pressed={feedback === "up"} title={locale === "vi" ? "Hữu ích" : "Helpful"} className={`message-secondary-action ${feedback === "up" ? "is-active" : ""}`}><ThumbsUp className="h-3.5 w-3.5" /><span>{locale === "vi" ? "Hữu ích" : "Helpful"}</span></button>
                        <button type="button" onClick={() => updateFeedback("down")} aria-label={locale === "vi" ? "Câu trả lời chưa hữu ích" : "Unhelpful answer"} aria-pressed={feedback === "down"} title={locale === "vi" ? "Chưa hữu ích" : "Unhelpful"} className={`message-secondary-action ${feedback === "down" ? "is-active is-negative" : ""}`}><ThumbsDown className="h-3.5 w-3.5" /><span>{locale === "vi" ? "Chưa hữu ích" : "Not helpful"}</span></button>
                      </div>
                    )}
                    {onSaveVariant && message.status !== "error" && !message.isStreaming && message.text && (
                      <button type="button" onClick={onSaveVariant} aria-label={locale === "vi" ? "Lưu phiên bản câu trả lời" : "Save answer variant"} title={locale === "vi" ? "Lưu phiên bản" : "Save variant"} className="message-secondary-action"><Layers2 className="h-3.5 w-3.5" /><span>{locale === "vi" ? "Lưu phiên bản" : "Save variant"}</span></button>
                    )}
                    {onSaveNote && message.status !== "error" && (
                      <button type="button" onClick={() => setIsNoteOpen((open) => !open)} aria-label={locale === "vi" ? "Ghi chú cho câu trả lời" : "Add note to answer"} aria-pressed={isNoteOpen || Boolean(message.note)} title={locale === "vi" ? "Ghi chú" : "Add note"} className={`message-secondary-action ${message.note ? "is-active is-note" : ""}`}><StickyNote className="h-3.5 w-3.5" /><span>{locale === "vi" ? "Ghi chú" : "Add note"}</span></button>
                    )}
                  </div>
                  {!isUser && feedback === "down" && !message.isStreaming && (
                    <div className="message-feedback-reasons" role="group" aria-label={locale === "vi" ? "Lý do đánh giá chưa hữu ích" : "Why was this answer unhelpful?"}>
                      <span className="font-semibold text-[var(--text-muted)]">{locale === "vi" ? "Lý do:" : "Reason:"}</span>
                      {FEEDBACK_CATEGORIES.map((category) => (
                        <button key={category.value} type="button" onClick={() => updateFeedbackCategory(category.value)} aria-pressed={feedbackCategory === category.value} className={`rounded-full border px-2 py-1 transition-colors ${feedbackCategory === category.value ? "border-rose-500/50 bg-rose-500/15 text-rose-700 dark:text-rose-300" : "border-[var(--border-subtle)] text-[var(--text-muted)] hover:bg-[var(--surface-muted)]"}`}>
                          {locale === "vi" ? category.vi : category.en}
                        </button>
                      ))}
                    </div>
                  )}
                  {!isUser && isNoteOpen && onSaveNote && !message.isStreaming && (
                    <div className="message-note-editor rounded-xl border border-amber-500/25 bg-amber-500/5 p-3">
                      <label className="block text-xs font-semibold text-[var(--text-muted)]" htmlFor={`note-${message.id}`}>{locale === "vi" ? "Ghi chú riêng trên thiết bị" : "Private device note"}</label>
                      <textarea id={`note-${message.id}`} value={noteDraft} onChange={(event) => setNoteDraft(event.target.value.slice(0, 10000))} maxLength={10000} rows={3} placeholder={locale === "vi" ? "Lưu ý, giả định hoặc việc cần kiểm tra…" : "Save an observation, assumption, or follow-up…"} className="mt-2 w-full resize-y rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-amber-500" />
                      <div className="mt-2 flex items-center justify-between gap-2"><span className="text-[11px] text-[var(--text-muted)]">{noteDraft.length}/10000</span><button type="button" onClick={() => { onSaveNote(noteDraft.trim()); setIsNoteOpen(false); }} className="rounded-lg bg-amber-500/15 px-3 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-500/25 dark:text-amber-300">{locale === "vi" ? "Lưu ghi chú" : "Save note"}</button></div>
                    </div>
                  )}
                </details>
              )}
            </div>
          )}

          {!isUser && message.note && !isNoteOpen && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-[var(--text-muted)]">
              <span className="font-semibold text-amber-700 dark:text-amber-300">{locale === "vi" ? "Ghi chú:" : "Note:"}</span> {message.note}
            </div>
          )}

          {!isUser && variants.length > 0 && (
            <div className="message-variant-switcher" aria-label={locale === "vi" ? "Các phiên bản câu trả lời" : "Answer variants"}>
              <span className="font-semibold text-[var(--text-muted)]">{locale === "vi" ? "Phiên bản:" : "Variants:"}</span>
              <button type="button" onClick={() => { setSelectedVariantId(null); reportDisplayedAnswerContext(null); }} className={`rounded-full border px-2 py-1 ${!selectedVariantId ? "border-[var(--accent-text)] bg-[var(--accent-soft)] text-[var(--accent-text)]" : "border-[var(--border-subtle)] text-[var(--text-muted)]"}`}>{locale === "vi" ? "Gốc" : "Original"}</button>
              {variants.map((variant, index) => (
                <button key={variant.id} type="button" onClick={() => { setSelectedVariantId(variant.id); reportDisplayedAnswerContext(variant.id); }} className={`rounded-full border px-2 py-1 ${selectedVariantId === variant.id ? "border-[var(--accent-text)] bg-[var(--accent-soft)] text-[var(--accent-text)]" : "border-[var(--border-subtle)] text-[var(--text-muted)]"}`}>
                  {locale === "vi" ? `Bản ${index + 1}` : `Variant ${index + 1}`}
                </button>
              ))}
            </div>
          )}

          {!isUser && (message.queryInterpretation || message.rewritten_query) && (
            <details className="group rounded-lg border border-brand-indigo/15 bg-brand-indigo/[0.035] text-xs">
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 font-semibold text-[var(--text-muted)] [&::-webkit-details-marker]:hidden">
                <span>{locale === "vi" ? "Câu hỏi đã diễn giải" : "Interpreted query"}</span>
                <ChevronDown className="h-4 w-4 text-brand-indigo transition-transform group-open:rotate-180" />
              </summary>
              <p className="ui-expand-enter border-t border-brand-indigo/10 px-3 py-2 font-mono text-xs italic leading-relaxed text-brand-indigo">{message.queryInterpretation?.retrieval_question || message.rewritten_query}</p>
            </details>
          )}

          {!isUser && (displayedExecution || pipelineStages?.length) && (
            <PipelineExecution events={pipelineStages} trace={displayedExecution} isStreaming={message.isStreaming} />
          )}

          {!isUser && !onInspectSource && displayedSources && displayedSources.length > 0 && (
            <SourcesPanel sources={displayedSources} messageId={messageId} focusSourceIndex={focusSourceIndex} onFocusHandled={() => setFocusSourceIndex(null)} />
          )}

          {!isUser && (message.subQueries || message.wasDecomposed) && (
            <SubQueriesPanel
              subQueries={message.subQueries || []}
              isLatest={isLatest}
            />
          )}

          </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Memoized so that streaming token updates to the latest message do not
 * re-render every historical message in the list. Props are shallow-compared:
 * message objects keep stable identity for untouched items because the parent
 * maps with immutable updates.
 */
export const ChatMessage = React.memo(ChatMessageBase);
