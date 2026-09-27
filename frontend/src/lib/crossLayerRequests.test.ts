import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, test, vi } from "vitest";
import * as api from "./api";
import { createPipelineApiClient } from "./pipelineApi";
import { createEvaluationApiClient } from "./evaluationApi";
import { createOperationalApi } from "./operationalApi";
import { createWorkspaceTransferClient } from "./workspaceRepository";
import type { WorkspaceBackup } from "./workspaceBackup";
import type { EvaluationJobCreate, NativeCompareRequest } from "./evaluationTypes";

const fixture = (name: string) => JSON.parse(readFileSync(resolve(process.cwd(), `../tests/fixtures/${name}.json`), "utf8"));
const catalog = fixture("cross_layer_contracts") as { routes: Array<{ id: string; method: string; path: string; access: string; revision?: string }> };
interface RequestExample { id: string; body?: Record<string, unknown>; query?: Record<string, string | number | boolean>; headers?: Record<string, string>; staged_no_bearer?: boolean }
const requests = fixture("cross_layer_requests") as { ids: Record<string, string>; requests: RequestExample[] };
const ids = requests.ids, token = "test002-synthetic-memory-token";

afterEach(() => vi.unstubAllGlobals());
describe("TEST-002 real client requests against the shared backend route catalog", () => {
  test.each(["preview", "import", "export"])("%s: reuse the canonical transfer fixture and exact registered transport", async id => {
    const backup = (fixture("workspace_transfer_roundtrip") as { fixtures: Array<{ backup: WorkspaceBackup }> }).fixtures[0].backup;
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(Response.json(id === "export" ? backup : { digest: backup.digest }));
    const client = createWorkspaceTransferClient({ apiBaseUrl: "http://localhost:8000/", getBearerToken: () => token, fetchImpl });
    if (id === "preview") await client.preview(backup);
    else if (id === "import") await client.importBackup(backup, backup.digest);
    else expect(await client.exportBackup()).toEqual(backup);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [input, init] = fetchImpl.mock.calls[0], contract = catalog.routes.find(route => route.id === id)!;
    expect(new URL(String(input)).pathname).toBe(contract.path);
    expect(init?.method).toBe(contract.method);
    expect(new Headers(init?.headers).get("Authorization")).toBe(`Bearer ${token}`);
    expect(String(input)).not.toContain(token);
    if (id !== "export") expect(JSON.parse(String(init?.body))).toEqual(id === "preview" ? backup : { backup, preview_digest: backup.digest });
    else expect(init?.body).toBeUndefined();
  });
  test.each(requests.requests)("$id: method, encoded path/query, body, revisions, bearer and signal", async example => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 404 }));
    vi.stubGlobal("fetch", fetchImpl);
    const pipeline = createPipelineApiClient({ fetchImpl }), evaluation = createEvaluationApiClient({ fetchImpl }), operational = createOperationalApi({ fetchImpl });
    const signal = new AbortController().signal, q = example.query ?? {}, b = example.body ?? {};
    const invoke: Record<string, () => Promise<unknown>> = {
      models: () => api.getModels("embedding", signal), modelTest: () => api.testModelRuntimeIdentity("generator", signal),
      datasets: () => api.getDatasets("evaluation", signal), dataset: () => api.getDataset("serving-corpus", signal),
      documents: () => api.getDocuments(q, signal), chunks: () => api.getDocumentChunks(ids.document_id, q, signal), facets: () => api.getDocumentFacets(q, signal), stats: () => api.getDocumentStats(signal),
      search: () => api.createDiscoverySearch(b as unknown as Parameters<typeof api.createDiscoverySearch>[0], signal),
      searchPage: () => api.getDiscoverySnapshot(ids.search_id, q, signal), inspect: () => api.inspectRetrieval(b as unknown as Parameters<typeof api.inspectRetrieval>[0], signal),
      collections: () => api.listCollections(q, signal), collectionCreate: () => api.createCollection(b as unknown as Parameters<typeof api.createCollection>[0], signal), collection: () => api.getCollection(ids.collection_id, signal),
      collectionUpdate: () => api.updateCollection(ids.collection_id, b as unknown as Parameters<typeof api.updateCollection>[1], signal), collectionDelete: () => api.deleteCollection(ids.collection_id, 3, signal),
      items: () => api.listCollectionItems(ids.collection_id, { kind: "evidence", page: 2, page_size: 10 }, signal), itemAdd: () => api.addCollectionItem(ids.collection_id, b as unknown as Parameters<typeof api.addCollectionItem>[1], signal), itemDelete: () => api.deleteCollectionItem(ids.collection_id, ids.item_id, 3, signal),
      notes: () => api.listCollectionNotes(ids.collection_id, q, signal), noteAdd: () => api.addCollectionNote(ids.collection_id, b as unknown as Parameters<typeof api.addCollectionNote>[1], signal), noteUpdate: () => api.updateCollectionNote(ids.collection_id, ids.note_id, b as unknown as Parameters<typeof api.updateCollectionNote>[2], signal), noteDelete: () => api.deleteCollectionNote(ids.collection_id, ids.note_id, 3, signal),
      activity: () => api.listCollectionActivity(ids.collection_id, q, signal), collectionExport: () => api.exportCollection(ids.collection_id, "json", signal),
      pipeline: () => pipeline.getDefinition(signal), pipelineList: () => pipeline.listRuns(token, { state: "interrupted", page: 2, page_size: 10 }, signal), pipelineCreate: () => pipeline.stageRun(token, { input_ids: ["AAPL"], staging_profile: "isolated" }, signal), pipelineDetail: () => pipeline.getRun(token, ids.run_id, signal), pipelineCancel: () => pipeline.cancelRun(token, ids.run_id, 3, signal), pipelineEvents: () => pipeline.getRunEvents(token, ids.run_id, 2, signal),
      metrics: () => evaluation.getMetrics(signal), reports: () => evaluation.listReports({ status: "incomplete", page: 2, page_size: 10 }, signal), report: () => evaluation.getReport(ids.run_id, signal), results: () => evaluation.getResults(ids.run_id, { case_id: "case & one", page: 2, page_size: 10 }, signal), compare: () => evaluation.compare(b as unknown as NativeCompareRequest, signal),
      trends: () => evaluation.getTrends({ metric_id: "native.faithfulness", page: 2, page_size: 10 }, signal), failures: () => evaluation.getFailures({ run_id: ids.run_id, category: "unavailable_prerequisite", page: 2, page_size: 10 }, signal),
      jobList: () => evaluation.listJobs(token, { state: "cancelling", page: 2, page_size: 10 }, signal), jobCreate: () => evaluation.createJob(token, b as unknown as EvaluationJobCreate, "contract-request-1", signal), jobDetail: () => evaluation.getJob(token, ids.job_id, signal), jobResults: () => evaluation.getJobResults(token, ids.job_id, { page: 2, page_size: 10 }, signal), jobCancel: () => evaluation.cancelJob(token, ids.job_id, 3, signal), jobEvents: () => evaluation.getJobEvents(token, ids.job_id, 2, signal),
      summary: () => operational.summary(token, "30d", signal), timeseries: () => operational.timeseries(token, "30d", "hour", "request_duration_p95_ms", signal), logs: () => operational.logs(token, { category: "job", level: "warning", cursor: "opaque+/cursor==", limit: 50 }, signal), configuration: () => operational.configuration(token, signal), system: () => operational.settingsFacts(signal),
    };
    expect(invoke[example.id], "fixture must name a real client invocation").toBeDefined();
    await expect(invoke[example.id]()).rejects.toMatchObject({ status: 404 });
    expect(fetchImpl).toHaveBeenCalledTimes(1); // No conflict/refusal retry or hidden execution.
    const [input, init] = fetchImpl.mock.calls[0], url = new URL(String(input));
    const contract = catalog.routes.find(route => route.id === example.id)!;
    const path = contract.path.replace(/\{([^}]+)\}/g, (_, key: string) => encodeURIComponent(ids[key]));
    expect(url.pathname).toBe(path);
    expect(init?.method).toBe(contract.method);
    expect(Object.fromEntries(url.searchParams)).toEqual(Object.fromEntries(Object.entries(q).map(([key, value]) => [key, String(value)])));
    expect(init?.signal).toBe(signal);
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe(contract.access === "public" || example.staged_no_bearer ? null : `Bearer ${token}`);
    expect(url.href).not.toContain(token);
    if (example.body) {
      expect(headers.get("Content-Type")).toBe("application/json");
      expect(JSON.parse(String(init?.body))).toEqual(example.body);
    } else expect(init?.body).toBeUndefined();
    for (const [name, value] of Object.entries(example.headers ?? {})) expect(headers.get(name)).toBe(value);
    if (contract.revision === "query" || contract.revision === "body") expect(headers.has("If-Match")).toBe(false);
    if (contract.revision === "If-Match") expect(url.searchParams.has("revision")).toBe(false);
  });
});
