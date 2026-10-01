export const analyticsRanges = ["24h", "7d", "30d"] as const;
export const analyticsIntervals = ["hour", "day"] as const;
export const analyticsMetrics = ["request_count", "request_failure_count", "request_duration_p50_ms", "request_duration_p95_ms", "terminal_job_count"] as const;
export const outcomes = ["succeeded", "rejected", "failed", "cancelled", "interrupted"] as const;
export const levels = ["info", "warning", "error"] as const;
export type AnalyticsRange = typeof analyticsRanges[number];
export type AnalyticsInterval = typeof analyticsIntervals[number];
export type AnalyticsMetric = typeof analyticsMetrics[number];
export type Outcome = typeof outcomes[number];
export type LogLevel = typeof levels[number];
export type LogCategory = "request" | "job";
export interface RatePopulation { value: number | null; numerator: number; denominator: number }
export interface AnalyticsSummary {
  range: AnalyticsRange; started_at: string; ended_at: string;
  requests: { terminal_count: number; outcomes: Record<Outcome, number>; success_rate: RatePopulation; failure_rate: RatePopulation; duration_ms: { known_count: number; unknown_count: number; p50: number | null; p95: number | null } };
  terminal_jobs: { terminal_count: number; by_namespace: Record<"pipeline" | "evaluation" | "model_test", number>; by_outcome: Record<Exclude<Outcome, "rejected">, number> };
}
export interface AnalyticsPoint { started_at: string; ended_at: string; value: number | null; denominator: number }
export interface AnalyticsTimeseries { range: AnalyticsRange; interval: AnalyticsInterval; metric: AnalyticsMetric; unit: "count" | "milliseconds"; started_at: string; ended_at: string; points: AnalyticsPoint[] }
export interface OperationalLog {
  record_id: string; occurred_at: string; category: LogCategory; level: LogLevel;
  kind: "request_terminal" | "job_terminal"; subsystem: "query" | "search" | "retrieval" | "pipeline" | "evaluation" | "model_test";
  outcome: Outcome; correlation_id: string; domain_id: string | null; route_template: string | null;
  error_code: string | null; duration_ms: number | null;
  metadata: { http_method?: "GET" | "POST"; streaming?: boolean; decomposed?: boolean; status_code?: number };
}
export interface OperationalLogPage { items: OperationalLog[]; next_cursor: string | null; has_more: boolean; limit: number }
export interface SettingsFacts { api_version: string; default_retrieval: string }
