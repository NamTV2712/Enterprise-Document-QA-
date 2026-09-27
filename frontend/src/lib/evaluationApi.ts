import { getApiBaseUrl } from "./api";
import type {
  EvaluationJob, EvaluationJobCreate, EvaluationJobEvent, EvaluationJobState, EvaluationMetrics,
  EvaluationPage, FailureCategory, NativeCaseMetric, NativeCompareRequest, NativeComparison,
  NativeFailures, NativeMetricDefinition, NativeMetricId, NativeResultsPage, NativeTrends,
  PublishedDetail, PublishedSummary, SafeJobResults,
} from "./evaluationTypes";

export class EvaluationApiError extends Error {
  constructor(readonly status: number) {
    super(evaluationErrorMessage(status));
    this.name = "EvaluationApiError";
  }
}
export function evaluationErrorMessage(status: number, locale: "en" | "vi" = "en"): string {
  const messages: Record<number, [string, string]> = {
    0: ["The backend could not be reached. Check the connection and try again.", "Không thể kết nối backend. Kiểm tra kết nối và thử lại."],
    401: ["The workspace token was rejected. Connect again.", "Token workspace bị từ chối. Hãy kết nối lại."],
    403: ["Access or execution was denied from this host or origin.", "Truy cập hoặc thực thi bị từ chối từ host hoặc origin này."],
    404: ["Evaluation is unavailable here or this record was not found.", "Đánh giá không khả dụng hoặc không tìm thấy bản ghi này."],
    409: ["Revision, state or report compatibility conflict. Reload to reconcile; no overwrite was made.", "Xung đột phiên bản, trạng thái hoặc báo cáo. Tải lại để đối chiếu; không ghi đè."],
    422: ["The evaluation request was refused. Check its artifact, metrics, budget or filters.", "Yêu cầu đánh giá bị từ chối. Kiểm tra artifact, chỉ số, ngân sách hoặc bộ lọc."],
    428: ["A current job revision is required. Reload the job.", "Cần phiên bản job hiện tại. Hãy tải lại job."],
    502: ["The evaluation response was invalid. Reload to try again.", "Phản hồi đánh giá không hợp lệ. Hãy tải lại."],
    503: ["The evaluation workspace is temporarily unavailable.", "Workspace đánh giá tạm thời không khả dụng."],
  };
  return messages[status]?.[locale === "vi" ? 1 : 0]
    ?? (locale === "vi" ? `Yêu cầu đánh giá thất bại (HTTP ${status}).` : `Evaluation request failed (HTTP ${status}).`);
}
export interface PageParams { page?: number; page_size?: number }
export interface ReportListParams extends PageParams { status?: "official" | "candidate" | "historical" | "complete" | "incomplete" }
export interface TrendParams extends PageParams { metric_id: NativeMetricId; binding_group?: string; start_at?: string; end_at?: string }
export interface FailureParams extends PageParams { run_id: string; category?: FailureCategory }
export interface EvaluationApiClient {
  getMetrics(signal?: AbortSignal): Promise<EvaluationMetrics>;
  listReports(params?: ReportListParams, signal?: AbortSignal): Promise<EvaluationPage<PublishedSummary>>;
  getReport(runId: string, signal?: AbortSignal): Promise<PublishedDetail>;
  getResults(runId: string, params?: PageParams & { case_id?: string }, signal?: AbortSignal): Promise<NativeResultsPage>;
  compare(body: NativeCompareRequest, signal?: AbortSignal): Promise<NativeComparison>;
  getTrends(params: TrendParams, signal?: AbortSignal): Promise<NativeTrends>;
  getFailures(params: FailureParams, signal?: AbortSignal): Promise<NativeFailures>;
  listJobs(token: string, params?: PageParams & { state?: EvaluationJobState }, signal?: AbortSignal): Promise<EvaluationPage<EvaluationJob>>;
  createJob(token: string, body: EvaluationJobCreate, idempotencyKey: string, signal?: AbortSignal): Promise<EvaluationJob>;
  getJob(token: string, jobId: string, signal?: AbortSignal): Promise<EvaluationJob>;
  getJobResults(token: string, jobId: string, params?: PageParams, signal?: AbortSignal): Promise<SafeJobResults>;
  cancelJob(token: string, jobId: string, revision: number, signal?: AbortSignal): Promise<EvaluationJob>;
  getJobEvents(token: string, jobId: string, afterSequence: number, signal?: AbortSignal): Promise<EvaluationJobEvent[]>;
}

const metricIds = new Set<string>([
  "native.faithfulness", "native.answer_relevancy", "native.context_precision",
  "native.citation_index_validity", "native.keyword_recall_proxy", "native.fallback_correctness",
]);
const jobStates = new Set<string>(["queued", "running", "cancelling", "cancelled", "succeeded", "failed", "interrupted"]);
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new EvaluationApiError(502);
  return value as Record<string, unknown>;
}
function string(value: unknown): string {
  if (typeof value !== "string") throw new EvaluationApiError(502);
  return value;
}
function nullableString(value: unknown): string | null { return value === null ? null : string(value); }
function count(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) throw new EvaluationApiError(502);
  return value;
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new EvaluationApiError(502);
  return value;
}
function metric(value: unknown): NativeCaseMetric {
  const item = object(value);
  const id = string(item.metric_id);
  if (!metricIds.has(id) || !["computed", "unavailable", "not_applicable"].includes(string(item.status))) throw new EvaluationApiError(502);
  const status = item.status as NativeCaseMetric["status"];
  if (status === "computed") {
    if (id === "native.fallback_correctness" ? typeof item.value !== "boolean"
      : typeof item.value !== "number" || !Number.isFinite(item.value) || item.value < 0 || item.value > 1) throw new EvaluationApiError(502);
  } else if (item.value !== null) throw new EvaluationApiError(502);
  return {
    metric_id: id as NativeMetricId, metric_version: count(item.metric_version), status,
    value: item.value as number | boolean | null, reason_code: nullableString(item.reason_code),
  };
}
/** Projection, not a cast: hidden private case text never reaches React state. */
function safeJobResults(value: unknown): SafeJobResults {
  const page = object(value);
  const reportStatus = page.report_status;
  if (reportStatus !== null && reportStatus !== "complete" && reportStatus !== "incomplete") throw new EvaluationApiError(502);
  return {
    job_id: string(page.job_id), total: count(page.total), page: count(page.page), page_size: count(page.page_size),
    report_status: reportStatus as SafeJobResults["report_status"], report_digest: nullableString(page.report_digest),
    // These arrays are public protocol DTOs, not private case inputs.
    metric_definitions: array(page.metric_definitions).map((entry) => {
      const item = object(entry);
      return {
        metric_id: item.metric_id, metric_version: item.metric_version, label: item.label, meaning: item.meaning,
        value_kind: item.value_kind, aggregate_kind: item.aggregate_kind, direction: item.direction,
        source: item.source, minimum: item.minimum, maximum: item.maximum, required_inputs: item.required_inputs,
      } as NativeMetricDefinition;
    }),
    aggregates: array(page.aggregates).map((entry) => {
      const item = object(entry);
      if (!metricIds.has(string(item.metric_id))) throw new EvaluationApiError(502);
      const status = string(item.status);
      if (!["computed", "unavailable", "not_applicable"].includes(status)
        || (status === "computed" ? typeof item.value !== "number" || !Number.isFinite(item.value) : item.value !== null)) throw new EvaluationApiError(502);
      return {
        metric_id: item.metric_id as NativeMetricId, metric_version: count(item.metric_version),
        status: status as NativeCaseMetric["status"], value: item.value as number | null,
        total_cases: count(item.total_cases), denominator: count(item.denominator),
        unavailable_count: count(item.unavailable_count), not_applicable_count: count(item.not_applicable_count),
      };
    }),
    items: array(page.items).map((entry) => {
      const item = object(entry);
      const input = object(item.input);
      return {
        case_id: string(item.case_id), metrics: array(item.metrics).map(metric),
        generation_context_sha256: nullableString(input.generation_context_sha256),
        judge_context_sha256: nullableString(input.judge_context_sha256), judge_prompt_sha256: string(item.judge_prompt_sha256),
      };
    }),
  };
}
function parseEvents(text: string, jobId: string, afterSequence: number): EvaluationJobEvent[] {
  const result: EvaluationJobEvent[] = [];
  let previous = afterSequence;
  const seen = new Map<number, string>();
  for (const frame of text.replace(/\r\n?/g, "\n").split("\n\n")) {
    const lines = frame.split("\n");
    const data = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join("\n");
    if (!data) continue;
    let parsed: unknown;
    try { parsed = JSON.parse(data); } catch { throw new EvaluationApiError(502); }
    const item = object(parsed);
    const id = lines.find((line) => line.startsWith("id:"))?.slice(3).trim();
    if (!id || !/^(0|[1-9][0-9]*)$/.test(id)) throw new EvaluationApiError(502);
    const sequence = count(Number(id));
    if (sequence !== item.sequence || string(item.job_id) !== jobId || !Number.isFinite(Date.parse(string(item.occurred_at)))) throw new EvaluationApiError(502);
    if (item.state !== null && !jobStates.has(string(item.state))) throw new EvaluationApiError(502);
    if (sequence <= afterSequence) continue;
    if (seen.get(sequence) === data) continue;
    if (sequence <= previous) throw new EvaluationApiError(502);
    const progress = object(item.progress);
    result.push({
      event_id: string(item.event_id), job_id: jobId, sequence, event_type: string(item.event_type),
      state: item.state as EvaluationJobState | null, reason_code: nullableString(item.reason_code),
      occurred_at: string(item.occurred_at), progress: {
        stage: nullableString(progress.stage), current: progress.current === null ? null : count(progress.current),
        total: progress.total === null ? null : count(progress.total),
      },
    });
    seen.set(sequence, data);
    previous = sequence;
  }
  if (result.length > 100) throw new EvaluationApiError(502);
  return result;
}
function isAbort(error: unknown): boolean {
  return !!error && typeof error === "object" && "name" in error && error.name === "AbortError";
}
function query(params: Record<string, string | number | undefined>): string {
  return new URLSearchParams(Object.entries(params).flatMap(([key, value]) => value === undefined ? [] : [[key, String(value)]])).toString();
}
export function createEvaluationApiClient(options: { baseUrl?: string; fetchImpl?: typeof fetch } = {}): EvaluationApiClient {
  const base = (options.baseUrl ?? getApiBaseUrl()).replace(/\/$/, "");
  const fetchImpl = options.fetchImpl ?? ((input: RequestInfo | URL, init?: RequestInit) => fetch(input, init));
  async function request(path: string, init: RequestInit, token?: string): Promise<Response> {
    const headers = new Headers(init.headers);
    if (!headers.has("Accept")) headers.set("Accept", "application/json");
    if (base.includes("ngrok") || (typeof window !== "undefined" && window.location.hostname.includes("ngrok"))) headers.set("ngrok-skip-browser-warning", "true");
    if (token !== undefined) {
      if (!token.trim()) throw new EvaluationApiError(401);
      headers.set("Authorization", `Bearer ${token}`);
    }
    let response: Response;
    try { response = await fetchImpl(`${base}${path}`, { cache: "no-store", credentials: "omit", ...init, headers }); }
    catch (error) { if (isAbort(error)) throw error; throw new EvaluationApiError(0); }
    if (!response.ok) throw new EvaluationApiError(response.status);
    return response;
  }
  async function json<T>(path: string, init: RequestInit, token?: string): Promise<T> {
    const response = await request(path, init, token);
    try { return await response.json() as T; }
    catch (error) { if (isAbort(error)) throw error; throw new EvaluationApiError(502); }
  }
  const get = (signal?: AbortSignal): RequestInit => ({ method: "GET", signal });
  const resultsQuery = (params: PageParams = {}) => query({ page: params.page ?? 1, page_size: params.page_size ?? 50 });
  const jobPath = (id: string) => `/evaluation/jobs/${encodeURIComponent(id)}`;
  return {
    getMetrics: (signal) => json("/evaluation/metrics", get(signal)),
    listReports: (params = {}, signal) => json(`/evaluation/runs?${query({ page: params.page ?? 1, page_size: params.page_size ?? 20, status: params.status })}`, get(signal)),
    async getReport(id, signal) {
      const value = object(await json<unknown>(`/evaluation/runs/${encodeURIComponent(id)}`, get(signal)));
      if (value.run_id !== id) throw new EvaluationApiError(502);
      if (value.protocol === "native-evaluation") return value as unknown as PublishedDetail;
      // Legacy compatibility is metadata-only; no richer case-text fallback.
      const cases = array(value.cases).map((entry) => {
        const item = object(entry);
        return { case_id: string(item.case_id), status: item.status as "OK" | "ERROR" | "MISSING", scores: object(item.scores) as Record<string, number> };
      });
      return {
        run_id: id, title: string(value.title), status: value.status as "official" | "candidate" | "historical" | "incomplete",
        created_at: string(value.created_at), provenance: object(value.provenance) as Record<string, string>,
        aggregate: object(value.aggregate) as Record<string, number>, case_count: cases.length, cases,
      };
    },
    getResults: (id, params = {}, signal) => json(`/evaluation/runs/${encodeURIComponent(id)}/results?${query({ page: params.page ?? 1, page_size: params.page_size ?? 50, case_id: params.case_id, sort: "case_id_asc" })}`, get(signal)),
    compare: (body, signal) => json("/evaluation/compare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal }),
    getTrends: (params, signal) => json(`/evaluation/metrics/trends?${query({ ...params, sort: "published_at_asc", page: params.page ?? 1, page_size: params.page_size ?? 50 })}`, get(signal)),
    getFailures: (params, signal) => json(`/evaluation/failures?${query({ ...params, sort: "category_case_metric_asc", page: params.page ?? 1, page_size: params.page_size ?? 50 })}`, get(signal)),
    listJobs: (token, params = {}, signal) => json(`/evaluation/jobs?${query({ page: params.page ?? 1, page_size: params.page_size ?? 25, state: params.state })}`, get(signal), token),
    createJob: (token, body, key, signal) => json("/evaluation/jobs", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": key }, body: JSON.stringify(body), signal }, token),
    getJob: (token, id, signal) => json(jobPath(id), get(signal), token),
    async getJobResults(token, id, params, signal) {
      const result = safeJobResults(await json<unknown>(`${jobPath(id)}/results?${resultsQuery(params)}`, get(signal), token));
      if (result.job_id !== id) throw new EvaluationApiError(502);
      return result;
    },
    cancelJob: (token, id, revision, signal) => json(`${jobPath(id)}/cancel`, { method: "POST", headers: { "If-Match": `"${revision}"` }, signal }, token),
    async getJobEvents(token, id, after, signal) {
      if (!Number.isSafeInteger(after) || after < 0) throw new EvaluationApiError(422);
      const response = await request(`${jobPath(id)}/events`, { ...get(signal), headers: { Accept: "text/event-stream", "Last-Event-ID": String(after) } }, token);
      let body: string;
      try { body = await response.text(); } catch (error) { if (isAbort(error)) throw error; throw new EvaluationApiError(502); }
      return parseEvents(body, id, after);
    },
  };
}
export const evaluationApi = createEvaluationApiClient();
