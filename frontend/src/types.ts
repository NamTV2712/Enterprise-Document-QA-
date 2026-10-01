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
    document_revision?: string | null;
    source_set_revision?: string | null;
    representation?: "indexed_excerpt" | "structured_html" | "normalized_text";
    coverage_status?: ReaderCoverageStatus;
    location_status?: EvidenceLocation["status"];
    snapshot_state?: "captured" | "stale" | "unknown";
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
  | "volatile"
  | "pending"
  | "persisted"
  | "already_exists"
  | "retryable"
  | "cancelled";

/** Shared local action state used by answer controls. */
export type AnswerActionStatus =
  | "idle"
  | "pending"
  | "persisted"
  | "already_exists"
  | "volatile"
  | "failed"
  | "retryable"
  | "cancelled";

export type AnswerActionKind = "bookmark" | "save_version" | "feedback" | "note";

/** Exact answer/version target for local actions and late-result guards. */
export interface AnswerTarget {
  conversationId: string;
  messageId: string;
  variantId: string | null;
}

export interface AnswerActionState {
  kind: AnswerActionKind;
  target: AnswerTarget;
  status: AnswerActionStatus;
  warning: string | null;
  updatedAt: number;
}

export type RetrievalPreset = "bm25" | "dense" | "hybrid" | "hybrid_rerank";

/** API-005 stage availability; `not_executed` must never look like a run. */
export type RetrievalStageStatus = "executed" | "skipped" | "not_executed";

/** One score family: its scale and what it actually measures. */
export interface RetrievalScoreFamily {
  family: string;
  scale: string;
  definition: string;
}

export type RetrievalScoreKey = "bm25_score" | "dense_score" | "rrf_score" | "cross_encoder_score";

/**
 * The score families that apply to one trace, plus the API's own warning that
 * the families are distinct and that none is a confidence or probability.
 */
export interface RetrievalScoreSemantics {
  applies_to_preset: RetrievalPreset;
  note: string;
  families: Partial<Record<RetrievalScoreKey, RetrievalScoreFamily>>;
}

/**
 * Which production stages inspection does not reproduce, so a trace is never
 * read as production output.
 */
export interface RetrievalProductionParity {
  structured_promotion: RetrievalStageStatus;
  lexical_ladder_merge_into_final: RetrievalStageStatus;
  reason: string;
}

/** The effective inspection scope, with its bounded eligible-document list. */
export interface RetrievalScope {
  documents: number | null;
  eligible_document_ids: string[];
  truncated: boolean;
  reason: string | null;
}

/** The filters the endpoint actually applied to this trace. */
export interface RetrievalFilterValues {
  ticker: string | null;
  section: string | null;
  document_id: string | null;
  filing_date: string | null;
  year: number | null;
}

/** Why a candidate was not selected; null means the trace cannot prove one. */
export type RetrievalDroppedReason =
  | "ranked_below_top_k"
  | "outside_candidate_pool"
  | "not_in_selected_preset_stage";

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
  /** Only reported when this trace can prove why; never invented. */
  dropped_reason?: RetrievalDroppedReason | null;
}

export interface RetrievalTraceStage {
  name: string;
  /** Null for a stage that did not run, so a duration is never implied. */
  elapsed_ms: number | null;
  skipped?: boolean;
  /** API-005 stage availability: executed, skipped, or not_executed. */
  status?: RetrievalStageStatus;
  reason?: string | null;
}

export interface RetrievalTrace {
  /** The trace shape version this consumer relies on. */
  trace_version?: string;
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
  stages: RetrievalTraceStage[];
  candidates: RetrievalCandidate[];
  selected_chunk_ids: string[];
  candidate_count?: number;
  selected_count?: number;
  elapsed_ms: number | null;
  /** The score families that apply to this trace, with the API's own note. */
  score_semantics?: RetrievalScoreSemantics;
  /** Which production stages inspection does not reproduce. */
  production_parity?: RetrievalProductionParity;
  /** The effective scope, including a bounded eligible-document list. */
  scope?: RetrievalScope;
  /** The filters the endpoint applied to this trace. */
  filter_values?: RetrievalFilterValues;
}

/** The request body API-005 accepts for one inspection. */
export interface RetrievalInspectRequest {
  question: string;
  ticker?: string | null;
  section?: string | null;
  document_id?: string | null;
  filing_date?: string | null;
  year?: number | null;
  top_k?: number;
  candidate_pool?: number;
  preset?: RetrievalPreset;
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

export interface AnswerWorkspaceTarget {
  kind: "answer";
  selection: EvidenceSelection;
  source: Source;
}

export interface CatalogWorkspaceTarget {
  kind: "catalog";
  documentId: string;
  title?: string;
  ticker?: string | null;
  filingDate?: string | null;
  reportDate?: string | null;
  accessionNumber?: string | null;
  sourceUrl?: string | null;
  selectedSource?: Source;
  initialTab?: "document" | "excerpt" | "metadata";
  /** "library" is the Collections origin, added by UI-008 alongside the pages
   * that already opened the reader from Documents, Search and Retrieval. */
  returnView: "documents" | "library";
  returnFocusId: string;
}

export interface SearchWorkspaceTarget {
  kind: "search";
  documentId: string;
  selectedSource?: Source;
  initialTab?: "document" | "excerpt" | "metadata";
  returnView: "search";
  returnFocusId: string;
}

export interface RetrievalWorkspaceTarget {
  kind: "retrieval";
  documentId: string;
  title?: string;
  selectedSource?: Source;
  initialTab?: "document" | "excerpt" | "metadata";
  returnView: "retrieval";
  returnFocusId: string;
}

export type DocumentWorkspaceTarget = CatalogWorkspaceTarget | SearchWorkspaceTarget | RetrievalWorkspaceTarget;
export type WorkspaceTarget = AnswerWorkspaceTarget | CatalogWorkspaceTarget | SearchWorkspaceTarget | RetrievalWorkspaceTarget;

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
  /** Echoed by API-003 so the client never guesses the applied order. */
  sort?: DocumentSortField;
  direction?: "asc" | "desc";
}

/** Sort keys the catalog actually supports (API-003). */
export type DocumentSortField = "ticker" | "filing_date" | "chunk_count" | "document_id";

/** One recorded facet value with its truthful document count. */
export interface CatalogFacetValue {
  value: string | number;
  count: number;
}

/**
 * One facet dimension. `availability` distinguishes a recorded dimension from
 * one the stored metadata never carries; an unknown dimension must not be read
 * as a real zero.
 */
export interface CatalogFacet {
  dimension: "company" | "year" | "section";
  availability: "recorded" | "unknown";
  reason: string | null;
  documents_without_value?: number | null;
  values: CatalogFacetValue[];
}

export interface DocumentFacetsResponse {
  generated_at: string;
  /**
   * Every facet counts the applied filters except its own dimension, so a
   * facet reports what selecting one of its values would leave.
   */
  count_basis: "all_filters_except_own_dimension";
  scope: {
    ticker: string | null;
    section: string | null;
    year: number | null;
    filing_date: string | null;
    search: string | null;
    documents: number;
  };
  facets: CatalogFacet[];
}

export interface DocumentStatsResponse {
  generated_at: string;
  documents: number;
  companies: number;
  chunks: number;
  configured_companies: number;
  configured_companies_without_documents: string[];
  configured_companies_with_documents: string[];
  filing_dates: {
    availability: "recorded" | "unknown";
    reason: string | null;
    earliest: number | null;
    latest: number | null;
    documents_without_value: number;
  };
  report_dates: {
    availability: "recorded" | "unknown";
    reason: string | null;
    documents_with_value: number;
  };
  sections: {
    availability: "recorded" | "unknown";
    reason: string | null;
    documents_without_value: number;
    values: CatalogFacetValue[];
  };
  /** No stored artifact records a per-filing form type, so this stays unknown. */
  filing_type: {
    availability: "recorded" | "unknown";
    reason: string | null;
    value: string | null;
  };
}

export interface DocumentChunkListResponse {
  items: DocumentChunk[];
  total: number;
  page: number;
  page_size: number;
}

/** The only discovery mode API-004 defines; there is no semantic mode. */
export type DiscoveryMode = "keyword";

/** API-004 groups a snapshot by filing or by excerpt. */
export type DiscoveryGrouping = "document" | "chunk";

/**
 * A bounded real-text excerpt. `ranges` are half-open Unicode code-point
 * offsets into the original `text`, not UTF-16 or casefolded-text offsets.
 * The client highlights literal text and never renders it as HTML.
 */
export interface DiscoverySnippet {
  text: string;
  ranges: Array<[number, number]>;
  truncated: boolean;
}

/** One ranked excerpt with its canonical chunk and document identity. */
export interface DiscoveryHit {
  chunk_id: string;
  document_id: string;
  ticker: string | null;
  section: string | null;
  filing_date: string | null;
  report_date: string | null;
  chunk_index: number | null;
  /** Raw BM25 lexical score; a ranking signal, never a confidence. */
  score: number;
  snippet: DiscoverySnippet;
}

/** One grouped result (a filing) with its best-matching excerpts. */
export interface DiscoveryGroup {
  document_id: string;
  ticker: string | null;
  filing_date: string | null;
  report_date: string | null;
  sections: string[];
  best_score: number;
  hit_count: number;
  hits: DiscoveryHit[];
}

/** The ranking engine identity and its explicit definition. */
export interface DiscoveryEngine {
  key: string;
  version: string;
  definition: string;
}

/**
 * Truthful count metadata. `count_scope` states that the reported total is
 * bounded by `candidate_ceiling`, so a client must never present it as a
 * whole-corpus total.
 */
export interface DiscoveryScopeMetadata {
  ticker: string | null;
  section: string | null;
  year: number | null;
  filing_date: string | null;
  documents: number;
  count_scope: "bounded_candidates" | "no_matches";
  candidate_ceiling: number;
  limited_by_ceiling: boolean;
  matched_documents: number;
  matched_chunks: number;
}

/** One discovery snapshot page: a stable ranked result set plus its scope. */
export interface DiscoverySnapshotResponse {
  search_id: string;
  query: { text: string; normalized: string; mode: DiscoveryMode };
  grouping: { group_by: DiscoveryGrouping; group_count: number; hit_count: number };
  engine: DiscoveryEngine;
  scope: DiscoveryScopeMetadata;
  items: DiscoveryGroup[] | DiscoveryHit[];
  /** The pageable length of the bounded set, in the snapshot's grouping unit. */
  total: number;
  page: number;
  page_size: number;
  /** API-003 facets for the same scope: they count documents, not matches. */
  facets: CatalogFacet[];
  created_at: string;
  expires_at: string;
  ttl_seconds: number;
}

/** One provider-free discovery request; every filter is a real API-004 axis. */
export interface DiscoverySearchRequest {
  query: string;
  mode?: DiscoveryMode;
  group_by?: DiscoveryGrouping;
  ticker?: string | null;
  section?: string | null;
  year?: number | null;
  filing_date?: string | null;
  page?: number;
  page_size?: number;
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

export type ModelRole = "generator" | "embedding" | "reranker";
export type ConfigurationStatus = "configured" | "not_configured";
export type ModelLoadStatus = "loaded" | "not_loaded" | "unknown";
export type ModelAvailabilityStatus = "available" | "unavailable" | "unknown";

export interface ModelRegistryEntry {
  id: ModelRole;
  role: ModelRole;
  provider: "groq" | "hugging_face";
  configured_model_id: string | null;
  configured_revision: string | null;
  runtime_model_id: string | null;
  runtime_revision: string | null;
  configuration_status: ConfigurationStatus;
  load_status: ModelLoadStatus;
  availability_status: ModelAvailabilityStatus;
  availability_reason: string | null;
  credential_status: "configured" | "not_configured" | "not_required";
  test_capabilities: Array<"runtime_identity">;
}

export interface ModelRegistryResponse {
  items: ModelRegistryEntry[];
  total: number;
}

export interface ModelTestCheck {
  id: "configured_identity" | "runtime_loaded" | "runtime_identity" | "runtime_revision";
  status: "passed" | "failed" | "unavailable";
  reason: string | null;
}

export interface ModelTestResponse {
  model_id: ModelRole;
  test_type: "runtime_identity";
  result: "passed" | "failed" | "unavailable";
  provider_executed: false;
  checks: ModelTestCheck[];
}

export type DatasetKind = "corpus" | "evaluation";
export type DatasetAvailability = "available" | "degraded" | "unavailable";
export type DatasetRegistryId = "serving-corpus" | "evaluation-test-set";
export type DatasetProvenanceStatus = "consistent" | "recorded" | "missing" | "invalid" | "mismatch";

export interface DatasetSummary {
  id: DatasetRegistryId;
  kind: DatasetKind;
  name: string;
  description: string;
  availability: DatasetAvailability;
  reason_code: string | null;
  reason: string | null;
  version: string | null;
  revision: string | null;
  record_count: number | null;
  record_unit: "documents" | "cases";
}

export interface DatasetRegistryResponse {
  items: DatasetSummary[];
  total: number;
}

export interface DatasetCount {
  key: string;
  count: number;
}

export interface FilingYearCoverage {
  availability: "recorded" | "unknown";
  earliest: number | null;
  latest: number | null;
  documents_without_value: number;
  reason: string | null;
}

export interface CorpusDatasetCoverage {
  kind: "corpus";
  documents: number;
  companies: number;
  chunks: number;
  configured_companies: number;
  configured_companies_with_documents: string[];
  configured_companies_without_documents: string[];
  filing_years: FilingYearCoverage;
  sections: DatasetCount[];
}

export interface EvaluationDatasetCoverage {
  kind: "evaluation";
  cases: number;
  categories: DatasetCount[];
  priorities: DatasetCount[];
  tickers: string[];
  sections: string[];
}

export type DatasetCoverage = CorpusDatasetCoverage | EvaluationDatasetCoverage;

export interface DatasetProvenance {
  authority: "qdrant_index_manifest" | "built_in_evaluation_test_set";
  status: DatasetProvenanceStatus;
  reason_code: string | null;
  reason: string | null;
  schema_version: number | null;
  revision: string | null;
  build_version: string | null;
  collection_name: string | null;
  point_count: number | null;
  embedding_model_id: string | null;
  embedding_model_revision: string | null;
  vector_dimension: number | null;
  distance_metric: string | null;
  snapshot_id: string | null;
  embedding_generation_id: string | null;
  embedding_generation_fingerprint: string | null;
}

export interface DatasetDetail extends DatasetSummary {
  coverage: DatasetCoverage | null;
  provenance: DatasetProvenance;
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

export type ReaderCoverageStatus = "complete" | "partial" | "unknown";

export type ReaderRepresentationStatus =
  | "available"
  | "partial"
  | "unavailable"
  | "supported"
  | "generating"
  | "failed"
  | "stale"
  | "unsupported";

export type PdfArtifactStatus = Exclude<ReaderRepresentationStatus, "partial">;
export type PdfMappingStatus = "exact" | "ambiguous" | "unavailable" | "stale";
export type PdfPageSemantics = "official_pdf_pages" | "generated_representation_pages";

export interface ReaderAvailability {
  kind: "normalized_text" | "structured" | "pdf";
  status: ReaderRepresentationStatus;
  reason_code:
    | "available"
    | "identity_unverified"
    | "source_unavailable"
    | "structured_representation_unavailable"
    | "pdf_representation_unavailable"
    | "pdf_available"
    | "pdf_supported"
    | "pdf_generating"
    | "pdf_generation_failed"
    | "pdf_stale";
  reason: string | null;
  coverage_status?: ReaderCoverageStatus;
  coverage_reason?: string | null;
  coverage_reason_code?: string | null;
  representation_id?: string | null;
  representation_type?: "OFFICIAL_PDF" | "DERIVED_PDF" | null;
  page_semantics?: PdfPageSemantics | null;
  artifact_key?: string | null;
  artifact_hash?: string | null;
  source_content_hash?: string | null;
  page_count?: number | null;
  mapping_status?: PdfMappingStatus | null;
}

export interface PdfRendererProfile {
  renderer: string;
  renderer_version: string;
  template_version: string;
  page_size: string;
  orientation: "portrait" | "landscape" | string;
  margins_pt: Record<string, number>;
  print_background: boolean;
  locale: string;
  font_family: string;
}

export interface PdfRepresentationManifest {
  schema_version: "sec-pdf-manifest-v2";
  representation_id: string;
  representation_type: "OFFICIAL_PDF" | "DERIVED_PDF";
  page_semantics: PdfPageSemantics;
  artifact_status: PdfArtifactStatus;
  document_id: string;
  source_document_id: string | null;
  source_set_revision: string | null;
  document_revision: string | null;
  source_content_hash: string | null;
  artifact_key: string | null;
  artifact_hash: string | null;
  artifact_size_bytes: number | null;
  page_count: number | null;
  renderer: PdfRendererProfile;
  generated_at: string | null;
  mapping_manifest_id: string | null;
  mapping_status: PdfMappingStatus;
  mapping_entry_count: number;
  reason: string | null;
}

export interface PdfMappingRect {
  page: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PdfMappingEntry {
  block_id: string;
  block_index: number;
  block_kind: "heading" | "paragraph" | "table";
  char_start: number;
  char_end: number;
  text_preview: string;
  status: PdfMappingStatus;
  reason: string | null;
  rects: PdfMappingRect[];
}

export interface PdfMappingManifest {
  schema_version: "sec-pdf-mapping-v2";
  mapping_manifest_id: string | null;
  representation_id: string;
  document_id: string;
  source_document_id: string;
  source_content_hash: string;
  artifact_key: string;
  artifact_hash: string;
  source_set_revision: string;
  document_revision: string;
  entries: PdfMappingEntry[];
}

export interface PdfEvidenceLocation {
  schema_version: "sec-pdf-evidence-location-v1";
  document_id: string;
  source_document_id: string;
  source_set_revision: string;
  document_revision: string;
  source_content_hash: string;
  representation_id: string;
  artifact_key: string;
  artifact_hash: string;
  mapping_manifest_id: string | null;
  chunk_id: string;
  chunk_text_hash: string;
  status: PdfMappingStatus;
  reason: string | null;
  match_count: number;
  match_count_capped: boolean;
  entry_ids: string[];
  rects: PdfMappingRect[];
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
  cell_id?: string | null;
  source_row?: number | null;
  source_column?: number | null;
}

export type StructuredTableMode = "semantic" | "source_layout" | "unsupported";

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
  table_mode?: StructuredTableMode | null;
  table_adapter_version?: string | null;
  table_reason?: string | null;
  header_rows?: StructuredCell[][];
  header_row_count?: number;
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
  coverage_status?: ReaderCoverageStatus;
  coverage_reason?: string | null;
  coverage_reason_code?: string | null;
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
  coverage_status?: ReaderCoverageStatus;
  coverage_reason?: string | null;
  coverage_reason_code?: string | null;
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
  coverage_status?: ReaderCoverageStatus;
  coverage_reason?: string | null;
  coverage_reason_code?: string | null;
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
/**
 * Presentation mode a conversation was started in. "chat" is the direct
 * question/answer flow; "research" adds the organized research composition
 * (follow-up tiles, insights). The mode never changes retrieval semantics.
 */
export type ConversationMode = "chat" | "research";

export interface RequestSnapshot {
  ticker: string | null;
  section: string | null;
  topK: number;
  enableComparative: boolean;
  answerLanguage: AnswerLanguage;
  /** Presentation mode captured from the route family at send time. */
  mode?: ConversationMode;
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
  /** Optional answer-version binding; absent/null means the original answer. */
  variantId?: string | null;
  /** Required for the `other` category; kept as bounded local text. */
  otherText?: string;
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

/**
 * DATA-003 typed collections.
 *
 * Everything here mirrors the protected local-workspace routes exactly:
 * responses are the repository payloads, so the frontend never invents a
 * collection field, a member kind, or a revision of its own.
 */
export type CollectionItemKind = "document" | "evidence" | "answer" | "note";
export type CollectionSortField = "name" | "updated_at" | "created_at" | "item_count";
export type CollectionSortDirection = "asc" | "desc";
export type CollectionExportFormat = "json" | "markdown";

export type CollectionActivityEvent =
  | "collection_created"
  | "collection_updated"
  | "collection_deleted"
  | "item_added"
  | "item_removed"
  | "note_added"
  | "note_updated"
  | "note_removed";

export interface CollectionRecord {
  collection_id: string;
  name: string;
  description: string;
  tags: string[];
  favorite: boolean;
  private: boolean;
  revision: number;
  created_at: string;
  updated_at: string;
  item_count: number;
}

export interface CollectionListResponse {
  items: CollectionRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface CollectionItemRecord {
  item_id: string;
  collection_id: string;
  item_kind: CollectionItemKind;
  citation: string;
  excerpt: string;
  reference: Record<string, unknown>;
  revision: number;
  created_at: string;
  updated_at: string;
  snapshot?: Record<string, unknown>;
}

export interface CollectionItemListResponse {
  items: CollectionItemRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface CollectionNoteRecord {
  note_id: string;
  collection_id: string;
  text: string;
  revision: number;
  created_at: string;
  updated_at: string;
  evidence_ref?: Record<string, unknown>;
}

export interface CollectionNoteListResponse {
  items: CollectionNoteRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface CollectionActivityRecord {
  activity_id: string;
  collection_id: string;
  entity_type: string;
  entity_id: string;
  event_type: CollectionActivityEvent;
  occurred_at: string;
}

export interface CollectionActivityListResponse {
  items: CollectionActivityRecord[];
  total: number;
  page: number;
  page_size: number;
}

/** The receipt a delete returns; it names the tombstoned entity and revision. */
export interface CollectionReceipt {
  operation: string;
  entity_type: string;
  entity_id: string;
  revision: number;
  deleted_at: string | null;
}

export interface CollectionCreateRequest {
  name: string;
  description?: string;
  tags?: string[];
  favorite?: boolean;
  private?: boolean;
}

/** Every mutable collection field, with the revision the caller last read. */
export interface CollectionUpdateRequest {
  revision: number;
  name?: string;
  description?: string;
  tags?: string[];
  favorite?: boolean;
  private?: boolean;
}

export interface CollectionItemRequest {
  item_kind: CollectionItemKind;
  citation?: string;
  excerpt?: string;
  reference?: Record<string, unknown>;
  snapshot?: Record<string, unknown>;
}

export interface CollectionNoteRequest {
  text: string;
  evidence_ref?: Record<string, unknown>;
}

export interface CollectionNoteUpdateRequest {
  revision: number;
  text: string;
}

/** `GET /collections/{id}/export?format=json` — the collection as a document. */
export interface CollectionExportDocument {
  id: string;
  name: string;
  description: string;
  tags: string[];
  favorite: boolean;
  private: boolean;
  revision: number;
  created_at: string;
  updated_at: string;
  items: Array<{
    id: string;
    kind: CollectionItemKind;
    citation: string;
    excerpt: string;
    reference: Record<string, unknown>;
    snapshot?: Record<string, unknown>;
    created_at: string;
  }>;
  notes: Array<{
    id: string;
    text: string;
    evidence_ref?: Record<string, unknown>;
    revision: number;
    created_at: string;
    updated_at: string;
  }>;
}

export interface CollectionExportMarkdown {
  format: "markdown";
  content: string;
}

export type PipelineRunState =
  | "queued"
  | "running"
  | "cancelling"
  | "cancelled"
  | "succeeded"
  | "failed"
  | "interrupted";

export type PipelineStepState =
  | "pending"
  | "running"
  | "cancelled"
  | "succeeded"
  | "failed"
  | "skipped"
  | "interrupted";

export type PipelineStageId =
  | "download_filings"
  | "chunk_filings"
  | "add_table_chunks"
  | "embed_chunks"
  | "index_chunks";

export interface PipelineStageDefinition {
  stage_id: PipelineStageId;
  order: number;
  description: string;
}

export interface PipelineDefinition {
  pipeline_id: "sec_10k_ingestion";
  name: string;
  input_kind: "ticker";
  registered_input_ids: string[];
  staging_profiles: Array<"isolated">;
  stages: PipelineStageDefinition[];
  capabilities: {
    can_stage: true;
    can_cancel: true;
    event_transport: "sse";
    executes_during_staging: false;
    automatically_promotes_to_serving: false;
  };
}

export interface PipelineProgress {
  stage: PipelineStageId | null;
  current: number | null;
  total: number | null;
}

export interface PipelineStep {
  step_id: string;
  stage_id: PipelineStageId;
  state: PipelineStepState;
  revision: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface PipelineRun {
  id: string;
  pipeline_id: "sec_10k_ingestion";
  state: PipelineRunState;
  revision: number;
  configuration_fingerprint: string;
  input_ids: string[];
  staging_profile: "isolated";
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  cancellation_requested_at: string | null;
  progress: PipelineProgress;
  steps: PipelineStep[];
  artifact_references: string[];
  failure: { code: string; message: string } | null;
}

export interface PipelineRunPage {
  items: PipelineRun[];
  total: number;
  page: number;
  page_size: number;
}

export interface PipelineRunEvent {
  run_id: string;
  event_id: string;
  sequence: number;
  event_type:
    | "created"
    | "state_changed"
    | "progress"
    | "step_changed"
    | "cancellation_requested"
    | "cancelled"
    | "interrupted";
  state: PipelineRunState | null;
  reason_code: string | null;
  progress: PipelineProgress;
  occurred_at: string;
}

export interface LocalWorkspaceConfigurationStatus {
  deployment_mode: string;
  agent_decision_provider?: { available: boolean };
  capabilities: {
    public_provider_free: boolean;
    local_workspace: boolean;
    execution_jobs: boolean;
  };
}
