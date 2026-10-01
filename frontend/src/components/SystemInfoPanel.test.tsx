import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { SystemInfoPanel } from "./SystemInfoPanel";
import { LocaleProvider } from "../lib/i18n";
import { getSystemInfo } from "../lib/api";
import type { SystemInfoResponse } from "../types";

vi.mock("../lib/api", () => ({ getSystemInfo: vi.fn() }));
const getSystemInfoMock = vi.mocked(getSystemInfo);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const info: SystemInfoResponse = {
  api_version: "test-api",
  corpus: { searchable_company_count: 50, indexed_chunk_count: 10053 },
  retrieval: { embedding_model: "embed", reranker_model: "reranker", presets: ["bm25", "hybrid_rerank"], default: "hybrid_rerank" },
  build: {},
  capabilities: { document_indexed_viewer: true, original_document_viewer: { enabled: true, representation: "normalized_text" as const, normalizer_version: "test" } },
};

describe("SystemInfoPanel", () => {
  test("shows actionable truthful status and exposes safe next actions", async () => {
    getSystemInfoMock.mockResolvedValue(info);
    const onOpenDocuments = vi.fn();
    const onOpenRetrieval = vi.fn();
    const onOpenEvaluation = vi.fn();
    render(<LocaleProvider><SystemInfoPanel onOpenDocuments={onOpenDocuments} onOpenRetrieval={onOpenRetrieval} onOpenEvaluation={onOpenEvaluation} /></LocaleProvider>);
    expect(await screen.findByRole("heading", { name: "System & provenance" })).toBeInTheDocument();
    expect(screen.getByText("Reader availability")).toBeInTheDocument();
    expect(screen.getByText("No verified source")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Open Documents/i }));
    fireEvent.click(screen.getByRole("button", { name: /Open Retrieval Lab/i }));
    fireEvent.click(screen.getByRole("button", { name: /Open Evaluation/i }));
    expect(onOpenDocuments).toHaveBeenCalledTimes(1);
    expect(onOpenRetrieval).toHaveBeenCalledTimes(1);
    expect(onOpenEvaluation).toHaveBeenCalledTimes(1);
  });

  test("refreshes without changing the capability contract", async () => {
    getSystemInfoMock.mockResolvedValue(info);
    render(<LocaleProvider><SystemInfoPanel /></LocaleProvider>);
    await screen.findByRole("heading", { name: "System & provenance" });
    fireEvent.click(screen.getByRole("button", { name: "Refresh status" }));
    expect(getSystemInfoMock).toHaveBeenCalledTimes(2);
  });
});
