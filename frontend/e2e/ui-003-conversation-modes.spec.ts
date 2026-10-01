import { expect, test } from "@playwright/test";

import { askQuestion, installApiFixtures } from "./fixtures";

/**
 * UI-003 Chat/Research composition. Deterministic fixture API only; no
 * provider is ever reached. The screenshots recorded here are the receipts
 * compared against the two authoritative local references.
 */

const VIEWPORTS = [
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1280x856", width: 1280, height: 856 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "390x844", width: 390, height: 844 },
] as const;

test.describe("UI-003 conversation modes", () => {
  test("chat route is direct and research route keeps its own composition", async ({ page }) => {
    await installApiFixtures(page);

    await page.goto("/chat");
    await expect(page.getByRole("heading", { name: "Chat", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /New Chat/ })).toBeVisible();
    await expect(page.getByTestId("conversation-insights")).toHaveCount(0);

    await page.goto("/research?mode=conversation");
    await expect(page.getByRole("heading", { name: "Research", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /New Research/ })).toBeVisible();
  });

  test("asking on the chat page keeps the chat composition through streaming", async ({ page }) => {
    await installApiFixtures(page, { streamDelayMs: 5 });
    await page.goto("/chat");

    await askQuestion(page, "What are Apple's main risk factors?");
    await expect(page.getByRole("article", { name: "Research assistant response" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Chat", level: 2 })).toBeVisible();
    await expect(page).toHaveURL(/\/chat/);
  });

  test("research mode renders real insight tiles and keeps follow-ups composer-only", async ({ page }) => {
    await installApiFixtures(page, { streamDelayMs: 5 });
    await page.goto("/research?mode=conversation");

    await askQuestion(page, "How did Apple revenue change?");
    const answer = page.getByRole("article", { name: "Research assistant response" });
    await expect(answer).toBeVisible();
    await expect(answer).toContainText("competition risks");

    const insights = page.getByTestId("conversation-insights");
    await expect(insights).toBeVisible();
    await expect(insights.getByText("Sources used")).toBeVisible();

    const followUps = page.getByTestId("conversation-followups");
    await expect(followUps).toBeVisible();
    const composer = page.getByRole("textbox", { name: "Research question" });
    await expect(composer).toHaveValue("");
    await followUps.getByRole("button").first().click();
    // Selecting a follow-up fills the draft; it never submits a request.
    await expect(composer).not.toHaveValue("");
  });

  for (const viewport of VIEWPORTS) {
    test(`captures Chat and Research receipts at ${viewport.name}`, async ({ page, browserName }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await installApiFixtures(page, { streamDelayMs: 5 });

      // Fresh chat: the direct start surface.
      await page.goto("/chat");
      await expect(page.getByRole("heading", { name: "Chat", level: 2 })).toBeVisible();
      await page.screenshot({
        path: `test-results/ui-003/chat-empty-${viewport.name}-${browserName}.png`,
        fullPage: false,
      });

      // Populated chat: question + grounded answer in the chat composition.
      await askQuestion(page, "What are Apple's main risk factors?");
      await expect(page.getByRole("article", { name: "Research assistant response" })).toBeVisible();
      await page.screenshot({
        path: `test-results/ui-003/chat-answer-${viewport.name}-${browserName}.png`,
        fullPage: false,
      });

      // Populated research: the organized composition on a clean record.
      await page.evaluate(() => {
        window.localStorage.clear();
        window.location.assign("/research?mode=conversation");
      });
      await expect(page.getByRole("heading", { name: "Research", level: 2 })).toBeVisible();
      await askQuestion(page, "How did Apple revenue change?");
      await expect(page.getByRole("article", { name: "Research assistant response" })).toBeVisible();
      await page.screenshot({
        path: `test-results/ui-003/research-answer-${viewport.name}-${browserName}.png`,
        fullPage: false,
      });

      // Research detail: scrolled to the end so the real insight tiles show.
      await page.locator(".conversation-message-scroll").evaluate((node) => {
        node.scrollTop = node.scrollHeight;
      });
      await expect(page.getByTestId("conversation-insights")).toBeVisible();
      await page.screenshot({
        path: `test-results/ui-003/research-insights-${viewport.name}-${browserName}.png`,
        fullPage: false,
      });

      // No body-level horizontal scrolling at any target width.
      const overflow = await page.evaluate(() => ({
        body: document.body.scrollWidth - document.body.clientWidth,
        root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      }));
      expect(overflow.body, `body overflow at ${viewport.name}`).toBeLessThanOrEqual(0);
      expect(overflow.root, `root overflow at ${viewport.name}`).toBeLessThanOrEqual(0);
    });
  }
});
