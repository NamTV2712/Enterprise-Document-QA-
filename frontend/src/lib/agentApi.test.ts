import { afterEach, describe, expect, it, vi } from "vitest";

import { agentApi, AgentApiError, parseAgentSseBatch } from "./agentApi";

const RUN = "agent_abc123";
const TOKEN = "synthetic-agent-token";

afterEach(() => vi.unstubAllGlobals());

describe("private Agent API client", () => {
  it("uses the shared fetch boundary with header-only bearer and exact revision", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => Response.json({ run_id: RUN, state: "cancelling" }, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await agentApi.cancelRun(TOKEN, RUN, 12);
    const [url, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(url).toContain(`/agent/runs/${RUN}/cancel`);
    expect(url).not.toContain(TOKEN);
    expect(headers.get("Authorization")).toBe(`Bearer ${TOKEN}`);
    expect(headers.get("If-Match")).toBe('"12"');
    expect(init?.credentials).toBe("omit");
  });

  it("passes a stable numeric cursor in the Last-Event-ID header", async () => {
    const event = { run_id: RUN, event_id: "event_4", sequence: 4, event_type: "state_changed", state: "running", reason_code: null, occurred_at: "2026-09-30T00:00:00Z", summary: null };
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => new Response(`id: 4\nevent: state_changed\ndata: ${JSON.stringify(event)}\n\n`, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await agentApi.getEvents(TOKEN, RUN, 3)).toEqual([event]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).not.toContain(TOKEN);
    expect(new Headers(init?.headers).get("Last-Event-ID")).toBe("3");
  });

  it("rejects replayed, reordered and cross-run SSE events", () => {
    const event = { run_id: RUN, event_id: "event_4", sequence: 4, event_type: "created", state: "queued", reason_code: null, occurred_at: "2026-09-30T00:00:00Z", summary: null };
    const frame = `id: 4\ndata: ${JSON.stringify(event)}\n\n`;
    expect(() => parseAgentSseBatch(frame, RUN, 4)).toThrow(AgentApiError);
    expect(() => parseAgentSseBatch(frame + frame, RUN, 3)).toThrow(AgentApiError);
    expect(() => parseAgentSseBatch(frame, "agent_other", 3)).toThrow(AgentApiError);
    expect(() => parseAgentSseBatch("id: 4\ndata: {bad}\n\n", RUN, 3)).toThrow(AgentApiError);
  });

  it("preserves endpoint status but never displays raw server error text", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Bearer synthetic-secret" }), { status: 409 })));
    await expect(agentApi.getEvaluation(TOKEN, RUN)).rejects.toMatchObject({ status: 409, message: "Agent API request failed (409)" });
  });

  it("rejects a report bound to another run", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ run_id: "agent_other", protocol: "native-agent-evaluation", protocol_version: 1, metrics: [], metric_definitions: [] })));
    await expect(agentApi.getEvaluation(TOKEN, RUN)).rejects.toMatchObject({ status: 502 });
  });
});
