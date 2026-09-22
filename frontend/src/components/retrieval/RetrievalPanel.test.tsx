import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { RetrievalPanel } from "./RetrievalPanel";
import { LocaleProvider } from "../../lib/i18n";
import { getDocumentFacets, getDocuments, inspectRetrieval } from "../../lib/api";
import type { RetrievalInspectResponse, RetrievalPreset, Source } from "../../types";

vi.mock("../../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/api")>();
  return {
    ...actual,
    inspectRetrieval: vi.fn(),
    getDocumentFacets: vi.fn(),
    getDocuments: vi.fn(),
  };
});

const inspectMock = vi.mocked(inspectRetrieval);
const facetsMock = vi.mocked(getDocumentFacets);
const documentsMock = vi.mocked(getDocuments);

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
    fusion_rank: 2,
    cross_encoder_score: -3.5,
    final_rank: 1,
    selected: true,
    dropped_reason: null,
    ...overrides,
  };
}

function response(overrides: Partial<RetrievalInspectResponse["trace"]> = {}): RetrievalInspectResponse {
  return {
    query_interpretation: {
      original_question: "What was Apple's total revenue in 2024?",
      retrieval_question: "What was Apple's total revenue in 2024?",
      translation_method: "identity",
      detected_ticker: null,
      requested_periods: [],
      is_comparative: false,
    },
    trace: {
      trace_version: "retrieval-trace-v1",
      preset: "hybrid_rerank",
      query: "What was Apple's total revenue in 2024?",
      filters: { ticker: null, section: null },
      top_k: 5,
      candidate_pool: 10,
      models: { embedding: "embed", reranker: "cross-encoder/ms-marco-MiniLM-L-6-v2", rrf_k: 60 },
      stages: [
        { name: "embedding", elapsed_ms: 12.5, status: "executed" },
        { name: "bm25", elapsed_ms: 3.25, status: "executed" },
        { name: "reranker", elapsed_ms: 48.75, status: "executed", skipped: false, reason: null },
        { name: "structured_promotion", elapsed_ms: null, status: "not_executed", reason: "Inspection does not apply production structured financial-row promotion." },
      ],
      candidates: [
        candidate(),
        candidate({
          chunk_id: "MSFT_chunk",
          document_id: "MSFT:0001",
          citation: "MSFT 10-K, MD&A",
          text_preview: "Microsoft Cloud revenue grew.",
          ticker: "MSFT",
          section: "mdna",
          fusion_rank: 1,
          cross_encoder_score: 1.75,
          final_rank: 2,
        }),
        candidate({
          chunk_id: "HD_chunk",
          document_id: "HD:0002",
          citation: "HD 10-K, Risk Factors",
          text_preview: "Disruptions in our supply chain.",
          ticker: "HD",
          section: "risk_factors",
          final_rank: null,
          cross_encoder_score: null,
          selected: false,
          dropped_reason: "ranked_below_top_k",
        }),
      ],
      selected_chunk_ids: ["AAPL_fixture_revenue_0", "MSFT_chunk"],
      candidate_count: 3,
      selected_count: 2,
      elapsed_ms: 74.75,
      score_semantics: {
        applies_to_preset: "hybrid_rerank",
        note: "Score families are distinct and must not be compared with one another. None of them is a confidence, accuracy, or probability.",
        families: {
          bm25_score: { family: "lexical", scale: "unbounded_positive", definition: "BM25 term-frequency score." },
          dense_score: { family: "dense_similarity", scale: "vector_similarity_as_returned_by_the_store", definition: "Query embedding similarity." },
          rrf_score: { family: "fusion", scale: "sum_of_reciprocal_ranks", definition: "Reciprocal rank fusion." },
          cross_encoder_score: { family: "reranker", scale: "cross_encoder_logit", definition: "Cross-encoder logit." },
        },
      },
      production_parity: {
        structured_promotion: "not_executed",
        lexical_ladder_merge_into_final: "not_executed",
        reason: "Inspection exposes the ranking stages only.",
      },
      scope: { documents: 50, eligible_document_ids: ["AAPL:fixture", "MSFT:0001"], truncated: true, reason: null },
      filter_values: { ticker: null, section: null, document_id: null, filing_date: null, year: null },
      ...overrides,
    },
  };
}

function renderPanel(props: Partial<React.ComponentProps<typeof RetrievalPanel>> = {}) {
  return render(
    <LocaleProvider>
      <RetrievalPanel
        tickers={["AAPL", "MSFT"]}
        sections={["mdna", "risk_factors", "financial_statements"]}
        isBackendConnected={true}
        onUseQuestion={vi.fn()}
        {...props}
      />
    </LocaleProvider>,
  );
}

async function submit(text = "What was Apple's total revenue in 2024?") {
  fireEvent.change(screen.getByLabelText("Retrieval Query"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Run retrieval" }));
  await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
}

describe("RetrievalPanel", () => {
  beforeEach(() => {
    inspectMock.mockResolvedValue(response());
    facetsMock.mockResolvedValue({
      generated_at: "2026-09-22T00:00:00Z",
      count_basis: "all_filters_except_own_dimension",
      scope: { ticker: null, section: null, year: null, filing_date: null, search: null, documents: 50 },
      facets: [
        { dimension: "company", availability: "recorded", reason: null, values: [{ value: "AAPL", count: 1 }] },
        { dimension: "year", availability: "recorded", reason: null, values: [{ value: 2025, count: 8 }, { value: 2026, count: 42 }] },
        { dimension: "section", availability: "recorded", reason: null, values: [{ value: "mdna", count: 46 }] },
      ],
    });
    documentsMock.mockResolvedValue({
      items: [{ document_id: "AAPL:fixture", ticker: "AAPL", filing_date: "2025-10-31", accession_number: "x", sections: ["mdna"], chunk_count: 3, source_url: null }],
      total: 1,
      page: 1,
      page_size: 50,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  test("typing never inspects: one submit sends exactly one request with the real filters", async () => {
    renderPanel();
    const input = screen.getByLabelText("Retrieval Query");
    fireEvent.change(input, { target: { value: "What was Apple's total revenue in 2024?" } });
    expect(inspectMock).not.toHaveBeenCalled();

    // Choose scope from catalog truth, then submit through the form.
    fireEvent.click(screen.getByRole("button", { name: "Company" }));
    fireEvent.click(screen.getByRole("option", { name: "Apple Inc. (AAPL)" }));
    fireEvent.click(await screen.findByRole("button", { name: "Year" }));
    fireEvent.click(screen.getByRole("option", { name: "2026 (42)" }));
    fireEvent.submit(input.closest("form") as HTMLFormElement);

    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    expect(inspectMock).toHaveBeenCalledWith(
      expect.objectContaining({ question: expect.stringContaining("total revenue"), ticker: "AAPL", year: 2026, preset: "hybrid_rerank", top_k: 5, candidate_pool: 10 }),
      expect.any(AbortSignal),
    );
    expect(await screen.findByTestId("submitted-retrieval-configuration")).toBeInTheDocument();
  });

  test("a too-short question cannot be submitted", async () => {
    renderPanel();
    fireEvent.change(screen.getByLabelText("Retrieval Query"), { target: { value: "hi" } });
    expect(screen.getByRole("button", { name: "Run retrieval" })).toBeDisabled();
    expect(inspectMock).not.toHaveBeenCalled();
  });

  test("selection, ordering, and paging are views over one trace and never inspect again", async () => {
    renderPanel();
    await submit();

    // Select a different row: no request, and the preview follows the selection.
    fireEvent.click(screen.getByRole("row", { name: /Microsoft Cloud revenue grew/ }));
    await waitFor(() => expect(screen.getByText("MSFT_chunk")).toBeInTheDocument());

    // Change the view order and the page size: still no request.
    fireEvent.click(screen.getByRole("button", { name: "Order" }));
    fireEvent.click(screen.getByRole("option", { name: "Reranker (score)" }));
    fireEvent.click(screen.getByRole("button", { name: "Rows per page" }));
    fireEvent.click(screen.getByRole("option", { name: "50 per page" }));
    expect(inspectMock).toHaveBeenCalledTimes(1);
  });

  test("shows real counts, real durations, and a null duration as unavailable", async () => {
    renderPanel();
    await submit();

    const summary = within(screen.getByTestId("retrieval-analyst-summary"));
    expect(summary.getByText("Candidates Retrieved")).toBeInTheDocument();
    expect(summary.getByText("3")).toBeInTheDocument();
    expect(summary.getByText("From 3 document sections")).toBeInTheDocument();
    expect(summary.getByText("Selected Results")).toBeInTheDocument();
    expect(summary.getAllByText("2").length).toBeGreaterThan(0);
    expect(summary.getByText("74.8 ms")).toBeInTheDocument();
    expect(summary.getByText(/embedding 12.5 ms \+ bm25 3.3 ms \+ reranker 48.8 ms/)).toBeInTheDocument();
  });

  test("keeps the score families distinct and never prints a percentage or confidence", async () => {
    renderPanel();
    await submit();

    const familyList = within(screen.getByTestId("score-family-list"));
    expect(familyList.getByText("BM25")).toBeInTheDocument();
    expect(familyList.getByText("Dense similarity")).toBeInTheDocument();
    expect(familyList.getByText("RRF")).toBeInTheDocument();
    expect(familyList.getByText("Reranker")).toBeInTheDocument();
    expect(familyList.getByText("cross_encoder_logit")).toBeInTheDocument();

    // The results card and the preview rail never carry a percentage or a
    // confidence label; the API's own semantics note is the only place those
    // words appear, and it says the families are *not* any of them.
    const results = within(screen.getByRole("heading", { name: "Retrieved Results" }).closest(".console-card") as HTMLElement);
    const resultsText = (results.getByRole("table").textContent ?? "").toLowerCase();
    expect(resultsText).not.toContain("%");
    expect(resultsText).not.toContain("confidence");
    expect(resultsText).not.toContain("probability");
    expect(document.body.textContent ?? "").not.toContain("%");
  });

  test("labels stages truthfully, including the inspection-only stage", async () => {
    renderPanel();
    await submit();

    expect(screen.getAllByText("structured_promotion").length).toBeGreaterThan(0);
    expect(screen.getByText("Inspection does not apply production structured financial-row promotion.")).toBeInTheDocument();
    // The stage list marks each stage exactly once, and the three stages that
    // ran are not counted among the ones that did not.
    const stageCard = within(screen.getByText("Stages in this trace").closest(".console-card") as HTMLElement);
    expect(stageCard.getAllByText("Executed")).toHaveLength(3);
    expect(stageCard.getAllByText("Not executed in inspection")).toHaveLength(1);
    expect(stageCard.getByText("structured_promotion")).toBeInTheDocument();
  });

  test("reports the bounded scope instead of presenting it as complete", async () => {
    renderPanel();
    await submit();
    expect(screen.getByText(/50 eligible documents \(the id list is bounded to the first 2\)/)).toBeInTheDocument();
  });

  test("shows only the dropped reason the trace supplied", async () => {
    renderPanel();
    await submit();
    expect(screen.getByText("Ranked below the selected top-k")).toBeInTheDocument();
    // The candidate without a reported reason is not explained.
    expect(screen.queryByText("Outside the candidate pool")).not.toBeInTheDocument();
  });

  test("states a skipped reranker stage instead of naming a model", async () => {
    inspectMock.mockResolvedValue(response({
      preset: "hybrid",
      models: { embedding: "embed", reranker: null, rrf_k: 60 },
      stages: [
        { name: "bm25", elapsed_ms: 3.25, status: "executed" },
        { name: "reranker", elapsed_ms: null, status: "skipped", skipped: true, reason: "The selected preset ranks without the cross-encoder." },
      ],
      score_semantics: {
        applies_to_preset: "hybrid",
        note: "Score families are distinct and must not be compared with one another. None of them is a confidence, accuracy, or probability.",
        families: {
          rrf_score: { family: "fusion", scale: "sum_of_reciprocal_ranks", definition: "Reciprocal rank fusion." },
        },
      },
    }));
    renderPanel();
    await submit();

    const summary = within(screen.getByTestId("retrieval-analyst-summary"));
    expect(summary.getByText("Skipped")).toBeInTheDocument();
    expect(summary.getByText("The selected preset ranks without the cross-encoder.")).toBeInTheDocument();
  });

  test("never renders a missing score as zero", async () => {
    renderPanel();
    await submit();

    // The third candidate reports no reranker score, so the family is named as
    // unavailable rather than shown as 0.
    fireEvent.click(screen.getByText("Disruptions in our supply chain."));
    const families = within(await screen.findByTestId("candidate-score-families"));
    expect(families.getAllByText("Not reported").length).toBeGreaterThan(0);
    expect(families.queryByText("0.0000")).not.toBeInTheDocument();
  });

  test("a stale response never replaces a newer trace", async () => {
    renderPanel();
    const form = () => screen.getByLabelText("Retrieval Query").closest("form") as HTMLFormElement;
    let resolveFirst: ((value: RetrievalInspectResponse) => void) | null = null;
    inspectMock.mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }));

    fireEvent.change(screen.getByLabelText("Retrieval Query"), { target: { value: "first question about revenue" } });
    fireEvent.submit(form());

    inspectMock.mockResolvedValueOnce(response({ query: "second question about supply chain" }));
    fireEvent.change(screen.getByLabelText("Retrieval Query"), { target: { value: "second question about supply chain" } });
    // A changed question can be committed while the first run is still open.
    fireEvent.submit(form());
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByText(/second question about supply chain/)).toBeInTheDocument());

    resolveFirst?.(response({ query: "first question about revenue" }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.getByText(/second question about supply chain/)).toBeInTheDocument();
    expect(screen.queryByText(/"first question about revenue"/)).not.toBeInTheDocument();
  });

  test("hands the reader the canonical chunk and document identity", async () => {
    const onOpenDocument = vi.fn();
    const onOpenSource = vi.fn();
    const onSaveEvidence = vi.fn<(source: Source) => void>();
    renderPanel({ onOpenDocument, onOpenSource, onSaveEvidence });
    await submit();

    const row = screen.getByRole("row", { name: /AAPL 10-K, Financial Statements/ });
    fireEvent.click(within(row).getByRole("button", { name: "Open document workspace" }));
    expect(onOpenDocument).toHaveBeenCalledWith(expect.objectContaining({
      kind: "retrieval",
      documentId: "AAPL:fixture",
      returnView: "retrieval",
      returnFocusId: "retrieval-document-workspace-AAPL_fixture_revenue_0",
      selectedSource: expect.objectContaining({ chunk_id: "AAPL_fixture_revenue_0", document_id: "AAPL:fixture" }),
    }));
    expect(inspectMock).toHaveBeenCalledTimes(1);

    fireEvent.click(within(row).getByRole("button", { name: "Save evidence" }));
    expect(onSaveEvidence).toHaveBeenCalledWith(expect.objectContaining({ chunk_id: "AAPL_fixture_revenue_0" }));

    fireEvent.click(within(row).getByRole("button", { name: "Open indexed source" }));
    expect(onOpenSource).toHaveBeenCalledWith(expect.objectContaining({ chunk_id: "AAPL_fixture_revenue_0" }));
    expect(inspectMock).toHaveBeenCalledTimes(1);
  });

  test("exports the completed trace that the endpoint returned", async () => {
    let exported = "";
    const createObjectURL = vi.fn((blob: Blob) => {
      exported = String((blob as unknown as { parts?: unknown[] }).parts?.[0] ?? "");
      return "blob:trace";
    });
    class RecordingBlob {
      parts: unknown[];
      constructor(parts: unknown[]) {
        this.parts = parts;
      }
    }
    vi.stubGlobal("Blob", RecordingBlob);
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL: vi.fn() });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    renderPanel();
    await submit();

    fireEvent.click(screen.getByRole("button", { name: "JSON" }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(JSON.parse(exported)).toMatchObject({ trace_version: "retrieval-trace-v1", preset: "hybrid_rerank" });
    expect(exported).toContain("AAPL_fixture_revenue_0");

    fireEvent.click(screen.getByRole("button", { name: "CSV" }));
    expect(exported.split("\n")[0]).toContain("cross_encoder_score");
    expect(exported).toContain("ranked_below_top_k");
    clickSpy.mockRestore();
    vi.unstubAllGlobals();
  });

  test("marks the draft as different without hiding the trace it already has", async () => {
    renderPanel();
    await submit();
    fireEvent.change(screen.getByLabelText("Retrieval Query"), { target: { value: "a different question entirely" } });
    expect(screen.getByText(/This configuration differs from the trace on screen/)).toBeInTheDocument();
    // The trace keeps its own submitted configuration, unrelabelled.
    expect(screen.getByTestId("submitted-retrieval-configuration")).toHaveTextContent("What was Apple's total revenue in 2024?");
    expect(inspectMock).toHaveBeenCalledTimes(1);
  });

  test("a preset without the cross-encoder offers no reranker ordering", async () => {
    inspectMock.mockResolvedValue(response({
      preset: "bm25" as RetrievalPreset,
      score_semantics: {
        applies_to_preset: "bm25",
        note: "Score families are distinct and must not be compared with one another. None of them is a confidence, accuracy, or probability.",
        families: { bm25_score: { family: "lexical", scale: "unbounded_positive", definition: "BM25 term-frequency score." } },
      },
      candidates: [candidate({ cross_encoder_score: null, rrf_score: null, dense_score: null })],
    }));
    renderPanel();
    fireEvent.change(screen.getByRole("button", { name: "Preset" }) ? screen.getByLabelText("Retrieval Query") : screen.getByLabelText("Retrieval Query"), { target: { value: "What was Apple's total revenue in 2024?" } });
    fireEvent.click(screen.getByRole("button", { name: "Preset" }));
    fireEvent.click(screen.getByRole("option", { name: "BM25" }));
    fireEvent.click(screen.getByRole("button", { name: "Run retrieval" }));
    await waitFor(() => expect(inspectMock).toHaveBeenCalledTimes(1));
    expect(inspectMock.mock.calls[0]?.[0].preset).toBe("bm25");

    fireEvent.click(await screen.findByRole("button", { name: "Order" }));
    expect(screen.getByRole("option", { name: "BM25 (score)" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Reranker (score)" })).not.toBeInTheDocument();
  });
});
