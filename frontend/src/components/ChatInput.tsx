/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useRef, useEffect, memo } from "react";
import { Send, AlertTriangle, Loader2, Square } from "lucide-react";
import { Tooltip } from "./Tooltip";
import { ScopeEditor } from "./ScopeEditor";
import { useLocale } from "../lib/i18n";

interface ChatInputProps {
  inputText: string;
  setInputText: (text: string) => void;
  onSendMessage: (text: string) => void;
  onStopGenerating: () => void;
  isLoading: boolean;
  isStreaming: boolean;
  isPreflightRunning?: boolean;
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  showBanner?: boolean;
  scopeLabel?: string;
  /** Read-only saved conversations accept drafts but never send. */
  isReadOnly?: boolean;
  readOnlyMessage?: string;
  tickers?: string[];
  sections?: string[];
  selectedTicker?: string | null;
  onSelectTicker?: (ticker: string | null) => void;
  selectedSection?: string | null;
  onSelectSection?: (section: string | null) => void;
  topK?: number;
  onChangeTopK?: (topK: number) => void;
  enableComparative?: boolean;
  onToggleComparative?: (enabled: boolean) => void;
  scopeOpen?: boolean;
  onScopeOpenChange?: (open: boolean) => void;
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
        <div className="connection-banner connection-banner--checking flex items-center gap-2 p-2.5 rounded-lg text-xs font-semibold font-sans" role="status" aria-live="polite">
          <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" />
          <span>{t("connection.connecting")}</span>
        </div>
      );
    }

    if (isBackendConnected === false) {
      return (
        <div className="connection-banner connection-banner--danger flex items-center gap-2 p-2.5 rounded-lg text-xs font-semibold font-sans" role="alert">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>
            {t("connection.unavailable")}
          </span>
        </div>
      );
    }

    if (isPipelineReady === false) {
      return (
        <div className="connection-banner connection-banner--warning flex items-center gap-2 p-2.5 rounded-lg text-xs font-semibold font-sans" role="status" aria-live="polite">
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
  isPreflightRunning = false,
  isBackendConnected,
  isPipelineReady,
  showBanner = true,
  scopeLabel,
  isReadOnly = false,
  readOnlyMessage,
  tickers = [],
  sections = [],
  selectedTicker = null,
  onSelectTicker = () => {},
  selectedSection = null,
  onSelectSection = () => {},
  topK = 5,
  onChangeTopK = () => {},
  enableComparative = false,
  onToggleComparative = () => {},
  scopeOpen,
  onScopeOpenChange,
}) => {
  const { t, locale } = useLocale();
  const vi = locale === "vi";
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const composingRef = useRef(false);

  const charCount = inputText.length;
  const trimmedLength = inputText.trim().length;
  const isTooShort = charCount > 0 && trimmedLength < 5;
  const isTooLong = charCount > 500;
  const isValidLength = trimmedLength >= 5 && charCount <= 500;

  const isDisabled =
    isLoading || isPreflightRunning || !isBackendConnected || !isPipelineReady || isReadOnly;
  // Connectivity and request state control sending, not drafting. Keep the
  // textarea editable so a next question can be recovered during a stream.
  const isTextareaDisabled = false;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isValidLength && !isDisabled) {
      onSendMessage(inputText.trim());
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
      }
    }
  };

  // Keep the composer stable after width, zoom, or font changes as well as
  // after text input. Once the cap is reached, preserve an explicit internal
  // scrollbar instead of clipping the draft.
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const resize = () => {
      textarea.style.height = "auto";
      const nextHeight = Math.min(textarea.scrollHeight, 160);
      textarea.style.height = `${nextHeight}px`;
      textarea.style.overflowY = textarea.scrollHeight > 160 ? "auto" : "hidden";
    };
    let frame = requestAnimationFrame(resize);
    // Observe the width-bearing parent, never the textarea whose height this
    // effect writes; doing so can cause ResizeObserver feedback on typing.
    const observer = typeof ResizeObserver === "undefined" || !textarea.parentElement
      ? null
      : new ResizeObserver(() => {
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(resize);
      });
    if (textarea.parentElement) observer?.observe(textarea.parentElement);
    return () => { cancelAnimationFrame(frame); observer?.disconnect(); };
  }, [inputText]);

  return (
    <div className="w-full max-w-full min-w-0 pt-2 pb-[calc(0.875rem+env(safe-area-inset-bottom))] md:pb-3.5 px-4 transition-colors">
      <div className="w-full max-w-4xl mx-auto space-y-3 min-w-0">
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
            <div className="composer-loading-track absolute top-0 left-0 right-0 h-[2.5px] overflow-hidden">
              <div className="composer-loading-track__bar h-full w-1/3 rounded-full animate-shimmer-slide" />
            </div>
          )}

          <div className="flex min-w-0 flex-1 flex-col gap-1">
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
            className="flex-1 resize-none bg-transparent border-0 outline-none focus:ring-0 text-sm md:text-base text-[var(--text-primary)] py-2.5 min-h-[40px] pr-2 font-sans"
          />
          </div>

          <div className="flex items-center gap-2.5 pr-1.5 pb-1">
            {/* Character Counter */}
            {charCount > 0 && (
              <Tooltip content="Maximum 500 characters per question.">
                <span
                  className={`composer-character-count text-xs font-mono font-semibold select-none cursor-help px-1.5 py-0.5 rounded ${
                    isTooShort || isTooLong
                      ? "composer-character-count--invalid"
                      : ""
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
                className="composer-stop-button min-h-10 px-3.5 rounded-xl flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-3xs"
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
                    : "composer-send-button--disabled cursor-not-allowed"
                }`}
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline text-xs font-semibold">{t("input.ask")}</span>
              </button>
            )}
          </div>
        </form>

        <ScopeEditor
          scopeLabel={scopeLabel}
          tickers={tickers}
          sections={sections}
          selectedTicker={selectedTicker}
          onSelectTicker={onSelectTicker}
          selectedSection={selectedSection}
          onSelectSection={onSelectSection}
          topK={topK}
          onChangeTopK={onChangeTopK}
          enableComparative={enableComparative}
          onToggleComparative={onToggleComparative}
          open={scopeOpen}
          onOpenChange={onScopeOpenChange}
          disabled={isLoading}
        />

        {/* Char count warnings & shortcuts hint */}
        <div id="chat-input-hint" className="composer-input-hint flex justify-between items-center text-xs font-sans font-medium px-1.5" role="status" aria-live="polite">
          {charCount > 0 ? (
            <>
              {isTooShort && (
                <span className="state-danger-text font-bold">
                  {t("input.min")}
                </span>
              )}
              {isTooLong && (
                <span className="state-danger-text font-bold">
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
            <span className="text-[11px] flex items-center gap-1">
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
