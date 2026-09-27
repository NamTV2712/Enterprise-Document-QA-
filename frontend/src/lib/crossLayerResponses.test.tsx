import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { getModels, getDatasets } from "./api";
import { projectLogPage, projectTimeseries } from "./operationalApi";
import { createPipelineApiClient } from "./pipelineApi";
import { createEvaluationApiClient } from "./evaluationApi";
import { snippetSegments } from "./searchModel";
import { NativeCases } from "../components/evaluation/NativeMetrics";
import { durationText } from "../components/operations/OperationalShared";
import type { DiscoverySnippet } from "../types";
import type { NativeCaseResult } from "./evaluationTypes";
import { evaluationJob } from "../test/evaluationFixtures";

const fixture = JSON.parse(readFileSync(resolve(process.cwd(), "../tests/fixtures/cross_layer_responses.json"), "utf8")) as {
  responses: Array<{ id: string; value: Record<string, unknown> }>;
  snippets: Array<{ text: string; snippet: DiscoverySnippet; marked: string[] }>;
};
const value = (id: string) => fixture.responses.find(entry => entry.id === id)!.value;
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("TEST-002 backend-validated responses reach frontend semantics", () => {
  test("the private job fixture uses the persisted zero-based durable step order", () => {
    expect(evaluationJob().steps.map(({ name, ordinal }) => ({ name, ordinal }))).toEqual([
      { name: "execute_cases", ordinal: 0 }, { name: "aggregate_report", ordinal: 1 },
    ]);
  });
  test("registry configured/load/unknown and dataset null/zero survive the actual clients", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(Response.json(value("models"))).mockResolvedValueOnce(Response.json(value("datasets"))));
    const models = await getModels(), datasets = await getDatasets();
    expect(models).toEqual(value("models"));
    expect(models.items[0]).toMatchObject({ configuration_status: "configured", load_status: "not_loaded", availability_status: "unknown", runtime_model_id: null });
    expect(datasets).toEqual(value("datasets"));
    expect(datasets.items.map(item => item.record_count)).toEqual([null, 0]);
  });
  test("logs retain opaque cursor/order, independent outcome/level, false and null vs measured zero", () => {
    const page = projectLogPage(value("logs"));
    expect(page).toEqual(value("logs"));
    expect(page.items.map(item => item.duration_ms)).toEqual([0, null]);
    expect(durationText(page.items[0].duration_ms)).toBe("0 ms");
    expect(durationText(page.items[1].duration_ms)).toBe("Not measured");
    expect(page.items[0].metadata.decomposed).toBe(false);
    const series = projectTimeseries(value("series"));
    expect(series).toEqual(value("series"));
    expect(series.points.map(point => point.value)).toEqual([null, 0]);
  });
  test("native case zero, false, unavailable and not-applicable render as four different meanings", () => {
    render(<NativeCases items={[value("nativeCase") as unknown as NativeCaseResult]} definitions={[]} total={1} page={1} pageSize={50} onPage={() => {}} />);
    for (const text of ["contract-case", "0.000", "False", "Unavailable", "Not applicable", "Not reported"]) expect(screen.getByText(text)).toBeInTheDocument();
  });
  test.each(["pipelineEvent", "evaluationEvent"])("%s finite SSE preserves identity/zero/state and does not infer success from close", async id => {
    const event = value(id), frame = `id: 3\nevent: progress\ndata: ${JSON.stringify(event)}\n\n`;
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response(frame, { headers: { "Content-Type": "text/event-stream" } }));
    const events = id === "pipelineEvent"
      ? await createPipelineApiClient({ fetchImpl }).getRunEvents("synthetic", "contract-run", 2)
      : await createEvaluationApiClient({ fetchImpl }).getJobEvents("synthetic", "contract-job", 2);
    expect(events).toEqual([event]);
    expect(events[0].state).not.toBe("succeeded");
    expect(new Headers(fetchImpl.mock.calls[0][1]?.headers).get("Last-Event-ID")).toBe("2");
  });
  test.each(["pipelineEvent", "evaluationEvent"])("%s rejects foreign identity, mismatched frame ID, invalid date and decreasing event order", async id => {
    const event = value(id);
    const frame = (data: Record<string, unknown>, sequence = 3) => `id: ${sequence}\nevent: progress\ndata: ${JSON.stringify(data)}\n\n`;
    for (const body of [
      frame({ ...event, [id === "pipelineEvent" ? "run_id" : "job_id"]: "other" }),
      frame(event, 4), frame({ ...event, occurred_at: "invalid" }),
      frame(event) + frame({ ...event, sequence: 2 }, 2),
    ]) {
      const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response(body));
      const read = id === "pipelineEvent"
        ? createPipelineApiClient({ fetchImpl }).getRunEvents("synthetic", "contract-run", 0)
        : createEvaluationApiClient({ fetchImpl }).getJobEvents("synthetic", "contract-job", 0);
      await expect(read).rejects.toMatchObject({ status: 502 });
      expect(fetchImpl).toHaveBeenCalledTimes(1);
    }
  });
  test.each(["pipelineEvent", "evaluationEvent"])("%s empty finite stream is not a terminal event", async id => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response(""));
    const events = id === "pipelineEvent"
      ? await createPipelineApiClient({ fetchImpl }).getRunEvents("synthetic", "contract-run", 2)
      : await createEvaluationApiClient({ fetchImpl }).getJobEvents("synthetic", "contract-job", 2);
    expect(events).toEqual([]);
  });
  test.each(fixture.snippets)("original Unicode text $text uses the backend's code-point offsets", example => {
    const segments = snippetSegments(example.snippet);
    expect(segments.filter(segment => segment.match).map(segment => segment.text)).toEqual(example.marked);
    expect(segments.map(segment => segment.text).join("")).toBe(example.snippet.text);
  });
});
