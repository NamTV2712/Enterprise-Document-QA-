/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
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
  AnswerActionKind,
  AnswerActionState,
  AnswerActionStatus,
  EvidenceSelection,
  FeedbackCategory,
  Message,
  MessageFeedback,
  SaveAnswerVersionStatus,
  RequestSnapshot,
  StageEvent,
} from "../types";
import { SourcesPane } from "./workbench/SourcesPane";
import { SourcesPanel } from "./SourcesPanel";
import { SubQueriesPanel } from "./SubQueriesPanel";
import { useLocale } from "../lib/i18n";
import { formatCompanyLabel, SECTION_METADATA } from "../lib/displayMetadata";
import { getSourceKey } from "../lib/sourceIdentity";
import { PipelineExecution } from "./PipelineExecution";
import { RelatedResearchPanel } from "./RelatedResearchPanel";
import { buildRelatedResearchSuggestions } from "../lib/relatedResearch";

interface ChatMessageProps {
  message: Message;
  messageId?: string;
  isLatest?: boolean;
  onRetry?: (text: string, snapshot?: RequestSnapshot) => void;
  /** Bookmarked answers can be reopened from the Library filter. */
  bookmarked?: boolean;
  onToggleBookmark?: () => void | Promise<unknown>;
  onSaveNote?: (note: string) => void | Promise<unknown>;
  onFeedback?: (feedback: MessageFeedback | undefined) => void | Promise<unknown>;
  /** Local action states keyed to this exact answer/version target. */
  answerActionStates?: Partial<Record<AnswerActionKind, AnswerActionState>>;
  variants?: AnswerVariant[];
  onSaveVariant?: (context: { messageId: string; variantId: string | null }) => void;
  saveVariantStatus?: SaveAnswerVersionStatus;
  onRetrySaveVariant?: (context: { messageId: string; variantId: string | null }) => void;
  onViewSavedVersion?: () => void;
  /** The article container is focusable so Library links can land on it. */
  tabIndex?: number;
  /** Durable variant selected by an exact Library reopen action. */
  initialVariantId?: string;
  onInspectSource?: (selection: Omit<EvidenceSelection, "conversationId">) => void;
  /** Publishes answer identity only on focus, pointer interaction, or variant changes. */
  onDisplayedAnswerContext?: (context: { messageId: string; variantId: string | null }) => void;
  pipelineStages?: StageEvent[];
  availableSections?: readonly string[];
  onUseRelatedResearch?: (question: string, scope: { ticker: string | null; section: string | null }) => void;
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
  { value: "irrelevant", en: "Irrelevant", vi: "Không liên quan" },
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

const MarkdownCitationContext = createContext<{ onCitation: (index: number) => void; sourceCount: number } | null>(null);

function useFormattedMarkdownChildren(children: React.ReactNode): React.ReactNode {
  const binding = useContext(MarkdownCitationContext);
  return renderFormattedChildren(children, binding?.onCitation, binding?.sourceCount ?? 0);
}

const ChatMessageBase: React.FC<ChatMessageProps> = ({
  message,
  messageId = message.id,
  isLatest = false,
  onRetry,
  bookmarked = false,
  onToggleBookmark,
  onSaveNote,
  onFeedback,
  answerActionStates,
  variants = [],
  onSaveVariant,
  saveVariantStatus = "idle",
  onRetrySaveVariant,
  onViewSavedVersion,
  tabIndex,
  onInspectSource,
  onDisplayedAnswerContext,
  pipelineStages,
  availableSections = [],
  onUseRelatedResearch,
  initialVariantId,
}) => {
  const { locale, t } = useLocale();
  const isUser = message.sender === "user";
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [focusSourceIndex, setFocusSourceIndex] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(message.feedback?.rating ?? null);
  const [feedbackCategory, setFeedbackCategory] = useState<FeedbackCategory | null>(message.feedback?.category ?? null);
  const [otherFeedbackDraft, setOtherFeedbackDraft] = useState(message.feedback?.otherText ?? "");
  const [isOtherFeedbackOpen, setIsOtherFeedbackOpen] = useState(false);
  const [feedbackValidationError, setFeedbackValidationError] = useState<string | null>(null);
  const [isNoteOpen, setIsNoteOpen] = useState(false);
  const [isSecondaryActionsOpen, setIsSecondaryActionsOpen] = useState(false);
  const [noteDraft, setNoteDraft] = useState(message.note ?? "");
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(initialVariantId ?? null);
  const lastInitialVariantRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (initialVariantId === undefined) {
      lastInitialVariantRef.current = undefined;
      return;
    }
    if (lastInitialVariantRef.current === initialVariantId) return;
    lastInitialVariantRef.current = initialVariantId;
    if (variants.some((variant) => variant.id === initialVariantId)) setSelectedVariantId(initialVariantId);
  }, [initialVariantId, message.id, variants]);
  const selectedVariant = variants.find((variant) => variant.id === selectedVariantId) ?? null;
  const displayedText = selectedVariant?.text ?? message.text;
  const displayedSources = selectedVariant?.sources ?? message.sources;
  const displayedExecution = selectedVariant?.execution ?? message.execution;
  const factualMetadata = [
    typeof displayedSources?.length === "number" ? `${displayedSources.length} ${locale === "vi" ? "nguồn" : "sources"}` : null,
    typeof displayedExecution?.elapsed_ms === "number" ? `${(displayedExecution.elapsed_ms / 1000).toFixed(1)}s` : null,
    message.model_used?.trim() || null,
  ].filter((value): value is string => Boolean(value));
  const displayedVisualAnswer = selectedVariant?.visualAnswer ?? message.visualAnswer;
  const selectedVariantIndex = selectedVariant ? variants.findIndex((variant) => variant.id === selectedVariant.id) + 1 : 0;
  const bookmarkAction = answerActionStates?.bookmark;
  const feedbackAction = answerActionStates?.feedback;
  const noteAction = answerActionStates?.note;
  const actionPending = (action?: AnswerActionState) => action?.status === "pending";
  const actionStatusLabel = (status: AnswerActionStatus, kind: AnswerActionKind): string => {
    if (status === "pending") return locale === "vi" ? "Đang xử lý…" : "Working…";
    if (status === "persisted") return kind === "feedback"
      ? (locale === "vi" ? "Đã lưu đánh giá trên thiết bị." : "Feedback saved on this device.")
      : kind === "note"
        ? (locale === "vi" ? "Đã lưu ghi chú trên thiết bị." : "Note saved on this device.")
        : (locale === "vi" ? "Đã lưu trên thiết bị." : "Saved on this device.");
    if (status === "already_exists") return locale === "vi" ? "Đã tồn tại trong dữ liệu cục bộ." : "Already exists locally.";
    if (status === "volatile") return locale === "vi" ? "Chỉ giữ trong tab này; hãy thử lại hoặc xuất Thư viện." : "Saved for this tab only; retry or export the Library.";
    if (status === "cancelled") return locale === "vi" ? "Đã hủy do thay đổi ngữ cảnh." : "Cancelled after the answer context changed.";
    return locale === "vi" ? "Không thể lưu; hãy thử lại." : "Could not save; retry.";
  };
  const relatedSuggestions = onUseRelatedResearch && !isUser
    ? buildRelatedResearchSuggestions(message, availableSections)
    : [];
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
  const inspectCitation = useCallback((citationIndex: number, fallbackSource?: { citation: string; text_preview: string; chunk_id?: string; document_id?: string }) => {
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
  }, [displayedSources, messageId, onInspectSource, selectedVariant?.id]);

  // Stable Markdown component types preserve citation nodes and focus across
  // unrelated answer-action or reader updates.
  const markdownComponents = useMemo<Components>(() => ({
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
        {useFormattedMarkdownChildren(children)}
      </p>
    ),
    ul: ({ children }) => (
      <ul className="list-disc pl-5 mb-3 text-sm space-y-1.5 text-[var(--text-primary)]">
        {useFormattedMarkdownChildren(children)}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal pl-5 mb-3 text-sm space-y-1.5 text-[var(--text-primary)]">
        {useFormattedMarkdownChildren(children)}
      </ol>
    ),
    li: ({ children }) => (
      <li className="text-sm md:text-base leading-relaxed">
        {useFormattedMarkdownChildren(children)}
      </li>
    ),
    strong: ({ children, ...props }) => (
      <strong
        className="font-bold text-[var(--text-primary)] font-sans"
        {...props}
      >
        {useFormattedMarkdownChildren(children)}
      </strong>
    ),
    em: ({ children, ...props }) => (
      <em className="italic" {...props}>
        {useFormattedMarkdownChildren(children)}
      </em>
    ),
  }), []);

  useEffect(() => {
    const appliesToVariant = (message.feedback?.variantId ?? null) === (selectedVariantId ?? null);
    setFeedback(appliesToVariant ? message.feedback?.rating ?? null : null);
    setFeedbackCategory(appliesToVariant ? message.feedback?.category ?? null : null);
    setOtherFeedbackDraft(appliesToVariant ? message.feedback?.otherText ?? "" : "");
    setIsOtherFeedbackOpen(false);
    setFeedbackValidationError(null);
  }, [message.feedback, message.id, selectedVariantId]);

  const updateFeedback = (rating: "up" | "down") => {
    if (feedback === rating) {
      setFeedback(null);
      setFeedbackCategory(null);
      setIsOtherFeedbackOpen(false);
      setFeedbackValidationError(null);
      onFeedback?.(undefined);
      return;
    }
    setFeedback(rating);
    const category = rating === "down" ? feedbackCategory ?? undefined : undefined;
    if (rating === "up") {
      setFeedbackCategory(null);
      setIsOtherFeedbackOpen(false);
      setFeedbackValidationError(null);
    }
    onFeedback?.({ rating, ...(category ? { category } : {}), ...(selectedVariant?.id ? { variantId: selectedVariant.id } : {}), at: Date.now() });
  };

  const updateFeedbackCategory = (category: FeedbackCategory) => {
    setFeedback("down");
    setFeedbackCategory(category);
    setFeedbackValidationError(null);
    if (category === "other") {
      setIsOtherFeedbackOpen(true);
      return;
    }
    setIsOtherFeedbackOpen(false);
    onFeedback?.({ rating: "down", category, ...(selectedVariant?.id ? { variantId: selectedVariant.id } : {}), at: Date.now() });
  };

  const submitOtherFeedback = () => {
    const text = otherFeedbackDraft.trim().slice(0, 2_000);
    if (!text) {
      setFeedbackValidationError(locale === "vi" ? "Hãy nhập lý do trước khi gửi." : "Add a short reason before submitting.");
      return;
    }
    setFeedbackValidationError(null);
    setIsOtherFeedbackOpen(false);
    onFeedback?.({ rating: "down", category: "other", otherText: text, ...(selectedVariant?.id ? { variantId: selectedVariant.id } : {}), at: Date.now() });
  };

  const cancelOtherFeedback = () => {
    const persisted = message.feedback;
    const appliesToVariant = (persisted?.variantId ?? null) === (selectedVariantId ?? null);
    setIsOtherFeedbackOpen(false);
    setFeedbackValidationError(null);
    setFeedback(appliesToVariant ? persisted?.rating ?? null : null);
    setFeedbackCategory(appliesToVariant ? persisted?.category ?? null : null);
    setOtherFeedbackDraft(appliesToVariant ? persisted?.otherText ?? "" : "");
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
        className={`w-full flex gap-3 md:gap-4 ${
          isUser
            ? "flex-row-reverse items-start py-2"
            : "chat-message-assistant items-start rounded-lg p-3.5 md:p-4.5"
        }`}
      >
        <div className="flex-shrink-0">
          {isUser ? (
            <div className="w-8 h-8 rounded-full border border-slate-700 bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-400 shadow-sm" aria-label={locale === "vi" ? "Danh tính người dùng chưa có" : "User identity unavailable"}>
              ?
            </div>
          ) : (
            <div className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shadow-sm">
              <Cpu className="w-4 h-4" />
            </div>
          )}
        </div>

        <div
          className={`${isUser ? "flex-none w-fit max-w-[85%] md:max-w-2xl" : "flex-1"} space-y-2 overflow-hidden`}
        >
          {!isUser && (
            <div className="flex flex-wrap items-center justify-between gap-2 pb-1.5 mb-1.5 border-b border-slate-800/80">
              <div className="flex items-center gap-2">
                <span className="sr-only">
                  {locale === "vi" ? "Trợ lý Nghiên cứu Hồ sơ SEC" : "SEC Filing Research Assistant"}
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-[var(--state-success-surface)] text-[var(--state-success-text)] border border-[var(--state-success-border)]">
                  Answer
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {factualMetadata.length > 0
                    ? factualMetadata.join(" · ")
                    : (locale === "vi" ? "Chưa có metadata thực thi" : "Execution metadata unavailable")}
                </span>
              </div>
            </div>
          )}

          {isUser && (
            <div className="flex items-center justify-between gap-4 mb-1 text-xs text-slate-500">
              <span className="font-semibold text-[var(--text-muted)]">{locale === "vi" ? "Câu hỏi" : "Question"}</span>
            </div>
          )}

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
                        <MarkdownCitationContext.Provider value={{ onCitation: inspectCitation, sourceCount: displayedSources?.length ?? 0 }}>
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={markdownComponents}
                          >
                            {displayedText}
                          </ReactMarkdown>
                        </MarkdownCitationContext.Provider>
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
            <div className="message-answer-meta sr-only" aria-label={locale === "vi" ? "Siêu dữ liệu câu trả lời" : "Answer metadata"}>
              {displayedSources && displayedSources.length > 0 && (
                <span><FileText className="h-3.5 w-3.5" aria-hidden="true" />{displayedSources.length} {locale === "vi" ? "nguồn" : "sources"}</span>
              )}
              <span>{selectedVariant ? (locale === "vi" ? `Bản ${selectedVariantIndex}` : `Variant ${selectedVariantIndex}`) : (locale === "vi" ? "Bản gốc" : "Original answer")}</span>
              {typeof displayedExecution?.elapsed_ms === "number" && <span>{displayedExecution.elapsed_ms.toFixed(0)} ms</span>}
            </div>
          )}

          {!isUser && !message.isStreaming && (
            <div className="message-actions-container space-y-2 pt-2">
              {/* Citation Pills [1] [2] [3] [4] [5] */}
              {displayedSources && displayedSources.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap">
                  {displayedSources.slice(0, 5).map((source, idx) => (
                    <button
                      key={source.chunk_id || idx}
                      type="button"
                      onClick={() => inspectCitation(idx)}
                      className="min-h-11 min-w-11 sm:min-h-0 sm:min-w-0 px-2.5 py-0.5 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 text-xs font-mono text-[var(--accent-text)] font-semibold transition-colors"
                      title={`Open source [${idx + 1}]`}
                    >
                      [{idx + 1}]
                    </button>
                  ))}
                </div>
              )}

              {/* Action Buttons Row */}
              <div className="flex items-center justify-between gap-3 pt-1">
                <div className="flex items-center gap-2 flex-wrap">
                  {onInspectSource && displayedSources && displayedSources.length > 0 && (
                    <button
                      type="button"
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1 text-xs font-medium text-[var(--text-muted)] transition-colors hover:bg-slate-800 hover:text-[var(--text-primary)]"
                      onClick={() => onInspectSource?.({
                        citationIndex: 0,
                        chunkId: displayedSources[0]?.chunk_id,
                        sourceKey: getSourceKey(displayedSources[0]),
                        messageId: message.id,
                      })}
                      aria-label={`${locale === "vi" ? "Mở" : "Open"} ${displayedSources.length} ${locale === "vi" ? "nguồn" : "sources"}`}
                      title={`${locale === "vi" ? "Mở" : "Open"} ${displayedSources.length} ${locale === "vi" ? "nguồn" : "sources"}`}
                    >
                      <Layers2 className="h-3.5 w-3.5 text-slate-400" />
                      <span>{displayedSources.length} {locale === "vi" ? "nguồn" : "sources"}</span>
                    </button>
                  )}
                  {displayedText && (
                    <button
                      type="button"
                      onClick={handleCopy}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-xs text-[var(--text-muted)] font-medium transition-colors"
                    >
                      {copyState === "copied" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                      <span>{copyState === "copied" ? "Copied" : "Copy"}</span>
                    </button>
                  )}
                  {onRetry && (
                    <button
                      type="button"
                      onClick={() => onRetry(message.retryText || message.text, message.requestSnapshot)}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-xs text-[var(--text-muted)] font-medium transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
                      <span>Regenerate</span>
                    </button>
                  )}
                  {onSaveNote && (
                    <button
                      type="button"
                      onClick={() => setIsNoteOpen((open) => !open)}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-xs text-[var(--text-muted)] font-medium transition-colors"
                    >
                      <StickyNote className="w-3.5 h-3.5 text-slate-400" />
                      <span>Add to notes</span>
                    </button>
                  )}

                  {hasSecondaryActions && (
                    <details
                      className="message-secondary-actions"
                      open={isSecondaryActionsOpen || feedback === "down" || isNoteOpen}
                      onToggle={(event) => setIsSecondaryActionsOpen(event.currentTarget.open)}
                    >
                      <summary aria-label={locale === "vi" ? "Thao tác phụ của câu trả lời" : "Secondary answer actions"}>
                        <span>{locale === "vi" ? "Thao tác khác" : "More"}</span>
                        <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                      </summary>
                      <div className="message-secondary-actions__body">
                        {onToggleBookmark && message.status !== "error" && (
                          <button
                            type="button"
                            onClick={onToggleBookmark}
                            disabled={actionPending(bookmarkAction)}
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
                            <button type="button" onClick={() => updateFeedback("up")} disabled={actionPending(feedbackAction)} aria-label={locale === "vi" ? "Câu trả lời hữu ích" : "Helpful answer"} aria-pressed={feedback === "up"} title={locale === "vi" ? "Hữu ích" : "Helpful"} className={`message-secondary-action ${feedback === "up" ? "is-active" : ""}`}><ThumbsUp className="h-3.5 w-3.5" /><span>{locale === "vi" ? "Hữu ích" : "Helpful"}</span></button>
                            <button type="button" onClick={() => updateFeedback("down")} disabled={actionPending(feedbackAction)} aria-label={locale === "vi" ? "Câu trả lời chưa hữu ích" : "Unhelpful answer"} aria-pressed={feedback === "down"} title={locale === "vi" ? "Chưa hữu ích" : "Not helpful"} className={`message-secondary-action ${feedback === "down" ? "is-active is-negative" : ""}`}><ThumbsDown className="h-3.5 w-3.5" /><span>{locale === "vi" ? "Chưa hữu ích" : "Not helpful"}</span></button>
                          </div>
                        )}
                        {onSaveVariant && message.status !== "error" && !message.isStreaming && message.text && (
                          <button
                            type="button"
                            onClick={() => onSaveVariant({ messageId, variantId: selectedVariant?.id ?? null })}
                            disabled={saveVariantStatus === "saving" || saveVariantStatus === "pending"}
                            aria-label={locale === "vi" ? "Lưu phiên bản câu trả lời" : "Save answer version"}
                            title={locale === "vi" ? "Lưu phiên bản" : "Save answer version"}
                            className="message-secondary-action"
                          >
                            {saveVariantStatus === "saving" || saveVariantStatus === "pending" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Layers2 className="h-3.5 w-3.5" />}
                            <span>{locale === "vi" ? "Lưu phiên bản" : "Save answer version"}</span>
                          </button>
                        )}
                        {onSaveNote && message.status !== "error" && (
                          <button type="button" onClick={() => setIsNoteOpen((open) => !open)} disabled={actionPending(noteAction)} aria-label={locale === "vi" ? "Ghi chú cho câu trả lời" : "Add note to answer"} aria-pressed={isNoteOpen || Boolean(message.note)} title={locale === "vi" ? "Ghi chú" : "Add note"} className={`message-secondary-action ${message.note ? "is-active is-note" : ""}`}><StickyNote className="h-3.5 w-3.5" /><span>{locale === "vi" ? "Ghi chú" : "Add note"}</span></button>
                        )}
                      </div>
                      {saveVariantStatus !== "idle" && (
                        <div className="message-action-status" role="status" aria-live="polite">
                          <span>
                            {saveVariantStatus === "saving" && (locale === "vi" ? "Đang lưu phiên bản câu trả lời…" : "Saving answer version…")}
                            {saveVariantStatus === "pending" && (locale === "vi" ? "Đang lưu phiên bản câu trả lời…" : "Saving answer version…")}
                            {saveVariantStatus === "saved" && (locale === "vi" ? "Đã lưu phiên bản vào Thư viện." : "Answer version saved to Library.")}
                            {saveVariantStatus === "persisted" && (locale === "vi" ? "Đã lưu phiên bản trên thiết bị." : "Answer version saved on this device.")}
                            {saveVariantStatus === "already_saved" && (locale === "vi" ? "Phiên bản này đã được lưu." : "Already saved.")}
                            {saveVariantStatus === "already_exists" && (locale === "vi" ? "Phiên bản này đã được lưu." : "Already saved.")}
                            {saveVariantStatus === "volatile" && (locale === "vi" ? "Chỉ giữ trong tab này; hãy thử lại hoặc xuất Thư viện." : "Only in this tab; retry or export the Library.")}
                            {saveVariantStatus === "failed" && (locale === "vi" ? "Không thể lưu phiên bản; hãy thử lại." : "Could not save this version; retry.")}
                            {saveVariantStatus === "retryable" && (locale === "vi" ? "Không thể lưu phiên bản; hãy thử lại." : "Could not save this version; retry.")}
                            {saveVariantStatus === "cancelled" && (locale === "vi" ? "Đã hủy do thay đổi ngữ cảnh." : "Cancelled after the answer context changed.")}
                          </span>
                          {(saveVariantStatus === "saved" || saveVariantStatus === "persisted" || saveVariantStatus === "already_saved" || saveVariantStatus === "already_exists") && onViewSavedVersion && (
                            <button type="button" onClick={onViewSavedVersion} className="message-action-status__link">
                              {locale === "vi" ? "Mở Thư viện" : "View in Library"}
                            </button>
                          )}
                          {(saveVariantStatus === "failed" || saveVariantStatus === "retryable" || saveVariantStatus === "volatile") && onRetrySaveVariant && (
                            <button type="button" onClick={() => onRetrySaveVariant({ messageId, variantId: selectedVariant?.id ?? null })} className="message-action-status__link">
                              {locale === "vi" ? "Thử lại" : "Retry"}
                            </button>
                          )}
                        </div>
                      )}
                      {feedbackAction && feedbackAction.status !== "idle" && (
                        <div className="message-action-status" role="status" aria-live="polite">
                          <span>{actionStatusLabel(feedbackAction.status, "feedback")}{feedbackAction.warning ? ` ${feedbackAction.warning}` : ""}</span>
                        </div>
                      )}
                      {bookmarkAction && bookmarkAction.status !== "idle" && (
                        <div className="message-action-status" role="status" aria-live="polite">
                          <span>{actionStatusLabel(bookmarkAction.status, "bookmark")}{bookmarkAction.warning ? ` ${bookmarkAction.warning}` : ""}</span>
                        </div>
                      )}
                      {noteAction && noteAction.status !== "idle" && (
                        <div className="message-action-status" role="status" aria-live="polite">
                          <span>{actionStatusLabel(noteAction.status, "note")}{noteAction.warning ? ` ${noteAction.warning}` : ""}</span>
                        </div>
                      )}
                    </details>
                  )}
                </div>

                {onFeedback && (
                  <div className="flex items-center gap-1 text-slate-400">
                    <button
                      type="button"
                      aria-label={locale === "vi" ? "Hữu ích" : "Helpful"}
                      onClick={() => updateFeedback("up")}
                      className={`p-1.5 rounded-lg hover:bg-slate-800 transition-colors ${feedback === "up" ? "text-emerald-400 bg-emerald-500/10" : ""}`}
                      title="Helpful"
                    >
                      <ThumbsUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      aria-label={locale === "vi" ? "Không hữu ích" : "Not helpful"}
                      onClick={() => updateFeedback("down")}
                      className={`p-1.5 rounded-lg hover:bg-slate-800 transition-colors ${feedback === "down" ? "text-rose-400 bg-rose-500/10" : ""}`}
                      title="Not helpful"
                    >
                      <ThumbsDown className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>

              {/* Feedback reason chips when thumb down */}
              {!isUser && feedback === "down" && !message.isStreaming && (
                <div
                  role="group"
                  aria-label={locale === "vi" ? "Tại sao câu trả lời này chưa tốt?" : "Why was this answer unhelpful?"}
                  className="message-feedback-categories flex flex-wrap items-center gap-1.5 text-xs pt-1.5"
                >
                  <span className="font-semibold text-slate-400">{locale === "vi" ? "Lý do:" : "Reason:"}</span>
                  {FEEDBACK_CATEGORIES.map((category) => (
                    <button
                      key={category.value}
                      type="button"
                      onClick={() => updateFeedbackCategory(category.value)}
                      disabled={actionPending(feedbackAction)}
                      aria-pressed={feedbackCategory === category.value}
                      className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
                        feedbackCategory === category.value
                          ? "border-rose-500/50 bg-rose-500/15 text-rose-300"
                          : "border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800 hover:text-[var(--text-primary)]"
                      }`}
                    >
                      {locale === "vi" ? category.vi : category.en}
                    </button>
                  ))}
                </div>
              )}

              {/* Other feedback detail form */}
              {!isUser && feedback === "down" && feedbackCategory === "other" && isOtherFeedbackOpen && !message.isStreaming && (
                <div className="message-feedback-other rounded-xl border border-rose-500/25 bg-rose-500/5 p-3 mt-2">
                  <label className="block text-xs font-semibold text-[var(--text-muted)]" htmlFor={`feedback-other-${message.id}`}>
                    {locale === "vi" ? "Mô tả ngắn (bắt buộc)" : "Short explanation (required)"}
                  </label>
                  <textarea
                    id={`feedback-other-${message.id}`}
                    value={otherFeedbackDraft}
                    onChange={(event) => setOtherFeedbackDraft(event.target.value.slice(0, 2_000))}
                    maxLength={2_000}
                    rows={3}
                    autoFocus
                    placeholder={locale === "vi" ? "Điều gì cần cải thiện?" : "What should be improved?"}
                    className="mt-2 w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-rose-500"
                  />
                  {feedbackValidationError && (
                    <p className="mt-2 text-xs text-rose-400" role="alert">
                      {feedbackValidationError}
                    </p>
                  )}
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <span className="text-[11px] text-slate-400">{otherFeedbackDraft.length}/2000</span>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={cancelOtherFeedback}
                        className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-[var(--text-muted)] hover:bg-slate-800"
                      >
                        {locale === "vi" ? "Hủy" : "Cancel"}
                      </button>
                      <button
                        type="button"
                        onClick={submitOtherFeedback}
                        disabled={actionPending(feedbackAction)}
                        className="rounded-lg bg-rose-500/20 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/30"
                      >
                        {locale === "vi" ? "Gửi" : "Submit"}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          {!isUser && isNoteOpen && onSaveNote && !message.isStreaming && (
            <div className="message-note-editor rounded-xl border border-amber-500/25 bg-amber-500/5 p-3 mt-2">
              <label className="block text-xs font-semibold text-[var(--text-muted)]" htmlFor={`note-${message.id}`}>{locale === "vi" ? "Ghi chú riêng trên thiết bị" : "Private device note"}</label>
              <textarea id={`note-${message.id}`} value={noteDraft} onChange={(event) => setNoteDraft(event.target.value.slice(0, 10000))} maxLength={10000} rows={3} placeholder={locale === "vi" ? "Lưu ý, giả định hoặc việc cần kiểm tra…" : "Save an observation, assumption, or follow-up…"} className="mt-2 w-full resize-y rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-amber-500" />
              <div className="mt-2 flex items-center justify-between gap-2"><span className="text-[11px] text-[var(--text-muted)]">{noteDraft.length}/10000</span><button type="button" disabled={actionPending(noteAction)} onClick={() => { void onSaveNote(noteDraft.trim()); }} className="rounded-lg bg-amber-500/15 px-3 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-500/25 dark:text-amber-300">{locale === "vi" ? "Lưu ghi chú" : "Save note"}</button></div>
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

          {!isUser && (displayedExecution || pipelineStages?.length || message.isStreaming) && (
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

          {!isUser && onUseRelatedResearch && (
            <RelatedResearchPanel
              suggestions={relatedSuggestions}
              onSelect={(suggestion) => onUseRelatedResearch(suggestion.question[locale], suggestion.scope)}
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
