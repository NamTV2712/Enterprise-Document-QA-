import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { installApiFixtures, askQuestion, openLibrary, LONG_ANSWER, API_ORIGIN } from "./fixtures";

const LONG_ANSWER_FIRST_LINE = LONG_ANSWER.split("\n")[0];

async function selectListboxOption(page: Page, label: string, option: string) {
  await page.getByRole("button", { name: label, exact: true }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

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

async function openTools(page: Page): Promise<void> {
  // PLAN V2 exposes real tool destinations in canonical groups rather than
  // hiding them behind the removed legacy Tools accordion.
  await expect(page.getByRole("button", { name: "Retrieval Lab", exact: true })).toBeVisible();
}

test("opens the exact citation in the indexed context viewer", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What are Apple's main business risks?");
  const sourcesButton = page.getByRole("button", { name: "Open 2 sources", exact: true });
  await expect(sourcesButton).toBeVisible();
  await sourcesButton.click();

  const contextPanel = page.locator(".context-panel");
  await expect(contextPanel).toBeVisible();
  await expect(contextPanel.getByText("Indexed excerpts").first()).toBeVisible();
  await expect(contextPanel.locator(".context-viewer-text")).toContainText("competition risks");
  await expect(contextPanel.getByRole("link", { name: "Open SEC" })).toHaveAttribute("href", /sec\.gov/);
  await expect(contextPanel.getByText("Indexed document chunks")).toBeVisible();
  await contextPanel.screenshot({ path: "test-results/p2-4-context-panel.png" });
});

test("evidence inspector uses the remaining-width mode and closes without losing citation identity", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await askQuestion(page, "What are Apple's main business risks?");
  const sourcesButton = page.getByRole("button", { name: "Open 2 sources", exact: true });
  await expect(sourcesButton).toBeVisible();
  await sourcesButton.click();
  await expect(page.locator(".context-panel")).toBeVisible();
  await expect(page.getByRole("dialog", { name: "Evidence inspector" })).toHaveCount(0);
  await page.getByRole("button", { name: "Close evidence inspector" }).click();
  await expect(page.locator(".context-panel")).toHaveCount(0);

  await page.setViewportSize({ width: 1024, height: 900 });
  const sourceButton = page.getByRole("button", { name: "Open source 1" }).first();
  await sourceButton.click();
  await expect(page.getByRole("dialog", { name: "Evidence inspector" })).toBeVisible();
  await page.getByRole("button", { name: "Close evidence inspector" }).click();
  await expect(page.getByRole("dialog", { name: "Evidence inspector" })).toHaveCount(0);
  await expect(sourceButton).toBeFocused();

  await page.getByRole("button", { name: "Use compact navigation" }).click();
  await sourceButton.click();
  await expect(page.getByRole("dialog", { name: "Evidence inspector" })).toBeVisible();
});

test("conversation keeps the message scroller and composer inside the primary column", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await askQuestion(page, "What are Apple's main business risks?");

  const primary = page.locator(".workspace-primary-column");
  const messageScroller = page.locator(".conversation-message-scroll");
  const composer = page.locator(".composer-shell");
  const answer = page.getByText(LONG_ANSWER_FIRST_LINE).first();
  await expect(answer).toBeVisible();
  const geometry = await page.evaluate(() => {
    const primaryBox = document.querySelector<HTMLElement>(".workspace-primary-column")?.getBoundingClientRect();
    const scrollerBox = document.querySelector<HTMLElement>(".conversation-message-scroll")?.getBoundingClientRect();
    const composerBox = document.querySelector<HTMLElement>(".composer-shell")?.getBoundingClientRect();
    const answerBox = document.querySelector<HTMLElement>(".message-answer-layout")?.getBoundingClientRect();
    return { primaryBox, scrollerBox, composerBox, answerBox };
  });
  expect(geometry.scrollerBox?.left ?? -1).toBeGreaterThanOrEqual((geometry.primaryBox?.left ?? 0) - 1);
  expect(geometry.scrollerBox?.right ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual((geometry.primaryBox?.right ?? 0) + 1);
  expect(geometry.composerBox?.top ?? -1).toBeGreaterThanOrEqual(geometry.scrollerBox?.top ?? 0);
  expect(geometry.composerBox?.bottom ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual(900 + 1);
  expect(geometry.answerBox?.bottom ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual((geometry.composerBox?.top ?? 0) + 1);

  const input = page.getByRole("textbox", { name: "Research question" });
  await input.fill("First line\nSecond line\nThird line");
  await expect(input).toHaveValue("First line\nSecond line\nThird line");
  const inputHeight = await input.evaluate((element) => element.getBoundingClientRect().height);
  expect(inputHeight).toBeGreaterThan(40);
  await page.setViewportSize({ width: 1024, height: 900 });
  await expect(input).toHaveValue("First line\nSecond line\nThird line");
  await expect(composer).toBeVisible();
  await expect(primary).toBeVisible();
  await expect(messageScroller).toBeVisible();
});

test("projects measured pipeline stages from the response stream", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What are Apple's main business risks?");

  const execution = page.getByText("Execution stages", { exact: true });
  await expect(execution).toBeVisible();
  await execution.click();
  const executionStatus = page.getByTestId("execution-stage-list");
  await expect(executionStatus.getByText("Query preparation", { exact: true })).toBeVisible();
  await expect(executionStatus.getByText("Retrieval", { exact: true })).toBeVisible();
  await expect(executionStatus.getByText("2 sources", { exact: true })).toBeVisible();
});

test("Retrieval Lab invalidates edited loading config and exports the completed trace", async ({ page }) => {
  let releaseInspection!: () => void;
  const inspectionHeld = new Promise<void>((resolve) => { releaseInspection = resolve; });
  await setup(page);
  await page.route(`${API_ORIGIN}/retrieval/inspect`, async (route) => {
    await inspectionHeld;
    await route.fallback();
  });

  await page.getByRole("button", { name: "Retrieval Lab", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Retrieval Lab", exact: true })).toBeVisible();
  const runButton = page.getByRole("button", { name: "Run retrieval", exact: true });
  await runButton.click();
  await expect(page.getByRole("button", { name: "Running…", exact: true })).toBeDisabled();
  await page.getByRole("textbox", { name: "Retrieval question" }).fill("A changed question must invalidate the pending trace");
  await expect(page.getByText("The configuration changed. Run retrieval again to refresh the trace and exports.")).toBeVisible();
  releaseInspection();
  await page.waitForTimeout(100);
  await expect(page.getByTestId("submitted-retrieval-configuration")).toHaveCount(0);
  await page.unroute(`${API_ORIGIN}/retrieval/inspect`);

  await runButton.click();
  await expect(page.getByTestId("submitted-retrieval-configuration")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "JSON", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("retrieval-trace.json");
});

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
  await page.route(`${API_ORIGIN}/query/decomposed/stream`, async (route) => {
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
      headers: { "access-control-allow-origin": "*", "content-type": "text/event-stream" },
      body: `data: ${JSON.stringify({ type: "token", data: "Late comparative answer that must never appear." })}\n\ndata: ${JSON.stringify({ type: "done", data: { request_status: "completed" } })}\n\n`,
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
  await page.getByRole("button", { name: "Research", exact: true }).click();
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
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  await openLibrary(page);
  await expect(page.getByText("Legacy copy")).toBeVisible();
  await expect(page.getByText(/could not be read/i)).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("sec_qa_library_v3"))).toBe(corrupt);
});

test("a second tab becomes the Library writer after the first tab closes", async ({ page }) => {
  await installApiFixtures(page);
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  const locksSupported = await page.evaluate(() => "locks" in navigator);
  test.skip(!locksSupported, "Web Locks are not available in this browser.");

  const second = await page.context().newPage();
  try {
    await installApiFixtures(second);
    await second.goto("/");
    await expect(second.getByRole("textbox", { name: "Research question" })).toBeEnabled();

    await openLibrary(page);
    await openLibrary(second);
    await expect(page.getByText("Saved on this device")).toBeVisible();
    await expect(second.getByText(/Read-only mode/i)).toBeVisible();
    await expect(second.getByText(/Another tab currently owns the Library writer lock/i)).toBeVisible();

    await page.close();
    await expect(second.getByText(/Read-only mode/i)).not.toBeVisible({ timeout: 5_000 });
    await expect(second.getByText("Saved on this device")).toBeVisible();
  } finally {
    await second.close();
  }
});

test("backup import previews before creating fresh local records", async ({ page }) => {
  await setup(page);
  await openLibrary(page);

  const backup = {
    format: "enterprise-document-qa.conversations",
    version: 2,
    exportedAt: "2026-09-07T00:00:00.000Z",
    conversations: [{
      schemaVersion: 4,
      id: "conversation-import-source",
      sessionId: "session-import-source",
      title: "Imported revenue review",
      titleMode: "custom",
      revision: 2,
      createdAt: 1,
      updatedAt: 2,
      draft: "",
      bookmarkedMessageIds: [],
      messages: [
        { id: "question-import-source", sender: "user", text: "What was revenue?" },
        { id: "answer-import-source", sender: "assistant", text: "Revenue was $100B.", status: "completed" },
      ],
    }],
    collections: [],
  };
  await page.locator('input[type="file"]').setInputFiles({
    name: "research-backup.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(backup)),
  });

  await expect(page.getByRole("dialog", { name: "Review backup before import" })).toBeVisible();
  await expect(page.getByText("Import creates fresh IDs and does not overwrite existing conversations.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirm import" })).toBeVisible();
  await page.getByRole("button", { name: "Confirm import" }).click();

  await expect(page.getByRole("status").filter({ hasText: "Imported 1" })).toBeVisible();
  await expect(page.getByText("Imported revenue review")).toBeVisible();
});

test("guided portfolio route reaches research, retrieval, evaluation, and architecture views", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER.split("\n")[0]).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Open source 1" }).first()).toBeVisible();

  await openTools(page);
  await page.getByRole("button", { name: "Retrieval Lab", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Retrieval Lab" })).toBeVisible();
  await expect(page.getByText("Provider-free")).toBeVisible();

  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Evaluation & experiments" })).toBeVisible();
  await selectListboxOption(page, "Mode", "Recorded demo");
  await expect(page.getByRole("heading", { name: "Recorded evaluation contract" })).toBeVisible();

  await page.getByRole("button", { name: "System", exact: true }).click();
  await expect(page.getByRole("heading", { name: "System & provenance" })).toBeVisible();
  await expect(page.getByText("Provider-free tools")).toBeVisible();
});

test("Documents and Search open the exact chunk in the shared indexed reader", async ({ page }) => {
  await setup(page);
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Search the filing corpus" })).toBeVisible();
  await page.getByRole("textbox", { name: "Search question" }).fill("What was Apple's total revenue in 2024?");
  await page.getByRole("button", { name: "Run search" }).click();
  await page.getByRole("button", { name: "Open indexed excerpt" }).click();
  await expect(page.locator(".context-viewer-text")).toContainText("Total revenue was reported in fiscal 2024.");
  await page.getByRole("button", { name: "Close evidence inspector" }).click();

  await page.getByRole("button", { name: "Documents", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Document Explorer" })).toBeVisible();
  await page.getByRole("button", { name: /Apple Inc\. \(AAPL\) · 2025-10-31/ }).click();
  await page.getByRole("button", { name: "Open indexed excerpt" }).click();
  await expect(page.locator(".document-workspace")).toBeVisible();
  await expect(page.locator(".document-workspace__excerpt")).toContainText("Total revenue was reported in fiscal 2024.");
  await expect(page.getByRole("heading", { name: "Selected indexed excerpt", exact: true })).toBeVisible();
});

test("wide tool views retain a usable canvas without evidence-rail geometry", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await openTools(page);

  for (const step of [
    { button: "Retrieval Lab", heading: "Retrieval Lab" },
    { button: "Evaluation", heading: "Evaluation & experiments" },
    { button: "Architecture", heading: "Architecture" },
  ]) {
    await page.getByRole("button", { name: step.button, exact: true }).click();
    await expect(page.getByRole("heading", { name: step.heading, exact: true })).toBeVisible();
    const geometry = await page.evaluate(() => {
      const primary = document.querySelector<HTMLElement>(".workspace-primary-column");
      return {
        primaryWidth: primary?.getBoundingClientRect().width ?? 0,
        scrollWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
      };
    });
    expect(geometry.primaryWidth).toBeGreaterThan(1_000);
    expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.viewportWidth);
  }

  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Evaluation & experiments", exact: true })).toBeVisible();
  await selectListboxOption(page, "Mode", "Recorded demo");
  const detailWidth = await page.getByRole("heading", { name: "Recorded evaluation contract demo (provider-free)" }).evaluate(
    (heading) => heading.closest("article")?.getBoundingClientRect().width ?? 0,
  );
  expect(detailWidth).toBeGreaterThan(650);
});

test("navigation reflows at the 1024px desktop boundary in both themes and locales", async ({ page }) => {
  await installApiFixtures(page);

  for (const theme of ["light", "dark"] as const) {
    for (const locale of ["en", "vi"] as const) {
      await page.setViewportSize({ width: 1440, height: 800 });
      await page.goto("/");
      await page.evaluate(({ nextTheme, nextLocale }) => {
        localStorage.setItem("theme", nextTheme);
        localStorage.setItem("sec_qa_locale", nextLocale);
        localStorage.setItem("sec_qa_navigation_layout_v1", "expanded");
      }, { nextTheme: theme, nextLocale: locale });
      await page.reload();
      await expect(page.getByRole("textbox", { name: locale === "vi" ? "Câu hỏi nghiên cứu" : "Research question" })).toBeVisible();

      for (const width of [1024, 1272, 1280, 1440]) {
        await page.setViewportSize({ width, height: 800 });
        await page.goto("/");
        const nav = page.locator(".sidebar-shell");
        const geometry = await page.evaluate(() => {
          const sidebar = document.querySelector<HTMLElement>(".sidebar-shell");
          const primary = document.querySelector<HTMLElement>(".workspace-primary-column");
          const composer = document.querySelector<HTMLElement>(".composer-shell");
          const sidebarBox = sidebar?.getBoundingClientRect();
          const primaryBox = primary?.getBoundingClientRect();
          const composerBox = composer?.getBoundingClientRect();
          const layoutControl = document.querySelector<HTMLElement>(".sidebar-layout-toggle");
          const themeControl = document.querySelector<HTMLElement>("#theme-switcher-btn");
          return {
            navigationMode: sidebar?.classList.contains("sidebar-shell--desktop") ? "inline" : "drawer",
            navigationWidth: sidebarBox?.width ?? 0,
            navigationRight: sidebarBox?.right ?? 0,
            primaryLeft: primaryBox?.left ?? 0,
            composerLeft: composerBox?.left ?? 0,
            composerRight: composerBox?.right ?? 0,
            foregroundPairs: [layoutControl, themeControl].map((element) => {
              if (!element) return null;
              const styles = getComputedStyle(element);
              return {
                height: element.getBoundingClientRect().height,
                color: styles.color,
                borderColor: styles.borderColor,
              };
            }),
            scrollWidth: document.documentElement.scrollWidth,
            viewportWidth: window.innerWidth,
          };
        });

        await expect(nav).toBeVisible();
        expect(geometry.navigationMode).toBe("inline");
        expect(geometry.navigationWidth).toBeGreaterThanOrEqual(215);
        expect(geometry.navigationWidth).toBeLessThanOrEqual(217);
        expect(geometry.primaryLeft).toBeGreaterThanOrEqual(geometry.navigationRight - 1);
        expect(geometry.composerLeft).toBeGreaterThanOrEqual(geometry.navigationRight - 1);
        expect(geometry.composerRight).toBeLessThanOrEqual(geometry.viewportWidth);
        for (const pair of geometry.foregroundPairs) {
          expect(pair).not.toBeNull();
          expect(pair?.height ?? 0).toBeGreaterThanOrEqual(44);
          expect(pair?.color).not.toBe(pair?.borderColor);
        }
        expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.viewportWidth);
      }

      await page.locator(".sidebar-layout-toggle").click();
      await expect(page.locator(".sidebar-shell--desktop")).toHaveAttribute("data-navigation-layout", "compact");
      await page.waitForFunction(() => {
        const sidebar = document.querySelector<HTMLElement>(".sidebar-shell--desktop");
        return (sidebar?.getBoundingClientRect().width ?? Number.POSITIVE_INFINITY) <= 57;
      });
      const compactWidth = await page.locator(".sidebar-shell--desktop").evaluate((element) => element.getBoundingClientRect().width);
      expect(compactWidth).toBeGreaterThanOrEqual(55);
      expect(compactWidth).toBeLessThanOrEqual(57);

      await page.setViewportSize({ width: 1023, height: 800 });
      await page.goto("/");
      await expect(page.locator("#sidebar-toggle")).toBeVisible();
      await expect(page.locator(".sidebar-shell")).toHaveCount(0);
      await page.locator("#sidebar-toggle").click();
      await expect(page.locator(".sidebar-shell--drawer")).toBeVisible();
      const menuControl = await page.locator("#sidebar-toggle").evaluate((element) => {
        const styles = getComputedStyle(element);
        return {
          height: element.getBoundingClientRect().height,
          color: styles.color,
          borderColor: styles.borderColor,
        };
      });
      expect(menuControl.height).toBeGreaterThanOrEqual(44);
      expect(menuControl.color).not.toBe(menuControl.borderColor);
      await page.locator(".sidebar-drawer-close").click();
      await expect(page.locator("#sidebar-toggle")).toBeFocused();
    }
  }
});

test("research shell stays inside the viewport from desktop to narrow phone widths", async ({ page }) => {
  await installApiFixtures(page);

  for (const width of [1920, 1440, 1366, 1280, 1272, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/");
    const input = page.getByRole("textbox", { name: "Research question" });
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();

    const geometry = await page.evaluate(() => {
      const composer = document.querySelector<HTMLElement>(".composer-shell");
      const inputElement = document.getElementById("chat-textarea");
      const composerBox = composer?.getBoundingClientRect();
      const inputBox = inputElement?.getBoundingClientRect();
      return {
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        documentWidth: document.documentElement.scrollWidth,
        bodyWidth: document.body.scrollWidth,
        composer: composerBox
          ? { left: composerBox.left, right: composerBox.right, bottom: composerBox.bottom }
          : null,
        input: inputBox
          ? { left: inputBox.left, right: inputBox.right, bottom: inputBox.bottom }
          : null,
      };
    });

    expect(geometry.documentWidth).toBeLessThanOrEqual(geometry.viewportWidth);
    expect(geometry.bodyWidth).toBeLessThanOrEqual(geometry.viewportWidth);
    expect(geometry.composer?.left ?? -1).toBeGreaterThanOrEqual(0);
    expect(geometry.composer?.right ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual(geometry.viewportWidth);
    expect(geometry.composer?.bottom ?? 0).toBeLessThanOrEqual(geometry.viewportHeight + 1);
    expect(geometry.input?.left ?? -1).toBeGreaterThanOrEqual(0);
    expect(geometry.input?.right ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual(geometry.viewportWidth);
    expect(geometry.input?.bottom ?? 0).toBeLessThanOrEqual(geometry.viewportHeight + 1);
  }
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
  await page.locator(".message-secondary-actions > summary").click();
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
    .getByRole("button", { name: "Open 2 sources", exact: true })
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

test("narrow header exposes command and More controls without horizontal overflow", async ({ page }) => {
  await installApiFixtures(page);
  await page.setViewportSize({ width: 1440, height: 800 });
  await page.goto("/");

  for (const locale of ["en", "vi"] as const) {
    await page.evaluate((nextLocale) => {
      localStorage.setItem("theme", "light");
      localStorage.setItem("sec_qa_locale", nextLocale);
    }, locale);
    await page.reload();

    for (const width of [320, 390, 768]) {
      await page.setViewportSize({ width, height: 700 });
      await page.goto("/");
      await expect(page.locator("#chat-textarea")).toBeVisible();

      const geometry = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        bodyWidth: document.body.scrollWidth,
        viewportWidth: window.innerWidth,
      }));
      expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.viewportWidth);
      expect(geometry.bodyWidth).toBeLessThanOrEqual(geometry.viewportWidth);
      await expect(page.locator("#sidebar-toggle")).toBeVisible();
      await expect(page.locator(".header-command-button")).toBeVisible();

      if (width < 768) {
        await expect(page.locator(".header-compact-status")).toBeVisible();
        await expect(page.locator(".header-more-trigger")).toBeVisible();
        await expect(page.locator("#theme-switcher-btn")).toBeHidden();
        await expect(page.locator(".locale-switcher.header-wide-control")).toBeHidden();

        await page.locator(".header-more-trigger").click();
        const moreDialog = page.locator(".header-more-dialog");
        await expect(moreDialog).toBeVisible();
        await expect(moreDialog.locator(".header-more-dialog__close")).toBeFocused();
        await expect(moreDialog.locator(".header-more-control-option")).toHaveCount(3);

        await moreDialog.getByRole("button", { name: /help|hướng dẫn/i }).click();
        await expect(moreDialog).toHaveCount(0);
        await expect(page.locator(".help-dialog-panel")).toBeVisible();
        await page.locator(".help-dialog-panel").getByRole("button").first().click();
        await expect(page.locator(".help-dialog-panel")).toHaveCount(0);
        await expect(page.locator(".header-more-trigger")).toBeFocused();
      } else {
        await expect(page.locator(".header-more-trigger")).toBeHidden();
        await expect(page.locator("#theme-switcher-btn")).toBeVisible();
        await expect(page.locator(".locale-switcher.header-wide-control")).toBeVisible();
      }
    }
  }
});

test("narrow-viewport reflow (640px CSS viewport, no browser zoom) keeps the workspace usable", async ({ page }) => {
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
    .getByRole("button", { name: "Open 2 sources", exact: true })
    .click();
    await expectVisiblyDisplayed(page.getByText("Microsoft Cloud revenue increased").first());
  });
});

// --- Persistence chains with real browser storage -------------------------

function libraryRecord(id: string, sessionId: string, title: string) {
  return {
    schemaVersion: 2,
    id,
    sessionId,
    title,
    titleMode: "auto",
    revision: 1,
    createdAt: 1,
    updatedAt: 2,
    messages: [
      { id: `${id}-u1`, sender: "user", text: `Question for ${title}` },
      { id: `${id}-a1`, sender: "assistant", text: `Answer for ${title}`, status: "completed" },
    ],
    draft: "",
    bookmarkedMessageIds: [],
  };
}

test("a pending update never removes the persisted copy of another conversation", async ({
  page,
}) => {
  // Seed a full library (100 records): the next new conversation cannot be
  // admitted, so its completed exchange stays pending while other saves
  // still work.
  await installApiFixtures(page);
  await page.addInitScript(() => {
    const records = [];
    for (let index = 0; index < 100; index += 1) {
      records.push({
        schemaVersion: 2,
        id: `conversation-seed-${index}`,
        sessionId: `session-seed-${index}`,
        title: `Seeded conversation ${index}`,
        titleMode: "auto",
        revision: 1,
        createdAt: index,
        updatedAt: index,
        messages: [
          { id: `s${index}-u1`, sender: "user", text: `Seed question ${index}` },
          { id: `s${index}-a1`, sender: "assistant", text: `Seed answer ${index}`, status: "completed" },
        ],
        draft: "",
        bookmarkedMessageIds: [],
      });
    }
    localStorage.setItem(
      "sec_qa_library_v3",
      JSON.stringify({ envelopeVersion: 3, records, tombstones: [] }),
    );
  });
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();

  // Conversation A completes an exchange but cannot be persisted (limit).
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER_FIRST_LINE).first()).toBeVisible();

  // Reload: the durable library is intact, still exactly 100 seeded records,
  // and the pending A was neither admitted nor dropped into storage.
  await page.reload();
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  await openLibrary(page);
  await expect(page.getByText("Seeded conversation 0")).toBeVisible();
  await expect(page.getByText("Seeded conversation 99")).toBeVisible();
  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("sec_qa_library_v3") ?? "{}"),
  );
  const seeded = (stored.records as { id: string }[]).filter((record) =>
    record.id.startsWith("conversation-seed-"),
  );
  expect(seeded).toHaveLength(100);
});

test("malformed tombstones are preserved and reported across reloads", async ({ page }) => {
  const malformed = JSON.stringify({
    envelopeVersion: 3,
    records: [libraryRecord("conversation-kept", "session-kept", "Kept conversation")],
    tombstones: [{ id: "broken", revision: "not-a-number", deletedAt: 1 }],
  });
  await installApiFixtures(page);
  await page.addInitScript((raw) => {
    localStorage.setItem("sec_qa_library_v3", raw);
  }, malformed);
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();

  await openLibrary(page);
  await expect(page.getByText("Kept conversation")).toBeVisible();
  await expect(page.getByText(/deletion state/i)).toBeVisible();

  // The malformed bytes survive ask/save/reload untouched.
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await askQuestion(page, "What was Apple's total net sales in fiscal year 2025?");
  await expect(page.getByText(LONG_ANSWER_FIRST_LINE).first()).toBeVisible();
  await page.reload();
  await openLibrary(page);
  await expect(page.getByText(/deletion state/i)).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("sec_qa_library_v3"))).toBe(malformed);
});

test("a durable tombstone shows deletion-pending with retry and locks editing", async ({
  page,
}) => {
  const payload = {
    envelopeVersion: 3,
    records: [libraryRecord("conversation-pending-ui", "session-pending-ui", "Pending deletion")],
    tombstones: [{ id: "conversation-pending-ui", revision: 1, deletedAt: 5 }],
  };
  await installApiFixtures(page);
  await page.addInitScript((raw) => {
    localStorage.setItem("sec_qa_library_v3", raw);
    localStorage.setItem("sec_qa_session_id", "session-pending-ui");
    localStorage.setItem("sec_qa_active_conversation_id", "conversation-pending-ui");
  }, JSON.stringify(payload));
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();

  await openLibrary(page);
  await expect(page.getByText(/Deletion pending/i).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry deletion" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Rename conversation" })).not.toBeVisible();
  // The active pending conversation locks follow-up sending.
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await expect(page.getByRole("button", { name: "Send question" })).toBeDisabled();

  await openLibrary(page);

  // Retry completes the deletion on healthy backends.
  await page.getByRole("button", { name: "Retry deletion" }).click();
  await expect(page.getByRole("button", { name: "Retry deletion" })).not.toBeVisible();
  await expect(page.getByText(/Deletion pending/i).first()).not.toBeVisible();

  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("sec_qa_library_v3") ?? "{}"),
  );
  expect(
    (stored.records as { id: string }[]).some((record) => record.id === "conversation-pending-ui"),
  ).toBe(false);
});

// --- Library state screenshots (Light/Dark, per browser) ------------------

const LIBRARY_STATES = [
  {
    name: "library-pending-deletion",
    tombstones: [{ id: "conversation-pending-ui", revision: 1, deletedAt: 5 }] as unknown[],
  },
  {
    name: "library-unreadable-warning",
    tombstones: [{ id: "broken", revision: "not-a-number", deletedAt: 1 }] as unknown[],
  },
];

for (const theme of ["light", "dark"] as const) {
  for (const state of LIBRARY_STATES) {
    test(`screenshot ${state.name} (${theme})`, async ({ page }, testInfo) => {
      const payload = {
        envelopeVersion: 3,
        records: [
          libraryRecord("conversation-pending-ui", "session-pending-ui", "Pending deletion"),
          libraryRecord("conversation-kept", "session-kept", "Kept research"),
        ],
        tombstones: state.tombstones,
      };
      await installApiFixtures(page);
      await page.addInitScript((raw) => {
        localStorage.setItem("sec_qa_library_v3", raw);
        localStorage.setItem("sec_qa_session_id", "session-pending-ui");
        localStorage.setItem("sec_qa_active_conversation_id", "conversation-pending-ui");
      }, JSON.stringify(payload));
      await page.goto("/");
      await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
      await openLibrary(page);
      await expect(
        page.getByText(/Pending deletion|Deletion pending|deletion state/i).first(),
      ).toBeVisible();
      if (theme === "dark") {
        await page.getByRole("button", { name: /Theme System/ }).click();
        await page.getByRole("menuitemradio", { name: "Dark" }).click();
      }
      await page.waitForTimeout(700);
      await page.screenshot({
        path: `e2e/screenshots/${testInfo.project.name}-${theme}-desktop-1440-${state.name}.png`,
      });
    });
  }
}

test("production Library search stays below the 200ms p95 budget", async ({ page }) => {
  await installApiFixtures(page);
  await page.addInitScript(() => {
    const records = Array.from({ length: 100 }, (_, conversationIndex) => {
      const topic = conversationIndex < 40
        ? "revenue"
        : conversationIndex < 70
          ? "risk"
          : "cash flow";
      return {
      schemaVersion: 4,
      id: `conversation-performance-${conversationIndex}`,
      sessionId: `session-performance-${conversationIndex}`,
      title: `Performance conversation ${conversationIndex}`,
      titleMode: "auto",
      revision: 1,
      createdAt: conversationIndex,
      updatedAt: conversationIndex,
      draft: "",
      tags: [topic],
      notes: [],
      variants: [],
      bookmarkedMessageIds: [],
      messages: Array.from({ length: 100 }, (_, messageIndex) => ({
        id: `message-performance-${conversationIndex}-${messageIndex}`,
        sender: "user",
        text: `Question ${messageIndex} about ${topic} and annual filing evidence`,
      })),
      };
    });
    localStorage.setItem(
      "sec_qa_library_v3",
      JSON.stringify({ envelopeVersion: 4, records, tombstones: [] }),
    );
  });
  await page.goto("/");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  await openLibrary(page);
  const search = page.getByRole("searchbox", { name: "Search saved conversations" });
  const items = page.locator(".library-item");
  await expect(search).toBeVisible();
  await expect(items).toHaveCount(100);

  const expectedCounts = new Map([
    ["revenue", 40],
    ["risk", 30],
    ["cash flow", 30],
  ]);
  for (const query of expectedCounts.keys()) {
    await search.fill(query);
    await expect(items).toHaveCount(expectedCounts.get(query)!);
    expect(new Set(await items.locator(".library-item-title").allTextContents()).size).toBe(expectedCounts.get(query));
  }

  const samples: number[] = [];
  for (let index = 0; index < 100; index += 1) {
    const start = performance.now();
    const query = ["revenue", "risk", "cash flow"][index % 3];
    await search.fill(query);
    await expect(items).toHaveCount(expectedCounts.get(query)!);
    samples.push(performance.now() - start);
  }
  samples.sort((left, right) => left - right);
  const p95 = samples[Math.ceil(samples.length * 0.95) - 1];
  console.log(`[performance] Library search p95=${p95.toFixed(2)}ms (${samples.length} samples)`);
  expect(p95).toBeLessThan(200);
});

test("production composer input stays below the 100ms p95 budget with 200 messages", async ({ page }) => {
  const messages = Array.from({ length: 200 }, (_, index) => ({
    id: `message-render-performance-${index}`,
    sender: index % 2 === 0 ? "user" : "assistant",
    text: index % 2 === 0
      ? `Question ${index} about annual filing evidence`
      : `Grounded answer ${index} with indexed filing evidence.`,
    status: "completed",
  }));
  const record = {
    schemaVersion: 4,
    id: "conversation-render-performance",
    sessionId: "session-render-performance",
    title: "200-message rendering benchmark",
    titleMode: "auto",
    revision: 1,
    createdAt: 1,
    updatedAt: 2,
    draft: "",
    tags: ["performance"],
    notes: [],
    variants: [],
    bookmarkedMessageIds: [],
    messages,
  };
  await installApiFixtures(page);
  await page.addInitScript((raw) => {
    localStorage.setItem("sec_qa_library_v3", raw);
    localStorage.setItem("sec_qa_session_id", "session-render-performance");
    localStorage.setItem("sec_qa_active_conversation_id", "conversation-render-performance");
  }, JSON.stringify({ envelopeVersion: 4, records: [record], tombstones: [] }));
  await page.goto("/?view=conversation");
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  await expect(page.getByRole("article")).toHaveCount(200);

  const samples = await page.evaluate(async () => {
    const input = document.querySelector<HTMLTextAreaElement>("#chat-textarea");
    if (!input) throw new Error("Research composer was not mounted");
    const valueSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
    if (!valueSetter) throw new Error("Textarea value setter was not found");
    const durations: number[] = [];
    for (let index = 0; index < 100; index += 1) {
      const start = performance.now();
      valueSetter.call(input, `Performance sample ${index}`);
      input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText" }));
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
      durations.push(performance.now() - start);
    }
    return durations;
  });
  samples.sort((left, right) => left - right);
  const p95 = samples[Math.ceil(samples.length * 0.95) - 1];
  console.log(`[performance] 200-message composer input p95=${p95.toFixed(2)}ms (${samples.length} samples)`);
  expect(p95).toBeLessThan(100);
});
