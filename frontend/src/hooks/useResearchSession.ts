import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import type { Message } from "../types";

export interface StreamingBuffer {
  messageId: string;
  text: string;
}

interface UseResearchSessionOptions {
  updateMessages: (updater: (previous: Message[]) => Message[]) => void;
}

export interface ResearchSessionController {
  isLoading: boolean;
  streamingBufferRef: MutableRefObject<StreamingBuffer | null>;
  beginRequest: () => AbortController;
  isCurrentRequest: (controller: AbortController) => boolean;
  markRequestIdle: () => void;
  finishRequest: (controller: AbortController) => void;
  cancelActiveRequest: () => void;
  stopGenerating: () => void;
}

/**
 * Owns only the transport lifecycle of the active research request. Session
 * identity, conversation epochs, and persistence remain in the library hook.
 */
export function useResearchSession({ updateMessages }: UseResearchSessionOptions): ResearchSessionController {
  const [isLoading, setIsLoading] = useState(false);
  const requestAbortRef = useRef<AbortController | null>(null);
  const streamingBufferRef = useRef<StreamingBuffer | null>(null);

  const beginRequest = useCallback(() => {
    requestAbortRef.current?.abort();
    const controller = new AbortController();
    requestAbortRef.current = controller;
    setIsLoading(true);
    return controller;
  }, []);

  const isCurrentRequest = useCallback(
    (controller: AbortController) =>
      requestAbortRef.current === controller && !controller.signal.aborted,
    [],
  );

  const markRequestIdle = useCallback(() => {
    setIsLoading(false);
  }, []);

  const finishRequest = useCallback((controller: AbortController) => {
    if (requestAbortRef.current === controller) {
      requestAbortRef.current = null;
      setIsLoading(false);
    }
  }, []);

  const cancelActiveRequest = useCallback(() => {
    const buffer = streamingBufferRef.current;
    if (buffer?.text) {
      updateMessages((previous) =>
        previous.map((message) =>
          message.id === buffer.messageId && message.isStreaming
            ? { ...message, text: buffer.text }
            : message,
        ),
      );
    }
    streamingBufferRef.current = null;
    const controller = requestAbortRef.current;
    requestAbortRef.current = null;
    controller?.abort();
    setIsLoading(false);
  }, [updateMessages]);

  const stopGenerating = useCallback(() => {
    const controller = requestAbortRef.current;
    if (!controller) return;

    requestAbortRef.current = null;
    controller.abort();
    setIsLoading(false);
    updateMessages((previous) =>
      previous.map((message) =>
        message.isStreaming
          ? {
              ...message,
              text: message.text || "Generation stopped.",
              isStreaming: false,
              status: "stopped" as const,
            }
          : message,
      ),
    );
  }, [updateMessages]);

  useEffect(() => () => {
    requestAbortRef.current?.abort();
    requestAbortRef.current = null;
    streamingBufferRef.current = null;
  }, []);

  return {
    isLoading,
    streamingBufferRef,
    beginRequest,
    isCurrentRequest,
    markRequestIdle,
    finishRequest,
    cancelActiveRequest,
    stopGenerating,
  };
}
