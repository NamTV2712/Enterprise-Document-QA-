import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import {
  NAVIGATION_LAYOUT_STORAGE_KEY,
  useNavigationLayout,
} from "./useNavigationLayout";

describe("useNavigationLayout", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("defaults to expanded and persists only the allowed raw values", () => {
    const { result } = renderHook(() => useNavigationLayout());

    expect(result.current.layout).toBe("expanded");
    act(() => result.current.setLayout("compact"));
    expect(result.current.layout).toBe("compact");
    expect(localStorage.getItem(NAVIGATION_LAYOUT_STORAGE_KEY)).toBe("compact");

    act(() => result.current.toggleLayout());
    expect(result.current.layout).toBe("expanded");
    expect(localStorage.getItem(NAVIGATION_LAYOUT_STORAGE_KEY)).toBe("expanded");
  });

  test("ignores malformed stored and cross-tab values", () => {
    localStorage.setItem(NAVIGATION_LAYOUT_STORAGE_KEY, "rail");
    const { result } = renderHook(() => useNavigationLayout());
    expect(result.current.layout).toBe("expanded");

    act(() => {
      window.dispatchEvent(new StorageEvent("storage", {
        key: NAVIGATION_LAYOUT_STORAGE_KEY,
        newValue: "compact",
        storageArea: localStorage,
      }));
    });
    expect(result.current.layout).toBe("compact");

    act(() => {
      window.dispatchEvent(new StorageEvent("storage", {
        key: NAVIGATION_LAYOUT_STORAGE_KEY,
        newValue: "rail",
        storageArea: localStorage,
      }));
    });
    expect(result.current.layout).toBe("compact");
  });

  test("keeps an in-memory preference when storage fails", () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    const { result } = renderHook(() => useNavigationLayout());

    act(() => result.current.setLayout("compact"));
    expect(result.current.layout).toBe("compact");
    setItem.mockRestore();
  });
});
