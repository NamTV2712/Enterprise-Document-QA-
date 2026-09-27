import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { installOperationalFixture } from "./operational-fixtures";
import { operationalCursor, operationalToken } from "../src/test/operationalFixtures";
const viewports = [{ width: 1586, height: 992 }, { width: 1440, height: 900 }, { width: 1280, height: 856 }, { width: 1024, height: 768 }, { width: 768, height: 900 }, { width: 390, height: 844 }, { width: 1440, height: 700 }, { width: 1366, height: 768 }, { width: 1920, height: 1080 }];
async function connect(page: Page, vi = false) {
  const form = page.locator(".operations-connection form");
  await form.getByLabel(vi ? "Token workspace cục bộ" : "Local workspace token").fill(operationalToken);
  await form.getByRole("button", { name: vi ? "Kết nối" : "Connect", exact: true }).click();
  await expect(page.getByText(vi ? "Đã kết nối · token chỉ trong bộ nhớ" : "Connected · token held in memory only")).toBeVisible();
}
async function privacy(page: Page) {
  const value = await page.evaluate(() => ({ local: Object.entries(localStorage), session: Object.entries(sessionStorage), text: document.body.innerText, html: document.querySelector(".operations-page")?.innerHTML, url: location.href, cookies: document.cookie }));
  expect(JSON.stringify(value)).not.toMatch(/HIDDEN_(QUERY|ANSWER|EVIDENCE|SESSION|PROMPT|PROVIDER|STACK|BEARER|COOKIE|PATH)_UI012/);
  expect(JSON.stringify(value)).not.toContain(operationalToken);
}
async function overflow(page: Page) { expect(await page.evaluate(() => ({ body: document.body.scrollWidth - document.body.clientWidth, root: document.documentElement.scrollWidth - document.documentElement.clientWidth }))).toEqual({ body: 0, root: 0 }); }
test.describe("UI-012 operations", () => {
  test.describe.configure({ mode: "serial" });
  test("direct analytics is private-unavailable before connection, never a zero dashboard", async ({ page }, info) => {
    const fixture = await installOperationalFixture(page); await page.goto("/analytics");
    await expect(page.getByRole("heading", { name: "Analytics", exact: true })).toBeVisible(); await expect(page.getByText("Private data is not connected")).toBeVisible();
    await expect(page.getByText("Terminal requests", { exact: true })).toHaveCount(0); expect(fixture.calls.some(call => call.path.startsWith("/analytics"))).toBe(false);
    await page.screenshot({ path: info.outputPath("analytics-disconnected.png") });
  });
  test("public mode rejects explicit connection without creating false analytics or logs", async ({ page }) => {
    const fixture = await installOperationalFixture(page, { publicMode: true }); await page.goto("/analytics");
    await page.getByLabel("Local workspace token").fill(operationalToken); await page.getByRole("button", { name: "Connect", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("local workspace is unavailable"); expect(fixture.calls.some(call => call.path.startsWith("/analytics"))).toBe(false); await privacy(page);
  });
  test("connected server summary retains numerator/denominator, outcomes, jobs and zero duration", async ({ page }, info) => {
    const fixture = await installOperationalFixture(page); await page.addInitScript(() => localStorage.setItem("theme", "dark")); await page.goto("/analytics"); await connect(page);
    await expect(page.getByText("2 / 5 requests")).toBeVisible(); await expect(page.getByText("1 / 5 requests")).toBeVisible(); await expect(page.getByText("40%", { exact: true })).toBeVisible(); await expect(page.getByText("0 ms", { exact: true })).toBeVisible(); await expect(page.getByText("Terminal jobs · 4")).toBeVisible();
    expect(fixture.calls.filter(call => call.path.startsWith("/analytics")).every(call => call.authorization === `Bearer ${operationalToken}`)).toBe(true);
    await expect(page.locator(".operations-page")).not.toContainText(/CPU|token usage|monetary|confidence|uptime|Local events/i); await privacy(page); await page.screenshot({ path: info.outputPath("analytics-connected-dark.png"), fullPage: true });
  });
  test("range and timeseries selectors preserve history and do only required reads", async ({ page }) => {
    const fixture = await installOperationalFixture(page); await page.goto("/analytics"); await connect(page); await expect(page.getByText("40%", { exact: true })).toBeVisible();
    for (const range of ["7d", "30d"]) { await page.getByLabel("Time range").selectOption(range); await expect(page.getByLabel("Time range")).toHaveValue(range); await expect(page.getByText("40%", { exact: true })).toBeVisible(); }
    const summaries = fixture.calls.filter(call => call.path === "/analytics/summary").length;
    for (const metric of ["request_failure_count", "request_duration_p50_ms", "request_duration_p95_ms", "terminal_job_count", "request_count"]) { await page.getByLabel("Metric", { exact: true }).selectOption(metric); await expect(page.locator(".operations-chart")).toBeVisible(); }
    await page.getByLabel("Interval", { exact: true }).selectOption("day"); await expect(page.locator(".operations-chart")).toBeVisible(); expect(fixture.calls.filter(call => call.path === "/analytics/summary")).toHaveLength(summaries);
    await page.goBack(); await expect(page.getByLabel("Interval", { exact: true })).toHaveValue("hour"); await page.goForward(); await expect(page.getByLabel("Interval", { exact: true })).toHaveValue("day");
    await page.getByLabel("Interval", { exact: true }).selectOption("hour"); await page.getByText(/Bucket table and populations/).click(); await expect(page.locator(".operations-table-scroll tbody tr")).toHaveCount(720);
  });
  test("duration null is absent while measured zero remains a real plotted point", async ({ page }, info) => {
    await installOperationalFixture(page); await page.goto("/analytics?metric=request_duration_p95_ms"); await connect(page); await expect(page.locator(".operations-chart circle")).toHaveCount(1);
    await page.getByText(/Bucket table and populations/).click(); await expect(page.getByRole("cell", { name: "Not measured", exact: true })).toHaveCount(23); await expect(page.getByRole("cell", { name: "0 ms", exact: true })).toHaveCount(1); await expect(page.locator(".operations-chart polyline, .operations-chart path")).toHaveCount(0);
    await page.screenshot({ path: info.outputPath("analytics-duration-null-zero.png"), fullPage: true });
  });
  test("empty telemetry and unavailable backend are separate states", async ({ page }) => {
    await installOperationalFixture(page, { empty: true }); await page.goto("/analytics?metric=request_duration_p50_ms"); await connect(page); await expect(page.getByText("No terminal requests recorded in this range.")).toBeVisible(); await expect(page.getByText("No measured population in this range.")).toBeVisible(); await expect(page.getByText("0 ms", { exact: true })).toHaveCount(0);
    await page.unrouteAll({ behavior: "wait" }); await installOperationalFixture(page, { failure: 503 }); await page.reload(); await connect(page); await expect(page.getByRole("alert").first()).toContainText("temporarily unavailable"); await expect(page.getByText("No terminal requests recorded in this range.")).toHaveCount(0);
  });
  test("late range completion cannot overwrite current selection", async ({ page }) => {
    await installOperationalFixture(page, { delayedRange: true }); await page.goto("/analytics"); await connect(page); await page.getByLabel("Time range").selectOption("7d"); await expect(page.getByText("77", { exact: true })).toBeVisible(); await page.waitForTimeout(500); await expect(page.getByText("77", { exact: true })).toBeVisible();
  });
  test("logs directly loads safe ordered request/job records with severity separate from outcome", async ({ page }, info) => {
    const fixture = await installOperationalFixture(page); await page.goto("/logs"); await expect(page.getByRole("heading", { name: "Logs", exact: true })).toBeVisible(); await connect(page); const rows = page.locator(".operations-logs li");
    await expect(rows).toHaveCount(2); await expect(rows.nth(0)).toContainText("info"); await expect(rows.nth(0)).toContainText("cancelled"); await expect(rows.nth(1)).toContainText("warning"); await expect(rows.nth(1)).toContainText("failed"); await expect(rows.nth(1)).toContainText("Not measured"); await expect(rows.nth(1)).toContainText("budget_exhausted");
    await rows.nth(0).getByText("Record details").click(); await expect(page.getByText("req_safe_012", { exact: true })).toBeVisible(); await expect(page.getByText("status_code", { exact: true })).toBeVisible(); expect(fixture.calls.filter(call => call.path === "/logs")).toHaveLength(1); await privacy(page); await page.screenshot({ path: info.outputPath("logs-record-details.png"), fullPage: true });
  });
  test("logs filters are server reads and opaque cursor paging respects Back/Forward", async ({ page }) => {
    const fixture = await installOperationalFixture(page); await page.goto("/logs"); await connect(page); await expect(page.locator(".operations-logs li")).toHaveCount(2);
    await page.getByRole("button", { name: "Next page" }).click(); await expect(page).toHaveURL(new RegExp(`cursor=${encodeURIComponent(operationalCursor).replace(/[+]/g, "\\+")}`)); await expect(page.locator(".operations-logs li")).toHaveCount(1); await page.getByText("Record details").click(); await expect(page.getByText("tel_next", { exact: true })).toBeVisible(); await page.goBack(); await expect(page.locator(".operations-logs li")).toHaveCount(2); await page.goForward(); await expect(page.locator(".operations-logs li")).toHaveCount(1);
    await page.getByLabel("Category", { exact: true }).selectOption("job"); await expect(page).not.toHaveURL(/cursor=/); await expect(page.locator(".operations-logs li")).toHaveCount(1);
    await page.getByLabel("Severity", { exact: true }).selectOption("error"); await expect(page.getByText(/No records for these filters/)).toBeVisible(); await expect(page.getByRole("button", { name: "Next page" })).toBeDisabled();
    await page.getByLabel("Severity", { exact: true }).selectOption("warning"); await expect(page.locator(".operations-logs li")).toHaveCount(1); await page.getByLabel("Category", { exact: true }).selectOption("request"); await page.getByLabel("Severity", { exact: true }).selectOption("info"); await expect(page.locator(".operations-logs li")).toHaveCount(1);
    expect(fixture.calls.filter(call => call.path === "/logs").every(call => call.authorization === `Bearer ${operationalToken}`)).toBe(true);
  });
  test("settings uses supported read-only facts and shared memory session across route navigation", async ({ page }, info) => {
    const fixture = await installOperationalFixture(page); await page.goto("/settings"); await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible(); await expect(page.getByText("balanced", { exact: true })).toBeVisible(); await expect(page.getByText("30 days", { exact: true })).toBeVisible(); await expect(page.getByText("7 days", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /Save|Apply|Clear logs/ })).toHaveCount(0); await connect(page); await expect(page.getByText("Deployment mode", { exact: true })).toBeVisible(); await expect(page.getByText("execution jobs", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Analytics", exact: true }).click(); await expect(page.getByText("40%", { exact: true })).toBeVisible(); await expect(page.getByLabel("Local workspace token")).toHaveCount(0); await page.getByRole("link", { name: "Logs", exact: true }).click(); await expect(page.locator(".operations-logs li")).toHaveCount(2); await privacy(page);
    expect(fixture.calls.filter(call => call.path === "/system/info").every(call => call.authorization === null)).toBe(true);
    await page.getByRole("link", { name: "Settings", exact: true }).click(); await expect(page.getByText("Deployment mode", { exact: true })).toBeVisible(); await page.screenshot({ path: info.outputPath("settings-connected.png"), fullPage: true }); await page.reload(); await expect(page.getByLabel("Local workspace token")).toHaveValue(""); await expect(page.getByText("Deployment mode", { exact: true })).toHaveCount(0); await privacy(page);
  });
  test("settings theme/language and backup recovery controls perform their real actions", async ({ page }) => {
    await installOperationalFixture(page); await page.goto("/settings"); await page.getByLabel("Theme", { exact: true }).selectOption("dark"); await expect(page.locator("html")).toHaveClass(/dark/); await page.getByRole("combobox", { name: "Language", exact: true }).selectOption("vi"); await expect(page.getByRole("heading", { name: "Cài đặt", exact: true })).toBeVisible();
    await page.getByLabel("Xem trước backup để nhập").setInputFiles({ name: "synthetic-invalid.json", mimeType: "application/json", buffer: Buffer.from("{}") }); await expect(page.getByText("Backup không hợp lệ hoặc vượt quá 25 MiB.")).toBeVisible();
    const download = page.waitForEvent("download"); await page.getByRole("button", { name: "Xuất backup" }).click(); expect((await download).suggestedFilename()).toMatch(/json$/);
    await page.getByRole("combobox", { name: "Ngôn ngữ", exact: true }).selectOption("en");
    const backup = { format: "enterprise-document-qa.conversations", version: 2, exportedAt: "2026-09-27T00:00:00Z", collections: [], conversations: [{ schemaVersion: 2, titleMode: "custom", revision: 1, id: "synthetic-conversation", sessionId: "synthetic-session", title: "Synthetic recovery", createdAt: 1, updatedAt: 2, draft: "", bookmarkedMessageIds: [], messages: [{ id: "synthetic-user", sender: "user", text: "Synthetic backup question" }] }] };
    await page.getByLabel("Preview a backup to import").setInputFiles({ name: "synthetic-valid.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(backup)) });
    await expect(page.getByText("Confirm import", { exact: true })).toBeVisible(); await expect(page.locator(".operations-page")).not.toContainText("Synthetic backup question");
    await page.getByRole("button", { name: "Import backup", exact: true }).click(); await expect(page.getByText(/Imported 1; persisted 1/)).toBeVisible(); await privacy(page);
  });
  for (const route of ["analytics", "logs", "settings"] as const) test(`${route} responsive light/EN and dark/VI, keyboard, axe and zero overflow`, async ({ page }, info) => {
    test.setTimeout(120000); await installOperationalFixture(page); await page.emulateMedia({ reducedMotion: "reduce" });
    for (const variant of [{ theme: "light", locale: "en" }, { theme: "dark", locale: "vi" }]) {
      await page.goto(`/${route}`); await page.evaluate(v => { localStorage.setItem("theme", v.theme); localStorage.setItem("sec_qa_locale", v.locale); }, variant); await page.reload(); const vi = variant.locale === "vi"; await connect(page, vi);
      await expect(page.locator(".operations-page")).not.toContainText(vi ? "Đang đọc dữ liệu server…" : "Reading server data…");
      for (const viewport of viewports) { await page.setViewportSize(viewport); await overflow(page); const controls = page.locator(".operations-page select"); await controls.first().focus(); await expect(controls.first()).toBeFocused(); if (viewport.width === 390 || viewport.width === 1586) await page.screenshot({ path: info.outputPath(`${route}-${variant.theme}-${variant.locale}-${viewport.width}.png`), fullPage: true }); }
      await page.setViewportSize({ width: 390, height: 844 });
      const lastAction = route === "analytics" ? page.getByText(/Bucket table and populations|Bảng bucket và quần thể/) : route === "logs" ? page.getByRole("button", { name: vi ? "Trang tiếp" : "Next page" }) : page.getByRole("link", { name: vi ? "Kiến trúc và trợ giúp" : "Architecture and help" });
      await lastAction.scrollIntoViewIfNeeded(); await expect(lastAction).toBeVisible(); await lastAction.focus(); await expect(lastAction).toBeFocused(); await overflow(page);
      await page.screenshot({ path: info.outputPath(`${route}-${variant.theme}-${variant.locale}-390-lower.png`), fullPage: true });
      const violations = (await new AxeBuilder({ page }).include(".operations-page").withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()).violations; expect(violations).toEqual([]); await privacy(page);
    }
  });
});
