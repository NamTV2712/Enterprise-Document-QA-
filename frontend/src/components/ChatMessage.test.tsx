import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ChatMessage } from "./ChatMessage";

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
});
