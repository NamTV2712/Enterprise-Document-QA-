import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { installApiFixtures, askQuestion, openLibrary, LONG_ANSWER, API_ORIGIN } from "./fixtures";

/**
 * Regression coverage for the persistence and request-lifecycle fixes. All
 * backend traffic is mocked; storage is the browser's real IndexedDB and
 * localStorage.
 */

async function setup(page: Page, options?: Parameters<typeof installApiFixtures>[1]) {
  await installApiFixtures(page, options);
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "Research question" });
  await expect(input).toBeVisible();
  await expect(input).toBeEnabled();
}

async function expectVisiblyDisplayed(locator: import("@playwright/test").Locator): Promise<void> {
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

test("switching conversations during a pending preflight never sends the old question", async ({
  page,
}) => {
  let preflightReleased = false;
  await installApiFixtures(page);
  // Hold the saved conversation's preflight response until the test
  // releases it, after the switch has happened.
  await page.route(`${API_ORIGIN}/session/saved-session/history`, async (route) => {
    await new Promise<void>((resolve) => {
      const interval = setInterval(() => {
        if (preflightReleased) {
          clearInterval(interval);
          resolve();
        }
      }, 25);
    });
    await route.fulfill({
      status: 200,
      headers: { "access-control-allow-origin": "*", "content-type": "application/json" },
      body: JSON.stringify({
        session_id: "saved-session",
        turns: [],
        context: { status: "available", retained_turns: 2, ttl_remaining_seconds: 600 },
      }),
    });
  });
  await page.addInitScript(() => {
    localStorage.setItem("sec_qa_session_id", "saved-session");
    localStorage.setItem("sec_qa_active_conversation_id", "conversation-saved");
    localStorage.setItem(
      "sec_qa_library_v3",
      JSON.stringify({
        envelopeVersion: 3,
        records: [
          {
            schemaVersion: 2,
            id: "conversation-saved",
            sessionId: "saved-session",
            title: "Saved session",
            titleMode: "auto",
            revision: 1,
            createdAt: 1,
            updatedAt: 2,
            messages: [
              { id: "u-1", sender: "user", text: "Earlier question" },
              { id: "a-1", sender: "assistant", text: "Earlier answer", status: "completed" },
            ],
            draft: "",
            bookmarkedMessageIds: [],
          },
        ],
        tombstones: [],
      }),
    );
  });
  await page.goto("/");
  await expect(page.getByText("Earlier answer")).toBeVisible();

  let streamCalled = false;
  page.on("request", (request) => {
    if (request.url().includes("/query/stream")) streamCalled = true;
  });

  await askQuestion(page, "This question must never be sent");
  // While the preflight waits, start a new conversation: the old preflight
  // is invalidated instead of being answered into the new conversation.
  await page.locator("#quick-reset-btn").click();
  await page
    .getByRole("dialog", { name: "Start a new conversation?" })
    .getByRole("button", { name: "Start new conversation" })
    .click();

  preflightReleased = true;
  await page.waitForTimeout(600);
  expect(streamCalled).toBe(false);
  // The new conversation stays empty and fresh.
  await expect(page.getByText("Earlier answer")).not.toBeVisible();
});

test("deleting the active conversation while a request is pending aborts and isolates the late response", async ({
  page,
}) => {
  let lateResponseReleased = false;
  await installApiFixtures(page, {
    history: {
      session_id: "saved-session",
      turns: [],
      context: { status: "available", retained_turns: 2, ttl_remaining_seconds: 600 },
    },
  });
  // Hold the decomposed response until the deletion has won; the request
  // stays pending in the app while the user deletes the conversation.
  await page.route(`${API_ORIGIN}/query/decomposed`, async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: { "access-control-allow-origin": "*" },
      });
      return;
    }
    await new Promise<void>((resolve) => {
      const interval = setInterval(() => {
        if (lateResponseReleased) {
          clearInterval(interval);
          resolve();
        }
      }, 25);
    });
    await route.fulfill({
      status: 200,
      headers: { "access-control-allow-origin": "*", "content-type": "application/json" },
      body: JSON.stringify({
        answer: "Late comparative answer that must never appear.",
        model_used: "openai/gpt-oss-120b",
        was_decomposed: true,
        sub_queries: [],
        sources: [],
        num_total_chunks: 0,
      }),
    });
  });
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();

  // Complete one exchange first so the conversation exists in the Library;
  // the second request is the one left pending when the deletion happens.
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();

  await askQuestion(page, "Compare Apple and Microsoft cloud revenue");
  await expect(page.getByRole("button", { name: "Query breakdown Preparing" })).toBeVisible();

  await openLibrary(page);
  await page.getByRole("button", { name: "Delete conversation" }).click();
  await page.getByRole("button", { name: "Delete", exact: true }).click();

  // A fresh conversation replaced the deleted one.
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();

  // The late response must not leak into the new conversation.
  lateResponseReleased = true;
  await page.waitForTimeout(500);
  await expect(page.getByText("Late comparative answer that must never appear.")).not.toBeVisible();
});

test("reload after a fallback failure keeps saved data and warnings", async ({ page }) => {
  const corrupt = '{"envelopeVersion":3,"records":[{"id":"broken"';
  await installApiFixtures(page);
  await page.addInitScript((raw) => {
    localStorage.setItem("sec_qa_library_v3", raw);
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

  await openLibrary(page);
  await expect(page.getByText("Legacy copy")).toBeVisible();
  await expect(page.getByText(/could not be read/i)).toBeVisible();

  // A reload runs the same protection path again.
  await page.reload();
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  await openLibrary(page);
  await expect(page.getByText("Legacy copy")).toBeVisible();
  await expect(page.getByText(/could not be read/i)).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("sec_qa_library_v3"))).toBe(corrupt);
});

test("closing the help dialog returns focus to its opener", async ({ page }) => {
  await setup(page);
  await page.getByRole("button", { name: "Open help" }).click();
  const dialog = page.getByRole("dialog", { name: "How to use this research workspace" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Close help" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Open help" })).toBeFocused();
});

test("opening a bookmarked answer scrolls to and focuses the message", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  const answerText = page.getByText(LONG_ANSWER.split("\n")[0]).first();
  await expect(answerText).toBeVisible();
  await page.getByRole("button", { name: "Bookmark this answer" }).click();

  await openLibrary(page);
  await page.getByRole("button", { name: "Bookmarked answers" }).click();
  await page.getByText(/Apple's total net sales were/).first().click();

  await expect(async () => {
    const focused = await page.evaluate(() => ({
      id: document.activeElement?.id ?? "",
      tag: document.activeElement?.tagName ?? "",
    }));
    expect(focused.id).toContain("message-");
    expect(focused.tag).not.toBe("BODY");
  }).toPass({ timeout: 5_000 });
});

test("conversation view passes the color-contrast scan", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();
  await page
    .getByRole("button", { name: /Show 2 retrieved filing evidence excerpts/i })
    .click();
  await expect(page.getByText("Microsoft Cloud revenue increased").first()).toBeVisible();

  const results = await new AxeBuilder({ page })
    .include("main")
    .options({ runOnly: ["color-contrast"] })
    .analyze();
  const serious = results.violations.filter(
    (violation) => violation.impact === "critical" || violation.impact === "serious",
  );
  expect(serious).toEqual([]);
});

test("320px smoke keeps the workspace visibly usable", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await setup(page);
  await expectVisiblyDisplayed(page.getByText("Ask questions. Verify every answer."));
  await expectVisiblyDisplayed(page.getByRole("textbox", { name: "Research question" }));
});

test("200% zoom (640px CSS viewport) keeps the workspace visibly usable", async ({ page }) => {
  await page.setViewportSize({ width: 640, height: 450 });
  await setup(page);
  await expectVisiblyDisplayed(page.getByText("Ask questions. Verify every answer."));
  await expectVisiblyDisplayed(page.getByRole("textbox", { name: "Research question" }));
});

test.describe("390px reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("answer and evidence render visibly", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expectVisiblyDisplayed(page.getByText(LONG_ANSWER.split("\n")[0]).first());
  await page
    .getByRole("button", { name: /Show 2 retrieved filing evidence excerpts/i })
    .click();
    await expectVisiblyDisplayed(page.getByText("Microsoft Cloud revenue increased").first());
  });
});
