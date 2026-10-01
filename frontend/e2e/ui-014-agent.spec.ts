import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { AGENT_FIXTURE_TOKEN, installAgentFixture } from "./agent-fixtures";
import { agentResearchRun, agentRunningRun } from "../src/test/agentFixtures";

async function connect(page: Page, locale: "en" | "vi" = "en") {
  const label = locale === "vi" ? "Kết nối workspace cục bộ" : "Connect local workspace";
  await page.getByRole("button", { name: label }).first().click();
  const dialog = page.getByRole("dialog", { name: label });
  await dialog.getByLabel(locale === "vi" ? "Token workspace cục bộ" : "Local workspace token").fill(AGENT_FIXTURE_TOKEN);
  await dialog.getByRole("button", { name: locale === "vi" ? "Xác minh và kết nối" : "Verify and connect" }).click();
  await expect(dialog).toBeHidden();
}

async function noHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => ({
    body: document.body.scrollWidth - document.body.clientWidth,
    root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }))).toEqual({ body: 0, root: 0 });
}

test.describe("UI-014 Agent workspace", () => {
  test("keeps private history gated and forgets the bearer after reload", async ({ page }) => {
    const fixture = await installAgentFixture(page);
    await page.goto(`/agent/runs/${agentResearchRun.run_id}`);
    await expect(page.getByRole("heading", { name: "Private workspace disconnected" })).toBeVisible();
    expect(fixture.calls).toEqual([]);
    await connect(page);
    await expect(page.getByRole("heading", { name: "Research objectives" })).toBeVisible();
    expect(fixture.calls.filter((call) => call.path.startsWith("/agent/runs")).every((call) => call.authorized)).toBe(true);
    expect(await page.evaluate(() => JSON.stringify({ local: localStorage, session: sessionStorage, cookie: document.cookie, url: location.href }))).not.toContain(AGENT_FIXTURE_TOKEN);
    await page.reload();
    await expect(page.getByRole("heading", { name: "Private workspace disconnected" })).toBeVisible();
    expect(fixture.calls.filter((call) => call.method === "GET").every((call) => call.authorized)).toBe(true);
  });

  test("renders recorded research, safe activity, all native metrics and provenance", async ({ page }, testInfo) => {
    const fixture = await installAgentFixture(page);
    await page.goto(`/agent/runs/${agentResearchRun.run_id}`);
    await connect(page);
    await expect(page.getByRole("heading", { name: "Research objectives" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Native Agent evaluation" })).toBeVisible();
    await expect(page.locator(".agent-metric")).toHaveCount(21);
    await expect(page.locator(".agent-trace-item")).toHaveCount(9);
    await expect(page.getByText(agentResearchRun.result!.answer!)).toBeVisible();
    await expect(page.getByText("Search attempts exhausted").first()).toBeVisible();
    await expect(page.getByText("MSFT:10-K:2025:chunk-1")).toBeVisible();
    await expect(page.getByText("0.6000")).toBeVisible();
    await expect(page.getByText("No overall score or factual correctness claim.", { exact: false })).toBeVisible();
    expect(await page.locator(".agent-workspace").innerText()).not.toMatch(/chain of thought|agent thoughts|overall agent score/i);
    await expect.poll(() => fixture.calls.some((call) => call.path.endsWith("/events") && call.lastEventId === "9")).toBe(true);
    await page.screenshot({ path: testInfo.outputPath("agent-research-desktop.png"), animations: "disabled", fullPage: true });
  });

  test("creates a real recorded research run and reports provider unavailability", async ({ page }) => {
    const fixture = await installAgentFixture(page, { initialRuns: [] });
    await page.goto("/agent");
    await connect(page);
    await expect(page.getByText("No Agent runs recorded in this local workspace.")).toBeVisible();
    await page.getByRole("button", { name: "Create recorded run" }).click();
    const dialog = page.getByRole("dialog", { name: "Create a recorded Agent run" });
    await dialog.getByRole("button", { name: "Create run" }).click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    await dialog.getByLabel("Goal").fill("Review Microsoft AI risk evidence.");
    await dialog.getByLabel("Mode").selectOption("research");
    await dialog.getByLabel("Question").fill("Find Microsoft AI risk evidence");
    await dialog.getByLabel("Ticker scope (optional)").fill("MSFT");
    await dialog.getByRole("button", { name: "Create run" }).click();
    await expect(page).toHaveURL(/\/agent\/runs\/agent_created_1$/);
    await expect(page.getByText("No final answer was recorded for this outcome.")).toBeVisible();
    expect(fixture.createCount()).toBe(1);
    expect(fixture.calls.find((call) => call.method === "POST" && call.path === "/agent/runs")?.authorized).toBe(true);
  });

  test("reconciles revision conflicts and never calls a cancelling run cancelled", async ({ page }) => {
    const fixture = await installAgentFixture(page, { initialRuns: [agentRunningRun] });
    await page.goto(`/agent/runs/${agentRunningRun.run_id}`);
    await connect(page);
    const detail = page.locator(".agent-run-detail");
    await expect(detail.getByRole("button", { name: "Request cancellation" })).toBeVisible();
    fixture.forceConflictOnce();
    await detail.getByRole("button", { name: "Request cancellation" }).click();
    await expect(detail.getByText("The run changed before cancellation.", { exact: false })).toBeVisible();
    await expect(detail.getByRole("button", { name: "Request cancellation" })).toBeVisible();
    await detail.getByRole("button", { name: "Request cancellation" }).click();
    await expect(detail.getByText("Cancellation requested. An in-flight call may continue", { exact: false })).toBeVisible();
    await expect(detail.getByRole("button", { name: "Request cancellation" })).toHaveCount(0);
    expect(fixture.cancelCount()).toBe(2);
    expect(fixture.calls.filter((call) => call.path.endsWith("/cancel")).map((call) => call.ifMatch)).toEqual(['"3"', '"4"']);
  });

  test("keeps public mode unavailable and execution-disabled local access read only", async ({ page }) => {
    const publicFixture = await installAgentFixture(page, { mode: "public" });
    await page.goto("/agent");
    await page.getByRole("button", { name: "Connect local workspace" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Connect local workspace" });
    await dialog.getByLabel("Local workspace token").fill(AGENT_FIXTURE_TOKEN);
    await dialog.getByRole("button", { name: "Verify and connect" }).click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    expect(publicFixture.calls).toEqual([]);
    await page.reload();
    const localFixture = await installAgentFixture(page, { executionEnabled: false });
    await connect(page);
    await expect(page.getByText("Local access · execution disabled")).toBeVisible();
    await expect(page.getByRole("button", { name: "Create recorded run" })).toHaveCount(0);
    await page.getByRole("button", { name: "Inspect current filings.", exact: false }).click();
    await expect(page.getByRole("button", { name: "Request cancellation" })).toHaveCount(0);
    expect(localFixture.createCount()).toBe(0);
  });

  test("uses canonical run URLs, browser history and an honest unknown-run state", async ({ page }) => {
    await installAgentFixture(page);
    await page.goto("/agent/runs/agent_missing");
    await connect(page);
    await expect(page.getByText("This Agent run was not found.", { exact: false })).toBeVisible();
    await page.getByRole("button", { name: agentResearchRun.frozen.goal, exact: false }).click();
    await expect(page).toHaveURL(/\/agent\/runs\/agent_alpha$/);
    await expect(page.getByRole("heading", { name: "Research objectives" })).toBeVisible();
    await page.goBack();
    await expect(page).toHaveURL(/\/agent\/runs\/agent_missing$/);
    await expect(page.getByText("This Agent run was not found.", { exact: false })).toBeVisible();
    await page.goForward();
    await expect(page).toHaveURL(/\/agent\/runs\/agent_alpha$/);
    await expect(page.getByRole("heading", { name: "Research objectives" })).toBeVisible();
  });

  test("supports Vietnamese and responsive light/dark layouts with accessible states", async ({ page }, testInfo) => {
    await page.addInitScript(() => { localStorage.setItem("sec_qa_locale", "vi"); localStorage.setItem("theme", "dark"); });
    await installAgentFixture(page);
    await page.goto(`/agent/runs/${agentResearchRun.run_id}`);
    expect((await new AxeBuilder({ page }).include(".agent-workspace").analyze()).violations).toEqual([]);
    await page.getByRole("button", { name: "Kết nối workspace cục bộ" }).first().click();
    expect((await new AxeBuilder({ page }).include('[role="dialog"]').analyze()).violations).toEqual([]);
    const dialog = page.getByRole("dialog", { name: "Kết nối workspace cục bộ" });
    await dialog.getByLabel("Token workspace cục bộ").fill(AGENT_FIXTURE_TOKEN);
    await dialog.getByRole("button", { name: "Xác minh và kết nối" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByRole("heading", { name: "Mục tiêu nghiên cứu" })).toBeVisible();
    await expect(page.locator(".agent-metric")).toHaveCount(21);
    await expect(page.locator(".agent-trace-item")).toHaveCount(9);
    for (const viewport of [{ width: 1440, height: 900 }, { width: 1024, height: 768 }, { width: 768, height: 900 }, { width: 390, height: 844 }, { width: 1440, height: 700 }]) {
      await page.setViewportSize(viewport);
      await noHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: "Lần chạy đã chọn" })).toBeVisible();
      if (viewport.width === 390) await page.screenshot({ path: testInfo.outputPath("agent-vi-dark-mobile.png"), animations: "disabled", fullPage: true });
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    expect((await new AxeBuilder({ page }).include(".agent-workspace").analyze()).violations).toEqual([]);
    await page.addInitScript(() => localStorage.setItem("theme", "light"));
    await page.reload();
    await connect(page, "vi");
    await noHorizontalOverflow(page);
    expect((await new AxeBuilder({ page }).include(".agent-workspace").analyze()).violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath("agent-vi-light-desktop.png"), animations: "disabled", fullPage: true });
  });
});
