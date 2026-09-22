import { describe, expect, test } from "vitest";

import {
  ceilingNote,
  describeDiscoveryError,
  filingYear,
  formatScore,
  itemScore,
  pageRangeLabel,
  primaryHit,
  relativeSearchTime,
  scopeSummary,
  snippetSegments,
  submittableQuery,
  topScore,
  type RecentSearch,
} from "./searchModel";
import { ApiError } from "./api";
import type { DiscoveryGroup, DiscoveryHit, DiscoveryScopeMetadata } from "../types";

const scope = (overrides: Partial<DiscoveryScopeMetadata> = {}): DiscoveryScopeMetadata => ({
  ticker: null,
  section: null,
  year: null,
  filing_date: null,
  documents: 50,
  count_scope: "bounded_candidates",
  candidate_ceiling: 200,
  limited_by_ceiling: false,
  matched_documents: 15,
  matched_chunks: 200,
  ...overrides,
});

const hit = (overrides: Partial<DiscoveryHit> = {}): DiscoveryHit => ({
  chunk_id: "AAPL_x_risk_factors_0001",
  document_id: "AAPL:0001",
  ticker: "AAPL",
  section: "risk_factors",
  filing_date: "2025-10-31",
  report_date: "2025-09-27",
  chunk_index: 1,
  score: 10.703384,
  snippet: { text: "Our business could be adversely affected by competition.", ranges: [[42, 53]], truncated: false },
  ...overrides,
});

const group = (overrides: Partial<DiscoveryGroup> = {}): DiscoveryGroup => ({
  document_id: "AAPL:0001",
  ticker: "AAPL",
  filing_date: "2025-10-31",
  report_date: "2025-09-27",
  sections: ["risk_factors"],
  best_score: 10.703384,
  hit_count: 3,
  hits: [hit()],
  ...overrides,
});

describe("searchModel snippet highlighting", () => {
  test("splits real API ranges into highlighted and plain segments", () => {
    const segments = snippetSegments({ text: "supply chain risk", ranges: [[0, 6], [7, 12]], truncated: true });
    expect(segments).toEqual([
      { text: "supply", match: true },
      { text: " ", match: false },
      { text: "chain", match: true },
      { text: " risk", match: false },
    ]);
  });

  test("clamps out-of-range and overlapping ranges instead of throwing", () => {
    const segments = snippetSegments({ text: "abc", ranges: [[2, 99], [0, 1], [0, 1]], truncated: false });
    // Ranges are clamped to the text, duplicates merged, and the untouched
    // middle stays plain rather than being swallowed by a neighbour.
    expect(segments).toEqual([
      { text: "a", match: true },
      { text: "b", match: false },
      { text: "c", match: true },
    ]);
    expect(snippetSegments({ text: "abc", ranges: [], truncated: false })).toEqual([{ text: "abc", match: false }]);
  });

  test("keeps Vietnamese text and punctuation intact", () => {
    const text = "Rủi ro chuỗi cung ứng, gồm cả nhà cung cấp — và chi phí.";
    const start = text.indexOf("chuỗi");
    const segments = snippetSegments({ text, ranges: [[start, start + 5]], truncated: false });
    expect(segments.filter((segment) => segment.match).map((segment) => segment.text)).toEqual(["chuỗi"]);
    expect(segments.map((segment) => segment.text).join("")).toBe(text);
  });

  test("returns nothing for an empty snippet", () => {
    expect(snippetSegments({ text: "", ranges: [], truncated: false })).toEqual([]);
  });
});

describe("searchModel bounded counts", () => {
  test("labels a bounded page in the snapshot's own unit", () => {
    expect(pageRangeLabel(1, 20, 15, "document", false)).toBe("Showing 1–15 of 15 filings");
    expect(pageRangeLabel(2, 5, 12, "chunk", false)).toBe("Showing 6–10 of 12 excerpts");
    expect(pageRangeLabel(1, 20, 0, "document", false)).toBe("0 filings");
  });

  test("explains the candidate ceiling only when discovery was truncated", () => {
    expect(ceilingNote(scope({ limited_by_ceiling: true }), false)).toContain("first 200 candidates");
    expect(ceilingNote(scope({ limited_by_ceiling: false }), false)).toBeNull();
  });

  test("reads the top score from the snapshot's grouping unit", () => {
    expect(topScore([group({ best_score: 4.5 }), group({ best_score: 9.25 })], "document")).toBe(9.25);
    expect(topScore([hit({ score: 1.5 }), hit({ score: 3.25 })], "chunk")).toBe(3.25);
    expect(topScore([], "document")).toBeNull();
    expect(itemScore(group(), "document")).toBe(10.703384);
    expect(itemScore(hit(), "chunk")).toBe(10.703384);
  });

  test("takes the best excerpt of a group as the card's excerpt", () => {
    const best = hit({ chunk_id: "best" });
    expect(primaryHit(group({ hits: [best, hit({ chunk_id: "other" })] }), "document")?.chunk_id).toBe("best");
    expect(primaryHit(group({ hits: [] }), "document")).toBeNull();
    expect(primaryHit(hit({ chunk_id: "solo" }), "chunk")?.chunk_id).toBe("solo");
  });

  test("formats the raw BM25 score without turning it into a percentage", () => {
    expect(formatScore(10.703384)).toBe("10.703");
    expect(formatScore(0)).toBe("0.000");
  });

  test("reads the filing year from the recorded date only", () => {
    expect(filingYear("2025-10-31")).toBe(2025);
    expect(filingYear(null)).toBeNull();
    expect(filingYear("unknown")).toBeNull();
  });

  test("summarises the scope from the snapshot's own filters", () => {
    expect(scopeSummary(scope(), false)).toBe("The whole indexed catalog");
    expect(scopeSummary(scope({ ticker: "AAPL", section: "risk_factors", year: 2025 }), false)).toBe("AAPL · risk_factors · 2025");
  });
});

describe("searchModel query discipline", () => {
  test("accepts a trimmed query inside the API bounds", () => {
    expect(submittableQuery("  cloud   revenue ")).toBe("cloud revenue");
    expect(submittableQuery("a")).toBeNull();
    expect(submittableQuery("   ")).toBeNull();
    expect(submittableQuery("x".repeat(201))).toBeNull();
  });

  test("names each discovery failure instead of flattening it", () => {
    expect(describeDiscoveryError(new ApiError("gone", 410), false).kind).toBe("expired");
    expect(describeDiscoveryError(new ApiError("missing", 404), false).kind).toBe("unknown_snapshot");
    expect(describeDiscoveryError(new ApiError("slow down", 429, null, 12), false)).toMatchObject({ kind: "rate_limited" });
    expect(describeDiscoveryError(new ApiError("slow down", 429, null, 12), false).message).toContain("12s");
    expect(describeDiscoveryError(new ApiError("Query too short", 422), false).message).toBe("Query too short");
    expect(describeDiscoveryError(new ApiError("invalid query", 422), false).canRerun).toBe(false);
    expect(describeDiscoveryError(new ApiError("not ready", 503), false).kind).toBe("unavailable");
    expect(describeDiscoveryError(new Error("boom"), false).kind).toBe("generic");
  });

  test("formats real recent-search times", () => {
    // Local calendar days: the helper compares the reader's own day boundaries.
    const now = new Date(2026, 8, 22, 18, 0).getTime();
    const today = new Date(2026, 8, 22, 9, 32).getTime();
    const yesterday = new Date(2026, 8, 21, 3, 21).getTime();
    expect(relativeSearchTime(today, now, false)).toContain("Today");
    expect(relativeSearchTime(yesterday, now, false)).toContain("Yesterday");
    expect(relativeSearchTime(new Date(2026, 0, 15, 12, 0).getTime(), now, false)).toContain("2026");
  });

  test("keeps the stored recent-search shape", () => {
    const entry: RecentSearch = { query: "cloud revenue", results: 15, at: 1 };
    expect(typeof entry.results).toBe("number");
  });
});
