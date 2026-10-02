import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const routes = [
  "chat", "research", "documents", "search", "collections", "retrieval", "models",
  "pipeline", "reranker", "evaluation", "analytics", "datasets", "settings", "logs",
] as const;
const compactRoutes = new Set(["research", "documents", "search", "collections", "retrieval", "evaluation", "analytics", "logs"]);
const origin = "http://localhost:4177";
const api = "http://127.0.0.1:8778";
const publicApi = "http://127.0.0.1:8777";

async function prepare(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/*", async route => {
    if ([origin, api, publicApi].includes(new URL(route.request().url()).origin)) await route.continue();
    else await route.abort();
  });
  await page.goto("/chat");
}

async function inspect(page: Page, route: string, width: number, height: number, locale: "en" | "vi") {
  await page.setViewportSize({ width, height });
  await page.evaluate(lang => {
    localStorage.setItem("theme", "dark");
    localStorage.setItem("sec_qa_locale", lang);
  }, locale);
  await page.goto(`/${route}`);
  await expect(page.getByRole("main", { name: "Research workspace" })).toBeVisible();
  await page.evaluate(async () => { await document.fonts.ready; });
  const geometry = await page.evaluate(() => {
    const root = document.documentElement;
    const visible = (element: Element) => {
      const box = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return box.width > 0 && box.height > 0 && style.visibility !== "hidden" && style.display !== "none";
    };
    const clipped = [...document.querySelectorAll("button,h1,h2,h3,[role='tab'],summary")]
      .filter(visible)
      .filter(node => node.scrollWidth > node.clientWidth + 2 || node.scrollHeight > node.clientHeight + 2)
      .slice(0, 12)
      .map(node => ({ tag: node.tagName, text: node.textContent?.trim().slice(0, 80) }));
    const dialogs = [...document.querySelectorAll("[role='dialog'],[role='listbox']")].filter(visible)
      .map(node => { const b = node.getBoundingClientRect(); return { x: b.x, y: b.y, right: b.right, bottom: b.bottom }; });
    return {
      bodyOverflow: document.body.scrollWidth - document.body.clientWidth,
      rootOverflow: root.scrollWidth - root.clientWidth,
      clipped, dialogs,
    };
  });
  const label = `${route}-${width}-${locale}`;
  await page.screenshot({ path: test.info().outputPath(`${label}.png`), animations: "disabled", fullPage: true });
  await test.info().attach(`${label}-geometry`, {
    body: JSON.stringify(geometry), contentType: "application/json",
  });
  expect(geometry.bodyOverflow, label).toBe(0);
  expect(geometry.rootOverflow, label).toBe(0);
  expect(geometry.dialogs.every(box => box.x >= 0 && box.right <= width && box.y >= 0 && box.bottom <= height), label).toBe(true);
  return geometry;
}

for (const route of routes) {
  test(`${route} dark EN/VI desktop and phone layout`, async ({ page }) => {
    await prepare(page);
    for (const locale of ["en", "vi"] as const) {
      for (const [width, height] of [[1440, 900], [390, 844]] as const) {
        const geometry = await inspect(page, route, width, height, locale);
        // A clipped candidate needs screenshot and ancestor inspection before it is called a defect.
        if (geometry.clipped.length) console.log(`${route} ${width} ${locale} clipped candidates: ${JSON.stringify(geometry.clipped)}`);
      }
      if (compactRoutes.has(route)) await inspect(page, route, 1024, 768, locale);
    }
  });
}

test("representative dark desktop and phone accessibility", async ({ page }) => {
  await prepare(page);
  for (const [route, width, height, locale] of [
    ["chat", 1440, 900, "en"], ["search", 390, 844, "vi"],
    ["collections", 390, 844, "vi"], ["evaluation", 1440, 900, "en"],
  ] as const) {
    await inspect(page, route, width, height, locale);
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(result.violations, `${route} ${width} ${locale}`).toEqual([]);
  }
});

test("phone composer keeps its full prompt and a centered deep research switch", async ({ page }) => {
  await prepare(page);
  await inspect(page, "chat", 390, 844, "vi");
  const textarea = page.locator("#chat-textarea");
  const promptHeight = await textarea.evaluate(node => {
    const field = node as HTMLTextAreaElement;
    const style = getComputedStyle(node);
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d")!;
    context.font = style.font;
    const innerWidth = field.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    const wraps = context.measureText(field.placeholder).width > innerWidth;
    return {
      wraps,
      actual: field.clientHeight,
      // Reserve one extra line for browser placeholder wrapping/antialiasing.
      required: (wraps ? 3 : 1) * parseFloat(style.lineHeight)
        + parseFloat(style.paddingTop) + parseFloat(style.paddingBottom),
    };
  });
  expect(promptHeight.wraps).toBe(true);
  expect(promptHeight.actual).toBeGreaterThanOrEqual(promptHeight.required - 1);
  const switchControl = page.getByRole("switch", { name: "Bật hoặc tắt câu trả lời so sánh" });
  const track = switchControl.locator("[data-switch-track]");
  await expect(track).toBeVisible();
  expect(await track.evaluate(node => {
    const box = node.getBoundingClientRect();
    const parent = node.parentElement!.getBoundingClientRect();
    return Math.abs(box.width - 28) < 1 && Math.abs(box.height - 16) < 1
      && Math.abs((box.x + box.width / 2) - (parent.x + parent.width / 2)) < 1
      && Math.abs((box.y + box.height / 2) - (parent.y + parent.height / 2)) < 1;
  })).toBe(true);
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(result.violations).toEqual([]);
});
