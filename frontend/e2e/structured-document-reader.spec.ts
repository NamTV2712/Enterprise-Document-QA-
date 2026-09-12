import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures } from "./fixtures";

test.describe("V4 structured document reader", () => {
  test("opens an application-rendered document, navigates content, and searches it", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await installApiFixtures(page);
    await page.goto("/");
    await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
    await askQuestion(page, "What are Apple's main business risks?");
    await expect(page.getByText("competition risks").first()).toBeVisible();
    await page.getByRole("button", { name: "Open source 1", exact: true }).first().click();
    await page.getByRole("button", { name: "Open normalized original", exact: true }).click();

    await expect(page.locator(".document-workspace")).toBeVisible();
    await expect(page.locator(".structured-reader__availability")).toContainText("Structured HTML source ready");
    await expect(page.getByText("Evidence correspondence verified in the structured document.", { exact: true })).toBeVisible();
    const heading = page.getByRole("heading", { name: "Risk factors", exact: true });
    await expect(heading).toBeAttached();
    await heading.scrollIntoViewIfNeeded();
    await expect(heading).toBeVisible();
    const table = page.locator(".structured-reader__canvas table");
    await expect(table).toBeAttached();
    await table.scrollIntoViewIfNeeded();
    await expect(table).toContainText("416,161");

    const find = page.getByRole("textbox", { name: "Find in document" });
    await find.fill("competition");
    await find.press("Enter");
    await expect(page.getByRole("status").filter({ hasText: "1 match" })).toBeVisible();
  });
});
