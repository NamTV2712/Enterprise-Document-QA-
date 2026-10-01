import { getApiBaseUrl } from "./api";
import type {
  LocalWorkspaceConfigurationStatus,
  PipelineDefinition,
  PipelineRun,
  PipelineRunEvent,
  PipelineRunPage,
  PipelineRunState,
} from "../types";

export class PipelineApiError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(pipelineErrorMessage(status));
    this.name = "PipelineApiError";
    this.status = status;
  }
}

export function pipelineErrorMessage(status: number, locale: "en" | "vi" = "en"): string {
  if (locale === "vi") {
    if (status === 401) return "Token workspace không được chấp nhận. Hãy kết nối lại.";
    if (status === 403) return "API đã từ chối quyền truy cập từ máy chủ hoặc origin này.";
    if (status === 404) return "Workspace cục bộ không khả dụng hoặc không tìm thấy run này.";
    if (status === 409) return "Run đã thay đổi. Hãy làm mới trước khi thử lại.";
    if (status === 422) return "Yêu cầu staging không được chấp nhận. Hãy kiểm tra ticker đã chọn.";
    if (status === 503) return "Workspace cục bộ tạm thời không khả dụng.";
    return `Yêu cầu Pipeline thất bại (HTTP ${status}).`;
  }
  if (status === 401) return "The workspace token was rejected. Connect again.";
  if (status === 403) return "The API denied access from this host or origin.";
  if (status === 404) return "The local workspace is unavailable or this run was not found.";
  if (status === 409) return "This run changed. Refresh it before trying again.";
  if (status === 422) return "The staging request was not accepted. Check the selected tickers.";
  if (status === 503) return "The local workspace is temporarily unavailable.";
  return `Pipeline request failed (HTTP ${status}).`;
}

export interface PipelineRunListParams {
  page?: number;
  page_size?: number;
  state?: PipelineRunState | "all";
}

export interface PipelineStageRequest {
  input_ids: string[];
  staging_profile: "isolated";
}

export interface PipelineApiClient {
  getDefinition(signal?: AbortSignal): Promise<PipelineDefinition>;
  verifyLocalWorkspaceToken(token: string, signal?: AbortSignal): Promise<LocalWorkspaceConfigurationStatus>;
  listRuns(token: string, params?: PipelineRunListParams, signal?: AbortSignal): Promise<PipelineRunPage>;
  getRun(token: string, runId: string, signal?: AbortSignal): Promise<PipelineRun>;
  stageRun(token: string, body: PipelineStageRequest, signal?: AbortSignal): Promise<PipelineRun>;
  cancelRun(token: string, runId: string, revision: number, signal?: AbortSignal): Promise<PipelineRun>;
  getRunEvents(token: string, runId: string, afterSequence: number, signal?: AbortSignal): Promise<PipelineRunEvent[]>;
}

function parseSseBatch(text: string, runId: string, afterSequence: number): PipelineRunEvent[] {
  const events: PipelineRunEvent[] = [];
  let previous = afterSequence;
  const frames = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n\n");
  for (const frame of frames) {
    if (!frame.trim()) continue;
    let id: string | null = null;
    const data: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("id:")) id = line.slice(3).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (data.length === 0) continue;
    let event: PipelineRunEvent;
    try {
      event = JSON.parse(data.join("\n")) as PipelineRunEvent;
    } catch {
      throw new PipelineApiError(502);
    }
    const sequence = Number(id);
    if (
      !Number.isSafeInteger(sequence)
      || sequence <= previous
      || event.sequence !== sequence
      || event.run_id !== runId
      || !Number.isFinite(Date.parse(event.occurred_at))
    ) {
      throw new PipelineApiError(502);
    }
    previous = sequence;
    events.push(event);
  }
  return events;
}

export function createPipelineApiClient(
  options: { baseUrl?: string; fetchImpl?: typeof fetch } = {},
): PipelineApiClient {
  const baseUrl = (options.baseUrl ?? getApiBaseUrl()).replace(/\/$/, "");
  const fetchImpl = options.fetchImpl ?? ((input: RequestInfo | URL, init?: RequestInit) => fetch(input, init));

  const request = async (
    path: string,
    init: RequestInit,
    token?: string,
  ): Promise<Response> => {
    const headers = new Headers(init.headers);
    const isNgrokRequest = baseUrl.includes("ngrok")
      || (typeof window !== "undefined" && window.location.hostname.includes("ngrok"));
    if (isNgrokRequest) headers.set("ngrok-skip-browser-warning", "true");
    if (token !== undefined) {
      if (!token.trim()) throw new PipelineApiError(401);
      headers.set("Authorization", `Bearer ${token}`);
    }
    const response = await fetchImpl(`${baseUrl}${path}`, { ...init, headers });
    if (!response.ok) throw new PipelineApiError(response.status);
    return response;
  };

  const json = async <T>(path: string, init: RequestInit, token?: string): Promise<T> => {
    const response = await request(path, init, token);
    try {
      return await response.json() as T;
    } catch {
      throw new PipelineApiError(502);
    }
  };

  return {
    getDefinition(signal) {
      return json<PipelineDefinition>("/pipeline", {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal,
      });
    },
    verifyLocalWorkspaceToken(token, signal) {
      return json<LocalWorkspaceConfigurationStatus>("/system/configuration-status", {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal,
      }, token);
    },
    listRuns(token, params = {}, signal) {
      const query = new URLSearchParams({
        page: String(params.page ?? 1),
        page_size: String(params.page_size ?? 25),
      });
      if (params.state && params.state !== "all") query.set("state", params.state);
      return json<PipelineRunPage>(`/pipeline/runs?${query.toString()}`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal,
      }, token);
    },
    getRun(token, runId, signal) {
      return json<PipelineRun>(`/pipeline/runs/${encodeURIComponent(runId)}`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal,
      }, token);
    },
    stageRun(token, body, signal) {
      return json<PipelineRun>("/pipeline/runs", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
      }, token);
    },
    cancelRun(token, runId, revision, signal) {
      return json<PipelineRun>(`/pipeline/runs/${encodeURIComponent(runId)}/cancel`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "If-Match": `"${revision}"`,
        },
        signal,
      }, token);
    },
    async getRunEvents(token, runId, afterSequence, signal) {
      const response = await request(`/pipeline/runs/${encodeURIComponent(runId)}/events`, {
        method: "GET",
        headers: {
          Accept: "text/event-stream",
          "Last-Event-ID": String(afterSequence),
        },
        cache: "no-store",
        signal,
      }, token);
      let body: string;
      try {
        body = await response.text();
      } catch {
        throw new PipelineApiError(502);
      }
      return parseSseBatch(body, runId, afterSequence);
    },
  };
}

export const pipelineApi = createPipelineApiClient();
