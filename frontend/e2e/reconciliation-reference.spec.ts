import { expect, Page, test } from "@playwright/test";
import path from "node:path";
import {
  API_ORIGIN,
  askQuestion,
  createCollectionsFixtureState,
  installApiFixtures,
  RECONCILIATION_NET_SALES_ANSWER,
  RECONCILIATION_SOURCES,
} from "./fixtures";

const phase = process.env.RECONCILIATION_CAPTURE_PHASE ?? "before";

const surfaces = [
  { id: "r0-global-shell-overview", reference: "rag-workbench-master-reference-dark.png", path: "/?view=overview", width: 1254, height: 856, heading: "Available corpus", contentSelector: ".workspace-primary-column h2" },
  { id: "r0-global-shell-conversation", reference: "rag-workbench-master-reference-dark.png", path: "/?view=conversation", width: 1254, height: 856, heading: "Research", contentSelector: "[data-workbench-region='research']" },
  { id: "r1-research", reference: "research-ui-reference-dark-v1.png", path: "/?view=conversation", width: 1586, height: 992, heading: "Research", contentSelector: "[data-workbench-region='research']" },
  { id: "r2-documents", reference: "documents-ui-reference-dark-v1.png", path: "/?view=documents", width: 1586, height: 992, heading: "Documents", contentSelector: ".workspace-primary-column h1" },
  { id: "r3-search", reference: "search-ui-reference-dark-v1.png", path: "/?view=search", width: 1586, height: 992, heading: "Search", contentSelector: ".workspace-primary-column h1" },
  { id: "r4-library", reference: "collections-ui-reference-dark-v1.png", path: "/?view=library", width: 1586, height: 992, heading: "Collections", contentSelector: "#collections-title" },
  { id: "r5-retrieval", reference: "retrieval-ui-reference-dark-v1.png", path: "/?view=retrieval", width: 1586, height: 992, heading: "Retrieval", contentSelector: "#retrieval-lab-title" },
  { id: "r6-models", reference: "models-ui-reference-dark-v1.png", path: "/?view=models", width: 1586, height: 992, heading: "Models", contentSelector: ".workspace-primary-column h1" },
  { id: "r7-pipeline", reference: "pipeline-ui-reference-dark-v1.png", path: "/?view=pipeline", width: 1586, height: 992, heading: "Pipeline", contentSelector: ".workspace-primary-column h1" },
  { id: "r8-evaluation", reference: "evaluation-ui-reference-dark-v1.png", path: "/?view=evaluation", width: 1586, height: 992, heading: "Evaluation", contentSelector: ".workspace-primary-column h1" },
] as const;

const fabricatedCopy = [
  "Apple SEC 10-K",
  "GPT-4o",
  "gpt-4o",
  "Nguyen",
  "AI Engineer",
  "System Healthy",
  "Pipeline Healthy",
  "Upgrade Plan",
  "100 GB",
  "Recorded demo",
  "Official benchmark",
  "3.4s total",
];

async function assertReferenceContract(page: Page, surface: (typeof surfaces)[number]) {
  await expect(page.locator(surface.contentSelector)).toBeVisible();
  await expect(page.getByText(surface.heading, { exact: false }).first()).toBeVisible();
  const geometry = await page.evaluate(() => ({
    viewport: { width: window.innerWidth, height: window.innerHeight },
    scrollWidth: document.documentElement.scrollWidth,
    bodyText: document.body.innerText,
    unnamedButtons: [...document.querySelectorAll("button")]
      .filter((button) => !(button.getAttribute("aria-label") || button.textContent || "").trim())
      .map((button) => button.outerHTML.slice(0, 180)),
  }));
  expect(geometry.viewport).toEqual({ width: surface.width, height: surface.height });
  expect(geometry.scrollWidth).toBeLessThanOrEqual(surface.width + 2);
  expect(geometry.unnamedButtons).toEqual([]);
  for (const text of fabricatedCopy) expect(geometry.bodyText).not.toContain(text);
  expect(geometry.bodyText).toContain("No ticker selected");
  return geometry;
}

/**
 * Screenshot receipts deliberately exercise real UI handoffs against the
 * hermetic fixture API. They do not add product seed state or target-copy
 * filler: every visible answer, source, and document comes through the same
 * request and selection flow a reader uses in the application.
 */
async function preparePopulatedReceipt(page: Page, surface: (typeof surfaces)[number]) {
  if (surface.id === "r0-global-shell-conversation" || surface.id === "r1-research") {
    await askQuestion(page, "What were Apple's total net sales in fiscal year 2025?");
    await expect(page.getByText(RECONCILIATION_NET_SALES_ANSWER.split("\n")[0], { exact: false }).first()).toBeVisible();

    // The narrow master receipt retains the response in its truthful
    // responsive conversation layout. The desktop reference also shows the
    // actual source-to-document handoff, so exercise it at the wider size.
    if (surface.id === "r1-research") {
      await page.getByRole("button", { name: "Open 2 sources", exact: true }).click();
      const sources = page.locator("[data-workbench-region='sources']");
      await expect(sources).toBeVisible();
      await expect(sources.getByRole("button", { name: /Open source excerpt 1:/ })).toContainText(RECONCILIATION_SOURCES[0]?.text_preview ?? "");
      await page.getByRole("button", { name: "Open document for source 1", exact: true }).click();
      const document = page.locator("[data-workbench-region='document']");
      await expect(document).toBeVisible();
      await expect(document.getByText(RECONCILIATION_SOURCES[0]?.text ?? "", { exact: true }).first()).toBeVisible();
    }
    return;
  }

  if (surface.id === "r2-documents") {
    await page.getByRole("checkbox", { name: "Show details for AAPL", exact: true }).check();
    await expect(page.getByRole("heading", { name: "Apple Inc. (AAPL)", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Document Summary", exact: true })).toBeVisible();
    return;
  }

  if (surface.id === "r3-search") {
    await page.getByLabel("Search Query").fill("What was Apple's total revenue in 2024?");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByRole("heading", { name: /Results for/, exact: false })).toBeVisible();
    await expect(page.getByRole("button", { name: "Save evidence", exact: true }).first()).toBeVisible();
    return;
  }

  if (surface.id === "r4-library") {
    // A collection cannot be truthfully populated from a blank Library route.
    // Capture one through the application's real retrieval and save flow — the
    // save now names its typed workspace collection (DATA-003) — then return
    // through the canonical navigation item.
    await page.getByRole("link", { name: "Search", exact: true }).click();
    await page.getByLabel("Search Query").fill("What was Apple's total revenue in 2024?");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByRole("heading", { name: /Results for/, exact: false })).toBeVisible();
    await page.getByRole("button", { name: "Save evidence", exact: true }).first().click();

    const targetDialog = page.getByRole("dialog", { name: "Save evidence to a collection" });
    await expect(targetDialog).toBeVisible();
    await targetDialog.getByLabel("Or create a new collection").fill("Revenue evidence");
    await targetDialog.getByRole("button", { name: "Create and add" }).click();
    await expect(targetDialog).toBeHidden();

    await page.getByRole("link", { name: "Collections", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Collections", exact: true })).toBeVisible();
    const dismiss = page.getByRole("button", { name: "Dismiss", exact: true });
    if (await dismiss.isVisible()) await dismiss.click();
    await page.getByRole("button", { name: "Open Revenue evidence", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Items (1)", exact: true })).toBeVisible();
    // The saved member keeps the discovery excerpt's own citation.
    await expect(page.getByText("AAPL indexed excerpt · financial_statements", { exact: true })).toBeVisible();
    const collectionItem = page.locator(".collection-items__row", { hasText: "AAPL indexed excerpt · financial_statements" });
    const [titleBox, metaBox] = await Promise.all([
      collectionItem.locator(".collection-items__citation").boundingBox(),
      collectionItem.locator(".collection-items__provenance").first().boundingBox(),
    ]);
    expect(titleBox).not.toBeNull();
    expect(metaBox).not.toBeNull();
    expect(metaBox!.y).toBeGreaterThan(titleBox!.y);
    return;
  }

  if (surface.id === "r5-retrieval") {
    await page.getByRole("button", { name: "Run retrieval", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Retrieved Results", exact: true })).toBeVisible();
    // Every ranked row carries its own save action; the receipt needs one.
    await expect(page.getByRole("button", { name: "Save evidence", exact: true }).first()).toBeVisible();
  }
}

/** Keep visual receipts anchored at the application shell, not at a focused
 * control the setup flow may have scrolled into view. */
async function resetReceiptScroll(page: Page) {
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    document.querySelectorAll<HTMLElement>(
      ".workbench-application-main, .workspace-scroll, .conversation-message-scroll, .sidebar-scroll, .console-layout__aside, [data-workbench-region='document']",
    ).forEach((element) => element.scrollTo({ top: 0, left: 0 }));
  });
}

test.describe("Truthful workbench reference receipts", () => {
  test.use({ reducedMotion: "reduce" });

  test("pdf fixture reader availability mirrors the admitted derived artifact", async ({ page }) => {
    await installApiFixtures(page, { pdf: true });
    await page.goto("/?view=overview", { waitUntil: "domcontentloaded" });

    const contract = await page.evaluate(async (apiOrigin) => {
      const [readerResponse, manifestResponse, mappingResponse, contentResponse] = await Promise.all([
        fetch(`${apiOrigin}/documents/AAPL%3Afixture/reader`),
        fetch(`${apiOrigin}/documents/AAPL%3Afixture/pdf`),
        fetch(`${apiOrigin}/documents/AAPL%3Afixture/pdf/mapping`),
        fetch(`${apiOrigin}/documents/AAPL%3Afixture/pdf/content`),
      ]);
      const [reader, manifest, mapping, content] = await Promise.all([
        readerResponse.json(),
        manifestResponse.json(),
        mappingResponse.json(),
        contentResponse.arrayBuffer(),
      ]);
      const digest = await crypto.subtle.digest("SHA-256", content);
      const artifactHash = Array.from(new Uint8Array(digest))
        .map((byte) => byte.toString(16).padStart(2, "0"))
        .join("");
      return {
        readerPdf: reader.representations.find((representation: { kind: string }) => representation.kind === "pdf"),
        readerSource: reader.sources[0],
        readerSourceSetRevision: reader.source_set_revision,
        manifest,
        mapping,
        artifactHash,
        artifactSize: content.byteLength,
      };
    }, API_ORIGIN);

    expect(contract.manifest.representation_type).toBe("DERIVED_PDF");
    expect(contract.manifest.representation_id).toBe(`derived_pdf:${contract.manifest.artifact_key}`);
    expect(contract.manifest.artifact_size_bytes).toBe(contract.artifactSize);
    expect(contract.manifest.artifact_hash).toBe(contract.artifactHash);
    expect(contract.manifest.mapping_status).toBe("unavailable");
    expect(contract.readerSourceSetRevision).toBe(contract.manifest.source_set_revision);
    expect(contract.readerSource.source_document_id).toBe(contract.manifest.source_document_id);
    expect(contract.readerSource.document_revision).toBe(contract.manifest.document_revision);
    expect(contract.readerPdf).toMatchObject({
      kind: "pdf",
      status: "available",
      reason_code: "pdf_available",
      representation_id: contract.manifest.representation_id,
      representation_type: contract.manifest.representation_type,
      page_semantics: contract.manifest.page_semantics,
      artifact_key: contract.manifest.artifact_key,
      artifact_hash: contract.manifest.artifact_hash,
      source_content_hash: contract.manifest.source_content_hash,
      page_count: contract.manifest.page_count,
      mapping_status: contract.manifest.mapping_status,
    });
    expect(contract.mapping).toMatchObject({
      mapping_manifest_id: contract.manifest.mapping_manifest_id,
      representation_id: contract.manifest.representation_id,
      document_id: contract.manifest.document_id,
      source_document_id: contract.manifest.source_document_id,
      source_set_revision: contract.manifest.source_set_revision,
      document_revision: contract.manifest.document_revision,
      source_content_hash: contract.manifest.source_content_hash,
      artifact_key: contract.manifest.artifact_key,
      artifact_hash: contract.manifest.artifact_hash,
    });
    expect(contract.mapping.entries).toHaveLength(contract.manifest.mapping_entry_count);
    for (const entry of contract.mapping.entries) {
      expect(entry).toMatchObject({ status: "unavailable", rects: [] });
    }
  });

  test("pdf fixture does not fabricate a rectangle for unmapped net-sales evidence", async ({ page }) => {
    const netSalesSource = RECONCILIATION_SOURCES.find((source) => source?.chunk_id === "AAPL_fixture_net_sales_0");
    const netSalesChunkTextHash = netSalesSource?.chunk_text_hash;
    if (!netSalesSource || typeof netSalesChunkTextHash !== "string") {
      throw new Error("Expected the reconciliation net-sales fixture source.");
    }
    const source = { chunk_id: netSalesSource.chunk_id, chunk_text_hash: netSalesChunkTextHash };

    await installApiFixtures(page, { pdf: true });
    await page.goto("/?view=overview", { waitUntil: "domcontentloaded" });

    const result = await page.evaluate(async ({ apiOrigin, source }) => {
      const manifest = await fetch(`${apiOrigin}/documents/AAPL%3Afixture/pdf`).then((response) => response.json());
      const query = new URLSearchParams({
        chunk_id: source.chunk_id,
        chunk_text_hash: source.chunk_text_hash,
        source_document_id: manifest.source_document_id,
        source_set_revision: manifest.source_set_revision,
        document_revision: manifest.document_revision,
      });
      const response = await fetch(`${apiOrigin}/documents/AAPL%3Afixture/pdf/mapping/location?${query.toString()}`);
      return { ok: response.ok, manifest, location: await response.json() };
    }, { apiOrigin: API_ORIGIN, source });

    expect(result.ok).toBe(true);
    expect(result.location).toMatchObject({
      document_id: result.manifest.document_id,
      source_document_id: result.manifest.source_document_id,
      source_set_revision: result.manifest.source_set_revision,
      document_revision: result.manifest.document_revision,
      source_content_hash: result.manifest.source_content_hash,
      representation_id: result.manifest.representation_id,
      artifact_key: result.manifest.artifact_key,
      artifact_hash: result.manifest.artifact_hash,
      mapping_manifest_id: result.manifest.mapping_manifest_id,
      chunk_id: source.chunk_id,
      chunk_text_hash: source.chunk_text_hash,
      status: "unavailable",
      reason: "The selected range has no complete PDF rectangle mapping.",
      match_count: 0,
      match_count_capped: false,
      entry_ids: [],
      rects: [],
    });
    expect(result.location.chunk_id).not.toBe("AAPL_test_risk_factors_0");
  });

  test("fresh startup does not inject the former legacy example", async ({ page }) => {
    await page.setViewportSize({ width: 1254, height: 856 });
    await installApiFixtures(page, { pdf: true });
    await page.goto("/?view=overview", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);

    await expect(page.getByText("What are Apple's main risks mentioned in the 2024 10-K?", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Legacy example — not live evidence.", { exact: false })).toHaveCount(0);
  });

  test("sidebar exposes only canonical workspace routes", async ({ page }) => {
    await page.setViewportSize({ width: 1254, height: 856 });
    await installApiFixtures(page, { pdf: true });
    await page.goto("/?view=overview", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);

    const views = await page.locator("[data-workbench-region='navigation'] [data-route-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-route-id")));
    expect(views).toEqual([
      "chat",
      "research",
      "documents",
      "search",
      "collections",
      "retrieval",
      "models",
      "pipeline",
      "reranker",
      "evaluation",
      "analytics",
      "datasets",
      "settings",
      "logs",
    ]);
    await expect(page.locator("[data-workbench-region='navigation'] [data-route-id='reranker']")).toHaveAttribute("data-route-availability", "available");
    await expect(page.getByRole("link", { name: "Users", exact: true })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Research", exact: true })).toHaveCount(1);
  });

  for (const surface of surfaces) {
    test(`${phase} ${surface.id} against ${surface.reference}`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width: surface.width, height: surface.height });
      await page.addInitScript(() => window.localStorage.setItem("theme", "dark"));
      await installApiFixtures(page, {
        pdf: true,
        // The library receipt drives the real save flow, which now targets a
        // typed workspace collection (DATA-003).
        ...(surface.id === "r4-library" ? { collections: createCollectionsFixtureState() } : {}),
        ...(surface.id === "r0-global-shell-conversation" || surface.id === "r1-research"
          ? { streamAnswers: [RECONCILIATION_NET_SALES_ANSWER], streamSources: [RECONCILIATION_SOURCES] }
          : {}),
      });
      await page.goto(surface.path, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1800);
      await preparePopulatedReceipt(page, surface);
      await resetReceiptScroll(page);

      const geometry = await assertReferenceContract(page, surface);
      await page.waitForTimeout(1200);

      await page.screenshot({
        path: testInfo.outputPath(`${surface.id}-${phase}.png`),
        fullPage: false,
      });
      await testInfo.attach("actual-reference-file", {
        path: path.resolve(process.cwd(), "..", "docs", "ui-references", surface.reference),
      });
      await testInfo.attach("reference-contract", {
        body: JSON.stringify({ surface, geometry }, null, 2),
        contentType: "application/json",
      });
    });
  }

  test(`${phase} light-theme preservation and compact shell`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addInitScript(() => window.localStorage.setItem("theme", "light"));
    await installApiFixtures(page, { pdf: true });
    await page.goto("/?view=overview", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    const geometry = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      hasDarkClass: document.documentElement.classList.contains("dark"),
      bodyText: document.body.innerText,
    }));
    expect(geometry.scrollWidth).toBeLessThanOrEqual(392);
    expect(geometry.hasDarkClass).toBe(false);
    expect(geometry.bodyText).toContain("Available corpus");
    await page.screenshot({ path: testInfo.outputPath(`r0-light-mobile-${phase}.png`), fullPage: false });
  });
});
