/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  HealthResponse,
  SupportedTickersResponse,
  QueryRequest,
  QueryResponse,
  DecomposedResponse,
  ClearSessionResponse,
  SessionHistoryResponse,
  RetrievalInspectResponse,
  RetrievalInspectRequest,
  RetrievalPreset,
  DocumentListResponse,
  DocumentSortField,
  DocumentFacetsResponse,
  DocumentStatsResponse,
  DocumentChunkListResponse,
  DocumentChunkDetail,
  DiscoverySearchRequest,
  DiscoverySnapshotResponse,
  OriginalContent,
  OriginalManifest,
  ReaderManifest,
  EvidenceLocation,
  StructuredOutlineResponse,
  StructuredContentResponse,
  StructuredSearchResponse,
  OriginalSearchResponse,
  OriginalLocation,
  PdfMappingManifest,
  PdfEvidenceLocation,
  PdfRepresentationManifest,
  SystemInfoResponse,
  EvaluationRun,
  EvaluationRunListResponse,
  EvaluationRunStatus,
  CollectionActivityListResponse,
  CollectionCreateRequest,
  CollectionExportDocument,
  CollectionExportFormat,
  CollectionItemKind,
  CollectionItemListResponse,
  CollectionItemRecord,
  CollectionItemRequest,
  CollectionListResponse,
  CollectionNoteListResponse,
  CollectionNoteRecord,
  CollectionNoteRequest,
  CollectionNoteUpdateRequest,
  CollectionReceipt,
  CollectionRecord,
  CollectionSortDirection,
  CollectionSortField,
  CollectionUpdateRequest,
} from "../types";

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(
    message: string,
    status: number | null = null,
    code: string | null = null,
    retryAfterSeconds: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

async function throwApiError(response: Response, fallback: string): Promise<never> {
  const text = await response.text().catch(() => "");
  try {
    const payload = JSON.parse(text) as {
      detail?: { code?: unknown; message?: unknown; retry_after_seconds?: unknown } | string;
      code?: unknown;
      error?: unknown;
      retry_after_seconds?: unknown;
    };
    const detail = typeof payload.detail === "object" && payload.detail !== null ? payload.detail : null;
    const code = typeof detail?.code === "string" ? detail.code : typeof payload.code === "string" ? payload.code : null;
    const retryRaw = detail?.retry_after_seconds ?? payload.retry_after_seconds;
    const retryAfterSeconds = typeof retryRaw === "number" ? retryRaw : null;
    const message = typeof detail?.message === "string"
      ? detail.message
      : typeof payload.error === "string"
        ? payload.error
        : typeof payload.detail === "string"
          ? payload.detail
          : fallback;
    throw new ApiError(message, response.status, code, retryAfterSeconds);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(`${fallback}: ${text || response.statusText}`, response.status);
  }
}

// Note: QueryRequest and QueryResponse types are kept for compatibility
// but the frontend uses streaming (streamQuery) and decomposed (queryDecomposed) paths.
// The non-streaming queryDirect function was removed as unused.

export const getApiBaseUrl = (): string => {
  const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  return base.replace(/\/$/, ""); // Remove trailing slash
};

async function apiFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const baseUrl = getApiBaseUrl();
  if (import.meta.env.DEV) {
    console.log(`[API Client] Base URL: ${baseUrl}`);
    console.log(`[API Client] Full Request URL: ${url}`);
  }
  const headers = new Headers(options.headers);
  const isNgrokRequest =
    baseUrl.includes("ngrok") ||
    (typeof window !== "undefined" &&
      window.location.hostname.includes("ngrok"));
  if (isNgrokRequest) {
    headers.set("ngrok-skip-browser-warning", "true");
  }
  return fetch(url, {
    ...options,
    headers,
  });
}

export async function checkHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/health`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Health check failed with status: ${response.status}`, response.status);
  }
  return response.json();
}

export async function getSupportedTickers(
  signal?: AbortSignal,
): Promise<SupportedTickersResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/supported-tickers`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    // The indexed company/section catalog changes infrequently. Allow the
    // browser/edge cache to reuse it across reloads while the health/session
    // endpoints remain request-fresh.
    cache: "force-cache",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch supported tickers: ${response.status}`, response.status);
  }
  return response.json();
}

export async function inspectRetrieval(
  payload: RetrievalInspectRequest,
  signal?: AbortSignal,
): Promise<RetrievalInspectResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/retrieval/inspect`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new ApiError(
      `Retrieval inspection failed with status ${response.status}: ${detail || response.statusText}`,
      response.status,
    );
  }
  return response.json();
}

export async function getDocuments(
  params: {
    ticker?: string | null;
    section?: string | null;
    filing_date?: string | null;
    year?: number | null;
    search?: string;
    sort?: DocumentSortField;
    direction?: "asc" | "desc";
    page?: number;
    page_size?: number;
  } = {},
  signal?: AbortSignal,
): Promise<DocumentListResponse> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const response = await apiFetch(`${baseUrl}/documents?${query.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch documents: ${response.status}`, response.status);
  }
  return response.json();
}

export async function getDocumentFacets(
  params: {
    ticker?: string | null;
    section?: string | null;
    filing_date?: string | null;
    year?: number | null;
    search?: string;
  } = {},
  signal?: AbortSignal,
): Promise<DocumentFacetsResponse> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const response = await apiFetch(`${baseUrl}/documents/facets?${query.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch document facets: ${response.status}`, response.status);
  }
  return response.json();
}

export async function getDocumentStats(signal?: AbortSignal): Promise<DocumentStatsResponse> {
  const response = await apiFetch(`${getApiBaseUrl()}/documents/stats`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch document stats: ${response.status}`, response.status);
  }
  return response.json();
}

/**
 * Run one provider-free discovery search and return its stored snapshot.
 *
 * This is the only call that creates a snapshot: a new query, a newly
 * committed filter scope, or an explicit grouping change. Paging must use
 * `getDiscoverySnapshot` so the result set cannot change under a reader.
 */
export async function createDiscoverySearch(
  body: DiscoverySearchRequest,
  signal?: AbortSignal,
): Promise<DiscoverySnapshotResponse> {
  const response = await apiFetch(`${getApiBaseUrl()}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    cache: "no-store",
    signal,
    body: JSON.stringify(body),
  });
  if (!response.ok) await throwApiError(response, `Search failed: ${response.status}`);
  return response.json();
}

/** Read one page of an existing snapshot without re-running the search. */
export async function getDiscoverySnapshot(
  searchId: string,
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<DiscoverySnapshotResponse> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) query.set(key, String(value));
  }
  const response = await apiFetch(`${getApiBaseUrl()}/search/${encodeURIComponent(searchId)}?${query.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to read the search snapshot: ${response.status}`);
  return response.json();
}

export async function getDocumentChunks(
  documentId: string,
  params: { section?: string | null; search?: string; page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<DocumentChunkListResponse> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const response = await apiFetch(`${baseUrl}/documents/${encodeURIComponent(documentId)}/chunks?${query.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch document chunks: ${response.status}`, response.status);
  }
  return response.json();
}

export async function getChunkDetail(chunkId: string, signal?: AbortSignal): Promise<DocumentChunkDetail> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/chunks/${encodeURIComponent(chunkId)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch chunk: ${response.status}`, response.status);
  }
  return response.json();
}

export async function getOriginalManifest(documentId: string, signal?: AbortSignal): Promise<OriginalManifest> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/documents/${encodeURIComponent(documentId)}/original`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to fetch original manifest: ${response.status}`);
  return response.json();
}

export async function getReaderManifest(documentId: string, signal?: AbortSignal): Promise<ReaderManifest> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/documents/${encodeURIComponent(documentId)}/reader`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to fetch reader manifest: ${response.status}`);
  return response.json();
}

export async function getPdfManifest(documentId: string, signal?: AbortSignal): Promise<PdfRepresentationManifest> {
  const response = await apiFetch(`${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/pdf`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to fetch PDF representation: ${response.status}`);
  return response.json();
}

export async function generatePdfRepresentation(documentId: string, signal?: AbortSignal): Promise<PdfRepresentationManifest> {
  const response = await apiFetch(`${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/pdf`, {
    method: "POST", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to generate PDF representation: ${response.status}`);
  return response.json();
}

export function getPdfContentUrl(documentId: string): string {
  return `${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/pdf/content`;
}

export async function getPdfMapping(documentId: string, signal?: AbortSignal): Promise<PdfMappingManifest> {
  const response = await apiFetch(`${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/pdf/mapping`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to fetch PDF evidence mapping: ${response.status}`);
  return response.json();
}

export async function getPdfEvidenceLocation(
  documentId: string,
  params: {
    chunk_id: string;
    chunk_text_hash: string;
    source_document_id: string;
    source_set_revision: string;
    document_revision: string;
  },
  signal?: AbortSignal,
): Promise<PdfEvidenceLocation> {
  const query = new URLSearchParams(params);
  const response = await apiFetch(`${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/pdf/mapping/location?${query.toString()}`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to locate PDF evidence: ${response.status}`);
  return response.json();
}

function readerQuery(params: { source_document_id: string; source_set_revision: string; document_revision: string; cursor?: number; limit?: number; q?: string }): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  });
  return query.toString();
}

export async function getReaderOutline(documentId: string, params: { source_document_id: string; source_set_revision: string; document_revision: string; cursor?: number; limit?: number }, signal?: AbortSignal): Promise<StructuredOutlineResponse> {
  const response = await apiFetch(`${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/reader/outline?${readerQuery(params)}`, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal });
  if (!response.ok) await throwApiError(response, `Failed to fetch reader outline: ${response.status}`);
  return response.json();
}

export async function getReaderContent(documentId: string, params: { source_document_id: string; source_set_revision: string; document_revision: string; cursor?: number; limit?: number }, signal?: AbortSignal): Promise<StructuredContentResponse> {
  const response = await apiFetch(`${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/reader/content?${readerQuery(params)}`, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal });
  if (!response.ok) await throwApiError(response, `Failed to fetch reader content: ${response.status}`);
  return response.json();
}

export async function searchReader(documentId: string, params: { source_document_id: string; source_set_revision: string; document_revision: string; q: string; cursor?: number; limit?: number }, signal?: AbortSignal): Promise<StructuredSearchResponse> {
  const response = await apiFetch(`${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/reader/search?${readerQuery(params)}`, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal });
  if (!response.ok) await throwApiError(response, `Failed to search structured reader: ${response.status}`);
  return response.json();
}

export function getReaderSectionExportUrl(documentId: string, params: { source_document_id: string; source_set_revision: string; document_revision: string; format?: "html" | "markdown" }): string {
  return `${getApiBaseUrl()}/documents/${encodeURIComponent(documentId)}/reader/section-export?${readerQuery(params)}`;
}

export async function getReaderLocation(
  chunkId: string,
  params: { chunk_text_hash: string; source_set_revision: string },
  signal?: AbortSignal,
): Promise<EvidenceLocation> {
  const query = new URLSearchParams(params);
  const response = await apiFetch(`${getApiBaseUrl()}/chunks/${encodeURIComponent(chunkId)}/reader-location?${query.toString()}`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to locate structured evidence: ${response.status}`);
  return response.json();
}

export async function getOriginalContent(
  documentId: string,
  params: {
    source_document_id: string;
    source_set_revision: string;
    document_revision: string;
    start?: number;
    limit?: number;
    chunk_id?: string | null;
    chunk_text_hash?: string | null;
    find?: string | null;
  },
  signal?: AbortSignal,
): Promise<OriginalContent> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  });
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/documents/${encodeURIComponent(documentId)}/original/content?${query.toString()}`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to fetch original content: ${response.status}`);
  return response.json();
}

export async function searchOriginal(
  documentId: string,
  params: {
    source_document_id: string;
    source_set_revision: string;
    document_revision: string;
    q: string;
    cursor?: number;
    limit?: number;
  },
  signal?: AbortSignal,
): Promise<OriginalSearchResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  });
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/documents/${encodeURIComponent(documentId)}/original/search?${query.toString()}`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to search original: ${response.status}`);
  return response.json();
}

export async function getOriginalLocation(
  chunkId: string,
  params: { chunk_text_hash: string; source_set_revision: string },
  signal?: AbortSignal,
): Promise<OriginalLocation> {
  const query = new URLSearchParams(params);
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/chunks/${encodeURIComponent(chunkId)}/original-location?${query.toString()}`, {
    method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal,
  });
  if (!response.ok) await throwApiError(response, `Failed to locate indexed evidence: ${response.status}`);
  return response.json();
}

export async function getSystemInfo(signal?: AbortSignal): Promise<SystemInfoResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/system/info`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch system info: ${response.status}`, response.status);
  }
  return response.json();
}

export async function getEvaluationRuns(
  params: {
    status?: EvaluationRunStatus | null;
    language?: "en" | "vi" | null;
    intent?: string | null;
    ticker?: string | null;
    gate?: string | null;
    page?: number;
    page_size?: number;
  } = {},
  signal?: AbortSignal,
): Promise<EvaluationRunListResponse> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const response = await apiFetch(`${baseUrl}/evaluation/runs?${query.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch evaluation runs: ${response.status}`, response.status);
  }
  return response.json();
}

export async function getEvaluationRun(runId: string, signal?: AbortSignal): Promise<EvaluationRun> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/evaluation/runs/${encodeURIComponent(runId)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch evaluation run: ${response.status}`, response.status);
  }
  return response.json();
}

export async function queryDecomposed(
  payload: QueryRequest,
  signal?: AbortSignal,
): Promise<DecomposedResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/query/decomposed`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) {
    await throwApiError(response, `Decomposed query failed with status: ${response.status}`);
  }
  return response.json();
}

export async function deleteSession(
  sessionId: string,
): Promise<ClearSessionResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/session/${sessionId}`, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new ApiError(`Failed to delete session: ${response.status}`, response.status);
  }
  return response.json();
}

export async function getSessionHistory(
  sessionId: string,
  signal?: AbortSignal,
): Promise<SessionHistoryResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await apiFetch(`${baseUrl}/session/${sessionId}/history`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch session history: ${response.status}`, response.status);
  }
  return response.json();
}

/**
 * Handles the POST /query/stream SSE response chunk-by-chunk using a ReadableStream reader.
 */
export async function streamQuery(
  payload: QueryRequest,
  onEvent: (event: { type: string; data: any }) => void,
  onError: (error: Error) => void,
  signal?: AbortSignal,
): Promise<void> {
  const baseUrl = getApiBaseUrl();
  try {
    const response = await apiFetch(`${baseUrl}/query/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      await throwApiError(response, `Streaming query failed with status ${response.status}`);
    }

    if (!response.body) {
      throw new ApiError("No readable response body available for streaming.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");

      // Keep the last incomplete line in buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith("data: ")) {
          const jsonStr = trimmed.slice(6);
          try {
            const parsed = JSON.parse(jsonStr);
            onEvent(parsed);
          } catch (e) {
            console.error("Failed to parse stream event JSON:", trimmed, e);
          }
        }
      }
    }

    // Process any remaining text in buffer
    if (buffer) {
      const trimmed = buffer.trim();
      if (trimmed.startsWith("data: ")) {
        try {
          const parsed = JSON.parse(trimmed.slice(6));
          onEvent(parsed);
        } catch (e) {
          console.error("Failed to parse remaining stream buffer:", trimmed, e);
        }
      }
    }
  } catch (error: any) {
    if (signal?.aborted || error?.name === "AbortError") return;
    onError(
      error instanceof Error
        ? error
        : new Error(error?.message || "Unknown streaming error occurred."),
    );
  }
}

/** Handles the comparative SSE endpoint while keeping queryDecomposed available for legacy clients. */
export async function streamDecomposedQuery(
  payload: QueryRequest,
  onEvent: (event: { type: string; data: any }) => void,
  onError: (error: Error) => void,
  signal?: AbortSignal,
): Promise<void> {
  const baseUrl = getApiBaseUrl();
  try {
    const response = await apiFetch(`${baseUrl}/query/decomposed/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(payload),
      signal,
    });
    if (!response.ok) {
      await throwApiError(response, `Comparative streaming query failed with status ${response.status}`);
    }
    if (!response.body) throw new ApiError("No readable response body available for comparative streaming.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    const consume = (line: string) => {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) return;
      try {
        onEvent(JSON.parse(trimmed.slice(6)));
      } catch (error) {
        console.error("Failed to parse comparative stream event JSON:", trimmed, error);
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      lines.forEach(consume);
    }
    if (buffer.trim()) consume(buffer);
  } catch (error: any) {
    if (signal?.aborted || error?.name === "AbortError") return;
    onError(error instanceof Error ? error : new Error(error?.message || "Unknown comparative streaming error occurred."));
  }
}

/* ------------------------------------------------------------------ *
 * DATA-003 typed collections.
 *
 * These routes are private local-workspace routes (API-001 grant `L`): a
 * 404 means the capability is unavailable in this deployment mode, 401 that
 * the workspace token is required, 403 that the request is not from the
 * local machine, 410 that the record is tombstoned, 409 that the caller's
 * revision is stale and 422 that a bound, kind or reference was refused.
 * `throwApiError` keeps the status and the server's bounded detail, so the
 * page can tell those states apart instead of collapsing them into one.
 * ------------------------------------------------------------------ */

function collectionQuery(params: Record<string, unknown>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const entry of value) if (entry !== undefined && entry !== null && entry !== "") query.append(key, String(entry));
      continue;
    }
    query.set(key, String(value));
  }
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}

async function collectionsJson<T>(
  path: string,
  init: RequestInit,
  fallback: string,
): Promise<T> {
  const response = await apiFetch(`${getApiBaseUrl()}${path}`, init);
  if (!response.ok) await throwApiError(response, fallback);
  return response.json() as Promise<T>;
}

export async function listCollections(
  params: {
    search?: string | null;
    tags?: string[] | null;
    favorite?: boolean | null;
    sort?: CollectionSortField;
    direction?: CollectionSortDirection;
    page?: number;
    page_size?: number;
  } = {},
  signal?: AbortSignal,
): Promise<CollectionListResponse> {
  const path = `/collections${collectionQuery({ ...params })}`;
  return collectionsJson<CollectionListResponse>(path, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  }, `Failed to list collections: ${path}`);
}

export async function getCollection(collectionId: string, signal?: AbortSignal): Promise<CollectionRecord> {
  return collectionsJson<CollectionRecord>(`/collections/${encodeURIComponent(collectionId)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  }, "Failed to read the collection");
}

export async function createCollection(
  body: CollectionCreateRequest,
  signal?: AbortSignal,
): Promise<CollectionRecord> {
  return collectionsJson<CollectionRecord>("/collections", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
    signal,
  }, "Failed to create the collection");
}

export async function updateCollection(
  collectionId: string,
  body: CollectionUpdateRequest,
  signal?: AbortSignal,
): Promise<CollectionRecord> {
  return collectionsJson<CollectionRecord>(`/collections/${encodeURIComponent(collectionId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
    signal,
  }, "Failed to update the collection");
}

export async function deleteCollection(
  collectionId: string,
  revision: number,
  signal?: AbortSignal,
): Promise<CollectionReceipt> {
  return collectionsJson<CollectionReceipt>(
    `/collections/${encodeURIComponent(collectionId)}${collectionQuery({ revision })}`,
    { method: "DELETE", headers: { Accept: "application/json" }, signal },
    "Failed to delete the collection",
  );
}

export async function listCollectionItems(
  collectionId: string,
  params: { kind?: CollectionItemKind | null; page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<CollectionItemListResponse> {
  const path = `/collections/${encodeURIComponent(collectionId)}/items${collectionQuery({ ...params })}`;
  return collectionsJson<CollectionItemListResponse>(path, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  }, "Failed to list the collection items");
}

export async function addCollectionItem(
  collectionId: string,
  body: CollectionItemRequest,
  signal?: AbortSignal,
): Promise<CollectionItemRecord> {
  return collectionsJson<CollectionItemRecord>(`/collections/${encodeURIComponent(collectionId)}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
    signal,
  }, "Failed to add the collection item");
}

export async function deleteCollectionItem(
  collectionId: string,
  itemId: string,
  revision: number,
  signal?: AbortSignal,
): Promise<CollectionReceipt> {
  return collectionsJson<CollectionReceipt>(
    `/collections/${encodeURIComponent(collectionId)}/items/${encodeURIComponent(itemId)}${collectionQuery({ revision })}`,
    { method: "DELETE", headers: { Accept: "application/json" }, signal },
    "Failed to remove the collection item",
  );
}

export async function listCollectionNotes(
  collectionId: string,
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<CollectionNoteListResponse> {
  const path = `/collections/${encodeURIComponent(collectionId)}/notes${collectionQuery({ ...params })}`;
  return collectionsJson<CollectionNoteListResponse>(path, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  }, "Failed to list the collection notes");
}

export async function addCollectionNote(
  collectionId: string,
  body: CollectionNoteRequest,
  signal?: AbortSignal,
): Promise<CollectionNoteRecord> {
  return collectionsJson<CollectionNoteRecord>(`/collections/${encodeURIComponent(collectionId)}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
    signal,
  }, "Failed to add the collection note");
}

export async function updateCollectionNote(
  collectionId: string,
  noteId: string,
  body: CollectionNoteUpdateRequest,
  signal?: AbortSignal,
): Promise<CollectionNoteRecord> {
  return collectionsJson<CollectionNoteRecord>(
    `/collections/${encodeURIComponent(collectionId)}/notes/${encodeURIComponent(noteId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      signal,
    },
    "Failed to update the collection note",
  );
}

export async function deleteCollectionNote(
  collectionId: string,
  noteId: string,
  revision: number,
  signal?: AbortSignal,
): Promise<CollectionReceipt> {
  return collectionsJson<CollectionReceipt>(
    `/collections/${encodeURIComponent(collectionId)}/notes/${encodeURIComponent(noteId)}${collectionQuery({ revision })}`,
    { method: "DELETE", headers: { Accept: "application/json" }, signal },
    "Failed to delete the collection note",
  );
}

export async function listCollectionActivity(
  collectionId: string,
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<CollectionActivityListResponse> {
  const path = `/collections/${encodeURIComponent(collectionId)}/activity${collectionQuery({ ...params })}`;
  return collectionsJson<CollectionActivityListResponse>(path, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  }, "Failed to list the collection activity");
}

export type CollectionExportResult =
  | { format: "json"; document: CollectionExportDocument }
  | { format: "markdown"; content: string };

export async function exportCollection(
  collectionId: string,
  format: CollectionExportFormat = "json",
  signal?: AbortSignal,
): Promise<CollectionExportResult> {
  const response = await apiFetch(
    `${getApiBaseUrl()}/collections/${encodeURIComponent(collectionId)}/export${collectionQuery({ format })}`,
    { method: "GET", headers: { Accept: "application/json" }, cache: "no-store", signal },
  );
  if (!response.ok) await throwApiError(response, "Failed to export the collection");
  const payload = await response.json();
  if (payload && typeof payload === "object" && (payload as { format?: unknown }).format === "markdown") {
    return { format: "markdown", content: String((payload as { content?: unknown }).content ?? "") };
  }
  return { format: "json", document: payload as CollectionExportDocument };
}
