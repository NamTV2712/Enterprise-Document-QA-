import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
      tickers: ["AAPL"],
      sections: ["risk_factors"],
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

  test("session reload renders a full historical assistant answer", async () => {
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
  });

  test("stop generating aborts the stream and preserves partial text", async () => {
    let streamSignal: AbortSignal | undefined;
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

    const input = screen.getByRole("textbox");
    fireEvent.change(input, {
      target: { value: "What are Apple's main risk factors?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    await screen.findByText("Partial answer");
    fireEvent.click(
      screen.getByRole("button", { name: "Stop generating response" }),
    );

    expect(streamSignal?.aborted).toBe(true);
    expect(screen.getByText("Partial answer")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Stop generating response" }),
    ).not.toBeInTheDocument();
    expect(input).toBeEnabled();
  });
});
