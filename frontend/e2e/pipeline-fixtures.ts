import type { Page, Route } from "@playwright/test";

import { API_ORIGIN, installApiFixtures } from "./fixtures";
import type { PipelineDefinition, PipelineRun, PipelineRunEvent, PipelineRunState } from "../src/types";

export const PIPELINE_FIXTURE_TOKEN = "ui010-fixture-token-only";

const STAGES = [
  "download_filings",
  "chunk_filings",
  "add_table_chunks",
  "embed_chunks",
  "index_chunks",
] as const;

const CORS = {
  "access-control-allow-origin": "http://localhost:4173",
  "access-control-allow-headers": "Authorization, Content-Type, If-Match, Last-Event-ID",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-expose-headers": "ETag",
};

export const PIPELINE_DEFINITION: PipelineDefinition = {
  pipeline_id: "sec_10k_ingestion",
  name: "SEC 10-K ingestion",
  input_kind: "ticker",
  registered_input_ids: ["AAPL", "MSFT", "NVDA", "BRK-B"],
  staging_profiles: ["isolated"],
  stages: STAGES.map((stage_id, index) => ({
    stage_id,
    order: index + 1,
    description: [
      "Acquire SEC filings and extract sections.",
      "Build chunks from extracted sections.",
      "Add financial-table chunks before embedding.",
      "Create an immutable embedding generation.",
      "Build and verify an isolated staged index.",
    ][index],
  })),
  capabilities: {
    can_stage: true,
    can_cancel: true,
    event_transport: "sse",
    executes_during_staging: false,
    automatically_promotes_to_serving: false,
  },
};

export function pipelineRun(id: string, overrides: Partial<PipelineRun> = {}): PipelineRun {
  return {
    id,
    pipeline_id: "sec_10k_ingestion",
    state: "queued",
    revision: 1,
    configuration_fingerprint: "a".repeat(64),
    input_ids: ["AAPL"],
    staging_profile: "isolated",
    created_at: "2026-09-23T10:00:00Z",
    updated_at: "2026-09-23T10:00:00Z",
    started_at: null,
    finished_at: null,
    cancellation_requested_at: null,
    progress: { stage: null, current: null, total: null },
    steps: STAGES.map((stage_id, index) => ({
      step_id: `${id}-step-${index + 1}`,
      stage_id,
      state: "pending",
      revision: 1,
      started_at: null,
      finished_at: null,
    })),
    artifact_references: [],
    failure: null,
    ...overrides,
  };
}

interface PipelineFixtureOptions {
  mode?: "local" | "public";
  executionEnabled?: boolean;
  initialRuns?: PipelineRun[];
}

export interface PipelineFixtureCall {
  method: string;
  path: string;
  lastEventId: string | null;
  ifMatch: string | null;
}

export interface PipelineFixture {
  runs: Map<string, PipelineRun>;
  calls: PipelineFixtureCall[];
  stageCount: () => number;
  cancelCount: () => number;
  forceConflictOnce: () => void;
  emitState: (runId: string, state: PipelineRunState) => void;
}

async function fulfillJson(route: Route, status: number, body: unknown, extraHeaders: Record<string, string> = {}) {
  await route.fulfill({
    status,
    headers: { ...CORS, "content-type": "application/json", ...extraHeaders },
    body: JSON.stringify(body),
  });
}

function runEvent(run: PipelineRun, sequence: number, eventType: PipelineRunEvent["event_type"]): PipelineRunEvent {
  return {
    run_id: run.id,
    event_id: `${run.id}-event-${sequence}`,
    sequence,
    event_type: eventType,
    state: run.state,
    reason_code: null,
    progress: run.progress,
    occurred_at: run.updated_at,
  };
}

export async function installPipelineFixture(page: Page, options: PipelineFixtureOptions = {}): Promise<PipelineFixture> {
  await installApiFixtures(page);
  const mode = options.mode ?? "local";
  const executionEnabled = options.executionEnabled ?? true;
  const runs = new Map((options.initialRuns ?? []).map((run) => [run.id, run]));
  const events = new Map<string, PipelineRunEvent[]>();
  for (const run of runs.values()) events.set(run.id, [runEvent(run, 1, "created")]);
  const calls: PipelineFixtureCall[] = [];
  let stageCount = 0;
  let cancelCount = 0;
  let conflictOnce = false;

  const hasAuth = (route: Route) => route.request().headers().authorization === `Bearer ${PIPELINE_FIXTURE_TOKEN}`;
  const privateAccess = async (route: Route): Promise<boolean> => {
    if (mode !== "local") {
      await fulfillJson(route, 404, { detail: "Local workspace capability is unavailable" });
      return false;
    }
    if (!hasAuth(route)) {
      await fulfillJson(route, 401, { detail: "Local workspace authentication required" });
      return false;
    }
    return true;
  };

  await page.route(`${API_ORIGIN}/system/configuration-status`, async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: CORS });
      return;
    }
    if (!await privateAccess(route)) return;
    await fulfillJson(route, 200, {
      deployment_mode: "local",
      capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: executionEnabled },
    });
  });

  await page.route(`${API_ORIGIN}/pipeline**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = decodeURIComponent(url.pathname);
    const method = request.method();
    if (method === "OPTIONS") {
      await route.fulfill({ status: 204, headers: CORS });
      return;
    }
    calls.push({
      method,
      path,
      lastEventId: request.headers()["last-event-id"] ?? null,
      ifMatch: request.headers()["if-match"] ?? null,
    });
    if (path === "/pipeline" && method === "GET") {
      await fulfillJson(route, 200, PIPELINE_DEFINITION);
      return;
    }
    if (!await privateAccess(route)) return;
    if (path === "/pipeline/runs" && method === "GET") {
      const state = url.searchParams.get("state");
      const pageNumber = Number(url.searchParams.get("page") ?? "1");
      const pageSize = Number(url.searchParams.get("page_size") ?? "25");
      const selected = [...runs.values()]
        .filter((run) => !state || run.state === state)
        .sort((left, right) => right.created_at.localeCompare(left.created_at));
      const offset = (pageNumber - 1) * pageSize;
      await fulfillJson(route, 200, { items: selected.slice(offset, offset + pageSize), total: selected.length, page: pageNumber, page_size: pageSize });
      return;
    }
    if (path === "/pipeline/runs" && method === "POST") {
      if (!executionEnabled) {
        await fulfillJson(route, 403, { detail: "Workspace execution capability is disabled" });
        return;
      }
      stageCount += 1;
      const body = request.postDataJSON() as { input_ids?: unknown; staging_profile?: unknown };
      if (!Array.isArray(body.input_ids) || body.input_ids.length === 0 || body.staging_profile !== "isolated") {
        await fulfillJson(route, 422, { detail: "Invalid staging request" });
        return;
      }
      const id = `run-staged-${stageCount}`;
      const staged = pipelineRun(id, {
        input_ids: body.input_ids as string[],
        created_at: "2026-09-23T12:00:00Z",
        updated_at: "2026-09-23T12:00:00Z",
      });
      runs.set(id, staged);
      events.set(id, [runEvent(staged, 1, "created")]);
      await fulfillJson(route, 201, staged, { ETag: '"1"' });
      return;
    }

    const match = path.match(/^\/pipeline\/runs\/([A-Za-z0-9_-]+)(?:\/(cancel|events))?$/);
    if (!match) {
      await fulfillJson(route, 404, { detail: "Pipeline resource was not found" });
      return;
    }
    const id = match[1];
    const action = match[2] ?? "detail";
    const run = runs.get(id);
    if (!run) {
      await fulfillJson(route, 404, { detail: "Pipeline resource was not found" });
      return;
    }
    if (action === "detail" && method === "GET") {
      await fulfillJson(route, 200, run, { ETag: `"${run.revision}"` });
      return;
    }
    if (action === "events" && method === "GET") {
      const cursor = Number(request.headers()["last-event-id"] ?? "0");
      const batch = (events.get(id) ?? []).filter((event) => event.sequence > cursor).slice(0, 100);
      const body = batch.map((event) => `id: ${event.sequence}\nevent: ${event.event_type}\ndata: ${JSON.stringify(event)}\n\n`).join("");
      await route.fulfill({ status: 200, headers: { ...CORS, "content-type": "text/event-stream", "cache-control": "no-cache" }, body });
      return;
    }
    if (action === "cancel" && method === "POST") {
      if (!executionEnabled) {
        await fulfillJson(route, 403, { detail: "Workspace execution capability is disabled" });
        return;
      }
      cancelCount += 1;
      const ifMatch = request.headers()["if-match"];
      if (conflictOnce || ifMatch !== `"${run.revision}"`) {
        conflictOnce = false;
        await fulfillJson(route, 409, { detail: "Pipeline run revision or state conflict" });
        return;
      }
      const next = {
        ...run,
        state: run.state === "queued" ? "cancelled" : "cancelling",
        revision: run.revision + 1,
        cancellation_requested_at: "2026-09-23T12:05:00Z",
        updated_at: "2026-09-23T12:05:00Z",
      } satisfies PipelineRun;
      runs.set(id, next);
      const history = events.get(id) ?? [];
      events.set(id, [...history, runEvent(next, history.length + 1, next.state === "cancelled" ? "cancelled" : "cancellation_requested")]);
      await fulfillJson(route, 200, next, { ETag: `"${next.revision}"` });
      return;
    }
    await fulfillJson(route, 405, { detail: "Method not allowed" });
  });

  return {
    runs,
    calls,
    stageCount: () => stageCount,
    cancelCount: () => cancelCount,
    forceConflictOnce: () => { conflictOnce = true; },
    emitState: (runId, state) => {
      const previous = runs.get(runId);
      if (!previous) return;
      const next: PipelineRun = {
        ...previous,
        state,
        revision: previous.revision + 1,
        updated_at: "2026-09-23T12:10:00Z",
      };
      runs.set(runId, next);
      const history = events.get(runId) ?? [];
      events.set(runId, [...history, runEvent(next, history.length + 1, "state_changed")]);
    },
  };
}
