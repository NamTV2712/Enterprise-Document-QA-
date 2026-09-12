import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { useState } from "react";

import { ChatInput } from "./ChatInput";

function renderInput(onSendMessage = vi.fn()) {
  function Harness() {
    const [inputText, setInputText] = useState("");
    return (
      <ChatInput
        inputText={inputText}
        setInputText={setInputText}
        onSendMessage={onSendMessage}
        onStopGenerating={vi.fn()}
        isLoading={false}
        isStreaming={false}
        isBackendConnected={true}
        isPipelineReady={true}
      />
    );
  }

  return {
    onSendMessage,
    ...render(<Harness />),
  };
}

afterEach(() => cleanup());

describe("ChatInput", () => {
  test("does not submit Enter while an IME composition is active", () => {
    const { onSendMessage } = renderInput();
    const input = screen.getByRole("textbox", { name: "Research question" });

    fireEvent.change(input, { target: { value: "doanh thu Apple" } });
    fireEvent.compositionStart(input);
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onSendMessage).not.toHaveBeenCalled();

    fireEvent.compositionEnd(input);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSendMessage).toHaveBeenCalledWith("doanh thu Apple");
  });

  test("keeps the next draft editable and does not submit during a stream", () => {
    const onSendMessage = vi.fn();
    function StreamingHarness() {
      const [inputText, setInputText] = useState("");
      return (
        <ChatInput
          inputText={inputText}
          setInputText={setInputText}
          onSendMessage={onSendMessage}
          onStopGenerating={vi.fn()}
          isLoading={true}
          isStreaming={true}
          isBackendConnected={true}
          isPipelineReady={true}
        />
      );
    }

    render(<StreamingHarness />);
    const input = screen.getByRole("textbox", { name: "Research question" });
    fireEvent.change(input, { target: { value: "A follow-up draft while streaming" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(input).toHaveValue("A follow-up draft while streaming");
    expect(onSendMessage).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Stop generating response" })).toBeInTheDocument();
  });

  test("validates trimmed content and exposes the active scope", () => {
    const onSendMessage = vi.fn();
    render(
      <ChatInput
        inputText="     "
        setInputText={vi.fn()}
        onSendMessage={onSendMessage}
        onStopGenerating={vi.fn()}
        isLoading={false}
        isStreaming={false}
        isBackendConnected={true}
        isPipelineReady={true}
        scopeLabel="Apple Inc. (AAPL) · Risk Factors · Top 5"
      />,
    );

    expect(screen.getByText("Scope · Apple Inc. (AAPL) · Risk Factors · Top 5"))
      .toBeInTheDocument();
    expect(screen.getByText("Query must be at least 5 characters.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send question" })).toBeDisabled();
  });
});
