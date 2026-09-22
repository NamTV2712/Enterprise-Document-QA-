/**
 * Pure helpers for the discovery Search page.
 *
 * Everything here derives from what API-004 actually returned: page ranges in
 * the snapshot's own grouping unit, scores as ranking signals, and bounded
 * counts that are never presented as a whole-corpus total. No helper
 * re-derives a highlight, a total, or a rank that the API already decided.
 */

import { ApiError } from "./api";
import type {
  DiscoveryGroup,
  DiscoveryGrouping,
  DiscoveryHit,
  DiscoveryScopeMetadata,
  DiscoverySnippet,
} from "../types";

/** Existing browser-local recent-query key; UI-006 keeps its shape and bounds. */
export const RECENT_SEARCH_KEY = "sec_qa_search_history_v1";
export const RECENT_SEARCH_LIMIT = 5;

export const MIN_QUERY_LENGTH = 2;
export const MAX_QUERY_LENGTH = 200;
export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

export interface RecentSearch {
  query: string;
  /** Pageable length of the snapshot that query produced, when one ran. */
  results: number | null;
  /** Epoch milliseconds of the submission. */
  at: number;
}

function isRecentSearch(value: unknown): value is RecentSearch {
  if (typeof value !== "object" || value === null) return false;
  const entry = value as RecentSearch;
  return (
    typeof entry.query === "string" &&
    typeof entry.at === "number" &&
    (entry.results === null || typeof entry.results === "number")
  );
}

/** Read the bounded recent-query list, ignoring anything malformed. */
export function readRecentSearches(): RecentSearch[] {
  try {
    const raw = window.localStorage.getItem(RECENT_SEARCH_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isRecentSearch).slice(0, RECENT_SEARCH_LIMIT);
  } catch {
    return [];
  }
}

/** Record one submitted query, most recent first, and return the new list. */
export function rememberRecentSearch(query: string, results: number | null): RecentSearch[] {
  const trimmed = query.trim();
  const current = readRecentSearches().filter((entry) => entry.query.toLowerCase() !== trimmed.toLowerCase());
  const next = [{ query: trimmed, results, at: Date.now() }, ...current].slice(0, RECENT_SEARCH_LIMIT);
  try {
    window.localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(next));
  } catch {
    // Storage may be unavailable; the caller still renders the new list.
  }
  return next;
}

/** The unit a page is counted in, which follows the snapshot's own grouping. */
export function resultUnit(grouping: DiscoveryGrouping, vi: boolean): string {
  if (grouping === "chunk") return vi ? "đoạn nguồn" : "excerpts";
  return vi ? "hồ sơ" : "filings";
}

/**
 * The page range inside the bounded discovery set. When discovery stopped at
 * the candidate ceiling the caller must also render `ceilingNote`, because
 * this total is not a corpus total.
 */
export function pageRangeLabel(page: number, pageSize: number, total: number, grouping: DiscoveryGrouping, vi: boolean): string {
  const unit = resultUnit(grouping, vi);
  if (total === 0) return vi ? `0 ${unit}` : `0 ${unit}`;
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return vi
    ? `Hiển thị ${start}–${end} trên ${total} ${unit}`
    : `Showing ${start}–${end} of ${total} ${unit}`;
}

/**
 * The truthful consequence of `limited_by_ceiling`: discovery stopped at the
 * ceiling, so more matches may exist than the reported total.
 */
export function ceilingNote(scope: DiscoveryScopeMetadata, vi: boolean): string | null {
  if (!scope.limited_by_ceiling) return null;
  return vi
    ? `Discovery chỉ chấm ${scope.candidate_ceiling} ứng viên đầu tiên, nên có thể còn kết quả khớp khác.`
    : `Discovery ranked the first ${scope.candidate_ceiling} candidates, so further matches may exist.`;
}

/** The strongest score on this page, or null when the page is empty. */
export function topScore(items: Array<DiscoveryGroup | DiscoveryHit>, grouping: DiscoveryGrouping): number | null {
  if (items.length === 0) return null;
  const scores = grouping === "document"
    ? (items as DiscoveryGroup[]).map((group) => group.best_score)
    : (items as DiscoveryHit[]).map((hit) => hit.score);
  return scores.length > 0 ? Math.max(...scores) : null;
}

/** One result's own score: a group reports its best excerpt's score. */
export function itemScore(item: DiscoveryGroup | DiscoveryHit, grouping: DiscoveryGrouping): number {
  return grouping === "document" ? (item as DiscoveryGroup).best_score : (item as DiscoveryHit).score;
}

/** The excerpt a card shows and opens: the best-matching one in the result. */
export function primaryHit(item: DiscoveryGroup | DiscoveryHit, grouping: DiscoveryGrouping): DiscoveryHit | null {
  if (grouping === "chunk") return item as DiscoveryHit;
  const group = item as DiscoveryGroup;
  return group.hits.length > 0 ? group.hits[0] : null;
}

export function resultIdentity(item: DiscoveryGroup | DiscoveryHit, grouping: DiscoveryGrouping): string {
  return grouping === "document" ? (item as DiscoveryGroup).document_id : (item as DiscoveryHit).chunk_id;
}

export function resultSections(item: DiscoveryGroup | DiscoveryHit, grouping: DiscoveryGrouping): string[] {
  if (grouping === "chunk") {
    const hit = item as DiscoveryHit;
    return hit.section ? [hit.section] : [];
  }
  return (item as DiscoveryGroup).sections;
}

export function resultTicker(item: DiscoveryGroup | DiscoveryHit): string | null {
  return item.ticker;
}

export function resultFilingDate(item: DiscoveryGroup | DiscoveryHit): string | null {
  return item.filing_date;
}

/** The filing year a chip shows, taken from the recorded filing date. */
export function filingYear(filingDate: string | null): number | null {
  if (!filingDate) return null;
  const year = Number(filingDate.slice(0, 4));
  return Number.isFinite(year) ? year : null;
}

/** Raw BM25 score, shown to three decimals and never labelled as confidence. */
export function formatScore(score: number): string {
  return score.toFixed(3);
}

export interface SnippetSegment {
  text: string;
  match: boolean;
}

/**
 * Split a snippet into highlighted and plain segments from the API's ranges.
 * Ranges are clamped to the returned text and skipped when they are empty or
 * out of order, so malformed data renders as plain text instead of throwing.
 */
export function snippetSegments(snippet: DiscoverySnippet): SnippetSegment[] {
  const { text, ranges } = snippet;
  if (!text) return [];
  const safe = ranges
    .map(([start, end]) => [Math.max(0, start), Math.min(text.length, end)] as [number, number])
    .filter(([start, end]) => end > start)
    .sort((left, right) => left[0] - right[0]);
  if (safe.length === 0) return [{ text, match: false }];

  const merged: Array<[number, number]> = [];
  for (const [start, end] of safe) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1]) {
      last[1] = Math.max(last[1], end);
      continue;
    }
    merged.push([start, end]);
  }

  const segments: SnippetSegment[] = [];
  let cursor = 0;
  for (const [start, end] of merged) {
    if (start > cursor) segments.push({ text: text.slice(cursor, start), match: false });
    segments.push({ text: text.slice(start, end), match: true });
    cursor = end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), match: false });
  return segments;
}

/** A truthful one-line scope summary from the snapshot's own filter values. */
export function scopeSummary(scope: DiscoveryScopeMetadata, vi: boolean): string {
  const parts: string[] = [];
  if (scope.ticker) parts.push(scope.ticker);
  if (scope.section) parts.push(scope.section);
  if (scope.year) parts.push(String(scope.year));
  if (scope.filing_date) parts.push(scope.filing_date);
  if (parts.length === 0) return vi ? "Toàn bộ danh mục đã index" : "The whole indexed catalog";
  return parts.join(" · ");
}

export function relativeSearchTime(at: number, now: number, vi: boolean): string {
  const time = new Date(at);
  const clock = time.toLocaleTimeString(vi ? "vi-VN" : "en-US", { hour: "numeric", minute: "2-digit" });
  const day = new Date(now);
  const isSameDay = (left: Date, right: Date) =>
    left.getFullYear() === right.getFullYear() && left.getMonth() === right.getMonth() && left.getDate() === right.getDate();
  if (isSameDay(time, day)) return vi ? `Hôm nay, ${clock}` : `Today, ${clock}`;
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (isSameDay(time, yesterday)) return vi ? `Hôm qua, ${clock}` : `Yesterday, ${clock}`;
  const date = time.toLocaleDateString(vi ? "vi-VN" : "en-US", { month: "short", day: "numeric", year: "numeric" });
  return `${date}, ${clock}`;
}

export type DiscoveryErrorKind =
  | "expired"
  | "unknown_snapshot"
  | "rate_limited"
  | "invalid_query"
  | "unavailable"
  | "generic";

export interface DiscoveryErrorInfo {
  kind: DiscoveryErrorKind;
  message: string;
  /** A rerun is the honest next action for an expired snapshot. */
  canRerun: boolean;
}

/**
 * Tell a reader what actually failed. A 410 is an expired snapshot, a 404 an
 * unknown id, a 429 a rate limit, a 422 the API's own validation message; none
 * of them may be flattened into "no results".
 */
export function describeDiscoveryError(error: unknown, vi: boolean): DiscoveryErrorInfo {
  const status = error instanceof ApiError ? error.status : null;
  const detail = error instanceof ApiError ? error.message : null;
  if (status === 410) {
    return {
      kind: "expired",
      message: vi
        ? "Kết quả tìm kiếm này đã hết hạn lưu trữ. Hãy chạy lại tìm kiếm để có kết quả mới."
        : "This search snapshot expired. Run the search again for a fresh result set.",
      canRerun: true,
    };
  }
  if (status === 404) {
    return {
      kind: "unknown_snapshot",
      message: vi
        ? "Không tìm thấy snapshot tương ứng. Hãy chạy lại tìm kiếm."
        : "That search snapshot is not known any more. Run the search again.",
      canRerun: true,
    };
  }
  if (status === 429) {
    const retry = error instanceof ApiError && error.retryAfterSeconds ? ` (${error.retryAfterSeconds}s)` : "";
    return {
      kind: "rate_limited",
      message: vi
        ? `Đã chạm giới hạn tần suất tìm kiếm${retry}. Hãy chờ rồi thử lại.`
        : `The search rate limit was reached${retry}. Wait a moment, then try again.`,
      canRerun: true,
    };
  }
  if (status === 422) {
    return {
      kind: "invalid_query",
      message: detail ?? (vi ? "Truy vấn không hợp lệ." : "The query is not valid."),
      canRerun: false,
    };
  }
  if (status === 503) {
    return {
      kind: "unavailable",
      message: vi ? "Dịch vụ tìm kiếm chưa sẵn sàng." : "The search service is not ready yet.",
      canRerun: true,
    };
  }
  return {
    kind: "generic",
    message: detail ?? (vi ? "Không thể chạy tìm kiếm." : "The search could not be run."),
    canRerun: true,
  };
}

/** Trimmed query that API-004 will accept, or null when it would reject it. */
export function submittableQuery(raw: string): string | null {
  const trimmed = raw.trim().replace(/\s+/g, " ");
  if (trimmed.length < MIN_QUERY_LENGTH || trimmed.length > MAX_QUERY_LENGTH) return null;
  return trimmed;
}
