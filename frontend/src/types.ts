/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface HealthResponse {
  status: string;
  pipeline_ready: boolean;
  memory: {
    active_sessions: number;
    total_turns: number;
  };
  corpus?: {
    searchable_company_count?: number;
    indexed_chunk_count?: number;
  };
}

export interface SupportedTickersResponse {
  tickers: string[];
  sections: string[];
}

export interface QueryRequest {
  question: string;
  ticker: string | null;
  section: string | null;
  top_k: number;
  session_id: string | null;
}

export interface Source {
  citation: string;
  score: number;
  text_preview: string;
  text?: string;
  chunk_id?: string;
  ticker?: string;
  section?: string;
  filing_date?: string;
}

export type ThemePreference = "system" | "light" | "dark";
export type MessageStatus = "streaming" | "stopped" | "completed" | "error";

export interface RequestSnapshot {
  ticker: string | null;
  section: string | null;
  topK: number;
  enableComparative: boolean;
}

export interface QueryResponse {
  answer: string;
  model_used: string;
  sources: Source[];
  num_chunks_retrieved: number;
}

export interface SubQuery {
  query: string;
  ticker: string | null;
  section: string | null;
  num_chunks: number;
}

export interface DecomposedResponse {
  answer: string;
  model_used: string;
  was_decomposed: boolean;
  sub_queries: SubQuery[];
  sources: Source[];
  num_total_chunks: number;
}

export interface SessionContextInfo {
  status: "available" | "missing";
  retained_turns: number;
  ttl_remaining_seconds: number;
}

export interface SessionHistoryResponse {
  session_id: string;
  turns: HistoryTurn[];
  context?: SessionContextInfo;
}

export interface HistoryTurn {
  user: string;
  assistant: string;
  rewritten_query: string | null;
}

export interface ClearSessionResponse {
  cleared: string;
}

// UI State interfaces
export interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  sources?: Source[];
  model_used?: string;
  isStreaming?: boolean;
  subQueries?: SubQuery[];
  wasDecomposed?: boolean;
  numChunks?: number;
  rewritten_query?: string | null;
  error?: boolean;
  errorDetail?: string;
  retryText?: string;
  status?: MessageStatus;
  requestSnapshot?: RequestSnapshot;
}
