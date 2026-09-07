import { beforeEach, describe, expect, test } from "vitest";
import {
  clearAnalytics,
  exportAnalytics,
  readAnalyticsEvents,
  recordAnalyticsEvent,
} from "./analyticsStore";

describe("analyticsStore", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("stores metadata without question or answer content", () => {
    recordAnalyticsEvent({ kind: "query_completed", ticker: "AAPL", language: "vi", durationMs: 123 });

    expect(readAnalyticsEvents()).toHaveLength(1);
    expect(readAnalyticsEvents()[0]).toMatchObject({ kind: "query_completed", ticker: "AAPL", language: "vi" });
    const exported = JSON.parse(exportAnalytics()) as { events: Array<Record<string, unknown>> };
    expect(exported.events[0]).not.toHaveProperty("question");
    expect(exported.events[0]).not.toHaveProperty("answer");
    expect(exported.events[0]).not.toHaveProperty("session_id");
  });

  test("can clear local activity without touching conversation storage", () => {
    localStorage.setItem("sec_qa_library_v3", "kept");
    recordAnalyticsEvent({ kind: "feedback", status: "helpful" });
    clearAnalytics();

    expect(readAnalyticsEvents()).toEqual([]);
    expect(localStorage.getItem("sec_qa_library_v3")).toBe("kept");
  });
});
