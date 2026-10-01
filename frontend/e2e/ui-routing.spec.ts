import { expect, test } from "@playwright/test";

import { installApiFixtures } from "./fixtures";
import { installPipelineFixture } from "./pipeline-fixtures";

const directRoutes = [
  ["/chat", "chat"],
  ["/chat/missing-conversation", "chat-conversation"],
  ["/research", "research"],
  ["/research/missing-conversation", "research-conversation"],
  ["/documents", "documents"],
  ["/documents/AAPL%3A10-K%3A2025", "document-detail"],
  ["/search?company=AAPL&company=MSFT", "search"],
  ["/collections", "collections"],
  ["/collections/saved-1", "collection-detail"],
  ["/retrieval", "retrieval"],
  ["/models", "models"],
  ["/pipeline", "pipeline"],
  ["/pipeline/runs/run-1", "pipeline-run"],
  ["/reranker", "reranker"],
  ["/evaluation", "evaluation"],
  ["/evaluation/runs/eval-1", "evaluation-run"],
  ["/analytics", "analytics"],
  ["/datasets", "datasets"],
  ["/settings", "settings"],
  ["/logs", "logs"],
] as const;

test.describe("UI-002 routing and shell", () => {
  test("serves every explicit route directly from the production preview", async ({ page }) => {
    await installPipelineFixture(page);
    for (const [path, routeId] of directRoutes) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("main", { name: "Research workspace" })).toHaveAttribute("data-route-id", routeId);
    }
    await expect(page.getByRole("heading", { name: "Logs", exact: true })).toBeVisible();
    await expect(page.getByText("Private data is not connected")).toBeVisible();
  });

  test("translates legacy URLs once and preserves query and evidence identity", async ({ page }) => {
    await installApiFixtures(page);
    let generatedAnswers = 0;
    page.on("request", (request) => {
      if (/\/query\/(stream|decomposed\/stream)$/.test(new URL(request.url()).pathname)) generatedAnswers += 1;
    });
    const hash = "#evidence=answer-1-0?conversationId=missing-conversation&variantId=v1&sourceKey=s%2F1";
    await page.goto(`/?view=conversation&company=AAPL&company=MSFT${hash}`);
    await expect(page).toHaveURL(new RegExp(`/research/missing-conversation\\?company=AAPL&company=MSFT${hash.replace(/[?]/g, "\\?")}$`));
    await expect(page.getByText(/conversation in this (route|link) is unavailable/i)).toBeVisible();

    await page.goto("/?view=users&keep=1#unchanged");
    await expect(page).toHaveURL(/\/?view=users&keep=1#unchanged$/);
    await expect(page.locator("[data-route-state='unavailable']")).toBeVisible();
    expect(generatedAnswers).toBe(0);
  });

  test("supports route links, browser history, active state, and drawer focus restoration", async ({ page }) => {
    await page.setViewportSize({ width: 900, height: 800 });
    await installApiFixtures(page);
    await page.goto("/research?keep=1");

    const toggle = page.getByRole("button", { name: "Open navigation" });
    await toggle.click();
    await expect(page.getByRole("dialog", { name: "Open navigation" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Close navigation" })).toBeFocused();
    await page.getByRole("link", { name: "Search", exact: true }).click();
    await expect(page).toHaveURL(/\/search$/);

    await page.getByRole("button", { name: "Open navigation" }).click();
    await page.getByRole("link", { name: "Documents", exact: true }).click();
    await expect(page).toHaveURL(/\/documents$/);
    await page.goBack();
    await expect(page).toHaveURL(/\/search$/);

    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(page.getByRole("link", { name: "Search", exact: true })).toHaveAttribute("aria-current", "page");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Open navigation" })).toBeFocused();
  });
});
