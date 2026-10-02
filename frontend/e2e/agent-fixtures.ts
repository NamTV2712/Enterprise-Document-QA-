import type { Page, Route } from "@playwright/test";

import { API_ORIGIN, installApiFixtures } from "./fixtures";
import type { AgentEvent, AgentRun } from "../src/lib/agentTypes";
import { agentEvaluation, agentEvents, agentProviderRun, agentResearchRun, agentRunningRun } from "../src/test/agentFixtures";

export const AGENT_FIXTURE_TOKEN = "ui014-synthetic-local-token";
const CORS = {
  "access-control-allow-origin": "http://localhost:4173",
  "access-control-allow-headers": "Authorization, Content-Type, If-Match, Last-Event-ID, Idempotency-Key",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-expose-headers": "ETag",
};

export interface AgentFixtureCall { method: string; path: string; lastEventId: string | null; ifMatch: string | null; authorized: boolean }
export interface AgentFixture {
  runs: Map<string, AgentRun>;
  calls: AgentFixtureCall[];
  cancelCount: () => number;
  createCount: () => number;
  forceConflictOnce: () => void;
  advanceRun: (run: AgentRun) => void;
}

async function json(route: Route, status: number, body: unknown, headers: Record<string, string> = {}) {
  await route.fulfill({ status, headers: { ...CORS, "content-type": "application/json", ...headers }, body: JSON.stringify(body) });
}

function lifecycleEvent(run: AgentRun, sequence: number, eventType: string): AgentEvent {
  return { run_id: run.run_id, event_id: `${run.run_id}-event-${sequence}`, sequence, event_type: eventType,
    state: run.state, reason_code: null, occurred_at: run.updated_at, summary: null };
}

function eventsFor(run: AgentRun): AgentEvent[] {
  if (run.run_id === agentResearchRun.run_id) return agentEvents;
  if (run.state === "running") return [lifecycleEvent({ ...run, state: "queued" }, 1, "created"),
    lifecycleEvent(run, 2, "state_changed"), lifecycleEvent(run, 3, "step_changed")];
  return [lifecycleEvent({ ...run, state: "queued" }, 1, "created"),
    lifecycleEvent({ ...run, state: "running" }, 2, "state_changed"),
    lifecycleEvent({ ...run, state: "running" }, 3, "step_changed"), lifecycleEvent(run, 4, "state_changed")];
}

export async function installAgentFixture(page: Page, options: {
  initialRuns?: AgentRun[]; executionEnabled?: boolean; mode?: "local" | "public"; decisionProviderAvailable?: boolean; createdRun?: AgentRun;
} = {}): Promise<AgentFixture> {
  await installApiFixtures(page);
  const mode = options.mode ?? "local";
  const executionEnabled = options.executionEnabled ?? true;
  const runs = new Map((options.initialRuns ?? [agentResearchRun, agentProviderRun, agentRunningRun]).map((run) => [run.run_id, run]));
  const events = new Map([...runs.values()].map((run) => [run.run_id, eventsFor(run)]));
  const calls: AgentFixtureCall[] = [];
  let cancelCount = 0, createCount = 0, conflictOnce = false;
  const hasAuth = (route: Route) => route.request().headers().authorization === `Bearer ${AGENT_FIXTURE_TOKEN}`;
  const privateAccess = async (route: Route) => {
    if (mode !== "local") { await json(route, 404, { detail: "Local workspace capability unavailable" }); return false; }
    if (!hasAuth(route)) { await json(route, 401, { detail: "Local workspace authentication required" }); return false; }
    return true;
  };

  await page.route(`${API_ORIGIN}/system/configuration-status`, async (route) => {
    if (route.request().method() === "OPTIONS") { await route.fulfill({ status: 204, headers: CORS }); return; }
    if (!await privateAccess(route)) return;
    await json(route, 200, { deployment_mode: "local", agent_decision_provider: { available: options.decisionProviderAvailable === true }, capabilities: {
      public_provider_free: true, local_workspace: true, execution_jobs: executionEnabled,
    } });
  });

  await page.route(`${API_ORIGIN}/agent/runs**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = decodeURIComponent(url.pathname);
    const method = request.method();
    if (method === "OPTIONS") { await route.fulfill({ status: 204, headers: CORS }); return; }
    calls.push({ method, path, lastEventId: request.headers()["last-event-id"] ?? null,
      ifMatch: request.headers()["if-match"] ?? null, authorized: hasAuth(route) });
    if (!await privateAccess(route)) return;
    if (path === "/agent/runs" && method === "GET") {
      const pageNumber = Number(url.searchParams.get("page") ?? "1");
      const pageSize = Number(url.searchParams.get("page_size") ?? "25");
      const ordered = [...runs.values()];
      await json(route, 200, { items: ordered.slice((pageNumber - 1) * pageSize, pageNumber * pageSize),
        total: ordered.length, page: pageNumber, page_size: pageSize });
      return;
    }
    if (path === "/agent/runs" && method === "POST") {
      if (!executionEnabled) { await json(route, 403, { detail: "Execution disabled" }); return; }
      if (!request.headers()["idempotency-key"]) { await json(route, 422, { detail: "Idempotency-Key required" }); return; }
      createCount += 1;
      const body = request.postDataJSON() as { goal: string; locale: "en" | "vi" };
      const id = `agent_created_${createCount}`;
      const template = options.createdRun ?? agentProviderRun;
      const created: AgentRun = { ...template, run_id: id, frozen: { ...template.frozen, goal: body.goal, locale: body.locale }, revision: options.createdRun?.revision ?? 4 };
      runs.set(id, created);
      events.set(id, eventsFor(created));
      await json(route, 201, { ...created, state: "queued", revision: 1, result: null, failure: null }, { ETag: '"1"' });
      return;
    }
    const match = path.match(/^\/agent\/runs\/(agent_[A-Za-z0-9_-]+)(?:\/(results|evaluation|events|cancel))?$/);
    if (!match) { await json(route, 404, { detail: "Agent run was not found" }); return; }
    const id = match[1], action = match[2] ?? "detail";
    const run = runs.get(id);
    if (!run) { await json(route, 404, { detail: "Agent run was not found" }); return; }
    if (action === "detail" && method === "GET") { await json(route, 200, run, { ETag: `"${run.revision}"` }); return; }
    if (action === "results" && method === "GET") { await json(route, 200, { run_id: id, state: run.state, revision: run.revision, result: run.result, failure: run.failure }); return; }
    if (action === "evaluation" && method === "GET") {
      if (run.state === "running" || run.state === "queued" || run.state === "cancelling") {
        await json(route, 409, { detail: "Agent evaluation requires a terminal run" }); return;
      }
      const research = run.frozen.research !== null;
      const report = { ...agentEvaluation, run_id: id,
        metrics: agentEvaluation.metrics.map((item) => !research && ["objective_coverage", "unresolved_gap_fraction", "research_evidence_count", "distinct_document_count", "distinct_chunk_count"].some((name) => item.metric_id.endsWith(name))
          ? { ...item, status: "not_applicable", value: null, numerator: null, denominator: null, reason_code: "nonresearch" } : item),
        facts: { ...agentEvaluation.facts, terminal_state: run.state, agent_status: run.result?.agent_status ?? null,
          failure_code: run.result?.failure?.code ?? null },
      };
      await json(route, 200, report); return;
    }
    if (action === "events" && method === "GET") {
      const after = Number(request.headers()["last-event-id"] ?? "0");
      const selected = (events.get(id) ?? []).filter((item) => item.sequence > after);
      const body = selected.map((item) => `id: ${item.sequence}\nevent: ${item.event_type}\ndata: ${JSON.stringify(item)}\n\n`).join("");
      await route.fulfill({ status: 200, headers: { ...CORS, "content-type": "text/event-stream" }, body });
      return;
    }
    if (action === "cancel" && method === "POST") {
      if (!executionEnabled) { await json(route, 403, { detail: "Execution disabled" }); return; }
      cancelCount += 1;
      if (conflictOnce) {
        conflictOnce = false;
        const changed = { ...run, revision: run.revision + 1 };
        runs.set(id, changed);
        events.set(id, [...(events.get(id) ?? []), lifecycleEvent(changed, changed.revision, "state_changed")]);
        await json(route, 409, { detail: "Agent run revision or state conflict" }); return;
      }
      if (request.headers()["if-match"] !== `"${run.revision}"` || (run.state !== "running" && run.state !== "queued")) {
        await json(route, 409, { detail: "Agent run revision or state conflict" }); return;
      }
      const next: AgentRun = { ...run, state: run.state === "queued" ? "cancelled" : "cancelling", revision: run.revision + 1, cancellation_requested_at: run.updated_at };
      runs.set(id, next);
      events.set(id, [...(events.get(id) ?? []), lifecycleEvent(next, next.revision, "cancellation_requested")]);
      await json(route, 200, next, { ETag: `"${next.revision}"` });
      return;
    }
    await json(route, 405, { detail: "Unsupported Agent request" });
  });
  return { runs, calls, cancelCount: () => cancelCount, createCount: () => createCount, forceConflictOnce: () => { conflictOnce = true; },
    advanceRun: (run) => {
      runs.set(run.run_id, run);
      const prior = events.get(run.run_id) ?? [];
      events.set(run.run_id, [...prior, lifecycleEvent(run, (prior.at(-1)?.sequence ?? 0) + 1, "state_changed")]);
    },
  };
}
