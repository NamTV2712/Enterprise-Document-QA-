/**
 * Pure helpers for the Retrieval and Reranker inspection pages.
 *
 * Everything here reads what API-005 actually reported. The score families stay
 * distinct, a null duration or score is never rendered as zero, a stage that did
 * not run is never shown as a run, and a dropped reason is only ever the one the
 * trace supplied.
 */

import type {
  RetrievalCandidate,
  RetrievalDroppedReason,
  RetrievalPreset,
  RetrievalScoreKey,
  RetrievalScoreSemantics,
  RetrievalScope,
  RetrievalStageStatus,
  RetrievalTrace,
  RetrievalTraceStage,
} from "../types";

export const PRESET_ORDER: RetrievalPreset[] = ["bm25", "dense", "hybrid", "hybrid_rerank"];

export const PRESET_LABELS: Record<RetrievalPreset, { label: string; vi: string; description: string }> = {
  bm25: { label: "BM25", vi: "BM25", description: "Lexical ranking only" },
  dense: { label: "Dense vector", vi: "Vector dense", description: "Embedding similarity only" },
  hybrid: { label: "Hybrid RRF", vi: "Hybrid RRF", description: "Lexical and dense fused by RRF" },
  hybrid_rerank: { label: "Hybrid + reranker", vi: "Hybrid + reranker", description: "Fused pool reordered by the cross-encoder" },
};

export const SCORE_KEYS: RetrievalScoreKey[] = ["bm25_score", "dense_score", "rrf_score", "cross_encoder_score"];

export const SCORE_LABELS: Record<RetrievalScoreKey, string> = {
  bm25_score: "BM25",
  dense_score: "Dense similarity",
  rrf_score: "RRF",
  cross_encoder_score: "Reranker",
};

/** The signal a preset's final order is built from. */
export const PRIMARY_SCORE_KEY: Record<RetrievalPreset, RetrievalScoreKey> = {
  bm25: "bm25_score",
  dense: "dense_score",
  hybrid: "rrf_score",
  hybrid_rerank: "cross_encoder_score",
};

export function primaryScoreKey(preset: RetrievalPreset): RetrievalScoreKey {
  return PRIMARY_SCORE_KEY[preset] ?? "rrf_score";
}

/** A score that was not reported is named, never rendered as a zero. */
export function formatScore(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Not reported";
  // RRF sums reciprocal ranks and is far smaller than a BM25 score or a logit,
  // so its precision follows the family instead of one global format.
  if (Math.abs(value) < 0.1 && value !== 0) return value.toFixed(6);
  return value.toFixed(4);
}

export function formatScoreForFamily(key: RetrievalScoreKey, value: number | null | undefined, vi = false): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return vi ? "Chưa có dữ liệu" : "Not reported";
  if (key === "rrf_score") return value.toFixed(6);
  if (key === "bm25_score") return value.toFixed(4);
  return value.toFixed(4);
}

/** Milliseconds, or an explicit "not reported" — never a fabricated 0 ms. */
export function formatDuration(value: number | null | undefined, vi = false): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return vi ? "Chưa có dữ liệu" : "Not reported";
  if (value >= 1000) return `${(value / 1000).toFixed(2)} s`;
  return `${value.toFixed(1)} ms`;
}

export function formatCount(value: number | null | undefined, vi = false): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return vi ? "Chưa có dữ liệu" : "Not reported";
  return value.toLocaleString(vi ? "vi-VN" : "en-US");
}

export function stageStatus(stage: RetrievalTraceStage): RetrievalStageStatus {
  if (stage.status) return stage.status;
  if (stage.skipped) return "skipped";
  return stage.elapsed_ms === null ? "not_executed" : "executed";
}

export function stageStatusLabel(status: RetrievalStageStatus, vi = false): string {
  if (status === "executed") return vi ? "Đã chạy" : "Executed";
  if (status === "skipped") return vi ? "Bỏ qua" : "Skipped";
  return vi ? "Không chạy trong inspection" : "Not executed in inspection";
}

/**
 * The per-stage latency breakdown a reader can trust: only stages this trace
 * actually ran contribute, and a trace that ran none reports nothing.
 */
export function latencyBreakdown(trace: RetrievalTrace, vi = false): string | null {
  const parts = trace.stages
    .filter((stage) => stageStatus(stage) === "executed" && typeof stage.elapsed_ms === "number")
    .map((stage) => `${stage.name} ${formatDuration(stage.elapsed_ms, vi)}`);
  if (parts.length === 0) return null;
  return parts.join(" + ");
}

/** One named stage of a trace, or null when this trace does not report it. */
export function findStage(trace: RetrievalTrace, name: string): RetrievalTraceStage | null {
  return trace.stages.find((stage) => stage.name.toLowerCase() === name.toLowerCase()) ?? null;
}

export function rerankerStage(trace: RetrievalTrace): RetrievalTraceStage | null {
  return findStage(trace, "reranker");
}

/** The reranker identity only when the stage actually ran with it. */
export function rerankerModel(trace: RetrievalTrace): string | null {
  const stage = rerankerStage(trace);
  if (!stage || stageStatus(stage) !== "executed") return null;
  return trace.models.reranker ?? null;
}

export const DROPPED_REASON_LABELS: Record<RetrievalDroppedReason, { label: string; vi: string }> = {
  ranked_below_top_k: { label: "Ranked below the selected top-k", vi: "Xếp dưới top-k đã chọn" },
  outside_candidate_pool: { label: "Outside the candidate pool", vi: "Ngoài candidate pool" },
  not_in_selected_preset_stage: { label: "Not produced by this preset's stage", vi: "Không do stage của preset này tạo ra" },
};

export interface CandidateStatus {
  kind: "selected" | "dropped" | "not_selected";
  label: string;
}

/**
 * What this candidate's own trace says about it. A dropped candidate without a
 * reported reason stays "not selected"; no explanation is invented.
 */
export function candidateStatus(candidate: RetrievalCandidate, vi = false): CandidateStatus {
  if (candidate.selected) return { kind: "selected", label: vi ? "Đã chọn" : "Selected" };
  const reason = candidate.dropped_reason;
  if (reason && reason in DROPPED_REASON_LABELS) {
    return { kind: "dropped", label: vi ? DROPPED_REASON_LABELS[reason].vi : DROPPED_REASON_LABELS[reason].label };
  }
  return { kind: "not_selected", label: vi ? "Không được chọn" : "Not selected" };
}

export interface RankMovement {
  /** The rank the candidate held before the reranker reordered the pool. */
  before: number | null;
  /** The rank the trace assigned finally. */
  after: number | null;
  /** Positive means the candidate moved up (a smaller final rank). */
  delta: number | null;
  label: string;
}

/**
 * Rank movement for one candidate, computed from the trace's own ranks. The
 * fusion rank is the order entering the reranker, so a candidate without both
 * ranks reports no movement rather than an invented one.
 */
export function rankMovement(candidate: RetrievalCandidate, vi = false): RankMovement {
  const before = candidate.fusion_rank ?? null;
  const after = candidate.final_rank ?? null;
  if (before === null || after === null) {
    return { before, after, delta: null, label: vi ? "Chưa có dữ liệu" : "Not reported" };
  }
  const delta = before - after;
  if (delta === 0) return { before, after, delta, label: vi ? "Không đổi" : "No change" };
  return {
    before,
    after,
    delta,
    label: delta > 0 ? (vi ? `Lên ${delta}` : `Up ${delta}`) : (vi ? `Xuống ${Math.abs(delta)}` : `Down ${Math.abs(delta)}`),
  };
}

/** True when every candidate in the pool carries the reranker's own score. */
export function poolHasRerankerScores(candidates: RetrievalCandidate[]): boolean {
  const scored = candidates.filter((candidate) => typeof candidate.cross_encoder_score === "number");
  return candidates.length > 0 && scored.length === candidates.length;
}

/** The score families this trace actually reports, in a stable order. */
export function availableScoreKeys(trace: RetrievalTrace, candidates: RetrievalCandidate[]): RetrievalScoreKey[] {
  const reported = new Set<RetrievalScoreKey>();
  for (const candidate of candidates) {
    for (const key of SCORE_KEYS) {
      if (typeof candidate[key] === "number") reported.add(key);
    }
  }
  if (trace.score_semantics) {
    return SCORE_KEYS.filter((key) => key in trace.score_semantics!.families && reported.has(key));
  }
  return SCORE_KEYS.filter((key) => reported.has(key));
}

/** The API's own definition of a score family, for the disclosure surfaces. */
export function scoreFamilyDefinition(
  semantics: RetrievalScoreSemantics | undefined,
  key: RetrievalScoreKey,
): { family: string; scale: string; definition: string } | null {
  const entry = semantics?.families?.[key];
  if (!entry) return null;
  return entry;
}

/** The API's warning that the families are distinct and are not confidences. */
export function scoreSemanticsNote(trace: RetrievalTrace): string | null {
  return trace.score_semantics?.note ?? null;
}

/**
 * The effective scope, phrased so a bounded list is never presented as the
 * complete eligible set.
 */
export function scopeSummary(scope: RetrievalScope | undefined, vi = false): string | null {
  if (!scope) return null;
  if (scope.documents === null) {
    return scope.reason ?? (vi ? "Phạm vi chưa xác định." : "The scope could not be determined.");
  }
  const base = vi
    ? `${scope.documents} tài liệu đủ điều kiện`
    : `${scope.documents} eligible ${scope.documents === 1 ? "document" : "documents"}`;
  if (!scope.truncated) return base;
  const shown = scope.eligible_document_ids.length;
  return vi
    ? `${base} (danh sách id được giới hạn ở ${shown} mục đầu)`
    : `${base} (the id list is bounded to the first ${shown})`;
}

/** Distinct sections represented in the candidate pool, for the count hint. */
export function candidateSectionCount(candidates: RetrievalCandidate[]): number {
  return new Set(candidates.map((candidate) => candidate.section).filter((section): section is string => Boolean(section))).size;
}

export type ResultOrderKey = "trace_order" | RetrievalScoreKey;

export interface ResultOrderOption {
  value: ResultOrderKey;
  label: string;
}

/**
 * The view orders a reader may choose. The trace's own order always comes
 * first, and a score order is offered only for families this trace reported —
 * so a BM25-only trace never offers a reranker order, and reordering never
 * invents a rank: it only changes which column the rows are listed by.
 */
export function orderOptions(trace: RetrievalTrace, candidates: RetrievalCandidate[], vi = false): ResultOrderOption[] {
  const options: ResultOrderOption[] = [
    { value: "trace_order", label: vi ? "Thứ tự trace (hạng cuối)" : "Trace order (final rank)" },
  ];
  for (const key of availableScoreKeys(trace, candidates)) {
    options.push({ value: key, label: vi ? `${SCORE_LABELS[key]} (điểm)` : `${SCORE_LABELS[key]} (score)` });
  }
  return options;
}

function compareRank(left: number | null | undefined, right: number | null | undefined): number {
  const leftValue = typeof left === "number" ? left : Number.POSITIVE_INFINITY;
  const rightValue = typeof right === "number" ? right : Number.POSITIVE_INFINITY;
  return leftValue - rightValue;
}

/**
 * Order the fetched candidates for display. Ties fall back to the trace's own
 * final rank and then to the canonical chunk id, so the view order is
 * deterministic and never depends on the response order.
 */
export function sortCandidates(
  candidates: RetrievalCandidate[],
  order: ResultOrderKey,
): RetrievalCandidate[] {
  const byIdentity = (left: RetrievalCandidate, right: RetrievalCandidate) =>
    compareRank(left.final_rank, right.final_rank) || left.chunk_id.localeCompare(right.chunk_id);
  if (order === "trace_order") return [...candidates].sort(byIdentity);
  const key = order;
  return [...candidates].sort((left, right) => {
    const leftValue = left[key];
    const rightValue = right[key];
    const leftMissing = typeof leftValue !== "number";
    const rightMissing = typeof rightValue !== "number";
    // A candidate without this score is listed after the scored ones rather
    // than being treated as a zero.
    if (leftMissing !== rightMissing) return leftMissing ? 1 : -1;
    if (leftMissing && rightMissing) return byIdentity(left, right);
    return (rightValue as number) - (leftValue as number) || byIdentity(left, right);
  });
}

export interface PageRange {
  start: number;
  end: number;
  pageCount: number;
}

/** Page geometry over the fetched pool; pagination is a view over one trace. */
export function pageRange(total: number, page: number, pageSize: number): PageRange {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(1, page), pageCount);
  const start = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const end = Math.min(safePage * pageSize, total);
  return { start, end, pageCount };
}

export function pageLabel(range: PageRange, total: number, vi = false): string {
  if (total === 0) return vi ? "0 ứng viên" : "0 candidates";
  return vi
    ? `Hiển thị ${range.start}–${range.end} trên ${total} ứng viên`
    : `Showing ${range.start}–${range.end} of ${total} candidates`;
}

/** The configuration one submitted trace belongs to, for the staleness note. */
export function traceConfigurationKey(input: {
  question: string;
  ticker: string | null;
  section: string | null;
  documentId: string | null;
  filingDate: string | null;
  year: number | null;
  topK: number;
  candidatePool: number;
  preset: RetrievalPreset;
}): string {
  return JSON.stringify({
    question: input.question.trim(),
    ticker: input.ticker,
    section: input.section,
    documentId: input.documentId,
    filingDate: input.filingDate,
    year: input.year,
    topK: input.topK,
    candidatePool: input.candidatePool,
    preset: input.preset,
  });
}

/** The submitted configuration, described from the trace's own filter values. */
export function traceConfigurationSummary(trace: RetrievalTrace, vi = false): string {
  const values = trace.filter_values;
  const ticker = values?.ticker ?? trace.filters.ticker;
  const section = values?.section ?? trace.filters.section;
  const parts = [
    ticker ?? (vi ? "Tất cả công ty" : "All companies"),
    section ?? (vi ? "Tất cả mục" : "All sections"),
    vi ? `top K ${trace.top_k}` : `top K ${trace.top_k}`,
    vi ? `pool ${trace.candidate_pool}` : `pool ${trace.candidate_pool}`,
    PRESET_LABELS[trace.preset]?.[vi ? "vi" : "label"] ?? trace.preset,
  ];
  if (values?.document_id) parts.push(values.document_id);
  if (values?.filing_date) parts.push(values.filing_date);
  if (typeof values?.year === "number") parts.push(String(values.year));
  return parts.join(" · ");
}

/** True when any candidate in the pool carries a negative score. */
export function hasNegativeScore(candidates: RetrievalCandidate[], key: RetrievalScoreKey): boolean {
  return candidates.some((candidate) => typeof candidate[key] === "number" && (candidate[key] as number) < 0);
}

/** Production parity entries, phrased with the API's own reason. */
export function productionParityEntries(trace: RetrievalTrace): Array<{ name: string; status: RetrievalStageStatus }> {
  const parity = trace.production_parity;
  if (!parity) return [];
  return [
    { name: "structured_promotion", status: parity.structured_promotion },
    { name: "lexical_ladder_merge_into_final", status: parity.lexical_ladder_merge_into_final },
  ];
}
