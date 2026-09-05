import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import App from "./App";

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

  test("initialization shares one abort signal across all requests", async () => {
    const { unmount } = render(<App />);

    await waitFor(() => expect(apiMocks.getSessionHistory).toHaveBeenCalled());
    const healthSignal = apiMocks.checkHealth.mock.calls[0][0];
    const tickerSignal = apiMocks.getSupportedTickers.mock.calls[0][0];
    const historySignal = apiMocks.getSessionHistory.mock.calls[0][1];

    expect(tickerSignal).toBe(healthSignal);
    expect(historySignal).toBe(healthSignal);
    expect(healthSignal.aborted).toBe(false);

    unmount();
    expect(healthSignal.aborted).toBe(true);
  });

  test("loads supported metadata and session history in parallel", async () => {
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

    await waitFor(() => expect(apiMocks.getSessionHistory).toHaveBeenCalled());
    expect(resolveSupportedTickers).toBeDefined();

    resolveSupportedTickers?.({ tickers: ["AAPL"], sections: ["business"] });
    expect(await screen.findByText("Pipeline: Ready")).toBeInTheDocument();
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

    expect(await screen.findByText(longAnswer)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Overview" }));
    expect(
      await screen.findByText("Ask questions. Verify every answer."),
    ).toBeInTheDocument();
    expect(screen.queryByText(longAnswer)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Return to conversation" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Conversation" }));
    expect(await screen.findByText(longAnswer)).toBeInTheDocument();
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
    expect(screen.getByText("In-memory conversations")).toBeInTheDocument();
    expect(screen.getByText("Retained messages")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Explain active sessions" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Explain total turns" }),
    ).not.toBeInTheDocument();
  });

  test("theme preference cycles through system, light, and dark", async () => {
    render(<App />);
    await screen.findByText("Pipeline: Ready");

    const themeButton = screen.getByRole("button", {
      name: "Theme system. Switch to light theme",
    });
    expect(document.documentElement).not.toHaveClass("dark");

    fireEvent.click(themeButton);
    expect(themeButton).toHaveAccessibleName("Theme light. Switch to dark theme");
    expect(document.documentElement).not.toHaveClass("dark");

    fireEvent.click(themeButton);
    expect(themeButton).toHaveAccessibleName("Theme dark. Switch to system theme");
    expect(document.documentElement).toHaveClass("dark");

    fireEvent.click(themeButton);
    expect(themeButton).toHaveAccessibleName("Theme system. Switch to light theme");
    expect(document.documentElement).not.toHaveClass("dark");
  });

  test("sidebar width can be adjusted with the resize separator", async () => {
    render(<App />);
    await screen.findByText("Pipeline: Ready");

    const resizeHandle = screen.getByRole("separator", {
      name: "Resize search controls",
    });
    expect(resizeHandle).toHaveAttribute("aria-valuenow", "320");

    fireEvent.keyDown(resizeHandle, { key: "ArrowRight" });

    expect(resizeHandle).toHaveAttribute("aria-valuenow", "336");
    expect(document.getElementById("control-sidebar")).toHaveStyle({
      width: "min(336px, calc(100vw - 2rem))",
    });
  });

  test("ticker picker shows and searches company names", async () => {
    render(<App />);
    await screen.findByText("Pipeline: Ready");

    fireEvent.click(screen.getByRole("button", { name: /All companies/i }));
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
    expect(screen.getByText("Microsoft Corporation")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Search company or ticker..."),
      { target: { value: "Microsoft" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Microsoft Corporation MSFT/i }),
    );
    expect(screen.getByText("Microsoft Corporation (MSFT)")).toBeInTheDocument();
  });

  test("section picker explains filing scope", async () => {
    render(<App />);
    await screen.findByText("Pipeline: Ready");

    fireEvent.click(screen.getByRole("button", { name: /All sections/i }));
    expect(screen.getByText("Risk Factors")).toBeInTheDocument();
    expect(screen.queryByText(/Item 1A/)).not.toBeInTheDocument();
    expect(
      screen.getByText("Material risks disclosed by company management."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Extracted rows optimized for exact numeric retrieval."),
    ).toBeInTheDocument();
  });

  test("suggested questions use readable company names", async () => {
    render(<App />);

    expect(
      await screen.findByText("Apple vs Microsoft — Risk Factors"),
    ).toBeInTheDocument();
    expect(screen.getByText("Amazon — MD&A Highlights")).toBeInTheDocument();
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
    await screen.findByText("Pipeline: Ready");
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
        setItemSpy.mock.calls.filter(([key]) => key === "sec_qa_messages"),
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
    await screen.findByText("Pipeline: Ready");

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
    await waitFor(() => expect(apiMocks.deleteSession).toHaveBeenCalledWith("reset-test"));
  });
});
