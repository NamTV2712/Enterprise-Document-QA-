import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  getDataset,
  getDatasets,
  getModels,
  getOriginalLocation,
  getPdfEvidenceLocation,
  getPdfManifest,
  getReaderLocation,
  testModelRuntimeIdentity,
} from "./api";

describe("reader location API clients", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("keeps exact chunk hash and source-set revision in the structured lookup", async () => {
    const response = {
      chunk_id: "chunk/1",
      chunk_text_hash: "hash with spaces",
      document_id: "document-1",
      source_set_revision: "source-set-1",
      status: "not_found",
      reason_code: "not_found",
      reason: "No match",
      source_document_id: null,
      document_revision: null,
      representation_revision: null,
      ranges: [],
      match_count: 0,
      match_count_capped: false,
    };
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(response), { status: 200 }));

    await expect(getReaderLocation("chunk/1", {
      chunk_text_hash: "hash with spaces",
      source_set_revision: "source-set/1",
    })).resolves.toEqual(response);

    const requestUrl = new URL(String(vi.mocked(fetch).mock.calls[0]?.[0]));
    expect(requestUrl.pathname).toContain("/chunks/chunk%2F1/reader-location");
    expect(requestUrl.searchParams.get("chunk_text_hash")).toBe("hash with spaces");
    expect(requestUrl.searchParams.get("source_set_revision")).toBe("source-set/1");
  });

  test("preserves stale location errors for callers to classify without changing the endpoint contract", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({
      detail: { code: "source_changed", message: "The source revision changed." },
    }), { status: 409 }));

    await expect(getOriginalLocation("chunk-1", {
      chunk_text_hash: "hash-1",
      source_set_revision: "source-set-1",
    })).rejects.toMatchObject({
      status: 409,
      code: "source_changed",
      message: "The source revision changed.",
    });
  });

  test("keeps PDF manifest transport bound to the document identity", async () => {
    const manifest = { document_id: "AAPL:fixture", artifact_status: "supported" };
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(manifest), { status: 200 }));

    await expect(getPdfManifest("AAPL:fixture")).resolves.toEqual(manifest);

    const requestUrl = new URL(String(vi.mocked(fetch).mock.calls[0]?.[0]));
    expect(requestUrl.pathname).toBe("/documents/AAPL%3Afixture/pdf");
    expect(requestUrl.search).toBe("");
  });

  test("sends the complete PDF evidence identity to the bound location route", async () => {
    const location = { status: "unavailable", document_id: "AAPL:fixture" };
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(location), { status: 200 }));

    await expect(getPdfEvidenceLocation("AAPL:fixture", {
      chunk_id: "chunk/1",
      chunk_text_hash: "a".repeat(64),
      source_document_id: "source/1",
      source_set_revision: "set/1",
      document_revision: "revision/1",
    })).resolves.toEqual(location);

    const requestUrl = new URL(String(vi.mocked(fetch).mock.calls[0]?.[0]));
    expect(requestUrl.pathname).toBe("/documents/AAPL%3Afixture/pdf/mapping/location");
    expect(requestUrl.searchParams.get("chunk_id")).toBe("chunk/1");
    expect(requestUrl.searchParams.get("chunk_text_hash")).toBe("a".repeat(64));
    expect(requestUrl.searchParams.get("source_document_id")).toBe("source/1");
    expect(requestUrl.searchParams.get("source_set_revision")).toBe("set/1");
    expect(requestUrl.searchParams.get("document_revision")).toBe("revision/1");
  });
});

describe("API-006 registry clients", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 })));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("uses the exact model routes and optional role filter", async () => {
    const controller = new AbortController();
    await getModels(undefined, controller.signal);
    await getModels("embedding");

    expect(new URL(String(vi.mocked(fetch).mock.calls[0]?.[0])).pathname).toBe("/models");
    const filtered = new URL(String(vi.mocked(fetch).mock.calls[1]?.[0]));
    expect(filtered.pathname).toBe("/models");
    expect(filtered.searchParams.get("role")).toBe("embedding");
    expect(vi.mocked(fetch).mock.calls[0]?.[1]).toMatchObject({ method: "GET", cache: "no-store", signal: controller.signal });
  });

  test("posts only the bounded runtime identity test and forwards AbortSignal", async () => {
    const controller = new AbortController();
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({
      model_id: "generator",
      test_type: "runtime_identity",
      result: "passed",
      provider_executed: false,
      checks: [],
    }), { status: 200 }));

    await testModelRuntimeIdentity("generator", controller.signal);

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(new URL(String(url)).pathname).toBe("/models/generator/tests");
    expect(init).toMatchObject({ method: "POST", signal: controller.signal });
    expect(JSON.parse(String(init?.body))).toEqual({ test_type: "runtime_identity" });
  });

  test("uses dataset list filters and encodes the canonical detail identity", async () => {
    await getDatasets();
    await getDatasets("evaluation");
    await getDataset("serving-corpus");

    const unfiltered = new URL(String(vi.mocked(fetch).mock.calls[0]?.[0]));
    expect(unfiltered.pathname).toBe("/datasets");
    expect(unfiltered.search).toBe("");
    const list = new URL(String(vi.mocked(fetch).mock.calls[1]?.[0]));
    expect(list.pathname).toBe("/datasets");
    expect(list.searchParams.get("kind")).toBe("evaluation");
    expect(new URL(String(vi.mocked(fetch).mock.calls[2]?.[0])).pathname).toBe("/datasets/serving-corpus");
    expect(vi.mocked(fetch).mock.calls[2]?.[1]).toMatchObject({ method: "GET", cache: "no-store" });
  });
});
