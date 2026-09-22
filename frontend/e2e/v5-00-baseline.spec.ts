import { test, expect } from "@playwright/test";
import { askQuestion, installApiFixtures, LONG_ANSWER } from "./fixtures";

/**
 * V5-00 baseline capture. The assertions intentionally describe behavior that
 * remains valid after the workbench migration; the logged legacy geometry
 * records the current rail composition without freezing obsolete selectors as
 * a future-target acceptance test.
 */
test.describe("V5-00 current workbench baseline", () => {
  test.use({ reducedMotion: "reduce" });

  for (const viewport of [
    { name: "1440x900", width: 1440, height: 900 },
    { name: "1920x1080", width: 1920, height: 1080 },
  ]) {
    test(`captures ${viewport.name} answer and evidence composition`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await installApiFixtures(page);
      await page.goto("/");
      await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
      await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();
      await page.getByRole("button", { name: "Open source 1", exact: true }).first().click();
      await expect(page.getByText("The company faces competition risks in consumer markets").first()).toBeVisible();

      const geometry = await page.evaluate(() => {
        const rect = (selector: string) => {
          const element = document.querySelector<HTMLElement>(selector);
          if (!element) return null;
          const box = element.getBoundingClientRect();
          return { left: box.left, top: box.top, width: box.width, height: box.height };
        };
        return {
          viewport: { width: window.innerWidth, height: window.innerHeight },
          scrollWidth: document.documentElement.scrollWidth,
          sidebar: rect(".sidebar-shell--desktop"),
          primary: rect(".workspace-primary-column"),
          legacyEvidenceRail: rect(".context-panel"),
          legacyEvidenceGrid: rect(".workspace-main-grid--with-evidence"),
          sourceCards: document.querySelectorAll(".context-source-card").length,
          reader: rect(".context-viewer"),
        };
      });
      console.log(`[V5-00 baseline] ${testInfo.project.name} ${viewport.name} ${JSON.stringify(geometry)}`);
      expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.viewport.width);
      await page.screenshot({
        path: `e2e/screenshots/v5-00-baseline-${testInfo.project.name}-${viewport.name}.png`,
        fullPage: false,
      });
    });
  }
});
