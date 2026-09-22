import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures } from "./fixtures";

test.describe("V5-04 shared document pane", () => {
  test("keeps both real representations, context tabs, find state, and restore controls explicit", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    await page.goto("/");
    await askQuestion(page, "What are Apple's main business risks?");

    await expect(page.getByText("competition risks").first()).toBeVisible();
    await page.getByRole("button", { name: "Open 2 sources", exact: true }).click();
    const sourcesPane = page.locator("[data-workbench-region='sources']");
    await expect(sourcesPane).toBeVisible();
    await sourcesPane.getByRole("button", { name: /Open source excerpt 1:/ }).click();
    const contextTabs = page.getByRole("tablist", { name: "Context panes" });
    if (await contextTabs.isVisible().catch(() => false)) {
      await contextTabs.getByRole("tab", { name: "Document", exact: true }).click();
    } else {
      const legacyOriginalAction = page.getByRole("button", { name: "Open normalized original", exact: true });
      if (await legacyOriginalAction.isVisible()) await legacyOriginalAction.click();
    }

    const pane = page.locator("[data-document-pane='true']");
    await expect(pane).toBeVisible();
    await expect(pane.getByRole("heading", { name: "Risk factors", exact: true })).toBeAttached();
    await expect(pane.getByRole("button", { name: "Structured", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expect(pane.getByRole("button", { name: "Normalized text", exact: true })).toHaveAttribute("aria-pressed", "false");
    await expect(pane.getByRole("tab", { name: "Evidence", exact: true })).toBeVisible();
    await expect(pane.getByRole("tab", { name: "Metadata", exact: true })).toBeVisible();
    await expect(pane.getByRole("tab", { name: "Notes", exact: true })).toHaveCount(0);

    const structuredFind = pane.getByRole("textbox", { name: "Find in document" });
    await structuredFind.fill("competition");
    await expect(structuredFind).toHaveValue("competition");
    await expect(pane.locator("[data-reader-representation='structured']")).toBeVisible();

    await pane.getByRole("button", { name: "Normalized text", exact: true }).click();
    await expect(pane.getByRole("button", { name: "Normalized text", exact: true })).toHaveAttribute("aria-pressed", "true");
    const normalizedReader = pane.locator("[data-reader-representation='normalized']");
    await expect(normalizedReader).toBeVisible();
    await expect(normalizedReader.getByRole("textbox", { name: "Find in original source" })).toHaveValue("competition");

    await pane.getByRole("tab", { name: "Metadata", exact: true }).click();
    await expect(pane.locator("#document-context-panel-metadata")).toBeVisible();
    await expect(pane.locator("#document-context-panel-metadata")).toContainText("Document ID");

    await pane.getByRole("button", { name: "Expand document" }).click();
    await expect(pane.locator(".document-workspace.is-expanded")).toBeVisible();
    await expect(pane.getByRole("button", { name: "Restore document" })).toBeVisible();
    await pane.getByRole("button", { name: "Restore document" }).click();
    await expect(pane.getByRole("button", { name: "Expand document" })).toBeVisible();

    await expect(pane.locator("input[aria-label*='Page'], input[aria-label*='Zoom'], button[aria-label*='Page'], button[aria-label*='Zoom']")).toHaveCount(0);
    await page.screenshot({ path: "e2e/screenshots/v5-04-document-1440x900.png", fullPage: false });
  });
});
