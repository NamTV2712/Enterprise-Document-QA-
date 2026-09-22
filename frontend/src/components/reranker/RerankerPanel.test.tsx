import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { RerankerPanel } from "./RerankerPanel";
import { LocaleProvider } from "../../lib/i18n";
import { inspectRetrieval } from "../../lib/api";
import type { RetrievalInspectResponse, Source } from "../../types";

vi.mock("../../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/api")>();
  return { ...actual, inspectRetrieval: vi.fn() };
});

const inspectMock = vi.mocked(inspectRetrieval);

function candidate(overrides: Record<string, unknown> = {}) {
  return {
    chunk_id: "AAPL_fixture_revenue_0",
    document_id: "AAPL:fixture",
    citation: "AAPL 10-K, Financial Statements",
    text_preview: "Total revenue was reported in fiscal 2024.",
    ticker: "AAPL",
    section: "financial_statements",
    filing_date: "2025-10-31",
    bm25_score: 12.5,
    bm25_rank: 1,
    dense_score: 0.71,
    dense_rank: 2,
    lexical_rank: 1,
    rrf_score: 0.0326,
    fusion_rank: 4,
    cross_encoder_score: 8.25,
    final_rank: 1,
    selected: true,
    dropped_reason: null,
    ...overrides,
  };
}

function response(overrides: Partial<RetrievalInspectResponse["trace"]> = {}): RetrievalInspectResponse {
  return {
    query_interpretation: {
      original_question: "supply chain risk",
      retrieval_question: "supply chain risk",
      translation_method: "identity",
      detected_ticker: null,
      requested_periods: [],
      is_comparative: false,
    },
    trace: {
      trace_version: "retrieval-trace-v1",
      preset: "hybrid_rerank",
      query: "supply chain risk",
      filters: { ticker: null, section: null },
      top_k: 5,
      candidate_pool: 10,
      models: { embedding: "embed", reranker: "cross-encoder/ms-marco-MiniLM-L-6-v2", rrf_k: 60 },
      stages: [
        { name: "bm25", elapsed_ms: 3.25, status: "executed" },
        { name: "reranker", elapsed_ms: 48.75, status: "executed", skipped: false, reason: null },
      ],
      candidates: [
        candidate(),
        candidate({
          chunk_id: "ORCL_chunk",
          document_id: "ORCL:0001",
          citation: "ORCL 10-K, MD&A",
          text_preview: "Our cloud and software business.",
          ticker: "ORCL",
          section: "mdna",
          fusion_rank: 1,
          cross_encoder_score: -3.5,
          final_rank: 2,
        }),
        candidate({
          chunk_id: "HD_chunk",
          document_id: "HD:0002",
          citation: "HD 10-K, Risk Factors",
          text_preview: "Disruptions in our supply chain.",
          ticker: "HD",
          section: "risk_factors",
          fusion_rank: 3,
          cross_encoder_score: null,
          final_rank: null,
          selected: false,
          dropped_reason: "ranked_below_top_k",
        }),
      ],
      selected_chunk_ids: ["AAPL_fixture_revenue_0", "ORCL_chunk"],
      candidate_count: 3,
      selected_count: 2,
      elapsed_ms: 74.75,
      score_semantics: {
        applies_to_preset: "hybrid_rerank",
        note: "Score families are distinct and must not be compared with one another. None of them is a confidence, accuracy, or probability.",
        families: {
          rrf_score: { family: "fusion", scale: "sum_of_reciprocal_ranks", definition: "Reciprocal rank fusion." },
          cross_encoder_score: { family: "reranker", scale: "cross_encoder_logit", definition: "Cross-encoder relevance logit for the query/chunk pair." },
        },
      },
      production_parity: {
        structured_promotion: "not_executed",
        lexical_ladder_merge_into_final: "not_executed",
        reason: "Inspection exposes the ranking stages only.",
      },
      scope: { documents: 50, eligible_document_ids: ["AAPL:fixture"], truncated: false, reason: null },
      filter_values: { ticker: null, section: null, document_id: null, filing_date: null, year: null },
      ...overrides,
    },
  };
}

function renderPanel(props: Partial<React.ComponentProps<typeof RerankerPanel>> = {}) {
  return render(
    <LocaleProvider>
      <RerankerPanel
        tickers={["AAPL", "MSFT"]}
        sections={["mdna", "risk_factors"]}
        isBackendConnected={true}
        onUseQuestion={vi.fn()}
        {...props}
      />
    </LocaleProvider>,
  );
}

async function submit(text = "supply chain risk") {
  const input = screen.getByLabelText("Comparison Query");
  fireEvent.change(input, { target: { value: text } });
  fireEvent.submit(input.closest("form") as HTMLFormElement);
  await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
}

describe("RerankerPanel", () => {
  beforeEach(() => {
    inspectMock.mockResolvedValue(response());
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  test("one submitted comparison runs the inspection exactly once", async () => {
    renderPanel();
    const input = screen.getByLabelText("Comparison Query");
    fireEvent.change(input, { target: { value: "supply chain risk" } });
    expect(inspectMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Run reranker comparison" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    expect(inspectMock).toHaveBeenCalledWith(
      expect.objectContaining({ question: "supply chain risk", preset: "hybrid_rerank" }),
      expect.any(AbortSignal),
    );
  });

  test("compares fusion and cross-encoder ranks from the same trace and never reranks again", async () => {
    renderPanel({ onOpenDocument: vi.fn(), onOpenSource: vi.fn() });
    await submit();

    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);

    // Same pool: the fusion rank and the reranker score come from one response.
    const first = within(rows[0]!);
    expect(first.getByText("AAPL 10-K, Financial Statements")).toBeInTheDocument();
    expect(first.getByText("8.2500")).toBeInTheDocument();
    expect(first.getByText("4")).toBeInTheDocument(); // fusion rank before reranking

    // Selection and detail actions are views over that trace.
    fireEvent.click(rows[1]!);
    const refreshed = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    fireEvent.click(within(refreshed[0]!).getByRole("button", { name: "Open document workspace" }));
    expect(inspectMock).toHaveBeenCalledTimes(1);
  });

  test("states rank movement from the trace's own ranks", async () => {
    renderPanel();
    await submit();

    expect(screen.getByText("Up 3")).toBeInTheDocument(); // fusion 4 -> final 1
    expect(screen.getByText("Down 1")).toBeInTheDocument(); // fusion 1 -> final 2
    expect(screen.getByText("Not reported")).toBeInTheDocument(); // no final rank
    expect(screen.queryByText("No change")).not.toBeInTheDocument();
  });

  test("keeps a negative reranker logit negative and never invents a score", async () => {
    renderPanel();
    await submit();

    expect(screen.getByText("-3.5000")).toBeInTheDocument();
    // The candidate without a reranker score says so, and the header counts it.
    expect(screen.getByText("1 candidate has no reranker score in this trace.")).toBeInTheDocument();
    expect(screen.getAllByText("No score")).toHaveLength(1);
    const tableText = (screen.getByRole("table").textContent ?? "").toLowerCase();
    expect(tableText).not.toContain("%");
    expect(tableText).not.toContain("confidence");
    expect(tableText).not.toContain("probability");
    expect(tableText).not.toContain("0.0000");
  });

  test("reports a skipped reranker stage instead of a comparison", async () => {
    inspectMock.mockResolvedValue(response({
      preset: "hybrid",
      models: { embedding: "embed", reranker: null, rrf_k: 60 },
      stages: [
        { name: "bm25", elapsed_ms: 3.25, status: "executed" },
        { name: "reranker", elapsed_ms: null, status: "skipped", skipped: true, reason: "The selected preset ranks without the cross-encoder." },
      ],
      candidates: [candidate({ cross_encoder_score: null, final_rank: null })],
    }));
    renderPanel();
    await submit();

    const summary = within(screen.getByTestId("reranker-stage-summary"));
    expect(summary.getByText("Skipped")).toBeInTheDocument();
    expect(summary.getByText("The selected preset ranks without the cross-encoder.")).toBeInTheDocument();
    expect(summary.getByText("0")).toBeInTheDocument();
    expect(screen.getAllByText("No score").length).toBeGreaterThan(0);
    expect(screen.queryByText("8.2500")).not.toBeInTheDocument();
  });

  test("hands the reader canonical identity without running anything again", async () => {
    const onOpenDocument = vi.fn();
    const onOpenSource = vi.fn();
    const onSaveEvidence = vi.fn<(source: Source) => void>();
    renderPanel({ onOpenDocument, onOpenSource, onSaveEvidence });
    await submit();

    const row = screen.getByRole("row", { name: /ORCL 10-K, MD&A/ });
    fireEvent.click(within(row).getByRole("button", { name: "Open document workspace" }));
    expect(onOpenDocument).toHaveBeenCalledWith(expect.objectContaining({
      kind: "retrieval",
      documentId: "ORCL:0001",
      returnView: "retrieval",
      returnFocusId: "retrieval-document-workspace-ORCL_chunk",
      selectedSource: expect.objectContaining({ chunk_id: "ORCL_chunk" }),
    }));

    fireEvent.click(within(row).getByRole("button", { name: "Open indexed source" }));
    expect(onOpenSource).toHaveBeenCalledWith(expect.objectContaining({ chunk_id: "ORCL_chunk" }));

    fireEvent.click(screen.getByRole("button", { name: "Save as Evidence" }));
    expect(onSaveEvidence).toHaveBeenCalledWith(expect.objectContaining({ chunk_id: "AAPL_fixture_revenue_0" }));
    expect(inspectMock).toHaveBeenCalledTimes(1);
  });

  test("keeps the draft separate from the submitted comparison", async () => {
    renderPanel();
    await submit();
    fireEvent.change(screen.getByLabelText("Comparison Query"), { target: { value: "a different comparison entirely" } });
    expect(screen.getByText(/This configuration differs from the trace on screen/)).toBeInTheDocument();
    // The query context keeps the submitted query, unrelabelled by the draft.
    expect(within(screen.getByTestId("reranker-query-context")).getByText("supply chain risk")).toBeInTheDocument();
    expect(inspectMock).toHaveBeenCalledTimes(1);
  });
});
