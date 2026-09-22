import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures } from "./fixtures";

test.describe("V5-05 exact source synchronization", () => {
  test("opens the selected citation in both reader representations with exact identity", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    await page.goto("/");
    await askQuestion(page, "What are Apple's main business risks?");

    await page.getByRole("button", { name: "Open 2 sources", exact: true }).click();
    const sourcesPane = page.locator("[data-workbench-region='sources']");
    await sourcesPane.getByRole("button", { name: /Open document for source 1/ }).click();

    const documentPane = page.locator("[data-document-pane='true']");
    await expect(documentPane).toBeVisible();
    await expect(documentPane.getByText("Evidence correspondence verified in the structured document.", { exact: true })).toBeVisible();
    await expect(documentPane.locator(".structured-reader__evidence-match")).toHaveCount(1);
    if (test.info().project.name === "chromium") {
      await page.screenshot({ path: "e2e/screenshots/v5-05-sync-1440x900.png", fullPage: true });
    }

    const linkedUrl = new URL(page.url());
    expect(linkedUrl.hash).toContain("#evidence=");
    expect(linkedUrl.hash).toContain("conversationId=");
    expect(linkedUrl.hash).toContain("sourceKey=");

    await documentPane.getByRole("button", { name: "Normalized text", exact: true }).click();
    await expect(documentPane.getByText("Evidence correspondence verified in this document representation.", { exact: true })).toBeVisible();
    await expect(documentPane.locator(".original-reader__evidence-match")).toHaveCount(1);
  });

  test("reopens an exact canonical deep link without falling forward to another source", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    await page.goto("/");
    await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
    await page.getByRole("button", { name: "Open 2 sources", exact: true }).click();
    const sourcesPane = page.locator("[data-workbench-region='sources']");
    await sourcesPane.getByRole("button", { name: /Open source excerpt 2:/ }).click();

    const linkedUrl = page.url();
    expect(new URL(linkedUrl).hash).toContain("sourceKey=");
    await page.reload();

    const reopenedSources = page.locator("[data-workbench-region='sources']");
    await expect(reopenedSources).toBeVisible();
    await expect(reopenedSources.getByRole("button", { name: /Open source excerpt 2:/ })).toHaveAttribute("aria-pressed", "true");
    await expect(reopenedSources.getByText("Microsoft Cloud revenue increased", { exact: false })).toBeVisible();
  });
});
