import { test, expect, Page } from "@playwright/test";
import { installApiFixtures, LONG_ANSWER } from "./fixtures";

const LONG_ANSWER_FIRST_LINE = LONG_ANSWER.split("\n")[0];

type Box = {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
};

type LayoutState = {
  viewport: Box;
  sidebar: Box | null;
  primary: Box | null;
  scroller: Box | null;
  composer: Box | null;
  evidenceGrid: Box | null;
  evidence: Box | null;
  overflowWidth: number;
  navigationMode: string | null;
  navigationLayout: string | null;
};

async function readLayout(page: Page): Promise<LayoutState> {
  return page.evaluate(() => {
    const viewport = {
      left: 0,
      top: 0,
      right: window.innerWidth,
      bottom: window.innerHeight,
      width: window.innerWidth,
      height: window.innerHeight,
    };
    return {
      viewport,
      sidebar: box(document.querySelector(".sidebar-shell--desktop")),
      primary: box(document.querySelector(".workspace-primary-column")),
      scroller: box(document.querySelector(".conversation-message-scroll")),
      composer: box(document.querySelector(".composer-shell")),
      evidenceGrid: box(document.querySelector(".workspace-main-grid--with-evidence")),
      evidence: box(document.querySelector(".context-panel")),
      overflowWidth: document.documentElement.scrollWidth,
      navigationMode: document.querySelector(".sidebar-shell")?.classList.contains("sidebar-shell--desktop")
        ? "desktop"
        : null,
      navigationLayout: document.querySelector(".sidebar-shell")?.getAttribute("data-navigation-layout") ?? null,
    } satisfies LayoutState;

    function box(element: Element | null): Box | null {
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      return {
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height,
      };
    }
  });
}

function expectInside(inner: Box | null, outer: Box | null, label: string): void {
  expect(inner, `${label} is present`).not.toBeNull();
  expect(outer, `${label} parent is present`).not.toBeNull();
  expect(inner?.left ?? -1, `${label} left`).toBeGreaterThanOrEqual((outer?.left ?? 0) - 2);
  expect(inner?.right ?? Number.MAX_SAFE_INTEGER, `${label} right`).toBeLessThanOrEqual((outer?.right ?? 0) + 2);
  expect(inner?.top ?? -1, `${label} top`).toBeGreaterThanOrEqual((outer?.top ?? 0) - 2);
  expect(inner?.bottom ?? Number.MAX_SAFE_INTEGER, `${label} bottom`).toBeLessThanOrEqual((outer?.bottom ?? 0) + 2);
}

async function expectHitTest(page: Page, selector: string): Promise<void> {
  await expect.poll(
    () => page.locator(selector).evaluate((element) => {
      const rect = element.getBoundingClientRect();
      const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      return {
        hasSize: rect.width > 0 && rect.height > 0,
        isHit: Boolean(hit && (hit === element || element.contains(hit))),
      };
    }),
    { message: `${selector} should receive its center hit test` },
  ).toEqual({ hasSize: true, isHit: true });
}

async function expectStableGeometry(page: Page, selector: string): Promise<void> {
  await page.waitForFunction((target) => {
    const element = document.querySelector<HTMLElement>(target);
    if (!element) return false;
    const first = element.getBoundingClientRect();
    return new Promise<boolean>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        const second = element.getBoundingClientRect();
        resolve(
          Math.abs(first.left - second.left) < 0.5 &&
          Math.abs(first.top - second.top) < 0.5 &&
          Math.abs(first.width - second.width) < 0.5 &&
          Math.abs(first.height - second.height) < 0.5,
        );
      }));
    });
  }, selector);
}

async function waitForNavigationWidth(page: Page, min: number, max: number): Promise<void> {
  await page.waitForFunction(({ lower, upper }) => {
    const width = document.querySelector<HTMLElement>(".sidebar-shell--desktop")?.getBoundingClientRect().width ?? 0;
    return width >= lower && width <= upper;
  }, { lower: min, upper: max });
}

async function expectConversationGeometry(
  page: Page,
  expectedNavigationLayout: "expanded" | "compact",
): Promise<void> {
  const state = await readLayout(page);
  expect(state.overflowWidth).toBeLessThanOrEqual(state.viewport.width);
  expect(state.navigationMode).toBe("desktop");
  expect(state.navigationLayout).toBe(expectedNavigationLayout);
  expectInside(state.primary, state.viewport, "primary column");
  expectInside(state.scroller, state.primary, "conversation message scroller");
  expectInside(state.composer, state.primary, "conversation composer");
  expect(state.composer?.bottom ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual(state.viewport.bottom + 2);
  expect(state.sidebar?.right ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual((state.primary?.left ?? 0) + 2);
  expectHitTest(page, ".composer-shell #chat-textarea");
}

async function expectMobileConversationGeometry(page: Page): Promise<void> {
  const state = await readLayout(page);
  expect(state.overflowWidth).toBeLessThanOrEqual(state.viewport.width);
  expect(state.navigationMode).toBeNull();
  expectInside(state.primary, state.viewport, "mobile primary column");
  expectInside(state.scroller, state.primary, "mobile conversation message scroller");
  expectInside(state.composer, state.primary, "mobile conversation composer");
  expect(state.composer?.bottom ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual(state.viewport.bottom + 2);
  await expectHitTest(page, ".composer-shell #chat-textarea");
}

async function expectInlineEvidence(
  page: Page,
  expectedNavigationLayout: "expanded" | "compact",
): Promise<void> {
  await expect(page.locator(".context-panel")).toBeVisible();
  await expect(page.locator(".workspace-main-grid--with-evidence")).toHaveCount(1);
  await expect(page.locator(".evidence-drawer-dialog")).toHaveCount(0);
  await expectStableGeometry(page, ".context-panel");
  const state = await readLayout(page);
  await expectConversationGeometry(page, expectedNavigationLayout);
  expectInside(state.evidence, state.viewport, "inline evidence panel");
  expect(state.evidence?.width ?? 0).toBeGreaterThanOrEqual(360 - 1);
  expect(state.evidence?.width ?? 0).toBeLessThanOrEqual(560 + 1);
  expect(state.primary?.right ?? Number.MAX_SAFE_INTEGER).toBeLessThanOrEqual((state.evidence?.left ?? 0) + 2);
  await expectHitTest(page, ".context-panel__close");
}

async function openEvidence(page: Page): Promise<ReturnType<Page["locator"]>> {
  // A viewport transition can finish one modal cleanup microtask after the
  // source citation is visible. Wait for the previous evidence surface to be
  // fully gone before exercising the next open path.
  await expect(page.locator(".evidence-drawer-overlay")).toHaveCount(0);
  await expect(page.locator("#root")).not.toHaveAttribute("inert", "");
  const sourceButton = page.getByRole("button", { name: "Open source 1" }).first();
  await expect(sourceButton).toBeVisible();
  await sourceButton.click();
  await expect(page.locator(".context-panel")).toBeVisible();
  return sourceButton;
}

async function closeEvidence(page: Page, sourceButton: ReturnType<Page["locator"]>): Promise<void> {
  await page.locator(".context-panel__close").click();
  await expect(page.locator(".context-panel")).toHaveCount(0);
  await expect(page.locator(".evidence-drawer-dialog")).toHaveCount(0);
  await expect(page.locator("#root")).not.toHaveAttribute("inert", "");
  await expect(sourceButton).toBeFocused();
}

async function expectDrawerEvidence(page: Page): Promise<void> {
  await expect(page.locator(".evidence-drawer-dialog")).toBeVisible();
  await expect(page.locator(".context-panel")).toBeVisible();
  await expect(page.locator(".workspace-main-grid--with-evidence")).toHaveCount(0);
  await expect(page.locator("#root")).toHaveAttribute("inert", "");
  const dialog = await page.locator(".evidence-drawer-dialog").boundingBox();
  expect(dialog).not.toBeNull();
  expect(dialog?.x ?? -1).toBeGreaterThanOrEqual(0);
  expect((dialog?.x ?? 0) + (dialog?.width ?? Number.MAX_SAFE_INTEGER)).toBeLessThanOrEqual(page.viewportSize()?.width ?? 0);
  await expectHitTest(page, ".context-panel__close");
}

async function loadAnswer(page: Page, theme: "light" | "dark", locale: "en" | "vi"): Promise<void> {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.evaluate(({ nextTheme, nextLocale }) => {
    localStorage.setItem("theme", nextTheme);
    localStorage.setItem("sec_qa_locale", nextLocale);
    localStorage.setItem("sec_qa_navigation_layout_v1", "expanded");
  }, { nextTheme: theme, nextLocale: locale });
  await page.reload();
  // A reload can restore the previous local conversation after its mocked
  // backend session has expired. Start a fresh conversation before exercising
  // the next theme/locale matrix cell so the fixture remains writable.
  const startNewConversation = page.getByRole("button", { name: "Start new conversation", exact: true });
  if (await startNewConversation.isVisible()) {
    await startNewConversation.click();
  }
  const input = page.locator("#chat-textarea");
  await expect(input).toBeVisible();
  await input.fill("What are Apple's main business risks?");
  await input.press("Enter");
  await expect(page.getByText(LONG_ANSWER_FIRST_LINE).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Open source 1" }).first()).toBeVisible();
}

async function runLayoutMatrix(page: Page, theme: "light" | "dark", locale: "en" | "vi"): Promise<void> {
  await loadAnswer(page, theme, locale);

  // A — expanded desktop navigation, evidence closed.
  await expectConversationGeometry(page, "expanded");
  expect((await readLayout(page)).sidebar?.width ?? 0).toBeGreaterThanOrEqual(215);
  expect((await readLayout(page)).sidebar?.width ?? 0).toBeLessThanOrEqual(217);

  // B — compact desktop navigation, evidence closed.
  await page.locator(".sidebar-layout-toggle").click();
  await expect(page.locator(".sidebar-shell--desktop")).toHaveAttribute("data-navigation-layout", "compact");
  await waitForNavigationWidth(page, 55, 57);
  await expectConversationGeometry(page, "compact");
  expect((await readLayout(page)).sidebar?.width ?? 0).toBeGreaterThanOrEqual(55);
  expect((await readLayout(page)).sidebar?.width ?? 0).toBeLessThanOrEqual(57);

  // C — expanded navigation with inline evidence.
  await page.locator(".sidebar-layout-toggle").click();
  await expect(page.locator(".sidebar-shell--desktop")).toHaveAttribute("data-navigation-layout", "expanded");
  await waitForNavigationWidth(page, 215, 217);
  await openEvidence(page);
  await expectInlineEvidence(page, "expanded");
  const firstSource = page.getByRole("button", { name: "Open source 1" }).first();
  await closeEvidence(page, firstSource);

  // D — compact navigation with inline evidence.
  await page.locator(".sidebar-layout-toggle").click();
  await waitForNavigationWidth(page, 55, 57);
  await expect(page.locator(".sidebar-shell--desktop")).toHaveAttribute("data-navigation-layout", "compact");
  await openEvidence(page);
  await expectInlineEvidence(page, "compact");
  await closeEvidence(page, firstSource);

  // E — the remaining-width threshold uses a drawer at 1024px. Transition
  // while open is also covered so a portal cleanup cannot strand inert state.
  await page.locator(".sidebar-layout-toggle").click();
  await waitForNavigationWidth(page, 215, 217);
  await page.setViewportSize({ width: 1024, height: 900 });
  await openEvidence(page);
  await expectDrawerEvidence(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator(".evidence-drawer-dialog")).toHaveCount(0);
  await expectInlineEvidence(page, "expanded");
  await closeEvidence(page, firstSource);

  // F — the navigation drawer is a real modal at phone/tablet width, and the
  // open drawer must clean up when crossing back into the desktop shell.
  await page.setViewportSize({ width: 768, height: 900 });
  await expect(page.locator("#sidebar-toggle")).toBeVisible();
  await expect(page.locator(".sidebar-shell--desktop")).toHaveCount(0);
  await page.locator("#sidebar-toggle").click();
  await expect(page.locator(".sidebar-drawer-dialog")).toBeVisible();
  await expect(page.locator(".sidebar-shell--drawer")).toBeVisible();
  await expect(page.locator("#root")).toHaveAttribute("inert", "");
  await expectHitTest(page, ".sidebar-drawer-close");
  await page.keyboard.press("Escape");
  await expect(page.locator(".sidebar-drawer-dialog")).toHaveCount(0);
  await expect(page.locator("#root")).not.toHaveAttribute("inert", "");
  await expect(page.locator("#sidebar-toggle")).toBeFocused();

  await page.locator("#sidebar-toggle").click();
  await expect(page.locator(".sidebar-drawer-dialog")).toBeVisible();
  await page.setViewportSize({ width: 1024, height: 900 });
  await expect(page.locator(".sidebar-drawer-dialog")).toHaveCount(0);
  await expect(page.locator(".sidebar-shell--desktop")).toBeVisible();
  await expect(page.locator("#root")).not.toHaveAttribute("inert", "");

  // G — evidence remains a drawer at 768px and closes through the same
  // keyboard/focus lifecycle as the 1024px remaining-width mode.
  await page.setViewportSize({ width: 768, height: 900 });
  const mobileSource = await openEvidence(page);
  await expectDrawerEvidence(page);
  await page.keyboard.press("Escape");
  await expect(page.locator(".evidence-drawer-dialog")).toHaveCount(0);
  await expect(page.locator("#root")).not.toHaveAttribute("inert", "");
  await expect(mobileSource).toBeFocused();
  await expectMobileConversationGeometry(page);
}

test.describe("workspace layout matrix", () => {
  test("A-G geometry, hit testing, focus, preferences, and modal cleanup", async ({ page }) => {
    await installApiFixtures(page);
    for (const theme of ["light", "dark"] as const) {
      for (const locale of ["en", "vi"] as const) {
        await runLayoutMatrix(page, theme, locale);
      }
    }
  });
});
