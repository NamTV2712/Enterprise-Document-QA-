import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { RetrievalLabPanel } from "./RetrievalLabPanel";
import { LocaleProvider } from "../lib/i18n";
import { inspectRetrieval } from "../lib/api";

vi.mock("../lib/api", () => ({ inspectRetrieval: vi.fn() }));

const inspectMock = vi.mocked(inspectRetrieval);

function renderPanel(onUseQuestion = vi.fn()) {
  return render(
    <LocaleProvider>
      <RetrievalLabPanel
        tickers={["AAPL"]}
        sections={["financial_table"]}
        selectedTicker={null}
        selectedSection={null}
        isBackendConnected={true}
        onUseQuestion={onUseQuestion}
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

    await waitFor(() => expect(inspectMock).toHaveBeenCalledWith(expect.objectContaining({ preset: "hybrid_rerank" })));
    expect(await screen.findByText("AAPL 10-K p. 1")).toBeInTheDocument();
    expect(screen.getByText("bm25")).toBeInTheDocument();
  });

  test("can hand the current question back to Research", () => {
    const onUseQuestion = vi.fn();
    renderPanel(onUseQuestion);
    fireEvent.click(screen.getByRole("button", { name: "Use in Research" }));
    expect(onUseQuestion).toHaveBeenCalledWith("What was Apple's total revenue in 2024?");
  });
});
