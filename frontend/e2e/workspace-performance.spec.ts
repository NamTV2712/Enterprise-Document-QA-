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

  const viewSamples: number[] = [];
  for (let index = 0; index < 30; index += 1) {
    viewSamples.push(await elapsed(page, async () => {
      await page.getByRole("button", { name: "Documents", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Document Explorer", exact: true })).toBeVisible();
      await page.getByRole("button", { name: "Research", exact: true }).click();
      await expect(input).toBeVisible();
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

  const markdownSamples = await Promise.all(Array.from({ length: 30 }, () => elapsed(page, async () => {
    await expect(response.locator(".markdown-body")).toBeVisible();
    await response.locator(".markdown-body").evaluate((element) => element.getBoundingClientRect().height);
  })));
  report("final Markdown layout read", markdownSamples);
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
