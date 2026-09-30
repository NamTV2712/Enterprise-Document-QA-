import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const API = "http://127.0.0.1:8789";
const TOKEN = "AGENT_PROVIDER_TEST_BEARER_7D2A_browser_synthetic";
const KEY = "AGENT_PROVIDER_TEST_KEY_91C4_browser_synthetic";

async function connect(page: Page, locale: "en" | "vi") {
  const title = locale === "en" ? "Connect local workspace" : "Kết nối workspace cục bộ";
  await page.getByRole("button", { name: title }).first().click();
  const dialog = page.getByRole("dialog", { name: title });
  await dialog.getByLabel(locale === "en" ? "Local workspace token" : "Token workspace cục bộ").fill(TOKEN);
  await dialog.getByRole("button", { name: locale === "en" ? "Verify and connect" : "Xác minh và kết nối" }).click();
  await expect(dialog).toBeHidden();
}

async function setup(page: Page, locale: "en" | "vi", theme: "light" | "dark", width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(value => {
    localStorage.setItem("sec_qa_locale", value.locale);
    localStorage.setItem("theme", value.theme);
  }, { locale, theme });
  await page.route("**/*", async route => {
    if ([API, "http://localhost:4189"].includes(new URL(route.request().url()).origin)) await route.continue();
    else await route.abort();
  });
  await page.goto("/agent");
  await connect(page, locale);
}

for (const locale of ["en", "vi"] as const) for (const theme of ["light", "dark"] as const)
for (const width of [390, 1440]) test(`real structured adapter research ${locale} ${theme} ${width}`, async ({ page }, info) => {
  await page.request.post(`${API}/__provider001__/mode`, { data: { mode: "configured" } });
  const before = (await (await page.request.get(`${API}/__provider001__/attempts`)).json()).attempts;
  await setup(page, locale, theme, width);
  await expect(page.locator(".agent-runtime-note")).toContainText(locale === "en" ? "supported structured decision provider" : "provider quyết định có cấu trúc");
  await page.getByRole("button", { name: locale === "en" ? "Create recorded run" : "Tạo lần chạy ghi nhận" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel(locale === "en" ? "Goal" : "Mục tiêu")).toBeFocused();
  await dialog.getByLabel(locale === "en" ? "Goal" : "Mục tiêu").fill("Research Apple risk evidence.");
  await dialog.getByLabel(locale === "en" ? "Mode" : "Chế độ").selectOption("research");
  await dialog.getByLabel(locale === "en" ? "Question" : "Câu hỏi", { exact: true }).fill("Find Apple risk evidence");
  await dialog.getByLabel(locale === "en" ? "Ticker scope (optional)" : "Mã cổ phiếu (tùy chọn)").fill("AAPL");
  const consent = dialog.getByRole("checkbox");
  await expect(consent).not.toBeChecked();
  await consent.check();
  const violations = await new AxeBuilder({ page }).include(".agent-dialog").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(violations.violations).toEqual([]);
  await page.screenshot({ path: info.outputPath("provider-consent.png"), fullPage: true });
  await dialog.getByRole("button", { name: locale === "en" ? "Create run" : "Tạo lần chạy", exact: true }).click();
  await expect(page).toHaveURL(/\/agent\/runs\/agent_[a-z0-9]+$/);
  await expect(page.getByText("Recorded Apple filing evidence supports this bounded summary.")).toBeVisible();
  await expect(page.locator(".agent-metric")).toHaveCount(21);
  const id = new URL(page.url()).pathname.split("/").pop();
  const run = await (await page.request.get(`${API}/agent/runs/${id}`, { headers: { Authorization: `Bearer ${TOKEN}` } })).json();
  expect(run.frozen.allow_decision_provider_execution).toBe(true);
  expect(run.frozen.allow_provider_tool_execution).toBe(false);
  expect(run.frozen.decision_provider.mechanism).toBe("native_strict_json_schema");
  expect(run.result.research.objectives[0].coverage).toBe("sufficient");
  expect((await (await page.request.get(`${API}/__provider001__/attempts`)).json()).attempts - before).toBe(3);
  const text = await page.locator(".agent-workspace").innerText();
  expect(text).not.toContain(KEY); expect(text).not.toContain(TOKEN); expect(text).not.toContain("CONTROL_JSON");
  expect(await page.evaluate(() => JSON.stringify({ local: localStorage, session: sessionStorage, cookie: document.cookie }))).not.toContain(TOKEN);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
  const resultAxe = await new AxeBuilder({ page }).include(".agent-workspace").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(resultAxe.violations).toEqual([]);
  await page.screenshot({ path: info.outputPath("provider-research-result.png"), fullPage: true });
});

for (const mode of ["missing", "unsupported"]) test(`unavailable capability ${mode} has no transport calls`, async ({ page }) => {
  const before = (await (await page.request.post(`${API}/__provider001__/mode`, { data: { mode } })).json()).attempts;
  await setup(page, "en", "light", 1440);
  await expect(page.locator(".agent-runtime-note")).toContainText("not configured");
  await page.getByRole("button", { name: "Create recorded run" }).click();
  await expect(page.getByRole("checkbox")).toBeDisabled();
  await page.getByLabel("Goal").fill("Check provider availability.");
  await page.getByRole("button", { name: "Create run", exact: true }).click();
  await expect(page.getByText("Structured Agent decision provider is not configured for production execution.")).toBeVisible();
  expect((await (await page.request.get(`${API}/__provider001__/attempts`)).json()).attempts).toBe(before);
});
