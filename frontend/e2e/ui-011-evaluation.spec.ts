import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import {
  EVALUATION_FIXTURE_TOKEN,
  installEvaluationFixture,
  populatedJob,
  type EvaluationFixture,
} from "./evaluation-fixtures";

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
  await page.getByRole("tab", { name: "Private jobs" }).click();
  const form = page.locator(".evaluation-connect form");
  await form.getByLabel("Local workspace token").fill(EVALUATION_FIXTURE_TOKEN);
  await form.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(page.getByText(/Connected · (execution enabled|read only)/)).toBeVisible();
}

async function noHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => ({
    body: document.body.scrollWidth - document.body.clientWidth,
    root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }))).toEqual({ body: 0, root: 0 });
}

test.describe("UI-011 Evaluation", () => {
  test.describe.configure({ mode: "serial" });
  test("direct public load exposes the exact six native definitions without private auth", async ({ page }, testInfo) => {
    const fixture = await installEvaluationFixture(page);
    await page.addInitScript(() => localStorage.setItem("theme", "dark"));
    await page.setViewportSize(VIEWPORTS[0]);
    await page.goto("/evaluation");

    await expect(page.getByRole("heading", { name: "Evaluation", exact: true })).toBeVisible();
    for (const label of ["Faithfulness", "Answer relevancy", "Context precision", "Citation index validity", "Keyword recall proxy", "Fallback correctness"]) {
      await expect(page.getByRole("heading", { name: label, exact: true })).toBeVisible();
    }
    const citationMetric = page.locator(".evaluation-metric").filter({ has: page.getByRole("heading", { name: "Citation index validity" }) });
    await citationMetric.getByText(/Definition · v1/).click();
    await expect(citationMetric.getByText("native.citation_index_validity")).toBeVisible();
    await expect(citationMetric.getByText(/not claim support/i)).toBeVisible();
    const keywordMetric = page.locator(".evaluation-metric").filter({ has: page.getByRole("heading", { name: "Keyword recall proxy" }) });
    await keywordMetric.getByText(/Definition · v1/).click();
    await expect(keywordMetric.getByText(/not Recall@K/i)).toBeVisible();
    await expect(page.getByText(/No substitute data, demo trends or inferred scores/)).toHaveCount(0);
    expect(fixture.calls.filter((call) => call.path.startsWith("/evaluation/") && !call.path.startsWith("/evaluation/jobs")).every((call) => call.authorization === null)).toBe(true);
    expect(fixture.calls.some((call) => call.path.startsWith("/evaluation/jobs"))).toBe(false);
    await page.screenshot({ path: testInfo.outputPath("evaluation-reference-native-default.png"), animations: "disabled" });
  });

  test("published report deep links, pages safe results, and honors browser history", async ({ page }) => {
    await installEvaluationFixture(page);
    await page.goto("/evaluation/runs/baseline-native");
    const detail = page.getByRole("complementary", { name: "Report detail" });
    await expect(detail.getByRole("heading", { name: "baseline-native" })).toBeVisible();
    await expect(detail.getByText("0.000").first()).toBeVisible();
    await expect(detail.getByText("False")).toBeVisible();
    await expect(detail.getByText("Unavailable")).toBeVisible();
    await expect(detail.getByText("Not applicable")).toBeVisible();
    await expect(page.getByText("3 / 5").first()).toBeVisible();
    await detail.getByRole("button", { name: "Next" }).click();
    await expect(detail.getByText("safe-case-2")).toBeVisible();
    await page.getByRole("button", { name: /candidate-native/ }).click();
    await expect(page).toHaveURL(/\/evaluation\/runs\/candidate-native$/);
    await page.goBack();
    await expect(page).toHaveURL(/\/evaluation\/runs\/baseline-native$/);
    await expect(detail.getByRole("heading", { name: "baseline-native" })).toBeVisible();
    await page.goForward();
    await expect(page).toHaveURL(/\/evaluation\/runs\/candidate-native$/);
    await expect(detail.getByRole("heading", { name: "candidate-native" })).toBeVisible();
  });

  test("comparison preserves backend deltas, counts and incompatibility without winner claims", async ({ page }, testInfo) => {
    await installEvaluationFixture(page);
    await page.goto("/evaluation");
    await page.getByRole("tab", { name: "Compare", exact: true }).click();
    await page.locator(".evaluation-tool-form select").nth(0).selectOption("baseline-native");
    await page.locator(".evaluation-tool-form select").nth(1).selectOption("candidate-native");
    await page.getByRole("button", { name: "Compare", exact: true }).click();

    await expect(page.getByText("Not fully compatible")).toBeVisible();
    await expect(page.getByText("context_binding_mismatch").first()).toBeVisible();
    await expect(page.getByText("computed_case_coverage_mismatch")).toBeVisible();
    await expect(page.getByText("+0.500").first()).toBeVisible();
    await expect(page.getByText("Not reported").first()).toBeVisible();
    await expect(page.getByText("3 / 5").first()).toBeVisible();
    await expect(page.getByText(/^winner$/i)).toHaveCount(0);
    await expect(page.getByText(/not a winner or statistical-significance claim/i)).toBeVisible();
    await expect(page.getByText(/confidence interval/i)).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath("evaluation-compare-incompatible.png"), animations: "disabled", fullPage: true });
  });

  test("trends show truthful empty history or separate real backend observations without interpolation", async ({ page }, testInfo) => {
    await installEvaluationFixture(page);
    await page.goto("/evaluation");
    await page.getByRole("tab", { name: "Trends" }).click();
    await expect(page.getByText("No published native trend history")).toBeVisible();
    await expect(page.getByText(/No demo or interpolated observations/)).toBeVisible();
    await expect(page.locator(".evaluation-trend-groups")).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath("evaluation-trends-empty.png"), animations: "disabled" });
  });

  test("real trends render exact point observations and a text equivalent", async ({ page }, testInfo) => {
    await installEvaluationFixture(page, { realTrends: true });
    await page.goto("/evaluation");
    await page.getByRole("tab", { name: "Trends" }).click();
    await expect(page.getByText(/2 backend observations/)).toBeVisible();
    await expect(page.locator(".evaluation-trend-groups circle")).toHaveCount(2);
    await expect(page.locator(".evaluation-trend-groups path, .evaluation-trend-groups polyline")).toHaveCount(0);
    await expect(page.getByText(/Missing points are not connected, smoothed, or forecast/)).toBeVisible();
    await expect(page.getByRole("cell", { name: "0.250" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "0.750" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("evaluation-trends-real.png"), animations: "disabled", fullPage: true });
  });

  test("failure analysis uses only the four backend categories and no hidden text", async ({ page }, testInfo) => {
    await installEvaluationFixture(page);
    await page.goto("/evaluation");
    await page.getByRole("tab", { name: "Failures" }).click();
    for (const category of ["Fallback expectation mismatch", "Invalid citation indices", "Missing required keywords", "Unavailable prerequisites"]) {
      await expect(page.locator(".evaluation-failure-bars").getByText(category)).toBeVisible();
    }
    await expect(page.getByText(/not automatically a model failure/i)).toBeVisible();
    await expect(page.getByText("False", { exact: true })).toBeVisible();
    await expect(page.getByText("Unavailable", { exact: true })).toBeVisible();
    await expect(page.getByText(/hallucination|poor quality|bad answer/i)).toHaveCount(0);
    expect(await page.locator("body").innerText()).not.toMatch(/HIDDEN_(QUESTION|ANSWER|GROUND_TRUTH|EVIDENCE)_UI011/);
    await page.screenshot({ path: testInfo.outputPath("evaluation-failures.png"), animations: "disabled", fullPage: true });
  });

  test("private-unavailable mode remains public and reports the failed explicit connection", async ({ page }, testInfo) => {
    const fixture = await installEvaluationFixture(page, { mode: "public" });
    await page.goto("/evaluation");
    await page.getByRole("tab", { name: "Private jobs" }).click();
    const form = page.locator(".evaluation-connect form");
    await form.getByLabel("Local workspace token").fill(EVALUATION_FIXTURE_TOKEN);
    await form.getByRole("button", { name: "Connect", exact: true }).click();
    await expect(form.getByRole("alert")).toContainText("local workspace is unavailable");
    expect(fixture.calls.some((call) => call.path.startsWith("/evaluation/jobs"))).toBe(false);
    expect(JSON.stringify(await page.evaluate(() => ({ local: Object.entries(localStorage), session: Object.entries(sessionStorage), url: location.href, text: document.body.innerText })))).not.toContain(EVALUATION_FIXTURE_TOKEN);
    await page.screenshot({ path: testInfo.outputPath("evaluation-private-unavailable.png"), animations: "disabled" });
  });

  test("shared memory-only session creates exactly one canonical queued job with the frozen two-step plan", async ({ page }, testInfo) => {
    const fixture = await installEvaluationFixture(page);
    await page.goto("/evaluation");
    await connect(page);
    await page.getByRole("button", { name: "New evaluation" }).click();
    const dialog = page.getByRole("dialog", { name: "Create a frozen evaluation" });
    await dialog.getByLabel("Registered artifact ID").fill("synthetic-phase1");
    await dialog.getByLabel("Provider attempt slot budget").fill("6");
    await dialog.getByRole("button", { name: "Freeze and queue" }).evaluate((button) => {
      (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click();
    });

    await expect(page).toHaveURL(/\/evaluation\/runs\/job-canonical-1\?source=job$/);
    await expect(page.getByRole("heading", { name: "job-canonical-1" })).toBeVisible();
    await expect(page.locator(".evaluation-job-detail .evaluation-state")).toHaveText("queued");
    await expect(page.getByText("execute_cases")).toBeVisible();
    await expect(page.getByText("aggregate_report")).toBeVisible();
    await expect(page.getByText(/0 \/ 6 provider_attempt_slot/).first()).toBeVisible();
    await expect(page.getByText(/Unknown/)).toBeVisible();
    await expect(page.getByText(/Frozen snapshot · not editable/)).toBeVisible();
    expect(fixture.createCount()).toBe(1);
    const create = fixture.calls.find((call) => call.method === "POST" && call.path === "/evaluation/jobs");
    expect(create?.authorization).toBe(`Bearer ${EVALUATION_FIXTURE_TOKEN}`);
    expect(JSON.stringify(await page.evaluate(() => ({ local: Object.entries(localStorage), session: Object.entries(sessionStorage), url: location.href, text: document.body.innerText })))).not.toContain(EVALUATION_FIXTURE_TOKEN);
    await page.screenshot({ path: testInfo.outputPath("evaluation-job-queued.png"), animations: "disabled", fullPage: true });
  });

  test("job events reconcile durable running state and private result projection drops raw case text", async ({ page }, testInfo) => {
    const fixture = await installEvaluationFixture(page, { jobs: [populatedJob("job-live")] });
    await page.goto("/evaluation/runs/job-live?source=job");
    await connect(page);
    await expect(page.getByRole("heading", { name: "job-live" })).toBeVisible();
    await expect.poll(() => fixture.calls.some((call) => call.path === "/evaluation/jobs/job-live/events" && call.lastEventId === "1"), { timeout: 15_000 }).toBe(true);
    fixture.emitState("job-live", "running");
    await expect(page.locator(".evaluation-job-detail .evaluation-state").first()).toHaveText("running", { timeout: 6_000 });
    await expect(page.getByText("1 / 2 · execute_cases")).toBeVisible();
    await expect(page.getByText("safe-private-case")).toBeVisible();
    await expect(page.getByText("False", { exact: true })).toBeVisible();
    expect(await page.locator("body").innerText()).not.toMatch(/HIDDEN_(QUESTION|ANSWER|GROUND_TRUTH|EVIDENCE)_UI011/);
    await page.screenshot({ path: testInfo.outputPath("evaluation-job-running-results.png"), animations: "disabled", fullPage: true });
  });

  test("budget exhaustion, cancellation conflict, cancelling and interrupted remain distinct", async ({ page }, testInfo) => {
    const budget = populatedJob("job-budget", "failed", { failure: { code: "budget_exhausted", message: "Provider attempt slot budget was exhausted." }, budget_consumed: 6 });
    const running = populatedJob("job-cancel", "running");
    const interrupted = populatedJob("job-interrupted", "interrupted");
    const fixture = await installEvaluationFixture(page, { jobs: [budget, running, interrupted] });
    await page.goto("/evaluation/runs/job-budget?source=job");
    await connect(page);
    await expect(page.getByText("budget_exhausted")).toBeVisible();
    await expect(page.getByText(/not a zero score or generic model failure/)).toBeVisible();
    await page.locator(".evaluation-job-cards button").filter({ hasText: "job-cancel" }).click();
    fixture.forceConflictOnce();
    await page.getByRole("button", { name: "Request cancellation" }).click();
    await expect(page.getByRole("alert")).toContainText("Revision, state or report compatibility conflict");
    await page.getByRole("button", { name: "Request cancellation" }).click();
    await expect(page.locator(".evaluation-job-detail .evaluation-state").first()).toHaveText("cancelling");
    expect(fixture.cancelCount()).toBe(2);
    expect(fixture.calls.filter((call) => call.path.endsWith("/cancel"))[1]?.ifMatch).toBe('"2"');
    await page.locator(".evaluation-job-cards button").filter({ hasText: "job-interrupted" }).click();
    await expect(page.getByText(/Interrupted is terminal/)).toBeVisible();
    await expect(page.getByRole("button", { name: /resume|retry|restart/i })).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath("evaluation-budget-cancel-interrupted.png"), animations: "disabled", fullPage: true });
  });

  test("Vietnamese mode keeps native identities while translating workspace semantics", async ({ page }, testInfo) => {
    await installEvaluationFixture(page);
    await page.goto("/evaluation");
    await page.getByRole("button", { name: "VI", exact: true }).click();
    await expect(page.getByText(/Định nghĩa native, báo cáo public/)).toBeVisible();
    await expect(page.getByRole("tab", { name: "So sánh" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Xu hướng" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Jobs riêng tư" })).toBeVisible();
    await expect(page.getByText("native.citation_index_validity")).toHaveCount(1);
    await page.screenshot({ path: testInfo.outputPath("evaluation-vi-light.png"), animations: "disabled" });
  });

  test("reference, desktop, compact, mobile and short-height layouts have no root overflow and pass axe", async ({ page }, testInfo) => {
    await installEvaluationFixture(page, { jobs: [populatedJob("job-reference", "running")] });
    await page.addInitScript(() => localStorage.setItem("theme", "dark"));
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize(VIEWPORTS[0]);
    await page.goto("/evaluation/runs/baseline-native");
    await expect(page.getByRole("heading", { name: "baseline-native" })).toBeVisible();
    await noHorizontalOverflow(page);
    const geometry = await page.evaluate(() => {
      const rect = (selector: string) => { const value = document.querySelector(selector)?.getBoundingClientRect(); return value ? { x: Math.round(value.x), y: Math.round(value.y), width: Math.round(value.width), height: Math.round(value.height) } : null; };
      return { header: rect(".console-page-header"), metrics: rect(".evaluation-metrics"), overview: rect(".evaluation-overview"), reports: rect(".evaluation-reports"), detail: rect(".evaluation-report-detail") };
    });
    expect(geometry.metrics?.width).toBeGreaterThan(900);
    expect(geometry.detail?.x).toBeGreaterThan(geometry.reports?.x ?? 0);
    await page.screenshot({ path: testInfo.outputPath("evaluation-1586x992-report.png"), animations: "disabled", fullPage: true });

    for (const viewport of VIEWPORTS.slice(1)) {
      await page.setViewportSize(viewport);
      await expect(page.getByRole("heading", { name: "Evaluation", exact: true })).toBeVisible();
      await noHorizontalOverflow(page);
      await page.screenshot({ path: testInfo.outputPath(`evaluation-${viewport.name}.png`), animations: "disabled", fullPage: viewport.width <= 390 });
    }
    const accessibility = await new AxeBuilder({ page }).include(".evaluation-workspace").withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(accessibility.violations).toEqual([]);
  });
});
