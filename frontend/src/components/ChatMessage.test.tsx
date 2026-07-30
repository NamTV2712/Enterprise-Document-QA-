import { render, screen, within } from "@testing-library/react";
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
});
