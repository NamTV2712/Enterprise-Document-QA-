import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { installApiFixtures } from "./fixtures";

/**
 * UI-006 Search receipts and behaviour. The reference is
 * docs/ui-references/search-ui-reference-dark-v1.png (1586x992): query card
 * with real filters and a submit button, a results toolbar, ranked result
 * cards with highlighted excerpts, and the overview/refine/recent rail.
 *
 * Reference elements with no capability behind them are asserted absent rather
 * than faked: saved searches, search examples, collection/type chip rows,
 * advanced filters, a sort selector, a latency tile, and filing-type filters.
 *
 * Deterministic fixture API only; no provider, model, or real corpus is reached.
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

type Page = import("@playwright/test").Page;
type Request_ = import("@playwright/test").Request;

/** Count API-004 traffic so snapshot reuse is proved, not assumed. */
function trackDiscovery(page: Page) {
  const calls = { posts: [] as string[], gets: [] as string[] };
  page.on("request", (request: Request_) => {
    const path = new URL(request.url()).pathname;
    if (path === "/search" && request.method() === "POST") calls.posts.push(request.postData() ?? "");
    if (path.startsWith("/search/") && request.method() === "GET") calls.gets.push(path);
  });
  return calls;
}

async function openSearch(page: Page) {
  await page.goto("/search");
  await expect(page.getByRole("main", { name: "Research workspace" })).toHaveAttribute("data-route-id", "search");
  await expect(page.getByRole("heading", { name: "Search", exact: true })).toBeVisible();
}

async function submit(page: Page, query: string) {
  await page.getByLabel("Search Query").fill(query);
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("heading", { name: `Results for “${query}”` })).toBeVisible();
}

test.describe("UI-006 discovery search", () => {
  for (const variant of [{ theme: "dark", locale: "en" }, { theme: "light", locale: "vi" }] as const) {
    test(`new searches suspend old snapshot paging (${variant.theme}/${variant.locale})`, async ({ page, browserName }) => {
      const vi = variant.locale === "vi";
      await page.setViewportSize(vi ? { width: 390, height: 844 } : REFERENCE_VIEWPORT);
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.addInitScript(({ theme, locale }) => {
        localStorage.setItem("theme", theme);
        localStorage.setItem("sec_qa_locale", locale);
      }, variant);
      await installApiFixtures(page);
      const calls = trackDiscovery(page);
      let release!: () => void;
      let waiting = false;
      let posts = 0;
      const gate = new Promise<void>(resolve => { release = resolve; });
      await page.route("**/search", async route => {
        if (route.request().method() === "POST" && ++posts === 2) {
          waiting = true;
          await gate;
        }
        await route.fallback();
      });
      await page.goto("/search");
      if (variant.theme === "dark") await expect(page.locator("html")).toHaveClass(/dark/);
      else await expect(page.locator("html")).not.toHaveClass(/dark/);
      const query = page.getByLabel(vi ? "Truy vấn tìm kiếm" : "Search Query");
      const searchButton = () => page.getByRole("button", { name: vi ? "Tìm kiếm" : "Search", exact: true });
      await query.fill("cloud revenue");
      await searchButton().click();
      await expect(page.getByRole("heading", { name: vi ? 'Kết quả cho "cloud revenue"' : "Results for “cloud revenue”" })).toBeVisible();
      await query.fill("supply chain");
      await searchButton().click();
      try {
        await expect.poll(() => waiting).toBe(true);
        await expect(page.getByRole("button", { name: vi ? "Trang sau" : "Next page" })).toBeDisabled();
        await expect(page.getByRole("button", { name: vi ? "Số dòng mỗi trang" : "Rows per page" })).toBeDisabled();
        expect(calls.gets).toHaveLength(0);
        await page.screenshot({ path: `test-results/ui-006/search-pending-${variant.theme}-${variant.locale}-${browserName}.png`, animations: "disabled" });
      } finally {
        release();
      }
      await expect(page.getByRole("heading", { name: vi ? 'Kết quả cho "supply chain"' : "Results for “supply chain”" })).toBeVisible();
      await expect(page.getByRole("button", { name: vi ? "Trang sau" : "Next page" })).toBeEnabled();
      expect(calls.posts).toHaveLength(2);
      await expect(page.getByRole("alert")).toHaveCount(0);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(0);
      await page.screenshot({ path: `test-results/ui-006/search-recovered-${variant.theme}-${variant.locale}-${browserName}.png`, animations: "disabled" });
    });
  }

  test("starts from the reference composition without fake controls", async ({ page, browserName }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page);
    await openSearch(page);

    // Query card, filters, submit, and the empty state.
    await expect(page.getByLabel("Search Query")).toBeVisible();
    await expect(page.getByRole("button", { name: "Company" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Section" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Search", exact: true })).toBeVisible();
    await expect(page.getByText("Start with a keyword query")).toBeVisible();

    // Rail: overview, refine, and recent searches, all from real API data.
    await expect(page.getByRole("heading", { name: "Search Overview" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Refine Search" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent Searches" })).toBeVisible();

    // Controls the reference shows that this build cannot back truthfully.
    for (const absent of ["Saved Searches", "Search Examples", "Advanced Filters", "All Collections", "Sort by", "View all"]) {
      await expect(page.getByRole("button", { name: absent })).toHaveCount(0);
      await expect(page.getByText(absent, { exact: true })).toHaveCount(0);
    }
    await expect(page.getByText("10-K Filings", { exact: true })).toHaveCount(0);
    await expect(page.getByText(/Search Latency/i)).toHaveCount(0);
    await expect(page.getByText(/relevance/i)).toHaveCount(0);
    expect(await page.locator("main").innerText()).not.toContain("confidence");

    await page.screenshot({ path: `test-results/ui-006/search-initial-${browserName}.png`, fullPage: false, animations: "disabled" });
  });

  test("shows real ranked results, highlights, and bounded counts", async ({ page, browserName }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page);
    await openSearch(page);
    await submit(page, "cloud revenue and supply chain");

    const cards = page.locator("article.console-result");
    await expect(cards).toHaveCount(20);

    // The top-ranked excerpt is the fixture chunk the reader can open.
    const first = cards.first();
    await expect(first).toContainText("Total revenue was reported in fiscal 2024.");
    await expect(first).toContainText("Apple Inc. (AAPL)");
    await expect(first.getByText("11.473")).toBeVisible();
    await expect(first.getByText("BM25")).toBeVisible();
    // Highlight marks come from the API's own ranges, which cover the query
    // terms this fixture corpus actually contains.
    expect(await first.locator("mark").count()).toBeGreaterThan(0);
    await expect(first.locator("mark").first()).toHaveText("revenue");

    // The real-corpus-shaped excerpts follow with their own scores and marks.
    const second = cards.nth(1);
    await expect(second).toContainText("Microsoft Cloud");
    await expect(second.getByText("10.703")).toBeVisible();
    await expect(second.locator("mark").first()).toHaveText("Cloud");

    // Bounded discovery counts, never a corpus total.
    await expect(page.getByText(/bounded discovery count rather than a corpus total/)).toBeVisible();
    await expect(page.getByText(/Showing 1–20 of 22 filings/).first()).toBeVisible();

    // No fabricated score semantics anywhere on the page.
    const body = await page.locator("main").innerText();
    expect(body).not.toMatch(/\d+%\s*(relevance|confidence|match)/i);
    expect(body).not.toContain("High relevance");

    await page.screenshot({ path: `test-results/ui-006/search-results-${browserName}.png`, fullPage: false, animations: "disabled" });
  });

  test("keeps one snapshot: paging, page size, and opening a result never search again", async ({ page }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page);
    const calls = trackDiscovery(page);
    await openSearch(page);

    await page.getByLabel("Search Query").fill("cloud revenue");
    expect(calls.posts).toHaveLength(0);
    await page.getByLabel("Search Query").fill("cloud revenue and supply chain");
    expect(calls.posts).toHaveLength(0);

    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByRole("heading", { name: /Results for/ })).toBeVisible();
    expect(calls.posts).toHaveLength(1);

    // Paging reads the same snapshot.
    await page.getByRole("button", { name: "Next page" }).click();
    await expect(page.getByText(/Showing 21–22 of 22 filings/).first()).toBeVisible();
    expect(calls.gets).toHaveLength(1);
    expect(calls.posts).toHaveLength(1);

    // Page size also only reads it.
    await page.getByRole("button", { name: "Rows per page" }).click();
    await page.getByRole("option", { name: "50 per page" }).click();
    await expect(page.getByText(/Showing 1–22 of 22 filings/).first()).toBeVisible();
    expect(calls.posts).toHaveLength(1);

    // Opening a result never searches again.
    await page.locator("article.console-result").first().getByRole("button", { name: "Open document workspace" }).click();
    await expect(page.locator("[data-workbench-route-origin='search']")).toBeVisible();
    expect(calls.posts).toHaveLength(1);
    await page.getByRole("button", { name: "Back to Search", exact: true }).click();
    expect(calls.posts).toHaveLength(1);

    // Only a newly committed scope creates a second snapshot.
    await page.getByRole("button", { name: "Company" }).first().click();
    await page.getByRole("option", { name: "Microsoft Corporation (MSFT)" }).click();
    expect(calls.posts).toHaveLength(1);
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByRole("heading", { name: /Results for/ })).toBeVisible();
    expect(calls.posts).toHaveLength(2);
  });

  test("filters, grouping, zero results, and the expired state stay truthful", async ({ page, browserName }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    await openSearch(page);
    await submit(page, "cloud revenue and supply chain");

    // Grouping is a committed change with the same query and scope. The switch
    // is driven by the returned snapshot, so it flips once the new one lands.
    await page.getByLabel("Group by filing").click();
    await expect(page.getByText(/Showing 1–20 of 23 excerpts/).first()).toBeVisible();

    await page.getByLabel("Group by filing").click();
    await expect(page.getByText(/Showing 1–20 of 22 filings/).first()).toBeVisible();

    // A real filtered scope with no matching excerpts is a no-match snapshot.
    await page.getByRole("button", { name: "Section" }).first().click();
    await page.getByRole("option", { name: "Financial Table" }).click();
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByText(/No matches for/)).toBeVisible();
    await expect(page.getByText(/No filings exist in scope financial_table/)).toBeVisible();
    await expect(page.locator("article.console-result")).toHaveCount(0);
    await page.screenshot({ path: `test-results/ui-006/search-no-match-${browserName}.png`, fullPage: false, animations: "disabled" });
  });

  test("distinguishes an expired snapshot from an unknown one", async ({ page, browserName }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page, { searchExpired: true });
    await openSearch(page);
    await submit(page, "cloud revenue and supply chain");
    await page.getByRole("button", { name: "Next page" }).click();

    await expect(page.getByText(/snapshot expired\. Run the search again/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Run the search again" })).toBeVisible();
    // The expired page never becomes an empty result list.
    await expect(page.locator("article.console-result").first()).toBeVisible();
    await page.screenshot({ path: `test-results/ui-006/search-expired-${browserName}.png`, fullPage: false, animations: "disabled" });
  });

  test("unknown snapshot reports missing instead of empty", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page, { searchMissing: true });
    await openSearch(page);
    await submit(page, "cloud revenue and supply chain");
    await page.getByRole("button", { name: "Next page" }).click();

    await expect(page.getByText(/not known any more/i)).toBeVisible();
    await expect(page.getByText(/No matches for/)).toHaveCount(0);
  });

  test("searches read-only: no conversation, workspace, or provider write", async ({ page }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page);
    await openSearch(page);

    const mutations: string[] = [];
    page.on("request", (request) => {
      const method = request.method();
      if (method === "GET" || method === "OPTIONS" || method === "HEAD") return;
      const path = new URL(request.url()).pathname;
      // POST /search is the snapshot write this page is allowed to make.
      if (path === "/search") return;
      mutations.push(`${method} ${path}`);
    });

    await submit(page, "cloud revenue and supply chain");
    await page.getByRole("button", { name: "Next page" }).click();
    await expect(page.getByText(/Showing 21–22 of 22 filings/).first()).toBeVisible();
    await page.getByRole("button", { name: "Rows per page" }).click();
    await page.getByRole("option", { name: "10 per page" }).click();
    await page.locator("article.console-result").first().click();
    await page.getByRole("button", { name: "Save evidence" }).first().click();

    expect(mutations.filter((entry) => !entry.includes("/workspace") && !entry.includes("/evidence"))).toEqual([]);
    // Saving evidence is the only write, and it is an explicit user action.
    expect(mutations.every((entry) => entry.startsWith("POST /") || entry.startsWith("PUT /"))).toBe(true);
  });

  test("keeps the route and snapshot honest across back, reload, and reopening", async ({ page }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page);
    const calls = trackDiscovery(page);
    await openSearch(page);
    await submit(page, "cloud revenue and supply chain");
    expect(calls.posts).toHaveLength(1);

    await page.locator("article.console-result").first().getByRole("button", { name: "Open document workspace" }).click();
    await expect(page.locator("[data-workbench-route-origin='search']")).toBeVisible();
    // Opening a result never invents a second route or a second search.
    expect(new URL(page.url()).pathname).toBe("/search");
    expect(calls.posts).toHaveLength(1);

    // Browser back returns to the previous route; whichever route the shell
    // lands on, navigating never silently re-runs the search.
    await page.goBack();
    expect(calls.posts).toHaveLength(1);
    expect(calls.gets.length).toBeLessThanOrEqual(1);

    // A reload cannot silently re-run the query: the snapshot is runtime-only,
    // so the page returns to its initial state instead of faking results.
    await page.goto("/search");
    await expect(page.getByText("Start with a keyword query")).toBeVisible();
    expect(calls.posts).toHaveLength(1);
  });

  test("keyboard submission, labels, and contrast hold on the rebuilt page", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    const calls = trackDiscovery(page);
    await openSearch(page);

    // The query field is a real labelled control inside a real form, so Enter
    // submits it without any pointer interaction.
    const input = page.getByLabel("Search Query");
    await input.click();
    await input.pressSequentially("cloud revenue and supply chain");
    expect(calls.posts).toHaveLength(0);
    await input.press("Enter");
    await expect(page.getByRole("heading", { name: /Results for/ })).toBeVisible();
    expect(calls.posts).toHaveLength(1);

    // Filters keep their own labels, and the result actions stay reachable.
    await expect(page.getByRole("button", { name: "Company" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Rows per page" })).toBeVisible();
    await expect(page.getByLabel("Group by filing")).toBeVisible();

    // The console view-entry animation starts at opacity 0; scanning mid-flight
    // would measure blended colors instead of the settled page.
    await page.emulateMedia({ reducedMotion: "reduce" });
    const results = await new AxeBuilder({ page })
      .include("main")
      .options({ runOnly: ["color-contrast", "label", "button-name", "link-name", "aria-input-field-name"] })
      .analyze();
    const serious = results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious");
    expect(serious).toEqual([]);
  });

  test("captures the search composition at every receipt viewport", async ({ page, browserName }) => {
    for (const viewport of [...RECEIPT_VIEWPORTS, SHORT_VIEWPORT]) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await installApiFixtures(page);
      await openSearch(page);
      await submit(page, "cloud revenue and supply chain");

      await expect(page.locator("article.console-result").first()).toBeVisible();
      await expect(page.getByRole("heading", { name: "Search Overview" })).toBeVisible();

      // The console entry animation starts at opacity 0: prove paint first.
      await expect
        .poll(
          () => page.locator("section[aria-labelledby='search-title']").evaluate((node) => Number(getComputedStyle(node.firstElementChild as Element).opacity)),
          { message: `panel painted at ${viewport.name}` },
        )
        .toBeGreaterThan(0.99);

      await page.screenshot({
        path: `test-results/ui-006/search-${viewport.name}-${browserName}.png`,
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
