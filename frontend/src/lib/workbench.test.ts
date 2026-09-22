import { beforeEach, describe, expect, test } from "vitest";
import {
  DEFAULT_WORKBENCH_PANE_PREFERENCES,
  LEGACY_CONTEXT_RAIL_WIDTH_STORAGE_KEY,
  WORKBENCH_PANE_PREFERENCES_STORAGE_KEY,
  clampPaneWidth,
  deriveEffectivePaneWidths,
  deriveWorkbenchLayoutMode,
  getFlexibleResearchWidth,
  getWorkbenchContentWidth,
  normalizeWorkbenchPanePreferences,
  readWorkbenchPanePreferences,
} from "./workbench";

describe("workbench geometry and preference primitives", () => {
  beforeEach(() => localStorage.clear());

  test("keeps pane widths inside the reference composition contract", () => {
    expect(clampPaneWidth("sources", 1)).toBe(300);
    expect(clampPaneWidth("sources", 999)).toBe(400);
    expect(clampPaneWidth("document", 271)).toBe(272);
    expect(clampPaneWidth("document", 560.4)).toBe(560);
    expect(normalizeWorkbenchPanePreferences({
      schemaVersion: 1,
      sourcesWidth: 500,
      documentWidth: 100,
      sourcesCollapsed: false,
      documentCollapsed: true,
    })).toEqual({
      schemaVersion: 1,
      sourcesWidth: 400,
      documentWidth: 272,
      sourcesCollapsed: false,
      documentCollapsed: true,
    });
  });

  test("rejects malformed and future preference schemas without rewriting them", () => {
    expect(normalizeWorkbenchPanePreferences(null)).toBeNull();
    expect(normalizeWorkbenchPanePreferences({ ...DEFAULT_WORKBENCH_PANE_PREFERENCES, schemaVersion: 2 })).toBeNull();
    expect(normalizeWorkbenchPanePreferences({ ...DEFAULT_WORKBENCH_PANE_PREFERENCES, sourcesWidth: "wide" })).toBeNull();

    const future = JSON.stringify({ ...DEFAULT_WORKBENCH_PANE_PREFERENCES, schemaVersion: 2 });
    localStorage.setItem(WORKBENCH_PANE_PREFERENCES_STORAGE_KEY, future);
    localStorage.setItem(LEGACY_CONTEXT_RAIL_WIDTH_STORAGE_KEY, "340");
    expect(readWorkbenchPanePreferences(localStorage)).toEqual(DEFAULT_WORKBENCH_PANE_PREFERENCES);
    expect(localStorage.getItem(WORKBENCH_PANE_PREFERENCES_STORAGE_KEY)).toBe(future);
  });

  test("migrates only the old rail width and leaves the old key intact", () => {
    localStorage.setItem(LEGACY_CONTEXT_RAIL_WIDTH_STORAGE_KEY, "512");

    expect(readWorkbenchPanePreferences(localStorage)).toEqual({
      ...DEFAULT_WORKBENCH_PANE_PREFERENCES,
      sourcesWidth: 400,
    });
    expect(localStorage.getItem(LEGACY_CONTEXT_RAIL_WIDTH_STORAGE_KEY)).toBe("512");
    expect(JSON.parse(localStorage.getItem(WORKBENCH_PANE_PREFERENCES_STORAGE_KEY) ?? "{}"))
      .toMatchObject({ schemaVersion: 1, sourcesWidth: 400 });
  });

  test("uses actual container geometry for every planned layout mode", () => {
    const base = { sourcesWidth: 332, documentWidth: 400 };
    // The authoritative references show the four-pane workbench from the
    // 1254px reference width, so the composition is available there and stays
    // available on wider desktops.
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1254, containerHeight: 856, navigationWidth: 158 })).toBe("four-pane");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1280, containerHeight: 856, navigationWidth: 160 })).toBe("four-pane");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1440, containerHeight: 900, navigationWidth: 56 })).toBe("four-pane");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1920, containerHeight: 1080, navigationWidth: 216 })).toBe("four-pane");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1366, containerHeight: 768, navigationWidth: 56 })).toBe("four-pane");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1100, containerHeight: 800, navigationWidth: 158 })).toBe("contextual-surface");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1024, containerHeight: 768, navigationWidth: 0 })).toBe("drawer");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 768, containerHeight: 900, navigationWidth: 0 })).toBe("drawer");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 390, containerHeight: 844, navigationWidth: 0 })).toBe("single-surface");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1920, containerHeight: 600, navigationWidth: 216 })).toBe("contextual-surface");
    expect(deriveWorkbenchLayoutMode({ ...base, containerWidth: 1920, containerHeight: 700, navigationWidth: 216 })).toBe("context-dock");
  });

  test("shrinks the document pane to fit before changing the layout mode", () => {
    const geometry = {
      containerWidth: 1254,
      navigationWidth: 158,
      containerHeight: 856,
      sourcesWidth: 332,
      documentWidth: 560,
    };
    const effective = deriveEffectivePaneWidths(geometry);

    // Sources keep their preferred width; the document pane narrows into the
    // remaining room and never below its own minimum.
    expect(effective.sourcesWidth).toBe(332);
    expect(effective.documentWidth).toBe(1254 - 158 - 430 - 332 - 16);
    expect(effective.documentWidth).toBeGreaterThanOrEqual(272);
    expect(deriveWorkbenchLayoutMode(geometry)).toBe("four-pane");
  });

  test("reports remaining width instead of assuming a viewport breakpoint", () => {
    const geometry = {
      containerWidth: 1440,
      containerHeight: 900,
      navigationWidth: 56,
      sourcesWidth: 304,
      documentWidth: 440,
    };
    expect(getWorkbenchContentWidth(geometry)).toBe(1384);
    expect(getFlexibleResearchWidth(geometry)).toBe(624);
    expect(getWorkbenchContentWidth({ ...geometry, navigationWidth: 216 })).toBe(1224);
  });
});
