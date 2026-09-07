import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { installApiFixtures, askQuestion, openLibrary, LONG_ANSWER, API_ORIGIN } from "./fixtures";

const LONG_ANSWER_FIRST_LINE = LONG_ANSWER.split("\n")[0];

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

  await page.getByRole("button", { name: "Retrieval Lab", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Retrieval Lab" })).toBeVisible();
  await expect(page.getByText("Provider-free")).toBeVisible();

  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Evaluation & experiments" })).toBeVisible();
  await page.getByRole("combobox", { name: "Evaluation mode" }).selectOption("recorded");
  await expect(page.getByRole("heading", { name: "Recorded evaluation contract" })).toBeVisible();

  await page.getByRole("button", { name: "System", exact: true }).click();
  await expect(page.getByRole("heading", { name: "System & provenance" })).toBeVisible();
  await expect(page.getByText("Provider-free tools")).toBeVisible();
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
    .getByRole("button", { name: /Show 2 retrieved filing evidence excerpts/i })
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
  await page.getByRole("tab", { name: /Research/ }).click();
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
  await expect(page.getByRole("button", { name: "Send question" })).toBeDisabled();

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
    const records = Array.from({ length: 100 }, (_, conversationIndex) => ({
      schemaVersion: 4,
      id: `conversation-performance-${conversationIndex}`,
      sessionId: `session-performance-${conversationIndex}`,
      title: `Performance conversation ${conversationIndex}`,
      titleMode: "auto",
      revision: 1,
      createdAt: conversationIndex,
      updatedAt: conversationIndex,
      draft: "",
      tags: ["revenue"],
      notes: [],
      variants: [],
      bookmarkedMessageIds: [],
      messages: Array.from({ length: 100 }, (_, messageIndex) => ({
        id: `message-performance-${conversationIndex}-${messageIndex}`,
        sender: "user",
        text: `Question ${messageIndex} about annual filing evidence and revenue`,
      })),
    }));
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

  for (const query of ["filing evidence", "revenue", "annual filing"]) {
    await search.fill(query);
    await expect(items).toHaveCount(100);
  }

  const samples: number[] = [];
  for (let index = 0; index < 100; index += 1) {
    const start = performance.now();
    await search.fill(index % 2 ? "revenue" : "filing evidence");
    await expect(items).toHaveCount(100);
    samples.push(performance.now() - start);
  }
  samples.sort((left, right) => left - right);
  const p95 = samples[Math.ceil(samples.length * 0.95) - 1];
  console.log(`[performance] Library search p95=${p95.toFixed(2)}ms (${samples.length} samples)`);
  expect(p95).toBeLessThan(200);
});
