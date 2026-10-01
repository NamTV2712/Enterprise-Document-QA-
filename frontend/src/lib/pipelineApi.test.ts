import { describe, expect, test } from "vitest";

import { createPipelineApiClient, PipelineApiError } from "./pipelineApi";
import type { PipelineDefinition, PipelineRun, PipelineRunEvent } from "../types";

function definition(): PipelineDefinition {
  return {
    pipeline_id: "sec_10k_ingestion",
    name: "SEC 10-K ingestion",
    input_kind: "ticker",
    registered_input_ids: ["AAPL", "MSFT"],
    staging_profiles: ["isolated"],
    stages: [],
    capabilities: {
      can_stage: true,
      can_cancel: true,
      event_transport: "sse",
      executes_during_staging: false,
      automatically_promotes_to_serving: false,
    },
  };
}

function run(): PipelineRun {
  return {
    id: "run-1",
    pipeline_id: "sec_10k_ingestion",
    state: "queued",
    revision: 3,
    configuration_fingerprint: "a".repeat(64),
    input_ids: ["AAPL"],
    staging_profile: "isolated",
    created_at: "2026-09-23T10:00:00Z",
    updated_at: "2026-09-23T10:00:00Z",
    started_at: null,
    finished_at: null,
    cancellation_requested_at: null,
    progress: { stage: null, current: null, total: null },
    steps: [],
    artifact_references: [],
    failure: null,
  };
}

function event(sequence: number): PipelineRunEvent {
  return {
    run_id: "run-1",
    event_id: `event-${sequence}`,
    sequence,
    event_type: "created",
    state: "queued",
    reason_code: null,
    progress: { stage: null, current: null, total: null },
    occurred_at: "2026-09-23T10:00:00Z",
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

interface CapturedRequest {
  url: string;
  init: RequestInit;
}

function recordingFetch(
  respond: (url: string, init: RequestInit) => Promise<Response>,
): [typeof fetch, CapturedRequest[]] {
  const requests: CapturedRequest[] = [];
  const fetchImpl: typeof fetch = async (input, init) => {
    const request = { url: String(input), init: init ?? {} };
    requests.push(request);
    return respond(request.url, request.init);
  };
  return [fetchImpl, requests];
}

describe("Pipeline API client", () => {
  test("keeps the public definition request anonymous", async () => {
    const [fetchImpl, requests] = recordingFetch(async () => jsonResponse(definition()));
    const client = createPipelineApiClient({ baseUrl: "http://127.0.0.1:8000/", fetchImpl });

    await client.getDefinition();

    expect(requests[0].url).toBe("http://127.0.0.1:8000/pipeline");
    expect(requests[0].init.method).toBe("GET");
    const headers = new Headers(requests[0].init.headers);
    expect(headers.get("Authorization")).toBeNull();
    expect(headers.get("Accept")).toBe("application/json");
  });

  test("uses the exact private list, detail, stage and revision-cancel contracts", async () => {
    const [fetchImpl, requests] = recordingFetch(async (url) => {
      if (url.endsWith("/cancel")) return jsonResponse(run());
      if (url.endsWith("/pipeline/runs")) return jsonResponse(run());
      if (url.includes("/pipeline/runs?")) return jsonResponse({ items: [], total: 0, page: 1, page_size: 25 });
      return jsonResponse(run());
    });
    const client = createPipelineApiClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });

    await client.listRuns("local-token", { page: 1, page_size: 25, state: "queued" });
    await client.getRun("local-token", "run-1");
    await client.stageRun("local-token", { input_ids: ["AAPL"], staging_profile: "isolated" });
    await client.cancelRun("local-token", "run-1", 3);

    expect(requests[0].url).toBe("http://127.0.0.1:8000/pipeline/runs?page=1&page_size=25&state=queued");
    expect(requests[1].url).toBe("http://127.0.0.1:8000/pipeline/runs/run-1");
    expect(requests[2].url).toBe("http://127.0.0.1:8000/pipeline/runs");
    expect(requests[3].url).toBe("http://127.0.0.1:8000/pipeline/runs/run-1/cancel");
    for (const { init } of requests) {
      expect(new Headers(init.headers).get("Authorization")).toBe("Bearer local-token");
    }
    expect(JSON.parse(String(requests[2].init.body))).toEqual({ input_ids: ["AAPL"], staging_profile: "isolated" });
    expect(new Headers(requests[3].init.headers).get("If-Match")).toBe('"3"');
  });

  test("verifies a candidate token with the protected capability-status endpoint", async () => {
    const [fetchImpl, requests] = recordingFetch(async () => jsonResponse({
      deployment_mode: "local",
      capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: false },
    }));
    const client = createPipelineApiClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });

    await client.verifyLocalWorkspaceToken("candidate-token");

    expect(requests[0].url).toBe("http://127.0.0.1:8000/system/configuration-status");
    expect(new Headers(requests[0].init.headers).get("Authorization")).toBe("Bearer candidate-token");
  });

  test("resumes finite SSE batches with a numeric cursor and validates returned frames", async () => {
    const [fetchImpl, requests] = recordingFetch(async () => new Response(
      `id: 5\nevent: created\ndata: ${JSON.stringify(event(5))}\n\n`,
      { status: 200, headers: { "Content-Type": "text/event-stream" } },
    ));
    const client = createPipelineApiClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });

    await expect(client.getRunEvents("local-token", "run-1", 4)).resolves.toEqual([event(5)]);

    const headers = new Headers(requests[0].init.headers);
    expect(requests[0].url).toBe("http://127.0.0.1:8000/pipeline/runs/run-1/events");
    expect(headers.get("Authorization")).toBe("Bearer local-token");
    expect(headers.get("Last-Event-ID")).toBe("4");
    expect(headers.get("Accept")).toBe("text/event-stream");
  });

  test("maps status codes without reflecting response bodies that may contain secrets", async () => {
    const [fetchImpl] = recordingFetch(async () => new Response("candidate-token leaked by server", { status: 409 }));
    const client = createPipelineApiClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });

    await expect(client.listRuns("candidate-token")).rejects.toMatchObject({
      name: "PipelineApiError",
      status: 409,
      message: "This run changed. Refresh it before trying again.",
    } satisfies Partial<PipelineApiError>);
  });
});
