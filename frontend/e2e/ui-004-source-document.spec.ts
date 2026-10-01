import { expect, test } from "@playwright/test";

import { askQuestion, installApiFixtures } from "./fixtures";

/**
 * UI-004 source/document composition receipts and behaviour. Deterministic
 * fixture API only; no provider is reached.
 *
 * Reference targets: docs/ui-references/rag-workbench-master-reference-dark.png
 * (1254x856) and research-ui-reference-dark-v1.png (1586x992), which both show
 * the retrieved-sources rail beside the document viewer.
 */

const VIEWPORTS = [
  { name: "1254x856", width: 1254, height: 856 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1280x856", width: 1280, height: 856 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "390x844", width: 390, height: 844 },
] as const;

async function openEvidence(page: import("@playwright/test").Page) {
  await askQuestion(page, "What are Apple's main business risks?");
  await expect(page.getByRole("article", { name: "Research assistant response" })).toBeVisible();
  await page.getByRole("button", { name: "Open source 1", exact: true }).first().click();
}

async function layoutMode(page: import("@playwright/test").Page): Promise<string> {
  return (await page.locator("[data-workbench-layout]").getAttribute("data-workbench-layout-mode")) ?? "unknown";
}

test.describe("UI-004 source and document composition", () => {
  test("a selected citation opens the sources rail without regenerating the answer", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page, { streamDelayMs: 5 });
    await page.goto("/research?mode=conversation");
    await openEvidence(page);

    // The evidence surface is open and the sources rail lists the answer's
    // real sources.
    expect(await layoutMode(page)).toBe("four-pane");
    await expect(page.getByRole("complementary", { name: "Sources and document" })).toBeVisible();
    await expect(page.getByText("Retrieved Sources")).toBeVisible();

    // Selecting a source does not issue another answer request.
    const streamed = await page.evaluate(() => (window as unknown as { __streamCount?: number }).__streamCount ?? 0);
    expect(streamed).toBe(0);
  });

  test("keeps the reference four-pane composition at the 1254px reference width", async ({ page }) => {
    await page.setViewportSize({ width: 1254, height: 856 });
    await installApiFixtures(page, { streamDelayMs: 5 });
    await page.goto("/research?mode=conversation");
    await openEvidence(page);

    // rag-workbench-master-reference-dark.png shows navigation, conversation,
    // retrieved sources and the document viewer side by side at 1254px.
    expect(await layoutMode(page)).toBe("four-pane");
    await expect(page.getByRole("complementary", { name: "Sources and document" })).toBeVisible();
    await expect(page.getByText("Retrieved Sources")).toBeVisible();
  });

  test("captures the source/document composition at the reference widths", async ({ page, browserName }) => {
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await installApiFixtures(page, { streamDelayMs: 5 });
      await page.goto("/research?mode=conversation");
      await openEvidence(page);

      // Wide viewports keep the reference four-pane workbench; narrow ones use
      // the documented contextual fallback. Either way the retrieved-source
      // rail must be present with the answer's real sources.
      const mode = await layoutMode(page);
      if (viewport.width >= 1254) {
        expect(mode, `layout mode at ${viewport.name}`).toBe("four-pane");
      }
      await expect(page.getByText("Retrieved Sources")).toBeVisible();

      await page.screenshot({
        path: `test-results/ui-004/evidence-${viewport.name}-${browserName}.png`,
        fullPage: false,
      });

      const overflow = await page.evaluate(() => ({
        body: document.body.scrollWidth - document.body.clientWidth,
        root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      }));
      expect(overflow.body, `body overflow at ${viewport.name}`).toBeLessThanOrEqual(0);
      expect(overflow.root, `root overflow at ${viewport.name}`).toBeLessThanOrEqual(0);
    }
  });
});
