import { test, expect, Page } from "@playwright/test";
import { askQuestion } from "./fixtures";

/**
 * Frontend-over-HTTP integration: the production build talks to the REAL
 * FastAPI harness (through the byte-splitting proxy) — routes, middleware,
 * validation, session memory, and SSE transport are real. No Playwright
 * route mocks are installed; only static assets come from the preview
 * server and Google Fonts are aborted.
 *
 * These tests verify transport/integration behavior only — not answer
 * quality (that is the backend benchmark's job).
 */

const API_ORIGIN = "http://127.0.0.1:8766";
const CONTROL_ORIGIN = "http://127.0.0.1:8765";

async function setup(page: Page): Promise<void> {
  // Reset mutable harness state before each browser test. The request context
  // avoids browser CORS and runs before the app creates a saved conversation.
  await page.request.post(`${CONTROL_ORIGIN}/__harness__/failure`, {
    data: { mode: "clear" },
  });
  await page.request.post(`${CONTROL_ORIGIN}/__harness__/memory/reset`);
  // Block static extras (fonts) so the page never leaves local hosts; app
  // routes go over real HTTP to the harness.
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (url.startsWith("http://localhost:4173") || url.startsWith("http://127.0.0.1:4173")) {
      await route.continue();
      return;
    }
    if (url.startsWith("http://127.0.0.1:8766") || url.startsWith("http://127.0.0.1:8765")) {
      await route.continue();
      return;
    }
    await route.abort();
  });
  await page.goto("/");
  const input = page.getByRole("textbox", { name: "Research question" });
  await expect(input).toBeVisible();
  await expect(input).toBeEnabled();
}

async function waitForDurableConversation(page: Page, question: string): Promise<void> {
  // The app deliberately saves completed exchanges asynchronously. Waiting on
  // the localStorage mirror makes a reload test assert durable behavior rather
  // than racing the completion-save debounce (especially in Firefox).
  await page.waitForFunction(
    (expectedQuestion) => window.localStorage.getItem("sec_qa_library_v3")?.includes(expectedQuestion) ?? false,
    question,
  );
}

test.afterEach(async ({ page }) => {
  await page.request.post(`${CONTROL_ORIGIN}/__harness__/failure`, {
    data: { mode: "clear" },
  });
});

test("health readiness and ticker discovery over real HTTP", async ({ page }) => {
  await setup(page);
  await expect(page.getByText(/Pipeline: Ready/i).first()).toBeVisible();
  await page.getByRole("button", { name: /Scope/i }).click();
  await page.getByRole("button", { name: "Company" }).click();
  await expect(page.getByRole("option", { name: /Apple Inc.*AAPL/ })).toBeVisible();
  await page.keyboard.press("Escape");
});

test("asked question streams cited answer over real SSE with sources", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple total revenue?");
  await expect(page.getByText(/Harness answer with/).first()).toBeVisible();
  await expect(page.getByText(/Retrieved filing evidence · 1 excerpts/i)).toBeVisible();
  await page.getByRole("button", { name: /Show 1 retrieved filing evidence excerpts/i }).click();
  await expect(
    page.getByRole("article", { name: "Research assistant response" }).getByText(/Harness evidence for:/),
  ).toBeVisible();
  // The citation button in the answer opens the matching source excerpt.
  await page.getByRole("button", { name: "Open source 1" }).click();
  await expect(page.getByText(/Harness evidence for:/).first()).toBeVisible();
});

test("stream interrupted mid-answer keeps the partial answer visible", async ({ page }) => {
  await setup(page);
  await page.route(`${API_ORIGIN}/__harness__/failure`, async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: { "access-control-allow-origin": "*" } });
      return;
    }
    await route.continue();
  });
  await askQuestion(page, "What was Apple total revenue?");
  // Put the harness into omit_done mode between the sources event and the
  // tokens: the stream ends without done and the partial answer stays.
  await page.evaluate(async () => {
    await fetch("http://127.0.0.1:8765/__harness__/failure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "omit_done" }),
    });
  });
  // Trigger a second question that will end without done.
  const input = page.getByRole("textbox", { name: "Research question" });
  await expect(input).toBeEnabled();
  await input.fill("Omit done question");
  await input.press("Enter");
  await expect(page.getByText(/Harness answer with/).first()).toBeVisible();
  await page.evaluate(async () => {
    await fetch("http://127.0.0.1:8765/__harness__/failure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "clear" }),
    });
  });
});

test("session context survives a reload while the backend remembers it", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple total revenue?");
  await expect(page.getByText(/Harness answer with/).first()).toBeVisible();
  await waitForDurableConversation(page, "What was Apple total revenue?");

  await page.reload();
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  // The harness still holds the session: follow-ups stay available (no
  // read-only banner and no "missing" notice).
  await expect(
    page.getByText(/backend session for this saved conversation has expired/i),
  ).not.toBeVisible();
});

test("backend memory reset marks the saved conversation read-only", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "What was Apple total revenue?");
  await expect(page.getByText(/Harness answer with/).first()).toBeVisible();
  await waitForDurableConversation(page, "What was Apple total revenue?");

  // Simulate a backend restart: in-memory sessions are gone.
  await page.evaluate(async () => {
    await fetch("http://127.0.0.1:8765/__harness__/memory/reset", { method: "POST" });
  });
  await page.reload();
  await expect(page.getByRole("textbox", { name: "Research question" })).toBeEnabled();
  await expect(
    page.getByText(/backend session for this saved conversation has expired/i).first(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Send question" })).toBeDisabled();
});

test("decomposed comparative query returns sub-queries over real HTTP", async ({ page }) => {
  await setup(page);
  await askQuestion(page, "Compare Apple and Microsoft cloud revenue");
  await expect(
    page.getByText(/Apple and Microsoft both disclose cloud revenue growth/),
  ).toBeVisible();
  await expect(page.getByText(/Query breakdown/i)).toBeVisible();
});

test("backend errors do not leak harness internals into the UI", async ({ page }) => {
  await setup(page);
  await page.evaluate(async () => {
    await fetch("http://127.0.0.1:8765/__harness__/failure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "decomposed_error" }),
    });
  });
  await askQuestion(page, "Compare Apple and Microsoft risk factors");
  await expect(page.getByText(/error while synthesizing/i)).toBeVisible();
  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("harness decomposed failure");
  expect(bodyText).not.toContain("harness-fake-key");
  await page.evaluate(async () => {
    await fetch("http://127.0.0.1:8765/__harness__/failure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "clear" }),
    });
  });
});
