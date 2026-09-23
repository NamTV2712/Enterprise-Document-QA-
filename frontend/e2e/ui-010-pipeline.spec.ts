import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import {
  installPipelineFixture,
  pipelineRun,
  PIPELINE_FIXTURE_TOKEN,
  type PipelineFixture,
} from "./pipeline-fixtures";

const VIEWPORTS = [
  { name: "1586x992", width: 1586, height: 992 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1280x856", width: 1280, height: 856 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "768x900", width: 768, height: 900 },
  { name: "390x844", width: 390, height: 844 },
  { name: "1440x700", width: 1440, height: 700 },
] as const;

async function connect(page: Page) {
  await page.getByRole("button", { name: "Connect", exact: true }).first().click();
  const dialog = page.getByRole("dialog", { name: "Connect local workspace" });
  await expect(dialog.getByLabel("Local workspace token")).toBeFocused();
  await dialog.getByLabel("Local workspace token").fill(PIPELINE_FIXTURE_TOKEN);
  await dialog.getByRole("button", { name: "Verify and connect" }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText(/^Connected · (local|read only)$/)).toBeVisible();
}

async function noHorizontalOverflow(page: Page) {
  const widths = await page.evaluate(() => ({
    body: document.body.scrollWidth - document.body.clientWidth,
    root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  expect(widths).toEqual({ body: 0, root: 0 });
}

function trackNonPipelineMutations(page: Page) {
  const requests: string[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET" && request.method() !== "OPTIONS" && !path.startsWith("/pipeline/")) {
      requests.push(`${request.method()} ${path}`);
    }
  });
  return requests;
}

test.describe("UI-010 Pipeline", () => {
  test("loads the public five-step definition and keeps private history gated", async ({ page }) => {
    const fixture = await installPipelineFixture(page);
    const mutations = trackNonPipelineMutations(page);
    await page.goto("/pipeline");

    await expect(page.getByRole("heading", { name: "Pipeline", exact: true })).toBeVisible();
    await expect(page.locator("[data-testid^='pipeline-stage-']")).toHaveCount(5);
    await expect(page.getByRole("heading", { name: "Connect to view local runs" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Stage run" })).toBeDisabled();
    expect(fixture.calls.filter((call) => call.path !== "/pipeline")).toEqual([]);
    expect(mutations).toEqual([]);
  });

  test("public mode reports the private capability as unavailable after an explicit connection attempt", async ({ page }, testInfo) => {
    const fixture = await installPipelineFixture(page, { mode: "public" });
    await page.goto("/pipeline");
    await expect(page.locator("[data-testid^='pipeline-stage-']")).toHaveCount(5);
    await page.getByRole("button", { name: "Connect", exact: true }).first().click();
    const dialog = page.getByRole("dialog", { name: "Connect local workspace" });
    await dialog.getByLabel("Local workspace token").fill(PIPELINE_FIXTURE_TOKEN);
    await dialog.getByRole("button", { name: "Verify and connect" }).click();

    await expect(dialog.getByRole("alert")).toContainText("local workspace is unavailable");
    await page.screenshot({ path: testInfo.outputPath("pipeline-private-unavailable.png"), animations: "disabled" });
    await dialog.getByRole("button", { name: "Close" }).first().click();
    await expect(page.getByRole("heading", { name: "Connect to view local runs" })).toBeVisible();
    expect(fixture.calls.filter((call) => call.path.startsWith("/pipeline/runs"))).toEqual([]);
  });

  test("shows protected history but does not offer staging when execution is disabled", async ({ page }) => {
    const fixture = await installPipelineFixture(page, {
      executionEnabled: false,
      initialRuns: [pipelineRun("run-existing")],
    });
    await page.goto("/pipeline");
    await connect(page);
    await expect(page.getByRole("button", { name: "Select a run run-existing" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Stage run" })).toBeDisabled();
    expect(fixture.stageCount()).toBe(0);
  });

  test("connects in memory, stages one queued run, and renders five pending durable steps", async ({ page }, testInfo) => {
    const fixture = await installPipelineFixture(page);
    const mutations = trackNonPipelineMutations(page);
    await page.goto("/pipeline");
    await connect(page);
    await expect(page.getByRole("heading", { name: "No staged runs yet" })).toBeVisible();
    await page.getByRole("button", { name: "Stage run" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Stage an isolated run" });
    await dialog.getByRole("checkbox", { name: "AAPL" }).check();
    await dialog.getByRole("button", { name: "Create staged run" }).evaluate((button) => {
      (button as HTMLButtonElement).click();
      (button as HTMLButtonElement).click();
    });

    await expect(page).toHaveURL(/\/pipeline\/runs\/run-staged-1$/);
    await expect(page.getByRole("status").filter({ hasText: "Staged record created" })).toBeVisible();
    const detail = page.getByTestId("pipeline-run-detail");
    await expect(detail).toContainText("Queued");
    await expect(detail.locator(".pipeline-step-item")).toHaveCount(5);
    await expect(detail.locator(".pipeline-step-item.is-pending")).toHaveCount(5);
    await expect(detail).toContainText("Not reported");
    await page.screenshot({ path: testInfo.outputPath("pipeline-staged-queued.png"), animations: "disabled" });
    expect(fixture.stageCount()).toBe(1);
    expect(fixture.runs.get("run-staged-1")?.state).toBe("queued");
    expect(mutations).toEqual([]);
  });

  test("keeps a newly selected run untouched when the old run receives later events", async ({ page }) => {
    const fixture = await installPipelineFixture(page, {
      initialRuns: [pipelineRun("run-A"), pipelineRun("run-B", { input_ids: ["MSFT"] })],
    });
    await page.goto("/pipeline/runs/run-A");
    await connect(page);
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("run-A");
    await page.getByRole("button", { name: "Select a run run-B" }).click();
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("MSFT");
    fixture.emitState("run-A", "failed");
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("run-B");
    await expect(page.getByTestId("pipeline-run-detail")).not.toContainText("Failed");
    await expect.poll(() => fixture.calls.some((call) => call.path === "/pipeline/runs/run-B/events"), { timeout: 5_000 }).toBe(true);
  });

  test("resumes SSE, reconciles server state, and preserves revision cancellation conflicts", async ({ page }) => {
    const fixture = await installPipelineFixture(page, {
      initialRuns: [pipelineRun("run-A")],
    });
    await page.goto("/pipeline/runs/run-A");
    await connect(page);
    const detail = page.getByTestId("pipeline-run-detail");
    await expect(detail.locator(".pipeline-step-item")).toHaveCount(5);
    await expect.poll(() => fixture.calls.some((call) => call.path === "/pipeline/runs/run-A/events" && call.lastEventId === "1"), { timeout: 5_000 }).toBe(true);

    fixture.emitState("run-A", "running");
    await expect(detail.locator(".pipeline-detail-summary")).toContainText("Running", { timeout: 6_000 });
    fixture.forceConflictOnce();
    await detail.getByRole("button", { name: "Request cancellation" }).click();
    await expect(detail.getByRole("alert")).toContainText("This run changed. Refresh it before trying again.");
    expect(fixture.cancelCount()).toBe(1);
    await expect(detail.locator(".pipeline-detail-revision")).toContainText("r2");

    await detail.getByRole("button", { name: "Request cancellation" }).click();
    await expect(detail.locator(".pipeline-detail-summary")).toContainText("Cancelling");
    await expect(detail).toContainText("The run remains cancelling until the backend confirms it.");
    await expect(detail.getByRole("button", { name: "Request cancellation" })).toHaveCount(0);
    expect(fixture.cancelCount()).toBe(2);
    expect(fixture.calls.find((call) => call.path.endsWith("/cancel"))?.ifMatch).toBe('"2"');
  });

  test("uses canonical run routes, browser history, and forgets the credential on reload", async ({ page }) => {
    const fixture = await installPipelineFixture(page, {
      initialRuns: [pipelineRun("run-A"), pipelineRun("run-B", { input_ids: ["MSFT"] })],
    });
    await page.goto("/pipeline/runs/run-A");
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("Connect to the local workspace");
    await connect(page);
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("run-A");
    await page.getByRole("button", { name: "Select a run run-B" }).click();
    await expect(page).toHaveURL(/\/pipeline\/runs\/run-B$/);
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("MSFT");
    await page.goBack();
    await expect(page).toHaveURL(/\/pipeline\/runs\/run-A$/);
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("run-A");
    await page.goForward();
    await expect(page).toHaveURL(/\/pipeline\/runs\/run-B$/);

    const beforeReload = await page.evaluate(() => ({
      url: location.href,
      local: Object.entries(localStorage),
      session: Object.entries(sessionStorage),
      visibleText: document.body.innerText,
    }));
    expect(JSON.stringify(beforeReload)).not.toContain(PIPELINE_FIXTURE_TOKEN);
    await page.reload();
    await expect(page.getByRole("heading", { name: "Connect to view local runs" })).toBeVisible();
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("Connect to the local workspace");
    expect(fixture.stageCount()).toBe(0);
  });

  test("matches the reference composition where server facts allow and stays usable at every required width", async ({ page }, testInfo) => {
    const fixture: PipelineFixture = await installPipelineFixture(page, {
      initialRuns: [
        pipelineRun("run-reference-1", { state: "running", revision: 3, input_ids: ["AAPL"] }),
        pipelineRun("run-reference-2", { state: "queued", input_ids: ["MSFT"] }),
        pipelineRun("run-reference-3", { state: "succeeded", input_ids: ["NVDA"] }),
        pipelineRun("run-reference-4", { state: "failed", input_ids: ["BRK-B"] }),
        pipelineRun("run-reference-5", { state: "cancelled", input_ids: ["AAPL", "MSFT"] }),
      ],
    });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.addInitScript(() => localStorage.setItem("theme", "dark"));
    await page.setViewportSize(VIEWPORTS[0]);
    await page.goto("/pipeline");
    await expect(page.locator("[data-testid^='pipeline-stage-']")).toHaveCount(5);
    await page.screenshot({ path: testInfo.outputPath("pipeline-1586x992-initial.png"), animations: "disabled" });
    await connect(page);
    await page.getByRole("button", { name: "Select a run run-reference-1" }).click();
    await expect(page.getByTestId("pipeline-run-detail").locator(".pipeline-step-item")).toHaveCount(5);

    const geometry = await page.evaluate(() => {
      const box = (selector: string) => {
        const rect = document.querySelector(selector)?.getBoundingClientRect();
        return rect ? { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) } : null;
      };
      return {
        header: box(".pipeline-page-header"),
        metrics: box(".pipeline-metrics"),
        flow: box(".pipeline-flow-card"),
        history: box(".pipeline-history-card"),
        detail: box(".pipeline-detail-card"),
      };
    });
    expect(geometry.metrics?.width).toBeGreaterThan(500);
    expect(geometry.detail?.width).toBeGreaterThan(300);
    expect(geometry.detail?.x).toBeGreaterThan(geometry.flow?.x ?? 0);
    await page.screenshot({ path: testInfo.outputPath("pipeline-1586x992-selected.png"), animations: "disabled" });

    for (const viewport of VIEWPORTS.slice(1)) {
      await page.setViewportSize(viewport);
      await expect(page.getByRole("heading", { name: "Pipeline", exact: true })).toBeVisible();
      await expect(page.locator("[data-testid^='pipeline-stage-']")).toHaveCount(5);
      await noHorizontalOverflow(page);
      await page.screenshot({ path: testInfo.outputPath(`pipeline-${viewport.name}-selected.png`), fullPage: viewport.width <= 390, animations: "disabled" });
      if (viewport.width === 390) {
        await page.getByTestId("pipeline-run-detail").scrollIntoViewIfNeeded();
        await page.screenshot({ path: testInfo.outputPath("pipeline-390x844-detail.png"), animations: "disabled" });
      }
    }

    await page.setViewportSize(VIEWPORTS[0]);
    await page.getByTestId("pipeline-run-detail").getByRole("button", { name: "Request cancellation" }).click();
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("Cancelling");
    await page.screenshot({ path: testInfo.outputPath("pipeline-1586x992-cancelling.png"), animations: "disabled" });
    expect(fixture.cancelCount()).toBe(1);

    const accessibility = await new AxeBuilder({ page }).include(".pipeline-workspace").withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(accessibility.violations).toEqual([]);
  });
});
