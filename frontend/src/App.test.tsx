import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import App, { resolveDisplayedAnswerTarget, resolveEvidenceCommandTarget } from "./App";
import { LocaleProvider } from "./lib/i18n";
import type { EvidenceSelection, Message } from "./types";
import type { ConversationRecord } from "./lib/conversationStore";

const apiMocks = vi.hoisted(() => ({
  checkHealth: vi.fn(),
  getSupportedTickers: vi.fn(),
  queryDecomposed: vi.fn(),
  deleteSession: vi.fn(),
  getSessionHistory: vi.fn(),
  streamQuery: vi.fn(),
}));

vi.mock("./lib/api", () => ({
  ...apiMocks,
  getApiBaseUrl: () => "http://localhost:8000",
}));

describe("App request cancellation", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    apiMocks.checkHealth.mockResolvedValue({
      status: "ok",
      pipeline_ready: true,
      memory: { active_sessions: 0, total_turns: 0 },
    });
    apiMocks.getSupportedTickers.mockResolvedValue({
      tickers: ["AAPL", "MSFT"],
      sections: ["business", "risk_factors", "mdna", "financial_statements", "financial_table"],
    });
    apiMocks.getSessionHistory.mockResolvedValue({
      session_id: "test-session",
      turns: [],
    });
  });

  afterEach(() => {
    cleanup();
  });

  test("unmounting aborts initialization without reporting a connection error", async () => {
    let initializationSignal: AbortSignal | undefined;
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    apiMocks.checkHealth.mockImplementation((signal?: AbortSignal) => {
      initializationSignal = signal;
      return new Promise((_resolve, reject) => {
        signal?.addEventListener(
          "abort",
          () => reject(new DOMException("Aborted", "AbortError")),
          { once: true },
        );
      });
    });

    const { unmount } = render(<App />);
    await waitFor(() => expect(initializationSignal).toBeDefined());

    unmount();

    expect(initializationSignal?.aborted).toBe(true);
    await Promise.resolve();
    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  test("initialization shares one abort signal across health and metadata requests", async () => {
    const { unmount } = render(<App />);

    await waitFor(() => expect(apiMocks.getSupportedTickers).toHaveBeenCalled());
    const healthSignal = apiMocks.checkHealth.mock.calls[0][0];
    const tickerSignal = apiMocks.getSupportedTickers.mock.calls[0][0];

    expect(tickerSignal).toBe(healthSignal);
    expect(healthSignal.aborted).toBe(false);
    // Session history is consulted only after local hydration completes;
    // it is not part of the abort-shared initialization pair.
    expect(apiMocks.getSessionHistory.mock.calls.length).toBeLessThanOrEqual(1);

    unmount();
    expect(healthSignal.aborted).toBe(true);
  });

  test("loads supported metadata after readiness without blocking on history", async () => {
    let resolveSupportedTickers: ((value: {
      tickers: string[];
      sections: string[];
    }) => void) | undefined;
    apiMocks.getSupportedTickers.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSupportedTickers = resolve;
        }),
    );

    render(<App />);

    await waitFor(() => expect(apiMocks.checkHealth).toHaveBeenCalled());
    expect(resolveSupportedTickers).toBeDefined();

    resolveSupportedTickers?.({ tickers: ["AAPL"], sections: ["business"] });
    expect(await screen.findByText("Research ready")).toBeInTheDocument();
  });

  test("session history can switch between conversation and overview", async () => {
    const longAnswer = "Full historical answer ".repeat(30).trim();
    apiMocks.getSessionHistory.mockResolvedValue({
      session_id: "history-test",
      turns: [
        {
          user: "What are the main risks?",
          assistant: longAnswer,
          rewritten_query: null,
        },
      ],
    });

    render(<App />);

    expect(
      await screen.findByRole("article", { name: "Research assistant response" }),
    ).toHaveTextContent(longAnswer);

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    fireEvent.click(screen.getByRole("button", { name: "Research" }));
    expect(
      await screen.findByText("Ask questions. Verify every answer."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Research assistant response" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Return to conversation" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    fireEvent.click(screen.getByRole("button", { name: "Current conversation" }));
    expect(
      await screen.findByRole("article", { name: "Research assistant response" }),
    ).toHaveTextContent(longAnswer);
  });

  test("explains when a locally saved conversation has expired backend context", async () => {
    localStorage.setItem("sec_qa_session_id", "expired-session");
    localStorage.setItem("sec_qa_active_conversation_id", "conversation-expired-session");
    localStorage.setItem(
      "sec_qa_conversations_v2",
      JSON.stringify([
        {
          schemaVersion: 1,
          id: "conversation-expired-session",
          sessionId: "expired-session",
          title: "Saved risks",
          createdAt: 1,
          updatedAt: 2,
          draft: "",
          bookmarkedMessageIds: [],
          messages: [
            { id: "u-1", sender: "user", text: "What are the risks?" },
            { id: "a-1", sender: "assistant", text: "Saved answer with evidence." },
          ],
        },
      ]),
    );
    apiMocks.getSessionHistory.mockResolvedValue({
      session_id: "expired-session",
      turns: [],
      context: { status: "missing", retained_turns: 0, ttl_remaining_seconds: 0 },
    });

    render(<App />);

    expect(await screen.findByText("Saved answer with evidence.")).toBeInTheDocument();
    expect(
      (await screen.findAllByText(/backend session for this saved conversation has expired/i)).length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Start new conversation" })).toBeInTheDocument();
    // The composer must not offer sending follow-ups in read-only mode.
    expect(screen.getByRole("button", { name: "Send question" })).toBeDisabled();
  });

  test("keeps an expired saved conversation readable and does not resend it as context", async () => {
    localStorage.setItem("sec_qa_session_id", "expired-session-2");
    localStorage.setItem("sec_qa_active_conversation_id", "conversation-expired-session-2");
    localStorage.setItem(
      "sec_qa_conversations_v2",
      JSON.stringify([
        {
          schemaVersion: 1,
          id: "conversation-expired-session-2",
          sessionId: "expired-session-2",
          title: "Read-only copy",
          createdAt: 1,
          updatedAt: 2,
          draft: "",
          bookmarkedMessageIds: ["a-1"],
          messages: [
            { id: "u-1", sender: "user", text: "What are the risks?" },
            { id: "a-1", sender: "assistant", text: "Saved answer kept for reading." },
          ],
        },
      ]),
    );
    apiMocks.getSessionHistory.mockResolvedValue({
      session_id: "expired-session-2",
      turns: [],
      context: { status: "missing", retained_turns: 0, ttl_remaining_seconds: 0 },
    });

    render(<App />);

    expect(await screen.findByText("Saved answer kept for reading.")).toBeInTheDocument();
    // No retry affordance while the conversation is read-only.
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /Retry/i })).not.toBeInTheDocument();
    });
  });

  test("onboarding explains scope and how to verify results", async () => {
    render(<App />);

    expect(
      await screen.findByText("Ask questions. Verify every answer."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/API:\s*https?:\/\//i)).not.toBeInTheDocument();
    expect(screen.getByText("How to read the workspace")).toBeInTheDocument();
    expect(
      screen.getByText(/Rank scores order results; they are not confidence percentages/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Scope · All companies · All sections · Top 5/ })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Explain active sessions" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Explain total turns" }),
    ).not.toBeInTheDocument();
  });

  test("theme preference can be selected from the three-mode menu", async () => {
    render(<App />);
    await screen.findByText("Research ready");

    const themeButton = screen.getByRole("button", {
      name: "Theme System. Choose light, dark, or system theme",
    });
    expect(document.documentElement).not.toHaveClass("dark");

    fireEvent.click(themeButton);
    expect(screen.getByRole("menu", { name: "Theme preference" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("menuitemradio", { name: "Dark" }));
    expect(themeButton).toHaveAccessibleName("Theme Dark. Choose light, dark, or system theme");
    expect(document.documentElement).toHaveClass("dark");

    fireEvent.click(themeButton);
    fireEvent.click(screen.getByRole("menuitemradio", { name: "Light" }));
    expect(themeButton).toHaveAccessibleName("Theme Light. Choose light, dark, or system theme");
    expect(document.documentElement).not.toHaveClass("dark");

    fireEvent.click(themeButton);
    fireEvent.click(screen.getByRole("menuitemradio", { name: "System" }));
    expect(themeButton).toHaveAccessibleName("Theme System. Choose light, dark, or system theme");
  });

  test("narrow header keeps secondary controls in More and closes it before Help", async () => {
    render(<App />);
    await screen.findByText("Research ready");

    fireEvent.click(screen.getByRole("button", { name: "More workspace controls" }));
    const moreDialog = screen.getByRole("dialog", { name: "Workspace controls" });
    expect(moreDialog).toBeInTheDocument();
    expect(within(moreDialog).getByRole("button", { name: "Close workspace controls" })).toHaveFocus();
    expect(within(moreDialog).getByRole("group", { name: "Language" })).toBeInTheDocument();

    fireEvent.click(within(moreDialog).getByRole("button", { name: "Open help" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Workspace controls" })).not.toBeInTheDocument();
      expect(screen.getByRole("dialog", { name: "How to use this research workspace" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Close help" })).toHaveFocus();
  });

  test("sidebar is a stable navigation surface without a resizer or duplicate Library", async () => {
    render(<App />);
    await screen.findByText("Research ready");

    expect(screen.queryByRole("separator", { name: /Resize/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(screen.getAllByRole("button", { name: /Library/i })).toHaveLength(1);
  });

  test("research scope is controlled next to the composer", async () => {
    render(<App />);
    await screen.findByText("Research ready");

    fireEvent.click(screen.getByRole("button", { name: /Scope · All companies/ }));
    fireEvent.click(screen.getByRole("button", { name: "Company" }));
    fireEvent.click(screen.getByRole("option", { name: "Microsoft Corporation (MSFT)" }));
    expect(screen.getByRole("button", { name: /Scope · Microsoft Corporation \(MSFT\) · All sections · Top 5/ })).toBeInTheDocument();
  });

  test("research scope keeps selected filing section visible", async () => {
    render(<App />);
    await screen.findByText("Research ready");

    fireEvent.click(screen.getByRole("button", { name: /Scope · All companies/ }));
    fireEvent.click(screen.getByRole("button", { name: "10-K section" }));
    fireEvent.click(screen.getByRole("option", { name: "Risk Factors" }));
    expect(screen.getAllByText(/^Risk Factors$/).length).toBeGreaterThan(0);
  });

  test("applies a validated template question with its selected company scope without sending", async () => {
    render(<App />);
    await screen.findByText("Research ready");

    fireEvent.click(screen.getByRole("button", { name: /^Revenue fact/ }));
    const dialog = screen.getByRole("dialog", { name: "Revenue fact" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Company" }));
    fireEvent.click(screen.getByRole("option", { name: "Apple Inc. (AAPL)" }));
    fireEvent.change(within(dialog).getByLabelText("Fiscal year"), { target: { value: "2024" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Use in question" }));

    expect(apiMocks.streamQuery).not.toHaveBeenCalled();
    expect(document.getElementById("chat-textarea")).toHaveValue("What total revenue did AAPL report in 2024?");
    expect(screen.getByRole("button", { name: /Scope · Apple Inc\. \(AAPL\) · Financial Tables · Top 5/ })).toBeInTheDocument();
  });

  test("rejects a template apply after the current draft changes and preserves that draft", async () => {
    render(<App />);
    await screen.findByText("Research ready");

    fireEvent.click(screen.getByRole("button", { name: /^Revenue fact/ }));
    const dialog = screen.getByRole("dialog", { name: "Revenue fact" });
    fireEvent.change(document.getElementById("chat-textarea")!, { target: { value: "A newer draft" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Company" }));
    fireEvent.click(screen.getByRole("option", { name: "Apple Inc. (AAPL)" }));
    fireEvent.change(within(dialog).getByLabelText("Fiscal year"), { target: { value: "2024" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Use in question" }));

    expect(screen.getByText("Research context changed; reopen this template.")).toBeInTheDocument();
    expect(document.getElementById("chat-textarea")).toHaveValue("A newer draft");
    expect(screen.getByRole("button", { name: /Scope · All companies · All sections · Top 5/ })).toBeInTheDocument();
    expect(apiMocks.streamQuery).not.toHaveBeenCalled();
  });

  test("sidebar keeps retrieval and diagnostics grouped", async () => {
    render(<App />);
    await screen.findByText("Research ready");
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(screen.getByText("Retrieval")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retrieval Lab" })).toBeInTheDocument();
  });

  test("sends the shared interface language without changing the evidence request", async () => {
    apiMocks.streamQuery.mockImplementation(async (_payload, onEvent) => {
      onEvent({ type: "token", data: "Câu trả lời có nguồn [Source 1]." });
      onEvent({ type: "done", data: { answer_language: "vi" } });
    });

    render(<LocaleProvider><App /></LocaleProvider>);
    await screen.findByText("Research ready");
    fireEvent.click(screen.getByRole("button", { name: "VI" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "VI" })).toHaveAttribute("aria-pressed", "true"));
    fireEvent.change(document.getElementById("chat-textarea")!, {
      target: { value: "Doanh thu của Apple năm 2024 là bao nhiêu?" },
    });
    fireEvent.click(document.getElementById("send-message-btn")!);

    // The citation formatter wraps [Source 1] in a button, so assert the
    // answer's accessible article text rather than requiring one DOM text node.
    await waitFor(() =>
      expect(
        screen.getByRole("article", { name: /Research assistant response|Câu trả lời của trợ lý nghiên cứu/ }),
      ).toHaveTextContent("Câu trả lời có nguồn"),
    );
    expect(apiMocks.streamQuery.mock.calls[0][0]).toMatchObject({
      answer_language: "vi",
      question: "Doanh thu của Apple năm 2024 là bao nhiêu?",
    });
  });

  test("stop generating aborts the stream and preserves partial text", async () => {
    let streamSignal: AbortSignal | undefined;
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");
    apiMocks.streamQuery.mockImplementation(
      async (_payload, onEvent, _onError, signal?: AbortSignal) => {
        streamSignal = signal;
        onEvent({ type: "token", data: "Partial answer" });
        await new Promise<void>((resolve) => {
          if (signal?.aborted) {
            resolve();
            return;
          }
          signal?.addEventListener("abort", () => resolve(), { once: true });
        });
      },
    );

    render(<App />);
    await screen.findByText("Research ready");
    setItemSpy.mockClear();

    const input = screen.getByRole("textbox");
    fireEvent.change(input, {
      target: { value: "What are Apple's main risk factors?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    await screen.findByText("Partial answer");
    expect(
      setItemSpy.mock.calls.filter(([key]) => key === "sec_qa_messages"),
    ).toHaveLength(0);
    fireEvent.click(
      screen.getByRole("button", { name: "Stop generating response" }),
    );

    expect(streamSignal?.aborted).toBe(true);
    expect(screen.getByText("Partial answer")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Stop generating response" }),
    ).not.toBeInTheDocument();
    expect(input).toBeEnabled();
    await waitFor(() =>
      expect(
        setItemSpy.mock.calls.filter(([key]) => key === "sec_qa_library_v3"),
      ).toHaveLength(1),
    );
    setItemSpy.mockRestore();
  });

  test("comparative analysis can be stopped while the request is pending", async () => {
    let querySignal: AbortSignal | undefined;
    apiMocks.queryDecomposed.mockImplementation(
      async (_payload, signal?: AbortSignal) => {
        querySignal = signal;
        await new Promise<void>((resolve) => {
          if (signal?.aborted) {
            resolve();
            return;
          }
          signal?.addEventListener("abort", () => resolve(), { once: true });
        });
        return {
          answer: "",
          model_used: "test-model",
          was_decomposed: true,
          sub_queries: [],
          sources: [],
          num_total_chunks: 0,
        };
      },
    );

    render(<App />);
    await screen.findByText("Research ready");

    const input = screen.getByRole("textbox");
    fireEvent.change(input, {
      target: { value: "Compare Apple and Microsoft risk factors" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    const stopButton = await screen.findByRole("button", {
      name: "Stop generating response",
    });
    fireEvent.click(stopButton);

    expect(querySignal?.aborted).toBe(true);
    // Let the aborted request's catch/finally settle before asserting.
    await new Promise((resolve) => setTimeout(resolve, 200));
    expect(await screen.findByText("Generation stopped.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Stop generating response" }),
    ).not.toBeInTheDocument();
  });

  test("confirms before clearing an existing conversation", async () => {
    localStorage.setItem("sec_qa_session_id", "reset-test");
    apiMocks.deleteSession.mockResolvedValue(undefined);
    apiMocks.getSessionHistory.mockResolvedValue({
      session_id: "reset-test",
      turns: [{ user: "What was revenue?", assistant: "Full historical answer" }],
    });

    render(<App />);
    expect(await screen.findByText("Full historical answer")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Start a new conversation" }),
    );
    expect(
      screen.getByRole("dialog", { name: "Start a new conversation?" }),
    ).toBeInTheDocument();
    expect(apiMocks.deleteSession).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Keep conversation" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Start a new conversation" }),
    );
    const dialog = screen.getByRole("dialog", { name: "Start a new conversation?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Start new conversation" }));
    await waitFor(() => {
      const raw = localStorage.getItem("sec_qa_library_v3");
      expect(raw).toContain("Full historical answer");
    });
    expect(apiMocks.deleteSession).not.toHaveBeenCalled();
  });
});

describe("displayed answer command identity", () => {
  const messages: Message[] = [
    {
      id: "answer-older",
      sender: "assistant",
      text: "Older original answer.",
      sources: [{ citation: "Older source", chunk_id: "older-chunk", text_preview: "Older excerpt" }],
    },
    {
      id: "answer-newer",
      sender: "assistant",
      text: "Newer answer.",
      sources: [{ citation: "Newer source", chunk_id: "newer-chunk", text_preview: "Newer excerpt" }],
    },
  ];
  const record = {
    variants: [{
      id: "older-variant",
      originMessageId: "answer-older",
      text: "Older selected variant.",
      sources: [{ citation: "Variant source", chunk_id: "variant-chunk", text_preview: "Variant excerpt" }],
      answerLanguage: "en" as const,
      status: "completed" as const,
      createdAt: 1,
      updatedAt: 1,
  }],
  } as unknown as ConversationRecord;

  test("resolves copy and source commands to the focused older variant", () => {
    const context = { conversationId: "conversation-1", messageId: "answer-older", variantId: "older-variant" };
    const answer = resolveDisplayedAnswerTarget(context, messages, record, "conversation-1");
    expect(answer?.text).toBe("Older selected variant.");
    expect(answer?.sources[0].chunk_id).toBe("variant-chunk");

    const target = resolveEvidenceCommandTarget(context, null, messages, record, "conversation-1");
    expect(target?.source.chunk_id).toBe("variant-chunk");
    expect(target?.selection).toEqual(expect.objectContaining({ messageId: "answer-older", variantId: "older-variant" }));
  });

  test("fails closed when a focused variant disappears instead of falling back to newest", () => {
    const context = { conversationId: "conversation-1", messageId: "answer-older", variantId: "deleted-variant" };
    expect(resolveDisplayedAnswerTarget(context, messages, record, "conversation-1")).toBeNull();
    expect(resolveEvidenceCommandTarget(context, null, messages, record, "conversation-1")).toBeNull();

    const staleSelection: EvidenceSelection = {
      conversationId: "conversation-1",
      messageId: "answer-older",
      variantId: "deleted-variant",
      citationIndex: 0,
      sourceKey: "chunk:variant-chunk",
    };
    expect(resolveEvidenceCommandTarget(context, staleSelection, messages, record, "conversation-1")).toBeNull();
  });
});
