import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import {
  DEFAULT_WORKBENCH_PANE_PREFERENCES,
  WORKBENCH_PANE_PREFERENCES_STORAGE_KEY,
} from "../lib/workbench";
import { useWorkbenchPreferences } from "./useWorkbenchPreferences";

describe("useWorkbenchPreferences", () => {
  beforeEach(() => localStorage.clear());

  test("keeps layout changes in the V5 preference envelope", () => {
    const { result } = renderHook(() => useWorkbenchPreferences());

    expect(result.current.preferences).toEqual(DEFAULT_WORKBENCH_PANE_PREFERENCES);
    act(() => {
      result.current.setSourcesWidth(999);
      result.current.setDocumentWidth(399);
      result.current.setSourcesCollapsed(true);
    });

    expect(result.current.preferences).toMatchObject({
      sourcesWidth: 400,
      documentWidth: 399,
      sourcesCollapsed: true,
      documentCollapsed: false,
    });
    expect(JSON.parse(localStorage.getItem(WORKBENCH_PANE_PREFERENCES_STORAGE_KEY) ?? "{}"))
      .toEqual(result.current.preferences);
  });

  test("accepts valid cross-tab updates and ignores malformed/future payloads", () => {
    const { result } = renderHook(() => useWorkbenchPreferences());
    const dispatchStorage = (newValue: string | null) => {
      window.dispatchEvent(new StorageEvent("storage", {
        key: WORKBENCH_PANE_PREFERENCES_STORAGE_KEY,
        newValue,
        storageArea: localStorage,
      }));
    };

    act(() => dispatchStorage(JSON.stringify({
      ...DEFAULT_WORKBENCH_PANE_PREFERENCES,
      sourcesWidth: 350,
      documentCollapsed: true,
    })));
    expect(result.current.preferences).toMatchObject({ sourcesWidth: 350, documentCollapsed: true });

    act(() => dispatchStorage("not-json"));
    expect(result.current.preferences).toMatchObject({ sourcesWidth: 350, documentCollapsed: true });

    act(() => dispatchStorage(JSON.stringify({
      ...DEFAULT_WORKBENCH_PANE_PREFERENCES,
      schemaVersion: 99,
    })));
    expect(result.current.preferences).toMatchObject({ sourcesWidth: 350, documentCollapsed: true });

    act(() => dispatchStorage(null));
    expect(result.current.preferences).toEqual(DEFAULT_WORKBENCH_PANE_PREFERENCES);
  });

  test("reset restores defaults and storage failures keep the tab usable", () => {
    const { result } = renderHook(() => useWorkbenchPreferences());
    act(() => result.current.commit({ sourcesWidth: 320, documentCollapsed: true }));
    expect(result.current.sourcesWidth).toBe(320);
    expect(result.current.documentCollapsed).toBe(true);

    act(() => result.current.reset());
    expect(result.current.preferences).toEqual(DEFAULT_WORKBENCH_PANE_PREFERENCES);

    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    try {
      act(() => result.current.setDocumentWidth(560));
      expect(result.current.documentWidth).toBe(560);
    } finally {
      setItem.mockRestore();
    }
  });
});
