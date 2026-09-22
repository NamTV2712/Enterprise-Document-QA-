import { expect, test } from "@playwright/test";

import { installApiFixtures } from "./fixtures";

/**
 * UI-005 Documents composition. The reference is
 * docs/ui-references/documents-ui-reference-dark-v1.png (1586x992): page header,
 * a search row, a filter row, four statistic cards, one table card with inline
 * sort and rows-per-page controls, and the detail rail on the right.
 *
 * Two reference elements are deliberately absent rather than faked:
 * - the "Filing Type" filter and column, because API-003 publishes the form
 *   type as unknown while no stored artifact records one;
 * - the header's Import / Manage Sources / overflow actions and the sidebar
 *   storage meter, because none of them is a real capability of this build.
 *
 * Deterministic fixture API only; no provider or real corpus is reached.
 */

const REFERENCE_VIEWPORT = { width: 1586, height: 992 } as const;

const RECEIPT_VIEWPORTS = [
  { name: "1586x992", width: 1586, height: 992 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1280x856", width: 1280, height: 856 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "390x844", width: 390, height: 844 },
] as const;

/** Short viewport: the table card must still page instead of collapsing. */
const SHORT_VIEWPORT = { name: "1440x700", width: 1440, height: 700 } as const;

type Page = import("@playwright/test").Page;

async function openDocuments(page: Page) {
  await page.goto("/documents");
  await expect(page.getByRole("main", { name: "Research workspace" })).toHaveAttribute("data-route-id", "documents");
  await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Documents (12)" })).toBeVisible();
}

/** The Documents panel root, so shell chrome cannot satisfy an assertion. */
function panel(page: Page) {
  return page.locator('section[aria-labelledby="document-explorer-title"]');
}

/** One statistic card by its label. */
function statCard(page: Page, label: string) {
  return panel(page).locator(".console-stat").filter({ hasText: label });
}

/** The paging footer, which is the only range label with pagination controls. */
function pagingFooter(page: Page) {
  return panel(page).locator(".console-card__footer");
}

test.describe("UI-005 documents workspace", () => {
  test("reports catalog facts from the API-003 routes and never invents a form type", async ({ page }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page, { catalog: true });
    await openDocuments(page);

    // Totals come from /documents/stats, not from the current page of rows.
    await expect(statCard(page, "Total Documents")).toContainText("12");
    await expect(statCard(page, "Companies")).toContainText("8");
    await expect(statCard(page, "Total Chunks")).toContainText("22,538");
    await expect(statCard(page, "Total Documents")).toContainText("Filing years 2024–2025");

    // The form type is published as unknown with its reason, and the panel
    // neither names a form type nor ships a filter for one.
    await expect(statCard(page, "Filing Type")).toContainText("Unknown");
    await expect(statCard(page, "Filing Type")).toContainText("Stored filing artifacts record no per-filing form type.");
    expect(await panel(page).innerText()).not.toContain("10-K");

    // Reference actions that would be dead controls are absent.
    for (const fakeAction of ["Import Documents", "Manage Sources"]) {
      await expect(page.getByRole("button", { name: fakeAction })).toHaveCount(0);
    }
  });

  test("offers the recorded facet dimensions with counts that match the results they select", async ({ page }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page, { catalog: true });
    await openDocuments(page);

    // Company facet: AAPL has two filings in the fixture catalog.
    await page.getByRole("button", { name: "Company / Ticker" }).click();
    await expect(page.getByRole("option", { name: "Apple Inc. (AAPL) (2)" })).toBeVisible();
    await page.getByRole("option", { name: "Apple Inc. (AAPL) (2)" }).click();
    await expect(page.getByRole("heading", { name: "Documents (2)" })).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(2);

    // API-003's basis: the year facet now counts the applied company filter,
    // so each remaining year carries its own real count.
    await page.getByRole("button", { name: "Year" }).click();
    await expect(page.getByRole("option", { name: "2024 (1)" })).toBeVisible();
    await expect(page.getByRole("option", { name: "2025 (1)" })).toBeVisible();
    await page.getByRole("option", { name: "2025 (1)" }).click();
    await expect(page.getByRole("heading", { name: "Documents (1)" })).toBeVisible();
    await expect(page.locator("tbody tr")).toContainText("2025-10-31");

    // Clearing every filter restores the whole catalog.
    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(page.getByRole("heading", { name: "Documents (12)" })).toBeVisible();
  });

  test("sorts and pages the catalog through the query, not through the loaded rows", async ({ page }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page, { catalog: true });
    await openDocuments(page);

    // Default: newest filing first, ten rows per page.
    await expect(page.locator("tbody tr")).toHaveCount(10);
    await expect(pagingFooter(page)).toContainText("Showing 1–10 of 12 documents");
    await expect(page.locator("tbody tr").first()).toContainText("AAPL");
    await expect(page.locator("tbody tr").first()).toContainText("2025-10-31");

    await page.getByRole("button", { name: "Sort by" }).click();
    await page.getByRole("option", { name: "Filing date (oldest)" }).click();
    // 2024-01-26 is the oldest filing date in the fixture catalog.
    await expect(page.locator("tbody tr").first()).toContainText("TSLA");
    await expect(page.locator("tbody tr").first()).toContainText("2024-01-26");

    await page.getByRole("button", { name: "Sort by" }).click();
    await page.getByRole("option", { name: "Chunks (most)" }).click();
    await expect(page.locator("tbody tr").first()).toContainText("AMZN");

    await page.getByRole("button", { name: "Rows per page" }).click();
    await page.getByRole("option", { name: "20 per page" }).click();
    await expect(page.locator("tbody tr")).toHaveCount(12);
    await expect(pagingFooter(page)).toContainText("Showing 1–12 of 12 documents");

    // Page size is honoured by the pager: 10 per page means two pages.
    await page.getByRole("button", { name: "Rows per page" }).click();
    await page.getByRole("option", { name: "10 per page" }).click();
    await page.getByRole("button", { name: "Next page" }).click();
    await expect(pagingFooter(page)).toContainText("Showing 11–12 of 12 documents");
  });

  test("browses read-only: no conversation or repository mutation while working the list", async ({ page }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page, { catalog: true });
    await openDocuments(page);

    const mutations: string[] = [];
    page.on("request", (request) => {
      const method = request.method();
      if (method === "GET" || method === "OPTIONS") return;
      mutations.push(`${method} ${new URL(request.url()).pathname}`);
    });

    await page.getByRole("textbox", { name: "Search filings" }).fill("MSFT");
    await expect(page.getByRole("heading", { name: "Documents (2)" })).toBeVisible();
    await page.getByRole("button", { name: "Year" }).click();
    await page.getByRole("option", { name: "2024 (1)" }).click();
    await expect(page.getByRole("heading", { name: "Documents (1)" })).toBeVisible();
    await page.getByRole("button", { name: "Sort by" }).click();
    await page.getByRole("option", { name: "Ticker (A-Z)" }).click();
    await page.locator("tbody tr").first().click();
    // The rail switches from its empty state to the selected filing's identity.
    await expect(page.getByRole("heading", { name: "Microsoft Corporation (MSFT)" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Document Details" })).toHaveCount(0);
    for (const tab of ["Sections (3)", "Representations", "Metadata"]) {
      await page.getByRole("tab", { name: tab }).click();
    }

    // The detail rail repeats the catalog's unknown form type.
    await expect(panel(page).locator("dt", { hasText: "Filing Type" })).toBeVisible();
    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(page.getByRole("heading", { name: "Microsoft Corporation (MSFT)" })).toBeVisible();

    expect(mutations).toEqual([]);
  });

  test("captures the documents composition at every receipt viewport", async ({ page, browserName }) => {
    for (const viewport of [...RECEIPT_VIEWPORTS, SHORT_VIEWPORT]) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await installApiFixtures(page, { catalog: true });
      await openDocuments(page);

      await expect(page.getByText("Total Chunks")).toBeVisible();
      await expect(page.getByRole("heading", { name: "Document Details" })).toBeVisible();

      // The console view-entry animation starts at opacity 0, so a receipt
      // taken too early would be blank even though the assertions pass.
      await expect
        .poll(
          () => panel(page).evaluate((node) => Number(getComputedStyle(node.firstElementChild as Element).opacity)),
          { message: `panel painted at ${viewport.name}` },
        )
        .toBeGreaterThan(0.99);

      if (viewport.width >= 1280) {
        const table = await page.locator(".console-layout__main").boundingBox();
        const rail = await page.locator(".console-layout__aside").boundingBox();
        expect(table, `table column at ${viewport.name}`).not.toBeNull();
        expect(rail, `detail rail at ${viewport.name}`).not.toBeNull();
        // The reference puts the detail rail beside the table, not below it.
        expect(rail!.x, `rail beside table at ${viewport.name}`).toBeGreaterThan(table!.x);
      }

      await page.screenshot({
        path: `test-results/ui-005/documents-${viewport.name}-${browserName}.png`,
        fullPage: false,
        animations: "disabled",
      });

      const overflow = await page.evaluate(() => ({
        body: document.body.scrollWidth - document.body.clientWidth,
        root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      }));
      expect(overflow.body, `body overflow at ${viewport.name}`).toBeLessThanOrEqual(0);
      expect(overflow.root, `root overflow at ${viewport.name}`).toBeLessThanOrEqual(0);
    }
  });
});
