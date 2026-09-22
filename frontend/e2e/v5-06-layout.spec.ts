import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures } from "./fixtures";

async function loadAnswer(page: Parameters<typeof askQuestion>[0], width: number, height: number): Promise<void> {
  await page.setViewportSize({ width, height });
  await page.goto("/");
  await askQuestion(page, "What are Apple's main business risks?");
  await page.getByRole("button", { name: "Open 2 sources", exact: true }).click();
  await expect(page.locator("[data-workbench-region='sources']")).toBeVisible();
}

async function readPanePreferences(page: Parameters<typeof askQuestion>[0]) {
  return page.evaluate(() => JSON.parse(localStorage.getItem("sec_qa_workbench_panes_v1") ?? "{}"));
}

test.describe("V5-06 responsive workbench", () => {
  test("renders the reference four-pane geometry at 1440 and 1920", async ({ page }) => {
    await installApiFixtures(page);

    // rag-workbench-master-reference-dark.png shows navigation, conversation,
    // retrieved sources and the document viewer side by side from 1254px up,
    // so both desktop targets are four-pane.
    for (const viewport of [
      { width: 1440, height: 900, navigation: 184, mode: "four-pane", research: 508 },
      { width: 1920, height: 1080, navigation: 216, mode: "four-pane", research: 956 },
    ]) {
      if (page.url().startsWith("http")) await page.evaluate(() => localStorage.clear());
      await loadAnswer(page, viewport.width, viewport.height);

      await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-layout-mode", viewport.mode);
      await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-navigation-width", String(viewport.navigation));
      await expect(page.locator("[data-workbench-region='research']")).toBeVisible();
      await expect(page.locator("[data-workbench-region='sources']")).toBeVisible();
      if (viewport.mode === "four-pane") {
        await expect(page.locator("[data-document-pane='true']")).toBeVisible();
      } else {
        await expect(page.locator("[data-document-pane='true']")).toHaveCount(0);
      }

      const geometry = await page.evaluate(() => {
        const box = (selector: string) => {
          const element = document.querySelector<HTMLElement>(selector);
          if (!element) return null;
          const rect = element.getBoundingClientRect();
          return { left: rect.left, width: rect.width, right: rect.right, height: rect.height };
        };
        return {
          research: box("[data-workbench-region='research']"),
          sources: box("[data-workbench-region='sources']"),
          document: box("[data-document-pane='true']"),
          splitters: Array.from(document.querySelectorAll<HTMLElement>("[data-pane-resizer]")).map((element) => element.getBoundingClientRect().width),
          viewportWidth: window.innerWidth,
          scrollWidth: document.documentElement.scrollWidth,
        };
      });

      expect(geometry.research?.width).toBeCloseTo(viewport.research, 0);
      expect(Math.abs((geometry.sources?.width ?? 0) - 332)).toBeLessThanOrEqual(1);
      if (viewport.mode === "four-pane") {
        expect(geometry.document?.width).toBeCloseTo(400, 0);
        expect(geometry.splitters).toEqual([8, 8]);
      } else {
        expect(geometry.document).toBeNull();
        expect(geometry.splitters).toEqual([]);
      }
      expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.viewportWidth);

      if (test.info().project.name === "chromium") {
        await page.screenshot({
          path: `e2e/screenshots/v5-06-four-pane-${viewport.width}x${viewport.height}.png`,
          fullPage: false,
        });
      }
    }
  });

  test("uses the context dock and then truthful modal surfaces as geometry narrows", async ({ page }) => {
    await installApiFixtures(page);

    // The reference width keeps the side-by-side composition. The measured
    // container excludes the 56px toolbar, so 768px of viewport is below the
    // four-pane height floor; the reference height is 856px.
    await loadAnswer(page, 1366, 856);
    await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-layout-mode", "four-pane");
    await expect(page.locator("[data-workbench-region='sources']")).toBeVisible();
    await expect(page.locator("[data-document-pane='true']")).toBeVisible();

    await page.setViewportSize({ width: 1280, height: 856 });
    await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-layout-mode", "four-pane");

    // A wide but short viewport is where the dock is the honest presentation:
    // the two context panes share one rail and switch by tab.
    await page.setViewportSize({ width: 1920, height: 700 });
    await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-layout-mode", "context-dock");
    const contextTabs = page.getByRole("tablist", { name: "Context panes" });
    await expect(contextTabs).toBeVisible();

    await contextTabs.getByRole("tab", { name: "Sources", exact: true }).click();
    await expect(page.locator("[data-workbench-region='sources']")).toBeVisible();
    await expect(page.locator("[data-document-pane='true']")).toHaveCount(0);

    await contextTabs.getByRole("tab", { name: "Document", exact: true }).click();
    await expect(page.locator("[data-document-pane='true']")).toBeVisible();
    await expect(page.locator("[data-workbench-region='sources']")).toHaveCount(0);
    await contextTabs.getByRole("tab", { name: "Sources", exact: true }).click();
    await expect(page.locator("[data-workbench-region='sources']")).toBeVisible();

    await page.setViewportSize({ width: 1366, height: 520 });
    await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-layout-mode", "contextual-surface");
    await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-short-height", "true");
    await expect(page.locator(".evidence-drawer-dialog")).toBeVisible();
    await expect(page.locator("#root")).toHaveAttribute("inert", "");
    const shortHeightOverflow = await page.locator("[data-workbench-app='true']").evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    expect(shortHeightOverflow).toBe(true);
    await page.keyboard.press("Escape");
    await expect(page.locator("#root")).not.toHaveAttribute("inert", "");

    await page.setViewportSize({ width: 1024, height: 768 });
    await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-layout-mode", "drawer");
    await page.getByRole("button", { name: "Open source 1", exact: true }).first().click();
    await expect(page.locator(".evidence-drawer-dialog")).toBeVisible();
    await expect(page.locator("#root")).toHaveAttribute("inert", "");
    await expect(page.locator(".context-panel__close")).toBeFocused();

    await page.keyboard.press("Escape");
    await expect(page.locator(".evidence-drawer-dialog")).toHaveCount(0);
    await expect(page.locator("#root")).not.toHaveAttribute("inert", "");

    await page.setViewportSize({ width: 768, height: 900 });
    const sourceButton = page.getByRole("button", { name: "Open source 1", exact: true }).first();
    await sourceButton.click();
    await expect(page.locator(".evidence-drawer-dialog")).toBeVisible();
    await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-layout-mode", "drawer");
    await expect(page.locator("#root")).toHaveAttribute("inert", "");
    await page.keyboard.press("Escape");
    await expect(page.locator("#root")).not.toHaveAttribute("inert", "");
    await expect(sourceButton).toBeFocused();

    await page.setViewportSize({ width: 390, height: 844 });
    await sourceButton.click();
    await expect(page.locator(".evidence-drawer-dialog")).toBeVisible();
    await expect(page.locator(".workbench-layout")).toHaveAttribute("data-workbench-layout-mode", "single-surface");
    await page.keyboard.press("Escape");
    await expect(page.locator("#root")).not.toHaveAttribute("inert", "");
  });

  test("keeps pointer resizing off React until commit and exposes keyboard/reset/collapse controls", async ({ page }) => {
    await installApiFixtures(page);
    await loadAnswer(page, 1920, 1080);

    const resizer = page.locator("[data-pane-resizer='sources']");
    await expect(resizer).toHaveAttribute("aria-valuemin", "300");
    await expect(resizer).toHaveAttribute("aria-valuemax", "400");
    const initial = await readPanePreferences(page);

    const box = await resizer.boundingBox();
    expect(box).not.toBeNull();
    await page.mouse.move((box?.x ?? 0) + (box?.width ?? 0) / 2, (box?.y ?? 0) + 200);
    await page.mouse.down();
    await page.mouse.move((box?.x ?? 0) + (box?.width ?? 0) / 2 - 24, (box?.y ?? 0) + 200, { steps: 2 });
    await page.waitForTimeout(20);
    expect(await readPanePreferences(page)).toEqual(initial);
    await page.mouse.up();
    // Dragging the splitter left widens the sources pane, as the V5 control
    // has always behaved; the delta is what this test pins, not the sign.
    await expect.poll(async () => (await readPanePreferences(page)).sourcesWidth).toBe(356);

    await resizer.focus();
    await page.keyboard.press("Home");
    await expect.poll(async () => (await readPanePreferences(page)).sourcesWidth).toBe(300);
    await page.keyboard.press("End");
    await expect.poll(async () => (await readPanePreferences(page)).sourcesWidth).toBe(400);
    await page.keyboard.press("Enter");
    await expect(page.locator("[data-workbench-region='sources']")).toHaveAttribute("data-sources-collapsed", "true");
    await expect.poll(async () => (await readPanePreferences(page)).sourcesCollapsed).toBe(true);
    await page.keyboard.press("Enter");
    await expect(page.locator("[data-workbench-region='sources']")).toHaveAttribute("data-sources-collapsed", "false");

    await resizer.dblclick();
    await expect.poll(async () => (await readPanePreferences(page)).sourcesWidth).toBe(332);

    const documentPane = page.locator("[data-document-pane='true']");
    await documentPane.getByRole("button", { name: "Collapse document pane", exact: true }).click();
    await expect(page.locator("[data-document-pane-collapsed='true']")).toBeVisible();
    await page.getByRole("button", { name: "Expand document pane", exact: true }).click();
    await expect(documentPane).toBeVisible();
    const noPageOverflow = await page.locator("[data-workbench-app='true']").evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    expect(noPageOverflow).toBe(true);
  });
});
