import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DEFAULT_WORKBENCH_PANE_PREFERENCES,
  WORKBENCH_PANE_PREFERENCES_STORAGE_KEY,
  normalizeWorkbenchPanePreferences,
  readWorkbenchPanePreferences,
  writeWorkbenchPanePreferences,
  type WorkbenchPanePreferencesV1,
} from "../lib/workbench";

export type WorkbenchPanePreferencePatch = Partial<
  Pick<
    WorkbenchPanePreferencesV1,
    "sourcesWidth" | "documentWidth" | "sourcesCollapsed" | "documentCollapsed"
  >
>;

export interface WorkbenchPreferencesController {
  preferences: WorkbenchPanePreferencesV1;
  sourcesWidth: number;
  documentWidth: number;
  sourcesCollapsed: boolean;
  documentCollapsed: boolean;
  /** Commit a complete user preference patch to React state and storage. */
  commit: (patch: WorkbenchPanePreferencePatch) => void;
  setSourcesWidth: (width: number) => void;
  setDocumentWidth: (width: number) => void;
  setSourcesCollapsed: (collapsed: boolean) => void;
  setDocumentCollapsed: (collapsed: boolean) => void;
  reset: () => void;
}

function samePreferences(
  left: WorkbenchPanePreferencesV1,
  right: WorkbenchPanePreferencesV1,
): boolean {
  return left.sourcesWidth === right.sourcesWidth &&
    left.documentWidth === right.documentWidth &&
    left.sourcesCollapsed === right.sourcesCollapsed &&
    left.documentCollapsed === right.documentCollapsed;
}

/**
 * Owns only layout preferences. Source content, selected evidence, reader
 * state, search text, and fullscreen state deliberately do not enter storage.
 * Pass a Storage in tests when a non-window store is needed.
 */
export function useWorkbenchPreferences(
  storage?: Storage | null,
): WorkbenchPreferencesController {
  const [preferences, setPreferences] = useState<WorkbenchPanePreferencesV1>(() =>
    readWorkbenchPanePreferences(storage),
  );

  const commit = useCallback(
    (patch: WorkbenchPanePreferencePatch) => {
      setPreferences((current) => {
        const next = normalizeWorkbenchPanePreferences({
          ...current,
          ...patch,
        });
        if (!next || samePreferences(current, next)) return current;
        writeWorkbenchPanePreferences(next, storage);
        return next;
      });
    },
    [storage],
  );

  const setSourcesWidth = useCallback((width: number) => {
    commit({ sourcesWidth: width });
  }, [commit]);
  const setDocumentWidth = useCallback((width: number) => {
    commit({ documentWidth: width });
  }, [commit]);
  const setSourcesCollapsed = useCallback((collapsed: boolean) => {
    commit({ sourcesCollapsed: collapsed });
  }, [commit]);
  const setDocumentCollapsed = useCallback((collapsed: boolean) => {
    commit({ documentCollapsed: collapsed });
  }, [commit]);
  const reset = useCallback(() => {
    setPreferences((current) => {
      const next = { ...DEFAULT_WORKBENCH_PANE_PREFERENCES };
      if (samePreferences(current, next)) return current;
      writeWorkbenchPanePreferences(next, storage);
      return next;
    });
  }, [storage]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    let expectedStorage: Storage | null = storage ?? null;
    if (storage === undefined) {
      try {
        expectedStorage = window.localStorage;
      } catch {
        expectedStorage = null;
      }
    }

    const onStorage = (event: StorageEvent) => {
      if (event.key !== WORKBENCH_PANE_PREFERENCES_STORAGE_KEY) return;
      if (expectedStorage && event.storageArea && event.storageArea !== expectedStorage) return;
      if (event.newValue === null) {
        setPreferences({ ...DEFAULT_WORKBENCH_PANE_PREFERENCES });
        return;
      }
      const parsed = normalizeStoredEvent(event.newValue);
      // Keep malformed/future payloads untouched and preserve the last known
      // in-memory value rather than allowing another tab to erase it.
      if (parsed) setPreferences(parsed);
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [storage]);

  return useMemo(
    () => ({
      preferences,
      sourcesWidth: preferences.sourcesWidth,
      documentWidth: preferences.documentWidth,
      sourcesCollapsed: preferences.sourcesCollapsed,
      documentCollapsed: preferences.documentCollapsed,
      commit,
      setSourcesWidth,
      setDocumentWidth,
      setSourcesCollapsed,
      setDocumentCollapsed,
      reset,
    }),
    [
      commit,
      preferences,
      reset,
      setDocumentCollapsed,
      setDocumentWidth,
      setSourcesCollapsed,
      setSourcesWidth,
    ],
  );
}

function normalizeStoredEvent(raw: string): WorkbenchPanePreferencesV1 | null {
  try {
    return normalizeWorkbenchPanePreferences(JSON.parse(raw) as unknown);
  } catch {
    return null;
  }
}
