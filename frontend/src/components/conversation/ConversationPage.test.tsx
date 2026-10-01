import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ConversationPageHeader } from "./ConversationPageHeader";
import { ConversationPageShell } from "./ConversationPageShell";
import { FollowUpTiles } from "./FollowUpTiles";
import { ResearchInsightsRow } from "./ResearchInsightsRow";
import { LocaleProvider } from "../../lib/i18n";
import type { RelatedResearchSuggestion } from "../../lib/relatedResearch";
import type { Message } from "../../types";

function renderWithLocale(node: React.ReactNode) {
  return render(<LocaleProvider>{node}</LocaleProvider>);
}

const suggestion: RelatedResearchSuggestion = {
  id: "source-audit",
  label: { en: "Audit the cited sources", vi: "Kiểm tra nguồn đã dẫn" },
  description: { en: "Check the filing sections.", vi: "Kiểm tra các mục filing." },
  question: { en: "Which filing sections support this answer?", vi: "Mục filing nào hỗ trợ câu trả lời này?" },
  scope: { ticker: "AAPL", section: "risk_factors" },
};

function completedAnswer(overrides: Partial<Message> = {}): Message {
  return {
    id: "assistant-1",
    sender: "assistant",
    text: "Revenue increased [Source 1].",
    status: "completed",
    sources: [
      { citation: "AAPL 10-K [Source 1]", score: 0.891, chunk_id: "chunk-1", document_id: "doc-1" },
      { citation: "AAPL 10-K [Source 2]", score: 0.742, chunk_id: "chunk-2", document_id: "doc-1" },
    ],
    numChunks: 12,
    execution: { elapsed_ms: 2_800, stages: [] },
    ...overrides,
  } as Message;
}

describe("ConversationPageHeader", () => {
  afterEach(cleanup);

  test("presents the chat mode with its own label and new-conversation action", () => {
    renderWithLocale(
      <ConversationPageHeader mode="chat" onNewConversation={vi.fn()} onOpenHistory={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: "Chat" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /New Chat/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /History/ })).toBeTruthy();
  });

  test("presents the research mode and never renders a fake options control", () => {
    renderWithLocale(
      <ConversationPageHeader mode="research" onNewConversation={vi.fn()} onOpenHistory={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: "Research" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /New Research/ })).toBeTruthy();
    // The reference's overflow control has no implemented behavior, so it is
    // intentionally absent rather than shipped as a dead button.
    expect(screen.queryByLabelText(/Research options/)).toBeNull();
  });

  test("wires the header actions to their real handlers", () => {
    const onNewConversation = vi.fn();
    const onOpenHistory = vi.fn();
    renderWithLocale(
      <ConversationPageHeader mode="research" onNewConversation={onNewConversation} onOpenHistory={onOpenHistory} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /New Research/ }));
    fireEvent.click(screen.getByRole("button", { name: /History/ }));
    expect(onNewConversation).toHaveBeenCalledTimes(1);
    expect(onOpenHistory).toHaveBeenCalledTimes(1);
  });
});

describe("ResearchInsightsRow", () => {
  afterEach(cleanup);

  test("renders tiles only from values the answer actually carries", () => {
    renderWithLocale(<ResearchInsightsRow message={completedAnswer()} />);
    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText("Sources used")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
    expect(screen.getByText("Total chunks")).toBeTruthy();
    expect(screen.getByText("0.891")).toBeTruthy();
    // Retrieval scores are labelled as a retrieval score, never as confidence.
    expect(screen.getByText("Top retrieval score")).toBeTruthy();
    expect(screen.getByText("2.8s")).toBeTruthy();
  });

  test("omits tiles with no backing value instead of inventing numbers", () => {
    renderWithLocale(
      <ResearchInsightsRow
        message={completedAnswer({ numChunks: undefined, execution: undefined, sources: undefined })}
      />,
    );
    expect(screen.queryByText("Total chunks")).toBeNull();
    expect(screen.queryByText("Response time")).toBeNull();
    expect(screen.queryByText("Sources used")).toBeNull();
  });

  test("renders nothing without a completed answer", () => {
    const { container } = renderWithLocale(<ResearchInsightsRow message={null} />);
    expect(container.textContent).toBe("");
    const streaming = renderWithLocale(
      <ResearchInsightsRow message={completedAnswer({ isStreaming: true })} />,
    );
    expect(streaming.container.textContent).toBe("");
  });
});

describe("FollowUpTiles", () => {
  afterEach(cleanup);

  test("research mode renders tiles that fill the composer without submitting", () => {
    const onSelect = vi.fn();
    renderWithLocale(<FollowUpTiles mode="research" suggestions={[suggestion]} onSelect={onSelect} />);
    const tile = screen.getByRole("button", { name: /Audit the cited sources/ });
    expect(tile.className).toContain("conversation-followup-tile");
    fireEvent.click(tile);
    expect(onSelect).toHaveBeenCalledWith("Which filing sections support this answer?", {
      ticker: "AAPL",
      section: "risk_factors",
    });
  });

  test("chat mode keeps the compact chip strip", () => {
    renderWithLocale(<FollowUpTiles mode="chat" suggestions={[suggestion]} onSelect={vi.fn()} />);
    const chip = screen.getByRole("button", { name: /Audit the cited sources/ });
    expect(chip.className).toContain("followup-chip");
    expect(screen.getByText("Follow-up questions")).toBeTruthy();
  });

  test("renders nothing when no suggestion is available", () => {
    const { container } = renderWithLocale(
      <FollowUpTiles mode="research" suggestions={[]} onSelect={vi.fn()} />,
    );
    expect(container.textContent).toBe("");
  });
});

describe("ConversationPageShell", () => {
  afterEach(cleanup);

  test("composes header, thread, insights, follow-ups, and composer slots", () => {
    renderWithLocale(
      <ConversationPageShell
        mode="research"
        insightMessage={completedAnswer()}
        followUps={[suggestion]}
        onNewConversation={vi.fn()}
        onOpenHistory={vi.fn()}
        onSelectFollowUp={vi.fn()}
        scrollContainerRef={{ current: null }}
        messagesEndRef={{ current: null }}
        canShowFollowUps
        composer={<div data-testid="composer-slot" />}
      >
        <p>Thread content</p>
      </ConversationPageShell>,
    );
    expect(screen.getByRole("heading", { name: "Research" })).toBeTruthy();
    expect(screen.getByText("Thread content")).toBeTruthy();
    expect(screen.getByTestId("conversation-insights")).toBeTruthy();
    expect(screen.getByTestId("conversation-followups")).toBeTruthy();
    expect(screen.getByTestId("composer-slot")).toBeTruthy();
  });

  test("chat mode hides insight tiles while keeping the thread and composer", () => {
    renderWithLocale(
      <ConversationPageShell
        mode="chat"
        insightMessage={completedAnswer()}
        followUps={[]}
        onNewConversation={vi.fn()}
        onOpenHistory={vi.fn()}
        onSelectFollowUp={vi.fn()}
        scrollContainerRef={{ current: null }}
        messagesEndRef={{ current: null }}
        canShowFollowUps={false}
        composer={<div data-testid="composer-slot" />}
      >
        <p>Thread content</p>
      </ConversationPageShell>,
    );
    expect(screen.queryByTestId("conversation-insights")).toBeNull();
    expect(screen.queryByTestId("conversation-followups")).toBeNull();
    expect(screen.getByTestId("composer-slot")).toBeTruthy();
  });
});
