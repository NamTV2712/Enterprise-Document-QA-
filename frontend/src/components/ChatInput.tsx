/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useRef, useEffect, memo } from "react";
import { motion } from "motion/react";
import { Send, AlertTriangle, Loader2 } from "lucide-react";
import { Tooltip } from "./Tooltip";

interface ChatInputProps {
  inputText: string;
  setInputText: (text: string) => void;
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  showBanner?: boolean;
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
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/20 text-slate-600 dark:text-slate-400 text-xs font-semibold font-mono">
          <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" />
          <span>Connecting to the FastAPI backend...</span>
        </div>
      );
    }

    if (isBackendConnected === false) {
      return (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-red-200 dark:border-red-950/40 bg-red-50 dark:bg-red-950/20 text-red-750 dark:text-red-400 text-xs font-semibold font-mono">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>
            Connection error: FastAPI service at [API] is unreachable. Verify
            your VITE_API_BASE_URL parameter.
          </span>
        </div>
      );
    }

    if (isPipelineReady === false) {
      return (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-amber-200 dark:border-amber-950/40 bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400 text-xs font-semibold font-mono">
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

export const ChatInput: React.FC<ChatInputProps> = ({
  inputText,
  setInputText,
  onSendMessage,
  isLoading,
  isBackendConnected,
  isPipelineReady,
  showBanner = true,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const charCount = inputText.length;
  const isTooShort = charCount > 0 && charCount < 5;
  const isTooLong = charCount > 500;
  const isValidLength = charCount >= 5 && charCount <= 500;

  const isDisabled = isLoading || !isBackendConnected || !isPipelineReady;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isValidLength && !isDisabled) {
      onSendMessage(inputText.trim());
      setInputText("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
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
    <div className="w-full bg-gradient-to-t from-[#F7F7F5] via-[#F7F7F5]/95 to-transparent dark:from-[#12161C] dark:via-[#12161C]/95 to-transparent pt-8 pb-4 md:pb-6 px-4 backdrop-blur-3xs">
      <div className="max-w-4xl mx-auto space-y-3">
        {/* Banner Alert for Pipeline Not Ready or Disconnected */}
        {showBanner && (
          <ConnectionBanner
            isBackendConnected={isBackendConnected}
            isPipelineReady={isPipelineReady}
          />
        )}

        <form
          onSubmit={handleSubmit}
          className="relative flex items-end gap-2 bg-white dark:bg-[#1B2430]/30 border border-slate-300 dark:border-slate-800 rounded-xl shadow-xs focus-within:ring-2 focus-within:ring-[#1B2430]/10 dark:focus-within:ring-[#F7F7F5]/10 focus-within:border-[#1B2430] dark:focus-within:border-[#F7F7F5] transition-all duration-200 p-2 pl-4 overflow-hidden"
        >
          {/* Subtle loading shimmer bar along the top edge of the input area */}
          {isLoading && (
            <div className="absolute top-0 left-0 right-0 h-[2.5px] bg-slate-100 dark:bg-slate-800 overflow-hidden">
              <div className="h-full bg-brand-indigo w-1/3 rounded-full animate-shimmer-slide" />
            </div>
          )}

          <textarea
            ref={textareaRef}
            id="chat-textarea"
            rows={1}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
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
            className="flex-1 resize-none bg-transparent border-0 outline-none focus:ring-0 text-sm md:text-base text-slate-850 dark:text-[#F7F7F5] py-2.5 max-h-40 min-h-[40px] pr-12 scrollbar-none font-sans"
          />

          <div className="flex items-center gap-3 pr-1.5 pb-1">
            {/* Character Counter */}
            {charCount > 0 && (
              <Tooltip content="Maximum 500 characters per question.">
                <span
                  className={`text-[10px] font-mono font-bold select-none cursor-help ${
                    isTooShort || isTooLong
                      ? "text-rose-500"
                      : "text-slate-400 dark:text-slate-500"
                  }`}
                >
                  {charCount}/500
                </span>
              </Tooltip>
            )}

            <motion.button
              whileHover={
                isValidLength && !isDisabled ? { scale: 1.02, y: -0.5 } : {}
              }
              whileTap={isValidLength && !isDisabled ? { scale: 0.98 } : {}}
              type="submit"
              id="send-message-btn"
              title="Ask"
              aria-label="Send question"
              disabled={!isValidLength || isDisabled}
              className={`p-2.5 rounded-lg flex items-center justify-center transition-all ${
                isValidLength && !isDisabled
                  ? "bg-[#1B2430] dark:bg-[#F7F7F5] text-[#F7F7F5] dark:text-[#1B2430] hover:opacity-95 cursor-pointer shadow-3xs"
                  : "bg-slate-100 dark:bg-slate-900/50 text-slate-400 dark:text-slate-650 cursor-not-allowed border border-slate-200/50 dark:border-slate-800/50"
              }`}
            >
              <Send className="w-4 h-4" />
            </motion.button>
          </div>
        </form>

        {/* Char count warnings */}
        {charCount > 0 && (
          <div className="flex justify-between text-[10px] font-mono font-bold text-slate-400 dark:text-slate-500 px-1 uppercase tracking-wider">
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
          </div>
        )}
      </div>
    </div>
  );
};
