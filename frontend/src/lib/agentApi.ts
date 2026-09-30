import { apiFetch, getApiBaseUrl } from "./api";
import type {
  AgentCreateRequest, AgentEvaluationReport, AgentEvent, AgentRun, AgentRunPage, AgentRunResult,
} from "./agentTypes";

export class AgentApiError extends Error {
  constructor(readonly status: number) {
    super(`Agent API request failed (${status})`);
    this.name = "AgentApiError";
  }
}

function object(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new AgentApiError(502);
  return value as Record<string, unknown>;
}

export function parseAgentSseBatch(body: string, runId: string, afterSequence: number): AgentEvent[] {
  if (!Number.isSafeInteger(afterSequence) || afterSequence < 0) throw new AgentApiError(422);
  const events: AgentEvent[] = [];
  let previous = afterSequence;
  for (const frame of body.replace(/\r\n/g, "\n").split("\n\n")) {
    if (!frame.trim()) continue;
    let id = "";
    const data: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("id:")) id = line.slice(3).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (data.length === 0) continue;
    let raw: Record<string, unknown>;
    try { raw = object(JSON.parse(data.join("\n")) as unknown); }
    catch { throw new AgentApiError(502); }
    const sequence = Number(id);
    if (!/^[1-9][0-9]*$/.test(id) || !Number.isSafeInteger(sequence) || sequence <= previous
      || raw.sequence !== sequence || raw.run_id !== runId || typeof raw.event_id !== "string"
      || typeof raw.event_type !== "string" || typeof raw.occurred_at !== "string"
      || !Number.isFinite(Date.parse(raw.occurred_at))) throw new AgentApiError(502);
    previous = sequence;
    events.push(raw as unknown as AgentEvent);
  }
  return events;
}

async function agentRequest(path: string, token: string, init: RequestInit = {}): Promise<Response> {
  if (!token.trim()) throw new AgentApiError(401);
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  try {
    const response = await apiFetch(`${getApiBaseUrl()}${path}`, {
      ...init, headers, cache: "no-store", credentials: "omit",
    });
    if (!response.ok) throw new AgentApiError(response.status);
    return response;
  } catch (error) {
    if (error instanceof AgentApiError || (error instanceof Error && error.name === "AbortError")) throw error;
    throw new AgentApiError(0);
  }
}

async function agentJson<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await agentRequest(path, token, init);
  try { return await response.json() as T; }
  catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error;
    throw new AgentApiError(502);
  }
}

const pathFor = (runId: string) => `/agent/runs/${encodeURIComponent(runId)}`;

export const agentApi = {
  listRuns(token: string, page = 1, signal?: AbortSignal): Promise<AgentRunPage> {
    return agentJson(`/agent/runs?page=${page}&page_size=25`, token, { signal });
  },
  async getRun(token: string, runId: string, signal?: AbortSignal): Promise<AgentRun> {
    const run = await agentJson<AgentRun>(pathFor(runId), token, { signal });
    if (run.run_id !== runId) throw new AgentApiError(502);
    return run;
  },
  async getResult(token: string, runId: string, signal?: AbortSignal): Promise<AgentRunResult> {
    const result = await agentJson<AgentRunResult>(`${pathFor(runId)}/results`, token, { signal });
    if (result.run_id !== runId) throw new AgentApiError(502);
    return result;
  },
  async getEvaluation(token: string, runId: string, signal?: AbortSignal): Promise<AgentEvaluationReport> {
    const report = await agentJson<AgentEvaluationReport>(`${pathFor(runId)}/evaluation`, token, { signal });
    if (report.run_id !== runId || report.protocol !== "native-agent-evaluation" || report.protocol_version !== 1
      || !Array.isArray(report.metrics) || !Array.isArray(report.metric_definitions)
      || report.metrics.length !== report.metric_definitions.length) throw new AgentApiError(502);
    return report;
  },
  cancelRun(token: string, runId: string, revision: number, signal?: AbortSignal): Promise<AgentRun> {
    if (!Number.isSafeInteger(revision) || revision < 1) throw new AgentApiError(422);
    return agentJson(pathFor(runId) + "/cancel", token, {
      method: "POST", headers: { "If-Match": `"${revision}"` }, signal,
    });
  },
  createRun(token: string, body: AgentCreateRequest, idempotencyKey: string, signal?: AbortSignal): Promise<AgentRun> {
    return agentJson("/agent/runs", token, {
      method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(body), signal,
    });
  },
  async getEvents(token: string, runId: string, afterSequence: number, signal?: AbortSignal): Promise<AgentEvent[]> {
    if (!Number.isSafeInteger(afterSequence) || afterSequence < 0) throw new AgentApiError(422);
    const response = await agentRequest(`${pathFor(runId)}/events`, token, {
      headers: { Accept: "text/event-stream", "Last-Event-ID": String(afterSequence) }, signal,
    });
    let body: string;
    try { body = await response.text(); }
    catch (error) {
      if (error instanceof Error && error.name === "AbortError") throw error;
      throw new AgentApiError(502);
    }
    return parseAgentSseBatch(body, runId, afterSequence);
  },
};
