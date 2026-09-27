import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const API = "http://127.0.0.1:8778";
const PUBLIC = "http://127.0.0.1:8777";
const TOKEN = "test004-synthetic-local-token-0123456789abcdef";
const headers = { Authorization: `Bearer ${TOKEN}`, Origin: "http://localhost:4177" };

async function setup(page: Page, route: string, variant = { theme: "light", locale: "en" }) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(value => { localStorage.setItem("theme", value.theme); localStorage.setItem("sec_qa_locale", value.locale); }, variant);
  // This is an origin firewall, not an API response fixture. Every application
  // request continues to a real FastAPI server or the production asset server.
  await page.route("**/*", async route => {
    if ([API, PUBLIC, "http://localhost:4177"].includes(new URL(route.request().url()).origin)) await route.continue();
    else await route.abort();
  });
  await page.goto(route);
  await expect(page.getByRole("main", { name: "Research workspace" })).toBeVisible();
}

async function connect(page: Page) {
  await page.getByRole("button", { name: "Connect", exact: true }).first().click();
  const dialog = page.getByRole("dialog", { name: "Connect local workspace" });
  await dialog.getByLabel("Local workspace token").fill(TOKEN);
  await dialog.getByRole("button", { name: "Verify and connect" }).click();
  await expect(dialog).toBeHidden();
}

async function audit(page: Page, label: string) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    for (const animation of document.getAnimations()) {
      if (animation.effect?.getComputedTiming().iterations !== Infinity) animation.finish();
    }
  });
  expect(await page.evaluate(() => ({ body: document.body.scrollWidth - document.body.clientWidth,
    root: document.documentElement.scrollWidth - document.documentElement.clientWidth }))).toEqual({ body: 0, root: 0 });
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()).violations, label).toEqual([]);
  await page.screenshot({ path: test.info().outputPath(`${label}.png`), animations: "disabled" });
}

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error" && !message.text().startsWith("Failed to load resource:")) errors.push(message.text()); });
  page.on("response", response => {
    if (response.status() >= 500 || (new URL(response.url()).origin === "http://localhost:4177" && response.status() >= 400)) errors.push(`${response.status()} ${new URL(response.url()).pathname}`);
  });
  page.on("requestfailed", request => {
    if ([API, PUBLIC, "http://localhost:4177"].includes(new URL(request.url()).origin)
      && !request.failure()?.errorText.includes("ABORTED")
      && !request.failure()?.errorText.includes("NS_BINDING_ABORTED")) errors.push(`resource ${request.url()}`);
  });
  test.info().annotations.push({ type: "runtime-errors", description: "Unexpected JS/React/HTTP5xx/local asset failures checked after each journey." });
  (page as Page & { productErrors?: string[] }).productErrors = errors;
});

test.afterEach(async ({ page }) => {
  expect((page as Page & { productErrors?: string[] }).productErrors).toEqual([]);
});

test("scope controls accept real pointer interaction above the composer", async ({ page }) => {
  await setup(page, "/chat");
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.getByRole("button", { name: /Scope/ }).click();
  const company = page.getByRole("dialog", { name: "Retrieval scope" }).getByRole("button", { name: "Company", exact: true });
  await expect.poll(() => company.evaluate(node => {
    const box = node.getBoundingClientRect();
    const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
    return hit === node || node.contains(hit);
  })).toBe(true);
  await company.click();
  await expect(page.getByRole("option", { name: /Apple Inc.*AAPL/ })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Retrieval scope" })).toBeHidden();
});

test("A knowledge: catalog, real search snapshot and canonical reader", async ({ page }) => {
  await setup(page, "/documents");
  await expect(page.getByRole("heading", { name: "Documents (2)" })).toBeVisible();
  const stats = await (await page.request.get(`${API}/documents/stats`)).json();
  expect(stats).toMatchObject({ documents: 2, companies: 2, chunks: 4 });
  await page.getByRole("link", { name: "Search", exact: true }).click();
  const searches: string[] = [];
  const snapshotReads: string[] = [];
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (path === "/search" && request.method() === "POST") searches.push(request.postData() ?? "");
    if (path.startsWith("/search/") && request.method() === "GET") snapshotReads.push(path);
  });
  await page.getByLabel("Search Query").fill("Harness indexed excerpt");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.locator("article.console-result").first()).toBeVisible();
  await page.getByRole("button", { name: "Rows per page" }).click();
  await page.getByRole("option", { name: "50 per page" }).click();
  expect(snapshotReads).toHaveLength(1);
  expect(snapshotReads[0]).toMatch(/^\/search\/search-[0-9a-f]{16}$/);
  await page.locator("article.console-result").first().getByRole("button", { name: "Open document workspace" }).click();
  await expect(page.locator("[data-workbench-route-origin='search']")).toBeVisible();
  expect(searches).toHaveLength(1);
  await audit(page, "A-indexed-reader");
  await page.getByRole("button", { name: "Back to Search", exact: true }).click();
  expect(searches).toHaveLength(1);
  await page.getByRole("link", { name: "Retrieval Lab", exact: true }).click();
  await page.getByRole("button", { name: "Run retrieval" }).click();
  await expect(page.getByTestId("retrieval-analyst-summary")).toBeVisible();
  await expect(page.getByText(/provider-free/i).first()).toBeVisible();
});

test("B question to actual SSE answer, cited excerpt and Research", async ({ page }) => {
  await setup(page, "/chat");
  for (const route of ["chat", "research"]) {
    if (route === "research") await page.getByRole("link", { name: "Research", exact: true }).click();
    const input = page.getByRole("textbox", { name: "Research question" });
    await input.fill("What was Apple total revenue?");
    await input.press("Enter");
    await expect(page.getByText(/Harness answer with é/).first()).toBeVisible();
    await page.getByRole("button", { name: "Open source 1", exact: true }).first().click();
    await expect(page.getByText(/Harness indexed excerpt for AAPL/).first()).toBeVisible();
    await audit(page, `B-${route}-cited-source`);
    await page.getByRole("button", { name: /Open document for source 1/ }).click();
    await expect(page.locator("[data-workbench-region='document']")).toBeVisible();
    await expect(page.getByText(/Harness indexed excerpt for AAPL/).first()).toBeVisible();
    await audit(page, `B-${route}-document-handoff`);
  }
});

test("C protected SQLite collections lifecycle and honest browser refusal", async ({ page }) => {
  await setup(page, "/pipeline");
  expect((await page.request.get(`${PUBLIC}/collections`)).status()).toBe(404);
  expect((await page.request.get(`${API}/collections`)).status()).toBe(401);
  expect((await page.request.get(`${API}/collections`, { headers: { ...headers, Authorization: "Bearer wrong" } })).status()).toBe(401);
  expect((await page.request.get(`${API}/collections`, { headers: { ...headers, Origin: "https://untrusted.invalid" } })).status()).toBe(403);
  await connect(page);
  const id = `test004-${test.info().project.name}`;
  const created = await page.request.post(`${API}/collections`, { headers, data: { collection_id: id, name: "Final validation", tags: ["sec"] } });
  expect(created.status()).toBe(200);
  expect(await created.json()).toMatchObject({ collection_id: id, revision: 1, private: true });
  const reference = { document_id: "AAPL:harness", chunk_id: "AAPL_harness_0000" };
  expect((await page.request.post(`${API}/collections/${id}/items`, { headers, data: { item_kind: "evidence", citation: "AAPL SEC", excerpt: "Synthetic indexed evidence", reference } })).status()).toBe(200);
  const note = await (await page.request.post(`${API}/collections/${id}/notes`, { headers, data: { text: "Verify identity", evidence_ref: reference } })).json();
  expect((await page.request.patch(`${API}/collections/${id}/notes/${note.note_id}`, { headers, data: { revision: 1, text: "Verified" } })).status()).toBe(200);
  expect((await page.request.patch(`${API}/collections/${id}/notes/${note.note_id}`, { headers, data: { revision: 1, text: "Stale" } })).status()).toBe(409);
  expect((await (await page.request.get(`${API}/collections/${id}/activity`, { headers })).json()).items.length).toBeGreaterThan(2);
  const exported = await (await page.request.get(`${API}/collections/${id}/export`, { headers })).json();
  expect(exported.items.find((item: { itemKind: string; reference: { chunk_id?: string } }) => item.reference?.chunk_id === reference.chunk_id)?.reference).toEqual(reference);
  const refusal = page.waitForResponse(response => new URL(response.url()).pathname === "/collections" && response.request().method() === "GET");
  await page.getByRole("link", { name: "Collections", exact: true }).click();
  // This wrapper is deliberately staged: final validation must not silently
  // add bearer integration or manufacture a working private browser feature.
  expect((await refusal).status()).toBe(401);
  expect((await refusal).request().headers().authorization).toBeUndefined();
  await expect(page.getByRole("heading", { name: "Local workspace access required" })).toBeVisible();
  await audit(page, "C-staged-wrapper-refusal");
  const current = await (await page.request.get(`${API}/collections/${id}`, { headers })).json();
  expect((await page.request.delete(`${API}/collections/${id}?revision=${current.revision}`, { headers })).status()).toBe(200);
  expect((await page.request.get(`${API}/collections/${id}`, { headers })).status()).toBe(410);
});

test("D real registries and queued five-step staging, finite events and cancellation", async ({ page }) => {
  await setup(page, "/models");
  const models = await (await page.request.get(`${API}/models`)).json();
  expect(models.items).toHaveLength(3);
  expect(models.items.find((item: { role: string }) => item.role === "generator")).toMatchObject({ availability_status: "unavailable", load_status: "loaded" });
  const datasets = await (await page.request.get(`${API}/datasets`)).json();
  expect(datasets.items).toHaveLength(2);
  await audit(page, "D-models-identity-mismatch");
  await page.getByRole("link", { name: "Pipeline", exact: true }).click();
  await connect(page);
  const staged: string[] = [];
  page.on("request", request => { if (new URL(request.url()).pathname === "/pipeline/runs" && request.method() === "POST") staged.push(request.postData() ?? ""); });
  await page.getByRole("button", { name: "Stage run", exact: true }).first().click();
  const dialog = page.getByRole("dialog", { name: "Stage an isolated run" });
  // Staging deduplicates by input fingerprint, even after cancellation. Each
  // engine owns a distinct supported input in this shared durable server.
  await dialog.getByRole("checkbox", { name: test.info().project.name.endsWith("firefox") ? "MSFT" : "AAPL", exact: true }).check();
  await dialog.getByRole("button", { name: "Create staged run" }).click();
  await expect(page.getByTestId("pipeline-run-detail")).toContainText("Queued");
  await expect(page.locator(".pipeline-step-item.is-pending")).toHaveCount(5);
  expect(staged).toHaveLength(1);
  const id = new URL(page.url()).pathname.split("/").pop();
  const run = await (await page.request.get(`${API}/pipeline/runs/${id}`, { headers })).json();
  expect(run.state).toBe("queued");
  expect(run.progress.current).toBeNull();
  const events = await page.request.get(`${API}/pipeline/runs/${id}/events`, { headers });
  expect(events.status()).toBe(200);
  expect(await events.text()).toContain("id:");
  await audit(page, "D-queued-no-execution");
  const cancelled = await page.request.post(`${API}/pipeline/runs/${id}/cancel`, { headers: { ...headers, "If-Match": String(run.revision) } });
  expect(cancelled.status()).toBe(200);
  expect((await cancelled.json()).state).toBe("cancelled");
});

test("E native definitions, exact zero and frozen real evaluation execution", async ({ page }) => {
  await setup(page, "/evaluation/runs/test004-baseline");
  const detail = page.getByRole("complementary", { name: "Report detail" });
  await expect(detail.getByRole("heading", { name: "test004-baseline" })).toBeVisible();
  await expect(detail.getByText("0.000").first()).toBeVisible();
  await audit(page, "E-native-zero");
  const definitions = await (await page.request.get(`${API}/evaluation/metrics`)).json();
  expect(definitions.items).toHaveLength(6);
  await page.getByRole("tab", { name: "Private jobs" }).click();
  const form = page.locator(".evaluation-connect form");
  await form.getByLabel("Local workspace token").fill(TOKEN);
  await form.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(page.getByText(/Connected · execution enabled/)).toBeVisible();
  const response = await page.request.post(`${API}/evaluation/jobs`, { headers: { ...headers, "Idempotency-Key": test.info().project.name }, data: {
    artifact_id: "test004-phase1", engine: "native", mode: "provider_backed", budget: 3,
    metrics: definitions.items.map((item: { metric_id: string }) => item.metric_id),
  } });
  expect(response.status()).toBe(201);
  const job = await response.json();
  expect(job.frozen).toMatchObject({ budget_limit: 3, budget_unit: "provider_attempt_slot", protocol_version: 1 });
  await expect.poll(async () => (await (await page.request.get(`${API}/evaluation/jobs/${job.id}`, { headers })).json()).state).toBe("succeeded");
  const finished = await (await page.request.get(`${API}/evaluation/jobs/${job.id}`, { headers })).json();
  expect(finished.steps.map((step: { ordinal: number }) => step.ordinal)).toEqual([0, 1]);
  expect(finished.budget_consumed).toBe(2);
  expect(finished.publication_status).toBe("not_published");
  expect((await (await page.request.get(`${API}/evaluation/jobs/${job.id}/results`, { headers })).json()).items).toHaveLength(1);
});

test("F real terminal telemetry, shared memory connection, Settings and reload loss", async ({ page }) => {
  await setup(page, "/settings");
  // Own a real terminal request; this journey also runs independently of B.
  expect((await page.request.post(`${API}/query`, { data: { question: "What was Apple total revenue?", ticker: "AAPL", top_k: 5 } })).status()).toBe(200);
  const form = page.locator(".operations-connection form");
  await form.getByLabel("Local workspace token").fill(TOKEN);
  await form.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(page.getByText("Connected · token held in memory only")).toBeVisible();
  await page.getByRole("link", { name: "Analytics", exact: true }).click();
  await expect(page.getByText("Terminal requests", { exact: true })).toBeVisible();
  const summary = await page.request.get(`${API}/analytics/summary`, { headers });
  expect(summary.status()).toBe(200);
  await audit(page, "F-real-analytics");
  await page.getByRole("link", { name: "Logs", exact: true }).click();
  await expect(page.locator(".operations-logs li").first()).toBeVisible();
  const logs = await (await page.request.get(`${API}/logs?limit=1`, { headers })).json();
  expect(logs.items).toHaveLength(1);
  expect(JSON.stringify(logs)).not.toContain("What was Apple total revenue?");
  expect(JSON.stringify(logs)).not.toContain(TOKEN);
  const exported = await page.request.get(`${API}/workspace/export`, { headers });
  expect(exported.status()).toBe(200);
  const backup = await exported.json();
  expect(backup.format).toBe("enterprise-document-qa.workspace");
  expect(backup).not.toHaveProperty("jobs");
  expect(backup).not.toHaveProperty("telemetry");
  const preview = await page.request.post(`${API}/workspace/imports/preview`, { headers, data: backup });
  expect(preview.status()).toBe(200);
  expect((await preview.json()).digest).toBe(backup.digest);
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  const storage = await page.evaluate(() => ({ local: Object.entries(localStorage), session: Object.entries(sessionStorage), cookies: document.cookie, url: location.href, html: document.body.innerHTML }));
  expect(JSON.stringify(storage)).not.toContain(TOKEN);
  const indexed = await page.evaluate(async () => {
    const values: unknown[] = [];
    for (const entry of await indexedDB.databases()) {
      if (!entry.name) continue;
      const database = await new Promise<IDBDatabase>((resolve, reject) => {
        const request = indexedDB.open(entry.name!);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      try {
        for (const name of Array.from(database.objectStoreNames)) {
          const transaction = database.transaction(name, "readonly");
          const store = transaction.objectStore(name);
          for (const request of [store.getAll(), store.getAllKeys()]) {
            values.push(await new Promise((resolve, reject) => {
              request.onsuccess = () => resolve(request.result);
              request.onerror = () => reject(request.error);
            }));
          }
        }
      } finally { database.close(); }
    }
    return values;
  });
  expect(JSON.stringify(indexed)).not.toContain(TOKEN);
  expect(JSON.stringify(await page.context().cookies())).not.toContain(TOKEN);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export backup", exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/json$/);
  await page.getByRole("button", { name: "Disconnect", exact: true }).click();
  await expect(page.getByText("Deployment mode", { exact: true })).toHaveCount(0);
  await form.getByLabel("Local workspace token").fill(TOKEN);
  await form.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(page.getByText("Deployment mode", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Local workspace token")).toHaveValue("");
  await expect(page.getByText("Deployment mode", { exact: true })).toHaveCount(0);
});

test("direct route and browser Back/Forward smoke over real HTTP", async ({ page }) => {
  await setup(page, "/chat");
  for (const route of ["chat", "research", "documents", "search", "collections", "retrieval", "models", "pipeline", "reranker", "evaluation", "analytics", "datasets", "settings", "logs"]) {
    await page.goto(`/${route}`);
    await expect(page.getByRole("main", { name: "Research workspace" })).toHaveAttribute("data-route-id", route);
  }
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/logs$/);
  await page.goForward();
  await expect(page).toHaveURL(/\/settings$/);
});

test("published report metadata remains accessible on dark hover and keyboard focus", async ({ page }) => {
  await setup(page, "/evaluation", { theme: "dark", locale: "vi" });
  const report = page.locator(".evaluation-report-list > button").first();
  await expect(report).toBeVisible();
  await report.hover();
  await audit(page, "E-report-hover-dark");
  await page.mouse.move(0, 0);
  await report.focus();
  await audit(page, "E-report-keyboard-dark");
});

for (const variant of [{ theme: "light", locale: "en" }, { theme: "dark", locale: "vi" }]) {
  test(`compact final responsive ${variant.theme}/${variant.locale}`, async ({ page }) => {
    test.setTimeout(120_000);
    await setup(page, "/chat", variant);
    for (const route of ["chat", "search", "pipeline", "evaluation", "analytics", "settings"]) {
      await page.goto(`/${route}`);
      await expect(page.getByRole("main", { name: "Research workspace" })).toHaveAttribute("data-route-id", route);
      for (const viewport of [{ width: 1440, height: 900 }, { width: 1024, height: 768 }, { width: 390, height: 844 }, { width: 1440, height: 700 }]) {
        await page.setViewportSize(viewport);
        await audit(page, `${route}-${variant.theme}-${variant.locale}-${viewport.width}x${viewport.height}`);
        if (route === "chat") {
          await page.getByRole("button", { name: /Scope|Phạm vi/ }).click();
          const scope = page.getByRole("dialog", { name: /Retrieval scope|Phạm vi truy xuất/ });
          const company = scope.getByRole("button", { name: variant.locale === "vi" ? "Công ty" : "Company", exact: true });
          await company.click();
          await expect(page.getByRole("option", { name: /Apple Inc.*AAPL/ })).toBeVisible();
          await page.keyboard.press("Escape");
          await page.keyboard.press("Escape");
          await expect(scope).toBeHidden();
        }
      }
    }
  });
}
