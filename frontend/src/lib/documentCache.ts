import { getApiBaseUrl, getChunkDetail, getDocumentChunks } from "./api";
import type { DocumentChunkDetail, DocumentChunkListResponse } from "../types";

const CACHE_TTL_MS = 5 * 60 * 1000;
const MAX_CHUNK_DETAILS = 100;

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

const detailCache = new Map<string, CacheEntry<DocumentChunkDetail>>();
const listCache = new Map<string, CacheEntry<DocumentChunkListResponse>>();
const detailInFlight = new Map<string, Promise<DocumentChunkDetail>>();
const listInFlight = new Map<string, Promise<DocumentChunkListResponse>>();

function cacheKey(resource: string, identity: string): string {
  let apiBase = "unknown";
  try {
    apiBase = typeof getApiBaseUrl === "function" ? getApiBaseUrl() : "unknown";
  } catch {
    // Keep cache isolation deterministic in tests or partially configured shells.
  }
  return `${apiBase}|${resource}|${identity}`;
}

function read<T>(cache: Map<string, CacheEntry<T>>, key: string): T | undefined {
  const entry = cache.get(key);
  if (!entry) return undefined;
  if (entry.expiresAt <= Date.now()) {
    cache.delete(key);
    return undefined;
  }
  return entry.value;
}

function writeDetail(key: string, value: DocumentChunkDetail): void {
  detailCache.delete(key);
  detailCache.set(key, { value, expiresAt: Date.now() + CACHE_TTL_MS });
  while (detailCache.size > MAX_CHUNK_DETAILS) {
    const oldest = detailCache.keys().next().value;
    if (typeof oldest !== "string") break;
    detailCache.delete(oldest);
  }
}

function withAbort<T>(promise: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return promise;
  if (signal.aborted) return Promise.reject(new DOMException("The request was aborted.", "AbortError"));
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => reject(new DOMException("The request was aborted.", "AbortError"));
    signal.addEventListener("abort", onAbort, { once: true });
    promise.then(
      (value) => { signal.removeEventListener("abort", onAbort); resolve(value); },
      (error) => { signal.removeEventListener("abort", onAbort); reject(error); },
    );
  });
}

export function getCachedChunkDetail(chunkId: string, signal?: AbortSignal): Promise<DocumentChunkDetail> {
  const key = cacheKey("chunk", chunkId);
  const cached = read(detailCache, key);
  if (cached) return withAbort(Promise.resolve(cached), signal);
  let request = detailInFlight.get(key);
  if (!request) {
    const requestController = new AbortController();
    request = getChunkDetail(chunkId, requestController.signal).then((value) => {
      writeDetail(key, value);
      return value;
    }).finally(() => detailInFlight.delete(key));
    detailInFlight.set(key, request);
  }
  return withAbort(request, signal);
}

export function getCachedDocumentChunks(
  documentId: string,
  params: { section?: string | null; search?: string; page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<DocumentChunkListResponse> {
  const identity = `${documentId}|${JSON.stringify(params)}`;
  const key = cacheKey("document-chunks", identity);
  const cached = read(listCache, key);
  if (cached) return withAbort(Promise.resolve(cached), signal);
  let request = listInFlight.get(key);
  if (!request) {
    const requestController = new AbortController();
    request = getDocumentChunks(documentId, params, requestController.signal).then((value) => {
      listCache.set(key, { value, expiresAt: Date.now() + CACHE_TTL_MS });
      return value;
    }).finally(() => listInFlight.delete(key));
    listInFlight.set(key, request);
  }
  return withAbort(request, signal);
}

export function clearDocumentCache(): void {
  detailCache.clear();
  listCache.clear();
  detailInFlight.clear();
  listInFlight.clear();
}
