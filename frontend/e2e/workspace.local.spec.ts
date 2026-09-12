import { expect, Page, test } from "@playwright/test";
import { askQuestion } from "./fixtures";

const API_ORIGIN = "http://127.0.0.1:8766";
const CONTROL_ORIGIN = "http://127.0.0.1:8765";

async function setup(page: Page): Promise<void> {
  await page.request.post(`${CONTROL_ORIGIN}/__harness__/failure`, {
    data: { mode: "clear" },
  });
  await page.request.post(`${CONTROL_ORIGIN}/__harness__/memory/reset`);
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (
      url.startsWith("http://localhost:4175") ||
      url.startsWith("http://127.0.0.1:4175") ||
      url.startsWith(API_ORIGIN) ||
      url.startsWith(CONTROL_ORIGIN)
    ) {
      await route.continue();
      return;
    }
    await route.abort();
  });
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
}

test.afterEach(async ({ page }) => {
  await page.request.post(`${CONTROL_ORIGIN}/__harness__/failure`, {
    data: { mode: "clear" },
  });
});

test("renders real stage events and exact indexed reader identity", async ({ page }) => {
  await setup(page);
  await expect(page.getByText(/Research ready/i).first()).toBeVisible();

  await askQuestion(page, "What was Apple total revenue?");
  await expect(page.getByText(/Harness answer with/).first()).toBeVisible();
  await expect(page.getByText("Execution stages", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Open 1 sources", exact: true }).click();
  await page.getByRole("button", { name: /Open source excerpt/ }).click();
  await expect(page.locator(".context-viewer-text").getByText("Harness indexed excerpt for AAPL.", { exact: true })).toBeVisible();
  await page.getByText("About this source", { exact: true }).click();
  await expect(page.locator(".context-metadata")).toContainText("Chunk: AAPL_harness_0000");
  await expect(page.getByText("Indexed document chunks", { exact: true })).toBeVisible();
  await expect(page.getByText("Harness neighboring indexed excerpt for AAPL.")).toBeVisible();
  await page.locator(".context-neighbor-row").filter({ hasText: "Harness neighboring indexed excerpt for AAPL." }).click();
  await expect(page.locator(".context-metadata")).toContainText("Chunk: AAPL_harness_0001");
  await expect(page.getByRole("button", { name: "Return to cited excerpt" })).toBeVisible();
  await page.getByRole("button", { name: "Return to cited excerpt" }).click();
  await expect(page.locator(".context-metadata")).toContainText("Chunk: AAPL_harness_0000");
});

test("keeps the harness readiness contract observable over HTTP", async ({ page }) => {
  await setup(page);
  const downStatus = await page.evaluate(async (controlOrigin) => {
    const response = await fetch(`${controlOrigin}/__harness__/state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pipeline_ready: false }),
    });
    return response.status;
  }, CONTROL_ORIGIN);
  expect(downStatus).toBe(200);
  const response = await page.request.get(`${API_ORIGIN}/health/ready`);
  expect(response.status()).toBe(503);

  await page.evaluate(async (controlOrigin) => {
    await fetch(`${controlOrigin}/__harness__/state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pipeline_ready: true }),
    });
  }, CONTROL_ORIGIN);
  await expect(page.getByText(/Research ready/i).first()).toBeVisible();
});

test("does not substitute another source for an unknown chunk identity", async ({ page }) => {
  await setup(page);
  const response = await page.request.get(`${API_ORIGIN}/chunks/unknown-fixture-chunk`);
  expect(response.status()).toBe(404);
});
