import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures, LONG_ANSWER } from "./fixtures";

test.describe("V5-03 source pane", () => {
  test("keeps source identity, state filters, focus, and reader handoff explicit", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page, { pdf: true });
    await page.goto("/");
    await askQuestion(page, "What are Apple's main business risks?");

    await expect(page.getByText(LONG_ANSWER.split("\n")[0], { exact: true }).first()).toBeVisible();
    await page.getByRole("button", { name: "Open 2 sources", exact: true }).click();

    const pane = page.locator("[data-workbench-region='sources']");
    await expect(pane).toBeVisible();
    await expect(pane.getByRole("heading", { name: "Retrieved sources", exact: true })).toBeVisible();
    await expect(pane.getByRole("listitem")).toHaveCount(2);
    await expect(pane.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
    await expect(pane.getByRole("button", { name: "Cited" })).toBeVisible();

    await page.screenshot({
      path: "e2e/screenshots/v5-03-sources-1440x900.png",
      fullPage: false,
    });

    await pane.getByRole("button", { name: "Save evidence source 1" }).click();
    await expect(pane.getByRole("button", { name: "Evidence saved for source 1" })).toBeDisabled();
    await expect(pane.getByText("Saved evidence").first()).toBeVisible();

    await pane.getByRole("button", { name: "Cited" }).click();
    await expect(pane.getByRole("button", { name: "Cited" })).toHaveAttribute("aria-pressed", "true");
    await expect(pane.getByRole("listitem")).toHaveCount(2);

    const sourceList = pane.getByRole("list", { name: "Source evidence list" });
    await sourceList.focus();
    await page.keyboard.press("End");
    await expect(pane.getByRole("button", { name: /Open source excerpt 2:/ })).toHaveAttribute("aria-pressed", "true");
    // The reference geometry keeps Sources and the document pane side by side
    // at this width, so selection stays in Sources and the explicit document
    // action owns the cross-pane handoff.
    await pane.getByRole("button", { name: "Open document for source 2" }).click();
    await expect(page.locator(".document-context-panel__excerpt")).toContainText("Microsoft Cloud revenue increased");

    // Four-pane shows both panes at once, so the pane switcher only exists in
    // the dock/overlay presentations.
    const layoutMode = await page.locator("[data-workbench-layout]").getAttribute("data-workbench-layout-mode");
    if (layoutMode !== "four-pane") {
      await page.getByRole("tab", { name: "Sources", exact: true }).click();
    }
    await pane.getByRole("button", { name: /^Saved/ }).click();
    await expect(pane.getByRole("button", { name: /^Saved/ })).toHaveAttribute("aria-pressed", "true");
    await expect(pane.getByRole("listitem")).toHaveCount(1);
    await expect(pane.getByText("AAPL 10-K (filed 2025-10-31)", { exact: false })).toBeVisible();
  });
});
