import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ChatMessage } from "./ChatMessage";

afterEach(cleanup);

describe("ChatMessage", () => {
  test("visually separates a user question from a grounded response", () => {
    const { rerender } = render(
      <ChatMessage
        message={{ id: "user-1", sender: "user", text: "What was revenue?" }}
      />,
    );

    const question = screen.getByRole("article", { name: "Your question" });
    expect(within(question).getByText("What was revenue?")).toBeInTheDocument();
    expect(question.querySelector(".rounded-tr-md")).toBeInTheDocument();

    rerender(
      <ChatMessage
        message={{
          id: "assistant-1",
          sender: "assistant",
          text: "Revenue was $391,035 million.",
          model_used: "llama-3.3-70b-versatile",
          rewritten_query: "Apple fiscal 2024 revenue",
        }}
      />,
    );

    const response = screen.getByRole("article", {
      name: "Research assistant response",
    });
    expect(
      within(response).getByText("SEC Filing Research Assistant"),
    ).toBeInTheDocument();
    expect(within(response).getByText("Interpreted query")).toBeInTheDocument();
    expect(within(response).getByText("Apple fiscal 2024 revenue")).toBeInTheDocument();
  });

  test("citation buttons open and focus the matching source excerpt", async () => {
    render(
      <ChatMessage
        messageId="assistant-42"
        message={{
          id: "assistant-42",
          sender: "assistant",
          text: "Revenue was reported in the filing [Source 1]. [Source 2].",
          sources: [
            {
              citation: "AAPL 10-K (filed 2025-10-31), Section: Financial Table",
              score: 1,
              text_preview: "Total net sales | 416,161",
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Open source 1" }));

    await waitFor(() => {
      expect(screen.getByText("Total net sales | 416,161")).toBeInTheDocument();
      expect(document.activeElement?.id).toBe("assistant-42-source-0");
    });
    expect(screen.getByText("[Source 2]")).toHaveClass("citation-button--unavailable");
  });

  test("reports a citation with its message-scoped source identity", () => {
    const onInspectSource = vi.fn();
    render(
      <ChatMessage
        messageId="assistant-older"
        onInspectSource={onInspectSource}
        message={{
          id: "assistant-older",
          sender: "assistant",
          text: "The earlier answer cites [Source 2].",
          sources: [
            { citation: "AAPL source", score: 0.8, text_preview: "First" },
            { citation: "MSFT source", score: 0.7, text_preview: "Second" },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Open source 2" }));
    expect(onInspectSource).toHaveBeenCalledWith(expect.objectContaining({
      messageId: "assistant-older",
      citationIndex: 1,
      sourceKey: expect.stringContaining("MSFT%20source"),
    }));
  });

  test("keeps variant citation identity separate from the original answer", () => {
    const onInspectSource = vi.fn();
    render(
      <ChatMessage
        messageId="assistant-variant"
        onInspectSource={onInspectSource}
        variants={[{
          id: "variant-1",
          originMessageId: "assistant-variant",
          text: "Variant answer cites [Source 1].",
          sources: [{ citation: "MSFT source", chunk_id: "msft-chunk-1", score: 0.4, score_kind: "retrieval", text_preview: "Variant excerpt" }],
          answerLanguage: "en",
          status: "completed",
          createdAt: 1,
          updatedAt: 1,
        }]}
        message={{
          id: "assistant-variant",
          sender: "assistant",
          text: "Original answer cites [Source 1].",
          sources: [{ citation: "AAPL source", chunk_id: "apple-chunk-1", score: 0.8, score_kind: "retrieval", text_preview: "Original excerpt" }],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Variant 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Open source 1" }));
    expect(onInspectSource).toHaveBeenCalledWith({
      messageId: "assistant-variant",
      variantId: "variant-1",
      citationIndex: 0,
      chunkId: "msft-chunk-1",
      sourceKey: "chunk:msft-chunk-1",
    });
  });

  test("shows only backend-provided execution stages", () => {
    render(
      <ChatMessage
        message={{
          id: "assistant-trace",
          sender: "assistant",
          text: "Grounded answer.",
          execution: {
            elapsed_ms: 842.4,
            stages: [
              { name: "embedding", elapsed_ms: 42.1, status: "completed" },
              { name: "cache_lookup", elapsed_ms: 1.2, status: "miss" },
            ],
          },
        }}
      />,
    );

    fireEvent.click(screen.getByText("Execution stages"));
    expect(screen.getByText("embedding")).toBeInTheDocument();
    expect(screen.getByText("cache lookup · miss")).toBeInTheDocument();
    expect(screen.getByText("42 ms")).toBeInTheDocument();
  });

  test("keeps a verified visual metric linked to its exact source", () => {
    const onInspectSource = vi.fn();
    render(
      <ChatMessage
        messageId="assistant-metric"
        onInspectSource={onInspectSource}
        message={{
          id: "assistant-metric",
          sender: "assistant",
          text: "Revenue was reported.",
          visualAnswer: {
            kind: "metric",
            metric: "net_sales",
            label: "Apple total net sales",
            value: "416161",
            display_value: "$416,161 million",
            unit: "USD million",
            period: "2025",
            source_index: 1,
            source_chunk_id: "AAPL_table_1",
            citation: "Apple 10-K, Financial Table",
            evidence_quote: "Total net sales | 416,161",
          },
        }}
      />,
    );

    expect(screen.getByText("$416,161 million")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open evidence" }));
    expect(onInspectSource).toHaveBeenCalledWith({
      messageId: "assistant-metric",
      citationIndex: 1,
      chunkId: "AAPL_table_1",
      sourceKey: "chunk:AAPL_table_1",
    });
  });

  test("saves a private note without changing the answer text", () => {
    const onSaveNote = vi.fn();
    render(
      <ChatMessage
        message={{ id: "assistant-note", sender: "assistant", text: "Revenue was reported." }}
        onSaveNote={onSaveNote}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Add note to answer" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Private device note" }), {
      target: { value: "Verify the fiscal-year label." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save note" }));

    expect(onSaveNote).toHaveBeenCalledWith("Verify the fiscal-year label.");
    expect(screen.getByText("Revenue was reported.")).toBeInTheDocument();
  });

  test("renders the request scope snapshot on a user question", () => {
    render(
      <ChatMessage
        message={{
          id: "user-scope",
          sender: "user",
          text: "What are the main risks?",
          requestSnapshot: {
            ticker: "AAPL",
            section: "risk_factors",
            topK: 5,
            enableComparative: false,
            answerLanguage: "en",
          },
        }}
      />,
    );

    expect(screen.getByLabelText("Question scope: Apple Inc. (AAPL) · Risk Factors · Top 5")).toBeInTheDocument();
  });

  test("persists a negative feedback category", () => {
    const onFeedback = vi.fn();
    render(
      <ChatMessage
        message={{ id: "assistant-feedback", sender: "assistant", text: "Revenue was reported." }}
        onFeedback={onFeedback}
      />,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Unhelpful answer" }).at(-1)!);
    expect(screen.getByRole("group", { name: "Why was this answer unhelpful?" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Citation issue" }));

    expect(onFeedback).toHaveBeenLastCalledWith(expect.objectContaining({
      rating: "down",
      category: "citation_issue",
    }));
  });
});
