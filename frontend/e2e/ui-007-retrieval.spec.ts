import { expect, test } from "@playwright/test";

import { installApiFixtures } from "./fixtures";

/**
 * UI-007 Retrieval and Reranker receipts and behaviour.
 *
 * Retrieval is compared against
 * docs/ui-references/retrieval-ui-reference-dark-v1.png (1586x992). There is no
 * reranker reference screenshot — the master plan specifies that page — so the
 * Reranker receipts are captured on the same shell and checked for the
 * truthfulness rules the plan states (same pool, raw scores, rank movement, a
 * skipped stage that says so).
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

/** Count inspection traffic so "one submit, one run" is proved, not assumed. */
function trackInspections(page: Page) {
  const calls: string[] = [];
  page.on("request", (request: Request_) => {
    if (new URL(request.url()).pathname === "/retrieval/inspect" && request.method() === "POST") {
      calls.push(request.postData() ?? "");
    }
  });
  return calls;
}

async function openRetrieval(page: Page, path = "/retrieval") {
  await page.goto(path);
  await expect(page.getByRole("main", { name: "Research workspace" })).toHaveAttribute(
    "data-route-id",
    path === "/reranker" ? "reranker" : "retrieval",
  );
}

async function runInspection(page: Page, label: "Retrieval Query" | "Comparison Query") {
  await page.getByLabel(label).fill("What was Apple's total revenue in 2024?");
  await page.getByRole("button", { name: /^Run / }).first().click();
  await expect(page.getByRole("table")).toBeVisible();
}

test.describe("UI-007 retrieval and reranker", () => {
  test("retrieval renders the reference composition with real trace values", async ({ page, browserName }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page);
    await openRetrieval(page);

    // Query card, filters, the real pool bounds, and the submit control.
    await expect(page.getByLabel("Retrieval Query")).toBeVisible();
    await expect(page.getByRole("button", { name: "Company" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Document" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Section" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Preset" }).first()).toBeVisible();
    await expect(page.getByLabel("Final results (top K)")).toBeVisible();
    await expect(page.getByLabel("Candidate pool")).toBeVisible();
    await expect(page.getByText("Provider-free")).toBeVisible();

    // Reference page actions this build cannot back truthfully are absent.
    for (const absent of ["Query Examples", "Saved Searches", "Advanced Filters"]) {
      await expect(page.getByRole("button", { name: absent })).toHaveCount(0);
    }

    await runInspection(page, "Retrieval Query");

    // Four metric cards, each from the trace's own numbers.
    const metrics = page.getByTestId("retrieval-analyst-summary");
    await expect(metrics).toContainText("Candidates Retrieved");
    await expect(metrics).toContainText("From 3 document sections");
    await expect(metrics).toContainText("Selected Results");
    await expect(metrics).toContainText("Inspection Latency");
    await expect(metrics).toContainText("74.8 ms");
    await expect(metrics).toContainText("Reranker");
    await expect(metrics).toContainText("cross-encoder/ms-marco-MiniLM-L-6-v2");

    // Ranked table with the trace's own ranks and raw scores.
    const firstRow = page.getByRole("row", { name: /AAPL 10-K, Financial Statements/ });
    await expect(firstRow).toContainText("8.2500");
    await expect(page.getByRole("heading", { name: "Retrieved Results" })).toBeVisible();

    // Stage semantics, including the stage inspection never runs.
    await expect(page.getByText("Not executed in inspection").first()).toBeVisible();
    await expect(page.getByText("Inspection does not apply production structured financial-row promotion.")).toBeVisible();

    // The page's own labels never turn a ranking score into a percentage or a
    // confidence; filing excerpts may of course contain real "%" characters.
    expect(await metrics.innerText()).not.toContain("%");
    expect(await page.locator(".retrieval-score-column").first().innerText()).not.toContain("%");
    const labels = await page.locator(".console-stat__label, .console-stat__hint, .console-card__title").allInnerTexts();
    for (const label of labels) {
      expect(label.toLowerCase()).not.toContain("confidence");
      expect(label.toLowerCase()).not.toContain("%");
    }

    await page.screenshot({
      path: `test-results/ui-007/retrieval-results-1586x992-${browserName}.png`,
      fullPage: false,
      animations: "disabled",
    });
  });

  test("one submit runs one inspection and every later view change runs none", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    const calls = trackInspections(page);
    await openRetrieval(page);

    await page.getByLabel("Retrieval Query").fill("What was Apple's total revenue in 2024?");
    expect(calls).toHaveLength(0);
    await page.getByRole("button", { name: "Run retrieval" }).click();
    await expect(page.getByRole("table")).toBeVisible();
    expect(calls).toHaveLength(1);

    // Selecting a candidate, reordering, paging, and opening details are views.
    await page.getByRole("row", { name: /MSFT 10-K, MD&A/ }).click();
    await page.getByRole("button", { name: "Order" }).click();
    await page.getByRole("option", { name: "Reranker (score)" }).click();
    await page.getByRole("button", { name: "Rows per page" }).click();
    await page.getByRole("option", { name: "50 per page" }).click();
    expect(calls).toHaveLength(1);

    // A completed trace is never relabelled by editing the draft.
    await page.getByLabel("Retrieval Query").fill("a changed question");
    await expect(page.getByText(/This configuration differs from the trace on screen/)).toBeVisible();
    await expect(page.getByTestId("submitted-retrieval-configuration")).toContainText("What was Apple's total revenue in 2024?");
    expect(calls).toHaveLength(1);
  });

  test("a later submission wins over a slower earlier one", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    await openRetrieval(page);

    // Hold the first inspection open, then submit a second question.
    let heldRequest: import("@playwright/test").Route | null = null;
    await page.route("**/retrieval/inspect", async (route) => {
      if (heldRequest === null) {
        heldRequest = route;
        return;
      }
      await route.fallback();
    });

    await page.getByLabel("Retrieval Query").fill("first question about revenue");
    await page.getByRole("button", { name: "Run retrieval" }).click();
    await expect.poll(() => heldRequest !== null).toBe(true);

    await page.getByLabel("Retrieval Query").fill("second question about supply chain");
    await page.getByRole("button", { name: "Run retrieval" }).click();
    await expect(page.getByTestId("submitted-retrieval-configuration")).toContainText("second question about supply chain");

    // Release the slower first response: it must not replace the newer trace.
    await heldRequest!.fallback();
    await page.unroute("**/retrieval/inspect");
    await page.waitForTimeout(300);
    await expect(page.getByTestId("submitted-retrieval-configuration")).toContainText("second question about supply chain");
  });

  test("reranker compares fusion and cross-encoder from one run", async ({ page, browserName }) => {
    await page.setViewportSize(REFERENCE_VIEWPORT);
    await installApiFixtures(page);
    const calls = trackInspections(page);
    await openRetrieval(page, "/reranker");

    await runInspection(page, "Comparison Query");
    expect(calls).toHaveLength(1);

    // Both orderings come from the single response, and the page states how
    // many candidates the trace did not score instead of counting them as 0.
    const table = page.getByRole("table");
    await expect(table).toContainText("Fusion rank");
    await expect(table).toContainText("Reranker score");
    await expect(table).toContainText("8.2500");
    // A negative logit stays negative.
    await expect(table).toContainText("-3.5000");
    // Rank movement is named from the trace's own ranks: MSFT moves up one,
    // ORCL down one, and AAPL does not move at all.
    await expect(table).toContainText("Up 1");
    await expect(table).toContainText("Down 1");
    await expect(table).toContainText("No change");

    // The trace reports one candidate without a reranker score; it says so.
    await expect(page.getByText(/1 candidate has no reranker score in this trace/)).toBeVisible();

    // Selecting a row and opening details never runs the reranker again.
    await page.getByRole("row", { name: /ORCL 10-K, MD&A/ }).click();
    expect(calls).toHaveLength(1);

    // No invented zero and no percentage label on the page's own surfaces.
    const summary = await page.getByTestId("reranker-stage-summary").innerText();
    expect(summary).not.toContain("%");
    const scoreCells = await page.locator(".retrieval-score-column").allInnerTexts();
    for (const cell of scoreCells) expect(cell).not.toBe("0.0000");

    await page.screenshot({
      path: `test-results/ui-007/reranker-results-1586x992-${browserName}.png`,
      fullPage: false,
      animations: "disabled",
    });
  });

  test("a preset without the cross-encoder reports the stage as skipped", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    await openRetrieval(page, "/reranker");

    await page.getByLabel("Comparison Query").fill("What was Apple's total revenue in 2024?");
    await page.getByRole("button", { name: "Preset" }).click();
    await page.getByRole("option", { name: "Hybrid RRF" }).click();
    await page.getByRole("button", { name: "Run reranker comparison" }).click();

    const summary = page.getByTestId("reranker-stage-summary");
    await expect(summary).toContainText("Skipped");
    await expect(summary).toContainText("The selected preset ranks without the cross-encoder.");
    await expect(page.getByText(/no reranker score in this trace/)).toBeVisible();
    await page.screenshot({
      path: "test-results/ui-007/reranker-skipped-chromium.png",
      fullPage: false,
      animations: "disabled",
    });
  });

  test("opens the canonical chunk in the shared reader without re-running retrieval", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    const calls = trackInspections(page);
    await openRetrieval(page);
    await runInspection(page, "Retrieval Query");
    expect(calls).toHaveLength(1);

    const opener = page.locator("#retrieval-document-workspace-AAPL_fixture_revenue_0");
    await expect(opener).toBeVisible();
    await opener.click();
    await expect(page.locator("[data-workbench-route-origin='retrieval']")).toBeVisible();
    expect(calls).toHaveLength(1);
    await page.getByRole("button", { name: "Back to Retrieval", exact: true }).click();
    await expect(opener).toBeFocused();
    expect(calls).toHaveLength(1);
  });

  test("captures retrieval and reranker receipts at every viewport", async ({ page, browserName }) => {
    for (const viewport of [...RECEIPT_VIEWPORTS, SHORT_VIEWPORT]) {
      for (const surface of [
        { path: "/retrieval", label: "Retrieval Query" as const, id: "retrieval" },
        { path: "/reranker", label: "Comparison Query" as const, id: "reranker" },
      ]) {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await installApiFixtures(page);
        await openRetrieval(page, surface.path);
        await runInspection(page, surface.label);

        await expect(page.getByRole("table")).toBeVisible();
        // The console entry animation starts at opacity 0: prove paint first.
        await expect
          .poll(
            () => page.locator(".retrieval-page").evaluate((node) => Number(getComputedStyle(node.firstElementChild as Element).opacity)),
            { message: `${surface.id} painted at ${viewport.name}` },
          )
          .toBeGreaterThan(0.99);

        await page.screenshot({
          path: `test-results/ui-007/${surface.id}-${viewport.name}-${browserName}.png`,
          fullPage: false,
          animations: "disabled",
        });

        const overflow = await page.evaluate(() => ({
          body: document.body.scrollWidth - document.body.clientWidth,
          root: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        }));
        expect(overflow.body, `${surface.id} body overflow at ${viewport.name}`).toBeLessThanOrEqual(0);
        expect(overflow.root, `${surface.id} root overflow at ${viewport.name}`).toBeLessThanOrEqual(0);
      }
    }
  });
});
