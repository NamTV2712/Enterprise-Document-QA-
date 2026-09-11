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
  score?: number | null;
  text_preview: string;
  text?: string;
  chunk_id?: string | null;
  document_id?: string | null;
  ticker?: string | null;
  filing_type?: string | null;
  section?: string | null;
  filing_date?: string | null;
  report_date?: string | null;
  chunk_index?: number | null;
  source_url?: string | null;
  sec_index_url?: string | null;
  chunk_text_hash?: string;
  rank?: number | null;
  score_kind?: "retrieval" | "cross_encoder" | "rrf" | "unknown" | null;
  reranker_score?: number | null;
  /** Transient UI marker; never persisted in evidence collection storage. */
  stored_snapshot?: {
    chunk_id?: string | null;
  };
}

/** Exact source-selection identity used by citation jumps and the evidence rail. */
export interface EvidenceSelection {
  conversationId: string;
  messageId: string;
  variantId?: string;
  citationIndex: number;
  chunkId?: string;
  documentId?: string;
  /** Deterministic source identity, including an excerpt fallback when IDs are absent. */
  sourceKey: string;
}

/** Transient identity of the answer currently focused or displayed by the user. */
export interface DisplayedAnswerContext {
  conversationId: string;
  messageId: string;
  variantId: string | null;
}

/** User-visible state for saving the answer that is currently displayed. */
export type SaveAnswerVersionStatus =
  | "idle"
  | "saving"
  | "saved"
  | "already_saved"
  | "failed"
  | "volatile";

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
  fusion_rank?: number | null;
  final_rank?: number | null;
  document_id?: string | null;
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
  candidate_count?: number;
  selected_count?: number;
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
  report_date?: string | null;
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
  report_date?: string | null;
  accession_number: string | null;
  chunk_index?: number | null;
  text_preview: string;
  text_length: number;
  source_url: string | null;
}

export interface DocumentChunkDetail extends DocumentChunk {
  document_id: string;
  text: string;
  chunk_text_hash?: string;
  sec_index_url?: string | null;
  presentation?:
    | { kind: "plain_text"; reason: string | null }
    | { kind: "markdown_table"; caption: string | null; units: string | null; columns: string[]; rows: string[][] };
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
  capabilities?: {
    stage_events?: boolean;
    comparative_stream?: boolean;
    document_indexed_viewer?: boolean;
    original_document_viewer?: {
      enabled: boolean;
      representation: "normalized_text";
      normalizer_version: string;
    };
  };
}

export interface OriginalManifestSource {
  source_document_id: string;
  role: "primary_filing" | "annual_report_companion";
  label: string;
  status: "available" | "unavailable";
  reason: string | null;
  document_revision: string | null;
  text_length: number | null;
}

export interface OriginalManifest {
  document_id: string;
  status: "available" | "partial" | "unavailable";
  reason: string | null;
  normalizer_version: string;
  source_set_revision: string;
  sources: OriginalManifestSource[];
}

export interface ReaderFilingIdentity {
  ticker: string | null;
  cik: number | null;
  accession_number: string | null;
  filing_date: string | null;
  report_date: string | null;
  status: "verified" | "unverified";
  reason_code: "verified" | "identity_unverified";
}

export interface ReaderAvailability {
  kind: "normalized_text" | "structured" | "pdf";
  status: "available" | "partial" | "unavailable";
  reason_code:
    | "available"
    | "identity_unverified"
    | "source_unavailable"
    | "structured_representation_unavailable"
    | "pdf_representation_unavailable";
  reason: string | null;
}

export interface CanonicalSource {
  source_document_id: string;
  role: "primary_filing" | "annual_report_companion";
  label: string;
  status: "available" | "unavailable";
  reason_code: "available" | "identity_unverified" | "source_unavailable";
  reason: string | null;
  canonical_url: string | null;
  media_type: "text/html";
  document_revision: string | null;
  text_length: number | null;
}

export interface ReaderManifest {
  schema_version: "sec-reader-v4";
  document_id: string;
  status: "available" | "partial" | "unavailable";
  reason_code: "available" | "identity_unverified" | "source_unavailable";
  reason: string | null;
  identity: ReaderFilingIdentity;
  source_set_revision: string;
  sources: CanonicalSource[];
  representations: ReaderAvailability[];
}

export interface ReaderAcquisition {
  status: "not_needed" | "acquired" | "unavailable";
  code: string;
  message: string;
  canonical_url: string | null;
  raw_sha256: string | null;
  bytes_received: number | null;
  request_count: number;
}

export interface ReaderResolveResponse {
  manifest: ReaderManifest;
  acquisition: ReaderAcquisition;
}

export interface StructuredRun {
  text: string;
  emphasis: boolean;
  strong: boolean;
  superscript: boolean;
  subscript: boolean;
}

export interface StructuredCell {
  text: string;
  rowspan: number;
  colspan: number;
  header: boolean;
}

export interface StructuredBlock {
  block_id: string;
  kind: "heading" | "paragraph" | "list" | "table" | "separator" | "unsupported";
  text: string;
  runs: StructuredRun[];
  level: number | null;
  anchor: string | null;
  items: string[];
  caption: string | null;
  units?: string | null;
  columns: string[];
  rows: StructuredCell[][];
  continuation_index?: number | null;
  continuation_count?: number | null;
  source_text?: string;
}

export interface StructuredOutlineItem {
  block_id: string;
  label: string;
  level: number;
  anchor: string;
}

export interface StructuredOutlineResponse {
  document_id: string;
  source_document_id: string;
  source_set_revision: string;
  document_revision: string;
  items: StructuredOutlineItem[];
  next_cursor: number | null;
  complete: boolean;
  limitations: string[];
}

export interface StructuredContentResponse {
  document_id: string;
  source_document_id: string;
  source_set_revision: string;
  document_revision: string;
  blocks: StructuredBlock[];
  previous_cursor: number | null;
  next_cursor: number | null;
  complete: boolean;
  limitations: string[];
}

export interface StructuredSearchMatch {
  block_id: string;
  block_index: number;
  start: number;
  end: number;
  quote: string;
}

export interface StructuredSearchResponse {
  document_id: string;
  source_document_id: string;
  source_set_revision: string;
  document_revision: string;
  query: string;
  matches: StructuredSearchMatch[];
  total: number;
  next_cursor: number | null;
  complete: boolean;
}

export interface EvidenceRange {
  block_id: string;
  block_index: number;
  kind: StructuredBlock["kind"];
  start: number;
  end: number;
  method: "text_whitespace" | "table_semantic";
}

export interface EvidenceLocation {
  chunk_id: string;
  chunk_text_hash: string;
  document_id: string;
  source_set_revision: string;
  status: "exact" | "ambiguous" | "not_found" | "unavailable" | "stale";
  reason_code: "exact" | "ambiguous" | "not_found" | "unavailable" | "stale";
  reason: string | null;
  source_document_id: string | null;
  document_revision: string | null;
  representation_revision: string | null;
  ranges: EvidenceRange[];
  match_count: number;
  match_count_capped: boolean;
}

export interface OriginalContentSegment {
  text: string;
  evidence: boolean;
  search: boolean;
}

export interface OriginalContent {
  document_id: string;
  source_document_id: string;
  source_set_revision: string;
  document_revision: string;
  start: number;
  end: number;
  total_length: number;
  previous_start: number | null;
  next_start: number | null;
  segments: OriginalContentSegment[];
}

export interface OriginalSearchMatch {
  start: number;
  end: number;
  preview: string;
}

export interface OriginalSearchResponse {
  document_id: string;
  source_document_id: string;
  source_set_revision: string;
  document_revision: string;
  query: string;
  matches: OriginalSearchMatch[];
  next_cursor: number | null;
}

export interface OriginalLocation {
  chunk_id: string;
  chunk_text_hash: string;
  document_id: string;
  source_set_revision: string;
  matcher_version: string;
  status: "exact" | "not_found" | "ambiguous" | "unavailable";
  reason: string | null;
  match_count: 0 | 1 | 2;
  match_count_capped: boolean;
  location: {
    source_document_id: string;
    document_revision: string;
    method: "full_text_whitespace" | "table_serialization";
    start: number;
    end: number;
  } | null;
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

export interface ConversationNote {
  id: string;
  text: string;
  createdAt: number;
  updatedAt: number;
}

export type AnswerVariantStatus = "completed" | "stopped" | "error";

export type FeedbackRating = "up" | "down";
export type FeedbackCategory =
  | "inaccurate"
  | "incomplete"
  | "irrelevant"
  | "citation_issue"
  | "other";

export interface MessageFeedback {
  rating: FeedbackRating;
  category?: FeedbackCategory;
  at: number;
}

/** A saved answer alternative with its own evidence and request provenance. */
export interface AnswerVariant {
  id: string;
  originMessageId: string;
  text: string;
  sources: Source[];
  requestSnapshot?: RequestSnapshot;
  answerLanguage: AnswerLanguage;
  status: AnswerVariantStatus;
  /** Optional backend-measured work for this answer variant. */
  execution?: ExecutionTrace;
  /** Optional fact that is valid only against this variant's sources. */
  visualAnswer?: VisualAnswer;
  createdAt: number;
  updatedAt: number;
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

/** Actual request-scoped work reported by the backend; absent means unavailable. */
export interface ExecutionTrace {
  request_id?: string;
  elapsed_ms: number;
  stages: Array<{
    name: string;
    elapsed_ms: number;
    status: string;
  }>;
}

export type StageEventStatus = "pending" | "running" | "success" | "failed" | "skipped" | "cancelled";

export interface StageEvent {
  version: 1;
  request_id: string;
  sequence: number;
  stage_id: string;
  parent_stage_id?: string | null;
  status: StageEventStatus;
  elapsed_ms?: number;
  counters?: {
    candidate_count?: number;
    source_count?: number;
    subquery_count?: number;
    token_count?: number;
  };
  metadata?: Record<string, string | number | boolean | null>;
}

/** A backend-verified fact eligible for a compact visual treatment. */
export interface VisualAnswer {
  kind: "metric";
  metric: string;
  label: string;
  value: string;
  display_value: string;
  unit: string;
  period: string;
  source_index: number;
  source_chunk_id: string;
  citation: string;
  evidence_quote: string;
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
  visual_answer?: VisualAnswer;
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
  execution?: ExecutionTrace;
  visualAnswer?: VisualAnswer;
  note?: string;
  feedback?: MessageFeedback;
}
