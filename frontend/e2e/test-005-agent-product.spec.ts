import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const API = "http://127.0.0.1:8788";
const PUBLIC = "http://127.0.0.1:8787";
const APP = "http://localhost:4187";
const TOKEN = "test005-synthetic-local-token-0123456789abcdef";
const headers = { Authorization: `Bearer ${TOKEN}`, Origin: APP };

async function setup(page: Page, route: string, variant = { theme: "light", locale: "en" }) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(value => {
    localStorage.setItem("theme", value.theme);
    localStorage.setItem("sec_qa_locale", value.locale);
  }, variant);
  await page.route("**/*", async route => {
    if ([API, PUBLIC, APP].includes(new URL(route.request().url()).origin)) await route.continue();
    else await route.abort();
  });
  await page.goto(route);
  await expect(page.locator(".agent-workspace")).toBeVisible();
}

async function connect(page: Page, locale: "en" | "vi" = "en") {
  const title = locale === "vi" ? "Kết nối workspace cục bộ" : "Connect local workspace";
  await page.getByRole("button", { name: title }).first().click();
  const dialog = page.getByRole("dialog", { name: title });
  await dialog.getByLabel(locale === "vi" ? "Token workspace cục bộ" : "Local workspace token").fill(TOKEN);
  await dialog.getByRole("button", { name: locale === "vi" ? "Xác minh và kết nối" : "Verify and connect" }).click();
  await expect(dialog).toBeHidden();
}

async function mode(page: Page, name: "unconfigured" | "research" | "waiting") {
  expect((await page.request.post(`${API}/__test005__/agent/mode`, { data: { mode: name } })).status()).toBe(200);
}

async function create(page: Page, name: string, body: object): Promise<string> {
  const response = await page.request.post(`${API}/agent/runs`, {
    headers: { ...headers, "Idempotency-Key": `test005-${test.info().project.name}-${name}` }, data: body,
  });
  expect(response.status()).toBe(201);
  const run = await response.json();
  expect(run.run_id).toMatch(/^agent_[a-z0-9]+$/);
  return run.run_id;
}

async function run(page: Page, id: string) {
  const response = await page.request.get(`${API}/agent/runs/${id}`, { headers });
  expect(response.status()).toBe(200);
  return response.json();
}

async function terminal(page: Page, id: string) {
  await expect.poll(async () => (await run(page, id)).state, { timeout: 15_000 }).toMatch(/^(succeeded|failed|cancelled|interrupted)$/);
  return run(page, id);
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => ({
    body: document.body.scrollWidth - document.body.clientWidth,
    root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }))).toEqual({ body: 0, root: 0 });
}

async function axeAgent(page: Page) {
  const result = await new AxeBuilder({ page }).include(".agent-workspace")
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(result.violations.map(item => ({ id: item.id, targets: item.nodes.map(node => node.target) }))).toEqual([]);
}

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => {
    if (message.type() === "error" && !message.text().startsWith("Failed to load resource:")) errors.push(message.text());
  });
  (page as Page & { agentErrors?: string[] }).agentErrors = errors;
});

test.afterEach(async ({ page }) => {
  expect((page as Page & { agentErrors?: string[] }).agentErrors).toEqual([]);
});

test("A disconnected and public access never reveal private Agent history", async ({ page }) => {
  const privateCalls: string[] = [];
  page.on("request", request => {
    if (new URL(request.url()).pathname.startsWith("/agent/runs")) privateCalls.push(request.url());
  });
  await setup(page, "/agent");
  await expect(page.getByRole("heading", { name: "Private workspace disconnected" })).toBeVisible();
  expect(privateCalls).toEqual([]);
  expect((await page.request.get(`${PUBLIC}/agent/runs`)).status()).toBe(404);
  expect((await page.request.get(`${API}/agent/runs`)).status()).toBe(401);
  expect((await page.request.get(`${API}/agent/runs`, { headers: { ...headers, Authorization: "Bearer wrong" } })).status()).toBe(401);
  expect((await page.request.get(`${API}/agent/runs`, { headers })).status()).toBe(200);
  await axeAgent(page);
  await noOverflow(page);
});

test("B production run truthfully reports decision-provider unavailability", async ({ page }, testInfo) => {
  await mode(page, "unconfigured");
  await setup(page, "/agent");
  await connect(page);
  await page.getByRole("button", { name: "Create recorded run" }).click();
  const dialog = page.getByRole("dialog", { name: "Create a recorded Agent run" });
  await expect(dialog).toContainText("execution ends with decision-provider unavailability");
  await dialog.getByLabel("Goal").fill("Inspect recorded Agent availability.");
  await dialog.getByRole("button", { name: "Create run" }).click();
  await expect(page).toHaveURL(/\/agent\/runs\/agent_[a-z0-9]+$/);
  const id = new URL(page.url()).pathname.split("/").at(-1)!;
  const detail = await terminal(page, id);
  expect(detail.state).toBe("failed");
  expect(detail.result).toMatchObject({ agent_status: "unavailable", tool_call_count: 0,
    failure: { code: "decision_provider_unavailable" } });
  expect(detail.result.answer).toBeNull();
  const result = await (await page.request.get(`${API}/agent/runs/${id}/results`, { headers })).json();
  expect(result.result.tool_call_count).toBe(0);
  const report = await (await page.request.get(`${API}/agent/runs/${id}/evaluation`, { headers })).json();
  expect(report.metrics).toHaveLength(21);
  expect(report.metrics.find((metric: { metric_id: string }) => metric.metric_id === "native_agent.decision_provider_unavailable"))
    .toMatchObject({ status: "computed", value: true });
  await expect(page.getByText("No final answer was recorded for this outcome.")).toBeVisible();
  await expect(page.locator(".agent-metric")).toHaveCount(21);
  expect(await page.locator(".agent-workspace").innerText()).not.toMatch(/chain of thought|scratchpad|hidden reasoning/i);
  await axeAgent(page);
  await page.screenshot({ path: testInfo.outputPath("agent-real-provider-unavailable.png"), animations: "disabled" });
  expect(await page.evaluate(() => JSON.stringify({ local: localStorage, session: sessionStorage, cookie: document.cookie,
    url: location.href, dom: document.documentElement.outerHTML }))).not.toContain(TOKEN);
  const indexedDbValues = await page.evaluate(async () => {
    if (typeof indexedDB.databases !== "function") return "unsupported";
    const values: unknown[] = [];
    for (const entry of await indexedDB.databases()) {
      if (!entry.name) continue;
      const database = await new Promise<IDBDatabase>((resolve, reject) => {
        const request = indexedDB.open(entry.name!);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      for (const name of Array.from(database.objectStoreNames)) {
        const request = database.transaction(name, "readonly").objectStore(name).getAll();
        values.push(await new Promise<unknown[]>((resolve, reject) => {
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        }));
      }
      database.close();
    }
    return JSON.stringify(values);
  });
  expect(indexedDbValues).not.toContain(TOKEN);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Private workspace disconnected" })).toBeVisible();
  await connect(page);
  await page.getByRole("button", { name: "Disconnect" }).click();
  await expect(page.getByRole("heading", { name: "Private workspace disconnected" })).toBeVisible();
  expect(await page.locator(".agent-workspace").innerText()).not.toContain(id);
});

test("C scripted research crosses real Agent routes, durable events and evaluation", async ({ page }, testInfo) => {
  await mode(page, "research");
  const id = await create(page, "research", { goal: "Find recorded Apple risk evidence.",
    research: { version: "agent_research_v1", objectives: [
      { objective_id: "apple_risk", question: "Find Apple risk evidence", ticker_scope: "AAPL" },
    ] },
  });
  const detail = await terminal(page, id);
  expect(detail.state).toBe("succeeded");
  expect(detail.result.agent_status).toBe("completed");
  expect(detail.result.tool_call_count).toBe(2);
  expect(detail.result.research.objectives[0]).toMatchObject({ objective_id: "apple_risk", coverage: "sufficient" });
  expect(detail.result.research.evidence[0]).toMatchObject({ document_id: "AAPL:HARNESS", chunk_id: "AAPL_harness_0000",
    objective_ids: ["apple_risk"] });
  expect(detail.result.research.gaps).toEqual([]);
  const stream = await page.request.get(`${API}/agent/runs/${id}/events`, { headers });
  expect(stream.status()).toBe(200);
  const frames = await stream.text();
  expect(frames).toContain("event: agent_decision");
  expect(frames).not.toContain("The recorded Apple filing contains risk evidence.");
  const resumed = await page.request.get(`${API}/agent/runs/${id}/events`, { headers: { ...headers, "Last-Event-ID": "3" } });
  expect(await resumed.text()).not.toContain("id: 1\n");
  const evaluation = await (await page.request.get(`${API}/agent/runs/${id}/evaluation`, { headers })).json();
  expect(evaluation.metrics).toHaveLength(21);
  expect(evaluation.metrics.find((metric: { metric_id: string }) => metric.metric_id === "native_agent.objective_coverage"))
    .toMatchObject({ status: "computed", value: 1 });
  expect((await (await page.request.get(`${API}/__test005__/agent/state`)).json()).model_requests).toBe(3);
  await setup(page, `/agent/runs/${id}`);
  await connect(page);
  await expect(page.getByRole("heading", { name: "Research objectives" })).toBeVisible();
  await expect(page.locator(".agent-trace-item")).toHaveCount(8);
  await expect(page.locator(".agent-evidence-card .agent-long-id").filter({ hasText: "AAPL_harness_0000" })).toBeVisible();
  await expect(page.getByText("The recorded Apple filing contains risk evidence.")).toBeVisible();
  await expect(page.locator(".agent-metric")).toHaveCount(21);
  await axeAgent(page);
  await page.screenshot({ path: testInfo.outputPath("agent-real-research.png"), animations: "disabled" });
  await page.locator(".agent-evidence-card").first().getByRole("button", { name: "Open document" }).click();
  await expect(page).toHaveURL(/\/documents\/AAPL%3AHARNESS$/);
});

test("D real revisioned cancellation reaches cancelled after a deterministic boundary", async ({ page }) => {
  await mode(page, "waiting");
  const id = await create(page, "cancel", { goal: "Inspect current Apple risk evidence." });
  await expect.poll(async () => (await (await page.request.get(`${API}/__test005__/agent/state`)).json()).entered).toBe(true);
  const running = await run(page, id);
  expect(running.state).toBe("running");
  await setup(page, `/agent/runs/${id}`);
  await connect(page);
  const detail = page.locator(".agent-run-detail");
  await expect(detail.getByRole("button", { name: "Request cancellation" })).toBeVisible();
  const cancelRequest = page.waitForRequest(request => new URL(request.url()).pathname.endsWith(`/${id}/cancel`));
  await detail.getByRole("button", { name: "Request cancellation" }).click();
  expect((await cancelRequest).headers()["if-match"]).toBe(`"${running.revision}"`);
  await expect(detail.getByText("Cancellation requested. An in-flight call may continue", { exact: false })).toBeVisible();
  expect((await run(page, id)).state).toBe("cancelling");
  expect((await page.request.post(`${API}/agent/runs/${id}/cancel`, {
    headers: { ...headers, "If-Match": `"${running.revision}"` },
  })).status()).toBe(409);
  await page.request.post(`${API}/__test005__/agent/release`);
  expect((await terminal(page, id)).state).toBe("cancelled");
  await expect(detail.getByText("Cancelled").first()).toBeVisible({ timeout: 10_000 });
  expect((await page.request.get(`${API}/agent/runs/${id}/evaluation`, { headers })).status()).toBe(200);
  await axeAgent(page);
});

test("E interrupted durable record remains terminal with no automatic replay", async ({ page }) => {
  const fixture = await page.request.post(`${API}/__test005__/agent/interrupted`);
  expect(fixture.status()).toBe(200);
  const { run_id: id } = await fixture.json();
  expect((await run(page, id)).state).toBe("interrupted");
  const report = await page.request.get(`${API}/agent/runs/${id}/evaluation`, { headers });
  expect(report.status()).toBe(200);
  expect((await report.json()).metrics).toHaveLength(21);
  await setup(page, `/agent/runs/${id}`);
  await connect(page);
  await expect(page.getByText("No final answer was recorded for this outcome.")).toBeVisible();
  await expect(page.locator(".agent-metric")).toHaveCount(21);
  await expect(page.getByText("Interrupted").first()).toBeVisible();
});

test("F focused built-product responsive and accessibility states", async ({ page }, testInfo) => {
  await mode(page, "research");
  const id = await create(page, "responsive", { goal: "Compare long Apple research evidence identities.",
    research: { version: "agent_research_v1", objectives: [
      { objective_id: "apple_risk", question: "Find long Apple filing risk evidence", ticker_scope: "AAPL" },
    ] },
  });
  expect((await terminal(page, id)).state).toBe("succeeded");
  for (const variant of [
    { theme: "dark", locale: "en", width: 1440, height: 900 },
    { theme: "dark", locale: "vi", width: 1024, height: 768 },
    { theme: "dark", locale: "vi", width: 768, height: 900 },
    { theme: "light", locale: "vi", width: 390, height: 844 },
    { theme: "light", locale: "en", width: 1440, height: 700 },
  ] as const) {
    await setup(page, `/agent/runs/${id}`, { theme: variant.theme, locale: variant.locale });
    await page.setViewportSize({ width: variant.width, height: variant.height });
    await expect(page.locator("html")).toHaveAttribute("lang", variant.locale);
    expect(await page.locator("html").evaluate(element => element.classList.contains("dark"))).toBe(variant.theme === "dark");
    await connect(page, variant.locale);
    await expect(page.locator(".agent-metric")).toHaveCount(21);
    await expect(page.locator(".agent-evidence-card").first()).toBeVisible();
    await noOverflow(page);
    await axeAgent(page);
    if (variant.width === 390) await page.screenshot({ path: testInfo.outputPath("agent-real-phone-light-vi.png"), animations: "disabled" });
  }
});
