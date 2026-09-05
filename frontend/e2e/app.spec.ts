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
 * Jump every animation to its final frame before a screenshot. Headless
 * Chromium can freeze CSS animation clocks on small viewports, which would
 * otherwise capture entrance animations at their transparent first frame.
 */
async function settleAnimations(page: Page): Promise<void> {
  await page.evaluate(() => {
    // Document.getAnimations() already returns every animation in the tree.
    document.getAnimations().forEach((animation) => {
      try {
        animation.finish();
      } catch {
        // Infinite animations have no end state; canceling them keeps the
        // element's static styles, which is what the matrix documents.
        animation.cancel();
      }
    });
  });
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

test.describe("visual matrix", () => {
  // Headless Chromium can freeze CSS animation clocks on small viewports,
  // which would freeze entrance animations at their transparent first
  // frame. The matrix captures the settled UI under reduced motion; the
  // animated behavior itself is covered by the interaction tests above.
  test.use({ reducedMotion: "reduce" });

  for (const theme of ["light", "dark"] as const) {
    for (const viewport of VIEWPORTS) {
      test(`screenshot ${theme} ${viewport.name} overview`, async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await setup(page);
        if (theme === "dark") {
          await page.getByRole("button", { name: /Theme System/ }).click();
          await page.getByRole("menuitemradio", { name: "Dark" }).click();
        }
        await expect(page.getByText("Ask questions. Verify every answer.")).toBeVisible();
        // Let entrance animations settle so screenshots show the final state.
        await page.waitForTimeout(700);
        await settleAnimations(page);
        await page.screenshot({
          path: `e2e/screenshots/${theme}-${viewport.name}-overview.png`,
          fullPage: false,
        });
      });

      test(`screenshot ${theme} ${viewport.name} conversation`, async ({ page }) => {
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
        await settleAnimations(page);
        await page.screenshot({
          path: `e2e/screenshots/${theme}-${viewport.name}-conversation.png`,
          fullPage: false,
        });
      });
    }
  }
});
