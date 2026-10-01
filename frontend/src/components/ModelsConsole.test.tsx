import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ModelsConsole } from "./ModelsConsole";
import { ApiError, getModels, testModelRuntimeIdentity } from "../lib/api";
import { LocaleProvider } from "../lib/i18n";
import type { ModelRegistryEntry, ModelRegistryResponse, ModelTestResponse } from "../types";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, getModels: vi.fn(), testModelRuntimeIdentity: vi.fn() };
});

const getModelsMock = vi.mocked(getModels);
const testModelMock = vi.mocked(testModelRuntimeIdentity);

function model(overrides: Partial<ModelRegistryEntry> = {}): ModelRegistryEntry {
  return {
    id: "generator",
    role: "generator",
    provider: "groq",
    configured_model_id: "openai/gpt-oss-120b",
    configured_revision: null,
    runtime_model_id: "openai/gpt-oss-120b",
    runtime_revision: null,
    configuration_status: "configured",
    load_status: "loaded",
    availability_status: "unknown",
    availability_reason: "Remote provider reachability is not probed by registry reads.",
    credential_status: "configured",
    test_capabilities: ["runtime_identity"],
    ...overrides,
  };
}

const models = [
  model(),
  model({ id: "embedding", role: "embedding", provider: "hugging_face", configured_model_id: "nomic-ai/nomic-embed-text-v1.5", configured_revision: "embed-rev", runtime_model_id: "nomic-ai/nomic-embed-text-v1.5", runtime_revision: "embed-rev", credential_status: "not_required", availability_status: "available", availability_reason: null }),
  model({ id: "reranker", role: "reranker", provider: "hugging_face", configured_model_id: "cross-encoder/ms-marco-MiniLM-L-6-v2", configured_revision: "rerank-rev", runtime_model_id: null, runtime_revision: null, credential_status: "not_required", load_status: "not_loaded", availability_status: "unknown", availability_reason: "The configured local model is not loaded in the current runtime." }),
];

function response(items = models): ModelRegistryResponse {
  return { items, total: items.length };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

beforeEach(() => {
  getModelsMock.mockReset();
  testModelMock.mockReset();
  getModelsMock.mockImplementation(async (role) => response(role ? models.filter((item) => item.role === role) : models));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ModelsConsole", () => {
  test("renders real roles and keeps configured, loaded, available, and unknown distinct", async () => {
    render(<LocaleProvider><ModelsConsole /></LocaleProvider>);

    expect(await screen.findByRole("heading", { name: "Runtime registry" })).toBeInTheDocument();
    expect(screen.getAllByText("Generator").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Embedding").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Reranker").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unknown").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Loaded").length).toBeGreaterThan(0);
    expect(screen.getByText(/reachability is not probed/i)).toBeInTheDocument();
    expect(screen.queryByText(/Healthy|Online|Latency|Accuracy/)).toBeNull();
    expect(testModelMock).not.toHaveBeenCalled();
  });

  test("filters through the typed endpoint and a stale role response cannot repaint the newer filter", async () => {
    const generator = deferred<ModelRegistryResponse>();
    const embedding = deferred<ModelRegistryResponse>();
    getModelsMock.mockImplementation((role) => {
      if (role === "generator") return generator.promise;
      if (role === "embedding") return embedding.promise;
      return Promise.resolve(response());
    });
    render(<LocaleProvider><ModelsConsole /></LocaleProvider>);
    await screen.findByRole("heading", { name: "Runtime registry" });

    fireEvent.click(screen.getByRole("tab", { name: "Generator" }));
    fireEvent.click(screen.getByRole("tab", { name: "Embedding" }));
    embedding.resolve(response([models[1]]));
    expect((await screen.findAllByText("nomic-ai/nomic-embed-text-v1.5")).length).toBeGreaterThan(0);
    generator.resolve(response([models[0]]));
    await Promise.resolve();
    expect(screen.queryByText("openai/gpt-oss-120b")).toBeNull();
  });

  test("runs the bounded identity check only after an explicit click and prevents duplicates", async () => {
    const pending = deferred<ModelTestResponse>();
    testModelMock.mockReturnValue(pending.promise);
    render(<LocaleProvider><ModelsConsole /></LocaleProvider>);
    const button = await screen.findByRole("button", { name: "Run identity check" });

    expect(testModelMock).not.toHaveBeenCalled();
    fireEvent.click(button);
    fireEvent.click(button);
    expect(testModelMock).toHaveBeenCalledTimes(1);
    expect(button).toBeDisabled();

    pending.resolve({ model_id: "generator", test_type: "runtime_identity", result: "passed", provider_executed: false, checks: [{ id: "runtime_identity", status: "passed", reason: null }] });
    const result = await screen.findByRole("status");
    expect(within(result).getByText("Provider executed: No")).toBeInTheDocument();
    expect(within(result).getByText("Passed")).toBeInTheDocument();
  });

  test("explains local execution access failures without changing the read-only registry", async () => {
    testModelMock.mockRejectedValue(new ApiError("Local workspace authentication required", 401));
    render(<LocaleProvider><ModelsConsole /></LocaleProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "Run identity check" }));

    expect(await screen.findByText("Local workspace access is required to run this check.")).toBeInTheDocument();
    expect(screen.getAllByText("Generator").length).toBeGreaterThan(0);
  });

  test("a model test completion cannot cross into a newer selection", async () => {
    const pending = deferred<ModelTestResponse>();
    testModelMock.mockReturnValue(pending.promise);
    render(<LocaleProvider><ModelsConsole /></LocaleProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "Run identity check" }));
    fireEvent.click(screen.getByRole("button", { name: "Inspect Embedding" }));
    pending.resolve({ model_id: "generator", test_type: "runtime_identity", result: "passed", provider_executed: false, checks: [] });
    await Promise.resolve();

    expect(screen.getByRole("complementary", { name: "Embedding details" })).toBeInTheDocument();
    expect(screen.queryByText("Provider executed: No")).toBeNull();
  });
});
