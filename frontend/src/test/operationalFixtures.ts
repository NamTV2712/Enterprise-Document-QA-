import type { AnalyticsRange, AnalyticsMetric, AnalyticsInterval, AnalyticsSummary, AnalyticsTimeseries, OperationalLog, OperationalLogPage } from "../lib/operationalTypes";
export const operationalToken = "ui012-synthetic-memory-token";
export const operationalCursor = "opaque+/cursor==";
export const configurationFixture = { deployment_mode: "local", capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: false } };
export function summaryFixture(range: AnalyticsRange = "24h", empty = false): AnalyticsSummary {
  return { range, started_at: "2026-09-26T00:00:00Z", ended_at: "2026-09-27T00:00:00Z", requests: { terminal_count: empty ? 0 : 5, outcomes: { succeeded: empty ? 0 : 2, rejected: empty ? 0 : 1, failed: empty ? 0 : 1, cancelled: empty ? 0 : 1, interrupted: 0 }, success_rate: { value: empty ? null : .4, numerator: empty ? 0 : 2, denominator: empty ? 0 : 5 }, failure_rate: { value: empty ? null : .2, numerator: empty ? 0 : 1, denominator: empty ? 0 : 5 }, duration_ms: { known_count: empty ? 0 : 2, unknown_count: empty ? 0 : 3, p50: empty ? null : 0, p95: empty ? null : 15 } }, terminal_jobs: { terminal_count: empty ? 0 : 4, by_namespace: { pipeline: empty ? 0 : 2, evaluation: empty ? 0 : 1, model_test: empty ? 0 : 1 }, by_outcome: { succeeded: empty ? 0 : 1, failed: empty ? 0 : 1, cancelled: empty ? 0 : 1, interrupted: empty ? 0 : 1 } } };
}
export function seriesFixture(range: AnalyticsRange = "24h", interval: AnalyticsInterval = "hour", metric: AnalyticsMetric = "request_count", empty = false): AnalyticsTimeseries {
  const duration = metric.includes("duration");
  return { range, interval, metric, unit: duration ? "milliseconds" : "count", started_at: "2026-09-26T00:00:00Z", ended_at: "2026-09-26T02:00:00Z", points: [
    { started_at: "2026-09-26T00:00:00Z", ended_at: "2026-09-26T01:00:00Z", value: duration ? null : 0, denominator: 0 },
    { started_at: "2026-09-26T01:00:00Z", ended_at: "2026-09-26T02:00:00Z", value: empty ? (duration ? null : 0) : duration ? 0 : 2, denominator: empty ? 0 : 2 },
  ] };
}
export function logFixture(id = "tel_z"): OperationalLog { return { record_id: id, occurred_at: "2026-09-26T01:00:00Z", category: "request", level: "info", kind: "request_terminal", subsystem: "query", outcome: "cancelled", correlation_id: "req_safe_012", domain_id: null, route_template: "/query/stream", error_code: "client_disconnected", duration_ms: 0, metadata: { http_method: "POST", streaming: true, decomposed: false, status_code: 200 } }; }
export function jobLogFixture(): OperationalLog { return { ...logFixture("job:job_safe:2"), category: "job", kind: "job_terminal", subsystem: "evaluation", level: "warning", outcome: "failed", error_code: "budget_exhausted", duration_ms: null, correlation_id: "job_safe", domain_id: "job_safe", route_template: null, metadata: {} }; }
export function logPageFixture(): OperationalLogPage { return { items: [logFixture(), jobLogFixture()], next_cursor: operationalCursor, has_more: true, limit: 50 }; }
export const hiddenOperationalFields = { query: "HIDDEN_QUERY_UI012", answer: "HIDDEN_ANSWER_UI012", evidence: "HIDDEN_EVIDENCE_UI012", session_id: "HIDDEN_SESSION_UI012", prompt: "HIDDEN_PROMPT_UI012", provider_body: "HIDDEN_PROVIDER_UI012", stack_trace: "HIDDEN_STACK_UI012", bearer: "HIDDEN_BEARER_UI012", cookie: "HIDDEN_COOKIE_UI012", path: "HIDDEN_PATH_UI012" };
