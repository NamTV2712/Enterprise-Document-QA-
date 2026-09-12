import { beforeEach, describe, expect, test, vi } from "vitest";
import { getChunkDetail, getDocumentChunks } from "./api";
import { clearDocumentCache, getCachedChunkDetail, getCachedDocumentChunks } from "./documentCache";

vi.mock("./api", () => ({
  getApiBaseUrl: () => "http://localhost:8000",
  getChunkDetail: vi.fn(),
  getDocumentChunks: vi.fn(),
}));

const getChunkDetailMock = vi.mocked(getChunkDetail);
const getDocumentChunksMock = vi.mocked(getDocumentChunks);

describe("document cache", () => {
  beforeEach(() => {
    clearDocumentCache();
    vi.clearAllMocks();
  });

  test("deduplicates in-flight detail and document list requests", async () => {
    getChunkDetailMock.mockResolvedValue({ chunk_id: "chunk-1", text: "Full text" } as never);
    getDocumentChunksMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 8 } as never);

    const [detailA, detailB] = await Promise.all([
      getCachedChunkDetail("chunk-1"),
      getCachedChunkDetail("chunk-1"),
    ]);
    const [listA, listB] = await Promise.all([
      getCachedDocumentChunks("doc-1", { page: 1, page_size: 8 }),
      getCachedDocumentChunks("doc-1", { page: 1, page_size: 8 }),
    ]);

    expect(detailA).toEqual(detailB);
    expect(listA).toEqual(listB);
    expect(getChunkDetailMock).toHaveBeenCalledTimes(1);
    expect(getDocumentChunksMock).toHaveBeenCalledTimes(1);
  });

  test("bounds chunk detail entries to the documented maximum", async () => {
    getChunkDetailMock.mockImplementation(async (chunkId) => ({ chunk_id: chunkId, text: chunkId }) as never);
    for (let index = 0; index < 101; index += 1) await getCachedChunkDetail(`chunk-${index}`);
    await getCachedChunkDetail("chunk-0");

    expect(getChunkDetailMock).toHaveBeenCalledTimes(102);
  });
});
