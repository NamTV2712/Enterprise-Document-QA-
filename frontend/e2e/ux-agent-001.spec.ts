import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { AGENT_FIXTURE_TOKEN, installAgentFixture } from "./agent-fixtures";
import { API_ORIGIN, askQuestion } from "./fixtures";
import { agentResearchRun } from "../src/test/agentFixtures";

async function connect(page: Page, vi = false) {
  await page.getByRole("button", { name: vi ? "Kết nối workspace cục bộ" : "Connect local workspace", exact: true }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(vi ? "Token workspace cục bộ" : "Local workspace token").fill(AGENT_FIXTURE_TOKEN);
  await dialog.getByRole("button", { name: vi ? "Kết nối" : "Connect", exact: true }).click();
  await expect(dialog).toBeHidden();
}

async function auditStorage(page: Page) {
  const audit = await page.evaluate(async (sentinel) => {
    const storage = JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } });
    const databases = await indexedDB.databases();
    const records: unknown[] = [];
    for (const info of databases) {
      if (!info.name) continue;
      const db = await new Promise<IDBDatabase>((resolve, reject) => {
        const request = indexedDB.open(info.name!); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
      });
      for (const name of Array.from(db.objectStoreNames)) {
        records.push(await new Promise((resolve, reject) => {
          const request = db.transaction(name).objectStore(name).getAll(); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
        }));
      }
      db.close();
    }
    const bytes = JSON.stringify(records);
    const mirror = JSON.parse(localStorage.getItem("sec_qa_library_v3") ?? '{"records":[]}');
    const refs = mirror.records.flatMap((record: { messages: { assistantExecution?: { kind: string }; text: string }[] }) => record.messages.filter(message => message.assistantExecution?.kind === "agent_research"));
    return { tokenInStorage: storage.includes(sentinel), tokenInIdb: bytes.includes(sentinel), tokenInUrl: location.href.includes(sentinel), tokenInDom: document.body.textContent?.includes(sentinel),
      references: refs, backupContainsToken: JSON.stringify(mirror.records).includes(sentinel) };
  }, AGENT_FIXTURE_TOKEN);
  expect(audit).toMatchObject({ tokenInStorage: false, tokenInIdb: false, tokenInUrl: false, tokenInDom: false, backupContainsToken: false });
  for (const ref of audit.references) {
    expect(Object.keys(ref).sort()).toEqual(["assistantExecution", "id", "sender", "text"]);
    expect(Object.keys(ref.assistantExecution!).sort()).toEqual(["createdAt", "kind", "runId"]);
    expect(ref.text).toBe("");
  }
  return audit.references;
}

test("Quick and Deep share a conversation, with explicit consent, one durable card and reconnect", async ({ page }, info) => {
  const queued = { ...agentResearchRun, state: "queued" as const, revision: 1, result: null, failure: null, frozen: { ...agentResearchRun.frozen, research: null } };
  const fixture = await installAgentFixture(page, { initialRuns: [], decisionProviderAvailable: true, createdRun: queued });
  const posts: unknown[] = [];
  page.on("request", request => { if (request.method() === "POST" && request.url() === `${API_ORIGIN}/agent/runs`) posts.push(request.postDataJSON()); });
  await page.goto("/research");
  await expect(page.getByRole("button", { name: "Quick", exact: true })).toHaveAttribute("aria-pressed", "true");
  await askQuestion(page, "What are Apple competition risks?");
  expect(fixture.createCount()).toBe(0);
  const quick = page.getByRole("article", { name: "Research assistant response" });
  await expect(quick).toBeVisible();
  const quickText = await quick.textContent();
  await quick.getByRole("button", { name: "Open source 1" }).first().click();
  await expect(page.getByRole("button", { name: "Close evidence inspector" })).toBeVisible();
  await page.getByRole("button", { name: "Close evidence inspector" }).click();
  await page.getByRole("button", { name: "Research deeper", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Research goal" })).toHaveValue("What are Apple competition risks?");
  expect(fixture.createCount()).toBe(0);
  await connect(page);
  const submit = page.getByRole("button", { name: "Start Deep Research", exact: true });
  await expect(submit).toBeDisabled();
  await page.getByRole("checkbox", { name: "Allow bounded decision-provider calls for this run" }).check();
  await submit.click();
  const card = page.locator('.research-agent-message[data-agent-run-id="agent_created_1"]');
  await expect(card).toHaveCount(1); await expect(card.getByRole("status").first()).toHaveText("Queued");
  expect(posts).toEqual([{ goal: "What are Apple competition risks?", locale: "en", allow_decision_provider_execution: true }]);
  expect(fixture.createCount()).toBe(1);
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  const running = { ...fixture.runs.get("agent_created_1")!, state: "running" as const, revision: 2 };
  fixture.advanceRun(running); await expect(card.getByRole("status").first()).toHaveText("Running");
  const terminal = { ...running, state: "succeeded" as const, revision: 3, result: { ...agentResearchRun.result!, research: null } };
  fixture.advanceRun(terminal); await expect(card.getByText(agentResearchRun.result!.answer!)).toBeVisible();
  await expect(card.getByRole("button", { name: "Open document:", exact: false }).first()).toBeVisible();
  await expect(page.getByText(agentResearchRun.result!.answer!, { exact: true })).toHaveCount(1);
  await expect(card.locator("details").first()).not.toHaveAttribute("open", "");
  expect(await quick.textContent()).toBe(quickText);
  expect(await auditStorage(page)).toHaveLength(1);
  await card.getByText("Research details", { exact: true }).click(); await expect(card.locator(".agent-trace-item").first()).toBeVisible();
  await page.screenshot({ path: info.outputPath("unified-research.png"), fullPage: true, animations: "disabled" });
  await card.getByRole("link", { name: "Open full run" }).click(); await expect(page).toHaveURL(/\/agent\/runs\/agent_created_1$/);
  await page.goBack(); await expect(card).toHaveCount(1);
  await page.reload(); await expect(card.getByRole("button", { name: "Reconnect to read this run" })).toBeVisible();
  expect(await auditStorage(page)).toHaveLength(1);
  await card.getByRole("button", { name: "Reconnect to read this run" }).click();
  const dialog = page.getByRole("dialog"); await dialog.getByLabel("Local workspace token").fill(AGENT_FIXTURE_TOKEN);
  await dialog.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(card.getByText(agentResearchRun.result!.answer!)).toBeVisible(); expect(fixture.createCount()).toBe(1);
  fixture.runs.delete("agent_created_1"); await page.reload();
  await card.getByRole("button", { name: "Reconnect to read this run" }).click();
  await page.getByRole("dialog").getByLabel("Local workspace token").fill(AGENT_FIXTURE_TOKEN);
  await page.getByRole("dialog").getByRole("button", { name: "Connect", exact: true }).click();
  await expect(card.getByText("This run is unavailable.", { exact: false })).toBeVisible(); expect(await auditStorage(page)).toHaveLength(1);
});

test("conversation cancellation uses current revision and reconciles conflict", async ({ page }) => {
  const running = { ...agentResearchRun, state: "running" as const, revision: 3, result: null, failure: null, frozen: { ...agentResearchRun.frozen, research: null } };
  const fixture = await installAgentFixture(page, { initialRuns: [], createdRun: running });
  await page.goto("/chat"); await page.getByRole("button", { name: "Deep Research", exact: true }).click(); await connect(page);
  await page.getByRole("textbox", { name: "Research goal" }).fill("Review filing risk evidence.");
  await page.getByRole("button", { name: "Start Deep Research" }).click();
  const card = page.locator(".research-agent-message"); fixture.forceConflictOnce();
  await card.getByRole("button", { name: "Request cancellation" }).click();
  await expect(card.getByText("The run changed before cancellation.", { exact: false })).toBeVisible();
  await card.getByRole("button", { name: "Request cancellation" }).click();
  await expect(card.getByRole("status").first()).toHaveText("Cancelling");
  expect(fixture.calls.filter(call => call.path.endsWith("/cancel")).map(call => call.ifMatch)).toEqual(['"3"', '"4"']);
  fixture.advanceRun({ ...fixture.runs.get("agent_created_1")!, state: "cancelled", revision: 6 });
  await expect(card.getByRole("status").first()).toHaveText("Cancelled");
});

test("a late accepted run stays linked to its origin without redirecting a newer tool navigation", async ({ page }) => {
  const fixture = await installAgentFixture(page, { initialRuns: [] });
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let posted = false;
  let releaseSearch!: () => void;
  const heldSearch = new Promise<void>(resolve => { releaseSearch = resolve; });
  let searchRequested = false;
  await page.route("**/assets/DiscoverySearchPage-*.js", async route => {
    searchRequested = true; await heldSearch; await route.continue();
  });
  await page.route(`${API_ORIGIN}/agent/runs`, async route => {
    if (route.request().method() === "POST") { posted = true; await held; }
    await route.fallback();
  });
  try {
    await page.goto("/research");
    await page.getByRole("button", { name: "Deep Research", exact: true }).click();
    await connect(page);
    await page.getByRole("textbox", { name: "Research goal" }).fill("Review filing risk evidence.");
    await page.getByRole("button", { name: "Start Deep Research" }).click();
    await expect.poll(() => posted).toBe(true);
    await page.getByRole("link", { name: "Search", exact: true }).click();
    await expect(page).toHaveURL(/\/search$/);
    await expect.poll(() => searchRequested).toBe(true);
    release();
    await expect.poll(() => fixture.createCount()).toBe(1);
    await expect.poll(async () => (await auditStorage(page)).length).toBe(1);
    await expect(page).toHaveURL(/\/search$/);
  } finally { release(); releaseSearch(); }
  await expect(page.getByRole("heading", { name: "Search", exact: true })).toBeVisible();
});

test("Vietnamese compact Agent states and keyboard details remain readable on a phone", async ({ page }, info) => {
  await installAgentFixture(page, { initialRuns: [] });
  await page.addInitScript(() => localStorage.setItem("sec_qa_locale", "vi"));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/research?lang=vi");
  await page.getByRole("button", { name: "Nghiên cứu sâu", exact: true }).click();
  await connect(page, true);
  await page.getByRole("textbox", { name: "Mục tiêu nghiên cứu" }).fill("Kiểm tra bằng chứng về rủi ro Microsoft.");
  await page.getByRole("button", { name: "Bắt đầu nghiên cứu sâu" }).click();
  const card = page.locator(".research-agent-message");
  await expect(card.getByRole("status").first()).toHaveText("Thất bại");
  await card.locator("summary").first().focus(); await page.keyboard.press("Enter");
  await expect(card.locator("details").first()).toHaveAttribute("open", "");
  await expect(card.getByRole("link", { name: "Mở toàn bộ lần chạy" })).toBeVisible();
  expect(await auditStorage(page)).toHaveLength(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
  await page.screenshot({ path: info.outputPath("compact-agent-vi-phone.png"), fullPage: true, animations: "disabled" });
});

for (const width of [390, 768, 1024, 1280, 1366, 1440, 1920]) {
  test(`unified Research EN/VI and light/dark at ${width}`, async ({ page }, info) => {
    await installAgentFixture(page);
    await page.setViewportSize({ width, height: 900 });
    for (const locale of ["en", "vi"] as const) for (const theme of ["light", "dark"] as const) {
      await page.addInitScript(({ locale, theme }) => { localStorage.setItem("sec_qa_locale", locale); localStorage.setItem("theme", theme); }, { locale, theme });
      await page.goto(`/research?lang=${locale}`);
      const label = locale === "vi" ? "Nghiên cứu sâu" : "Deep Research";
      const button = page.getByRole("button", { name: label, exact: true });
      await button.focus(); await page.keyboard.press("Enter"); await expect(button).toHaveAttribute("aria-pressed", "true");
      await expect(button).toBeFocused();
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
      await page.screenshot({ path: info.outputPath(`research-${width}-${locale}-${theme}.png`), animations: "disabled", fullPage: true });
      if (width === 390 || width === 1440) {
        const axe = await new AxeBuilder({ page }).analyze();
        expect(axe.violations.filter(issue => ["serious", "critical"].includes(issue.impact ?? ""))).toEqual([]);
      }
    }
  });
}
