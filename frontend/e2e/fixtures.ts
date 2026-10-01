/**
 * API fixtures for browser tests. Every backend interaction is served from
 * local route mocks: tests never reach a real provider or backend, and any
 * request outside the mocked API origin fails the test loudly.
 */

import { createHash } from "node:crypto";
import { Page, Route, expect } from "@playwright/test";
import { nativeDefinitions } from "../src/test/evaluationFixtures";

export const API_ORIGIN = "http://127.0.0.1:8000";

export const MODEL_REGISTRY_FIXTURE = [
  {
    id: "generator",
    role: "generator",
    provider: "groq",
    configured_model_id: "openai/gpt-oss-120b",
    configured_revision: null,
    runtime_model_id: null,
    runtime_revision: null,
    configuration_status: "configured",
    load_status: "unknown",
    availability_status: "unknown",
    availability_reason: "Provider reachability is not probed while browsing the registry.",
    credential_status: "configured",
    test_capabilities: ["runtime_identity"],
  },
  {
    id: "embedding",
    role: "embedding",
    provider: "hugging_face",
    configured_model_id: "nomic-ai/nomic-embed-text-v1.5",
    configured_revision: "main",
    runtime_model_id: "nomic-ai/nomic-embed-text-v1.5",
    runtime_revision: "main",
    configuration_status: "configured",
    load_status: "loaded",
    availability_status: "available",
    availability_reason: null,
    credential_status: "not_required",
    test_capabilities: ["runtime_identity"],
  },
  {
    id: "reranker",
    role: "reranker",
    provider: "hugging_face",
    configured_model_id: "cross-encoder/ms-marco-MiniLM-L-6-v2",
    configured_revision: "main",
    runtime_model_id: null,
    runtime_revision: null,
    configuration_status: "configured",
    load_status: "not_loaded",
    availability_status: "unknown",
    availability_reason: "The reranker has not been loaded in this process.",
    credential_status: "not_required",
    test_capabilities: ["runtime_identity"],
  },
] as const;

export const DATASET_REGISTRY_FIXTURE = [
  {
    id: "serving-corpus",
    kind: "corpus",
    name: "Serving SEC filing corpus",
    description: "The SEC filing corpus currently bound to retrieval.",
    availability: "degraded",
    reason_code: "configured_company_gap",
    reason: "Two configured companies do not yet have searchable filings.",
    version: "index-build-2026-09-18",
    revision: "corpus-revision-8f3a",
    record_count: 48,
    record_unit: "documents",
  },
  {
    id: "evaluation-test-set",
    kind: "evaluation",
    name: "Built-in evaluation test set",
    description: "The repository-owned SEC QA evaluation cases.",
    availability: "available",
    reason_code: null,
    reason: null,
    version: "evaluation-test-set-v1",
    revision: "eval-revision-2026-09",
    record_count: 30,
    record_unit: "cases",
  },
] as const;

export const DATASET_DETAIL_FIXTURES: Record<string, Record<string, unknown>> = {
  "serving-corpus": {
    ...DATASET_REGISTRY_FIXTURE[0],
    coverage: {
      kind: "corpus",
      documents: 48,
      companies: 8,
      chunks: 10053,
      configured_companies: 10,
      configured_companies_with_documents: ["AAPL", "AMZN", "GOOGL", "HD", "MSFT", "NVDA", "ORCL", "TSLA"],
      configured_companies_without_documents: ["BRK-B", "JPM"],
      filing_years: { availability: "recorded", earliest: 2023, latest: 2026, documents_without_value: 0, reason: null },
      sections: [
        { key: "business", count: 48 },
        { key: "risk_factors", count: 47 },
        { key: "mdna", count: 45 },
        { key: "financial_statements", count: 42 },
        { key: "financial_table", count: 39 },
      ],
    },
    provenance: {
      authority: "qdrant_index_manifest",
      status: "consistent",
      reason_code: null,
      reason: null,
      schema_version: 1,
      revision: "corpus-revision-8f3a",
      build_version: "index-build-2026-09-18",
      collection_name: "sec_filings",
      point_count: 10053,
      embedding_model_id: "nomic-ai/nomic-embed-text-v1.5",
      embedding_model_revision: "main",
      vector_dimension: 768,
      distance_metric: "Cosine",
      snapshot_id: "snapshot-ui009",
      embedding_generation_id: "embedding-generation-ui009",
      embedding_generation_fingerprint: "fixture-fingerprint",
    },
  },
  "evaluation-test-set": {
    ...DATASET_REGISTRY_FIXTURE[1],
    coverage: {
      kind: "evaluation",
      cases: 30,
      categories: [{ key: "fact_lookup", count: 12 }, { key: "comparison", count: 10 }, { key: "synthesis", count: 8 }],
      priorities: [{ key: "1", count: 10 }, { key: "2", count: 20 }],
      tickers: ["AAPL", "AMZN", "GOOGL", "MSFT", "NVDA"],
      sections: ["business", "financial_statements", "mdna", "risk_factors"],
    },
    provenance: {
      authority: "built_in_evaluation_test_set",
      status: "recorded",
      reason_code: null,
      reason: null,
      schema_version: 1,
      revision: "eval-revision-2026-09",
      build_version: "evaluation-test-set-v1",
      collection_name: null,
      point_count: null,
      embedding_model_id: null,
      embedding_model_revision: null,
      vector_dimension: null,
      distance_metric: null,
      snapshot_id: null,
      embedding_generation_id: null,
      embedding_generation_fingerprint: null,
    },
  },
};

export interface HistoryTurnFixture {
  user: string;
  assistant: string;
  rewritten_query: string | null;
}

export interface HistoryFixture {
  session_id: string;
  turns: HistoryTurnFixture[];
  context?: {
    status: "available" | "missing";
    retained_turns: number;
    ttl_remaining_seconds: number;
  };
}

/**
 * Deterministic discovery corpus for the Search workspace.
 *
 * The excerpts, sections, filing dates and score magnitudes mirror the real
 * corpus shapes recorded by `scripts/diagnostics/ui006_discovery_probe.py`
 * (BM25 scores around 9-13, snippets bounded with leading/trailing ellipses and
 * character ranges, 200-candidate ceiling). Nothing here calls a model, a
 * provider, SEC, or a backend.
 */
export interface SearchFixtureHit {
  chunk_id: string;
  document_id: string;
  ticker: string;
  section: string;
  filing_date: string;
  report_date: string;
  chunk_index: number;
  score: number;
  text: string;
}

/**
 * The best-ranked fixture excerpt belongs to the fixture catalog document the
 * rest of the suite already knows (`AAPL:fixture`, served by the reader and
 * chunk routes), so a Search result handoff lands on a real fixture chunk
 * instead of an identity the reader cannot resolve.
 */
function searchPrimaryHit(): SearchFixtureHit {
  return {
    chunk_id: "AAPL_fixture_revenue_0",
    document_id: FIXTURE_DOCUMENT_ID,
    ticker: "AAPL",
    section: "financial_statements",
    filing_date: "2025-10-31",
    report_date: "2025-09-27",
    chunk_index: 2,
    score: 11.472913,
    text: "Total revenue was reported in fiscal 2024.",
  };
}

const SEARCH_FIXTURE_REAL_SHAPED_HITS: SearchFixtureHit[] = [
  {
    chunk_id: "MSFT_000095017025100235_mdna_0005",
    document_id: "MSFT:0000950170-25-100235",
    ticker: "MSFT",
    section: "mdna",
    filing_date: "2025-07-30",
    report_date: "2025-06-30",
    chunk_index: 5,
    score: 10.703384,
    text: "…Microsoft Cloud gross margin percentage Gross margin percentage for our Microsoft Cloud business grew as cloud revenue increased across every customer segment…",
  },
  {
    chunk_id: "MSFT_000095017025100235_mdna_0004",
    document_id: "MSFT:0000950170-25-100235",
    ticker: "MSFT",
    section: "mdna",
    filing_date: "2025-07-30",
    report_date: "2025-06-30",
    chunk_index: 4,
    score: 10.413538,
    text: "…icrosoft 365 Commercial cloud revenue growth metric. Other changes include combining Windows OEM and Devices into a single revenue growth metric…",
  },
  {
    chunk_id: "ORCL_000119312526277521_mdna_0076",
    document_id: "ORCL:0001193125-26-277521",
    ticker: "ORCL",
    section: "mdna",
    filing_date: "2026-06-22",
    report_date: "2026-05-31",
    chunk_index: 76,
    score: 9.230227,
    text: "Our cloud and software business, which represented 87% of our total revenues, delivers infrastructure technologies through our cloud revenue segments…",
  },
  {
    chunk_id: "INTC_000005086326000011_risk_factors_0024",
    document_id: "INTC:0000050863-26-000011",
    ticker: "INTC",
    section: "risk_factors",
    filing_date: "2026-01-23",
    report_date: "2025-12-27",
    chunk_index: 24,
    score: 10.32074,
    text: "…y upon a complex global supply chain. We have a highly complex global supply chain composed of thousands of suppliers…",
  },
  {
    chunk_id: "HD_000162828026019436_risk_factors_0030",
    document_id: "HD:0001628280-26-019436",
    ticker: "HD",
    section: "risk_factors",
    filing_date: "2026-03-18",
    report_date: "2026-02-01",
    chunk_index: 30,
    score: 10.06444,
    text: "Disruptions in our supply chain and other factors affecting the availability and distribution of our merchandise could adversely impact our business and reputation…",
  },
];

export const SEARCH_FIXTURE_SECTIONS = ["business", "financial_statements", "financial_table", "mdna", "risk_factors"] as const;

/**
 * The remaining ranked excerpts. They keep the fixture snapshot larger than one
 * page so pagination is exercised through the real API-004 paging path, and
 * their text still contains the fixture query words so highlights stay real.
 */
const SEARCH_FIXTURE_EXTRA_ROWS: Array<[string, string, string, number, string]> = [
  ["AAPL", "risk_factors", "2025-10-31", 9.812004, "…our supply chain and cloud revenue depend on suppliers and partners…"],
  ["AMZN", "mdna", "2026-02-07", 9.640112, "…aws cloud revenue and the supply chain of our retail operations…"],
  ["GOOGL", "business", "2026-01-31", 9.511877, "…cloud revenue growth and supply chain constraints for hardware…"],
  ["NVDA", "risk_factors", "2026-02-26", 9.402318, "…our supply chain and cloud revenue from data center customers…"],
  ["TSLA", "mdna", "2026-01-26", 9.208845, "…supply chain pressures and cloud revenue for energy services…"],
  ["BRK-B", "business", "2026-02-24", 9.077411, "…cloud revenue exposure and supply chain disruption in insurance…"],
  ["JPM", "risk_factors", "2026-02-16", 8.930512, "…technology supply chain and cloud revenue dependencies…"],
  ["GS", "business", "2026-02-25", 8.812007, "…cloud revenue platforms and supply chain of market data…"],
  ["MS", "risk_factors", "2026-02-19", 8.701244, "…cloud revenue and supply chain resilience expectations…"],
  ["XOM", "mdna", "2026-02-21", 8.640913, "…supply chain logistics and cloud revenue for digital services…"],
  ["CVX", "business", "2026-02-20", 8.512770, "…supply chain investments and cloud revenue reporting…"],
  ["PFE", "risk_factors", "2026-02-27", 8.402881, "…clinical supply chain and cloud revenue analytics…"],
  ["UNH", "mdna", "2026-02-13", 8.311004, "…supply chain of care services and cloud revenue systems…"],
  ["HD", "business", "2026-03-18", 8.220645, "…supply chain network and cloud revenue for online sales…"],
  ["LOW", "mdna", "2026-03-20", 8.110338, "…supply chain costs and cloud revenue channels…"],
  ["TGT", "risk_factors", "2026-03-11", 7.980221, "…supply chain disruption and cloud revenue dependencies…"],
  ["COST", "business", "2026-03-05", 7.845902, "…supply chain scale and cloud revenue reporting…"],
];

export interface SearchFixtureHit {
  chunk_id: string;
  document_id: string;
  ticker: string;
  section: string;
  filing_date: string;
  report_date: string;
  chunk_index: number;
  score: number;
  text: string;
}

export const SEARCH_FIXTURE_EXTRA_HITS: SearchFixtureHit[] = SEARCH_FIXTURE_EXTRA_ROWS.map(
  ([ticker, section, filingDate, score, text]) => ({
    chunk_id: `${ticker}_fixture_${section}_0002`,
    document_id: `${ticker}:0000${ticker.replace("-", "")}26-000002`,
    ticker,
    section,
    filing_date: filingDate,
    report_date: filingDate,
    chunk_index: 2,
    score,
    text,
  }),
);

export function searchFixtureHits(): SearchFixtureHit[] {
  return [searchPrimaryHit(), ...SEARCH_FIXTURE_REAL_SHAPED_HITS, ...SEARCH_FIXTURE_EXTRA_HITS];
}

/**
 * Match ranges for a fixture excerpt, derived the same way `build_snippet`
 * derives real ones: every occurrence of a literal query word, capped at the
 * API's eight-range bound.
 */
function fixtureRanges(text: string, terms: string[] = ["cloud", "revenue", "supply", "chain"]): Array<[number, number]> {
  const lower = text.toLowerCase();
  const ranges: Array<[number, number]> = [];
  for (const term of terms) {
    let cursor = 0;
    while (ranges.length < 8) {
      const at = lower.indexOf(term, cursor);
      if (at === -1) break;
      ranges.push([at, at + term.length]);
      cursor = at + term.length;
    }
  }
  return ranges.sort((left, right) => left[0] - right[0]);
}

function searchFixtureSnapshot(
  body: Record<string, unknown>,
  options: { ceiling: "bounded" | "complete" },
  page: number,
  pageSize: number,
): Record<string, unknown> {
  const query = String(body.query ?? "");
  const groupBy = body.group_by === "chunk" ? "chunk" : "document";
  const ticker = typeof body.ticker === "string" && body.ticker ? body.ticker : null;
  const section = typeof body.section === "string" && body.section ? body.section : null;
  const year = typeof body.year === "number" ? body.year : null;

  const matching = searchFixtureHits().filter((hit) => {
    if (ticker && hit.ticker !== ticker) return false;
    if (section && hit.section !== section) return false;
    if (year && Number(hit.filing_date.slice(0, 4)) !== year) return false;
    return true;
  });

  const hits = matching.map((hit) => ({
    chunk_id: hit.chunk_id,
    document_id: hit.document_id,
    ticker: hit.ticker,
    section: hit.section,
    filing_date: hit.filing_date,
    report_date: hit.report_date,
    chunk_index: hit.chunk_index,
    score: hit.score,
    // Ranges are derived from the returned text, exactly like the API does.
    snippet: { text: hit.text, ranges: fixtureRanges(hit.text), truncated: true },
  }));

  const groups = [...new Set(hits.map((hit) => hit.document_id))].map((documentId) => {
    const documentHits = hits.filter((hit) => hit.document_id === documentId);
    return {
      document_id: documentId,
      ticker: documentHits[0].ticker,
      filing_date: documentHits[0].filing_date,
      report_date: documentHits[0].report_date,
      sections: [...new Set(documentHits.map((hit) => hit.section))],
      best_score: Math.max(...documentHits.map((hit) => hit.score)),
      hit_count: documentHits.length,
      hits: documentHits,
    };
  });

  const items = groupBy === "document" ? groups : hits;
  const start = (page - 1) * pageSize;
  const documentCount = new Set(hits.map((hit) => hit.document_id)).size;
  // `ceiling` keeps both the bounded and the complete wording reachable. The
  // reported ceiling is this fixture's own ranked size, so the bounded copy
  // stays internally consistent with the counts beside it.
  const bounded = options.ceiling === "bounded" && items.length > 0;
  const scopeSections = [...new Set(matching.map((hit) => hit.section))].sort();
  const scopeYears = [...new Set(matching.map((hit) => Number(hit.filing_date.slice(0, 4))))].sort((left, right) => right - left);
  const scopeCompanies = [...new Set(matching.map((hit) => hit.ticker))].sort();

  return {
    search_id: `search-${String(options.ceiling === "bounded" ? "0123456789abcdef" : "fedcba9876543210")}`,
    query: { text: query, normalized: query.toLowerCase(), mode: "keyword" },
    grouping: { group_by: groupBy, group_count: groups.length, hit_count: hits.length },
    engine: {
      key: "bm25_lexical",
      version: "v1",
      definition:
        "Chunks that contain at least one query term match; BM25 lexical score over indexed chunk text orders them. The score is a ranking signal for keyword matching, not a confidence, accuracy, or probability, and a zero score means the term occurs without being discriminative.",
    },
    scope: {
      ticker,
      section,
      year,
      filing_date: null,
      documents: documentCount,
      count_scope: items.length > 0 ? "bounded_candidates" : "no_matches",
      candidate_ceiling: hits.length,
      limited_by_ceiling: bounded,
      matched_documents: documentCount,
      matched_chunks: hits.length,
    },
    items: items.slice(start, start + pageSize),
    total: items.length,
    page,
    page_size: pageSize,
    facets: [
      {
        dimension: "company",
        availability: "recorded",
        reason: null,
        values: scopeCompanies.map((value) => ({ value, count: matching.filter((hit) => hit.ticker === value).length })),
      },
      {
        dimension: "year",
        availability: "recorded",
        reason: null,
        values: scopeYears.map((value) => ({ value, count: matching.filter((hit) => Number(hit.filing_date.slice(0, 4)) === value).length })),
      },
      {
        dimension: "section",
        availability: "recorded",
        reason: null,
        values: scopeSections.map((value) => ({ value, count: matching.filter((hit) => hit.section === value).length })),
      },
    ],
    created_at: "2026-09-22T00:00:00Z",
    expires_at: "2026-09-22T00:15:00Z",
    ttl_seconds: 900,
  };
}

/**
 * The real API-005 trace shapes the Retrieval and Reranker pages consume.
 *
 * Ranks, score families, stage statuses, the bounded scope, and the dropped
 * reasons mirror `src/retrieval/hybrid_retriever.py`; a preset that does not
 * rerank reports the reranker stage as skipped with the API's own reason, and
 * the inspection-only stage reports `not_executed` with a null duration.
 */
const RETRIEVAL_SCORE_SEMANTICS: Record<string, { family: string; scale: string; definition: string }> = {
  bm25_score: {
    family: "lexical",
    scale: "unbounded_positive",
    definition: "BM25 term-frequency score over the filtered index; higher means stronger keyword overlap.",
  },
  dense_score: {
    family: "dense_similarity",
    scale: "vector_similarity_as_returned_by_the_store",
    definition: "Similarity of the query embedding to the chunk embedding, reported with the store's own scale.",
  },
  rrf_score: {
    family: "fusion",
    scale: "sum_of_reciprocal_ranks",
    definition: "Reciprocal rank fusion of the lexical, dense, and query-shaper rankings; not comparable across queries.",
  },
  cross_encoder_score: {
    family: "reranker",
    scale: "cross_encoder_logit",
    definition: "Cross-encoder relevance logit for the query/chunk pair; only comparable within one candidate pool.",
  },
};

const RETRIEVAL_SCORE_NOTE =
  "Score families are distinct and must not be compared with one another. None of them is a confidence, accuracy, or probability.";

function retrievalFixtureFamilies(preset: string) {
  const keys: Record<string, string[]> = {
    bm25: ["bm25_score"],
    dense: ["dense_score"],
    hybrid: ["bm25_score", "dense_score", "rrf_score"],
    hybrid_rerank: ["bm25_score", "dense_score", "rrf_score", "cross_encoder_score"],
  };
  const chosen = keys[preset] ?? keys.hybrid_rerank;
  return Object.fromEntries(chosen.map((key) => [key, RETRIEVAL_SCORE_SEMANTICS[key]]));
}

/** Six fixture candidates in the same shape the inspection endpoint returns. */
export function retrievalFixtureCandidates(preset: string) {
  const reranked = preset === "hybrid_rerank";
  const rows = [
    {
      chunk_id: "AAPL_fixture_revenue_0",
      document_id: FIXTURE_DOCUMENT_ID,
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
      fusion_rank: 1,
      cross_encoder_score: reranked ? 8.25 : null,
      final_rank: 1,
      selected: true,
      dropped_reason: null,
    },
    {
      chunk_id: "MSFT_000095017025100235_mdna_0005",
      document_id: "MSFT:0000950170-25-100235",
      citation: "MSFT 10-K, MD&A",
      text_preview: "Microsoft Cloud gross margin percentage grew as cloud revenue increased.",
      ticker: "MSFT",
      section: "mdna",
      filing_date: "2025-07-30",
      bm25_score: 10.25,
      bm25_rank: 2,
      dense_score: 0.68,
      dense_rank: 1,
      lexical_rank: 2,
      rrf_score: 0.0311,
      fusion_rank: 3,
      cross_encoder_score: reranked ? 1.75 : null,
      final_rank: 2,
      selected: true,
      dropped_reason: null,
    },
    {
      chunk_id: "ORCL_000119312526277521_mdna_0076",
      document_id: "ORCL:0001193125-26-277521",
      citation: "ORCL 10-K, MD&A",
      text_preview: "Our cloud and software business represented 87% of our total revenues.",
      ticker: "ORCL",
      section: "mdna",
      filing_date: "2026-06-22",
      bm25_score: 9.5,
      bm25_rank: 4,
      dense_score: 0.64,
      dense_rank: 3,
      lexical_rank: 4,
      rrf_score: 0.0295,
      fusion_rank: 2,
      cross_encoder_score: reranked ? -3.5 : null,
      final_rank: 3,
      selected: true,
      dropped_reason: null,
    },
    {
      chunk_id: "INTC_000005086326000011_risk_factors_0024",
      document_id: "INTC:0000050863-26-000011",
      citation: "INTC 10-K, Risk Factors",
      text_preview: "We depend upon a complex global supply chain.",
      ticker: "INTC",
      section: "risk_factors",
      filing_date: "2026-01-23",
      bm25_score: 8.75,
      bm25_rank: 3,
      dense_score: 0.6,
      dense_rank: 5,
      lexical_rank: 3,
      rrf_score: 0.0288,
      fusion_rank: 4,
      cross_encoder_score: reranked ? -8.5 : null,
      final_rank: 4,
      selected: true,
      dropped_reason: null,
    },
    {
      chunk_id: "HD_000162828026019436_risk_factors_0030",
      document_id: "HD:0001628280-26-019436",
      citation: "HD 10-K, Risk Factors",
      text_preview: "Disruptions in our supply chain could adversely impact our business.",
      ticker: "HD",
      section: "risk_factors",
      filing_date: "2026-03-18",
      bm25_score: 7.4,
      bm25_rank: 6,
      dense_score: 0.55,
      dense_rank: 4,
      lexical_rank: 6,
      rrf_score: 0.0261,
      fusion_rank: 6,
      cross_encoder_score: reranked ? -12.25 : null,
      final_rank: null,
      selected: false,
      dropped_reason: "ranked_below_top_k",
    },
    {
      chunk_id: "AAPL_fixture_risk_1",
      document_id: FIXTURE_DOCUMENT_ID,
      citation: "AAPL 10-K, Risk Factors",
      text_preview: "The company faces competition risks in consumer markets.",
      ticker: "AAPL",
      section: "risk_factors",
      filing_date: "2025-10-31",
      bm25_score: 6.1,
      bm25_rank: 5,
      dense_score: null,
      dense_rank: null,
      lexical_rank: 5,
      rrf_score: 0.0247,
      fusion_rank: 5,
      cross_encoder_score: null,
      final_rank: null,
      selected: false,
      dropped_reason: null,
    },
  ];
  // A preset that never runs the cross-encoder cannot report a reranker
  // decision, so its unselected rows carry the preset-stage reason instead.
  return preset === "bm25" || preset === "dense"
    ? rows.map((row) => ({ ...row, dropped_reason: row.selected ? null : "not_in_selected_preset_stage" }))
    : rows;
}

export function retrievalFixtureResponse(body: Record<string, unknown>) {
  const question = String(body.question ?? "fixture question");
  const preset = typeof body.preset === "string" ? body.preset : "hybrid_rerank";
  const reranked = preset === "hybrid_rerank";
  const topK = typeof body.top_k === "number" ? body.top_k : 5;
  const candidatePool = typeof body.candidate_pool === "number" ? body.candidate_pool : 10;
  const ticker = typeof body.ticker === "string" && body.ticker ? body.ticker : null;
  const section = typeof body.section === "string" && body.section ? body.section : null;
  const documentId = typeof body.document_id === "string" && body.document_id ? body.document_id : null;
  const year = typeof body.year === "number" ? body.year : null;
  const candidates = retrievalFixtureCandidates(preset);

  return {
    query_interpretation: {
      original_question: question,
      retrieval_question: question,
      translation_method: "identity",
      detected_ticker: ticker,
      requested_periods: [],
      is_comparative: false,
    },
    trace: {
      trace_version: "retrieval-trace-v1",
      preset,
      query: question,
      filters: { ticker, section },
      top_k: topK,
      candidate_pool: candidatePool,
      models: {
        embedding: "fixture-embedding",
        reranker: reranked ? "cross-encoder/ms-marco-MiniLM-L-6-v2" : null,
        rrf_k: 60,
      },
      score_semantics: {
        applies_to_preset: preset,
        note: RETRIEVAL_SCORE_NOTE,
        families: retrievalFixtureFamilies(preset),
      },
      production_parity: {
        structured_promotion: "not_executed",
        lexical_ladder_merge_into_final: "not_executed",
        reason:
          "Inspection exposes the ranking stages only; production /query applies structured financial-row promotion and lexical-ladder merging on top.",
      },
      stages: [
        { name: "embedding", elapsed_ms: 12.5, status: "executed" },
        { name: "bm25", elapsed_ms: 3.25, status: "executed" },
        { name: "dense", elapsed_ms: 8.75, status: "executed" },
        { name: "lexical_ladder", elapsed_ms: 1.5, status: "executed" },
        {
          name: "reranker",
          elapsed_ms: reranked ? 48.75 : null,
          skipped: !reranked,
          status: reranked ? "executed" : "skipped",
          reason: reranked ? null : "The selected preset ranks without the cross-encoder.",
        },
        {
          name: "structured_promotion",
          elapsed_ms: null,
          status: "not_executed",
          reason: "Inspection does not apply production structured financial-row promotion.",
        },
      ],
      candidates,
      selected_chunk_ids: candidates.filter((candidate) => candidate.selected).map((candidate) => candidate.chunk_id),
      candidate_count: candidates.length,
      selected_count: candidates.filter((candidate) => candidate.selected).length,
      elapsed_ms: reranked ? 74.75 : 26,
      filter_values: { ticker, section, document_id: documentId, filing_date: null, year },
      scope: {
        documents: 50,
        eligible_document_ids: ticker ? [FIXTURE_DOCUMENT_ID] : ["AAPL:fixture", "MSFT:0000950170-25-100235", "ORCL:0001193125-26-277521"],
        truncated: false,
        reason: null,
      },
    },
  };
}

const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "Content-Type",
  "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
};

const PDF_FIXTURE_BYTES = Buffer.from("JVBERi0xLjMKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgaHR0cDovL3d3dy5yZXBvcnRsYWIuY29tCjEgMCBvYmoKPDwKL0YxIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhIC9FbmNvZGluZyAvV2luQW5zaUVuY29kaW5nIC9OYW1lIC9GMSAvU3VidHlwZSAvVHlwZTEgL1R5cGUgL0ZvbnQKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDcgMCBSIC9NZWRpYUJveCBbIDAgMCA2MTIgNzkyIF0gL1BhcmVudCA2IDAgUiAvUmVzb3VyY2VzIDw8Ci9Gb250IDEgMCBSIC9Qcm9jU2V0IFsgL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSSBdCj4+IC9Sb3RhdGUgMCAvVHJhbnMgPDwKCj4+IAogIC9UeXBlIC9QYWdlCj4+CmVuZG9iago0IDAgb2JqCjw8Ci9QYWdlTW9kZSAvVXNlTm9uZSAvUGFnZXMgNiAwIFIgL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjUgMCBvYmoKPDwKL0F1dGhvciAoYW5vbnltb3VzKSAvQ3JlYXRpb25EYXRlIChEOjIwMjYwOTE0MDg1NDI3KzA3JzAwJykgL0NyZWF0b3IgKFJlcG9ydExhYiBQREYgTGlicmFyeSAtIHd3dy5yZXBvcnRsYWIuY29tKSAvS2V5d29yZHMgKCkgL01vZERhdGUgKEQ6MjAyNjA5MTQwODU0MjcrMDcnMDAnKSAvUHJvZHVjZXIgKFJlcG9ydExhYiBQREYgTGlicmFyeSAtIHd3dy5yZXBvcnRsYWIuY29tKSAKICAvU3ViamVjdCAodW5zcGVjaWZpZWQpIC9UaXRsZSAoUERGLmpzIGZpeHR1cmUpIC9UcmFwcGVkIC9GYWxzZQo+PgplbmRvYmoKNiAwIG9iago8PAovQ291bnQgMSAvS2lkcyBbIDMgMCBSIF0gL1R5cGUgL1BhZ2VzCj4+CmVuZG9iago3IDAgb2JqCjw8Ci9GaWx0ZXIgWyAvQVNDSUk4NURlY29kZSAvRmxhdGVEZWNvZGUgXSAvTGVuZ3RoIDIwMQo+PgpzdHJlYW0KR2FyVzFZbXVAPidMZDVbaWY8O1NabHVCSzstWShcaEBESTRMX1gpZT5DdWpmVWhYRW9uKWJ0ayUtSXEtZHR1X0IhVlYxaC4zS243Sl1ROltGTjBIKzBAKGpyZGQ8KlJPKCc/M0EwP05ETShMZShcQW1XLFU9IyNVMypxMlNUW2hoYDdAWDVALlgjX0g+bz9YXG1gSWBAVy8/Ii4qLUJRQEwiIWQvY3V0I2wldSkqYEVcLk5XWiQwSjpsQy0yVEBqRV4yKWFJXn4+ZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgOAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwNzMgMDAwMDAgbiAKMDAwMDAwMDEwNCAwMDAwMCBuIAowMDAwMDAwMjExIDAwMDAwIG4gCjAwMDAwMDA0MDQgMDAwMDAgbiAKMDAwMDAwMDQ3MiAwMDAwMCBuIAowMDAwMDAwNzc0IDAwMDAwIG4gCjAwMDAwMDA4MzMgMDAwMDAgbiAKdHJhaWxlcgo8PAovSUQgCls8YzI5Yzg4OWQ4Yjg0ZDYxZWE3ZmQ4YjJmZDU4Y2U1NDE+PGMyOWM4ODlkOGI4NGQ2MWVhN2ZkOGIyZmQ1OGNlNTQxPl0KJSBSZXBvcnRMYWIgZ2VuZXJhdGVkIFBERiBkb2N1bWVudCAtLSBkaWdlc3QgKGh0dHA6Ly93d3cucmVwb3J0bGFiLmNvbSkKCi9JbmZvIDUgMCBSCi9Sb290IDQgMCBSCi9TaXplIDgKPj4Kc3RhcnR4cmVmCjExMjQKJSVFT0YK", "base64");
const FIXTURE_DOCUMENT_ID = "AAPL:fixture";
const FIXTURE_SOURCE_DOCUMENT_ID = "fixture-source";
const FIXTURE_SOURCE_SET_REVISION = "fixture-source-set-revision";
const FIXTURE_DOCUMENT_REVISION = "fixture-document-revision";
const FIXTURE_RISK_TEXT = "The company faces competition risks in consumer markets worldwide, including aggressive pricing pressure from competitors.";
const RECONCILIATION_NET_SALES_TEXT = "Total net sales were $391,035 million in fiscal 2024 and $416,161 million in fiscal 2025.";
const FIXTURE_NORMALIZED_TEXT = `${FIXTURE_RISK_TEXT}\n\n${RECONCILIATION_NET_SALES_TEXT}`;
const FIXTURE_SOURCE_CONTENT_HASH = createHash("sha256").update(FIXTURE_NORMALIZED_TEXT).digest("hex");
const FIXTURE_RISK_CHUNK_HASH = createHash("sha256").update(FIXTURE_RISK_TEXT).digest("hex");
const RECONCILIATION_NET_SALES_CHUNK_HASH = createHash("sha256").update(RECONCILIATION_NET_SALES_TEXT).digest("hex");
const PDF_FIXTURE_ARTIFACT_KEY = "fixture-pdf-artifact";
const PDF_FIXTURE_REPRESENTATION_ID = `derived_pdf:${PDF_FIXTURE_ARTIFACT_KEY}`;
const PDF_FIXTURE_ARTIFACT_HASH = createHash("sha256").update(PDF_FIXTURE_BYTES).digest("hex");
const PDF_FIXTURE_MAPPING_MANIFEST_ID = `mapping:${PDF_FIXTURE_ARTIFACT_KEY}`;
const PDF_FIXTURE_REASON = "Fixture-only derived PDF artifact is available for the current source revision; no source-to-PDF evidence mapping is admitted.";

function fixturePdfReaderAvailability(enabled: boolean) {
  if (!enabled) {
    return {
      kind: "pdf",
      status: "unavailable",
      reason_code: "pdf_representation_unavailable",
      reason: "PDF is not available in the current corpus.",
    };
  }
  return {
    kind: "pdf",
    status: "available",
    reason_code: "pdf_available",
    reason: PDF_FIXTURE_REASON,
    coverage_status: "unknown",
    coverage_reason: PDF_FIXTURE_REASON,
    coverage_reason_code: "pdf_available",
    representation_id: PDF_FIXTURE_REPRESENTATION_ID,
    representation_type: "DERIVED_PDF",
    page_semantics: "generated_representation_pages",
    artifact_key: PDF_FIXTURE_ARTIFACT_KEY,
    artifact_hash: PDF_FIXTURE_ARTIFACT_HASH,
    source_content_hash: FIXTURE_SOURCE_CONTENT_HASH,
    page_count: 1,
    mapping_status: "unavailable",
  };
}

function fixtureEvidenceForChunk(chunkId: string | null) {
  if (chunkId === "AAPL_fixture_net_sales_0") {
    const start = FIXTURE_NORMALIZED_TEXT.indexOf(RECONCILIATION_NET_SALES_TEXT);
    return {
      chunkId,
      chunkTextHash: RECONCILIATION_NET_SALES_CHUNK_HASH,
      blockId: "fixture-net-sales",
      blockIndex: 2,
      text: RECONCILIATION_NET_SALES_TEXT,
      normalizedStart: start,
      normalizedEnd: start + RECONCILIATION_NET_SALES_TEXT.length,
    };
  }
  return {
    chunkId: "AAPL_test_risk_factors_0",
    chunkTextHash: FIXTURE_RISK_CHUNK_HASH,
    blockId: "fixture-paragraph",
    blockIndex: 1,
    text: FIXTURE_RISK_TEXT,
    normalizedStart: 0,
    normalizedEnd: FIXTURE_RISK_TEXT.length,
  };
}

function sseEvent(type: string, data: unknown): string {
  return `data: ${JSON.stringify({ type, data })}\n\n`;
}

export const SAMPLE_SOURCES = [
  {
    citation: "AAPL 10-K (filed 2025-10-31), Section: Risk Factors",
    score: 0.8123,
    text_preview: "The company faces competition risks in consumer markets.",
    text: FIXTURE_RISK_TEXT,
    chunk_id: "AAPL_test_risk_factors_0",
    document_id: "AAPL:fixture",
    ticker: "AAPL",
    section: "risk_factors",
    filing_date: "2025-10-31",
    report_date: "2025-09-27",
    chunk_index: 1,
    chunk_text_hash: FIXTURE_RISK_CHUNK_HASH,
    source_url: "https://www.sec.gov/Archives/edgar/data/1/fixture.htm",
    score_kind: "retrieval",
  },
  {
    citation: "MSFT 10-K (filed 2025-07-30), Section: MDNA",
    score: 0.7455,
    text_preview: "Microsoft Cloud revenue increased 23% to $168.9 billion.",
    text: "Microsoft Cloud revenue increased 23% to $168.9 billion driven by Azure growth across all customer segments this fiscal year.",
    chunk_id: "MSFT_test_mdna_0",
    document_id: "MSFT:fixture",
    ticker: "MSFT",
    section: "mdna",
    filing_date: "2025-07-30",
    report_date: "2025-06-30",
    chunk_index: 1,
    source_url: "https://www.sec.gov/Archives/edgar/data/2/fixture.htm",
    score_kind: "retrieval",
  },
];

export const LONG_ANSWER = [
  "Apple's filing says the company faces competition risks in consumer markets, including aggressive pricing pressure from competitors [Source 1].",
  "",
  "The cited evidence is the retrieved AAPL Risk Factors excerpt [Source 1].",
].join("\n");

/**
 * The visual receipt asks a net-sales question. Keep this answer/source pair
 * separate from SAMPLE_SOURCES, whose risk and cross-company examples cover
 * other browser journeys.
 */
export const RECONCILIATION_SOURCES = [
  {
    citation: "AAPL 10-K (filed 2025-10-31), Section: Financial Statements",
    score: 0.8123,
    text_preview: RECONCILIATION_NET_SALES_TEXT,
    text: RECONCILIATION_NET_SALES_TEXT,
    chunk_id: "AAPL_fixture_net_sales_0",
    document_id: FIXTURE_DOCUMENT_ID,
    ticker: "AAPL",
    section: "financial_statements",
    filing_date: "2025-10-31",
    report_date: "2025-09-27",
    chunk_index: 2,
    chunk_text_hash: RECONCILIATION_NET_SALES_CHUNK_HASH,
    source_url: "https://www.sec.gov/Archives/edgar/data/1/fixture.htm",
    score_kind: "retrieval",
  },
  SAMPLE_SOURCES[1],
];

export const RECONCILIATION_NET_SALES_ANSWER = [
  `${RECONCILIATION_NET_SALES_TEXT} [Source 1].`,
  "",
  "| Metric | FY2024 | FY2025 |",
  "| --- | --- | --- |",
  "| Total net sales | 391,035 | 416,161 |",
].join("\n");

/**
 * Opt-in catalog dataset for the Documents workspace. The default single-row
 * `/documents` fixture stays as it is so other journeys keep their exact
 * expectations; a test that needs facets, sorting and pagination passes
 * `catalog: true`.
 *
 * The form type is deliberately absent here for the same reason API-003
 * publishes it as unknown: no stored filing artifact records one.
 */
export interface CatalogRow {
  document_id: string;
  ticker: string;
  filing_date: string;
  accession_number: string;
  sections: readonly string[];
  chunk_count: number;
  source_url: string;
}

/** The single document every non-catalog journey already expects. */
export const DEFAULT_CATALOG_DOCUMENT: CatalogRow = {
  document_id: "AAPL:fixture",
  ticker: "AAPL",
  filing_date: "2025-10-31",
  accession_number: "fixture-accession",
  sections: ["financial_statements"],
  chunk_count: 1,
  source_url: "https://www.sec.gov/Archives/fixture",
};

export const CATALOG_FIXTURE_DOCUMENTS: readonly CatalogRow[] = [
  { document_id: "AAPL:0000320193-24-000123", ticker: "AAPL", filing_date: "2024-11-01", accession_number: "0000320193-24-000123", sections: ["business", "risk_factors", "mdna", "financial_statements"], chunk_count: 1842, source_url: "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm" },
  { document_id: "MSFT:0000950170-24-087843", ticker: "MSFT", filing_date: "2024-07-30", accession_number: "0000950170-24-087843", sections: ["business", "risk_factors", "mdna"], chunk_count: 2156, source_url: "https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm" },
  { document_id: "NVDA:0001045810-24-000029", ticker: "NVDA", filing_date: "2024-02-21", accession_number: "0001045810-24-000029", sections: ["business", "mdna", "financial_statements"], chunk_count: 1421, source_url: "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm" },
  { document_id: "GOOGL:0001652044-24-000022", ticker: "GOOGL", filing_date: "2024-01-31", accession_number: "0001652044-24-000022", sections: ["business", "risk_factors", "financial_statements"], chunk_count: 1980, source_url: "https://www.sec.gov/Archives/edgar/data/1652044/000165204424000022/goog-20231231.htm" },
  { document_id: "AMZN:0001018724-24-000008", ticker: "AMZN", filing_date: "2024-02-02", accession_number: "0001018724-24-000008", sections: ["business", "risk_factors", "financial_statements"], chunk_count: 2341, source_url: "https://www.sec.gov/Archives/edgar/data/1018724/000101872424000008/amzn-20231231.htm" },
  { document_id: "TSLA:0001318605-24-000033", ticker: "TSLA", filing_date: "2024-01-26", accession_number: "0001318605-24-000033", sections: ["business", "mdna"], chunk_count: 2018, source_url: "https://www.sec.gov/Archives/edgar/data/1318605/000131860524000033/tsla-20231231.htm" },
  { document_id: "BRK-A:0001081316-24-000012", ticker: "BRK-A", filing_date: "2024-02-24", accession_number: "0001081316-24-000012", sections: ["business", "risk_factors"], chunk_count: 1432, source_url: "https://www.sec.gov/Archives/edgar/data/1081316/000108131624000012/brka-20231231.htm" },
  { document_id: "JPM:0000019617-24-000123", ticker: "JPM", filing_date: "2024-02-16", accession_number: "0000019617-24-000123", sections: ["business", "risk_factors", "financial_statements"], chunk_count: 1287, source_url: "https://www.sec.gov/Archives/edgar/data/19617/000001961724000123/jpm-20231231.htm" },
  { document_id: "AAPL:0000320193-25-000079", ticker: "AAPL", filing_date: "2025-10-31", accession_number: "0000320193-25-000079", sections: ["business", "risk_factors", "financial_statements"], chunk_count: 1911, source_url: "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm" },
  { document_id: "MSFT:0000950170-25-100123", ticker: "MSFT", filing_date: "2025-07-30", accession_number: "0000950170-25-100123", sections: ["business", "mdna"], chunk_count: 2204, source_url: "https://www.sec.gov/Archives/edgar/data/789019/000095017025100123/msft-20250630.htm" },
  { document_id: "NVDA:0001045810-25-000020", ticker: "NVDA", filing_date: "2025-02-26", accession_number: "0001045810-25-000020", sections: ["business", "risk_factors", "mdna"], chunk_count: 1544, source_url: "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000020/nvda-20250126.htm" },
  { document_id: "AMZN:0001018724-25-000007", ticker: "AMZN", filing_date: "2025-02-07", accession_number: "0001018724-25-000007", sections: ["business", "financial_statements"], chunk_count: 2402, source_url: "https://www.sec.gov/Archives/edgar/data/1018724/000101872425000007/amzn-20241231.htm" },
];

/** The form-type state API-003 publishes while no artifact records one. */
const FILING_TYPE_UNAVAILABLE_REASON = "Stored filing artifacts record no per-filing form type.";

function catalogFilingYear(row: CatalogRow): number | null {
  const year = Number(row.filing_date.slice(0, 4));
  return Number.isFinite(year) ? year : null;
}

function catalogRowMatches(
  row: CatalogRow,
  filters: { ticker: string | null; section: string | null; year: number | null; search: string | null },
): boolean {
  if (filters.ticker && row.ticker !== filters.ticker) return false;
  if (filters.section && !row.sections.includes(filters.section)) return false;
  if (filters.year && catalogFilingYear(row) !== filters.year) return false;
  if (filters.search) {
    const haystack = `${row.ticker} ${row.filing_date} ${row.accession_number} ${row.document_id}`.toLowerCase();
    if (!haystack.includes(filters.search.toLowerCase())) return false;
  }
  return true;
}

/** Serve the API-003 catalog routes for the rows a test installed. */
function catalogResponseFor(
  url: URL,
  rows: readonly CatalogRow[],
): { status: number; body: unknown } | null {
  const path = url.pathname;
  const filters = {
    ticker: url.searchParams.get("ticker"),
    section: url.searchParams.get("section"),
    year: url.searchParams.get("year") ? Number(url.searchParams.get("year")) : null,
    search: url.searchParams.get("search"),
  };

  if (path === "/documents/stats") {
    const years = rows.map(catalogFilingYear).filter((year): year is number => year != null);
    return {
      status: 200,
      body: {
        generated_at: "2025-11-02T00:00:00Z",
        documents: rows.length,
        companies: new Set(rows.map((row) => row.ticker)).size,
        chunks: rows.reduce((sum, row) => sum + row.chunk_count, 0),
        configured_companies: 40,
        configured_companies_without_documents: ["ZZZZ"],
        configured_companies_with_documents: ["AAPL"],
        filing_dates: {
          availability: "recorded",
          reason: null,
          earliest: Math.min(...years),
          latest: Math.max(...years),
          documents_without_value: 0,
        },
        report_dates: { availability: "unknown", reason: "No loaded document records a report date.", documents_with_value: 0 },
        sections: {
          availability: "recorded",
          reason: null,
          documents_without_value: 0,
          values: [...new Set(rows.flatMap((row) => [...row.sections]))].sort().map((value) => ({
            value,
            count: rows.filter((row) => row.sections.includes(value)).length,
          })),
        },
        filing_type: { availability: "unknown", reason: FILING_TYPE_UNAVAILABLE_REASON, value: null },
      },
    };
  }

  if (path === "/documents/facets") {
    // API-003's documented basis: every facet counts the applied filters
    // except its own dimension.
    const facet = (dimension: "company" | "year" | "section") => {
      const scoped = rows.filter((row) =>
        catalogRowMatches(row, {
          ticker: dimension === "company" ? null : filters.ticker,
          section: dimension === "section" ? null : filters.section,
          year: dimension === "year" ? null : filters.year,
          search: filters.search,
        }),
      );
      const values = dimension === "company"
        ? [...new Set(scoped.map((row) => row.ticker))].sort().map((ticker) => ({ value: ticker, count: scoped.filter((row) => row.ticker === ticker).length }))
        : dimension === "year"
          ? [...new Set(scoped.map(catalogFilingYear).filter((year): year is number => year != null))]
              .sort((left, right) => right - left)
              .map((year) => ({ value: year, count: scoped.filter((row) => catalogFilingYear(row) === year).length }))
          : [...new Set(scoped.flatMap((row) => [...row.sections]))]
              .sort()
              .map((section) => ({ value: section, count: scoped.filter((row) => row.sections.includes(section)).length }));
      return { dimension, availability: "recorded", reason: null, values };
    };
    return {
      status: 200,
      body: {
        generated_at: "2025-11-02T00:00:00Z",
        count_basis: "all_filters_except_own_dimension",
        scope: { ...filters, filing_date: null, documents: rows.filter((row) => catalogRowMatches(row, filters)).length },
        facets: [facet("company"), facet("section"), facet("year")],
      },
    };
  }

  return null;
}

/**
 * Install route mocks for the whole API surface and block every other
 * external request so tests stay hermetic.
 */
export async function installApiFixtures(
  page: Page,
  options: {
    history?: HistoryFixture;
    health?: Record<string, unknown>;
    streamDelayMs?: number;
    streamAnswers?: string[];
    streamSources?: Array<typeof SAMPLE_SOURCES>;
    pdf?: boolean;
    catalog?: boolean;
    /** Discovery ceiling state the mocked `/search` snapshot reports. */
    searchCeiling?: "bounded" | "complete";
    /** Answer `GET /search/{id}` with 410 so the expired state is reachable. */
    searchExpired?: boolean;
    /** Answer `GET /search/{id}` with 404 so the unknown-id state is reachable. */
    searchMissing?: boolean;
    /** A mutable DATA-003 collections workspace for the UI-008 surfaces. */
    collections?: CollectionsFixtureState;
  } = {},
): Promise<void> {
  const history: HistoryFixture = options.history ?? {
    session_id: "session-test",
    turns: [],
    context: { status: "missing", retained_turns: 0, ttl_remaining_seconds: 0 },
  };
  let streamRequestIndex = 0;
  /** Snapshots created by this test's POSTs, so a GET pages the same scope. */
  const searchSnapshots = new Map<string, Record<string, unknown>>();

  // Playwright matches routes in reverse registration order, so the
  // catch-all guard must be registered FIRST and the specific API mock
  // LAST.
  // Block every other outbound request so the tests stay hermetic. Static
  // assets such as Google Fonts are aborted silently — the page falls back
  // to system fonts and no provider or backend is ever reached.
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (
      url.startsWith("http://localhost:4173") ||
      url.startsWith("http://127.0.0.1:4173")
    ) {
      await route.continue();
      return;
    }
    await route.abort();
  });

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    const decodedPath = decodeURIComponent(path);

    if (method === "OPTIONS") {
      await route.fulfill({ status: 204, headers: CORS_HEADERS });
      return;
    }

    if (decodedPath === "/models" && method === "GET") {
      const role = url.searchParams.get("role");
      const items = role
        ? MODEL_REGISTRY_FIXTURE.filter((item) => item.role === role)
        : MODEL_REGISTRY_FIXTURE;
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({ items, total: items.length }),
      });
      return;
    }

    const modelTestMatch = decodedPath.match(/^\/models\/(generator|embedding|reranker)\/tests$/);
    if (modelTestMatch && method === "POST") {
      const modelId = modelTestMatch[1];
      const body = (request.postDataJSON() ?? {}) as Record<string, unknown>;
      if (body.test_type !== "runtime_identity") {
        await route.fulfill({
          status: 422,
          headers: { ...CORS_HEADERS, "content-type": "application/json" },
          body: JSON.stringify({ detail: "Only runtime_identity is supported" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          model_id: modelId,
          test_type: "runtime_identity",
          result: "passed",
          provider_executed: false,
          checks: [
            { id: "configured_identity", status: "passed", reason: null },
            { id: "runtime_identity", status: "passed", reason: null },
          ],
        }),
      });
      return;
    }

    if (decodedPath === "/datasets" && method === "GET") {
      const kind = url.searchParams.get("kind");
      const items = kind
        ? DATASET_REGISTRY_FIXTURE.filter((item) => item.kind === kind)
        : DATASET_REGISTRY_FIXTURE;
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({ items, total: items.length }),
      });
      return;
    }

    const datasetDetailMatch = decodedPath.match(/^\/datasets\/([^/]+)$/);
    if (datasetDetailMatch && method === "GET") {
      const detail = DATASET_DETAIL_FIXTURES[datasetDetailMatch[1]];
      await route.fulfill({
        status: detail ? 200 : 404,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify(detail ?? { detail: "Dataset registry entry not found" }),
      });
      return;
    }

    if (path.startsWith("/collections")) {
      await handleCollectionsFixture(route, method, path, url, options.collections);
      return;
    }

    if (path === "/health") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify(
          options.health ?? {
            status: "ok",
            pipeline_ready: true,
            memory: { active_sessions: 1, total_turns: 2 },
            corpus: { searchable_company_count: 50, indexed_chunk_count: 10053 },
          },
        ),
      });
      return;
    }

    if (path === "/supported-tickers") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          tickers: ["AAPL", "MSFT", "AMZN"],
          sections: [
            "business",
            "risk_factors",
            "mdna",
            "financial_statements",
            "financial_table",
          ],
        }),
      });
      return;
    }

    // Discovery search (API-004). The snapshot is created once per POST and
    // paged from memory afterwards, so a browser test can prove that paging
    // never re-runs the search.
    if (decodedPath === "/search" && method === "POST") {
      const body = (request.postDataJSON() ?? {}) as Record<string, unknown>;
      const query = String(body.query ?? "").trim();
      if (query.length < 2 || query.length > 200) {
        await route.fulfill({
          status: 422,
          headers: { ...CORS_HEADERS, "content-type": "application/json" },
          body: JSON.stringify({ detail: "Query must be between 2 and 200 characters" }),
        });
        return;
      }
      const pageSize = typeof body.page_size === "number" ? body.page_size : 20;
      const snapshot = searchFixtureSnapshot(body, { ceiling: options.searchCeiling ?? "bounded" }, 1, pageSize);
      searchSnapshots.set(String(snapshot.search_id), body);
      await route.fulfill({ status: 200, headers: { ...CORS_HEADERS, "content-type": "application/json" }, body: JSON.stringify(snapshot) });
      return;
    }

    if (decodedPath.startsWith("/search/") && method === "GET") {
      if (options.searchExpired) {
        await route.fulfill({
          status: 410,
          headers: { ...CORS_HEADERS, "content-type": "application/json" },
          body: JSON.stringify({ detail: "Discovery snapshot expired; run the search again" }),
        });
        return;
      }
      const searchId = decodeURIComponent(decodedPath.slice("/search/".length));
      const stored = options.searchMissing ? undefined : searchSnapshots.get(searchId);
      if (!stored) {
        await route.fulfill({
          status: 404,
          headers: { ...CORS_HEADERS, "content-type": "application/json" },
          body: JSON.stringify({ detail: "Discovery snapshot not found" }),
        });
        return;
      }
      // Page the stored snapshot: the same scope and grouping, a new page.
      const page = Math.max(1, Number(url.searchParams.get("page") ?? 1));
      const pageSize = Math.max(1, Number(url.searchParams.get("page_size") ?? stored.page_size ?? 20));
      const snapshot = searchFixtureSnapshot(
        { ...stored, page_size: pageSize },
        { ceiling: options.searchCeiling ?? "bounded" },
        page,
        pageSize,
      );
      await route.fulfill({ status: 200, headers: { ...CORS_HEADERS, "content-type": "application/json" }, body: JSON.stringify(snapshot) });
      return;
    }

    // The API-003 routes answer for every journey; only the richer multi-row
    // dataset is opt-in.
    const catalogRows = options.catalog ? CATALOG_FIXTURE_DOCUMENTS : [DEFAULT_CATALOG_DOCUMENT];
    const catalogResponse = catalogResponseFor(url, catalogRows);
    if (catalogResponse) {
      await route.fulfill({ status: catalogResponse.status, headers: { ...CORS_HEADERS, "content-type": "application/json" }, body: JSON.stringify(catalogResponse.body) });
      return;
    }
    if (options.catalog && decodedPath === "/documents") {
      const filters = {
        ticker: url.searchParams.get("ticker"),
        section: url.searchParams.get("section"),
        year: url.searchParams.get("year") ? Number(url.searchParams.get("year")) : null,
        search: url.searchParams.get("search"),
      };
      const sort = url.searchParams.get("sort") ?? "filing_date";
      const direction = url.searchParams.get("direction") === "asc" ? 1 : -1;
      const page = Math.max(1, Number(url.searchParams.get("page") ?? 1));
      const pageSize = Math.max(1, Number(url.searchParams.get("page_size") ?? 10));
      const matched = CATALOG_FIXTURE_DOCUMENTS.filter((row) => catalogRowMatches(row, filters));
      const sorted = [...matched].sort((left, right) => {
        if (sort === "chunk_count") return (left.chunk_count - right.chunk_count) * direction;
        if (sort === "ticker") return left.ticker.localeCompare(right.ticker) * direction;
        if (sort === "document_id") return left.document_id.localeCompare(right.document_id) * direction;
        return left.filing_date.localeCompare(right.filing_date) * direction;
      });
      const start = (page - 1) * pageSize;
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          items: sorted.slice(start, start + pageSize).map((row) => ({ ...row, sections: [...row.sections] })),
          total: sorted.length,
          page,
          page_size: pageSize,
          sort,
          direction: url.searchParams.get("direction") ?? "desc",
        }),
      });
      return;
    }

    if (options.pdf && decodedPath === "/documents/AAPL:fixture/pdf") {
      const manifest = {
        schema_version: "sec-pdf-manifest-v2",
        representation_id: PDF_FIXTURE_REPRESENTATION_ID,
        representation_type: "DERIVED_PDF",
        page_semantics: "generated_representation_pages",
        artifact_status: "available",
        document_id: FIXTURE_DOCUMENT_ID,
        source_document_id: FIXTURE_SOURCE_DOCUMENT_ID,
        source_set_revision: FIXTURE_SOURCE_SET_REVISION,
        document_revision: FIXTURE_DOCUMENT_REVISION,
        source_content_hash: FIXTURE_SOURCE_CONTENT_HASH,
        artifact_key: PDF_FIXTURE_ARTIFACT_KEY,
        artifact_hash: PDF_FIXTURE_ARTIFACT_HASH,
        artifact_size_bytes: PDF_FIXTURE_BYTES.length,
        page_count: 1,
        renderer: { renderer: "fixture", renderer_version: "fixture", template_version: "fixture", page_size: "A4", orientation: "portrait", margins_pt: { top: 56, bottom: 56, left: 56, right: 56 }, print_background: true, locale: "en-US", font_family: "Helvetica" },
        generated_at: "2026-09-14T00:00:00Z",
        mapping_manifest_id: PDF_FIXTURE_MAPPING_MANIFEST_ID,
        mapping_status: "unavailable",
        mapping_entry_count: 2,
        reason: PDF_FIXTURE_REASON,
      };
      await route.fulfill({ status: 200, headers: { ...CORS_HEADERS, "content-type": "application/json" }, body: JSON.stringify(manifest) });
      return;
    }
    if (options.pdf && decodedPath === "/documents/AAPL:fixture/pdf/content") {
      await route.fulfill({ status: 200, headers: { ...CORS_HEADERS, "content-type": "application/pdf", "content-disposition": "inline; filename=fixture_generated.pdf" }, body: PDF_FIXTURE_BYTES });
      return;
    }
    if (options.pdf && decodedPath === "/documents/AAPL:fixture/pdf/mapping/location") {
      const chunkId = url.searchParams.get("chunk_id") ?? "";
      const chunkTextHash = url.searchParams.get("chunk_text_hash") ?? "";
      const sourceIdentityMatches = url.searchParams.get("source_document_id") === FIXTURE_SOURCE_DOCUMENT_ID
        && url.searchParams.get("source_set_revision") === FIXTURE_SOURCE_SET_REVISION
        && url.searchParams.get("document_revision") === FIXTURE_DOCUMENT_REVISION;
      const base = {
        schema_version: "sec-pdf-evidence-location-v1",
        document_id: FIXTURE_DOCUMENT_ID,
        source_document_id: FIXTURE_SOURCE_DOCUMENT_ID,
        source_set_revision: FIXTURE_SOURCE_SET_REVISION,
        document_revision: FIXTURE_DOCUMENT_REVISION,
        source_content_hash: FIXTURE_SOURCE_CONTENT_HASH,
        representation_id: PDF_FIXTURE_REPRESENTATION_ID,
        artifact_key: PDF_FIXTURE_ARTIFACT_KEY,
        artifact_hash: PDF_FIXTURE_ARTIFACT_HASH,
        mapping_manifest_id: PDF_FIXTURE_MAPPING_MANIFEST_ID,
        chunk_id: chunkId,
        chunk_text_hash: chunkTextHash,
      };
      const response = !sourceIdentityMatches
        ? {
            ...base,
            status: "stale",
            reason: "The selected source revision does not match the current PDF artifact.",
            match_count: 0,
            match_count_capped: false,
            entry_ids: [],
            rects: [],
          }
        : (chunkId === "AAPL_test_risk_factors_0" && chunkTextHash === FIXTURE_RISK_CHUNK_HASH)
          || (chunkId === "AAPL_fixture_net_sales_0" && chunkTextHash === RECONCILIATION_NET_SALES_CHUNK_HASH)
          ? {
              ...base,
              // The source chunk is current, but this fixture does not admit
              // a complete source-to-PDF rectangle for either source block.
              status: "unavailable",
              reason: "The selected range has no complete PDF rectangle mapping.",
              match_count: 0,
              match_count_capped: false,
              entry_ids: [],
              rects: [],
            }
            : {
                ...base,
                status: "stale",
                reason: "The indexed chunk changed.",
                match_count: 0,
                match_count_capped: false,
                entry_ids: [],
                rects: [],
              };
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify(response),
      });
      return;
    }
    if (options.pdf && decodedPath === "/documents/AAPL:fixture/pdf/mapping") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          schema_version: "sec-pdf-mapping-v2",
          mapping_manifest_id: PDF_FIXTURE_MAPPING_MANIFEST_ID,
          representation_id: PDF_FIXTURE_REPRESENTATION_ID,
          document_id: FIXTURE_DOCUMENT_ID,
          source_document_id: FIXTURE_SOURCE_DOCUMENT_ID,
          source_content_hash: FIXTURE_SOURCE_CONTENT_HASH,
          artifact_key: PDF_FIXTURE_ARTIFACT_KEY,
          artifact_hash: PDF_FIXTURE_ARTIFACT_HASH,
          source_set_revision: FIXTURE_SOURCE_SET_REVISION,
          document_revision: FIXTURE_DOCUMENT_REVISION,
          entries: [
            {
              block_id: "normalized:0",
              block_index: 0,
              block_kind: "paragraph",
              char_start: 0,
              char_end: FIXTURE_RISK_TEXT.length,
              text_preview: FIXTURE_RISK_TEXT,
              status: "unavailable",
              reason: "The block was not placed in the rendered artifact.",
              rects: [],
            },
            {
              block_id: "normalized:1",
              block_index: 1,
              block_kind: "paragraph",
              char_start: FIXTURE_NORMALIZED_TEXT.indexOf(RECONCILIATION_NET_SALES_TEXT),
              char_end: FIXTURE_NORMALIZED_TEXT.length,
              text_preview: RECONCILIATION_NET_SALES_TEXT,
              status: "unavailable",
              reason: "The block was not placed in the rendered artifact.",
              rects: [],
            },
          ],
        }),
      });
      return;
    }
    if (!options.pdf && decodedPath === "/documents/AAPL:fixture/pdf") {
      await route.fulfill({
        status: 404,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({ detail: "Fixture PDF is disabled for this test." }),
      });
      return;
    }
    const disabledPdfManifest = decodedPath.match(/^\/documents\/([^/]+)\/pdf$/);
    if (!options.pdf && disabledPdfManifest) {
      await route.fulfill({
        status: 404,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({ detail: "Fixture PDF is disabled for this test." }),
      });
      return;
    }
    const unsupportedPdfManifest = decodedPath.match(/^\/documents\/([^/]+)\/pdf$/);
    if (options.pdf && unsupportedPdfManifest && unsupportedPdfManifest[1] !== "AAPL:fixture") {
      await route.fulfill({
        status: 404,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({ detail: "Fixture PDF is only available for AAPL:fixture." }),
      });
      return;
    }
    const nonAppleReader = decodedPath.match(/^\/documents\/([^/]+)\/reader$/);
    if (nonAppleReader && nonAppleReader[1] !== "AAPL:fixture") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          schema_version: "sec-reader-v4",
          document_id: nonAppleReader[1],
          status: "unavailable",
          reason_code: "fixture_document_unavailable",
          reason: "This fixture intentionally covers source identity without a second reader corpus.",
          identity: { status: "unavailable", reason_code: "fixture_document_unavailable" },
          source_set_revision: "fixture-source-set-revision",
          sources: [],
          representations: [
            { kind: "structured", status: "unavailable", reason_code: "fixture_document_unavailable", reason: "Fixture document is unavailable." },
            { kind: "normalized_text", status: "unavailable", reason_code: "fixture_document_unavailable", reason: "Fixture document is unavailable." },
            { kind: "pdf", status: "unavailable", reason_code: "pdf_representation_unavailable", reason: "PDF is not available in the current corpus." },
          ],
        }),
      });
      return;
    }
    const nonAppleReaderSubpath = decodedPath.match(/^\/documents\/([^/]+)\/reader\/(outline|content|search)$/);
    if (nonAppleReaderSubpath && nonAppleReaderSubpath[1] !== "AAPL:fixture") {
      const documentId = nonAppleReaderSubpath[1];
      const kind = nonAppleReaderSubpath[2];
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify(kind === "outline"
          ? { document_id: documentId, source_document_id: "fixture-source", source_set_revision: "fixture-source-set-revision", document_revision: "fixture-document-revision", items: [], next_cursor: null, complete: true, limitations: [] }
          : kind === "content"
            ? { document_id: documentId, source_document_id: "fixture-source", source_set_revision: "fixture-source-set-revision", document_revision: "fixture-document-revision", blocks: [], previous_cursor: null, next_cursor: null, complete: true, limitations: [] }
            : { document_id: documentId, source_document_id: "fixture-source", source_set_revision: "fixture-source-set-revision", document_revision: "fixture-document-revision", query: url.searchParams.get("q") ?? "", matches: [], total: 0, next_cursor: null, complete: true }),
      });
      return;
    }
    if (decodedPath === "/documents/AAPL:fixture/reader") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          schema_version: "sec-reader-v4",
          document_id: "AAPL:fixture",
          status: "available",
          reason_code: "available",
          reason: null,
          identity: {
            ticker: "AAPL",
            cik: 320193,
            accession_number: "0000320193-25-000079",
            filing_date: "2025-10-31",
            report_date: "2025-09-27",
            status: "verified",
            reason_code: "verified",
          },
          source_set_revision: "fixture-source-set-revision",
          sources: [{
            source_document_id: "fixture-source",
            role: "primary_filing",
            label: "Primary filing",
            status: "available",
            reason_code: "available",
            reason: null,
            canonical_url: "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.html",
            media_type: "text/html",
            document_revision: "fixture-document-revision",
            text_length: FIXTURE_NORMALIZED_TEXT.length,
          }],
          representations: [
            { kind: "normalized_text", status: "available", reason_code: "available", reason: null },
            { kind: "structured", status: "available", reason_code: "available", reason: null },
            fixturePdfReaderAvailability(Boolean(options.pdf)),
          ],
        }),
      });
      return;
    }

    if (decodedPath === "/documents/AAPL:fixture/reader/outline") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          document_id: "AAPL:fixture",
          source_document_id: "fixture-source",
          source_set_revision: "fixture-source-set-revision",
          document_revision: "fixture-document-revision",
          items: [{ block_id: "fixture-heading", label: "Risk factors", level: 1, anchor: "risk-factors" }],
          next_cursor: null,
          complete: true,
          limitations: [],
        }),
      });
      return;
    }

    if (decodedPath === "/documents/AAPL:fixture/reader/content") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          document_id: "AAPL:fixture",
          source_document_id: "fixture-source",
          source_set_revision: "fixture-source-set-revision",
          document_revision: "fixture-document-revision",
          blocks: [
            { block_id: "fixture-heading", kind: "heading", text: "Risk factors", runs: [], level: 1, anchor: "risk-factors", items: [], caption: null, columns: [], rows: [], source_text: "Risk factors" },
            { block_id: "fixture-paragraph", kind: "paragraph", text: FIXTURE_RISK_TEXT, runs: [{ text: FIXTURE_RISK_TEXT, emphasis: false, strong: false, superscript: false, subscript: false }], level: null, anchor: null, items: [], caption: null, columns: [], rows: [], source_text: FIXTURE_RISK_TEXT },
            { block_id: "fixture-net-sales", kind: "paragraph", text: RECONCILIATION_NET_SALES_TEXT, runs: [{ text: RECONCILIATION_NET_SALES_TEXT, emphasis: false, strong: false, superscript: false, subscript: false }], level: null, anchor: null, items: [], caption: null, columns: [], rows: [], source_text: RECONCILIATION_NET_SALES_TEXT },
            { block_id: "fixture-table", kind: "table", text: "", runs: [], level: null, anchor: null, items: [], caption: "Total net sales", columns: ["Metric", "FY2024", "FY2025"], rows: [[{ text: "Total net sales", rowspan: 1, colspan: 1, header: false }, { text: "391,035", rowspan: 1, colspan: 1, header: false }, { text: "416,161", rowspan: 1, colspan: 1, header: false }]], source_text: "Total net sales 391,035 416,161" },
          ],
          previous_cursor: null,
          next_cursor: null,
          complete: true,
          limitations: [],
        }),
      });
      return;
    }

    if (decodedPath === "/documents/AAPL:fixture/reader/search") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          document_id: "AAPL:fixture",
          source_document_id: "fixture-source",
          source_set_revision: "fixture-source-set-revision",
          document_revision: "fixture-document-revision",
          query: url.searchParams.get("q") ?? "competition",
          matches: [{ block_id: "fixture-paragraph", block_index: 1, start: 29, end: 40, quote: "competition risks in consumer markets" }],
          total: 1,
          next_cursor: null,
          complete: true,
        }),
      });
      return;
    }

    if (decodedPath === "/documents/AAPL:fixture/original") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          document_id: "AAPL:fixture",
          status: "available",
          reason: null,
          normalizer_version: "sec-viewer-text-v1",
          source_set_revision: "fixture-source-set-revision",
          sources: [{
            source_document_id: "fixture-source",
            role: "primary_filing",
            label: "Primary filing",
            status: "available",
            reason: null,
            document_revision: "fixture-document-revision",
            text_length: FIXTURE_NORMALIZED_TEXT.length,
          }],
        }),
      });
      return;
    }

    if (decodedPath === "/documents/AAPL:fixture/original/content") {
      const selectedEvidence = fixtureEvidenceForChunk(url.searchParams.get("chunk_id"));
      const isNetSalesEvidence = selectedEvidence.chunkId === "AAPL_fixture_net_sales_0";
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          document_id: "AAPL:fixture",
          source_document_id: "fixture-source",
          source_set_revision: "fixture-source-set-revision",
          document_revision: "fixture-document-revision",
          start: 0,
          end: FIXTURE_NORMALIZED_TEXT.length,
          total_length: FIXTURE_NORMALIZED_TEXT.length,
          previous_start: null,
          next_start: null,
          segments: [
            { text: FIXTURE_RISK_TEXT, evidence: !isNetSalesEvidence, search: false },
            { text: "\n\n", evidence: false, search: false },
            { text: RECONCILIATION_NET_SALES_TEXT, evidence: isNetSalesEvidence, search: false },
          ],
        }),
      });
      return;
    }

    if (decodedPath === "/documents/AAPL:fixture/original/search") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          document_id: "AAPL:fixture",
          source_document_id: "fixture-source",
          source_set_revision: "fixture-source-set-revision",
          document_revision: "fixture-document-revision",
          query: url.searchParams.get("q") ?? "competition",
          matches: [{ start: 20, end: 31, preview: "competition risks" }],
          next_cursor: null,
        }),
      });
      return;
    }

    if (decodedPath.startsWith("/chunks/") && decodedPath.endsWith("/original-location") && method === "GET") {
      const chunkId = decodedPath.slice("/chunks/".length, -"/original-location".length);
      const evidence = fixtureEvidenceForChunk(chunkId);
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          chunk_id: evidence.chunkId,
          chunk_text_hash: evidence.chunkTextHash,
          document_id: FIXTURE_DOCUMENT_ID,
          source_set_revision: FIXTURE_SOURCE_SET_REVISION,
          matcher_version: "sec-viewer-location-v1",
          status: "exact",
          reason: "Exact normalized-source correspondence verified.",
          match_count: 1,
          match_count_capped: false,
          location: { source_document_id: FIXTURE_SOURCE_DOCUMENT_ID, document_revision: FIXTURE_DOCUMENT_REVISION, method: "full_text_whitespace", start: evidence.normalizedStart, end: evidence.normalizedEnd },
        }),
      });
      return;
    }

    if (path === "/retrieval/inspect" && method === "POST") {
      const body = (request.postDataJSON() ?? {}) as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify(retrievalFixtureResponse(body)),
      });
      return;
    }

    if (path === "/documents") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          items: [{
            document_id: "AAPL:fixture",
            ticker: "AAPL",
            filing_date: "2025-10-31",
            accession_number: "fixture-accession",
            sections: ["financial_statements"],
            chunk_count: 1,
            source_url: "https://www.sec.gov/Archives/fixture",
          }],
          total: 1,
          page: 1,
          page_size: 12,
        }),
      });
      return;
    }

    if (decodedPath.startsWith("/chunks/") && decodedPath.endsWith("/reader-location") && method === "GET") {
      const chunkId = decodedPath.slice("/chunks/".length, -"/reader-location".length);
      const evidence = fixtureEvidenceForChunk(chunkId);
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          chunk_id: evidence.chunkId,
          chunk_text_hash: evidence.chunkTextHash,
          document_id: FIXTURE_DOCUMENT_ID,
          source_set_revision: FIXTURE_SOURCE_SET_REVISION,
          status: "exact",
          reason_code: "exact",
          reason: null,
          source_document_id: FIXTURE_SOURCE_DOCUMENT_ID,
          document_revision: FIXTURE_DOCUMENT_REVISION,
          representation_revision: "fixture-structured-revision",
          ranges: [{ block_id: evidence.blockId, block_index: evidence.blockIndex, kind: "paragraph", start: 0, end: evidence.text.length, method: "text_whitespace" }],
          match_count: 1,
          match_count_capped: false,
        }),
      });
      return;
    }

    if (decodedPath.startsWith("/chunks/") && method === "GET") {
      const chunkId = decodeURIComponent(path.slice("/chunks/".length));
      const source = SAMPLE_SOURCES.find((item) => item.chunk_id === chunkId)
        ?? RECONCILIATION_SOURCES.find((item) => item?.chunk_id === chunkId)
        ?? (chunkId === "AAPL_fixture_revenue_0"
        ? {
            ...SAMPLE_SOURCES[0],
            chunk_id: chunkId,
            citation: "AAPL 10-K, Financial Statements",
            text_preview: "Total revenue was reported in fiscal 2024.",
            text: "Total revenue was reported in fiscal 2024.",
            section: "financial_statements",
          }
        : undefined);
      if (!source) {
        await route.fulfill({
          status: 404,
          headers: { ...CORS_HEADERS, "content-type": "application/json" },
          body: JSON.stringify({ detail: "Chunk not found" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          ...source,
          document_id: source.document_id,
          accession_number: "fixture-accession",
          text_length: source.text.length,
        }),
      });
      return;
    }

    if (path.startsWith("/documents/") && path.endsWith("/chunks")) {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          items: [{
            chunk_id: "AAPL_fixture_revenue_0",
            ticker: "AAPL",
            section: "financial_statements",
            filing_date: "2025-10-31",
            accession_number: "fixture-accession",
            text_preview: "Total revenue was reported in fiscal 2024.",
            text_length: 47,
            source_url: "https://www.sec.gov/Archives/fixture",
          }],
          total: 1,
          page: 1,
          page_size: 8,
        }),
      });
      return;
    }

    if (path === "/system/info") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          api_version: "fixture",
          corpus: { searchable_company_count: 3, indexed_chunk_count: 1 },
          retrieval: {
            embedding_model: "fixture-embedding",
            reranker_model: "fixture-reranker",
            presets: ["bm25", "dense", "hybrid", "hybrid_rerank"],
            default: "hybrid_rerank",
          },
          build: { revision: "fixture" },
        }),
      });
      return;
    }

    if (path === "/evaluation/runs" && method === "GET") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 }),
      });
      return;
    }

    if (path === "/evaluation/metrics" && method === "GET") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          protocol: "native-evaluation",
          protocol_version: 1,
          capabilities: { provider_free: true, computes_judge_scores: false, requires_bound_judge_scores: true },
          items: nativeDefinitions(),
          total: 6,
        }),
      });
      return;
    }

    if (path.startsWith("/evaluation/runs/") && method === "GET") {
      await route.fulfill({
        status: 404,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({ detail: "Published evaluation was not found" }),
      });
      return;
    }

    if (path.startsWith("/session/") && path.endsWith("/history")) {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify(history),
      });
      return;
    }

    if (path === "/query/stream" && method === "POST") {
      const responseIndex = streamRequestIndex++;
      const answer = options.streamAnswers?.[responseIndex] ?? LONG_ANSWER;
      const sources = options.streamSources?.[responseIndex] ?? SAMPLE_SOURCES;
      const body =
        sseEvent("stage", {
          version: 1,
          request_id: "fixture-request-1",
          sequence: 1,
          stage_id: "query_preparation",
          status: "running",
        }) +
        sseEvent("stage", {
          version: 1,
          request_id: "fixture-request-1",
          sequence: 2,
          stage_id: "query_preparation",
          status: "success",
          elapsed_ms: 1.4,
        }) +
        sseEvent("stage", {
          version: 1,
          request_id: "fixture-request-1",
          sequence: 3,
          stage_id: "retrieval",
          status: "success",
          elapsed_ms: 8.2,
          counters: { source_count: 2 },
        }) +
        sseEvent("sources", sources) +
        sseEvent("token", answer) +
        sseEvent("done", {
          request_id: "fixture-request-1",
          request_status: "completed",
          execution: {
            request_id: "fixture-request-1",
            elapsed_ms: 24.8,
            stages: [
              { name: "query_preparation", elapsed_ms: 1.4, status: "completed" },
              { name: "retrieval", elapsed_ms: 8.2, status: "completed" },
            ],
          },
        });
      if (options.streamDelayMs) {
        await new Promise((resolve) => setTimeout(resolve, options.streamDelayMs));
      }
      await route.fulfill({
        status: 200,
        headers: {
          ...CORS_HEADERS,
          "content-type": "text/event-stream",
          "cache-control": "no-cache",
        },
        body,
      });
      return;
    }

    if (path === "/query/decomposed/stream" && method === "POST") {
      const body =
        sseEvent("stage", {
          version: 1,
          request_id: "fixture-comparison-1",
          sequence: 1,
          stage_id: "decomposition_plan",
          status: "success",
          elapsed_ms: 4.1,
        }) +
        sseEvent("stage", {
          version: 1,
          request_id: "fixture-comparison-1",
          sequence: 2,
          stage_id: "subquery_retrieval",
          status: "success",
          elapsed_ms: 11.5,
          counters: { subquery_count: 2, source_count: 4 },
        }) +
        sseEvent("stage", {
          version: 1,
          request_id: "fixture-comparison-1",
          sequence: 3,
          stage_id: "synthesis",
          status: "success",
          elapsed_ms: 7.8,
        }) +
        sseEvent("sources", SAMPLE_SOURCES) +
        sseEvent("token", "Apple services revenue grew while Microsoft Cloud revenue increased 23% to $168.9 billion [Source 1] [Source 2].") +
        sseEvent("done", {
          request_id: "fixture-comparison-1",
          request_status: "completed",
          model_used: "openai/gpt-oss-120b",
          was_decomposed: true,
          sub_queries: [
            { query: "Apple services revenue", ticker: "AAPL", section: "mdna", num_chunks: 2 },
            { query: "Microsoft Cloud revenue", ticker: "MSFT", section: "mdna", num_chunks: 2 },
          ],
          num_total_chunks: 4,
        });
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "text/event-stream", "cache-control": "no-cache" },
        body,
      });
      return;
    }

    if (path === "/query/decomposed" && method === "POST") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          answer: "Apple services revenue grew while Microsoft Cloud revenue increased 23% to $168.9 billion [Source 1] [Source 2].",
          model_used: "openai/gpt-oss-120b",
          was_decomposed: true,
          sub_queries: [
            { query: "Apple services revenue", ticker: "AAPL", section: "mdna", num_chunks: 2 },
            { query: "Microsoft Cloud revenue", ticker: "MSFT", section: "mdna", num_chunks: 2 },
          ],
          sources: SAMPLE_SOURCES,
          num_total_chunks: 4,
        }),
      });
      return;
    }

    throw new Error(`Unexpected API request in test: ${method} ${path}`);
  });
}

export async function askQuestion(page: Page, question: string): Promise<void> {
  const input = page.getByRole("textbox", { name: "Research question" });
  await expect(input).toBeVisible();
  await input.fill(question);
  await input.press("Enter");
}

export async function openLibrary(page: Page): Promise<void> {
  await page.getByRole("link", { name: /Collections/ }).click();
  // The reconstructed Library opens on evidence Collections for the target
  // master-detail workspace. Conversation-specific tests deliberately enter
  // its real Conversations tab rather than assuming both surfaces mount.
  await page.getByRole("tab", { name: /Conversations/i }).click();
  await expect(page.getByRole("searchbox", { name: "Search saved conversations" })).toBeVisible();
}

/* ====================================================================== *
 * DATA-003 collections fixture
 *
 * A small in-memory implementation of the protected collections API. It
 * enforces the same membership rules, revision preconditions and tombstone
 * semantics the real router does, so a UI test proves the page against the
 * contract rather than against a permissive stub. Every request is recorded
 * so a test can assert that browsing wrote nothing.
 * ====================================================================== */

export type CollectionsFixtureItemKind = "document" | "evidence" | "answer" | "note";

export interface CollectionsFixtureItem {
  item_id: string;
  collection_id: string;
  item_kind: CollectionsFixtureItemKind;
  citation: string;
  excerpt: string;
  reference: Record<string, unknown>;
  revision: number;
  created_at: string;
  updated_at: string;
  snapshot?: Record<string, unknown>;
}

export interface CollectionsFixtureNote {
  note_id: string;
  collection_id: string;
  text: string;
  revision: number;
  created_at: string;
  updated_at: string;
  evidence_ref?: Record<string, unknown>;
}

export interface CollectionsFixtureActivity {
  activity_id: string;
  collection_id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  occurred_at: string;
}

export interface CollectionsFixtureCollection {
  collection_id: string;
  name: string;
  description: string;
  tags: string[];
  favorite: boolean;
  private: boolean;
  revision: number;
  created_at: string;
  updated_at: string;
  items: CollectionsFixtureItem[];
  notes: CollectionsFixtureNote[];
  activity: CollectionsFixtureActivity[];
  /** Tombstoned collections answer 410 exactly like the real repository. */
  deleted?: boolean;
}

export interface CollectionsFixtureState {
  collections: CollectionsFixtureCollection[];
  /** Force a status for `GET /collections` (404 unavailable, 401, 403, 500). */
  listStatus?: number;
  /** Force one mutation's status, keyed by operation. */
  mutationStatus?: Partial<Record<
    "create" | "update" | "delete" | "add-item" | "delete-item" | "add-note" | "update-note" | "delete-note",
    number
  >>;
  /** Every request the page made, in order, with its decoded body. */
  requests: Array<{ method: string; path: string; body: unknown }>;
  /** Details the forced-status responses report. */
  detail?: string;
}

export function createCollectionsFixtureState(
  collections: Array<Partial<CollectionsFixtureCollection> & { collection_id: string; name: string }> = [],
): CollectionsFixtureState {
  return {
    collections: collections.map((entry) => ({
      description: "",
      tags: [],
      favorite: false,
      private: true,
      revision: 1,
      created_at: "2026-09-20T08:00:00Z",
      updated_at: "2026-09-22T10:00:00Z",
      items: [],
      notes: [],
      activity: [],
      ...entry,
    })),
    requests: [],
    detail: "Local workspace capability is unavailable",
  };
}

function collectionsPayload(entry: CollectionsFixtureCollection) {
  return {
    collection_id: entry.collection_id,
    name: entry.name,
    description: entry.description,
    tags: entry.tags,
    favorite: entry.favorite,
    private: entry.private,
    revision: entry.revision,
    created_at: entry.created_at,
    updated_at: entry.updated_at,
    item_count: entry.items.length,
  };
}

function collectionsReferenceIsValid(kind: CollectionsFixtureItemKind, reference: Record<string, unknown>): boolean {
  const has = (keys: string[]) => keys.some((key) => typeof reference[key] === "string" && (reference[key] as string).length > 0);
  if (kind === "document") return has(["document_id"]);
  if (kind === "answer") return has(["conversation_id", "message_id", "answer_id"]);
  if (kind === "note") return true;
  return has(["document_id", "chunk_id", "source_document_id", "conversation_id", "message_id"]);
}

async function handleCollectionsFixture(
  route: Route,
  method: string,
  path: string,
  url: URL,
  state: CollectionsFixtureState | undefined,
): Promise<void> {
  const json = (body: unknown, status = 200) =>
    route.fulfill({ status, headers: { ...CORS_HEADERS, "content-type": "application/json" }, body: JSON.stringify(body) });

  if (!state) {
    await json({ detail: "The local workspace is not configured for this fixture." }, 404);
    return;
  }

  const body = method === "GET" || method === "DELETE" ? null : route.request().postDataJSON();
  state.requests.push({ method, path: `${path}${url.search}`, body });
  const refused = async (operation: keyof NonNullable<CollectionsFixtureState["mutationStatus"]>): Promise<boolean> => {
    const status = state.mutationStatus?.[operation];
    if (!status) return false;
    await json({ detail: state.detail ?? "Fixture refusal" }, status);
    return true;
  };
  const find = (collectionId: string) => state.collections.find((entry) => entry.collection_id === collectionId);
  const stamp = "2026-09-22T12:00:00Z";

  // GET /collections
  if (path === "/collections" && method === "GET") {
    if (state.listStatus) {
      await json({ detail: state.detail ?? "Fixture refusal" }, state.listStatus);
      return;
    }
    const search = (url.searchParams.get("search") ?? "").toLowerCase();
    const favorite = url.searchParams.get("favorite");
    const sort = url.searchParams.get("sort") ?? "updated_at";
    const direction = url.searchParams.get("direction") ?? "desc";
    const page = Number(url.searchParams.get("page") ?? "1");
    const pageSize = Number(url.searchParams.get("page_size") ?? "25");
    let items = state.collections.filter((entry) => !entry.deleted);
    if (favorite !== null) items = items.filter((entry) => entry.favorite === (favorite === "true"));
    if (search) {
      items = items.filter((entry) =>
        [entry.name, entry.description, ...entry.tags].join(" ").toLowerCase().includes(search),
      );
    }
    const directionFactor = direction === "asc" ? 1 : -1;
    items = [...items].sort((left, right) => {
      if (sort === "name") return left.name.localeCompare(right.name) * directionFactor;
      if (sort === "created_at") return left.created_at.localeCompare(right.created_at) * directionFactor;
      if (sort === "item_count") return (left.items.length - right.items.length) * directionFactor;
      return left.updated_at.localeCompare(right.updated_at) * directionFactor;
    });
    const total = items.length;
    const start = (page - 1) * pageSize;
    await json({
      items: items.slice(start, start + pageSize).map(collectionsPayload),
      total,
      page,
      page_size: pageSize,
    });
    return;
  }

  // POST /collections
  if (path === "/collections" && method === "POST") {
    if (await refused("create")) return;
    const payload = (body ?? {}) as Record<string, unknown>;
    const created: CollectionsFixtureCollection = {
      collection_id: `col-${state.collections.length + 1}`,
      name: String(payload.name ?? "Untitled"),
      description: String(payload.description ?? ""),
      tags: Array.isArray(payload.tags) ? (payload.tags as string[]) : [],
      favorite: Boolean(payload.favorite ?? false),
      private: payload.private === undefined ? true : Boolean(payload.private),
      revision: 1,
      created_at: stamp,
      updated_at: stamp,
      items: [],
      notes: [],
      activity: [
        { activity_id: `act-${state.collections.length + 1}-1`, collection_id: `col-${state.collections.length + 1}`, entity_type: "collection", entity_id: `col-${state.collections.length + 1}`, event_type: "collection_created", occurred_at: stamp },
      ],
    };
    state.collections.push(created);
    await json(collectionsPayload(created));
    return;
  }

  const detailMatch = path.match(/^\/collections\/([^/]+)$/);
  if (detailMatch) {
    const collectionId = decodeURIComponent(detailMatch[1]);
    const entry = find(collectionId);
    if (method === "GET") {
      if (!entry) {
        await json({ detail: "Collection not found" }, 404);
        return;
      }
      if (entry.deleted) {
        await json({ detail: "Collection is deleted" }, 410);
        return;
      }
      await json(collectionsPayload(entry));
      return;
    }
    if (method === "PATCH") {
      if (await refused("update")) return;
      if (!entry || entry.deleted) {
        await json({ detail: "Collection not found" }, entry?.deleted ? 410 : 404);
        return;
      }
      const payload = (body ?? {}) as Record<string, unknown>;
      if (payload.revision !== entry.revision) {
        await json({ detail: "Collection revision is stale" }, 409);
        return;
      }
      if (typeof payload.name === "string") entry.name = payload.name;
      if (typeof payload.description === "string") entry.description = payload.description;
      if (Array.isArray(payload.tags)) entry.tags = payload.tags as string[];
      if (typeof payload.favorite === "boolean") entry.favorite = payload.favorite;
      if (typeof payload.private === "boolean") entry.private = payload.private;
      entry.revision += 1;
      entry.updated_at = stamp;
      entry.activity.push({ activity_id: `act-${collectionId}-${entry.activity.length + 1}`, collection_id: collectionId, entity_type: "collection", entity_id: collectionId, event_type: "collection_updated", occurred_at: stamp });
      await json(collectionsPayload(entry));
      return;
    }
    if (method === "DELETE") {
      if (await refused("delete")) return;
      if (!entry) {
        await json({ detail: "Collection not found" }, 404);
        return;
      }
      if (entry.deleted) {
        await json({ detail: "Collection is already deleted" }, 410);
        return;
      }
      if (Number(url.searchParams.get("revision")) !== entry.revision) {
        await json({ detail: "Collection revision is stale" }, 409);
        return;
      }
      entry.deleted = true;
      entry.revision += 1;
      await json({ operation: "delete", entity_type: "collection", entity_id: collectionId, revision: entry.revision, deleted_at: stamp });
      return;
    }
  }

  const itemsMatch = path.match(/^\/collections\/([^/]+)\/items$/);
  if (itemsMatch) {
    const collectionId = decodeURIComponent(itemsMatch[1]);
    const entry = find(collectionId);
    if (!entry || entry.deleted) {
      await json({ detail: "Collection not found" }, entry?.deleted ? 410 : 404);
      return;
    }
    if (method === "GET") {
      const kind = url.searchParams.get("kind");
      const kindFiltered = kind ? entry.items.filter((member) => member.item_kind === kind) : entry.items;
      await json({ items: kindFiltered, total: kindFiltered.length, page: 1, page_size: 100 });
      return;
    }
    if (method === "POST") {
      if (await refused("add-item")) return;
      const payload = (body ?? {}) as Record<string, unknown>;
      const kind = String(payload.item_kind ?? "") as CollectionsFixtureItemKind;
      const reference = (payload.reference ?? {}) as Record<string, unknown>;
      if (!collectionsReferenceIsValid(kind, reference)) {
        await json({ detail: `a ${kind} item must carry its required identity` }, 422);
        return;
      }
      const created: CollectionsFixtureItem = {
        item_id: `itm-${entry.items.length + 1}`,
        collection_id: collectionId,
        item_kind: kind,
        citation: String(payload.citation ?? ""),
        excerpt: String(payload.excerpt ?? ""),
        reference,
        revision: 1,
        created_at: stamp,
        updated_at: stamp,
        ...(payload.snapshot ? { snapshot: payload.snapshot as Record<string, unknown> } : {}),
      };
      entry.items.push(created);
      entry.updated_at = stamp;
      entry.activity.push({ activity_id: `act-${collectionId}-${entry.activity.length + 1}`, collection_id: collectionId, entity_type: "item", entity_id: created.item_id, event_type: "item_added", occurred_at: stamp });
      await json(created);
      return;
    }
  }

  const itemMatch = path.match(/^\/collections\/([^/]+)\/items\/([^/]+)$/);
  if (itemMatch && method === "DELETE") {
    if (await refused("delete-item")) return;
    const entry = find(decodeURIComponent(itemMatch[1]));
    const itemId = decodeURIComponent(itemMatch[2]);
    const member = entry?.items.find((candidate) => candidate.item_id === itemId);
    if (!entry || !member) {
      await json({ detail: "Item not found" }, 404);
      return;
    }
    if (Number(url.searchParams.get("revision")) !== member.revision) {
      await json({ detail: "Item revision is stale" }, 409);
      return;
    }
    entry.items = entry.items.filter((candidate) => candidate.item_id !== itemId);
    entry.updated_at = stamp;
    entry.activity.push({ activity_id: `act-${entry.collection_id}-${entry.activity.length + 1}`, collection_id: entry.collection_id, entity_type: "item", entity_id: itemId, event_type: "item_removed", occurred_at: stamp });
    await json({ operation: "delete", entity_type: "collection_item", entity_id: itemId, revision: 2, deleted_at: stamp });
    return;
  }

  const notesMatch = path.match(/^\/collections\/([^/]+)\/notes$/);
  if (notesMatch) {
    const collectionId = decodeURIComponent(notesMatch[1]);
    const entry = find(collectionId);
    if (!entry || entry.deleted) {
      await json({ detail: "Collection not found" }, entry?.deleted ? 410 : 404);
      return;
    }
    if (method === "GET") {
      await json({ items: entry.notes, total: entry.notes.length, page: 1, page_size: 100 });
      return;
    }
    if (method === "POST") {
      if (await refused("add-note")) return;
      const payload = (body ?? {}) as Record<string, unknown>;
      const text = String(payload.text ?? "");
      if (text.length === 0) {
        await json({ detail: "a note must carry text" }, 422);
        return;
      }
      const created: CollectionsFixtureNote = {
        note_id: `note-${entry.notes.length + 1}`,
        collection_id: collectionId,
        text,
        revision: 1,
        created_at: stamp,
        updated_at: stamp,
        ...(payload.evidence_ref ? { evidence_ref: payload.evidence_ref as Record<string, unknown> } : {}),
      };
      entry.notes.push(created);
      entry.activity.push({ activity_id: `act-${collectionId}-${entry.activity.length + 1}`, collection_id: collectionId, entity_type: "note", entity_id: created.note_id, event_type: "note_added", occurred_at: stamp });
      await json(created);
      return;
    }
  }

  const noteMatch = path.match(/^\/collections\/([^/]+)\/notes\/([^/]+)$/);
  if (noteMatch) {
    const entry = find(decodeURIComponent(noteMatch[1]));
    const noteId = decodeURIComponent(noteMatch[2]);
    const note = entry?.notes.find((candidate) => candidate.note_id === noteId);
    if (!entry || !note) {
      await json({ detail: "Note not found" }, 404);
      return;
    }
    if (method === "PATCH") {
      if (await refused("update-note")) return;
      const payload = (body ?? {}) as Record<string, unknown>;
      if (payload.revision !== note.revision) {
        await json({ detail: "Note revision is stale" }, 409);
        return;
      }
      note.text = String(payload.text ?? note.text);
      note.revision += 1;
      note.updated_at = stamp;
      entry.activity.push({ activity_id: `act-${entry.collection_id}-${entry.activity.length + 1}`, collection_id: entry.collection_id, entity_type: "note", entity_id: noteId, event_type: "note_updated", occurred_at: stamp });
      await json(note);
      return;
    }
    if (method === "DELETE") {
      if (await refused("delete-note")) return;
      if (Number(url.searchParams.get("revision")) !== note.revision) {
        await json({ detail: "Note revision is stale" }, 409);
        return;
      }
      entry.notes = entry.notes.filter((candidate) => candidate.note_id !== noteId);
      entry.activity.push({ activity_id: `act-${entry.collection_id}-${entry.activity.length + 1}`, collection_id: entry.collection_id, entity_type: "note", entity_id: noteId, event_type: "note_removed", occurred_at: stamp });
      await json({ operation: "delete", entity_type: "note", entity_id: noteId, revision: 2, deleted_at: stamp });
      return;
    }
  }

  const activityMatch = path.match(/^\/collections\/([^/]+)\/activity$/);
  if (activityMatch && method === "GET") {
    const entry = find(decodeURIComponent(activityMatch[1]));
    if (!entry || entry.deleted) {
      await json({ detail: "Collection not found" }, entry?.deleted ? 410 : 404);
      return;
    }
    await json({ items: [...entry.activity].reverse(), total: entry.activity.length, page: 1, page_size: 100 });
    return;
  }

  const exportMatch = path.match(/^\/collections\/([^/]+)\/export$/);
  if (exportMatch && method === "GET") {
    const entry = find(decodeURIComponent(exportMatch[1]));
    if (!entry || entry.deleted) {
      await json({ detail: "Collection not found" }, entry?.deleted ? 410 : 404);
      return;
    }
    if (url.searchParams.get("format") === "markdown") {
      await json({ format: "markdown", content: `# ${entry.name}\n\n${entry.description}\n` });
      return;
    }
    await json({
      id: entry.collection_id,
      name: entry.name,
      description: entry.description,
      tags: entry.tags,
      favorite: entry.favorite,
      private: entry.private,
      revision: entry.revision,
      created_at: entry.created_at,
      updated_at: entry.updated_at,
      items: entry.items,
      notes: entry.notes,
    });
    return;
  }

  await json({ detail: "Unsupported collections fixture route" }, 404);
}
