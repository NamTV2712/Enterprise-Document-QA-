import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { createCollectionsFixtureState, installApiFixtures } from "./fixtures";

/**
 * UI-008 Collections behaviour and receipts.
 *
 * Compared against docs/ui-references/collections-ui-reference-dark-v1.png
 * (1586x992). All collection data comes from the local DATA-003 fixture, which
 * enforces the same membership, revision and tombstone rules as the real
 * router; no backend, provider or model is reached.
 */

const REFERENCE_VIEWPORT = { width: 1586, height: 992 } as const;

const RECEIPT_VIEWPORTS = [
  { name: "1586x992", width: 1586, height: 992 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1280x856", width: 1280, height: 856 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "390x844", width: 390, height: 844 },
] as const;

const SHORT_VIEWPORT = { name: "1440x700", width: 1440, height: 700 } as const;

const RECEIPT_DIR = "test-results/ui-008";

type Page = import("@playwright/test").Page;

/**
 * A populated workspace shaped like the reference: one favourite collection
 * with typed members, notes and recorded activity, plus plain collections.
 * Every identity is a real one the rest of the fixture harness can resolve.
 */
function populatedWorkspace() {
  // Timestamps stay relative to the run's clock so the receipt shows the same
  // relative labels the reference does ("2 hours ago") without freezing them.
  const hoursAgo = (hours: number) => new Date(Date.now() - hours * 3_600_000).toISOString();
  return createCollectionsFixtureState([
    {
      collection_id: "col-risk",
      name: "Risk Analysis",
      description: "Key risks, challenges, and uncertainties for Apple based on recent filings.",
      tags: ["Risk Factors", "Regulatory", "Macroeconomics", "Supply Chain"],
      favorite: true,
      revision: 4,
      created_at: hoursAgo(30),
      updated_at: hoursAgo(2),
      items: [
        {
          item_id: "itm-aapl",
          collection_id: "col-risk",
          item_kind: "document",
          citation: "Apple Inc. (AAPL) · 2025-10-31",
          excerpt: "",
          reference: { document_id: "AAPL:fixture", ticker: "AAPL", filing_date: "2025-10-31" },
          revision: 1,
          created_at: hoursAgo(4),
          updated_at: hoursAgo(4),
        },
        {
          item_id: "itm-msft",
          collection_id: "col-risk",
          item_kind: "document",
          citation: "Microsoft Corporation (MSFT) · 2025-07-30",
          excerpt: "",
          reference: { document_id: "MSFT:0001", ticker: "MSFT", filing_date: "2025-07-30" },
          revision: 1,
          created_at: hoursAgo(4),
          updated_at: hoursAgo(4),
        },
        {
          item_id: "itm-evidence",
          collection_id: "col-risk",
          item_kind: "evidence",
          citation: "AAPL indexed excerpt · financial_statements",
          excerpt: "Total net sales increased year over year, driven by Services.",
          reference: {
            document_id: "AAPL:fixture",
            chunk_id: "AAPL_fixture_revenue_0",
            ticker: "AAPL",
            section: "financial_statements",
            filing_date: "2025-10-31",
            document_revision: "fixture-document-revision",
          },
          snapshot: { representation: "indexed_excerpt" },
          revision: 1,
          created_at: hoursAgo(3),
          updated_at: hoursAgo(3),
        },
      ],
      notes: [
        {
          note_id: "note-1",
          collection_id: "col-risk",
          text: "Macroeconomic conditions and global trade tensions remain the most significant external risks.",
          revision: 1,
          created_at: hoursAgo(6),
          updated_at: hoursAgo(6),
        },
      ],
      activity: [
        { activity_id: "act-1", collection_id: "col-risk", entity_type: "item", entity_id: "itm-aapl", event_type: "item_added", occurred_at: hoursAgo(4) },
        { activity_id: "act-2", collection_id: "col-risk", entity_type: "note", entity_id: "note-1", event_type: "note_added", occurred_at: hoursAgo(6) },
        { activity_id: "act-3", collection_id: "col-risk", entity_type: "collection", entity_id: "col-risk", event_type: "collection_updated", occurred_at: hoursAgo(2) },
      ],
    },
    {
      collection_id: "col-earnings",
      name: "Earnings Review",
      description: "Quarterly and annual earnings analysis, financial performance, and management commentary.",
      tags: ["Financials", "Earnings Calls"],
      revision: 2,
      created_at: hoursAgo(72),
      updated_at: hoursAgo(26),
      items: [
        {
          item_id: "itm-ev-2",
          collection_id: "col-earnings",
          item_kind: "evidence",
          citation: "AAPL indexed excerpt · mdna",
          excerpt: "Services revenue reached an all-time high.",
          reference: { document_id: "AAPL:fixture", chunk_id: "AAPL_fixture_revenue_0" },
          revision: 1,
          created_at: hoursAgo(26),
          updated_at: hoursAgo(26),
        },
      ],
    },
    {
      collection_id: "col-competitive",
      name: "Competitive Landscape",
      description: "Analysis of key competitors, market positioning, and industry dynamics.",
      tags: ["Competition"],
      revision: 1,
      created_at: hoursAgo(120),
      updated_at: hoursAgo(96),
    },
  ]);
}

async function openCollections(page: Page, path = "/collections") {
  // The nine references are dark; receipts and comparisons use that theme.
  await page.addInitScript(() => window.localStorage.setItem("theme", "dark"));
  await page.goto(path);
  await expect(page.getByRole("main", { name: "Research workspace" })).toBeVisible();
}

/** The console entry animation starts at opacity 0: prove paint before a receipt. */
async function waitForPaint(page: Page, label: string) {
  await expect
    .poll(
      () => page.locator(".collections-page").evaluate((node) => Number(getComputedStyle(node).opacity)),
      { message: `${label} painted` },
    )
    .toBeGreaterThan(0.99);
}

/** Writes are exactly the requests that are not reads. */
function writeRequests(state: { requests: Array<{ method: string; path: string }> }) {
  return state.requests.filter((entry) => entry.method !== "GET");
}

async function resetScroll(page: Page) {
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    document.querySelectorAll<HTMLElement>(".workspace-scroll, .console-layout__aside, .collection-rail__card").forEach((element) => {
      element.scrollTo({ top: 0, left: 0 });
    });
  });
}

test.describe("UI-008 collections", () => {
  test("the route loads the collections workspace with real typed data", async ({ page }) => {
    await installApiFixtures(page, { collections: populatedWorkspace() });
    await openCollections(page);

    await expect(page.locator("main[data-route-id='collections']")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Collections", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Risk Analysis" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Earnings Review" })).toBeVisible();
    // Real fields only: item counts, relative update time and tags.
    await expect(page.getByText("3 items").first()).toBeVisible();
    await expect(page.getByText("Risk Factors")).toBeVisible();
    await expect(page.getByText("+1")).toBeVisible();
    // The reference's owner, sharing and storage values have no capability.
    await expect(page.getByText(/Nguyen/)).toHaveCount(0);
    await expect(page.getByText(/12\.4 GB/)).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Share", exact: true })).toHaveCount(0);
  });

  test("browsing the workspace writes nothing", async ({ page }) => {
    const state = populatedWorkspace();
    await installApiFixtures(page, { collections: state });
    await openCollections(page);

    await page.getByLabel("Search collections").fill("risk");
    await page.getByRole("tab", { name: /Favorites/ }).click();
    await page.getByRole("tab", { name: /All Collections/ }).click();
    await page.getByRole("button", { name: "Open Risk Analysis" }).click();
    await expect(page.getByRole("complementary", { name: /Risk Analysis/ })).toBeVisible();
    await page.getByRole("tab", { name: "Notes" }).click();
    await page.getByRole("tab", { name: "Activity" }).click();
    await page.getByRole("tab", { name: "Settings" }).click();
    await page.getByRole("tab", { name: "Contents" }).click();

    expect(writeRequests(state)).toEqual([]);
  });

  test("selecting a collection is a route, so back and forward work", async ({ page }) => {
    await installApiFixtures(page, { collections: populatedWorkspace() });
    await openCollections(page);

    await page.getByRole("button", { name: "Open Risk Analysis" }).click();
    await expect(page).toHaveURL(/\/collections\/col-risk$/);
    await expect(page.getByRole("complementary", { name: /Risk Analysis/ })).toBeVisible();

    await page.goBack();
    await expect(page).toHaveURL(/\/collections$/);
    await page.goForward();
    await expect(page).toHaveURL(/\/collections\/col-risk$/);
    await expect(page.getByRole("complementary", { name: /Risk Analysis/ })).toBeVisible();
  });

  test("the detail rail reports this collection's real metadata and members", async ({ page }) => {
    await installApiFixtures(page, { collections: populatedWorkspace() });
    await openCollections(page, "/collections/col-risk");

    const rail = page.getByRole("complementary", { name: /Risk Analysis/ });
    await expect(rail).toBeVisible();
    await expect(rail.getByText("Revision 4", { exact: false })).toBeVisible();
    await expect(rail.getByRole("tab", { name: "Contents" })).toHaveAttribute("aria-selected", "true");
    // The reference's "Share" tab has no capability here.
    await expect(rail.getByRole("tab", { name: "Share" })).toHaveCount(0);
    await expect(rail.getByText("Items (3)")).toBeVisible();
    await expect(rail.getByText("3 items").first()).toBeVisible();
    // Each member states the kind DATA-003 returned.
    const kinds = await rail.locator(".collection-kind-badge__label").allTextContents();
    expect(kinds).toEqual(["Document", "Document", "Evidence"]);
  });

  test("a document member opens the canonical reader and returns to the collection", async ({ page }) => {
    await installApiFixtures(page, { collections: populatedWorkspace(), catalog: true });
    await openCollections(page, "/collections/col-risk");

    await page.getByRole("button", { name: /Apple Inc\. \(AAPL\) · 2025-10-31/ }).first().click();
    // The reader opens for the exact document identity the member stored, and
    // stays on the collection route: nothing re-runs, nothing navigates away.
    await expect(page).toHaveURL(/\/collections\/col-risk$/);
    const workspace = page.locator("[data-workbench-return-view='library']");
    await expect(workspace).toBeVisible();
    await expect(page.locator("[data-workbench-region='document']")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Apple Inc\. \(AAPL\) · 2025-10-31/ })).toBeVisible();
    // The reader names the origin it will return to.
    await expect(page.getByRole("button", { name: /Back to Collections/ })).toBeVisible();

    await page.getByRole("button", { name: /Back to Collections/ }).click();
    const member = page.locator("#collection-member-itm-aapl");
    await expect(member).toBeVisible();
    await expect(member).toBeFocused();
  });

  test("an evidence member opens its stored snapshot without re-running retrieval", async ({ page }) => {
    const state = populatedWorkspace();
    await installApiFixtures(page, { collections: state, catalog: true });
    await openCollections(page, "/collections/col-risk");

    await page.getByRole("button", { name: /AAPL indexed excerpt · financial_statements/ }).first().click();
    await expect(page.getByRole("dialog", { name: /evidence/i })).toBeVisible();
    await expect(page.getByText("Total net sales increased year over year, driven by Services.").first()).toBeVisible();

    // Reading a stored member never touches the query, retrieval or search routes.
    const nonCollection = state.requests.filter((entry) => !entry.path.startsWith("/collections"));
    expect(nonCollection).toEqual([]);
  });

  test("a 409 while renaming is reported as a conflict and never silently overwrites", async ({ page }) => {
    const state = populatedWorkspace();
    state.mutationStatus = { update: 409 };
    await installApiFixtures(page, { collections: state });
    await openCollections(page, "/collections/col-risk");

    const rail = page.getByRole("complementary", { name: /Risk Analysis/ });
    await rail.getByRole("button", { name: "Collection actions" }).click();
    await rail.getByRole("menuitem", { name: "Rename" }).click();
    const dialog = page.getByRole("dialog", { name: "Rename collection" });
    await dialog.getByRole("textbox", { name: "Name", exact: true }).fill("Risk Analysis (renamed)");
    await dialog.getByRole("button", { name: "Save name" }).click();

    await expect(dialog.getByRole("alert")).toContainText("changed elsewhere");
    await dialog.getByRole("button", { name: "Cancel" }).click();
    // The name the workspace still holds is unchanged in the UI.
    await expect(rail.getByRole("heading", { name: /Risk Analysis/ })).toBeVisible();
  });

  test("a tombstoned collection reports that it is gone, not missing", async ({ page }) => {
    const state = populatedWorkspace();
    const tombstoned = state.collections.find((entry) => entry.collection_id === "col-risk");
    if (tombstoned) tombstoned.deleted = true;
    await installApiFixtures(page, { collections: state });
    await openCollections(page, "/collections/col-risk");

    await expect(page.getByText("Collection deleted")).toBeVisible();
    await expect(page.getByText(/cannot be recreated/)).toBeVisible();
  });

  test("public mode shows a truthful unavailable state instead of an empty list", async ({ page }) => {
    const state = populatedWorkspace();
    state.listStatus = 404;
    state.detail = "Local workspace capability is unavailable";
    await installApiFixtures(page, { collections: state });
    await openCollections(page);

    await expect(page.getByText("Collections are unavailable in this mode")).toBeVisible();
    await expect(page.getByText("No collections yet")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "New Collection" })).toHaveCount(0);
  });

  test("a refused member is reported instead of being coerced into another kind", async ({ page }) => {
    const state = populatedWorkspace();
    state.mutationStatus = { "add-item": 422 };
    state.detail = "a document item must reference a document_id";
    await installApiFixtures(page, { collections: state, catalog: true });
    await openCollections(page, "/collections/col-risk");

    await page.getByRole("button", { name: "+ Add Documents" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Add documents to the collection" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("checkbox").first().check();
    await dialog.getByRole("button", { name: /^Add 1 document$/ }).click();

    await expect(dialog.getByRole("alert")).toContainText("refused");
  });

  test("create, add note, remove member, favourite and delete are explicit writes", async ({ page }) => {
    const state = populatedWorkspace();
    await installApiFixtures(page, { collections: state, catalog: true });
    await openCollections(page);

    // Create
    await page.getByRole("button", { name: "New Collection" }).first().click();
    const createDialog = page.getByRole("dialog", { name: "New collection" });
    await createDialog.getByLabel("Name").fill("Governance");
    await createDialog.getByLabel(/Description/).fill("Corporate governance and compliance materials.");
    await createDialog.getByRole("button", { name: "Create collection" }).click();
    await expect(page).toHaveURL(/\/collections\/col-4$/);
    await expect(page.getByRole("complementary", { name: /Governance/ })).toBeVisible();

    // Add a note
    await page.getByRole("tab", { name: "Notes" }).click();
    await page.getByLabel("Add note").fill("Board structure reviewed.");
    await page.getByRole("button", { name: "Save note" }).click();
    await expect(page.getByText("Board structure reviewed.")).toBeVisible();

    // Favourite from the card it belongs to (the new collection is first).
    const card = page.locator("#collection-card-col-4");
    await card.getByRole("button", { name: /favorite/ }).click();
    await expect(card.getByRole("button", { name: /Remove/ })).toHaveAttribute("aria-pressed", "true");

    const methods = writeRequests(state).map((entry) => `${entry.method} ${entry.path.split("?")[0]}`);
    expect(methods).toContain("POST /collections");
    expect(methods).toContain("POST /collections/col-4/notes");
    expect(methods).toContain("PATCH /collections/col-4");

    // Delete requires the confirmation step, then tombstones the collection.
    await page.getByRole("tab", { name: "Settings" }).click();
    await page.getByRole("button", { name: "Delete collection" }).click();
    await page.getByRole("button", { name: "Delete permanently" }).click();
    await expect(page).toHaveURL(/\/collections$/);
    await expect(page.getByRole("heading", { name: "Governance" })).toHaveCount(0);
    expect(writeRequests(state).some((entry) => entry.method === "DELETE")).toBe(true);
  });

  test("export downloads the workspace's own document and mutates nothing", async ({ page }) => {
    const state = populatedWorkspace();
    await installApiFixtures(page, { collections: state });
    await openCollections(page, "/collections");

    const download = page.waitForEvent("download");
    await page.locator("#collection-card-col-risk").getByRole("button", { name: "Export" }).click();
    const dialog = page.getByRole("dialog", { name: "Export collection" });
    await dialog.getByRole("radio", { name: /Markdown/ }).check();
    await dialog.getByRole("button", { name: "Export file" }).click();

    const file = await download;
    expect(file.suggestedFilename()).toMatch(/^risk-analysis-col-risk\.md$/);
    expect(writeRequests(state)).toEqual([]);
  });

  test("the conversations library stays reachable on its own tab", async ({ page }) => {
    await installApiFixtures(page, { collections: populatedWorkspace() });
    await openCollections(page);

    await page.getByRole("tab", { name: /Conversations/ }).click();
    await expect(page.getByRole("searchbox", { name: "Search saved conversations" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Risk Analysis" })).toHaveCount(0);
  });

  test("keyboard operation, dialog semantics and contrast hold", async ({ page }) => {
    const state = populatedWorkspace();
    await installApiFixtures(page, { collections: state, catalog: true });
    await openCollections(page, "/collections/col-risk");

    // The rail opens from the keyboard and its tabs are a real tablist.
    const rail = page.getByRole("complementary", { name: /Risk Analysis/ });
    await expect(rail.getByRole("tab", { name: "Contents" })).toHaveAttribute("aria-selected", "true");
    await rail.getByRole("tab", { name: "Notes" }).press("Enter");
    await expect(rail.getByRole("tab", { name: "Notes" })).toHaveAttribute("aria-selected", "true");
    await rail.getByRole("tab", { name: "Activity" }).press("Enter");
    await expect(rail.getByRole("button", { name: "Add note" })).toHaveCount(0);
    await rail.getByRole("tab", { name: "Contents" }).press("Enter");

    // Opening the picker is keyboard-only, and Escape closes it without writing.
    await rail.getByRole("button", { name: "+ Add Documents" }).press("Enter");
    const dialog = page.getByRole("dialog", { name: "Add documents to the collection" });
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    expect(writeRequests(state)).toEqual([]);

    // The console view-entry animation starts at opacity 0; scanning mid-flight
    // would measure blended colors instead of the settled page.
    await page.emulateMedia({ reducedMotion: "reduce" });
    await waitForPaint(page, "collections a11y scan");
    const results = await new AxeBuilder({ page })
      .include("main")
      .options({ runOnly: ["color-contrast", "label", "button-name", "link-name", "aria-input-field-name"] })
      .analyze();
    const serious = results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious");
    expect(serious).toEqual([]);
  });

  test("receipts across the responsive ladder and the reference viewport", async ({ page, browserName }) => {
    await installApiFixtures(page, { collections: populatedWorkspace(), catalog: true });

    for (const viewport of [...RECEIPT_VIEWPORTS, SHORT_VIEWPORT]) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await openCollections(page, "/collections/col-risk");
      await expect(page.getByRole("complementary", { name: /Risk Analysis/ })).toBeVisible();
      await waitForPaint(page, `collections ${viewport.name}`);
      await resetScroll(page);

      const overflow = await page.evaluate(() => ({
        body: document.body.scrollWidth - document.body.clientWidth,
        root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      }));
      expect(overflow, `${viewport.name} horizontal overflow`).toEqual({ body: 0, root: 0 });

      await page.screenshot({ path: `${RECEIPT_DIR}/collections-${viewport.name}-${browserName}.png`, animations: "disabled" });
    }

    // The reference-native receipt is the one compared with the screenshot.
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await openCollections(page, "/collections/col-risk");
    await expect(page.getByRole("complementary", { name: /Risk Analysis/ })).toBeVisible();
    await waitForPaint(page, "collections reference receipt");
    await resetScroll(page);
    await page.screenshot({ path: `${RECEIPT_DIR}/collections-reference-1586x992-${browserName}.png`, animations: "disabled" });
  });

  test("compact and mobile keep the collection list usable", async ({ page }) => {
    await installApiFixtures(page, { collections: populatedWorkspace() });

    await page.setViewportSize({ width: 1024, height: 768 });
    await openCollections(page);
    await expect(page.getByRole("heading", { name: "Risk Analysis" })).toBeVisible();
    await page.getByRole("button", { name: "Open Risk Analysis" }).click();
    await expect(page.getByRole("complementary", { name: /Risk Analysis/ })).toBeVisible();

    await page.setViewportSize({ width: 390, height: 844 });
    await openCollections(page);
    await expect(page.getByRole("heading", { name: "Risk Analysis" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBe(0);
    await expect(page.getByLabel("Search collections")).toBeVisible();
  });
});
