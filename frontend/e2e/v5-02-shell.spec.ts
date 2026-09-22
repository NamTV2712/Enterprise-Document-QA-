import { test, expect } from "@playwright/test";
import { installApiFixtures } from "./fixtures";

test.describe("V5-02 shell foundation", () => {
  test("keeps the application landmarks and route content inside the measured shell", async ({ page }) => {
    for (const viewport of [
      { width: 1440, height: 900, expectedNavigation: 184, expectedMode: "context-dock" },
      { width: 1920, height: 1080, expectedNavigation: 216, expectedMode: "four-pane" },
    ]) {
      await page.setViewportSize(viewport);
      await installApiFixtures(page);
      await page.goto("/");

      const shell = page.locator("[data-workbench-app='true']");
      const layout = page.locator(".workbench-layout");
      await expect(shell).toBeVisible();
      await expect(layout).toHaveAttribute("data-workbench-measured", "true");
      await expect(layout).toHaveAttribute(
        "data-workbench-navigation-width",
        String(viewport.expectedNavigation),
      );
      await expect(layout).toHaveAttribute("data-workbench-layout-mode", viewport.expectedMode);
      await expect(page.locator("[data-workbench-region='navigation']")).toBeVisible();
      await expect(page.locator("[data-workbench-region='header']")).toBeVisible();
      await expect(page.getByRole("region", { name: "Research" })).toBeVisible();
      await expect(page.getByRole("main", { name: "Research workspace" })).toBeVisible();

      const geometry = await page.evaluate(() => {
        const shellRect = document.querySelector<HTMLElement>("[data-workbench-app]")?.getBoundingClientRect();
        const mainRect = document.querySelector<HTMLElement>("main[aria-label='Research workspace']")?.getBoundingClientRect();
        const headerRect = document.querySelector<HTMLElement>("[data-workbench-region='header']")?.getBoundingClientRect();
        return {
          scrollWidth: document.documentElement.scrollWidth,
          viewportWidth: window.innerWidth,
          shellWidth: shellRect?.width ?? 0,
          mainWidth: mainRect?.width ?? 0,
          headerHeight: headerRect?.height ?? 0,
        };
      });
      expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.viewportWidth);
      expect(geometry.shellWidth).toBe(geometry.viewportWidth);
      expect(geometry.mainWidth).toBeGreaterThan(0);
      expect(geometry.headerHeight).toBe(56);

      await page.screenshot({
        path: "e2e/screenshots/v5-02-shell-" + viewport.width + "x" + viewport.height + ".png",
        fullPage: false,
      });

      await page.goto("/?view=search");
      await expect(page.locator("[data-workbench-region='research']")).toBeVisible();
      await expect(page.getByRole("link", { name: "Search", exact: true })).toHaveAttribute(
        "aria-current",
        "page",
      );
    }
  });

  test("preserves compact navigation, theme, locale, and keyboard access", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await installApiFixtures(page);
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.setItem("theme", "dark");
      localStorage.setItem("sec_qa_locale", "vi");
      localStorage.setItem("sec_qa_navigation_layout_v1", "compact");
    });
    await page.reload();

    await expect(page.locator("html")).toHaveClass(/dark/);
    await expect(page.locator("[data-workbench-region='navigation']")).toHaveAttribute(
      "data-navigation-layout",
      "compact",
    );
    await expect(page.getByRole("link", { name: "Nghiên cứu", exact: true })).toBeVisible();
    await expect(page.getByRole("banner")).toHaveAttribute(
      "aria-label",
      "Thanh công cụ workspace",
    );
    await expect(page.getByRole("region", { name: "Nghiên cứu" })).toBeVisible();

    const focusable = page.locator("[data-workbench-region='header'] button:visible").first();
    await focusable.focus();
    await expect(focusable).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).not.toHaveCount(0);
  });
});
