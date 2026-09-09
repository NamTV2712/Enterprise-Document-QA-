import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { SearchWorkspace } from "./SearchWorkspace";
import { LocaleProvider } from "../lib/i18n";
import { inspectRetrieval } from "../lib/api";

vi.mock("../lib/api", () => ({ inspectRetrieval: vi.fn() }));

const inspectMock = vi.mocked(inspectRetrieval);

describe("SearchWorkspace", () => {
  beforeEach(() => inspectMock.mockReset());
  afterEach(() => cleanup());

  test("runs provider-free evidence search and exposes the source result", async () => {
    inspectMock.mockResolvedValue({
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
        candidates: [{ chunk_id: "risk-1", citation: "AAPL 10-K p. 12", text_preview: "Macroeconomic risks.", final_rank: 1, cross_encoder_score: 0.89, selected: true }],
        selected_chunk_ids: ["risk-1"],
        elapsed_ms: 5.2,
      },
    });

    render(<LocaleProvider><SearchWorkspace selectedTicker="AAPL" selectedSection={null} isBackendConnected={true} onUseQuestion={vi.fn()} /></LocaleProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Run search" }));

    await waitFor(() => expect(inspectMock).toHaveBeenCalledWith(expect.objectContaining({ ticker: "AAPL", preset: "hybrid_rerank" })));
    expect(await screen.findByText("AAPL 10-K p. 12")).toBeInTheDocument();
    expect(screen.getByText("Macroeconomic risks.")).toBeInTheDocument();
  });
});
