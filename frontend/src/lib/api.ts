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
} from "../types";

export class ApiError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
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
    throw new ApiError(`Decomposed query failed with status: ${response.status}`, response.status);
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
      const errText = await response.text().catch(() => "");
      throw new ApiError(
        `Streaming query failed with status ${response.status}: ${errText || response.statusText}`,
        response.status,
      );
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
