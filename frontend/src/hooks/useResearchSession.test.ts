import { act, renderHook } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import type { Message } from "../types";
import { useResearchSession } from "./useResearchSession";

describe("useResearchSession", () => {
  test("aborts the active request and preserves buffered partial text", () => {
    const updateMessages = vi.fn<(updater: (previous: Message[]) => Message[]) => void>();
    const { result } = renderHook(() => useResearchSession({ updateMessages }));

    let controller: AbortController;
    act(() => {
      controller = result.current.beginRequest();
      result.current.streamingBufferRef.current = { messageId: "assistant-1", text: "Partial" };
    });

    act(() => result.current.cancelActiveRequest());

    expect(controller!.signal.aborted).toBe(true);
    expect(result.current.isLoading).toBe(false);
    expect(updateMessages).toHaveBeenCalledTimes(1);
    expect(result.current.isCurrentRequest(controller!)).toBe(false);
  });

  test("Stop marks streaming messages stopped without changing completed messages", () => {
    const updateMessages = vi.fn<(updater: (previous: Message[]) => Message[]) => void>();
    const { result } = renderHook(() => useResearchSession({ updateMessages }));
    act(() => result.current.beginRequest());

    act(() => result.current.stopGenerating());

    const updater = updateMessages.mock.calls[0][0];
    const next = updater([
      { id: "streaming", sender: "assistant", text: "", isStreaming: true, status: "streaming" },
      { id: "done", sender: "assistant", text: "Done", isStreaming: false, status: "completed" },
    ]);
    expect(next[0]).toMatchObject({ text: "Generation stopped.", isStreaming: false, status: "stopped" });
    expect(next[1]).toMatchObject({ text: "Done", isStreaming: false, status: "completed" });
  });
});
