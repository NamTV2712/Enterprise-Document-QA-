/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import ReactMarkdown from "react-markdown";
import { User, Cpu, AlertCircle, Loader2 } from "lucide-react";
import { Message } from "../types";
import { SourcesPanel } from "./SourcesPanel";
import { SubQueriesPanel } from "./SubQueriesPanel";

interface ChatMessageProps {
  message: Message;
  isLatest?: boolean;
}

// Inline content helper to parse and wrap tickers and numbers in monospace font
const formatMonospaceInline = (text: any): React.ReactNode => {
  if (typeof text !== "string") return text;

  // Match tickers of 3-5 uppercase letters (e.g. AAPL, MSFT, GOOGL) and scores, currencies, percentages, and numbers
  const regex =
    /(\b[A-Z]{3,5}\b|\b\d+\.\d+%?|\b\d+,\d+(?:,\d+)*(?:\.\d+)?%?|\b\d+%|\$\d+(?:\.\d+)?[BMK]?)/g;
  const tokens = text.split(regex);

  return (
    <>
      {tokens.map((token, idx) => {
        // Tickers
        if (/^[A-Z]{3,5}$/.test(token)) {
          const commonTickers = [
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
          if (commonTickers.includes(token)) {
            return (
              <span
                key={idx}
                className="font-mono font-bold px-1 py-0.5 bg-slate-100 dark:bg-slate-800 text-[#1B2430] dark:text-[#F7F7F5] rounded text-xs select-all border border-slate-200/50 dark:border-slate-700/50"
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
              className="font-mono font-semibold text-[#1B2430] dark:text-[#F7F7F5] bg-[#F7F7F5] dark:bg-[#12161C] border border-slate-200/40 dark:border-slate-800/60 px-1 py-0.5 rounded text-xs"
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
): React.ReactNode => {
  return React.Children.map(children, (child) => {
    if (typeof child === "string") {
      return formatMonospaceInline(child);
    }
    if (React.isValidElement(child)) {
      // If the child is an element, recursively map its children
      const element = child as React.ReactElement<any>;
      if (element.props && element.props.children) {
        return React.cloneElement(element, {
          ...element.props,
          children: renderFormattedChildren(element.props.children),
        });
      }
    }
    return child;
  });
};

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isLatest = false,
}) => {
  const isUser = message.sender === "user";

  // Manage sequential trace state for decomposed queries
  const [traceComplete, setTraceComplete] = useState<boolean>(() => {
    if (!isLatest) return true;
    if (message.wasDecomposed) return false;
    return !message.subQueries || message.subQueries.length === 0;
  });

  useEffect(() => {
    if (!isLatest) {
      setTraceComplete(true);
      return;
    }
    // If it was not decomposed, we are complete immediately
    if (
      !message.wasDecomposed &&
      (!message.subQueries || message.subQueries.length === 0)
    ) {
      setTraceComplete(true);
    }
  }, [isLatest, message.subQueries, message.wasDecomposed]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 140, damping: 20 }}
      className={`w-full transition-colors border-b border-slate-200/50 dark:border-slate-900/20 ${
        isUser
          ? "bg-[#F7F7F5] dark:bg-[#12161C]"
          : "bg-white dark:bg-[#1B2430]/30"
      }`}
      id={`message-${message.id}`}
    >
      <div className="max-w-4xl mx-auto w-full flex gap-4 p-5 md:p-6">
        <div className="flex-shrink-0">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-3xs ${
              isUser
                ? "bg-[#1B2430] text-[#F7F7F5] dark:bg-[#F7F7F5] dark:text-[#1B2430]"
                : message.error
                  ? "bg-rose-100 text-rose-600 dark:bg-rose-950/50 dark:text-rose-400"
                  : "bg-slate-100 text-slate-700 dark:bg-slate-850 dark:text-slate-300"
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

        <div className="flex-1 space-y-4 overflow-hidden">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[#1B2430] dark:text-[#F7F7F5] uppercase tracking-wider font-sans">
              {isUser ? "Equity Analyst" : "SEC RAG Agent Pipeline"}
            </span>
            {!isUser && message.model_used && (
              <span className="text-[9px] font-mono font-bold bg-[#F7F7F5] dark:bg-[#12161C] border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 px-1.5 py-0.5 rounded shadow-4xs">
                {message.model_used}
              </span>
            )}
            {message.rewritten_query && (
              <span className="text-[10px] font-mono text-brand-indigo bg-brand-indigo/5 border border-brand-indigo/10 px-1.5 py-0.5 rounded italic shadow-4xs">
                Query: {message.rewritten_query}
              </span>
            )}
          </div>

          {/* Collapsible Decomposed Sub-Queries Trace Log (SIGNATURE ELEMENT) */}
          {!isUser && (message.subQueries || message.wasDecomposed) && (
            <SubQueriesPanel
              subQueries={message.subQueries || []}
              isLatest={isLatest}
              onTraceComplete={() => setTraceComplete(true)}
            />
          )}

          {/* Message body (only shows after trace completes to provide authentic experience) */}
          <AnimatePresence mode="wait">
            {traceComplete && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                className="prose prose-slate dark:prose-invert max-w-none text-[#1B2430] dark:text-[#F7F7F5] text-sm md:text-base leading-relaxed font-sans"
              >
                {isUser ? (
                  <p className="whitespace-pre-wrap select-text font-sans text-slate-850 dark:text-slate-200">
                    {message.text}
                  </p>
                ) : message.error ? (
                  <div className="p-3 bg-rose-50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-950/50 rounded-lg text-rose-850 dark:text-rose-300 flex items-start gap-2 font-sans">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <p className="text-xs md:text-sm font-medium">
                      {message.text}
                    </p>
                  </div>
                ) : (
                  <div className="markdown-body select-text">
                    {message.text ? (
                      <ReactMarkdown
                        components={{
                          table: ({ ...props }) => (
                            <div className="overflow-x-auto my-4 border border-slate-200 dark:border-slate-800 rounded-xl shadow-4xs">
                              <table
                                className="w-full text-xs text-left border-collapse"
                                {...props}
                              />
                            </div>
                          ),
                          thead: ({ ...props }) => (
                            <thead
                              className="bg-[#F7F7F5] dark:bg-[#12161C] text-[#1B2430] dark:text-[#F7F7F5] border-b border-slate-200 dark:border-slate-800"
                              {...props}
                            />
                          ),
                          th: ({ ...props }) => (
                            <th
                              className="p-2.5 font-bold text-xs tracking-wider uppercase font-sans"
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
                              className="p-2.5 font-mono text-xs text-[#1B2430] dark:text-[#F7F7F5]"
                              {...props}
                            />
                          ),
                          p: ({ children }) => (
                            <p className="mb-3.5 last:mb-0 text-sm md:text-base leading-relaxed text-slate-800 dark:text-slate-200">
                              {renderFormattedChildren(children)}
                            </p>
                          ),
                          ul: ({ children }) => (
                            <ul className="list-disc pl-5 mb-3 text-sm space-y-1.5 text-slate-800 dark:text-slate-200">
                              {renderFormattedChildren(children)}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="list-decimal pl-5 mb-3 text-sm space-y-1.5 text-slate-800 dark:text-slate-200">
                              {renderFormattedChildren(children)}
                            </ol>
                          ),
                          li: ({ children }) => (
                            <li className="text-sm md:text-base leading-relaxed">
                              {renderFormattedChildren(children)}
                            </li>
                          ),
                          strong: ({ ...props }) => (
                            <strong
                              className="font-bold text-[#1B2430] dark:text-[#F7F7F5] font-sans"
                              {...props}
                            />
                          ),
                          em: ({ ...props }) => (
                            <em className="italic" {...props} />
                          ),
                        }}
                      >
                        {message.text}
                      </ReactMarkdown>
                    ) : (
                      <div className="flex items-center gap-2 text-slate-400 py-1 font-mono">
                        <Loader2 className="w-4 h-4 animate-spin text-brand-indigo" />
                        <span className="text-xs font-semibold uppercase tracking-wider">
                          RETRIEVING DISCLOSURES & COMPILING RESPONSE...
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Streaming Blink Cursor */}
          {message.isStreaming && (
            <div className="inline-flex items-center ml-1">
              <span className="inline-block w-2 h-4 bg-brand-indigo animate-pulse rounded-xs" />
            </div>
          )}

          {/* Collapsible Sources (only shows after trace completes) */}
          {traceComplete &&
            !isUser &&
            message.sources &&
            message.sources.length > 0 && (
              <SourcesPanel sources={message.sources} />
            )}
        </div>
      </div>
    </motion.div>
  );
};
