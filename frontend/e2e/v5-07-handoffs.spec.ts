import { expect, test } from "@playwright/test";
import {
  askQuestion,
  createCollectionsFixtureState,
  installApiFixtures,
  RECONCILIATION_NET_SALES_ANSWER,
  RECONCILIATION_SOURCES,
} from "./fixtures";

test.describe("V5-07 analyst route handoffs", () => {
  test("keeps the Documents catalog mounted while the shared Document pane is open", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    await page.goto("/");

    await page.getByRole("link", { name: "Documents", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
    await page.getByText("Apple Inc. (AAPL)", { exact: true }).first().click();
    const opener = page.locator("#document-workspace-AAPL-fixture");
    await expect(opener).toBeVisible();
    await opener.click();

    await expect(page.locator(".workbench-layout__content[data-workbench-context-kind='document']")).toBeVisible();
    await expect(page.locator("[data-workbench-route-origin='catalog']")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
    await expect(page.locator(".document-workspace")).toBeVisible();

    await page.getByRole("button", { name: "Back to Documents", exact: true }).click();
    await expect(opener).toBeFocused();
  });

  test("preserves Search result identity, Save Evidence, and return focus", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page, { collections: createCollectionsFixtureState() });
    await page.goto("/");

    await page.getByRole("link", { name: "Search", exact: true }).click();
    await page.getByLabel("Search Query").fill("What was Apple's total revenue in 2024?");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByText("Total revenue was reported in fiscal 2024.").first()).toBeVisible();

    const result = page.locator("article.console-result").filter({ hasText: "Total revenue was reported in fiscal 2024." });
    const opener = result.getByRole("button", { name: "Open document workspace", exact: true });
    await expect(opener).toBeVisible();
    await opener.click();
    await expect(page.locator("[data-workbench-route-origin='search']")).toBeVisible();
    await expect(page.getByText("Search result context", { exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: "Back to Search", exact: true }).click();
    await expect(opener).toBeFocused();

    // The ranked list has one save action per result, so the flow addresses
    // the top card it opened rather than every save button on the page. Saving
    // now names a typed workspace collection instead of writing silently.
    await result.getByRole("button", { name: "Save evidence" }).click();
    const target = page.getByRole("dialog", { name: "Save evidence to a collection" });
    await expect(target).toBeVisible();
    await target.getByLabel("Or create a new collection").fill("Search evidence");
    await target.getByRole("button", { name: "Create and add" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Added to the collection" })).toBeVisible();
  });

  test("uses a typed Retrieval Lab document target and preserves the analyst action", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page, { collections: createCollectionsFixtureState() });
    await page.goto("/");

    await page.getByRole("link", { name: "Retrieval Lab", exact: true }).click();
    await page.getByRole("button", { name: "Run retrieval", exact: true }).click();
    await expect(page.getByTestId("retrieval-analyst-summary")).toBeVisible();

    const opener = page.locator("#retrieval-document-workspace-AAPL_fixture_revenue_0");
    await opener.click();
    await expect(page.locator("[data-workbench-route-origin='retrieval']")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Apple Inc\. \(AAPL\) · 2025-10-31/ })).toBeVisible();
    await page.getByRole("button", { name: "Back to Retrieval", exact: true }).click();
    await expect(opener).toBeFocused();

    // Every ranked row carries its own save action, so this flow saves the
    // candidate it opened rather than every save button on the page.
    await page.getByRole("row", { name: /AAPL 10-K, Financial Statements/ }).getByRole("button", { name: "Save evidence" }).click();
    const target = page.getByRole("dialog", { name: "Save evidence to a collection" });
    await expect(target).toBeVisible();
    await target.getByLabel("Or create a new collection").fill("Retrieval evidence");
    await target.getByRole("button", { name: "Create and add" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Added to the collection" })).toBeVisible();
  });

  test("returns Library saved evidence to its exact invoking action", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page, {
      collections: createCollectionsFixtureState(),
      streamAnswers: [RECONCILIATION_NET_SALES_ANSWER],
      streamSources: [RECONCILIATION_SOURCES],
    });
    await page.goto("/");

    // The conversation surfaces still keep their on-device evidence library,
    // which is where this handoff belongs.
    await page.getByRole("link", { name: "Research", exact: true }).click();
    await askQuestion(page, "What were Apple's total net sales in fiscal year 2025?");
    await expect(page.getByText(RECONCILIATION_NET_SALES_ANSWER.split("\n")[0], { exact: false }).first()).toBeVisible();
    await page.getByRole("button", { name: "Open 2 sources", exact: true }).click();
    // The conversation surface keeps its own on-device evidence save; the
    // library tab is where that handoff returns to.
    await page.getByRole("button", { name: "Save evidence", exact: true }).first().click();

    await page.getByRole("link", { name: /Collections/ }).click();
    await expect(page.getByRole("heading", { name: "Collections", exact: true })).toBeVisible();
    await page.getByRole("tab", { name: "Conversations", exact: true }).click();
    await page.getByRole("button", { name: "Research evidence · 1", exact: true }).click();
    const evidenceOpener = page.locator(".library-evidence-item__open").first();
    await expect(evidenceOpener).toBeVisible();
    const evidenceOpenerId = await evidenceOpener.getAttribute("id");
    expect(evidenceOpenerId).toBeTruthy();
    await evidenceOpener.click();

    await expect(page.locator("[data-workbench-region='sources']")).toBeVisible();
    await page.getByRole("button", { name: "Close evidence inspector", exact: true }).click();
    await expect(page.locator(`#${evidenceOpenerId}`)).toBeFocused();
  });
});
