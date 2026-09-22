import { describe, expect, test } from "vitest";

import {
  availableScoreKeys,
  candidateSectionCount,
  candidateStatus,
  formatDuration,
  formatScore,
  formatScoreForFamily,
  hasNegativeScore,
  latencyBreakdown,
  orderOptions,
  pageLabel,
  pageRange,
  poolHasRerankerScores,
  primaryScoreKey,
  productionParityEntries,
  rankMovement,
  rerankerModel,
  rerankerStage,
  scopeSummary,
  scoreFamilyDefinition,
  scoreSemanticsNote,
  sortCandidates,
  stageStatus,
  stageStatusLabel,
  traceConfigurationSummary,
} from "./traceModel";
import type { RetrievalCandidate, RetrievalTrace, RetrievalScoreSemantics } from "../types";

const SEMANTICS: RetrievalScoreSemantics = {
  applies_to_preset: "hybrid_rerank",
  note: "Score families are distinct and must not be compared with one another. None of them is a confidence, accuracy, or probability.",
  families: {
    bm25_score: { family: "lexical", scale: "unbounded_positive", definition: "BM25 term-frequency score over the filtered index." },
    dense_score: { family: "dense_similarity", scale: "vector_similarity_as_returned_by_the_store", definition: "Query embedding similarity." },
    rrf_score: { family: "fusion", scale: "sum_of_reciprocal_ranks", definition: "Reciprocal rank fusion of the stage rankings." },
    cross_encoder_score: { family: "reranker", scale: "cross_encoder_logit", definition: "Cross-encoder logit for the query/chunk pair." },
  },
};

function candidate(overrides: Partial<RetrievalCandidate> = {}): RetrievalCandidate {
  return {
    chunk_id: "AAPL_fixture_revenue_0",
    document_id: "AAPL:fixture",
    citation: "AAPL 10-K, Financial Statements",
    text_preview: "Total revenue was reported in fiscal 2024.",
    ticker: "AAPL",
    section: "financial_statements",
    filing_date: "2025-10-31",
    bm25_score: 12.5,
    bm25_rank: 2,
    dense_score: 0.71,
    dense_rank: 3,
    rrf_score: 0.0326,
    fusion_rank: 2,
    cross_encoder_score: -3.25,
    final_rank: 1,
    selected: true,
    dropped_reason: null,
    ...overrides,
  };
}

function trace(overrides: Partial<RetrievalTrace> = {}): RetrievalTrace {
  return {
    trace_version: "retrieval-trace-v1",
    preset: "hybrid_rerank",
    query: "revenue 2024",
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
    candidates: [candidate()],
    selected_chunk_ids: ["AAPL_fixture_revenue_0"],
    candidate_count: 1,
    selected_count: 1,
    elapsed_ms: 64.5,
    score_semantics: SEMANTICS,
    production_parity: {
      structured_promotion: "not_executed",
      lexical_ladder_merge_into_final: "not_executed",
      reason: "Inspection exposes the ranking stages only.",
    },
    scope: { documents: 50, eligible_document_ids: ["AAPL:fixture"], truncated: false, reason: null },
    filter_values: { ticker: "AAPL", section: "financial_statements", document_id: null, filing_date: null, year: 2025 },
    ...overrides,
  };
}

describe("traceModel score truthfulness", () => {
  test("names the primary signal per preset instead of a universal score", () => {
    expect(primaryScoreKey("bm25")).toBe("bm25_score");
    expect(primaryScoreKey("dense")).toBe("dense_score");
    expect(primaryScoreKey("hybrid")).toBe("rrf_score");
    expect(primaryScoreKey("hybrid_rerank")).toBe("cross_encoder_score");
  });

  test("never renders a missing score as zero", () => {
    expect(formatScore(null)).toBe("Not reported");
    expect(formatScore(undefined)).toBe("Not reported");
    expect(formatScore(0)).toBe("0.0000");
    expect(formatScoreForFamily("cross_encoder_score", null)).toBe("Not reported");
  });

  test("keeps a negative reranker logit negative", () => {
    expect(formatScore(-3.25)).toBe("-3.2500");
    expect(hasNegativeScore([candidate()], "cross_encoder_score")).toBe(true);
    expect(hasNegativeScore([candidate({ cross_encoder_score: 3.25 })], "cross_encoder_score")).toBe(false);
  });

  test("uses a precision that fits the family scale", () => {
    expect(formatScore(0.0326)).toBe("0.032600");
    expect(formatScore(12.5)).toBe("12.5000");
  });

  test("carries the API's own definition and note", () => {
    expect(scoreFamilyDefinition(SEMANTICS, "cross_encoder_score")?.scale).toBe("cross_encoder_logit");
    expect(scoreFamilyDefinition(undefined, "bm25_score")).toBeNull();
    expect(scoreSemanticsNote(trace())).toContain("None of them is a confidence, accuracy, or probability");
  });

  test("offers only the score orders the trace reported", () => {
    const full = orderOptions(trace(), [candidate()], false);
    expect(full.map((option) => option.value)).toEqual([
      "trace_order", "bm25_score", "dense_score", "rrf_score", "cross_encoder_score",
    ]);
    const lexicalOnly = orderOptions(
      trace({ preset: "bm25", score_semantics: { ...SEMANTICS, applies_to_preset: "bm25", families: { bm25_score: SEMANTICS.families.bm25_score! } } }),
      [candidate({ dense_score: null, rrf_score: null, cross_encoder_score: null })],
      false,
    );
    expect(lexicalOnly.map((option) => option.value)).toEqual(["trace_order", "bm25_score"]);
    expect(availableScoreKeys(trace(), [candidate()])).toHaveLength(4);
  });
});

describe("traceModel stage truthfulness", () => {
  test("reads status from the API and never implies a run", () => {
    expect(stageStatus({ name: "bm25", elapsed_ms: 1, status: "executed" })).toBe("executed");
    expect(stageStatus({ name: "reranker", elapsed_ms: 1, skipped: true })).toBe("skipped");
    expect(stageStatus({ name: "structured_promotion", elapsed_ms: null })).toBe("not_executed");
    expect(stageStatusLabel("not_executed", false)).toBe("Not executed in inspection");
  });

  test("reports a null duration as unavailable, never as zero", () => {
    expect(formatDuration(null)).toBe("Not reported");
    expect(formatDuration(0)).toBe("0.0 ms");
    expect(formatDuration(48.75)).toBe("48.8 ms");
    expect(formatDuration(1500)).toBe("1.50 s");
  });

  test("builds the latency breakdown only from stages that ran", () => {
    expect(latencyBreakdown(trace(), false)).toBe("embedding 12.5 ms + bm25 3.3 ms + reranker 48.8 ms");
    const nothingRan = trace({
      stages: [
        { name: "reranker", elapsed_ms: null, status: "skipped", skipped: true, reason: "preset" },
        { name: "structured_promotion", elapsed_ms: null, status: "not_executed" },
      ],
    });
    expect(latencyBreakdown(nothingRan, false)).toBeNull();
  });

  test("names the reranker model only when the stage ran with it", () => {
    expect(rerankerStage(trace())?.name).toBe("reranker");
    expect(rerankerModel(trace())).toBe("cross-encoder/ms-marco-MiniLM-L-6-v2");
    const skipped = trace({
      preset: "hybrid",
      models: { embedding: "embed", reranker: null, rrf_k: 60 },
      stages: [{ name: "reranker", elapsed_ms: null, status: "skipped", skipped: true, reason: "The selected preset ranks without the cross-encoder." }],
    });
    expect(rerankerModel(skipped)).toBeNull();
    expect(latencyBreakdown(skipped, false)).toBeNull();
  });

  test("reports production parity from the API's own statuses", () => {
    expect(productionParityEntries(trace())).toEqual([
      { name: "structured_promotion", status: "not_executed" },
      { name: "lexical_ladder_merge_into_final", status: "not_executed" },
    ]);
    expect(productionParityEntries(trace({ production_parity: undefined }))).toEqual([]);
  });
});

describe("traceModel candidate lineage", () => {
  test("uses the API's status and only the reported dropped reason", () => {
    expect(candidateStatus(candidate(), false)).toEqual({ kind: "selected", label: "Selected" });
    expect(candidateStatus(candidate({ selected: false, dropped_reason: "ranked_below_top_k" }), false))
      .toEqual({ kind: "dropped", label: "Ranked below the selected top-k" });
    expect(candidateStatus(candidate({ selected: false, dropped_reason: null }), false))
      .toEqual({ kind: "not_selected", label: "Not selected" });
  });

  test("computes rank movement from the trace's own ranks", () => {
    expect(rankMovement(candidate({ fusion_rank: 4, final_rank: 1 }), false))
      .toEqual({ before: 4, after: 1, delta: 3, label: "Up 3" });
    expect(rankMovement(candidate({ fusion_rank: 1, final_rank: 3 }), false).label).toBe("Down 2");
    expect(rankMovement(candidate({ fusion_rank: 2, final_rank: 2 }), false).label).toBe("No change");
    expect(rankMovement(candidate({ fusion_rank: null, final_rank: 2 }), false).label).toBe("Not reported");
    expect(rankMovement(candidate({ fusion_rank: 2, final_rank: null }), false).delta).toBeNull();
  });

  test("treats the pool as comparable only when every candidate is reranked", () => {
    expect(poolHasRerankerScores([candidate(), candidate({ chunk_id: "b" })])).toBe(true);
    expect(poolHasRerankerScores([candidate(), candidate({ chunk_id: "b", cross_encoder_score: null })])).toBe(false);
    expect(poolHasRerankerScores([])).toBe(false);
  });

  test("keeps ties and missing scores deterministic when ordering", () => {
    const tied = [
      candidate({ chunk_id: "b", rrf_score: 0.02, final_rank: 2 }),
      candidate({ chunk_id: "a", rrf_score: 0.02, final_rank: 1 }),
      candidate({ chunk_id: "c", rrf_score: null, final_rank: 3 }),
    ];
    expect(sortCandidates(tied, "rrf_score").map((item) => item.chunk_id)).toEqual(["a", "b", "c"]);
    expect(sortCandidates(tied, "trace_order").map((item) => item.chunk_id)).toEqual(["a", "b", "c"]);
  });

  test("counts distinct sections for the pool hint", () => {
    expect(candidateSectionCount([candidate(), candidate({ chunk_id: "b" }), candidate({ chunk_id: "c", section: "mdna" })])).toBe(2);
    expect(candidateSectionCount([candidate({ section: null })])).toBe(0);
  });
});

describe("traceModel scope and configuration", () => {
  test("never presents a bounded eligible list as complete", () => {
    expect(scopeSummary({ documents: 3, eligible_document_ids: ["a", "b", "c"], truncated: false, reason: null }, false))
      .toBe("3 eligible documents");
    expect(scopeSummary({ documents: 50, eligible_document_ids: ["a", "b"], truncated: true, reason: null }, false))
      .toBe("50 eligible documents (the id list is bounded to the first 2)");
    expect(scopeSummary({ documents: null, eligible_document_ids: [], truncated: false, reason: "The catalog is unavailable." }, false))
      .toBe("The catalog is unavailable.");
    expect(scopeSummary(undefined, false)).toBeNull();
  });

  test("describes the submitted configuration from the trace's own values", () => {
    expect(traceConfigurationSummary(trace(), false))
      .toBe("AAPL · financial_statements · top K 5 · pool 10 · Hybrid + reranker · 2025");
    const unfiltered = trace({ filter_values: { ticker: null, section: null, document_id: null, filing_date: null, year: null } });
    expect(traceConfigurationSummary(unfiltered, false)).toContain("All companies · All sections");
  });

  test("pages the fetched pool in the view", () => {
    expect(pageRange(0, 1, 20)).toEqual({ start: 0, end: 0, pageCount: 1 });
    expect(pageRange(45, 3, 20)).toEqual({ start: 41, end: 45, pageCount: 3 });
    expect(pageRange(45, 9, 20)).toEqual({ start: 41, end: 45, pageCount: 3 });
    expect(pageLabel(pageRange(45, 1, 20), 45, false)).toBe("Showing 1–20 of 45 candidates");
    expect(pageLabel(pageRange(0, 1, 20), 0, false)).toBe("0 candidates");
  });
});
