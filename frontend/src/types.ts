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
  answer_language: AnswerLanguage;
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

export type RetrievalPreset = "bm25" | "dense" | "hybrid" | "hybrid_rerank";

export interface RetrievalCandidate {
  chunk_id: string;
  ticker?: string | null;
  section?: string | null;
  filing_date?: string | null;
  citation: string;
  text_preview: string;
  bm25_score?: number | null;
  bm25_rank?: number | null;
  dense_score?: number | null;
  dense_rank?: number | null;
  lexical_rank?: number | null;
  rrf_score?: number | null;
  cross_encoder_score?: number | null;
  final_rank?: number | null;
  selected: boolean;
}

export interface RetrievalTrace {
  preset: RetrievalPreset;
  query: string;
  filters: { ticker: string | null; section: string | null };
  top_k: number;
  candidate_pool: number;
  models: {
    embedding?: string | null;
    reranker?: string | null;
    rrf_k?: number;
  };
  stages: Array<{ name: string; elapsed_ms: number; skipped?: boolean }>;
  candidates: RetrievalCandidate[];
  selected_chunk_ids: string[];
  elapsed_ms: number;
}

export interface RetrievalInspectResponse {
  query_interpretation: QueryInterpretation;
  trace: RetrievalTrace;
}

export interface DocumentRow {
  document_id: string;
  ticker: string | null;
  filing_date: string | null;
  accession_number: string | null;
  sections: string[];
  chunk_count: number;
  source_url: string | null;
}

export interface DocumentChunk {
  chunk_id: string | null;
  ticker: string | null;
  section: string | null;
  filing_date: string | null;
  accession_number: string | null;
  text_preview: string;
  text_length: number;
  source_url: string | null;
}

export interface DocumentListResponse {
  items: DocumentRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentChunkListResponse {
  items: DocumentChunk[];
  total: number;
  page: number;
  page_size: number;
}

export interface SystemInfoResponse {
  api_version: string;
  corpus: Record<string, unknown>;
  retrieval: {
    embedding_model?: string | null;
    reranker_model?: string | null;
    presets: RetrievalPreset[];
    default: RetrievalPreset;
  };
  build: Record<string, string>;
}

export type EvaluationRunStatus = "official" | "candidate" | "historical" | "incomplete";

export interface EvaluationCase {
  case_id: string;
  question: string;
  language: AnswerLanguage;
  intent?: string | null;
  ticker?: string | null;
  status: "OK" | "ERROR" | "MISSING";
  answer?: string | null;
  scores: Record<string, number>;
  gates: Record<string, boolean | number | string>;
  reasons: string[];
  evidence: Array<{ citation: string; excerpt: string }>;
}

export interface EvaluationRunSummary {
  run_id: string;
  title: string;
  status: EvaluationRunStatus;
  created_at: string;
  provenance: Record<string, string>;
  aggregate: Record<string, number>;
  case_count: number;
}

export interface EvaluationRun extends Omit<EvaluationRunSummary, "case_count"> {
  cases: EvaluationCase[];
  notes: string[];
}

export interface EvaluationRunListResponse {
  items: EvaluationRunSummary[];
  total: number;
  page: number;
  page_size: number;
}

export type ThemePreference = "system" | "light" | "dark";
export type AnswerLanguage = "en" | "vi";
export type MessageStatus = "streaming" | "stopped" | "completed" | "error";

export interface RequestSnapshot {
  ticker: string | null;
  section: string | null;
  topK: number;
  enableComparative: boolean;
  answerLanguage: AnswerLanguage;
}

export interface QueryResponse {
  answer: string;
  model_used: string;
  sources: Source[];
  num_chunks_retrieved: number;
  answer_language?: AnswerLanguage;
  query_interpretation?: QueryInterpretation;
}

export interface QueryInterpretation {
  original_question: string;
  retrieval_question: string;
  translation_method: string;
  detected_ticker?: string | null;
  requested_periods: string[];
  is_comparative: boolean;
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
  answer_language?: AnswerLanguage;
  query_interpretation?: QueryInterpretation;
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
  queryInterpretation?: QueryInterpretation;
  note?: string;
}
