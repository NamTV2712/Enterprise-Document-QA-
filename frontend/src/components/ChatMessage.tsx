/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from "react";
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
} from "lucide-react";
import { Message, RequestSnapshot } from "../types";
import { SourcesPanel } from "./SourcesPanel";
import { SubQueriesPanel } from "./SubQueriesPanel";

interface ChatMessageProps {
  message: Message;
  messageId?: string;
  isLatest?: boolean;
  onRetry?: (text: string, snapshot?: RequestSnapshot) => void;
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
              className="inline-flex items-center font-mono font-bold px-1.5 py-0.5 bg-brand-indigo/10 text-brand-indigo dark:bg-brand-indigo/20 dark:text-indigo-300 rounded text-xs select-all border border-brand-indigo/30 shadow-4xs mx-0.5"
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
                className="font-mono font-bold px-1 py-0.5 bg-slate-100 dark:bg-slate-800 text-[#26324A] dark:text-[#FCFBF8] rounded text-xs select-all border border-slate-200/50 dark:border-slate-700/50"
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
              className="font-mono font-semibold text-[#26324A] dark:text-[#FCFBF8] bg-[#FCFBF8] dark:bg-[#171D2B] border border-slate-200/40 dark:border-slate-800/60 px-1 py-0.5 rounded text-xs"
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
}) => {
  const isUser = message.sender === "user";
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [focusSourceIndex, setFocusSourceIndex] = useState<number | null>(null);

  const handleCopy = async () => {
    if (!message.text) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(message.text);
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
      aria-label={isUser ? "Your question" : "Research assistant response"}
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
                  : "bg-slate-100 text-slate-700 dark:bg-slate-850 dark:text-slate-300 border-slate-200 dark:border-slate-700"
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
                {isUser ? "Your question" : "SEC Filing Research Assistant"}
              </span>
              {!isUser && message.model_used && (
                <span className="text-xs font-mono font-medium bg-slate-50 dark:bg-[#171D2B] border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 px-1.5 py-0.5 rounded shadow-4xs">
                  {message.model_used}
                </span>
              )}
            </div>

            {!isUser && !message.isStreaming && message.text && (
              <button
                type="button"
                onClick={handleCopy}
                aria-label={copyState === "copied" ? "Copied answer" : "Copy answer"}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400 hover:text-brand-indigo dark:text-slate-500 dark:hover:text-indigo-300 transition-colors py-0.5 px-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer border border-transparent hover:border-slate-200 dark:hover:border-slate-700"
              >
                {copyState === "copied" ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-500" />
                    <span className="text-emerald-500 font-sans">Copied</span>
                  </>
                ) : copyState === "error" ? (
                  <>
                    <AlertCircle className="w-3 h-3 text-rose-500" />
                    <span className="text-rose-500 font-sans">Copy unavailable</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span className="font-sans">Copy</span>
                  </>
                )}
              </button>
            )}
          </div>

          {!isUser && message.rewritten_query && (
            <details className="group rounded-lg border border-brand-indigo/15 bg-brand-indigo/[0.035] text-xs">
              <summary className="flex min-h-10 cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 font-semibold text-slate-600 dark:text-slate-300 [&::-webkit-details-marker]:hidden">
                <span>Interpreted query</span>
                <ChevronDown className="h-4 w-4 text-brand-indigo transition-transform group-open:rotate-180" />
              </summary>
              <p className="ui-expand-enter border-t border-brand-indigo/10 px-3 py-2 font-mono text-xs italic leading-relaxed text-brand-indigo">
                {message.rewritten_query}
              </p>
            </details>
          )}

          {/* Keep the answer visually primary; execution details follow it. */}
          <div
            className={`ui-answer-enter prose prose-slate dark:prose-invert max-w-none text-[#26324A] dark:text-[#FCFBF8] text-sm md:text-base leading-relaxed font-sans ${
              isUser
                ? "rounded-2xl rounded-tr-md border border-brand-indigo/20 bg-brand-indigo/[0.06] dark:bg-brand-indigo/[0.10] px-4 py-3 shadow-3xs"
                : ""
            }`}
          >
                {isUser ? (
                  <p className="!m-0 whitespace-pre-wrap select-text font-sans text-slate-850 dark:text-slate-100">
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
                    {message.text ? (
                      message.isStreaming ? (
                          <p className="whitespace-pre-wrap text-sm md:text-base leading-relaxed text-[var(--text-primary)]">
                          {message.text}
                        </p>
                      ) : (
                        <ReactMarkdown
                          components={{
                          table: ({ ...props }) => (
                            <div className="overflow-x-auto my-4 border border-slate-200/90 dark:border-slate-800 rounded-xl shadow-4xs bg-white dark:bg-[#171D2B]/80">
                              <table
                                className="w-full text-xs text-left border-collapse"
                                {...props}
                              />
                            </div>
                          ),
                          thead: ({ ...props }) => (
                            <thead
                              className="bg-slate-50 dark:bg-[#171D2B] text-slate-700 dark:text-slate-200 border-b border-slate-200 dark:border-slate-800"
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
                              className="px-3 py-2.5 font-mono text-xs text-[#26324A] dark:text-[#FCFBF8] border-r last:border-r-0 border-slate-100 dark:border-slate-800/40"
                              {...props}
                            />
                          ),
                          p: ({ children }) => (
                            <p className="mb-3.5 last:mb-0 text-sm md:text-base leading-relaxed text-[var(--text-primary)]">
                              {renderFormattedChildren(children, (index) => setFocusSourceIndex(index), message.sources?.length || 0)}
                            </p>
                          ),
                          ul: ({ children }) => (
                            <ul className="list-disc pl-5 mb-3 text-sm space-y-1.5 text-slate-800 dark:text-slate-200">
                              {renderFormattedChildren(children, (index) => setFocusSourceIndex(index), message.sources?.length || 0)}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="list-decimal pl-5 mb-3 text-sm space-y-1.5 text-slate-800 dark:text-slate-200">
                              {renderFormattedChildren(children, (index) => setFocusSourceIndex(index), message.sources?.length || 0)}
                            </ol>
                          ),
                          li: ({ children }) => (
                            <li className="text-sm md:text-base leading-relaxed">
                              {renderFormattedChildren(children, (index) => setFocusSourceIndex(index), message.sources?.length || 0)}
                            </li>
                          ),
                          strong: ({ children, ...props }) => (
                            <strong
                              className="font-bold text-[#26324A] dark:text-[#FCFBF8] font-sans"
                              {...props}
                            >
                              {renderFormattedChildren(children, (index) => setFocusSourceIndex(index), message.sources?.length || 0)}
                            </strong>
                          ),
                          em: ({ children, ...props }) => (
                            <em className="italic" {...props}>
                              {renderFormattedChildren(children, (index) => setFocusSourceIndex(index), message.sources?.length || 0)}
                            </em>
                          ),
                          }}
                        >
                          {message.text}
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

          {!isUser && (message.subQueries || message.wasDecomposed) && (
            <SubQueriesPanel
              subQueries={message.subQueries || []}
              isLatest={isLatest}
            />
          )}

          {/* Streaming Blink Cursor */}
          {message.isStreaming && (
            <div className="inline-flex items-center ml-1">
              <span className="inline-block w-2 h-4 bg-brand-indigo animate-pulse rounded-xs" />
            </div>
          )}

          {/* Collapsible Sources */}
          {!isUser &&
            message.sources &&
            message.sources.length > 0 && (
            <SourcesPanel
              sources={message.sources}
              messageId={messageId}
              focusSourceIndex={focusSourceIndex}
              onFocusHandled={() => setFocusSourceIndex(null)}
            />
            )}
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
