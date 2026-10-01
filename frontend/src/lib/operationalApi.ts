import { apiFetch, getApiBaseUrl } from "./api";
import type { LocalWorkspaceConfigurationStatus } from "../types";
import { analyticsRanges, analyticsIntervals, analyticsMetrics, outcomes, levels, type AnalyticsSummary, type AnalyticsTimeseries, type OperationalLog, type OperationalLogPage, type LogCategory, type LogLevel, type AnalyticsRange, type AnalyticsInterval, type AnalyticsMetric, type SettingsFacts } from "./operationalTypes";

export class OperationalApiError extends Error {
  constructor(readonly status: number) { super(`Operational request failed (${status}).`); }
}
export function operationalErrorMessage(error: unknown, vi = false): string {
  const status = error instanceof OperationalApiError ? error.status : 0;
  const messages: Record<number, [string, string]> = {
    401: ["The workspace token was rejected. Connect again.", "Token bị từ chối. Hãy kết nối lại."],
    403: ["Access was denied for this host or origin.", "Máy chủ hoặc origin này bị từ chối truy cập."],
    404: ["Private workspace data is unavailable in this deployment.", "Dữ liệu workspace riêng tư không khả dụng ở triển khai này."],
    422: ["The selected range or filter is invalid. Reset the controls.", "Khoảng thời gian hoặc bộ lọc không hợp lệ. Hãy đặt lại."],
    502: ["The API returned an unsupported response. Refresh or check the backend.", "Phản hồi API không được hỗ trợ. Hãy làm mới hoặc kiểm tra backend."],
    503: ["The backend is temporarily unavailable. Try Refresh.", "Backend tạm thời không khả dụng. Hãy làm mới."],
  };
  if (status && !messages[status]) return vi ? `Yêu cầu vận hành thất bại (HTTP ${status}). Hãy làm mới.` : `The operational read failed (HTTP ${status}). Try Refresh.`;
  return (messages[status] ?? ["The backend could not be reached. Try Refresh.", "Không thể đọc dữ liệu backend. Hãy làm mới."])[vi ? 1 : 0];
}
const invalid = (): never => { throw new OperationalApiError(502); };
function object(value: unknown): Record<string, unknown> { return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : invalid(); }
function safeText(value: unknown, max = 128): string {
  if (typeof value !== "string" || value.length > max || /[\x00-\x1f\x7f]|(?:bearer\s|sk-[a-z0-9]{8}|[a-z]:[\\/]|\/home\/|\/users\/)/i.test(value)) return invalid();
  return value;
}
function timestamp(value: unknown): string { const text = safeText(value, 40); return Number.isFinite(Date.parse(text)) ? text : invalid(); }
function identifier(value: unknown, max = 128): string { const text = safeText(value, max); return /^[A-Za-z0-9][A-Za-z0-9._:-]*$/.test(text) && !/^(?:sk-|ghp_|github_pat_|xox[baprs]-|AIza)/i.test(text) ? text : invalid(); }
function number(value: unknown): number { return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : invalid(); }
function count(value: unknown): number { const result = number(value); return Number.isSafeInteger(result) ? result : invalid(); }
function nullable(value: unknown): number | null { return value === null ? null : number(value); }
function bool(value: unknown): boolean { return typeof value === "boolean" ? value : invalid(); }
function choice<T extends string>(value: unknown, values: readonly T[]): T { return values.includes(value as T) ? value as T : invalid(); }
function counts<T extends string>(value: unknown, keys: readonly T[]): Record<T, number> { const row = object(value); return Object.fromEntries(keys.map(key => [key, count(row[key])])) as Record<T, number>; }
function rate(value: unknown) { const row = object(value); const result = nullable(row.value); if (result !== null && result > 1) invalid(); return { value: result, numerator: count(row.numerator), denominator: count(row.denominator) }; }
export function projectSummary(value: unknown): AnalyticsSummary {
  const row = object(value), requests = object(row.requests), jobs = object(row.terminal_jobs), duration = object(requests.duration_ms);
  return { range: choice(row.range, analyticsRanges), started_at: timestamp(row.started_at), ended_at: timestamp(row.ended_at), requests: {
    terminal_count: count(requests.terminal_count), outcomes: counts(requests.outcomes, outcomes), success_rate: rate(requests.success_rate), failure_rate: rate(requests.failure_rate),
    duration_ms: { known_count: count(duration.known_count), unknown_count: count(duration.unknown_count), p50: nullable(duration.p50), p95: nullable(duration.p95) },
  }, terminal_jobs: { terminal_count: count(jobs.terminal_count), by_namespace: counts(jobs.by_namespace, ["pipeline", "evaluation", "model_test"]), by_outcome: counts(jobs.by_outcome, ["succeeded", "failed", "cancelled", "interrupted"]) } };
}
export function projectTimeseries(value: unknown): AnalyticsTimeseries {
  const row = object(value); if (!Array.isArray(row.points) || row.points.length > 720) invalid();
  const points = (row.points as unknown[]).map(value => { const p = object(value); return { started_at: timestamp(p.started_at), ended_at: timestamp(p.ended_at), value: nullable(p.value), denominator: count(p.denominator) }; });
  if (points.some((p, i) => Date.parse(p.started_at) >= Date.parse(p.ended_at) || (i > 0 && Date.parse(p.started_at) < Date.parse(points[i - 1].ended_at)))) invalid();
  return { range: choice(row.range, analyticsRanges), interval: choice(row.interval, analyticsIntervals), metric: choice(row.metric, analyticsMetrics), unit: choice(row.unit, ["count", "milliseconds"]), started_at: timestamp(row.started_at), ended_at: timestamp(row.ended_at), points };
}
export function projectLog(value: unknown): OperationalLog {
  const row = object(value), raw = object(row.metadata), metadata: OperationalLog["metadata"] = {};
  if (raw.http_method !== undefined) metadata.http_method = choice(raw.http_method, ["GET", "POST"]);
  for (const key of ["streaming", "decomposed"] as const) if (raw[key] !== undefined) metadata[key] = bool(raw[key]);
  if (raw.status_code !== undefined) { metadata.status_code = count(raw.status_code); if (metadata.status_code < 100 || metadata.status_code > 599) invalid(); }
  const optionalText = (value: unknown) => value === null || value === undefined ? null : identifier(value);
  const route = row.route_template === null || row.route_template === undefined ? null : safeText(row.route_template);
  if (route !== null && !["/query", "/query/decomposed", "/query/stream", "/query/decomposed/stream", "/search", "/retrieval/inspect"].includes(route)) invalid();
  return { record_id: identifier(row.record_id, 160), occurred_at: timestamp(row.occurred_at), category: choice(row.category, ["request", "job"]), level: choice(row.level, levels), kind: choice(row.kind, ["request_terminal", "job_terminal"]), subsystem: choice(row.subsystem, ["query", "search", "retrieval", "pipeline", "evaluation", "model_test"]), outcome: choice(row.outcome, outcomes), correlation_id: identifier(row.correlation_id), domain_id: optionalText(row.domain_id), route_template: route, error_code: optionalText(row.error_code), duration_ms: nullable(row.duration_ms), metadata };
}
export function projectLogPage(value: unknown): OperationalLogPage {
  const row = object(value); if (!Array.isArray(row.items) || row.items.length > 100) invalid();
  const limit = count(row.limit); if (limit < 1 || limit > 100) invalid();
  // Cursor is transport state only: never decode, interpret, or reconstruct it.
  const cursor = row.next_cursor === null ? null : typeof row.next_cursor === "string" && row.next_cursor.length <= 512 ? row.next_cursor : invalid();
  return { items: (row.items as unknown[]).map(projectLog), next_cursor: cursor, has_more: bool(row.has_more), limit };
}
export function createOperationalApi(options: { baseUrl?: string; fetchImpl?: typeof fetch } = {}) {
  const base = (options.baseUrl ?? getApiBaseUrl()).replace(/\/$/, "");
  const fetchImpl = options.fetchImpl ?? apiFetch;
  async function read(path: string, token: string | null, signal?: AbortSignal): Promise<unknown> {
    if (token !== null && !token.trim()) throw new OperationalApiError(401);
    const headers = new Headers({ Accept: "application/json" });
    if (token !== null) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetchImpl(`${base}${path}`, { method: "GET", headers, signal, cache: "no-store" });
    if (!response.ok) throw new OperationalApiError(response.status);
    try { return await response.json() as unknown; } catch { return invalid(); }
  }
  return {
    async summary(token: string, range: AnalyticsRange, signal?: AbortSignal) { return projectSummary(await read(`/analytics/summary?${new URLSearchParams({ range })}`, token, signal)); },
    async timeseries(token: string, range: AnalyticsRange, interval: AnalyticsInterval, metric: AnalyticsMetric, signal?: AbortSignal) { return projectTimeseries(await read(`/analytics/timeseries?${new URLSearchParams({ range, interval, metric })}`, token, signal)); },
    async logs(token: string, params: { category?: LogCategory; level?: LogLevel; cursor?: string; limit?: number } = {}, signal?: AbortSignal) {
      const query = new URLSearchParams({ limit: String(params.limit ?? 50) });
      for (const key of ["category", "level", "cursor"] as const) if (params[key]) query.set(key, params[key]);
      return projectLogPage(await read(`/logs?${query}`, token, signal));
    },
    async configuration(token: string, signal?: AbortSignal): Promise<LocalWorkspaceConfigurationStatus> {
      const row = object(await read("/system/configuration-status", token, signal)), caps = object(row.capabilities);
      return { deployment_mode: choice(row.deployment_mode, ["local", "public"]), capabilities: { public_provider_free: bool(caps.public_provider_free), local_workspace: bool(caps.local_workspace), execution_jobs: bool(caps.execution_jobs) } };
    },
    async settingsFacts(signal?: AbortSignal): Promise<SettingsFacts> {
      const row = object(await read("/system/info", null, signal)), retrieval = object(row.retrieval);
      return { api_version: safeText(row.api_version), default_retrieval: safeText(retrieval.default) };
    },
    async providerStatus(signal?: AbortSignal) {
      const row = object(await read("/models", null, signal));
      if (!Array.isArray(row.items)) invalid();
      const generators = (row.items as unknown[]).map(object).filter(item => item.role === "generator");
      if (generators.length !== 1) invalid();
      const generator = generators[0];
      return { provider: choice(generator.provider, ["groq"]), configuration_status: choice(generator.configuration_status, ["configured", "not_configured"]), credential_status: choice(generator.credential_status, ["configured", "not_configured", "not_required"]), availability_status: choice(generator.availability_status, ["available", "unavailable", "unknown"]) };
    },
  };
}
export const operationalApi = createOperationalApi();
