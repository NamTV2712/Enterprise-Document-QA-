import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures, LONG_ANSWER } from "./fixtures";

test.describe("PDF representation viewer", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("renders real PDF.js bytes without fabricating an evidence overlay", async ({ page }) => {
    await installApiFixtures(page, { pdf: true });
    await page.goto("/");
    await askQuestion(page, "What are the company's competition risks?");
    await expect(page.getByText(LONG_ANSWER.split("\n")[0], { exact: true }).first()).toBeVisible();

    await page.getByRole("button", { name: "Open 2 sources", exact: true }).dispatchEvent("click");
    const sources = page.locator("[data-workbench-region='sources']");
    await sources.getByRole("button", { name: /Open document for source 1/ }).click();

    const document = page.locator("[data-workbench-region='document']");
    await expect(document.getByRole("button", { name: "PDF", exact: true })).toBeVisible();
    await document.getByRole("button", { name: "PDF", exact: true }).click();

    const viewer = document.locator("[data-pdf-viewer='true']");
    const firstPageStarted = Date.now();
    await expect(viewer).toHaveAttribute("data-pdf-state", "ready", { timeout: 20_000 });
    const firstPageMs = Date.now() - firstPageStarted;
    await expect(viewer.locator("canvas")).toHaveAttribute("aria-label", "PDF page 1");
    await expect(viewer.getByRole("button", { name: "Zoom in" })).toBeEnabled();
    await expect(viewer.locator(".pdf-viewer__evidence-highlight")).toHaveCount(0);
    await expect(viewer.getByText("The selected range has no complete PDF rectangle mapping.", { exact: true })).toBeVisible();
    await expect(viewer.getByText("Verified PDF evidence", { exact: true })).toHaveCount(0);

    await viewer.getByRole("button", { name: "Zoom in" }).click();
    await expect(viewer.locator(".pdf-viewer__zoom-controls")).toContainText("%");
    await viewer.getByRole("textbox", { name: "Find in PDF" }).fill("Generated PDF");
    const searchStarted = Date.now();
    await viewer.getByRole("button", { name: "Find", exact: true }).click();
    await expect(viewer.getByText(/pages with matches/)).toBeVisible();
    const searchMs = Date.now() - searchStarted;
    const memoryBytes = await page.evaluate(() => {
      const candidate = performance as Performance & { memory?: { usedJSHeapSize?: number } };
      return candidate.memory?.usedJSHeapSize ?? null;
    });
    console.log(`[PDF perf] first page ${firstPageMs}ms; search ${searchMs}ms; heap ${memoryBytes ?? "unavailable"}`);
    expect(firstPageMs).toBeLessThan(10_000);
    expect(searchMs).toBeLessThan(2_000);

    await page.screenshot({ path: ".audit-runtime/pdf-viewer-1440x900.png" });
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.screenshot({ path: ".audit-runtime/pdf-viewer-1920x1080.png" });
    await page.setViewportSize({ width: 720, height: 900 });
    await expect(viewer).toHaveAttribute("data-pdf-state", "ready", { timeout: 20_000 });
    await expect(document.locator("[data-document-representation='pdf']")).toBeVisible();
    await page.screenshot({ path: ".audit-runtime/pdf-viewer-720x900.png" });
  });
});
