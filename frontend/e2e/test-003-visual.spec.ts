import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { askQuestion, createCollectionsFixtureState, installApiFixtures } from "./fixtures";
import { installPipelineFixture, pipelineRun, PIPELINE_FIXTURE_TOKEN } from "./pipeline-fixtures";
import { installEvaluationFixture } from "./evaluation-fixtures";

// Exactly nine reference families. Reranker is only a shared-style smoke target.
const surfaces = [
  { id: "collections", png: "collections-ui-reference-dark-v1.png", route: "/collections/col-risk", width: 1586, height: 992 },
  { id: "documents", png: "documents-ui-reference-dark-v1.png", route: "/documents", width: 1586, height: 992 },
  { id: "evaluation", png: "evaluation-ui-reference-dark-v1.png", route: "/evaluation/runs/baseline-native", width: 1586, height: 992 },
  { id: "models", png: "models-ui-reference-dark-v1.png", route: "/models", width: 1586, height: 992 },
  { id: "pipeline", png: "pipeline-ui-reference-dark-v1.png", route: "/pipeline/runs/run-reference-1", width: 1586, height: 992 },
  { id: "chat", png: "rag-workbench-master-reference-dark.png", route: "/chat", width: 1254, height: 856 },
  { id: "research", png: "research-ui-reference-dark-v1.png", route: "/research?mode=conversation", width: 1586, height: 992 },
  { id: "retrieval", png: "retrieval-ui-reference-dark-v1.png", route: "/retrieval", width: 1586, height: 992 },
  { id: "search", png: "search-ui-reference-dark-v1.png", route: "/search", width: 1586, height: 992 },
] as const;
type Surface = (typeof surfaces)[number];
const phase = process.env.TEST003_PHASE ?? "final";
const baseline = phase === "baseline";
const query = "What was Apple's total revenue in 2024?";

function collections() {
  return createCollectionsFixtureState([
    { collection_id: "col-risk", name: "Risk Analysis", description: "Key risks, challenges, and uncertainties based on indexed filings.", favorite: true, tags: ["Risk Factors", "Regulatory", "Macroeconomics", "Supply Chain"], revision: 4,
      items: [{ item_id: "itm-aapl", collection_id: "col-risk", item_kind: "document", citation: "Apple Inc. (AAPL) · 2025-10-31", excerpt: "", reference: { document_id: "AAPL:fixture", ticker: "AAPL", filing_date: "2025-10-31" }, revision: 1, created_at: "2026-09-26T10:00:00Z", updated_at: "2026-09-26T10:00:00Z" },
        { item_id: "itm-evidence", collection_id: "col-risk", item_kind: "evidence", citation: "AAPL indexed excerpt · financial_statements", excerpt: "Total net sales increased year over year, driven by Services.", reference: { document_id: "AAPL:fixture", chunk_id: "AAPL_fixture_revenue_0", ticker: "AAPL", section: "financial_statements" }, revision: 1, created_at: "2026-09-26T10:00:00Z", updated_at: "2026-09-26T10:00:00Z" }] },
    { collection_id: "col-earnings", name: "Earnings Review", description: "Quarterly and annual financial performance and management commentary.", tags: ["Financials", "Earnings Calls"] },
    { collection_id: "col-competitive", name: "Competitive Landscape", description: "Key competitors, market positioning and industry dynamics.", tags: ["Competition"] },
  ]);
}

async function setup(page: Page, surface: Surface, theme = "dark", locale = "en") {
  // Fail closed even if a preview is accidentally built with a developer origin.
  // Fonts are intentionally system fallbacks: no external request in this gate.
  await page.route("**/*", async (route) => {
    const origin = new URL(route.request().url()).origin;
    if (origin === "http://localhost:4173") await route.continue();
    else await route.abort();
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(({ theme, locale }) => {
    localStorage.setItem("theme", theme);
    localStorage.setItem("sec_qa_locale", locale);
  }, { theme, locale });
  if (surface.id === "pipeline") await installPipelineFixture(page, { initialRuns: [pipelineRun("run-reference-1")] });
  else if (surface.id === "evaluation") await installEvaluationFixture(page);
  else await installApiFixtures(page, { collections: collections(), streamDelayMs: 5 });
  await page.goto(surface.route);
  const routeId = surface.id === "collections" ? "collection-detail" : surface.id === "evaluation" ? "evaluation-run" : surface.id === "pipeline" ? "pipeline-run" : surface.id;
  await expect(page.getByRole("main", { name: "Research workspace" })).toHaveAttribute("data-route-id", routeId);
}

async function populate(page: Page, surface: Surface) {
  if (surface.id === "chat" || surface.id === "research") {
    await askQuestion(page, "What are Apple's main risk factors?");
    await expect(page.getByRole("article", { name: "Research assistant response" })).toContainText("competition risks");
    await expect(page.getByRole("button", { name: /Stop generating/ })).toHaveCount(0);
    await page.getByRole("button", { name: "Open source 1", exact: true }).first().click();
    const openDocument = page.getByRole("button", { name: /Open document for source 1/ });
    await expect(openDocument).toBeVisible();
    await openDocument.click();
    await expect(page.locator("[data-workbench-region='document']")).toBeVisible();
  } else if (surface.id === "documents") {
    await page.getByRole("checkbox", { name: "Show details for AAPL" }).check();
    await expect(page.getByRole("heading", { name: "Document Summary", exact: true })).toBeVisible();
  } else if (surface.id === "search") {
    await page.getByLabel("Search Query", { exact: true }).fill(query);
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByRole("button", { name: "Save evidence", exact: true }).first()).toBeVisible();
  } else if (surface.id === "retrieval") {
    await page.getByLabel("Retrieval Query", { exact: true }).fill(query);
    await page.getByRole("button", { name: "Run retrieval", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Retrieved Results", exact: true })).toBeVisible();
  } else if (surface.id === "pipeline") {
    await page.getByRole("button", { name: "Connect", exact: true }).first().click();
    const dialog = page.getByRole("dialog", { name: "Connect local workspace" });
    await dialog.getByLabel("Local workspace token").fill(PIPELINE_FIXTURE_TOKEN);
    await dialog.getByRole("button", { name: "Verify and connect" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByTestId("pipeline-run-detail")).toBeVisible();
    await expect(page.getByTestId("pipeline-run-detail")).toContainText("Queued");
  } else if (surface.id === "evaluation") {
    await expect(page.getByRole("complementary", { name: "Report detail" })).toContainText("baseline-native");
  } else if (surface.id === "collections") {
    await expect(page.getByRole("complementary", { name: "Risk Analysis details" })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Contents/ })).toBeVisible();
  } else {
    await expect(page.getByRole("heading", { name: "Runtime registry" })).toBeVisible();
    await expect(page.getByRole("complementary", { name: "Generator details" })).toContainText("Unknown");
  }
}

async function settle(page: Page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    // Equivalent to Playwright's animations:disabled capture policy. Firefox
    // can leave reduced-motion animations running on hidden layout targets.
    for (const animation of document.getAnimations()) {
      const timing = animation.effect?.getComputedTiming();
      if (timing && timing.iterations !== Infinity) animation.finish();
    }
    await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
  });
}

async function measurements(page: Page) {
  return page.evaluate(() => {
    const selectors = [".sidebar-shell--desktop", ".workbench-topbar", "header", ".workbench-application-main", ".workspace-primary-column", ".console-layout__aside", ".ui-detail-rail", "[data-workbench-region='research']", "[data-workbench-region='sources']", "[data-workbench-region='document']", ".collections-workspace", ".collections-detail", ".pipeline-workspace", ".pipeline-run-detail", "h1", "h2", ".ui-panel", "tbody tr", ".search-result-card", ".search-query-form__button"];
    const boxes = selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)).slice(0, 4).map((node) => {
      const b = node.getBoundingClientRect(), s = getComputedStyle(node);
      return { selector, text: node.textContent?.trim().slice(0, 60), x: b.x, y: b.y, w: b.width, h: b.height, font: s.fontSize, weight: s.fontWeight, color: s.color, background: s.backgroundColor, radius: s.borderRadius };
    }));
    const colorPairs = [".search-score__label", ".connection-status__meta"].flatMap((selector) => {
      const node = document.querySelector(selector);
      return node?.parentElement ? [{ selector, foreground: getComputedStyle(node).color, background: getComputedStyle(node.parentElement).backgroundColor }] : [];
    });
    const mobileControls = innerWidth === 390 ? Array.from(document.querySelectorAll("button, summary, input:not([type=checkbox]):not([type=radio]), textarea, select")).flatMap((node) => {
      const rect = node.getBoundingClientRect(), style = getComputedStyle(node);
      if (!rect.width || !rect.height || style.visibility === "hidden" || style.clip !== "auto" || node.closest("[inert]")) return [];
      const hitArea = node.closest("[data-composite-field]")?.getBoundingClientRect() ?? rect;
      return [{ label: node.getAttribute("aria-label") ?? node.textContent?.trim().slice(0, 60), classes: node.className, width: hitArea.width, height: hitArea.height, font: style.fontSize, input: ["INPUT", "TEXTAREA", "SELECT"].includes(node.tagName) }];
    }) : [];
    return { viewport: { width: innerWidth, height: innerHeight }, overflow: { body: document.body.scrollWidth - document.body.clientWidth, root: document.documentElement.scrollWidth - document.documentElement.clientWidth }, boxes, colorPairs, mobileControls, theme: document.documentElement.className, locale: document.documentElement.lang };
  });
}

async function primaryButtonStates(page: Page) {
  const button = page.locator(".console-btn--primary:enabled").first();
  if (!(await button.count())) return [];
  const states = [];
  for (const state of ["rest", "hover", "focus"] as const) {
    if (state === "rest") await page.mouse.move(0, 0);
    if (state === "hover") await button.hover();
    if (state === "focus") {
      await button.focus();
      await page.keyboard.press("Shift+Tab");
      await page.keyboard.press("Tab");
      await expect(button).toBeFocused();
    }
    const colors = await button.evaluate((node) => {
      const s = getComputedStyle(node);
      const luminance = (color: string) => {
        const channels = (color.match(/[\d.]+/g) ?? []).slice(0, 3).map(Number).map((value) => {
          const c = color.startsWith("color(srgb") ? value : value / 255;
          return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
        });
        return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
      };
      const a = luminance(s.color), b = luminance(s.backgroundColor);
      return { foreground: s.color, background: s.backgroundColor, ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05), outline: s.outlineStyle, outlineWidth: s.outlineWidth };
    });
    states.push({ state, ...colors });
    if (!baseline) expect(colors.ratio, `${state} primary text contrast`).toBeGreaterThanOrEqual(4.5);
    if (!baseline && state === "focus") {
      expect(colors.outline).not.toBe("none");
      expect(parseFloat(colors.outlineWidth)).toBeGreaterThanOrEqual(2);
    }
  }
  await button.evaluate((node) => (node as HTMLElement).blur());
  await page.mouse.move(0, 0);
  return states;
}

for (const surface of surfaces) {
  test(`@native ${surface.id}: native reference, geometry and whole-page accessibility`, async ({ page, browserName }) => {
    const reference = readFileSync(path.resolve("../docs/ui-references", surface.png));
    expect([reference.readUInt32BE(16), reference.readUInt32BE(20)]).toEqual([surface.width, surface.height]);
    await page.setViewportSize({ width: surface.width, height: surface.height });
    await setup(page, surface);
    await populate(page, surface);
    await settle(page);
    const primaryStates = await primaryButtonStates(page);
    const metrics = await measurements(page);
    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    const dir = `test-results/test-003/${phase}/${browserName}`;
    mkdirSync(dir, { recursive: true });
    await page.screenshot({ path: `${dir}/${surface.id}.png`, fullPage: false });
    writeFileSync(`${dir}/${surface.id}.json`, JSON.stringify({ surface, metrics, primaryStates, violations: axe.violations, incomplete: axe.incomplete }, null, 2));
    expect(metrics.overflow).toEqual({ body: 0, root: 0 });
    if (!baseline) expect(axe.violations, `${surface.id} whole-page A/AA`).toEqual([]);
    if (!baseline && (surface.id === "chat" || surface.id === "research")) {
      const separator = page.getByRole("separator", { name: "Resize Sources pane" });
      const width = Number(await separator.getAttribute("aria-valuenow"));
      await separator.focus();
      await page.keyboard.press("ArrowLeft");
      await expect(separator).toHaveAttribute("aria-valuenow", String(width + 16));
      await page.getByLabel("Open Sources pane size controls").click();
      const controls = page.getByRole("group", { name: "Sources pane size controls" });
      await controls.getByRole("button", { name: "Narrower", exact: true }).click();
      await expect(separator).toHaveAttribute("aria-valuenow", String(width));
    }
  });
}

const viewports = [[1600, 1000], [1440, 900], [1280, 856], [1024, 768], [768, 900], [390, 844], [1440, 700], [1366, 768], [1920, 1080]] as const;
for (const surface of surfaces) {
  for (const [theme, locale] of [["dark", "en"], ["dark", "vi"], ["light", "en"], ["light", "vi"]]) {
    test(`@responsive ${surface.id} ${theme}/${locale}: populated geometry`, async ({ page, browserName }) => {
      test.setTimeout(120_000);
      // Prepare using English locators, then switch through the established preference owner.
      await page.setViewportSize({ width: surface.width, height: surface.height });
      await setup(page, surface, theme, "en");
      await populate(page, surface);
      if (locale === "vi") {
        await page.getByRole("button", { name: "VI", exact: true }).click();
        await expect(page.locator("html")).toHaveAttribute("lang", "vi");
      }
      const results = [];
      for (const [width, height] of viewports) {
        await page.setViewportSize({ width, height });
        await settle(page);
        const metrics = await measurements(page);
        expect(metrics.overflow, `${surface.id} ${theme}/${locale} ${width}×${height}`).toEqual({ body: 0, root: 0 });
        for (const control of metrics.mobileControls) {
          expect(control.height, `${control.label} mobile hit area`).toBeGreaterThanOrEqual(44);
          expect(control.width, `${control.label} mobile hit area`).toBeGreaterThanOrEqual(44);
          if (control.input) expect(parseFloat(control.font), `${control.label} mobile input text`).toBeGreaterThanOrEqual(16);
        }
        const inspector = page.getByRole("dialog", { name: /Evidence inspector|Trình kiểm tra bằng chứng/ });
        if (await inspector.isVisible()) await expect(inspector).toBeVisible();
        else await expect(page.getByRole("main", { name: /Research workspace|Không gian nghiên cứu/ })).toBeVisible();
        results.push(metrics);
        if (width === 390 || (width === 1440 && height === 700)) {
          const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
          expect(axe.violations, `${surface.id} ${theme}/${locale} ${width} whole-page A/AA`).toEqual([]);
          const dir = `test-results/test-003/responsive/${browserName}`;
          mkdirSync(dir, { recursive: true });
          await page.screenshot({ path: `${dir}/${surface.id}-${theme}-${locale}-${width}x${height}.png` });
          if ((surface.id === "chat" || surface.id === "research") && width === 390) {
            const canvas = inspector.locator(".structured-reader__canvas");
            await expect(canvas).toBeVisible();
            const visibleHeight = await canvas.evaluate((node) => {
              let top = Math.max(0, node.getBoundingClientRect().top), bottom = Math.min(innerHeight, node.getBoundingClientRect().bottom);
              for (let parent = node.parentElement; parent; parent = parent.parentElement) {
                if (/hidden|auto|scroll|clip/.test(getComputedStyle(parent).overflowY)) {
                  const rect = parent.getBoundingClientRect();
                  top = Math.max(top, rect.top); bottom = Math.min(bottom, rect.bottom);
                }
              }
              return Math.max(0, bottom - top);
            });
            expect(visibleHeight, "unclipped useful phone reader content").toBeGreaterThanOrEqual(160);
            await expect(canvas.locator("mark").first()).toBeInViewport();
            await inspector.locator(".document-workspace__back").click();
            await expect(inspector.locator(".sources-pane")).toBeVisible();
            await inspector.getByRole("button", { name: /Open document for source 1|Mở tài liệu cho nguồn 1/ }).click();
            await expect(canvas).toBeVisible();
          }
          if (surface.id === "pipeline" && width === 390) {
            const track = page.getByRole("region", { name: /Staging step order|Thứ tự các bước staging/ });
            await track.scrollIntoViewIfNeeded();
            await track.focus();
            await expect(track).toBeFocused();
            const start = await track.evaluate((node) => node.scrollLeft);
            await page.keyboard.press("ArrowRight");
            await expect.poll(() => track.evaluate((node) => node.scrollLeft)).toBeGreaterThan(start);
            await page.locator(".pipeline-flow-item").last().scrollIntoViewIfNeeded();
            await expect(page.locator(".pipeline-flow-item").last()).toBeInViewport();
          }
          if (width === 390) {
            const targets = await page.locator(".console-btn:visible, .select-field__trigger:visible, .console-input:visible").evaluateAll((nodes) => nodes.map((node) => {
              const rect = node.getBoundingClientRect();
              return { text: node.getAttribute("aria-label") ?? node.textContent?.trim(), width: rect.width, height: rect.height, font: getComputedStyle(node).fontSize, input: node.classList.contains("console-input") };
            }));
            for (const target of targets) {
              expect(target.height, `${target.text} mobile target`).toBeGreaterThanOrEqual(44);
              if (target.input) expect(parseFloat(target.font)).toBeGreaterThanOrEqual(16);
            }
          }
          const scope = await inspector.isVisible() ? inspector : page.getByRole("main", { name: /Research workspace|Không gian nghiên cứu/ });
          const lastAction = scope.locator("button:visible:enabled").last();
          if (await lastAction.count()) {
            await lastAction.scrollIntoViewIfNeeded();
            await expect(lastAction).toBeInViewport();
          }
          if (await inspector.isVisible()) {
            await inspector.getByRole("button", { name: /Close evidence inspector|Đóng trình kiểm tra bằng chứng/ }).click();
            await expect(inspector).toBeHidden();
            await expect(page.getByRole("main", { name: /Research workspace|Không gian nghiên cứu/ })).toBeVisible();
          }
        }
      }
      const dir = `test-results/test-003/responsive/${browserName}`;
      mkdirSync(dir, { recursive: true });
      writeFileSync(`${dir}/${surface.id}-${theme}-${locale}.json`, JSON.stringify(results, null, 2));
    });
  }
}
