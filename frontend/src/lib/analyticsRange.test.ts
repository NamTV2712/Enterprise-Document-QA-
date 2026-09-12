import { describe, expect, test } from "vitest";
import { getAnalyticsCutoff } from "./analyticsRange";

describe("analytics range boundaries", () => {
  const now = new Date("2026-09-09T12:00:00Z").getTime();

  test("uses a complete 24-hour window rather than one hour", () => {
    expect(getAnalyticsCutoff("24h", now)).toBe(now - 24 * 60 * 60 * 1000);
  });

  test("uses exact seven and thirty day windows and retains all history", () => {
    expect(getAnalyticsCutoff("7", now)).toBe(now - 7 * 24 * 60 * 60 * 1000);
    expect(getAnalyticsCutoff("30", now)).toBe(now - 30 * 24 * 60 * 60 * 1000);
    expect(getAnalyticsCutoff("all", now)).toBe(0);
  });
});
