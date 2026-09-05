/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useRef, useEffect, memo } from "react";
import { Send, AlertTriangle, Loader2, Square } from "lucide-react";
import { Tooltip } from "./Tooltip";

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
}

export const ConnectionBanner = memo(
  ({
    isBackendConnected,
    isPipelineReady,
  }: {
    isBackendConnected: boolean | null;
    isPipelineReady: boolean | null;
  }) => {
    if (isBackendConnected === null || isPipelineReady === null) {
      return (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/20 text-slate-600 dark:text-slate-400 text-xs font-semibold font-sans" role="status" aria-live="polite">
          <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" />
          <span>Connecting to the FastAPI backend...</span>
        </div>
      );
    }

    if (isBackendConnected === false) {
      return (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-red-200 dark:border-red-950/40 bg-red-50 dark:bg-red-950/20 text-red-750 dark:text-red-400 text-xs font-semibold font-sans" role="alert">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>
            The research service is unavailable. Check the connection and try
            again.
          </span>
        </div>
      );
    }

    if (isPipelineReady === false) {
      return (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-amber-200 dark:border-amber-950/40 bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400 text-xs font-semibold font-sans" role="status" aria-live="polite">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>
            System status: FastAPI pipeline state is re-loading index vectors.
            Document retrieval currently unavailable.
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
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const composingRef = useRef(false);

  const charCount = inputText.length;
  const trimmedLength = inputText.trim().length;
  const isTooShort = charCount > 0 && trimmedLength < 5;
  const isTooLong = charCount > 500;
  const isValidLength = trimmedLength >= 5 && charCount <= 500;

  const isDisabled = isLoading || !isBackendConnected || !isPipelineReady;

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
          <div className="composer-scope" aria-label={`Active search scope: ${scopeLabel}`}>
            <span className="composer-scope__label">Scope</span>
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

          <textarea
            ref={textareaRef}
            id="chat-textarea"
            rows={1}
            aria-label="Research question"
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
              isBackendConnected === null || isPipelineReady === null
                ? "Connecting to the FastAPI backend..."
                : !isBackendConnected
                  ? "Connect the FastAPI backend to start asking questions"
                  : !isPipelineReady
                    ? "Pipeline index loading..."
                    : "Ask a question about 10-K filings (e.g. Compare risk factors...)"
            }
            disabled={isDisabled}
            aria-describedby="chat-input-hint"
            className="flex-1 resize-none bg-transparent border-0 outline-none focus:ring-0 text-sm md:text-base text-[var(--text-primary)] py-2.5 max-h-40 min-h-[40px] pr-12 scrollbar-none font-sans"
          />

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
                <span className="text-xs font-semibold">Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                id="send-message-btn"
                title="Ask"
                aria-label="Send question"
                disabled={!isValidLength || isDisabled}
                className={`min-h-10 min-w-10 sm:min-w-[4.5rem] px-3 rounded-xl flex items-center justify-center gap-1.5 transition-all duration-200 ${
                  isValidLength && !isDisabled
                    ? "primary-action-button cursor-pointer"
                    : "bg-slate-100 dark:bg-slate-800/40 text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-200/50 dark:border-slate-800/50"
                }`}
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline text-xs font-semibold">Ask</span>
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
                  Query must be at least 5 characters.
                </span>
              )}
              {isTooLong && (
                <span className="text-rose-500 font-bold">
                  Query must not exceed 500 characters.
                </span>
              )}
              {!isTooShort && !isTooLong && (
                <span className="italic font-normal">
                  Press enter to ask, shift+enter for new line.
                </span>
              )}
            </>
          ) : (
            <span className="text-[11px] text-slate-400 dark:text-slate-500 flex items-center gap-1">
              <span>↵ Enter to ask</span>
              <span>·</span>
              <span>Shift + ↵ for new line</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export const ChatInput = memo(ChatInputBase);
ChatInput.displayName = "ChatInput";
