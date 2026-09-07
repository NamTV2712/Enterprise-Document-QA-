/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useRef, useEffect, memo } from "react";
import { Send, AlertTriangle, Loader2, Square } from "lucide-react";
import { Tooltip } from "./Tooltip";
import { AnswerLanguage } from "../types";
import { useLocale } from "../lib/i18n";

interface ChatInputProps {
  inputText: string;
  setInputText: (text: string) => void;
  onSendMessage: (text: string) => void;
  onStopGenerating: () => void;
  isLoading: boolean;
  isStreaming: boolean;
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  showBanner?: boolean;
  scopeLabel?: string;
  /** Read-only saved conversations accept drafts but never send. */
  isReadOnly?: boolean;
  readOnlyMessage?: string;
  answerLanguage?: AnswerLanguage;
  onAnswerLanguageChange?: (language: AnswerLanguage) => void;
}

export const ConnectionBanner = memo(
  ({
    isBackendConnected,
    isPipelineReady,
  }: {
    isBackendConnected: boolean | null;
    isPipelineReady: boolean | null;
  }) => {
    const { t } = useLocale();
    if (isBackendConnected === null || isPipelineReady === null) {
      return (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/20 text-slate-600 dark:text-slate-400 text-xs font-semibold font-sans" role="status" aria-live="polite">
          <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" />
          <span>{t("connection.connecting")}</span>
        </div>
      );
    }

    if (isBackendConnected === false) {
      return (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-red-200 dark:border-red-950/40 bg-red-50 dark:bg-red-950/20 text-red-750 dark:text-red-400 text-xs font-semibold font-sans" role="alert">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>
            {t("connection.unavailable")}
          </span>
        </div>
      );
    }

    if (isPipelineReady === false) {
      return (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-amber-200 dark:border-amber-950/40 bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400 text-xs font-semibold font-sans" role="status" aria-live="polite">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>
            {t("connection.loading")}
          </span>
        </div>
      );
    }

    return null;
  },
);

ConnectionBanner.displayName = "ConnectionBanner";

const ChatInputBase: React.FC<ChatInputProps> = ({
  inputText,
  setInputText,
  onSendMessage,
  onStopGenerating,
  isLoading,
  isStreaming,
  isBackendConnected,
  isPipelineReady,
  showBanner = true,
  scopeLabel,
  isReadOnly = false,
  readOnlyMessage,
  answerLanguage = "en",
  onAnswerLanguageChange = () => {},
}) => {
  const { t } = useLocale();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const composingRef = useRef(false);

  const charCount = inputText.length;
  const trimmedLength = inputText.trim().length;
  const isTooShort = charCount > 0 && trimmedLength < 5;
  const isTooLong = charCount > 500;
  const isValidLength = trimmedLength >= 5 && charCount <= 500;

  const isDisabled =
    isLoading || !isBackendConnected || !isPipelineReady || isReadOnly;
  // Drafts stay editable in read-only conversations so the user can carry
  // them into a new conversation; only sending is locked.
  const isTextareaDisabled = isLoading || !isBackendConnected || !isPipelineReady;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isValidLength && !isDisabled) {
      onSendMessage(inputText.trim());
      setInputText("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends, Shift+Enter or Cmd/Ctrl+Enter for newline
    if (
      e.key === "Enter" &&
      !e.shiftKey &&
      !e.metaKey &&
      !e.ctrlKey &&
      !composingRef.current &&
      !e.nativeEvent.isComposing
    ) {
      e.preventDefault();
      if (isValidLength && !isDisabled) {
        onSendMessage(inputText.trim());
        setInputText("");
      }
    }
  };

  // Auto-resize textarea heights
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
    }
  }, [inputText]);

  return (
    <div className="w-full max-w-full min-w-0 pt-2 pb-[calc(0.875rem+env(safe-area-inset-bottom))] md:pb-3.5 px-4 transition-colors">
      <div className="w-full max-w-4xl mx-auto space-y-3 min-w-0">
        {scopeLabel && (
          <div className="composer-scope" aria-label={`${t("input.activeScope")}: ${scopeLabel}`}>
            <span className="composer-scope__label">{t("input.scope")}</span>
            <span className="composer-scope__value">{scopeLabel}</span>
          </div>
        )}
        {/* Banner Alert for Pipeline Not Ready or Disconnected */}
        {showBanner && (
          <ConnectionBanner
            isBackendConnected={isBackendConnected}
            isPipelineReady={isPipelineReady}
          />
        )}

        {/* Read-only notice for saved conversations without backend context */}
        {isReadOnly && readOnlyMessage && (
          <div
            className="flex items-center gap-2 p-2.5 rounded-lg border state-warning-border state-warning-surface state-warning-text text-xs font-semibold font-sans"
            role="status"
            aria-live="polite"
          >
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{readOnlyMessage}</span>
          </div>
        )}

        <form
          aria-label="Ask a research question"
          onSubmit={handleSubmit}
          className="chat-input-island relative flex items-end gap-2 p-2 pl-4 overflow-hidden"
        >
          {/* Subtle loading shimmer bar along the top edge of the input area */}
          {isLoading && (
            <div className="absolute top-0 left-0 right-0 h-[2.5px] bg-slate-100 dark:bg-slate-800/80 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-indigo-500 via-teal-400 to-indigo-500 w-1/3 rounded-full animate-shimmer-slide" />
            </div>
          )}

          <div className="flex min-w-0 flex-1 flex-col gap-1">
          <label className="sr-only" htmlFor="answer-language-select">{t("answerLanguage.label")}</label>
          <select
            id="answer-language-select"
            value={answerLanguage}
            onChange={(event) => onAnswerLanguageChange(event.target.value as AnswerLanguage)}
            disabled={isLoading || isReadOnly}
            className="self-start rounded-md border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-2 py-1 text-[11px] font-semibold text-[var(--text-muted)] outline-none focus:ring-2 focus:ring-[var(--primary)]"
            aria-label={t("answerLanguage.label")}
          >
            <option value="en">{t("answerLanguage.english")}</option>
            <option value="vi">{t("answerLanguage.vietnamese")}</option>
          </select>
          <textarea
            ref={textareaRef}
            id="chat-textarea"
            rows={1}
            aria-label={t("input.question")}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onCompositionStart={() => {
              composingRef.current = true;
            }}
            onCompositionEnd={() => {
              composingRef.current = false;
            }}
            onKeyDown={handleKeyDown}
            placeholder={
              isReadOnly
                ? t("input.readOnly")
                : isBackendConnected === null || isPipelineReady === null
                ? t("input.connecting")
                : !isBackendConnected
                  ? t("input.unavailable")
                  : !isPipelineReady
                    ? t("input.loading")
                    : t("input.placeholder")
            }
            disabled={isTextareaDisabled}
            aria-describedby="chat-input-hint"
            className="flex-1 resize-none bg-transparent border-0 outline-none focus:ring-0 text-sm md:text-base text-[var(--text-primary)] py-2.5 max-h-40 min-h-[40px] pr-12 scrollbar-none font-sans"
          />
          </div>

          <div className="flex items-center gap-2.5 pr-1.5 pb-1">
            {/* Character Counter */}
            {charCount > 0 && (
              <Tooltip content="Maximum 500 characters per question.">
                <span
                  className={`text-xs font-mono font-semibold select-none cursor-help px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 ${
                    isTooShort || isTooLong
                      ? "text-rose-500"
                      : "text-slate-500 dark:text-slate-400"
                  }`}
                >
                  {charCount}/500
                </span>
              </Tooltip>
            )}

            {isStreaming || isLoading ? (
              <button
                type="button"
                onClick={onStopGenerating}
                aria-label="Stop generating response"
                className="min-h-10 px-3.5 rounded-xl flex items-center justify-center gap-2 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-950/60 transition-colors cursor-pointer shadow-3xs"
              >
                <Square className="w-3 h-3 fill-current" />
                <span className="text-xs font-semibold">{t("input.stop")}</span>
              </button>
            ) : (
              <button
                type="submit"
                id="send-message-btn"
                title={t("input.ask")}
                aria-label={t("input.sendAria")}
                disabled={!isValidLength || isDisabled}
                className={`min-h-10 min-w-10 sm:min-w-[4.5rem] px-3 rounded-xl flex items-center justify-center gap-1.5 transition-all duration-200 ${
                  isValidLength && !isDisabled
                    ? "primary-action-button cursor-pointer"
                    : "bg-slate-100 dark:bg-slate-800/40 text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-200/50 dark:border-slate-800/50"
                }`}
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline text-xs font-semibold">{t("input.ask")}</span>
              </button>
            )}
          </div>
        </form>

        {/* Char count warnings & shortcuts hint */}
        <div id="chat-input-hint" className="flex justify-between items-center text-xs font-sans font-medium text-slate-400 dark:text-slate-500 px-1.5" role="status" aria-live="polite">
          {charCount > 0 ? (
            <>
              {isTooShort && (
                <span className="text-rose-500 font-bold">
                  {t("input.min")}
                </span>
              )}
              {isTooLong && (
                <span className="text-rose-500 font-bold">
                  {t("input.max")}
                </span>
              )}
              {!isTooShort && !isTooLong && (
                <span className="italic font-normal">
                  {t("input.hint")}
                </span>
              )}
            </>
          ) : (
            <span className="text-[11px] text-slate-400 dark:text-slate-500 flex items-center gap-1">
              <span>↵ {t("input.enter")}</span>
              <span>·</span>
              <span>{t("input.newline")}</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export const ChatInput = memo(ChatInputBase);
ChatInput.displayName = "ChatInput";
