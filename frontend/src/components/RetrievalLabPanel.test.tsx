import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { RetrievalLabPanel } from "./RetrievalLabPanel";
import { LocaleProvider } from "../lib/i18n";
import { inspectRetrieval } from "../lib/api";
import type { RetrievalPreset, Source } from "../types";

vi.mock("../lib/api", () => ({ inspectRetrieval: vi.fn() }));

const inspectMock = vi.mocked(inspectRetrieval);
type InspectResponse = Awaited<ReturnType<typeof inspectRetrieval>>;

function makeResponse(preset: RetrievalPreset = "hybrid_rerank", query = "Submitted retrieval query"): InspectResponse {
  return {
    query_interpretation: {
      original_question: query,
      retrieval_question: query,
      translation_method: "identity",
      detected_ticker: null,
      requested_periods: [],
      is_comparative: false,
    },
    trace: {
      preset,
      query,
      filters: { ticker: "AAPL", section: "financial_table" },
      top_k: 5,
      candidate_pool: 10,
      models: { embedding: "test-embed", reranker: "test-reranker", rrf_k: 60 },
      stages: [{ name: "bm25", elapsed_ms: 1.2 }],
      candidates: [{
        chunk_id: `${preset}-chunk`,
        document_id: "AAPL:0001",
        citation: `${preset} citation`,
        text_preview: `${preset} result`,
        bm25_score: 2,
        bm25_rank: 1,
        dense_score: 0.9,
        dense_rank: 1,
        rrf_score: 0.03,
        cross_encoder_score: 0.8,
        final_rank: 1,
        selected: true,
      }],
      selected_chunk_ids: [`${preset}-chunk`],
      elapsed_ms: 4.1,
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

function renderPanel(onUseQuestion = vi.fn(), onOpenSource?: (source: Source) => void, onSaveEvidence?: (source: Source) => void) {
  return render(
    <LocaleProvider>
      <RetrievalLabPanel
        tickers={["AAPL"]}
        sections={["financial_table"]}
        selectedTicker={null}
        selectedSection={null}
        isBackendConnected={true}
        onUseQuestion={onUseQuestion}
        onOpenSource={onOpenSource}
        onSaveEvidence={onSaveEvidence}
      />
    </LocaleProvider>,
  );
}

describe("RetrievalLabPanel", () => {
  beforeEach(() => {
    inspectMock.mockReset();
  });

  afterEach(() => cleanup());

  test("runs a provider-free trace and renders stage evidence", async () => {
    inspectMock.mockResolvedValue({
      query_interpretation: {
        original_question: "What was Apple's revenue?",
        retrieval_question: "What was Apple's revenue?",
        translation_method: "identity",
        detected_ticker: "AAPL",
        requested_periods: [],
        is_comparative: false,
      },
      trace: {
        preset: "hybrid_rerank",
        query: "What was Apple's revenue?",
        filters: { ticker: null, section: null },
        top_k: 5,
        candidate_pool: 10,
        models: { embedding: "test-embed", reranker: "test-reranker", rrf_k: 60 },
        stages: [{ name: "bm25", elapsed_ms: 1.2 }, { name: "dense", elapsed_ms: 2.3 }],
        candidates: [{
          chunk_id: "chunk-1",
          citation: "AAPL 10-K p. 1",
          text_preview: "Revenue was $100B.",
          bm25_score: 2,
          bm25_rank: 1,
          dense_score: 0.9,
          dense_rank: 1,
          rrf_score: 0.03,
          cross_encoder_score: 0.8,
          final_rank: 1,
          selected: true,
        }],
        selected_chunk_ids: ["chunk-1"],
        elapsed_ms: 4.1,
      },
    });

    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Run retrieval" }));

    await waitFor(() => expect(inspectMock).toHaveBeenCalledWith(
      expect.objectContaining({ preset: "hybrid_rerank" }),
      expect.any(AbortSignal),
    ));
    expect(await screen.findByText("AAPL 10-K p. 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Advanced mode" }));
    expect(screen.getByText("bm25")).toBeInTheDocument();
  });

  test("can hand the current question back to Research", () => {
    const onUseQuestion = vi.fn();
    renderPanel(onUseQuestion);
    fireEvent.click(screen.getByRole("button", { name: "Use in Research" }));
    expect(onUseQuestion).toHaveBeenCalledWith("What was Apple's total revenue in 2024?", { ticker: null, section: null });
  });

  test("keeps analyst results focused and exposes evidence actions", async () => {
    inspectMock.mockResolvedValue(makeResponse());
    const onOpenSource = vi.fn();
    const onSaveEvidence = vi.fn();
    renderPanel(vi.fn(), onOpenSource, onSaveEvidence);
    fireEvent.click(screen.getByRole("button", { name: "Run retrieval" }));
    expect(await screen.findByTestId("retrieval-analyst-summary")).toBeInTheDocument();
    expect(screen.getByText("Recommended strategy:")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open document" }));
    fireEvent.click(screen.getByRole("button", { name: "Save evidence" }));
    expect(onOpenSource).toHaveBeenCalledWith(expect.objectContaining({ document_id: "AAPL:0001" }));
    expect(onSaveEvidence).toHaveBeenCalledWith(expect.objectContaining({ chunk_id: "hybrid_rerank-chunk" }));
  });

  test("reveals stage diagnostics and bounded pool controls only in advanced mode", () => {
    renderPanel();
    expect(screen.queryByRole("slider", { name: "Candidate pool" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Advanced mode" }));
    expect(screen.getByRole("slider", { name: "Candidate pool" })).toBeInTheDocument();
  });

  test("uses the shared listbox control for retrieval presets", () => {
    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Preset" }));
    fireEvent.click(screen.getByRole("option", { name: "BM25" }));

    expect(screen.getByRole("button", { name: "Preset" })).toHaveTextContent("BM25");
  });

  test("clears inherited filters when the shared scope is reset", () => {
    const { rerender } = render(
      <LocaleProvider>
        <RetrievalLabPanel
          tickers={["AAPL"]}
          sections={["financial_table"]}
          selectedTicker="AAPL"
          selectedSection="financial_table"
          isBackendConnected={true}
          onUseQuestion={vi.fn()}
        />
      </LocaleProvider>,
    );
    expect(screen.getByRole("button", { name: "Company" })).toHaveTextContent("AAPL");
    expect(screen.getByRole("button", { name: "Section" })).toHaveTextContent("financial_table");

    rerender(
      <LocaleProvider>
        <RetrievalLabPanel
          tickers={["AAPL"]}
          sections={["financial_table"]}
          selectedTicker={null}
          selectedSection={null}
          isBackendConnected={true}
          onUseQuestion={vi.fn()}
        />
      </LocaleProvider>,
    );
    expect(screen.getByRole("button", { name: "Company" })).toHaveTextContent("All");
    expect(screen.getByRole("button", { name: "Section" })).toHaveTextContent("All");
  });

  test("invalidates a delayed inspection when the question changes", async () => {
    const pending = deferred<InspectResponse>();
    inspectMock.mockReturnValueOnce(pending.promise);
    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Run retrieval" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    const signal = inspectMock.mock.calls[0]?.[1] as AbortSignal;

    fireEvent.change(screen.getByRole("textbox", { name: "Retrieval question" }), { target: { value: "A changed retrieval question" } });
    expect(signal.aborted).toBe(true);
    await act(async () => pending.resolve(makeResponse("hybrid_rerank", "obsolete response")));

    expect(screen.queryByTestId("submitted-retrieval-configuration")).not.toBeInTheDocument();
    expect(screen.getByText("The configuration changed. Run retrieval again to refresh the trace and exports.")).toBeInTheDocument();
  });

  test("does not let a delayed comparison response repopulate an edited configuration", async () => {
    const primary = deferred<InspectResponse>();
    const comparison = deferred<InspectResponse>();
    inspectMock.mockReturnValueOnce(primary.promise).mockReturnValueOnce(comparison.promise);
    renderPanel();
    fireEvent.click(screen.getByRole("checkbox", { name: /Compare preset/i }));
    fireEvent.click(screen.getByRole("button", { name: "Run retrieval" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    await act(async () => primary.resolve(makeResponse("hybrid_rerank", "primary submitted query")));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(2));
    const signal = inspectMock.mock.calls[1]?.[1] as AbortSignal;

    fireEvent.click(screen.getByRole("button", { name: "Preset" }));
    fireEvent.click(screen.getByRole("option", { name: "BM25" }));
    expect(signal.aborted).toBe(true);
    await act(async () => comparison.resolve(makeResponse("bm25", "obsolete comparison query")));

    expect(screen.queryByTestId("submitted-retrieval-configuration")).not.toBeInTheDocument();
    expect(screen.getByText("The configuration changed. Run retrieval again to refresh the trace and exports.")).toBeInTheDocument();
  });

  test("aborts an active inspection when the Lab route unmounts", async () => {
    const pending = deferred<InspectResponse>();
    inspectMock.mockReturnValueOnce(pending.promise);
    const view = renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Run retrieval" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    const signal = inspectMock.mock.calls[0]?.[1] as AbortSignal;
    view.unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => pending.resolve(makeResponse("hybrid_rerank", "unmounted response")));
  });

  test("exports the submitted trace query and trace configuration", async () => {
    inspectMock.mockResolvedValue(makeResponse("hybrid_rerank", "Canonical trace query"));
    const originalCreateObjectUrl = (URL as typeof URL & { createObjectURL?: typeof URL.createObjectURL }).createObjectURL;
    const originalRevokeObjectUrl = (URL as typeof URL & { revokeObjectURL?: typeof URL.revokeObjectURL }).revokeObjectURL;
    const createObjectUrl = vi.fn((_: unknown) => "blob:retrieval-trace");
    const revokeObjectUrl = vi.fn();
    const originalBlob = globalThis.Blob;
    class TestBlob {
      constructor(public readonly parts: unknown[]) {}
    }
    Object.defineProperty(URL, "createObjectURL", { configurable: true, writable: true, value: createObjectUrl });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, writable: true, value: revokeObjectUrl });
    Object.defineProperty(globalThis, "Blob", { configurable: true, writable: true, value: TestBlob });
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Run retrieval" }));
    await screen.findByTestId("submitted-retrieval-configuration");
    fireEvent.click(screen.getByRole("button", { name: "JSON" }));

    const blob = createObjectUrl.mock.calls[0]?.[0] as unknown as TestBlob;
    const exported = JSON.parse(String(blob.parts[0])) as { query: string; configuration: { ticker: string; section: string; top_k: number; candidate_pool: number; preset: string } };
    expect(exported.query).toBe("Canonical trace query");
    expect(exported.configuration).toMatchObject({ ticker: "AAPL", section: "financial_table", top_k: 5, candidate_pool: 10, preset: "hybrid_rerank" });
    expect(anchorClick).toHaveBeenCalled();

    Object.defineProperty(URL, "createObjectURL", { configurable: true, writable: true, value: originalCreateObjectUrl });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, writable: true, value: originalRevokeObjectUrl });
    Object.defineProperty(globalThis, "Blob", { configurable: true, writable: true, value: originalBlob });
    anchorClick.mockRestore();
  });
});
