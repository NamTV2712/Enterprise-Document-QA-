/**
 * API fixtures for browser tests. Every backend interaction is served from
 * local route mocks: tests never reach a real provider or backend, and any
 * request outside the mocked API origin fails the test loudly.
 */

import { Page, expect } from "@playwright/test";

export const API_ORIGIN = "http://127.0.0.1:8000";

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

const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "Content-Type",
  "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
};

function sseEvent(type: string, data: unknown): string {
  return `data: ${JSON.stringify({ type, data })}\n\n`;
}

export const SAMPLE_SOURCES = [
  {
    citation: "AAPL 10-K (filed 2025-10-31), Section: Risk Factors",
    score: 0.8123,
    text_preview: "The company faces competition risks in consumer markets.",
    text: "The company faces competition risks in consumer markets worldwide, including aggressive pricing pressure from competitors.",
    chunk_id: "AAPL_test_risk_factors_0",
    document_id: "AAPL:fixture",
    ticker: "AAPL",
    section: "risk_factors",
    filing_date: "2025-10-31",
    report_date: "2025-09-27",
    chunk_index: 1,
    chunk_text_hash: "1111111111111111111111111111111111111111111111111111111111111111",
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
  "Apple's total net sales were $391,035 million in fiscal 2024 and $416,161 million in fiscal 2025 [Source 1].",
  "",
  "Key observations from the filing excerpts:",
  "",
  "- Products revenue remains the largest component of total net sales.",
  "- Services revenue grew year over year across every reported segment.",
  "- The company notes competition risks in consumer markets [Source 1].",
  "",
  "| Metric | FY2024 | FY2025 |",
  "| --- | --- | --- |",
  "| Total net sales | 391,035 | 416,161 |",
].join("\n");

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
  } = {},
): Promise<void> {
  const history: HistoryFixture = options.history ?? {
    session_id: "session-test",
    turns: [],
    context: { status: "missing", retained_turns: 0, ttl_remaining_seconds: 0 },
  };
  let streamRequestIndex = 0;

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

    if (method === "OPTIONS") {
      await route.fulfill({ status: 204, headers: CORS_HEADERS });
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

    const decodedPath = decodeURIComponent(path);
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
            text_length: 256,
          }],
          representations: [
            { kind: "normalized_text", status: "available", reason_code: "available", reason: null },
            { kind: "structured", status: "available", reason_code: "available", reason: null },
            { kind: "pdf", status: "unavailable", reason_code: "pdf_representation_unavailable", reason: "PDF is not available in the current corpus." },
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
            { block_id: "fixture-paragraph", kind: "paragraph", text: "The company faces competition risks in consumer markets worldwide.", runs: [{ text: "The company faces competition risks in consumer markets worldwide.", emphasis: false, strong: false, superscript: false, subscript: false }], level: null, anchor: null, items: [], caption: null, columns: [], rows: [], source_text: "The company faces competition risks in consumer markets worldwide." },
            { block_id: "fixture-table", kind: "table", text: "", runs: [], level: null, anchor: null, items: [], caption: "Revenue", columns: ["Metric", "FY2025"], rows: [[{ text: "Total sales", rowspan: 1, colspan: 1, header: false }, { text: "416,161", rowspan: 1, colspan: 1, header: false }]], source_text: "Total sales 416,161" },
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

    if (path === "/retrieval/inspect" && method === "POST") {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          query_interpretation: {
            original_question: "What was Apple's total revenue in 2024?",
            retrieval_question: "What was Apple's total revenue in 2024?",
            language: "en",
            detected_ticker: "AAPL",
          },
          trace: {
            preset: "hybrid_rerank",
            query: "What was Apple's total revenue in 2024?",
            filters: { ticker: null, section: null },
            top_k: 5,
            candidate_pool: 10,
            models: { embedding: "fixture-embedding", reranker: "fixture-reranker", rrf_k: 60 },
            stages: [{ name: "retrieval", elapsed_ms: 1.2 }],
            candidates: [{
              chunk_id: "AAPL_fixture_revenue_0",
              citation: "AAPL 10-K, Financial Statements",
              text_preview: "Total revenue was reported in fiscal 2024.",
              final_rank: 1,
              selected: true,
              bm25_score: 1,
              dense_score: 0.9,
              rrf_score: 0.8,
              cross_encoder_score: 0.7,
            }],
            selected_chunk_ids: ["AAPL_fixture_revenue_0"],
            elapsed_ms: 1.2,
          },
        }),
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
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify({
          chunk_id: "AAPL_test_risk_factors_0",
          chunk_text_hash: "1111111111111111111111111111111111111111111111111111111111111111",
          document_id: "AAPL:fixture",
          source_set_revision: "fixture-source-set-revision",
          status: "exact",
          reason_code: "exact",
          reason: null,
          source_document_id: "fixture-source",
          document_revision: "fixture-document-revision",
          representation_revision: "fixture-structured-revision",
          ranges: [{ block_id: "fixture-paragraph", block_index: 1, kind: "paragraph", start: 0, end: 65, method: "text_whitespace" }],
          match_count: 1,
          match_count_capped: false,
        }),
      });
      return;
    }

    if (decodedPath.startsWith("/chunks/") && method === "GET") {
      const chunkId = decodeURIComponent(path.slice("/chunks/".length));
      const source = SAMPLE_SOURCES.find((item) => item.chunk_id === chunkId) ?? (chunkId === "AAPL_fixture_revenue_0"
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
  await page.getByRole("button", { name: /Library/ }).click();
}
