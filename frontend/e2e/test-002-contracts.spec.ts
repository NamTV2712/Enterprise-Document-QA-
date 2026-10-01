import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { installApiFixtures } from "./fixtures";

const snippets = JSON.parse(readFileSync(resolve(process.cwd(), "../tests/fixtures/cross_layer_responses.json"), "utf8")).snippets as Array<{
  snippet: { text: string; ranges: number[][]; truncated: boolean }; marked: string[];
}>;

for (const variant of [
  { theme: "light", locale: "en", width: 1586, height: 992 },
  { theme: "dark", locale: "vi", width: 390, height: 844 },
] as const) {
  test(`TEST-002 original Unicode snippet highlights ${variant.theme}/${variant.locale}`, async ({ page, browserName }) => {
    await page.setViewportSize({ width: variant.width, height: variant.height });
    // Match the established Search accessibility gate: scan settled colors,
    // not the view-entry opacity animation's blended intermediate frame.
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.addInitScript(({ theme, locale }) => {
      localStorage.setItem("theme", theme);
      localStorage.setItem("sec_qa_locale", locale);
    }, variant);
    await installApiFixtures(page);
    const examples = snippets.filter(entry => entry.marked.length > 0);
    const hits = examples.map((entry, index) => ({
      chunk_id: `contract-chunk-${index}`, document_id: `contract:document-${index}`, ticker: "AAPL", section: "business",
      filing_date: "2024-01-01", report_date: null, chunk_index: index, score: 0, snippet: entry.snippet,
    }));
    await page.route("**/search", async route => {
      if (route.request().method() !== "POST") return route.fallback();
      const query = route.request().postDataJSON().query;
      const response = {
        search_id: "contract-search", query: { text: query, normalized: query, mode: "keyword" },
        grouping: { group_by: "document", group_count: hits.length, hit_count: hits.length },
        engine: { key: "bm25_lexical", version: "v1", definition: "Synthetic provider-free contract fixture" },
        scope: { ticker: null, section: null, year: null, filing_date: null, documents: hits.length, count_scope: "bounded_candidates", candidate_ceiling: 200, limited_by_ceiling: false, matched_documents: hits.length, matched_chunks: hits.length },
        items: hits.map(hit => ({ document_id: hit.document_id, ticker: hit.ticker, filing_date: hit.filing_date, report_date: null, sections: [hit.section], best_score: 0, hit_count: 1, hits: [hit] })),
        total: hits.length, page: 1, page_size: 20, facets: [], created_at: "2026-09-27T12:00:00Z", expires_at: "2026-09-27T12:10:00Z", ttl_seconds: 600,
      };
      await route.fulfill({ status: 200, contentType: "application/json", headers: { "Access-Control-Allow-Origin": "*" }, body: JSON.stringify(response) });
    });
    await page.goto("/search");
    const vi = variant.locale === "vi";
    await page.getByLabel(vi ? "Truy vấn tìm kiếm" : "Search Query").fill("revenue");
    await page.getByRole("button", { name: vi ? "Tìm kiếm" : "Search", exact: true }).click();
    const cards = page.locator("article.console-result");
    await expect(cards).toHaveCount(examples.length);
    for (let index = 0; index < examples.length; index++) {
      await expect(cards.nth(index)).toContainText(examples[index].snippet.text);
      await expect(cards.nth(index).locator("mark")).toHaveText(examples[index].marked);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    // This contract gate owns the changed excerpt renderer, not whole-page
    // visual certification. The dark page's existing button/score contrast
    // findings are recorded in the checkpoint; no CSS repair is claimed here.
    expect((await new AxeBuilder({ page }).include(".search-result__snippet").withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await page.route("**/collections?**", route => route.fulfill({ status: 404, contentType: "application/json", headers: { "Access-Control-Allow-Origin": "*" }, body: JSON.stringify({ detail: "Local workspace capability is unavailable" }) }));
    await cards.first().getByRole("button", { name: "Save evidence", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText(vi ? "Bộ sưu tập không khả dụng ở chế độ này" : "Collections are unavailable in this mode")).toBeVisible();
    await expect(dialog.getByRole("button", { name: vi ? "Tạo và thêm" : "Create and add" })).toHaveCount(0);
    await page.screenshot({ path: `test-results/test-002/unicode-${variant.theme}-${variant.locale}-${browserName}.png`, animations: "disabled" });
  });
}
