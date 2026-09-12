import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { SearchWorkspace } from "./SearchWorkspace";
import { LocaleProvider } from "../lib/i18n";
import { inspectRetrieval } from "../lib/api";

vi.mock("../lib/api", () => ({ inspectRetrieval: vi.fn() }));

const inspectMock = vi.mocked(inspectRetrieval);
type InspectResponse = Awaited<ReturnType<typeof inspectRetrieval>>;

function makeResponse(chunkId: string, preview: string, citation = `AAPL filing ${chunkId}`): InspectResponse {
  return {
    query_interpretation: {
      original_question: "What are Apple's risks?",
      retrieval_question: "What are Apple's risks?",
      translation_method: "identity",
      detected_ticker: "AAPL",
      requested_periods: [],
      is_comparative: false,
    },
    trace: {
      preset: "hybrid_rerank",
      query: "What are Apple's risks?",
      filters: { ticker: "AAPL", section: null },
      top_k: 8,
      candidate_pool: 24,
      models: {},
      stages: [{ name: "retrieve", elapsed_ms: 4.5 }],
      candidates: [{ chunk_id: chunkId, citation, text_preview: preview, document_id: "AAPL:0001", ticker: "AAPL", section: "risk_factors", filing_date: "2024-11-01", final_rank: 1, cross_encoder_score: 0.89, selected: true }],
      selected_chunk_ids: [chunkId],
      elapsed_ms: 5.2,
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

describe("SearchWorkspace", () => {
  beforeEach(() => inspectMock.mockReset());
  afterEach(() => cleanup());

  test("runs provider-free evidence search and exposes the source result", async () => {
    inspectMock.mockResolvedValue(makeResponse("risk-1", "Macroeconomic risks.", "AAPL 10-K p. 12"));

    render(<LocaleProvider><SearchWorkspace selectedTicker="AAPL" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));

    await waitFor(() => expect(inspectMock).toHaveBeenCalledWith(expect.objectContaining({ ticker: "AAPL", preset: "hybrid_rerank" }), expect.any(AbortSignal)));
    expect(await screen.findByText("AAPL 10-K p. 12")).toBeInTheDocument();
    expect(screen.getByText("Macroeconomic risks.")).toBeInTheDocument();
  });

  test("opens a candidate's document workspace without changing the submitted query", async () => {
    const onOpenDocument = vi.fn();
    inspectMock.mockResolvedValue(makeResponse("risk-1", "Macroeconomic risks.", "AAPL 10-K p. 12"));
    render(<LocaleProvider><SearchWorkspace selectedTicker="AAPL" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} onOpenDocument={onOpenDocument} /></LocaleProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));
    await screen.findByText("AAPL 10-K p. 12");
    fireEvent.click(screen.getByRole("button", { name: "Open document workspace" }));
    expect(onOpenDocument).toHaveBeenCalledWith(expect.objectContaining({ kind: "search", documentId: "AAPL:0001", returnView: "search" }));
  });

  test("does not let a late success mutate results after the submitted scope changes", async () => {
    const pending = deferred<InspectResponse>();
    inspectMock.mockReturnValueOnce(pending.promise);
    const view = render(<LocaleProvider><SearchWorkspace selectedTicker="AAPL" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));

    view.rerender(<LocaleProvider><SearchWorkspace selectedTicker="MSFT" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    await waitFor(() => expect((inspectMock.mock.calls[0]?.[1] as AbortSignal | undefined)?.aborted).toBe(true));
    await act(async () => pending.resolve(makeResponse("late-old", "Late AAPL result must be ignored.")));

    await waitFor(() => expect(screen.queryByText("Late AAPL result must be ignored.")).not.toBeInTheDocument());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run search" })).toBeEnabled();
  });

  test("ignores a late error after the submitted scope changes", async () => {
    const pending = deferred<InspectResponse>();
    inspectMock.mockReturnValueOnce(pending.promise);
    const view = render(<LocaleProvider><SearchWorkspace selectedTicker="AAPL" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    view.rerender(<LocaleProvider><SearchWorkspace selectedTicker="MSFT" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    await act(async () => pending.reject(new Error("Late old-scope failure")));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });

  test("retains same-scope results with a refresh status while a new search is pending", async () => {
    const pending = deferred<InspectResponse>();
    inspectMock.mockResolvedValueOnce(makeResponse("risk-first", "Previous submitted result."));
    inspectMock.mockReturnValueOnce(pending.promise);
    render(<LocaleProvider><SearchWorkspace selectedTicker="AAPL" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));
    expect(await screen.findByText("Previous submitted result.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Run search" }));
    expect(await screen.findByText(/Showing the previous results until the new response arrives/)).toBeInTheDocument();
    expect(screen.getByText("Previous submitted result.")).toBeInTheDocument();
    await act(async () => pending.resolve(makeResponse("risk-second", "Latest submitted result.")));
    expect(await screen.findByText("Latest submitted result.")).toBeInTheDocument();
  });

  test("aborts the active request when SearchWorkspace unmounts", async () => {
    const pending = deferred<InspectResponse>();
    inspectMock.mockReturnValueOnce(pending.promise);
    const view = render(<LocaleProvider><SearchWorkspace selectedTicker="AAPL" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    const signal = inspectMock.mock.calls[0]?.[1] as AbortSignal;
    view.unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => pending.resolve(makeResponse("unmounted", "Ignored after unmount.")));
  });

  test("keeps retrieval submit-only and ignores a double submit while loading", async () => {
    const pending = deferred<InspectResponse>();
    inspectMock.mockReturnValueOnce(pending.promise);
    render(<LocaleProvider><SearchWorkspace selectedTicker="AAPL" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    const input = screen.getByRole("textbox", { name: "Search question" });
    fireEvent.change(input, { target: { value: "A different filing question" } });
    expect(inspectMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    await act(async () => pending.resolve(makeResponse("single-submit", "One submitted request.")));
  });
});
