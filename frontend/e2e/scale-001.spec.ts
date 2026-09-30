import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const API = "http://127.0.0.1:8790";
const TOKEN = "SCALE001_SYNTHETIC_BEARER_BROWSER_719C";
const KEY = "SCALE001_SYNTHETIC_PROVIDER_KEY_72CD";
const headers = { Authorization: `Bearer ${TOKEN}`, Origin: "http://localhost:4191" };

async function control(page: Page, action: string) {
  const response = await page.request.post(`${API}/__scale001__/control`, { data: { action } });
  expect(response.status()).toBe(200);
  return response.json();
}
async function state(page: Page) {
  return (await page.request.get(`${API}/__scale001__/state`)).json();
}
async function connect(page: Page) {
  await page.getByRole("button", { name: "Connect local workspace" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Local workspace token").fill(TOKEN);
  await dialog.getByRole("button", { name: "Verify and connect" }).click();
  await expect(dialog).toBeHidden();
}
async function setup(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/*", async route => {
    if ([API, "http://localhost:4191"].includes(new URL(route.request().url()).origin)) await route.continue();
    else await route.abort();
  });
  await page.goto("/agent");
  await expect(page.locator(".agent-workspace")).toBeVisible();
  await connect(page);
}
async function create(page: Page, research = false) {
  await page.getByRole("button", { name: "Create recorded run" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Goal").fill("Research worker-owned Apple risk evidence.");
  if (research) {
    await dialog.getByLabel("Mode").selectOption("research");
    await dialog.getByLabel("Question", { exact: true }).fill("Find Apple risk evidence");
    await dialog.getByLabel("Ticker scope (optional)").fill("AAPL");
  }
  const consent = dialog.getByRole("checkbox");
  if (await consent.isEnabled()) await consent.check();
  const response = page.waitForResponse(response => response.url().endsWith("/agent/runs") && response.request().method() === "POST");
  await dialog.getByRole("button", { name: "Create run", exact: true }).click();
  const created = await response;
  expect(created.status()).toBe(201);
  const run = await created.json();
  expect(run.state).toBe("queued");
  await expect(page).toHaveURL(new RegExp(`/agent/runs/${run.run_id}$`));
  await expect(page.locator(".agent-run-detail .agent-state--queued")).toBeVisible();
  return run.run_id as string;
}
async function noLeaks(page: Page) {
  const content = await page.locator(".agent-workspace").innerText();
  expect(content).not.toContain(KEY); expect(content).not.toContain(TOKEN);
  expect(content).not.toContain("CONTROL_JSON");
  expect(await page.evaluate(() => JSON.stringify({ local: localStorage, session: sessionStorage, cookie: document.cookie }))).not.toContain(TOKEN);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
  expect((await new AxeBuilder({ page }).include(".agent-workspace").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()).violations).toEqual([]);
}

test("worker owns queued → running → research result and evaluation without refresh", async ({ page }, info) => {
  await control(page, "reset");
  await setup(page);
  const id = await create(page, true);
  expect((await state(page)).attempts).toBe(0);
  await control(page, "start");
  await expect.poll(async () => (await state(page)).entered).toBe(true);
  await expect(page.locator(".agent-run-detail .agent-state--running")).toBeVisible();
  expect(await state(page)).toMatchObject({ attempts: 1, workers: 2, active: 1,
    eligible: [["agent", "bounded_agent_run"]] });
  await page.screenshot({ path: info.outputPath("worker-running.png"), fullPage: true });
  await control(page, "release");
  await expect(page.locator(".agent-run-detail .agent-state--succeeded")).toBeVisible();
  await expect(page.getByText("Worker-owned Apple evidence summary.")).toBeVisible();
  await expect(page.locator(".agent-metric")).toHaveCount(21);
  const run = await (await page.request.get(`${API}/agent/runs/${id}`, { headers })).json();
  expect(run.result).toMatchObject({ agent_status: "completed", decision_call_count: 3, tool_call_count: 2 });
  expect(run.result.research.objectives[0].coverage).toBe("sufficient");
  expect((await state(page)).attempts).toBe(3);
  const stream = await page.request.get(`${API}/agent/runs/${id}/events`, { headers });
  expect(await stream.text()).toContain("event: agent_decision");
  const resumed = await page.request.get(`${API}/agent/runs/${id}/events`, { headers: { ...headers, "Last-Event-ID": "3" } });
  expect(await resumed.text()).not.toContain("id: 1\n");
  await noLeaks(page);
  await page.screenshot({ path: info.outputPath("worker-result.png"), fullPage: true });
});

test("queued cancellation prevents any worker transport", async ({ page }) => {
  await control(page, "reset");
  await setup(page);
  await create(page);
  await page.locator(".agent-run-detail").getByRole("button", { name: "Request cancellation" }).click();
  await expect(page.locator(".agent-run-detail .agent-state--cancelled")).toBeVisible();
  await control(page, "start");
  expect((await state(page)).attempts).toBe(0);
  await expect(page.locator(".agent-metric")).toHaveCount(21);
  await noLeaks(page);
});

test("running cancellation remains cancelling until in-flight transport returns", async ({ page }) => {
  await control(page, "reset");
  await setup(page);
  const id = await create(page);
  await control(page, "start");
  await expect.poll(async () => (await state(page)).entered).toBe(true);
  await expect(page.locator(".agent-run-detail .agent-state--running")).toBeVisible();
  await page.locator(".agent-run-detail").getByRole("button", { name: "Request cancellation" }).click();
  await expect(page.locator(".agent-run-detail .agent-state--cancelling")).toBeVisible();
  await expect(page.getByText("Cancellation requested. An in-flight call may continue", { exact: false })).toBeVisible();
  await control(page, "release");
  await expect(page.locator(".agent-run-detail .agent-state--cancelled")).toBeVisible();
  const run = await (await page.request.get(`${API}/agent/runs/${id}`, { headers })).json();
  expect(run.result.tool_call_count).toBe(0);
  expect((await state(page)).attempts).toBe(1);
  await noLeaks(page);
});

test("unavailable provider completes truthfully through worker ownership", async ({ page }) => {
  await control(page, "missing");
  await setup(page);
  await create(page);
  await control(page, "start");
  await expect(page.locator(".agent-run-detail .agent-state--failed")).toBeVisible();
  await expect(page.getByText("Structured Agent decision provider is not configured for production execution.", { exact: true })).toBeVisible();
  await expect(page.locator(".agent-metric")).toHaveCount(21);
  expect((await state(page)).attempts).toBe(0);
  await noLeaks(page);
});
