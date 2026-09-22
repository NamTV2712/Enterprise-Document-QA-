import { act, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { useReaderSession } from "./useReaderSession";

describe("useReaderSession", () => {
  test("increments generation and invalidates the previous target", () => {
    const { result } = renderHook(() => useReaderSession());
    let first = 0;
    act(() => { first = result.current.select({ documentId: "doc-1", sourceKey: "source-1" }); });
    const firstSignal = result.current.snapshot?.signal;
    let second = 0;
    act(() => { second = result.current.select({ documentId: "doc-2", sourceKey: "source-2" }); });

    expect(second).toBeGreaterThan(first);
    expect(firstSignal?.aborted).toBe(true);
    expect(result.current.isCurrent(first, { documentId: "doc-1", sourceKey: "source-1" })).toBe(false);
    expect(result.current.isCurrent(second, { documentId: "doc-2", sourceKey: "source-2" })).toBe(true);
  });

  test("reuses an unchanged target and clears it explicitly", () => {
    const { result } = renderHook(() => useReaderSession());
    let first = 0;
    act(() => { first = result.current.select({ documentId: "doc-1", sourceKey: "source-1" }); });
    let same = 0;
    act(() => { same = result.current.select({ documentId: "doc-1", sourceKey: "source-1" }); });
    expect(same).toBe(first);
    act(() => { result.current.clear(); });
    expect(result.current.snapshot).toBeNull();
    expect(result.current.isCurrent(first)).toBe(false);
  });

  test("representation switches abort the old reader load before the new one becomes current", () => {
    const { result } = renderHook(() => useReaderSession());
    let structuredGeneration = 0;
    act(() => {
      structuredGeneration = result.current.select({ documentId: "doc-1", sourceKey: "chunk-1", representation: "structured" });
    });
    const structuredSignal = result.current.snapshot?.signal;
    let normalizedGeneration = 0;
    act(() => {
      normalizedGeneration = result.current.select({ documentId: "doc-1", sourceKey: "chunk-1", representation: "normalized" });
    });

    expect(structuredSignal?.aborted).toBe(true);
    expect(result.current.isCurrent(structuredGeneration)).toBe(false);
    expect(result.current.isCurrent(normalizedGeneration, { documentId: "doc-1", sourceKey: "chunk-1", representation: "normalized" })).toBe(true);
  });
});
