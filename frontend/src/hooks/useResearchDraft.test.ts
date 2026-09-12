import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test } from "vitest";
import { useResearchDraft } from "./useResearchDraft";

describe("useResearchDraft", () => {
  beforeEach(() => localStorage.clear());

  test("keeps every retrieval constraint in one bounded scope snapshot", () => {
    const { result } = renderHook(() => useResearchDraft());

    act(() => {
      result.current.patchScope({ ticker: "AAPL", section: "risk_factors", topK: 24, enableComparative: false });
    });

    expect(result.current.scope).toEqual({
      ticker: "AAPL",
      section: "risk_factors",
      topK: 10,
      enableComparative: false,
    });
  });

  test("allows a scope source to clear filters without resetting unrelated constraints", () => {
    const { result } = renderHook(() => useResearchDraft({ ticker: "MSFT", section: "mdna", topK: 7 }));

    act(() => result.current.patchScope({ ticker: null, section: null }));

    expect(result.current.scope).toMatchObject({ ticker: null, section: null, topK: 7 });
  });

  test("persists scope per conversation and never leaks it to another conversation", async () => {
    const first = renderHook(() => useResearchDraft("conversation-a"));

    act(() => first.result.current.patchScope({ ticker: "AAPL", section: "risk_factors", enableComparative: false }));
    await waitFor(() => {
      expect(localStorage.getItem("sec_qa_research_scope_v1:conversation-a")).toContain("AAPL");
    });
    first.unmount();

    const restored = renderHook(() => useResearchDraft("conversation-a"));
    expect(restored.result.current.scope).toMatchObject({
      ticker: "AAPL",
      section: "risk_factors",
      enableComparative: false,
    });

    const other = renderHook(() => useResearchDraft("conversation-b"));
    expect(other.result.current.scope).toMatchObject({
      ticker: null,
      section: null,
      topK: 5,
      enableComparative: true,
    });
  });
});
