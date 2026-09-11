import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures } from "./fixtures";

test.describe("saved answer versions", () => {
  test("persists the displayed answer, deduplicates repeats, and reopens it from Library", async ({ page }) => {
    await installApiFixtures(page);
    await page.goto("/");
    await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
    await askQuestion(page, "What are Apple's main business risks?");

    await page.getByText("More actions", { exact: true }).click();
    await page.getByRole("button", { name: "Save answer version" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Answer version saved to Library." })).toBeVisible();

    await page.getByRole("button", { name: "Save answer version" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Already saved." })).toBeVisible();

    await page.getByRole("button", { name: "View in Library" }).click();
    await expect(page.getByRole("heading", { name: "Saved conversations" })).toBeVisible();
    await page.getByRole("button", { name: /messages ·/ }).click();
    await expect(page.getByRole("button", { name: "Variant 1" })).toBeVisible();
    await page.getByRole("button", { name: "Variant 1" }).click();
    await expect(page.getByText("Apple's total net sales were $391,035 million in fiscal 2024")).toBeVisible();
  });
});
