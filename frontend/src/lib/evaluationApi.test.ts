import { describe, expect, test, vi } from "vitest";
import { createEvaluationApiClient, EvaluationApiError } from "./evaluationApi";
import type { EvaluationJobCreate, NativeMetricId } from "./evaluationTypes";

const ids: NativeMetricId[] = ["native.faithfulness", "native.answer_relevancy", "native.context_precision", "native.citation_index_validity", "native.keyword_recall_proxy", "native.fallback_correctness"];
const creation: EvaluationJobCreate = { artifact_id: "synthetic-phase1", engine: "native", metrics: ids, mode: "provider_backed", budget: 12 };
const token = "synthetic-memory-only-token";
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
function setup(respond: (url: string, init: RequestInit) => Response | Promise<Response> = () => response({})) {
  const requests: Array<{ url: string; init: RequestInit }> = [];
  const fetchImpl: typeof fetch = async (input, init = {}) => {
    requests.push({ url: String(input), init });
    return respond(String(input), init);
  };
  return { requests, client: createEvaluationApiClient({ baseUrl: "http://127.0.0.1:8000/", fetchImpl }) };
}
function privatePage(values: Array<number | boolean | null> = [0, false, null, null]) {
  return {
    job_id: "job-a", page: 1, page_size: 50, total: 1, report_status: "incomplete", report_digest: null,
    metric_definitions: [], aggregates: [],
    items: [{
      case_id: "case-a", question: "HIDDEN_QUESTION", judge_prompt_sha256: "judge-hash",
      input: { answer: "HIDDEN_ANSWER", ground_truth: "HIDDEN_GROUND_TRUTH", rendered_context: "HIDDEN_EVIDENCE", required_keywords: ["HIDDEN_KEYWORD"], generation_context_sha256: "generation-hash", judge_context_sha256: "judge-hash" },
      metrics: values.map((value, index) => ({ metric_id: index === 1 ? ids[5] : ids[index], metric_version: 1, status: index === 2 ? "unavailable" : index === 3 ? "not_applicable" : "computed", value, reason_code: index > 1 ? "missing_input" : null, question: "HIDDEN_EXTRA" })),
    }],
  };
}
function event(sequence: number, overrides: Record<string, unknown> = {}) {
  return { job_id: "job-a", event_id: `event-${sequence}`, sequence, event_type: "progress", state: "running", reason_code: null, progress: { stage: "execute_cases", current: 0, total: 2 }, occurred_at: "2026-09-26T00:00:00Z", ...overrides };
}
function frame(item: ReturnType<typeof event>) { return `id: ${item.sequence}\nevent: ${item.event_type}\ndata: ${JSON.stringify(item)}\n\n`; }

describe("Evaluation API public contracts", () => {
  test("consumes exact seven public routes, filters, server sort and AbortSignal without bearer or cookies", async () => {
    const { client, requests } = setup((url) => response(url.endsWith("/run%20a") ? { protocol: "native-evaluation", run_id: "run a" } : {}));
    const signal = new AbortController().signal;
    await client.getMetrics(signal);
    await client.listReports({ status: "complete", page: 2, page_size: 10 }, signal);
    await client.getReport("run a", signal);
    await client.getResults("run a", { case_id: "case &1", page: 2 }, signal);
    await client.compare({ baseline_run_id: "run-a", candidate_run_id: "run-b", metric_ids: ids }, signal);
    await client.getTrends({ metric_id: ids[0], binding_group: `sha256:${"a".repeat(64)}`, start_at: "2026-09-01T00:00:00Z", end_at: "2026-09-26T00:00:00Z", page: 2 }, signal);
    await client.getFailures({ run_id: "run a", category: "unavailable_prerequisite", page: 2 }, signal);
    expect(requests.map(({ url }) => new URL(url).pathname)).toEqual(["/evaluation/metrics", "/evaluation/runs", "/evaluation/runs/run%20a", "/evaluation/runs/run%20a/results", "/evaluation/compare", "/evaluation/metrics/trends", "/evaluation/failures"]);
    for (const { init } of requests) {
      expect(new Headers(init.headers).get("Authorization")).toBeNull();
      expect(init.signal).toBe(signal);
      expect(init.credentials).toBe("omit");
      expect(init.cache).toBe("no-store");
    }
    expect(new URL(requests[1].url).searchParams.get("status")).toBe("complete");
    expect(new URL(requests[3].url).searchParams.get("case_id")).toBe("case &1");
    expect(new URL(requests[3].url).searchParams.get("sort")).toBe("case_id_asc");
    expect(JSON.parse(String(requests[4].init.body))).toEqual({ baseline_run_id: "run-a", candidate_run_id: "run-b", metric_ids: ids });
    expect(new URL(requests[5].url).searchParams.get("sort")).toBe("published_at_asc");
    expect(new URL(requests[6].url).searchParams.get("sort")).toBe("category_case_metric_asc");
  });
  test("does not recompute backend deltas, incompatibility, null values or counts", async () => {
    const canonical = { metrics: [{ candidate_minus_baseline: null, status: "incompatible", baseline: { value: 0, denominator: 2 }, candidate: { value: null, unavailable_count: 2 } }], eligibility_reasons: ["computed_case_coverage_mismatch"] };
    const { client } = setup(() => response(canonical));
    expect(await client.compare({ baseline_run_id: "a", candidate_run_id: "b" })).toEqual(canonical);
  });
  test("legacy compatibility drops all case text and notes", async () => {
    const { client } = setup(() => response({ run_id: "legacy", title: "Legacy publication", status: "historical", created_at: "2026-09-26T00:00:00Z", provenance: { binding: "synthetic" }, aggregate: { faithfulness: 0 }, notes: ["HIDDEN_NOTES"], cases: [{ case_id: "one", status: "OK", scores: { faithfulness: 0 }, question: "HIDDEN_QUESTION", answer: "HIDDEN_ANSWER", evidence: [{ excerpt: "HIDDEN_EVIDENCE" }] }] }));
    const result = await client.getReport("legacy");
    expect(JSON.stringify(result)).not.toContain("HIDDEN_");
    expect("cases" in result && result.cases[0]).toEqual({ case_id: "one", status: "OK", scores: { faithfulness: 0 } });
  });
  test("rejects a detail from another identity", async () => {
    const { client } = setup(() => response({ protocol: "native-evaluation", run_id: "other" }));
    await expect(client.getReport("selected")).rejects.toMatchObject({ status: 502 });
  });
});
describe("Evaluation API private contracts", () => {
  test("six job routes use explicit memory token, canonical identity, If-Match, Idempotency-Key and replay header", async () => {
    const { client, requests } = setup((url) => url.includes("/results?") ? response(privatePage()) : url.endsWith("/events") ? new Response(frame(event(4))) : response({ id: "job-a", state: "queued", revision: 3 }));
    const signal = new AbortController().signal;
    await client.listJobs(token, { state: "interrupted", page: 2 }, signal);
    const result = await client.createJob(token, creation, "logical-attempt-1", signal);
    expect(result.id).toBe("job-a");
    expect(result.state).toBe("queued");
    await client.getJob(token, "job-a", signal);
    await client.getJobResults(token, "job-a", { page: 2 }, signal);
    await client.cancelJob(token, "job-a", 3, signal);
    await client.getJobEvents(token, "job-a", 3, signal);
    expect(requests.map(({ url }) => new URL(url).pathname)).toEqual(["/evaluation/jobs", "/evaluation/jobs", "/evaluation/jobs/job-a", "/evaluation/jobs/job-a/results", "/evaluation/jobs/job-a/cancel", "/evaluation/jobs/job-a/events"]);
    for (const { url, init } of requests) {
      expect(url).not.toContain(token);
      expect(String(init.body)).not.toContain(token);
      expect(new Headers(init.headers).get("Authorization")).toBe(`Bearer ${token}`);
      expect(init.signal).toBe(signal);
    }
    expect(new Headers(requests[1].init.headers).get("Idempotency-Key")).toBe("logical-attempt-1");
    expect(JSON.parse(String(requests[1].init.body))).toEqual(creation);
    expect(new Headers(requests[4].init.headers).get("If-Match")).toBe('"3"');
    expect(new Headers(requests[5].init.headers).get("Last-Event-ID")).toBe("3");
    expect(new Headers(requests[5].init.headers).get("Accept")).toBe("text/event-stream");
  });
  test("private blank credentials fail before transport", async () => {
    const { client, requests } = setup();
    await expect(client.listJobs(" ")).rejects.toMatchObject({ status: 401 });
    expect(requests).toHaveLength(0);
  });
  test("private results discard hidden fields and preserve numeric zero, boolean false and both null statuses", async () => {
    const { client } = setup(() => response(privatePage()));
    const result = await client.getJobResults(token, "job-a");
    expect(JSON.stringify(result)).not.toContain("HIDDEN_");
    expect(result.items[0].metrics.map(({ value, status }) => ({ value, status }))).toEqual([
      { value: 0, status: "computed" }, { value: false, status: "computed" },
      { value: null, status: "unavailable" }, { value: null, status: "not_applicable" },
    ]);
    expect(Object.keys(result.items[0])).toEqual(["case_id", "metrics", "generation_context_sha256", "judge_context_sha256", "judge_prompt_sha256"]);
  });
  test.each(["unavailable", "not_applicable"])("rejects %s metrics with a fabricated zero", async (status) => {
    const page = privatePage(); page.items[0].metrics[0].status = status;
    const { client } = setup(() => response(page));
    await expect(client.getJobResults(token, "job-a")).rejects.toMatchObject({ status: 502 });
  });
  test("rejects private results for a different selected job", async () => {
    const { client } = setup(() => response({ ...privatePage(), job_id: "job-b" }));
    await expect(client.getJobResults(token, "job-a")).rejects.toMatchObject({ status: 502 });
  });
  test("creation is one transport attempt and preserves caller idempotency binding", async () => {
    const { client, requests } = setup(() => { throw new TypeError(`Unknown transport outcome ${token}`); });
    await expect(client.createJob(token, creation, "same-logical-key")).rejects.toMatchObject({ status: 0 });
    expect(requests).toHaveLength(1);
  });
});
describe("finite ordered job event batches", () => {
  test("empty network close is an empty batch, not a terminal state", async () => {
    const { client } = setup(() => new Response(""));
    expect(await client.getJobEvents(token, "job-a", 0)).toEqual([]);
  });
  test("deduplicates exact replay and keeps canonical order/progress including zero", async () => {
    const { client } = setup(() => new Response(frame(event(1)) + frame(event(2)) + frame(event(2)) + frame(event(3))));
    const batch = await client.getJobEvents(token, "job-a", 1);
    expect(batch.map(({ sequence }) => sequence)).toEqual([2, 3]);
    expect(batch[0].progress.current).toBe(0);
  });
  test.each([
    ["wrong job", frame(event(1, { job_id: "job-b" }))],
    ["wrong identity", frame(event(1)).replace("id: 1", "id: 2")],
    ["wrong date", frame(event(1, { occurred_at: "not-a-date" }))],
    ["wrong state", frame(event(1, { state: "completed" }))],
    ["out of order", frame(event(3)) + frame(event(2))],
    ["conflicting duplicate", frame(event(1)) + frame(event(1, { state: "failed" }))],
    ["invalid JSON", "id: 1\ndata: {invalid}\n\n"],
    ["unsafe sequence", frame(event(Number.MAX_SAFE_INTEGER + 1))],
  ])("rejects %s without accepting foreign state", async (_, body) => {
    const { client } = setup(() => new Response(body));
    await expect(client.getJobEvents(token, "job-a", 0)).rejects.toMatchObject({ status: 502 });
  });
  test("strips additional fields from events", async () => {
    const { client } = setup(() => new Response(frame(event(1, { question: "HIDDEN_EVENT_TEXT" }))));
    expect(JSON.stringify(await client.getJobEvents(token, "job-a", 0))).not.toContain("HIDDEN_");
  });
  test.each([-1, 0.5, Number.MAX_SAFE_INTEGER + 1])("refuses unsafe replay cursor %s before transport", async (cursor) => {
    const { client, requests } = setup();
    await expect(client.getJobEvents(token, "job-a", cursor)).rejects.toMatchObject({ status: 422 });
    expect(requests).toHaveLength(0);
  });
});
describe("typed sanitized errors and lifetime support", () => {
  test.each([401, 403, 404, 409, 422, 428, 503])("maps HTTP %s without reflecting response text or token", async (status) => {
    const { client } = setup(() => response({ detail: `HIDDEN_PROVIDER_TEXT ${token}` }, status));
    const error = await client.listJobs(token).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(EvaluationApiError);
    expect((error as EvaluationApiError).status).toBe(status);
    expect(String(error)).not.toMatch(/HIDDEN_|synthetic-memory/);
  });
  test("preserves caller abort instead of translating it into a network/job failure", async () => {
    const controller = new AbortController(); controller.abort();
    const fetchImpl = vi.fn<typeof fetch>(async (_input, init) => { init?.signal?.throwIfAborted(); return response({}); });
    const client = createEvaluationApiClient({ fetchImpl });
    await expect(client.getMetrics(controller.signal)).rejects.toMatchObject({ name: "AbortError" });
  });
  test("invalid JSON is typed but sanitized", async () => {
    const { client } = setup(() => new Response("HIDDEN_MALFORMED_TEXT"));
    await expect(client.getMetrics()).rejects.toMatchObject({ status: 502 });
  });
  test("adds the established ngrok warning header", async () => {
    const fetchImpl = vi.fn<typeof fetch>(async () => response({}));
    const client = createEvaluationApiClient({ baseUrl: "https://synthetic.ngrok-free.app", fetchImpl });
    await client.getMetrics();
    expect(new Headers(fetchImpl.mock.calls[0][1]?.headers).get("ngrok-skip-browser-warning")).toBe("true");
  });
});
