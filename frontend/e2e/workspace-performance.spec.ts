import { expect, Page, test } from "@playwright/test";
import { askQuestion, installApiFixtures } from "./fixtures";

const REAL_BACKEND = process.env.PLAYWRIGHT_REAL_BACKEND === "1";
const REAL_API_ORIGIN = "http://127.0.0.1:8000";

function percentile(samples: number[], percentileValue = 0.95): number {
  const ordered = [...samples].sort((left, right) => left - right);
  return ordered[Math.max(0, Math.ceil(ordered.length * percentileValue) - 1)] ?? 0;
}

async function elapsed(page: Page, action: () => Promise<void>): Promise<number> {
  const start = await page.evaluate(() => performance.now());
  await action();
  return (await page.evaluate(() => performance.now())) - start;
}

function report(label: string, samples: number[], budget?: number): void {
  const p50 = percentile(samples, 0.5);
  const p95 = percentile(samples);
  const budgetText = budget === undefined ? "no fixed budget" : `budget=${budget}ms`;
  console.log(`[performance] ${label}: p50=${p50.toFixed(2)}ms p95=${p95.toFixed(2)}ms n=${samples.length} ${budgetText}`);
}

async function setupSynthetic(page: Page): Promise<void> {
  await installApiFixtures(page);
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
}

type ReaderLayoutMetrics = {
  tableCount: number;
  figureCount: number;
  rowCount: number;
  cellCount: number;
  maxTableScrollWidth: number;
  maxTableClientWidth: number;
  globalScrollWidth: number;
  viewportWidth: number;
  domNodes: number;
  forcedLayoutMs: number;
  memoryMeasureSupported: boolean;
};

type ReaderRequestMetric = {
  endpoint: string;
  durationMs: number;
  status: "finished" | "failed";
};

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function companyLabel(ticker: string): string {
  const labels: Record<string, string> = {
    AAPL: "Apple Inc. (AAPL)",
    GOOGL: "Alphabet Inc. (Google) (GOOGL)",
    AMZN: "Amazon.com, Inc. (AMZN)",
  };
  return labels[ticker] ?? ticker;
}

async function captureReaderMetrics(page: Page): Promise<ReaderLayoutMetrics> {
  return page.evaluate(() => {
    const reader = document.querySelector<HTMLElement>(".structured-reader");
    const tableScrolls = Array.from(document.querySelectorAll<HTMLElement>(".structured-reader__table-scroll"));
    const tables = Array.from(document.querySelectorAll<HTMLTableElement>(".structured-reader__table table"));
    const layoutStart = performance.now();
    let measuredWidth = 0;
    for (const element of Array.from(reader?.querySelectorAll<HTMLElement>("*") ?? [])) {
      measuredWidth += element.getBoundingClientRect().width;
    }
    return {
      tableCount: tables.length,
      figureCount: document.querySelectorAll(".structured-reader__table").length,
      rowCount: tables.reduce((total, table) => total + table.rows.length, 0),
      cellCount: tables.reduce((total, table) => total + Array.from(table.rows).reduce((rowTotal, row) => rowTotal + row.cells.length, 0), 0),
      maxTableScrollWidth: Math.max(0, ...tableScrolls.map((element) => element.scrollWidth)),
      maxTableClientWidth: Math.max(0, ...tableScrolls.map((element) => element.clientWidth)),
      globalScrollWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      domNodes: document.querySelectorAll(".structured-reader *").length,
      forcedLayoutMs: performance.now() - layoutStart + measuredWidth * 0,
      memoryMeasureSupported: typeof (performance as Performance & { measureUserAgentSpecificMemory?: () => Promise<unknown> }).measureUserAgentSpecificMemory === "function",
    };
  });
}

async function measureReaderOpen(page: Page, documentId: string, action: () => Promise<void>): Promise<{ uiMs: number; requests: ReaderRequestMetric[]; metrics: ReaderLayoutMetrics }> {
  const encodedDocumentId = encodeURIComponent(documentId);
  const pending = new Map<unknown, { endpoint: string; started: number }>();
  const requests: ReaderRequestMetric[] = [];
  const endpointFor = (url: string): string | null => {
    try {
      const parsed = new URL(url);
      if (parsed.origin !== REAL_API_ORIGIN) return null;
      const prefix = `/documents/${encodedDocumentId}/reader`;
      if (!parsed.pathname.startsWith(prefix)) return null;
      if (parsed.pathname.endsWith("/outline")) return "outline";
      if (parsed.pathname.endsWith("/content")) return "content";
      if (parsed.pathname.endsWith("/search")) return "search";
      if (parsed.pathname.endsWith("/reader")) return "manifest";
      return null;
    } catch {
      return null;
    }
  };
  const onRequest = (request: { url(): string }) => {
    const endpoint = endpointFor(request.url());
    if (endpoint) pending.set(request, { endpoint, started: performance.now() });
  };
  const onFinished = (request: { url(): string }) => {
    const sample = pending.get(request);
    if (!sample) return;
    pending.delete(request);
    requests.push({ endpoint: sample.endpoint, durationMs: performance.now() - sample.started, status: "finished" });
  };
  const onFailed = (request: { url(): string }) => {
    const sample = pending.get(request);
    if (!sample) return;
    pending.delete(request);
    requests.push({ endpoint: sample.endpoint, durationMs: performance.now() - sample.started, status: "failed" });
  };
  page.on("request", onRequest);
  page.on("requestfinished", onFinished);
  page.on("requestfailed", onFailed);
  const started = performance.now();
  try {
    await action();
    // Content is rendered after its response is consumed. Give the outline
    // request a short opportunity to finish so the receipt includes the full
    // reader request set without waiting for unrelated application traffic.
    await page.waitForTimeout(50);
  } finally {
    page.off("request", onRequest);
    page.off("requestfinished", onFinished);
    page.off("requestfailed", onFailed);
  }
  return { uiMs: performance.now() - started, requests, metrics: await captureReaderMetrics(page) };
}

function summarizeReaderRequests(requests: ReaderRequestMetric[]): Record<string, { count: number; durationsMs: number[]; failed: number }> {
  return requests.reduce<Record<string, { count: number; durationsMs: number[]; failed: number }>>((summary, request) => {
    const item = summary[request.endpoint] ?? { count: 0, durationsMs: [], failed: 0 };
    item.count += 1;
    item.durationsMs.push(Number(request.durationMs.toFixed(2)));
    if (request.status === "failed") item.failed += 1;
    summary[request.endpoint] = item;
    return summary;
  }, {});
}

test("records synthetic frontend baselines for warm controls and workspace paths", async ({ page }) => {
  test.skip(REAL_BACKEND, "Synthetic baseline runs with provider-free browser fixtures.");
  await setupSynthetic(page);

  const input = page.getByRole("textbox", { name: "Research question" });
  const inputSamples: number[] = [];
  for (let index = 0; index < 40; index += 1) {
    inputSamples.push(await elapsed(page, () => input.fill(`Warm input sample ${index}`)));
  }
  report("warm composer input", inputSamples, 100);
  expect(percentile(inputSamples)).toBeLessThan(100);

  // Warm the lazy route once so the measured samples represent repeated
  // navigation rather than the first module fetch and initial mount.
  await page.locator('[data-workspace-view="documents"]').click({ force: true });
  await expect(page.locator(".document-explorer")).toBeVisible();
  await page.locator('[data-workspace-view="overview"]').click({ force: true });
  await expect(page.locator(".overview-panel")).toBeVisible();

  const viewSamples: number[] = [];
  for (let index = 0; index < 30; index += 1) {
    viewSamples.push(await elapsed(page, async () => {
      await page.locator('[data-workspace-view="documents"]').click({ force: true });
      await expect(page.locator(".document-explorer")).toBeVisible();
      await page.locator('[data-workspace-view="overview"]').click({ force: true });
      await expect(page.locator(".overview-panel")).toBeVisible();
    }));
  }
  report("warm view switch", viewSamples, 200);
  expect(percentile(viewSamples)).toBeLessThan(200);

  const paletteSamples: number[] = [];
  for (let index = 0; index < 20; index += 1) {
    paletteSamples.push(await elapsed(page, async () => {
      await page.getByRole("button", { name: "Open command palette" }).click();
      await expect(page.getByRole("dialog", { name: "Command palette" })).toBeVisible();
      await page.keyboard.press("Escape");
    }));
  }
  report("command palette mount cycle", paletteSamples);

  console.log("[performance] Scope editor mount on the empty overview: UNVERIFIED; existing ScopeEditor unit/interaction tests cover its lifecycle.");
  console.log("[performance] 60-second stream with simultaneous typing: UNVERIFIED in this provider-free baseline");
  console.log("[performance] Network/provider timing: UNVERIFIED here; local endpoint timings are recorded by the LOCAL BACKEND test.");
});

test("records source switching, reader warm/cold paths, and final Markdown render", async ({ page }) => {
  test.skip(REAL_BACKEND, "Synthetic reader baseline runs with provider-free browser fixtures.");
  await setupSynthetic(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText("Apple's total net sales were", { exact: false }).first()).toBeVisible();

  const response = page.getByRole("article", { name: "Research assistant response" });
  await expect(response.locator(".markdown-body")).toBeVisible();
  const markdownSamples = await Promise.all(Array.from({ length: 30 }, () => elapsed(page, async () => {
    await expect(response.locator(".markdown-body")).toBeVisible();
    await response.locator(".markdown-body").evaluate((element) => element.getBoundingClientRect().height);
  })));
  report("final Markdown layout read", markdownSamples);
  await page.getByRole("button", { name: "Open 2 sources", exact: true }).click();
  const cards = page.locator(".context-source-card");
  await expect(cards).toHaveCount(2);

  const coldReader = await elapsed(page, async () => {
    await cards.nth(0).click();
    await expect(page.locator(".context-viewer-text")).toContainText("competition risks");
  });
  const readerSamples: number[] = [coldReader];
  for (let index = 0; index < 30; index += 1) {
    const cardIndex = index % 2;
    readerSamples.push(await elapsed(page, async () => {
      await cards.nth(cardIndex).click();
      await expect(page.locator(".context-viewer-text")).toBeVisible();
    }));
  }
  report("source switching + reader", readerSamples);
  console.log("[performance] Scope-change request race and obsolete-response rejection: covered by existing lifecycle regression tests; not remeasured here.");
});

test("verifies provider-free local backend readiness and retrieval feasibility", async ({ page, request }) => {
  test.skip(!REAL_BACKEND, "Runs only with PLAYWRIGHT_REAL_BACKEND=1 against the verified local backend.");
  const timings: Record<string, number> = {};
  const timedRequest = async (name: string, action: () => Promise<{ status(): number; json(): Promise<any> }>) => {
    const start = performance.now();
    const response = await action();
    timings[name] = performance.now() - start;
    return response;
  };

  const live = await timedRequest("health/live", () => request.get(`${REAL_API_ORIGIN}/health/live`));
  expect(live.status()).toBe(200);
  const ready = await timedRequest("health/ready", () => request.get(`${REAL_API_ORIGIN}/health/ready`));
  expect(ready.status()).toBe(200);
  expect((await ready.json()).pipeline_ready).toBe(true);

  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();

  const system = await timedRequest("system/info", () => request.get(`${REAL_API_ORIGIN}/system/info`));
  expect(system.status()).toBe(200);
  const systemPayload = await system.json();
  expect(systemPayload.capabilities?.document_indexed_viewer).toBe(true);

  const documents = await timedRequest("documents", () => request.get(`${REAL_API_ORIGIN}/documents?page_size=3`));
  expect(documents.status()).toBe(200);
  const documentPayload = await documents.json();
  expect(documentPayload.items.length).toBeGreaterThan(0);
  const documentId = documentPayload.items[0].document_id as string;

  const chunks = await timedRequest("document chunks", () => request.get(`${REAL_API_ORIGIN}/documents/${encodeURIComponent(documentId)}/chunks?page_size=3`));
  expect(chunks.status()).toBe(200);
  const chunkPayload = await chunks.json();
  expect(chunkPayload.items.length).toBeGreaterThan(0);
  const chunkId = chunkPayload.items[0].chunk_id as string;
  expect(chunkId).toBeTruthy();

  const detail = await timedRequest("chunk detail", () => request.get(`${REAL_API_ORIGIN}/chunks/${encodeURIComponent(chunkId)}`));
  expect(detail.status()).toBe(200);
  expect((await detail.json()).chunk_id).toBe(chunkId);

  const retrieval = await timedRequest("retrieval inspect", () => request.post(`${REAL_API_ORIGIN}/retrieval/inspect`, {
    data: {
      question: "What was Apple's total revenue in 2024?",
      ticker: null,
      section: null,
      top_k: 5,
      candidate_pool: 10,
      preset: "hybrid_rerank",
    },
  }));
  expect(retrieval.status()).toBe(200);
  expect((await retrieval.json()).trace).toBeTruthy();
  console.log(`[performance] LOCAL BACKEND provider-free timings: ${JSON.stringify(timings)}`);
  console.log(`[performance] LOCAL BACKEND environment: Chromium=${test.info().project.name}, API=${REAL_API_ORIGIN}, no generation request issued`);
});

test("records P08 representative reader cold and warm baselines", async ({ page, request }) => {
  test.skip(!REAL_BACKEND, "Runs only with PLAYWRIGHT_REAL_BACKEND=1 against the verified local backend.");

  const probes: Array<Record<string, unknown>> = [];
  for (const ticker of ["AAPL", "GOOGL", "AMZN"]) {
    const documentsResponse = await request.get(`${REAL_API_ORIGIN}/documents?ticker=${ticker}&page=1&page_size=1`);
    expect(documentsResponse.status(), `${ticker} catalog request`).toBe(200);
    const documentsPayload = await documentsResponse.json();
    const document = documentsPayload.items?.[0] as { document_id: string; filing_date: string | null } | undefined;
    expect(document?.document_id, `${ticker} must have a representative document`).toBeTruthy();

    const label = companyLabel(ticker);
    const resultName = new RegExp(`${escapeRegex(label)} · \\d{4}-\\d{2}-\\d{2}`);
    await page.goto("/?view=documents");
    await expect(page.locator(".document-explorer")).toBeVisible();
    const companySelect = page.getByRole("button", { name: "Company", exact: true });
    await companySelect.click();
    await page.getByRole("listbox", { name: "Company" }).getByRole("option", { name: label, exact: true }).click();
    const result = page.getByRole("button", { name: resultName }).first();
    await expect(result).toBeVisible();
    await result.click();
    const openWorkspace = page.getByRole("button", { name: "Open document workspace", exact: true });
    await expect(openWorkspace).toBeVisible();
    const cold = await measureReaderOpen(page, document!.document_id, async () => {
      await openWorkspace.click();
      await expect(page.locator(".document-workspace")).toBeVisible();
      await expect(page.locator("#document-workspace-title")).toContainText(label);
      await expect(page.locator(".structured-reader__canvas")).toBeVisible();
      await expect(page.locator(".structured-reader__canvas [data-reader-block]").first()).toBeVisible();
    });

    const coldOverflow = cold.metrics.globalScrollWidth > cold.metrics.viewportWidth + 1;
    await page.getByRole("button", { name: "Back to Documents", exact: true }).click();
    await expect(page.locator(".document-explorer")).toBeVisible();
    const warmResult = page.getByRole("button", { name: resultName }).first();
    await expect(warmResult).toBeVisible();
    await warmResult.click();
    const warmOpenWorkspace = page.getByRole("button", { name: "Open document workspace", exact: true });
    await expect(warmOpenWorkspace).toBeVisible();
    const warm = await measureReaderOpen(page, document!.document_id, async () => {
      await warmOpenWorkspace.click();
      await expect(page.locator(".document-workspace")).toBeVisible();
      await expect(page.locator(".structured-reader__canvas")).toBeVisible();
      await expect(page.locator(".structured-reader__canvas [data-reader-block]").first()).toBeVisible();
    });

    const receipt = {
      ticker,
      companyLabel: label,
      documentId: document!.document_id,
      filingDate: document!.filing_date,
      cold: {
        firstReadableContentMs: Number(cold.uiMs.toFixed(2)),
        readerRequests: summarizeReaderRequests(cold.requests),
        layout: cold.metrics,
        pageHorizontalOverflow: coldOverflow,
      },
      warm: {
        firstReadableContentMs: Number(warm.uiMs.toFixed(2)),
        readerRequests: summarizeReaderRequests(warm.requests),
        layout: warm.metrics,
        pageHorizontalOverflow: warm.metrics.globalScrollWidth > warm.metrics.viewportWidth + 1,
      },
      classification: {
        tableAndReader: "measurement recorded; no optimization or representation change inferred from one browser sample",
        memory: cold.metrics.memoryMeasureSupported ? "browser exposes measureUserAgentSpecificMemory; not invoked in this baseline" : "not measurable in this browser; DOM node count is the proxy",
      },
    };
    probes.push(receipt);
    console.log(`[performance][P08] ${JSON.stringify(receipt)}`);
  }
  expect(probes).toHaveLength(3);
  console.log(`[performance][P08] representative reader baseline complete: ${JSON.stringify(probes)}`);
});
