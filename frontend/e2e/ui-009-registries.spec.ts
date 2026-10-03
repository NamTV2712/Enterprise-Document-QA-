import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { DATASET_DETAIL_FIXTURES, installApiFixtures } from "./fixtures";

const VIEWPORTS = [
  { name: "1586x992", width: 1586, height: 992 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1280x856", width: 1280, height: 856 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "768x900", width: 768, height: 900 },
  { name: "390x844", width: 390, height: 844 },
  { name: "1440x700", width: 1440, height: 700 },
] as const;

async function settle(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}

async function expectNoHorizontalOverflow(page: Page, label: string) {
  const overflow = await page.evaluate(() => ({
    body: document.body.scrollWidth - document.body.clientWidth,
    root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  expect(overflow, `${label} horizontal overflow`).toEqual({ body: 0, root: 0 });
}

test.describe("UI-009 Models and Datasets", () => {
  test("Models is provider-free until its bounded identity action is explicitly requested", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    const writes: string[] = [];
    page.on("request", (request) => {
      if (request.method() !== "GET" && request.method() !== "OPTIONS") writes.push(`${request.method()} ${new URL(request.url()).pathname}`);
    });

    await page.goto("/models");
    await expect(page.getByRole("heading", { name: "Models", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Runtime registry" })).toBeVisible();
    await expect(page.getByText("openai/gpt-oss-120b").first()).toBeVisible();
    await expect(page.getByText("nomic-ai/nomic-embed-text-v1.5").first()).toBeVisible();
    await expect(page.getByText("cross-encoder/ms-marco-MiniLM-L-6-v2").first()).toBeVisible();
    await expect(page.getByRole("complementary", { name: "Generator details" })).toContainText("Unknown");
    expect(writes).toEqual([]);

    const embeddingResponse = page.waitForResponse((response) => new URL(response.url()).searchParams.get("role") === "embedding");
    await page.getByRole("tab", { name: "Embedding", exact: true }).click();
    await embeddingResponse;
    await expect(page.getByRole("complementary", { name: "Embedding details" })).toContainText("Loaded");
    expect(writes).toEqual([]);

    await page.getByRole("button", { name: "Run identity check" }).click();
    await expect(page.getByRole("complementary", { name: "Embedding details" }).getByRole("status")).toContainText("Provider executed: No");
    expect(writes).toEqual(["POST /models/embedding/tests"]);
  });

  test("Models reports an unavailable execution gate without implying provider failure", async ({ page }) => {
    await installApiFixtures(page);
    await page.route("**/models/generator/tests", (route) => route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Local workspace capability is unavailable" }),
    }));
    await page.goto("/models");
    await page.getByRole("button", { name: "Run identity check" }).click();
    await expect(page.getByRole("alert")).toContainText("unavailable in the current deployment mode");
    await expect(page.getByText(/Healthy|Online|Reachable/)).toHaveCount(0);
  });

  test("Datasets renders corpus provenance and evaluation-safe aggregates without mutations", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    const writes: string[] = [];
    page.on("request", (request) => {
      if (request.method() !== "GET" && request.method() !== "OPTIONS") writes.push(`${request.method()} ${new URL(request.url()).pathname}`);
    });

    await page.goto("/datasets");
    await expect(page.getByRole("heading", { name: "Datasets", exact: true })).toBeVisible();
    const corpus = page.getByRole("complementary", { name: "Serving SEC filing corpus details" });
    await expect(corpus).toContainText("Degraded");
    await expect(corpus).toContainText("configured_company_gap");
    await expect(corpus).toContainText("10,053");
    await expect(corpus).toContainText("qdrant index manifest");

    await page.getByRole("button", { name: /Built-in evaluation test set/ }).click();
    const evaluation = page.getByRole("complementary", { name: "Built-in evaluation test set details" });
    await expect(evaluation).toContainText("fact_lookup");
    await expect(evaluation).toContainText("eval-revision-2026-09");
    await expect(evaluation).toContainText("questions and ground truth are not sent");
    await expect(evaluation).not.toContainText(/expected answer|judge label/i);
    expect(writes).toEqual([]);
  });

  test("Datasets keeps missing and mismatched provenance distinct from an empty registry", async ({ page }) => {
    await installApiFixtures(page);
    const mismatch = {
      ...DATASET_DETAIL_FIXTURES["serving-corpus"],
      availability: "degraded",
      reason_code: "index_manifest_mismatch",
      reason: "The manifest embedding binding differs from the configured embedding model.",
      provenance: {
        ...(DATASET_DETAIL_FIXTURES["serving-corpus"].provenance as Record<string, unknown>),
        status: "mismatch",
        reason_code: "embedding_binding_mismatch",
        reason: "The recorded and configured embedding bindings differ.",
      },
    };
    await page.route("**/datasets/serving-corpus", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mismatch) }));
    await page.goto("/datasets");
    const detail = page.getByRole("complementary", { name: "Serving SEC filing corpus details" });
    await expect(detail).toContainText("index_manifest_mismatch");
    await expect(detail).toContainText("mismatch");
    await expect(page.getByText("No datasets reported")).toHaveCount(0);

    await page.unroute("**/datasets/serving-corpus");
    await page.route("**/datasets/serving-corpus", (route) => route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Dataset registry entry not found" }) }));
    await page.getByRole("button", { name: "Refresh" }).click();
    await expect(page.getByRole("alert")).toContainText("no longer present in the registry");
    await expect(page.getByText("No datasets reported")).toHaveCount(0);
  });

  test("direct routing plus browser back and forward preserve both registry pages", async ({ page }) => {
    await page.setViewportSize({ width: 1586, height: 992 });
    await installApiFixtures(page);
    await page.goto("/models");
    await expect(page.getByRole("heading", { name: "Models", exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Datasets", exact: true }).click();
    await expect(page).toHaveURL(/\/datasets$/);
    await expect(page.getByRole("heading", { name: "Datasets", exact: true })).toBeVisible();
    await page.goBack();
    await expect(page).toHaveURL(/\/models$/);
    await page.goForward();
    await expect(page).toHaveURL(/\/datasets$/);
  });

  test("registry surfaces pass the focused accessibility scan", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("theme", "dark"));
    await installApiFixtures(page);
    for (const path of ["/models", "/datasets"]) {
      await page.goto(path);
      await settle(page);
      await expect(page.getByRole("heading", { name: path === "/models" ? "Models" : "Datasets", exact: true })).toBeVisible();
      for (const child of await page.locator(".console-view-enter > *").all()) {
        await expect(child).toHaveCSS("animation-name", "none");
        await expect(child).toHaveCSS("opacity", "1");
      }
      const results = await new AxeBuilder({ page })
        .include("main")
        .options({ runOnly: ["color-contrast", "label", "button-name", "link-name", "aria-allowed-attr", "aria-required-attr"] })
        .analyze();
      expect(results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious"), `${path} serious axe violations`).toEqual([]);
    }
  });

  test("receipts remain usable without horizontal overflow across the required viewport ladder", async ({ page, browserName }) => {
    await page.addInitScript(() => localStorage.setItem("theme", "dark"));
    await installApiFixtures(page);
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      for (const path of ["models", "datasets"] as const) {
        await page.goto(`/${path}`);
        await expect(page.getByRole("heading", { name: path === "models" ? "Models" : "Datasets", exact: true })).toBeVisible();
        await settle(page);
        await expectNoHorizontalOverflow(page, `${path} ${viewport.name}`);
        if (viewport.width <= 768 && path === "models") {
          await expect(page.locator(".registry-table-wrap")).toBeHidden();
          await expect(page.locator(".registry-mobile-list")).toBeVisible();
        }
        await page.screenshot({ path: `test-results/ui-009/${path}-${viewport.name}-${browserName}.png`, animations: "disabled" });
      }
    }
  });
});
