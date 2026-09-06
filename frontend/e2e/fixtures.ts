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
    ticker: "AAPL",
    section: "risk_factors",
    filing_date: "2025-10-31",
  },
  {
    citation: "MSFT 10-K (filed 2025-07-30), Section: MDNA",
    score: 0.7455,
    text_preview: "Microsoft Cloud revenue increased 23% to $168.9 billion.",
    text: "Microsoft Cloud revenue increased 23% to $168.9 billion driven by Azure growth across all customer segments this fiscal year.",
    chunk_id: "MSFT_test_mdna_0",
    ticker: "MSFT",
    section: "mdna",
    filing_date: "2025-07-30",
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
  options: { history?: HistoryFixture; health?: Record<string, unknown> } = {},
): Promise<void> {
  const history: HistoryFixture = options.history ?? {
    session_id: "session-test",
    turns: [],
    context: { status: "missing", retained_turns: 0, ttl_remaining_seconds: 0 },
  };

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

    if (path.startsWith("/session/") && path.endsWith("/history")) {
      await route.fulfill({
        status: 200,
        headers: { ...CORS_HEADERS, "content-type": "application/json" },
        body: JSON.stringify(history),
      });
      return;
    }

    if (path === "/query/stream" && method === "POST") {
      const body =
        sseEvent("sources", SAMPLE_SOURCES) +
        sseEvent("token", "Apple's total net sales were ") +
        sseEvent("token", "$391,035 million in fiscal 2024 ") +
        sseEvent("token", "and $416,161 million in fiscal 2025 [Source 1].") +
        sseEvent("done", null);
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
  await page.getByRole("tab", { name: /Library/ }).click();
}
