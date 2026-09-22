import { expect, test } from "@playwright/test";
import { askQuestion, installApiFixtures, LONG_ANSWER } from "./fixtures";

test.describe("saved answer versions", () => {
  test("persists the displayed answer, deduplicates repeats, and reopens it from Library", async ({ page }) => {
    await installApiFixtures(page);
    await page.goto("/");
    await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
    await askQuestion(page, "What are Apple's main business risks?");

    await page.locator(".message-secondary-actions > summary").click();
    await page.getByRole("button", { name: "Save answer version" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Answer version saved to Library." })).toBeVisible();

    await page.getByRole("button", { name: "Save answer version" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Already saved." })).toBeVisible();

    await page.getByRole("button", { name: "View in Library" }).click();
    await page.getByRole("tab", { name: "Conversations", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Conversation history", exact: true })).toBeVisible();
    await page.getByRole("button", { name: /messages ·/ }).click();
    await expect(page.getByRole("button", { name: "Variant 1" })).toBeVisible();
    await page.getByRole("button", { name: "Variant 1" }).click();
    await expect(page.getByText(LONG_ANSWER.split("\n")[0], { exact: true })).toBeVisible();
  });
});
