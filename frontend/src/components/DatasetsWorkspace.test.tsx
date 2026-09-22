import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { DatasetsWorkspace } from "./DatasetsWorkspace";
import { ApiError, getDataset, getDatasets } from "../lib/api";
import { LocaleProvider } from "../lib/i18n";
import type { DatasetDetail, DatasetRegistryResponse, DatasetSummary } from "../types";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, getDatasets: vi.fn(), getDataset: vi.fn() };
});

const getDatasetsMock = vi.mocked(getDatasets);
const getDatasetMock = vi.mocked(getDataset);

const summaries: DatasetSummary[] = [
  { id: "serving-corpus", kind: "corpus", name: "Serving SEC filing corpus", description: "The document corpus currently bound to retrieval.", availability: "degraded", reason_code: "index_manifest_missing", reason: "The serving index manifest is unavailable.", version: null, revision: null, record_count: 0, record_unit: "documents" },
  { id: "evaluation-test-set", kind: "evaluation", name: "Built-in evaluation test set", description: "The source-controlled cases used by the native evaluation workflow.", availability: "available", reason_code: null, reason: null, version: "evaluation-test-set-v1", revision: `sha256:${"a".repeat(64)}`, record_count: 30, record_unit: "cases" },
];

const corpusDetail: DatasetDetail = {
  ...summaries[0],
  coverage: { kind: "corpus", documents: 0, companies: 0, chunks: 0, configured_companies: 2, configured_companies_with_documents: [], configured_companies_without_documents: ["AAPL", "MSFT"], filing_years: { availability: "unknown", earliest: null, latest: null, documents_without_value: 0, reason: "No filing years recorded." }, sections: [] },
  provenance: { authority: "qdrant_index_manifest", status: "missing", reason_code: "index_manifest_missing", reason: "The serving index manifest is unavailable.", schema_version: null, revision: null, build_version: null, collection_name: null, point_count: null, embedding_model_id: null, embedding_model_revision: null, vector_dimension: null, distance_metric: null, snapshot_id: null, embedding_generation_id: null, embedding_generation_fingerprint: null },
};

const evaluationDetail: DatasetDetail = {
  ...summaries[1],
  coverage: { kind: "evaluation", cases: 30, categories: [{ key: "fact_lookup", count: 12 }, { key: "comparative", count: 6 }], priorities: [{ key: "1", count: 18 }, { key: "2", count: 12 }], tickers: ["AAPL", "MSFT"], sections: ["business", "risk_factors"] },
  provenance: { authority: "built_in_evaluation_test_set", status: "recorded", reason_code: null, reason: null, schema_version: 1, revision: summaries[1].revision, build_version: "evaluation-test-set-v1", collection_name: null, point_count: null, embedding_model_id: null, embedding_model_revision: null, vector_dimension: null, distance_metric: null, snapshot_id: null, embedding_generation_id: null, embedding_generation_fingerprint: null },
};

function list(items = summaries): DatasetRegistryResponse {
  return { items, total: items.length };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

beforeEach(() => {
  getDatasetsMock.mockReset();
  getDatasetMock.mockReset();
  getDatasetsMock.mockImplementation(async (kind) => list(kind ? summaries.filter((item) => item.kind === kind) : summaries));
  getDatasetMock.mockImplementation(async (id) => id === "serving-corpus" ? corpusDetail : evaluationDetail);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DatasetsWorkspace", () => {
  test("renders real dataset identities and preserves degraded, recorded zero, and unknown coverage", async () => {
    render(<LocaleProvider><DatasetsWorkspace /></LocaleProvider>);

    expect(await screen.findByRole("heading", { name: "Dataset registry" })).toBeInTheDocument();
    expect(screen.getByText("Serving SEC filing corpus")).toBeInTheDocument();
    expect(screen.getByText("Built-in evaluation test set")).toBeInTheDocument();
    const detail = await screen.findByRole("complementary", { name: "Serving SEC filing corpus details" });
    await within(detail).findByText("index_manifest_missing");
    expect(within(detail).getAllByText("0").length).toBeGreaterThan(0);
    expect(within(detail).getAllByText("Unknown").length).toBeGreaterThan(0);
    expect(within(detail).getAllByText("missing").length).toBeGreaterThan(0);
    expect(within(detail).getByText("index_manifest_missing")).toBeInTheDocument();
  });

  test("evaluation detail exposes aggregates and revision but no hidden cases or answers", async () => {
    render(<LocaleProvider><DatasetsWorkspace /></LocaleProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Built-in evaluation test set/ }));
    const detail = await screen.findByRole("complementary", { name: "Built-in evaluation test set details" });

    expect(within(detail).getByText("fact_lookup")).toBeInTheDocument();
    expect(within(detail).getByText("AAPL")).toBeInTheDocument();
    expect(within(detail).getByText(summaries[1].revision!)).toBeInTheDocument();
    expect(within(detail).getByText(/questions and ground truth are not sent/i)).toBeInTheDocument();
    expect(detail.textContent).not.toMatch(/expected answer|judge label/i);
  });

  test("filters through the typed endpoint without invoking any mutation", async () => {
    render(<LocaleProvider><DatasetsWorkspace /></LocaleProvider>);
    await screen.findByRole("heading", { name: "Dataset registry" });
    fireEvent.click(screen.getByRole("tab", { name: "Evaluation set" }));
    await waitFor(() => expect(getDatasetsMock).toHaveBeenLastCalledWith("evaluation", expect.any(AbortSignal)));
    await screen.findByRole("complementary", { name: "Built-in evaluation test set details" });
    const registry = screen.getByRole("region", { name: "Dataset registry" });
    expect(within(registry).getByText("Built-in evaluation test set")).toBeInTheDocument();
    expect(within(registry).queryByText("Serving SEC filing corpus")).toBeNull();
  });

  test("a detail 404 is a missing registry state rather than an empty dataset", async () => {
    getDatasetMock.mockRejectedValue(new ApiError("Dataset registry entry not found", 404));
    render(<LocaleProvider><DatasetsWorkspace /></LocaleProvider>);

    expect(await screen.findByText(/no longer present in the registry/i)).toBeInTheDocument();
    expect(screen.queryByText("No datasets reported")).toBeNull();
  });

  test("a late dataset detail cannot overwrite the newly selected dataset", async () => {
    const oldDetail = deferred<DatasetDetail>();
    getDatasetMock.mockImplementation((id) => id === "serving-corpus" ? oldDetail.promise : Promise.resolve(evaluationDetail));
    render(<LocaleProvider><DatasetsWorkspace /></LocaleProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Built-in evaluation test set/ }));
    const current = await screen.findByRole("complementary", { name: "Built-in evaluation test set details" });
    oldDetail.resolve(corpusDetail);
    await Promise.resolve();

    expect(current).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Serving SEC filing corpus details" })).toBeNull();
  });

  test("a stale failed detail cannot publish its error under the current dataset", async () => {
    const oldDetail = deferred<DatasetDetail>();
    getDatasetMock.mockImplementation((id) => id === "serving-corpus" ? oldDetail.promise : Promise.resolve(evaluationDetail));
    render(<LocaleProvider><DatasetsWorkspace /></LocaleProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Built-in evaluation test set/ }));
    const current = await screen.findByRole("complementary", { name: "Built-in evaluation test set details" });
    oldDetail.reject(new ApiError("Old detail failed", 503));
    await Promise.resolve();

    expect(current).toBeInTheDocument();
    expect(screen.queryByText("Old detail failed")).toBeNull();
  });
});
