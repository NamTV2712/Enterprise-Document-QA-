import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures } from "./fixtures";

test.describe("V4 document workspace shell", () => {
  test("keeps sources and reader in separate non-overlapping regions", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await installApiFixtures(page);
    await page.goto("/");
    await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
    await askQuestion(page, "What are Apple's main business risks?");
    await expect(page.getByText("competition risks").first()).toBeVisible();
    await page.getByRole("button", { name: "Open source 1", exact: true }).first().click();

    const panel = page.locator(".context-panel");
    await expect(panel).toBeVisible();
    const geometry = await page.evaluate(() => {
      const read = (selector: string) => {
        const element = document.querySelector<HTMLElement>(selector);
        if (!element) throw new Error(`Missing ${selector}`);
        const rect = element.getBoundingClientRect();
        return {
          top: rect.top,
          bottom: rect.bottom,
          clientHeight: element.clientHeight,
          scrollHeight: element.scrollHeight,
          overflowY: getComputedStyle(element).overflowY,
        };
      };
      return { panel: read(".context-panel"), sources: read(".context-sources"), sourceList: read(".context-source-list"), viewer: read(".context-viewer"), viewerText: read(".context-viewer-text") };
    });

    expect(geometry.sources.bottom).toBeLessThanOrEqual(geometry.viewer.top + 1);
    expect(geometry.panel.overflowY).toBe("hidden");
    expect(geometry.sourceList.overflowY).toBe("auto");
    expect(geometry.viewer.overflowY).toBe("auto");
    expect(geometry.viewerText.overflowY).toBe("visible");
    expect(await panel.getByRole("link", { name: "Open SEC" }).getAttribute("href")).toMatch(/^https:\/\/www\.sec\.gov\//);
  });

  test("moves the same reader into a bounded drawer at a short tablet width", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 480 });
    await installApiFixtures(page);
    await page.goto("/");
    await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
    await askQuestion(page, "What are Apple's main business risks?");
    await page.getByRole("button", { name: "Open source 1", exact: true }).first().click();

    await expect(page.getByRole("dialog", { name: "Evidence inspector" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Close evidence inspector" })).toBeVisible();
    const overflow = await page.evaluate(() => ({ documentWidth: document.documentElement.scrollWidth, viewportWidth: window.innerWidth }));
    expect(overflow.documentWidth).toBeLessThanOrEqual(overflow.viewportWidth);
  });
});
