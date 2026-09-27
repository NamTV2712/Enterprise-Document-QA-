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

  useEffect(() => {
    const handleSetQuestion = (e: Event) => {
      const customEvent = e as CustomEvent<{ question: string }>;
      if (customEvent.detail?.question) {
        setInputText(customEvent.detail.question);
        textareaRef.current?.focus();
      }
    };
    window.addEventListener("sec-qa-set-question", handleSetQuestion);
    return () => window.removeEventListener("sec-qa-set-question", handleSetQuestion);
  }, [setInputText]);

  return (
    <div className="w-full max-w-full min-w-0 pt-2 pb-[calc(0.875rem+env(safe-area-inset-bottom))] md:pb-3 px-3 md:px-4 transition-colors">
      <div className="w-full space-y-2 min-w-0">
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
          className="chat-input-island relative flex flex-col p-2.5 px-3.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] shadow-md"
        >
          {/* Subtle loading shimmer bar along the top edge of the input area */}
          {isLoading && (
            <div className="composer-loading-track absolute top-0 left-0 right-0 h-[2.5px] overflow-hidden">
              <div className="composer-loading-track__bar h-full w-1/3 rounded-full animate-shimmer-slide" />
            </div>
          )}

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
                    : "Ask your documents... (Shift + Enter for new line)"
            }
            disabled={isTextareaDisabled}
            aria-describedby="chat-input-hint"
            className="w-full resize-none bg-transparent border-0 outline-none focus:ring-0 text-sm md:text-base text-[var(--text-primary)] py-1 min-h-[38px] font-sans"
          />

          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 mt-1 border-t border-[var(--border-subtle)]">
            <div className="flex items-center gap-1.5 flex-wrap min-w-0">
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

              {/* Retrieval stack is fixed by the backend (BM25 + dense + RRF +
                  rerank); it is stated as a static fact instead of a dead
                  dropdown, and the reference's Web search control is omitted
                  because this product has no web retrieval capability. */}
              <span
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--surface-muted)] border border-[var(--border-subtle)] text-[var(--text-secondary)]"
                title="BM25 keyword search, dense vector search, reciprocal rank fusion, and cross-encoder re-ranking"
              >
                <span>Hybrid Search</span>
              </span>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <label className="flex items-center gap-2 text-xs font-medium text-[var(--text-secondary)] cursor-pointer select-none">
                <span>{locale === "vi" ? "Nghiên cứu sâu" : "Deep Research"}</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={enableComparative}
                  aria-label={locale === "vi" ? "Bật hoặc tắt nghiên cứu sâu" : "Toggle Deep Research"}
                  disabled={isLoading}
                  onClick={() => !isLoading && onToggleComparative(!enableComparative)}
                  className={`relative inline-flex h-4 w-7 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    enableComparative ? "bg-blue-600" : "bg-[var(--border-strong)]"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                      enableComparative ? "translate-x-3" : "translate-x-0"
                    }`}
                  />
                </button>
              </label>

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
                  className="composer-stop-button min-h-8 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-3xs text-xs font-semibold"
                >
                  <Square className="w-3 h-3 fill-current" />
                  <span>{t("input.stop")}</span>
                </button>
              ) : (
                <button
                  type="submit"
                  id="send-message-btn"
                  title={t("input.ask")}
                  aria-label={t("input.sendAria")}
                  disabled={!isValidLength || isDisabled}
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-150 ${
                    isValidLength && !isDisabled
                      ? "bg-blue-600 hover:bg-blue-500 text-white shadow-sm cursor-pointer"
                      : "bg-[var(--surface-muted)] text-[var(--text-subtle)] opacity-40 cursor-not-allowed"
                  }`}
                >
                  <Send className="w-3.5 h-3.5" />
                  <span className="sr-only">{t("input.ask")}</span>
                </button>
              )}
            </div>
          </div>
        </form>

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
            <span className="sr-only text-[11px] flex items-center gap-1">
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
