import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {
  installApiFixtures,
  askQuestion,
  openLibrary,
  LONG_ANSWER,
  API_ORIGIN,
} from "./fixtures";

/**
 * Browser verification for the research workspace. All backend traffic is
 * mocked locally; IndexedDB and localStorage are the browser's real stores.
 */

const VIEWPORTS = [
  { name: "mobile-390", width: 390, height: 844 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "desktop-1440", width: 1440, height: 900 },
];

async function setup(page: Page, options?: Parameters<typeof installApiFixtures>[1]) {
  await installApiFixtures(page, options);
  await page.goto("/");
  // The composer becomes usable once health reports the pipeline ready;
  // the "Pipeline: Ready" label is hidden on small viewports.
  const input = page.getByRole("textbox", { name: "Research question" });
  await expect(input).toBeVisible();
  await expect(input).toBeEnabled();
}

/**
 * Assert an element is genuinely displayed: non-zero size and a fully
 * opaque, visible ancestor chain. Condition-based retries replace fixed
 * sleeps, and no test ever forces animation state.
 */
export async function expectVisiblyDisplayed(locator: ReturnType<Page["getByText"]>): Promise<void>;
export async function expectVisiblyDisplayed(locator: import("@playwright/test").Locator): Promise<void>;
export async function expectVisiblyDisplayed(locator: import("@playwright/test").Locator): Promise<void> {
  await expect(async () => {
    const box = await locator.boundingBox();
    expect(box).not.toBeNull();
    expect(box?.width ?? 0).toBeGreaterThan(0);
    expect(box?.height ?? 0).toBeGreaterThan(0);
    const displayed = await locator.evaluate((element) => {
      let node: Element | null = element;
      while (node) {
        const style = getComputedStyle(node);
        if (style.visibility === "hidden" || style.display === "none") return false;
        if (Number.parseFloat(style.opacity) < 0.99) return false;
        node = node.parentElement;
      }
      return true;
    });
    expect(displayed).toBe(true);
  }).toPass({ timeout: 5_000 });
}

async function expectNoCriticalAxeViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    // Color-contrast runs separately against the real token values below.
    .disableRules("color-contrast")
    .analyze();
  const critical = results.violations.filter(
    (violation) => violation.impact === "critical" || violation.impact === "serious",
  );
  expect(critical).toEqual([]);
}

test("overview renders and passes accessibility scan", async ({ page }) => {
  await setup(page);
  await expect(page.getByText("Ask questions. Verify every answer.")).toBeVisible();
  await expectNoCriticalAxeViolations(page);
});

test("asked question streams a cited answer with evidence", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();
  await expect(
    page.getByText(/Retrieved filing evidence · 2 excerpts/i),
  ).toBeVisible();
});

test("a stream that ends without done keeps partial text as a stopped answer", async ({ page }) => {
  await installApiFixtures(page);
  await page.route(`${API_ORIGIN}/query/stream`, async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-headers": "Content-Type",
          "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
        },
      });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: {
        "access-control-allow-origin": "*",
        "content-type": "text/event-stream",
      },
      body:
        `data: ${JSON.stringify({ type: "sources", data: [] })}\n\n` +
        `data: ${JSON.stringify({ type: "token", data: "Partial answer before stop" })}\n\n`,
    });
  });
  await page.goto("/");
  await expect(page.getByText("Pipeline: Ready")).toBeVisible();
  await askQuestion(page, "What are Apple's main risk factors?");
  // The mocked stream ends without a done event; the connection closes so
  // the message normalizes to a stopped state with partial text kept.
  await expect(page.getByText(/Partial answer before stop/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Stop generating response" }),
  ).not.toBeVisible();
});

test("answer can be bookmarked and found through the Library filter", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();

  await page.getByRole("button", { name: "Bookmark this answer" }).click();
  await expect(page.getByRole("button", { name: "Remove bookmark from this answer" })).toBeVisible();

  await openLibrary(page);
  await page.getByRole("button", { name: "Bookmarked answers" }).click();
  await expect(page.getByText(/Apple's total net sales were/).first()).toBeVisible();
});

test("evidence panel search filters excerpts and keeps source numbers", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await page.getByRole("button", { name: /Show 2 retrieved filing evidence excerpts/i }).click();

  const search = page.getByRole("searchbox", {
    name: "Search within these evidence excerpts",
  });
  await search.fill("Microsoft Cloud");
  await expect(page.getByText(/Showing 1 of 2 excerpts/i)).toBeVisible();
  // The surviving excerpt keeps its original source identity and shows the
  // filing date as document metadata, not as a fiscal period.
  await expect(
    page.getByText(
      /Microsoft Corporation \(MSFT\) · Filed 2025-07-30 · Management Discussion & Analysis \(MD&A\)/,
    ),
  ).toBeVisible();

  await search.fill("");
  await expect(page.getByText(/Showing 2 of 2 excerpts/i)).toBeVisible();
});

test("evidence excerpt copy writes citation context to the clipboard", async ({
  page,
  context,
}, testInfo) => {
  // Firefox does not support programmatic clipboard permission grants.
  const isFirefox = testInfo.project.name === "firefox";
  if (!isFirefox) {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  }
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await page.getByRole("button", { name: /Show 2 retrieved filing evidence excerpts/i }).click();

  await page.getByRole("button", { name: "Copy excerpt 1 with citation" }).click();
  await expect(page.getByRole("button", { name: "Copied excerpt 1" })).toBeVisible();
  if (!isFirefox) {
    const clipboard = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboard).toContain("[Source 1] AAPL 10-K (filed 2025-10-31)");
    expect(clipboard).toContain("Filed: 2025-10-31");
  }
});

test("saved conversation becomes read-only when the backend session is gone", async ({ page }) => {
  await installApiFixtures(page, {
    history: {
      session_id: "expired-session",
      turns: [],
      context: { status: "missing", retained_turns: 0, ttl_remaining_seconds: 0 },
    },
  });
  await page.addInitScript(() => {
    localStorage.setItem("sec_qa_session_id", "expired-session");
    localStorage.setItem("sec_qa_active_conversation_id", "conversation-expired-session");
    localStorage.setItem(
      "sec_qa_conversations_v2",
      JSON.stringify([
        {
          schemaVersion: 2,
          id: "conversation-expired-session",
          sessionId: "expired-session",
          title: "Expired research",
          titleMode: "custom",
          revision: 2,
          createdAt: 1,
          updatedAt: 2,
          draft: "",
          bookmarkedMessageIds: [],
          messages: [
            { id: "u-1", sender: "user", text: "What are the main risks?" },
            {
              id: "a-1",
              sender: "assistant",
              text: "Saved answer kept for reading.",
              status: "completed",
            },
          ],
        },
      ]),
    );
  });
  await page.goto("/");

  await expect(page.getByText("Saved answer kept for reading.")).toBeVisible();
  await expect(
    page.getByText(/backend session for this saved conversation has expired/i).first(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Send question" })).toBeDisabled();
  // The composer still accepts a draft for the next conversation.
  const input = page.getByRole("textbox", { name: "Research question" });
  await input.fill("Follow-up draft for later");
  await expect(input).toHaveValue("Follow-up draft for later");
});

test("help dialog documents usage and closes with Escape", async ({ page }) => {
  await setup(page);
  await page.getByRole("button", { name: "Open help" }).click();
  const dialog = page.getByRole("dialog", { name: "How to use this research workspace" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText(/Shift\+Enter adds a new line/i)).toBeVisible();
  await expect(dialog.getByText(/up to 100 conversations/i)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});

test("library search is reachable with Ctrl+K", async ({ page }) => {
  await setup(page);
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("searchbox", { name: "Search saved conversations" })).toBeFocused();
});

test("theme choice persists and manual light survives a dark OS preference", async ({
  browser,
}) => {
  const context = await browser.newContext({ colorScheme: "dark" });
  const page = await context.newPage();
  await installApiFixtures(page);
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "Research question" });
  await expect(input).toBeEnabled();
  // System mode follows the dark OS preference.
  await expect(page.locator("html")).toHaveClass(/dark/);

  await page.getByRole("button", { name: /Theme System/ }).click();
  await page.getByRole("menuitemradio", { name: "Light" }).click();
  await expect(page.locator("html")).not.toHaveClass(/dark/);

  await page.reload();
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  await context.close();
});

test("theme menu supports keyboard selection", async ({ page }) => {
  await setup(page);
  // Stable id locator: the accessible name changes with the selection.
  const trigger = page.locator("#theme-switcher-btn");
  await trigger.click();
  const menu = page.getByRole("menu", { name: "Theme preference" });
  await expect(menu).toBeVisible();
  // The selected item receives focus when the menu opens (roving tabindex).
  await expect(page.getByRole("menuitemradio", { name: "System" })).toBeFocused();
  await page.keyboard.press("End");
  await page.keyboard.press("Enter");
  await expect(trigger).toHaveAccessibleName(/Theme Dark/);
  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect(menu).not.toBeVisible();
  // Focus returns to the trigger.
  await expect(trigger).toBeFocused();
});

test("conversation survives a full page reload through IndexedDB", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();
  // The persisted-write indicator lives in the Library panel.
  await openLibrary(page);
  await expect(page.getByText("Saved on this device")).toBeVisible();

  await page.reload();
  await expect(page.getByText("Pipeline: Ready")).toBeVisible();
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();
});

test("citation deep links survive reload and Markdown export keeps evidence anchors", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();

  await page.getByRole("button", { name: "Open source 1" }).first().click();
  await expect(page).toHaveURL(/#evidence=assistant-[A-Za-z0-9_-]+-0$/);
  const deepLink = page.url();

  await page.reload();
  await expect(page).toHaveURL(deepLink);
  await expect(
    page.getByRole("button", { name: /Hide 2 retrieved filing evidence excerpts/i }),
  ).toBeVisible();

  await openLibrary(page);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export conversation" }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.md$/);
  const stream = await download.createReadStream();
  let markdown = "";
  if (stream) {
    for await (const chunk of stream) markdown += chunk.toString();
  }
  expect(markdown).toContain("<a id=\"evidence-");
});

test("live evaluation fixture renders provenance and JSON/CSV exports", async ({ page }) => {
  await installApiFixtures(page);
  const summary = {
    run_id: "live-fixture-v1",
    title: "Live fixture evaluation",
    status: "candidate",
    created_at: "2026-09-07T00:00:00.000Z",
    provenance: { dataset_version: "fixture-v1" },
    aggregate: { faithfulness: 0.9, answer_relevancy: 0.8, sample_count: 1 },
    case_count: 1,
  };
  const run = {
    ...summary,
    cases: [{
      case_id: "fixture-case-1",
      question: "What was Apple's total net sales?",
      language: "en",
      status: "OK",
      answer: "Apple reported $391,035 million [Source 1].",
      scores: { faithfulness: 0.9 },
      gates: { citation_correctness: true },
      reasons: [],
      evidence: [{ citation: "AAPL 10-K", excerpt: "Total net sales 391,035" }],
    }],
    notes: ["Fixture only; not an official benchmark."],
  };
  await page.route(`${API_ORIGIN}/evaluation/runs?*`, async (route) => {
    await route.fulfill({ status: 200, headers: { "access-control-allow-origin": "*", "content-type": "application/json" }, body: JSON.stringify({ items: [summary], total: 1, page: 1, page_size: 20 }) });
  });
  await page.route(`${API_ORIGIN}/evaluation/runs/live-fixture-v1`, async (route) => {
    await route.fulfill({ status: 200, headers: { "access-control-allow-origin": "*", "content-type": "application/json" }, body: JSON.stringify(run) });
  });
  await page.goto("/?view=evaluation");

  await expect(page.getByText("Live fixture evaluation").first()).toBeVisible();
  await expect(page.getByText(/Fixture only; not an official benchmark/)).toBeVisible();
  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export evaluation JSON" }).click();
  expect((await jsonDownload).suggestedFilename()).toBe("live-fixture-v1.json");
  const csvDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export evaluation CSV" }).click();
  expect((await csvDownload).suggestedFilename()).toBe("live-fixture-v1.csv");
});

test.describe("visual matrix", () => {
  // Each screenshot name carries browser, theme, viewport, and state so
  // Chromium and Firefox never overwrite each other's images.
  // Headless Chromium can freeze CSS animation clocks on small viewports,
  // which would freeze entrance animations at their transparent first
  // frame. The matrix captures the settled UI under reduced motion; the
  // animated behavior itself is covered by the interaction tests above.
  test.use({ reducedMotion: "reduce" });

  for (const theme of ["light", "dark"] as const) {
    for (const viewport of VIEWPORTS) {
      test(`screenshot ${theme} ${viewport.name} overview`, async ({ page }, testInfo) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await setup(page);
        if (theme === "dark") {
          await page.getByRole("button", { name: /Theme System/ }).click();
          await page.getByRole("menuitemradio", { name: "Dark" }).click();
        }
        await expect(page.getByText("Ask questions. Verify every answer.")).toBeVisible();
        // Let entrance animations settle so screenshots show the final state.
        await page.waitForTimeout(700);
        await page.screenshot({
          path: `e2e/screenshots/${testInfo.project.name}-${theme}-${viewport.name}-overview.png`,
          fullPage: false,
        });
      });

      test(`screenshot ${theme} ${viewport.name} conversation`, async ({ page }, testInfo) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await setup(page);
        if (theme === "dark") {
          await page.getByRole("button", { name: /Theme System/ }).click();
          await page.getByRole("menuitemradio", { name: "Dark" }).click();
        }
        await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
        await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();
        await page.getByRole("button", { name: /Show 2 retrieved filing evidence excerpts/i }).click();
        await expect(page.getByText("Microsoft Cloud revenue increased").first()).toBeVisible();
        await page.waitForTimeout(700);
        await page.screenshot({
          path: `e2e/screenshots/${testInfo.project.name}-${theme}-${viewport.name}-conversation.png`,
          fullPage: false,
        });
      });
    }
  }
});

// --- Display verification without animation manipulation ----------------

async function expectWorkspaceVisible(page: Page): Promise<void> {
  // The heading, the composer, and (after a question) the answer and its
  // evidence must be genuinely displayed: sized, opaque, unclipped.
  const heading = page.getByText("Ask questions. Verify every answer.");
  await expectVisiblyDisplayed(heading);
  const composer = page.getByRole("textbox", { name: "Research question" });
  await expectVisiblyDisplayed(composer);
}

test.describe("display smokes", () => {
  for (const motion of ["no-preference", "reduce"] as const) {
    test.describe(`motion: ${motion}`, () => {
      test.use({ reducedMotion: motion });

      test(`390px overview renders visibly (${motion})`, async ({ page }) => {
        await page.setViewportSize({ width: 390, height: 844 });
        await setup(page);
        await expectWorkspaceVisible(page);
      });

      test(`390px answer and evidence render visibly (${motion})`, async ({ page }) => {
        await page.setViewportSize({ width: 390, height: 844 });
        await setup(page);
        await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
        const answer = page.getByText(LONG_ANSWER.split("\n")[0]).first();
        await expectVisiblyDisplayed(answer);
        await page
          .getByRole("button", { name: /Show 2 retrieved filing evidence excerpts/i })
          .click();
        await expectVisiblyDisplayed(
          page.getByText("Microsoft Cloud revenue increased").first(),
        );
      });
    });
  }

  test("320px smoke keeps the workspace usable", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 700 });
    await setup(page);
    await expectWorkspaceVisible(page);
  });

  test("narrow-viewport reflow (640px CSS viewport) keeps the workspace usable", async ({ page }) => {
    // This is an explicit CSS viewport receipt. Browser UI zoom is not
    // controllable consistently in headless Firefox/Chromium.
    await page.setViewportSize({ width: 640, height: 450 });
    await setup(page);
    await expectWorkspaceVisible(page);
  });
});

// --- Regression: persistence and request lifecycle -----------------------

test("unreadable library data survives load and later operations untouched", async ({
  page,
}) => {
  const corrupt =
    '{"envelopeVersion":3,"records":[{"id":"broken","schemaVersion":2';
  await installApiFixtures(page);
  await page.addInitScript((raw) => {
    localStorage.setItem("sec_qa_library_v3", raw);
    // The v2 fallback still holds one readable conversation.
    localStorage.setItem(
      "sec_qa_conversations_v2",
      JSON.stringify([
        {
          schemaVersion: 2,
          id: "conversation-legacy-copy",
          sessionId: "session-legacy-copy",
          title: "Legacy copy",
          titleMode: "auto",
          revision: 1,
          createdAt: 1,
          updatedAt: 2,
          messages: [
            { id: "u-1", sender: "user", text: "Legacy question" },
            { id: "a-1", sender: "assistant", text: "Legacy answer" },
          ],
          draft: "",
          bookmarkedMessageIds: [],
        },
      ]),
    );
  }, corrupt);
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();

  // The unreadable payload is reported and the legacy copy still shows.
  await openLibrary(page);
  await expect(page.getByText("Legacy copy")).toBeVisible();
  await expect(page.getByText(/could not be read/i)).toBeVisible();

  // Ask a question in a new conversation; the corrupt bytes must survive.
  await page.getByRole("tab", { name: /Research/ }).click();
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();
  await openLibrary(page);
  await expect(page.getByText(/could not be read/i)).toBeVisible();

  const stored = await page.evaluate(() => localStorage.getItem("sec_qa_library_v3"));
  expect(stored).toBe(corrupt);
});

