import type { WorkspaceTarget } from "../types";

/**
 * Presentation modes selected from the actual workbench geometry. These are
 * intentionally separate from route identity and from reader network state.
 */
export type WorkbenchLayoutMode =
  | "four-pane"
  | "context-dock"
  | "contextual-surface"
  | "drawer"
  | "single-surface";

export type ActiveRepresentation = "structured" | "normalized" | "pdf";

export type EvidenceBindingState =
  | "idle"
  | "resolving"
  | "ready"
  | "stale"
  | "unavailable"
  | "error";

export type WorkbenchPane = "sources" | "document";

export type SourceFilter = "all" | "cited" | "saved";

export type DocumentContextTab = "evidence" | "metadata" | "notes";

/** The existing identity-bearing handoff contract; no second target shape. */
export type WorkbenchTarget = WorkspaceTarget;

export interface WorkbenchPanePreferencesV1 {
  schemaVersion: 1;
  sourcesWidth: number;
  documentWidth: number;
  sourcesCollapsed: boolean;
  documentCollapsed: boolean;
}

export const WORKBENCH_PANE_PREFERENCES_STORAGE_KEY = "sec_qa_workbench_panes_v1";
export const LEGACY_CONTEXT_RAIL_WIDTH_STORAGE_KEY = "sec_qa_context_rail_width_v1";
export const WORKBENCH_PANE_PREFERENCES_SCHEMA_VERSION = 1 as const;

export const WORKBENCH_PANE_LIMITS = {
  sources: { min: 300, default: 332, max: 400 },
  document: { min: 272, default: 400, max: 560 },
} as const;

/**
 * Layout thresholds are content requirements, not viewport-only breakpoints.
 * `containerWidth` includes navigation; callers provide the actual measured
 * navigation width for the current layout.
 */
export const WORKBENCH_LAYOUT_CONSTRAINTS = {
  researchMinWidth: 430,
  fourPaneResearchMinWidth: 430,
  contextDockMinContentWidth: 1224,
  contextualSurfaceMinWidth: 1024,
  drawerMinWidth: 640,
  fourPaneMinHeight: 720,
  contextualMinHeight: 620,
  splitterWidth: 8,
} as const;

export const DEFAULT_WORKBENCH_PANE_PREFERENCES: WorkbenchPanePreferencesV1 = {
  schemaVersion: WORKBENCH_PANE_PREFERENCES_SCHEMA_VERSION,
  sourcesWidth: WORKBENCH_PANE_LIMITS.sources.default,
  documentWidth: WORKBENCH_PANE_LIMITS.document.default,
  sourcesCollapsed: false,
  documentCollapsed: false,
};

export interface WorkbenchGeometry {
  /** The measured workbench/container width, including navigation. */
  containerWidth: number;
  /** The measured usable workbench/container height. */
  containerHeight: number;
  /** The measured navigation width, or zero when navigation is a drawer. */
  navigationWidth: number;
  /** Current requested pane widths; defaults are used when omitted. */
  sourcesWidth?: number;
  documentWidth?: number;
  /** Width of each visual separator between flexible panes. */
  separatorWidth?: number;
}

function finiteOr(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function nonNegative(value: unknown): number {
  return Math.max(0, finiteOr(value, 0));
}

export function clampPaneWidth(pane: WorkbenchPane, value: number): number {
  const limits = WORKBENCH_PANE_LIMITS[pane];
  const candidate = finiteOr(value, limits.default);
  return Math.min(limits.max, Math.max(limits.min, Math.round(candidate)));
}

export function getWorkbenchContentWidth(geometry: WorkbenchGeometry): number {
  return Math.max(
    0,
    nonNegative(geometry.containerWidth) - nonNegative(geometry.navigationWidth),
  );
}

function validBoolean(value: unknown): value is boolean {
  return typeof value === "boolean";
}

/**
 * Normalize only a known V1 payload. A known schema with finite widths is
 * clamped; malformed and future schemas return null so the caller can keep
 * the raw storage value untouched and fall back safely.
 */
export function normalizeWorkbenchPanePreferences(
  value: unknown,
): WorkbenchPanePreferencesV1 | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<WorkbenchPanePreferencesV1>;
  if (
    candidate.schemaVersion !== WORKBENCH_PANE_PREFERENCES_SCHEMA_VERSION ||
    typeof candidate.sourcesWidth !== "number" ||
    !Number.isFinite(candidate.sourcesWidth) ||
    typeof candidate.documentWidth !== "number" ||
    !Number.isFinite(candidate.documentWidth) ||
    !validBoolean(candidate.sourcesCollapsed) ||
    !validBoolean(candidate.documentCollapsed)
  ) {
    return null;
  }

  return {
    schemaVersion: WORKBENCH_PANE_PREFERENCES_SCHEMA_VERSION,
    sourcesWidth: clampPaneWidth("sources", candidate.sourcesWidth),
    documentWidth: clampPaneWidth("document", candidate.documentWidth),
    sourcesCollapsed: candidate.sourcesCollapsed,
    documentCollapsed: candidate.documentCollapsed,
  };
}

export function parseWorkbenchPanePreferences(
  raw: string | null,
): WorkbenchPanePreferencesV1 | null {
  if (!raw) return null;
  try {
    return normalizeWorkbenchPanePreferences(JSON.parse(raw) as unknown);
  } catch {
    return null;
  }
}

export function serializeWorkbenchPanePreferences(
  preferences: WorkbenchPanePreferencesV1,
): string {
  const normalized = normalizeWorkbenchPanePreferences(preferences);
  return JSON.stringify(normalized ?? DEFAULT_WORKBENCH_PANE_PREFERENCES);
}

function resolveStorage(storage?: Storage | null): Storage | null {
  if (storage !== undefined) return storage;
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readLegacySourcesWidth(storage: Storage): number | null {
  try {
    const raw = storage.getItem(LEGACY_CONTEXT_RAIL_WIDTH_STORAGE_KEY);
    if (raw === null || raw.trim() === "") return null;
    const value = Number(raw);
    return Number.isFinite(value) ? clampPaneWidth("sources", value) : null;
  } catch {
    return null;
  }
}

function tryWritePreferences(
  storage: Storage | null,
  preferences: WorkbenchPanePreferencesV1,
): void {
  if (!storage) return;
  try {
    storage.setItem(
      WORKBENCH_PANE_PREFERENCES_STORAGE_KEY,
      serializeWorkbenchPanePreferences(preferences),
    );
  } catch {
    // Layout preferences are optional and must never block research or reading.
  }
}

/**
 * Read V1 preferences and perform the one-way, non-destructive old rail-width
 * migration. A malformed or future V5 payload is not overwritten.
 */
export function readWorkbenchPanePreferences(
  storage?: Storage | null,
): WorkbenchPanePreferencesV1 {
  const resolved = resolveStorage(storage);
  if (!resolved) return { ...DEFAULT_WORKBENCH_PANE_PREFERENCES };

  try {
    const currentRaw = resolved.getItem(WORKBENCH_PANE_PREFERENCES_STORAGE_KEY);
    if (currentRaw !== null) {
      return parseWorkbenchPanePreferences(currentRaw) ?? {
        ...DEFAULT_WORKBENCH_PANE_PREFERENCES,
      };
    }
  } catch {
    return { ...DEFAULT_WORKBENCH_PANE_PREFERENCES };
  }

  const legacySourcesWidth = readLegacySourcesWidth(resolved);
  if (legacySourcesWidth === null) {
    return { ...DEFAULT_WORKBENCH_PANE_PREFERENCES };
  }

  const migrated = {
    ...DEFAULT_WORKBENCH_PANE_PREFERENCES,
    sourcesWidth: legacySourcesWidth,
  };
  tryWritePreferences(resolved, migrated);
  return migrated;
}

export function writeWorkbenchPanePreferences(
  preferences: WorkbenchPanePreferencesV1,
  storage?: Storage | null,
): boolean {
  const resolved = resolveStorage(storage);
  if (!resolved) return false;
  try {
    resolved.setItem(
      WORKBENCH_PANE_PREFERENCES_STORAGE_KEY,
      serializeWorkbenchPanePreferences(preferences),
    );
    return true;
  } catch {
    return false;
  }
}

/**
 * Effective pane widths for the measured width.
 *
 * The reference workbench keeps the retrieved-sources rail at its preferred
 * width and lets the document viewer narrow toward its own minimum before the
 * layout falls back to a dock, so the same composition is available from the
 * ~1254px reference width instead of only on very wide desktops.
 */
export function deriveEffectivePaneWidths(geometry: {
  containerWidth: number;
  navigationWidth: number;
  sourcesWidth?: number;
  documentWidth?: number;
  separatorWidth?: number;
}): { sourcesWidth: number; documentWidth: number } {
  const contentWidth = Math.max(
    0,
    nonNegative(geometry.containerWidth) - nonNegative(geometry.navigationWidth),
  );
  const sourcesWidth = clampPaneWidth(
    "sources",
    finiteOr(geometry.sourcesWidth, WORKBENCH_PANE_LIMITS.sources.default),
  );
  const preferredDocument = clampPaneWidth(
    "document",
    finiteOr(geometry.documentWidth, WORKBENCH_PANE_LIMITS.document.default),
  );
  const separatorWidth = nonNegative(
    finiteOr(geometry.separatorWidth, WORKBENCH_LAYOUT_CONSTRAINTS.splitterWidth),
  );
  const roomForDocument =
    contentWidth -
    WORKBENCH_LAYOUT_CONSTRAINTS.researchMinWidth -
    sourcesWidth -
    separatorWidth * 2;
  return {
    sourcesWidth,
    documentWidth: clampPaneWidth("document", Math.min(preferredDocument, roomForDocument)),
  };
}

/**
 * Decide the presentation mode from measured container geometry and current
 * pane widths. The four-pane check uses the width the panes can actually take
 * (see ``deriveEffectivePaneWidths``), so a narrow desktop keeps the
 * reference composition instead of dropping to a contextual overlay.
 */
export function deriveWorkbenchLayoutMode(
  geometry: WorkbenchGeometry,
): WorkbenchLayoutMode {
  const containerWidth = nonNegative(geometry.containerWidth);
  const containerHeight = nonNegative(geometry.containerHeight);
  const contentWidth = getWorkbenchContentWidth(geometry);
  const { sourcesWidth, documentWidth } = deriveEffectivePaneWidths(geometry);
  const separatorWidth = nonNegative(
    finiteOr(geometry.separatorWidth, WORKBENCH_LAYOUT_CONSTRAINTS.splitterWidth),
  );
  const fourPaneMinimum =
    WORKBENCH_LAYOUT_CONSTRAINTS.fourPaneResearchMinWidth +
    sourcesWidth +
    documentWidth +
    separatorWidth * 2;

  if (containerWidth < WORKBENCH_LAYOUT_CONSTRAINTS.drawerMinWidth) {
    return "single-surface";
  }
  // At the exact threshold there is no spare width for an inline contextual
  // surface once its border, close control, and reader content are mounted.
  // Keep 1024px in the drawer contract; 1025px is the first inline width.
  if (containerWidth <= WORKBENCH_LAYOUT_CONSTRAINTS.contextualSurfaceMinWidth) {
    return "drawer";
  }
  if (containerHeight < WORKBENCH_LAYOUT_CONSTRAINTS.contextualMinHeight) {
    return "contextual-surface";
  }
  if (
    containerHeight >= WORKBENCH_LAYOUT_CONSTRAINTS.fourPaneMinHeight &&
    contentWidth >= fourPaneMinimum
  ) {
    return "four-pane";
  }
  if (
    contentWidth >= WORKBENCH_LAYOUT_CONSTRAINTS.contextDockMinContentWidth
  ) {
    return "context-dock";
  }
  return "contextual-surface";
}

export function getFlexibleResearchWidth(
  geometry: WorkbenchGeometry,
): number {
  const contentWidth = getWorkbenchContentWidth(geometry);
  const sourcesWidth = clampPaneWidth(
    "sources",
    finiteOr(geometry.sourcesWidth, WORKBENCH_PANE_LIMITS.sources.default),
  );
  const documentWidth = clampPaneWidth(
    "document",
    finiteOr(geometry.documentWidth, WORKBENCH_PANE_LIMITS.document.default),
  );
  const separatorWidth = nonNegative(
    finiteOr(geometry.separatorWidth, WORKBENCH_LAYOUT_CONSTRAINTS.splitterWidth),
  );
  return Math.max(0, contentWidth - sourcesWidth - documentWidth - separatorWidth * 2);
}
