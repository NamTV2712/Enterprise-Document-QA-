import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, CheckCircle2, Clock3, Download, GitCompare, Layers, ShieldAlert, ShieldCheck } from "lucide-react";

import { getDocumentFacets, getDocuments, inspectRetrieval } from "../../lib/api";
import { useLocale } from "../../lib/i18n";
import { describeRequestError } from "../../lib/requestError";
import { formatCompanyLabel } from "../../lib/displayMetadata";
import { getSectionDisplay } from "../../lib/sourcePresentation";
import {
  candidateSectionCount,
  formatCount,
  formatDuration,
  latencyBreakdown,
  orderOptions,
  pageRange,
  primaryScoreKey,
  SCORE_LABELS,
  rerankerModel,
  rerankerStage,
  sortCandidates,
  stageStatus,
  stageStatusLabel,
  traceConfigurationKey,
  traceConfigurationSummary,
} from "../../lib/traceModel";
import type {
  RetrievalCandidate,
  RetrievalPreset,
  RetrievalTrace,
  RetrievalWorkspaceTarget,
  Source,
} from "../../types";
import { CandidateTable } from "./CandidateTable";
import { EvidencePreviewRail } from "./EvidencePreviewRail";
import { RetrievalQueryCard, type RetrievalFilterDraft } from "./RetrievalQueryCard";
import { StageSummary } from "./StageSummary";
import { TraceDisclosures } from "./TraceDisclosures";

interface RetrievalPanelProps {
  tickers: string[];
  sections: string[];
  isBackendConnected: boolean | null;
  onUseQuestion: (question: string, scope?: { ticker: string | null; section: string | null }) => void;
  onOpenDocument?: (target: RetrievalWorkspaceTarget) => void;
  onOpenSource?: (source: Source) => void;
  onSaveEvidence?: (source: Source) => void;
}

const EMPTY_FILTERS: RetrievalFilterDraft = { ticker: "", year: "", documentId: "", section: "" };
const PAGE_SIZES = [10, 20, 50];
const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_QUESTION = "What was Apple's total revenue in 2024?";

interface SubmittedInspection {
  question: string;
  filters: RetrievalFilterDraft;
  topK: number;
  candidatePool: number;
  preset: RetrievalPreset;
  configurationKey: string;
}

export function retrievalFocusId(chunkId: string): string {
  return `retrieval-document-workspace-${chunkId.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

/**
 * Retrieval inspection.
 *
 * One submitted configuration produces exactly one POST /retrieval/inspect and
 * one trace. Picking a candidate, changing the row order, paging, and opening
 * details are all views over that trace and issue no further request; a late
 * response can never replace a newer trace. Every displayed value is one the
 * trace reported.
 */
export function RetrievalPanel({
  tickers = [],
  sections = [],
  isBackendConnected,
  onUseQuestion,
  onOpenDocument,
  onOpenSource,
  onSaveEvidence,
}: RetrievalPanelProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";

  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [filters, setFilters] = useState<RetrievalFilterDraft>(EMPTY_FILTERS);
  const [preset, setPreset] = useState<RetrievalPreset>("hybrid_rerank");
  const [topK, setTopK] = useState(5);
  const [candidatePool, setCandidatePool] = useState(10);
  const [categories, setCategories] = useState<{ years: Array<{ value: string; label: string }>; documents: Array<{ value: string; label: string }>; documentNote: string | null }>({
    years: [],
    documents: [],
    documentNote: null,
  });

  const [trace, setTrace] = useState<RetrievalTrace | null>(null);
  const [interpretation, setInterpretation] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<SubmittedInspection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [order, setOrder] = useState<"trace_order" | ReturnType<typeof primaryScoreKey>>("trace_order");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);

  const requestId = useRef(0);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => {
    requestId.current += 1;
    controller.current?.abort();
  }, []);

  // Catalog truth for the filter choices; the API decides what exists.
  useEffect(() => {
    const abort = new AbortController();
    void getDocumentFacets(
      {
        ticker: filters.ticker || null,
        section: filters.section || null,
        year: filters.year ? Number(filters.year) : null,
      },
      abort.signal,
    )
      .then((response) => {
        const years = response.facets.find((facet) => facet.dimension === "year")?.values ?? [];
        setCategories((current) => ({
          ...current,
          years: [
            { value: "", label: vi ? "Tất cả các năm" : "All years" },
            ...years.map((value) => ({ value: String(value.value), label: `${value.value} (${value.count})` })),
          ],
        }));
      })
      .catch(() => {
        if (abort.signal.aborted) return;
        setCategories((current) => ({ ...current, years: [] }));
      });
    return () => abort.abort();
  }, [filters.ticker, filters.section, filters.year, vi]);

  useEffect(() => {
    const abort = new AbortController();
    void getDocuments(
      {
        ticker: filters.ticker || null,
        section: filters.section || null,
        year: filters.year ? Number(filters.year) : null,
        sort: "filing_date",
        direction: "desc",
        page: 1,
        page_size: 50,
      },
      abort.signal,
    )
      .then((response) => {
        setCategories((current) => ({
          ...current,
          documents: [
            { value: "", label: vi ? "Tất cả tài liệu" : "All documents" },
            ...response.items.map((row) => ({
              value: row.document_id,
              label: `${row.ticker ? formatCompanyLabel(row.ticker) : row.document_id}${row.filing_date ? ` · ${row.filing_date}` : ""}`,
            })),
          ],
          documentNote: response.total > response.items.length
            ? (vi
                ? `Danh sách tài liệu được giới hạn ở ${response.items.length} trong ${response.total} tài liệu khớp phạm vi.`
                : `The document list is bounded to ${response.items.length} of ${response.total} documents in scope.`)
            : null,
        }));
      })
      .catch(() => {
        if (abort.signal.aborted) return;
        setCategories((current) => ({ ...current, documents: [], documentNote: null }));
      });
    return () => abort.abort();
  }, [filters.ticker, filters.section, filters.year, vi]);

  const configurationKey = traceConfigurationKey({
    question,
    ticker: filters.ticker || null,
    section: filters.section || null,
    documentId: filters.documentId || null,
    filingDate: null,
    year: filters.year ? Number(filters.year) : null,
    topK,
    candidatePool,
    preset,
  });
  const draftDiffers = Boolean(submitted) && submitted?.configurationKey !== configurationKey;

  const runInspection = useCallback(async () => {
    const trimmed = question.trim();
    if (trimmed.length < 5 || isBackendConnected === false) return;
    const requestConfiguration = traceConfigurationKey({
      question: trimmed,
      ticker: filters.ticker || null,
      section: filters.section || null,
      documentId: filters.documentId || null,
      filingDate: null,
      year: filters.year ? Number(filters.year) : null,
      topK,
      candidatePool,
      preset,
    });
    const currentRequestId = ++requestId.current;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setIsSubmitting(true);
    setError(null);
    setTrace(null);
    setInterpretation(null);
    setSelectedChunkId(null);
    setPage(1);
    setSubmitted({
      question: trimmed,
      filters,
      topK,
      candidatePool,
      preset,
      configurationKey: requestConfiguration,
    });
    try {
      const response = await inspectRetrieval(
        {
          question: trimmed,
          ticker: filters.ticker || null,
          section: filters.section || null,
          document_id: filters.documentId || null,
          year: filters.year ? Number(filters.year) : null,
          top_k: topK,
          candidate_pool: candidatePool,
          preset,
        },
        abort.signal,
      );
      if (currentRequestId !== requestId.current) return;
      setTrace(response.trace);
      setInterpretation(response.query_interpretation.retrieval_question);
      setOrder("trace_order");
    } catch (reason) {
      if (currentRequestId !== requestId.current) return;
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(describeRequestError(reason, vi ? "Không thể kiểm tra retrieval." : "Retrieval inspection failed.", vi ? "vi" : "en").message);
    } finally {
      if (currentRequestId === requestId.current) setIsSubmitting(false);
    }
  }, [candidatePool, filters, isBackendConnected, preset, question, topK, vi]);

  const candidates = trace?.candidates ?? [];
  const orderScoreKey = order === "trace_order" ? primaryScoreKey(trace?.preset ?? preset) : order;
  const orderedCandidates = useMemo(() => sortCandidates(candidates, order), [candidates, order]);
  const range = pageRange(orderedCandidates.length, page, pageSize);
  const pageCandidates = useMemo(
    () => orderedCandidates.slice((Math.min(page, range.pageCount) - 1) * pageSize, (Math.min(page, range.pageCount) - 1) * pageSize + pageSize),
    [orderedCandidates, page, pageSize, range.pageCount],
  );
  const orderOptionsList = useMemo(() => orderOptions(trace ?? { preset } as RetrievalTrace, candidates, vi), [candidates, preset, trace, vi]);
  const selectedCandidate = useMemo(
    // The rail previews the top-ranked candidate until a reader picks another
    // row, matching the reference composition without inventing a selection.
    () => candidates.find((candidate) => candidate.chunk_id === selectedChunkId) ?? orderedCandidates[0] ?? null,
    [candidates, orderedCandidates, selectedChunkId],
  );
  const rerankStage = trace ? rerankerStage(trace) : null;
  const rerankStatus = rerankStage ? stageStatus(rerankStage) : null;
  const rerankModel = trace ? rerankerModel(trace) : null;

  const tickerOptions = useMemo(
    () => [
      { value: "", label: vi ? "Tất cả công ty" : "All companies" },
      ...tickers.map((ticker) => ({ value: ticker, label: formatCompanyLabel(ticker) })),
    ],
    [tickers, vi],
  );
  const sectionOptions = useMemo(
    () => [
      { value: "", label: vi ? "Tất cả mục" : "All sections" },
      ...sections.map((section) => ({ value: section, label: getSectionDisplay("", section).section })),
    ],
    [sections, vi],
  );
  const documentOptions = useMemo(
    () => (categories.documents.length > 0 ? categories.documents : [{ value: "", label: vi ? "Tất cả tài liệu" : "All documents" }]),
    [categories.documents, vi],
  );

  const openDocument = useCallback((candidate: RetrievalCandidate) => {
    if (!candidate.document_id || !onOpenDocument) {
      onOpenSource?.({
        citation: candidate.citation,
        text_preview: candidate.text_preview,
        chunk_id: candidate.chunk_id,
        document_id: candidate.document_id,
        ticker: candidate.ticker,
        section: candidate.section,
        filing_date: candidate.filing_date,
      });
      return;
    }
    onOpenDocument({
      kind: "retrieval",
      documentId: candidate.document_id,
      title: `${candidate.ticker ? formatCompanyLabel(candidate.ticker) : "SEC filing"} · ${candidate.filing_date ?? "date unavailable"}`,
      selectedSource: {
        citation: candidate.citation,
        text_preview: candidate.text_preview,
        chunk_id: candidate.chunk_id,
        document_id: candidate.document_id,
        ticker: candidate.ticker,
        section: candidate.section,
        filing_date: candidate.filing_date,
      },
      returnView: "retrieval",
      returnFocusId: retrievalFocusId(candidate.chunk_id),
    });
  }, [onOpenDocument, onOpenSource]);

  // Export is the app's existing capability for a completed trace: the file
  // carries exactly the values the trace reported, nothing derived.
  const downloadTrace = useCallback((format: "json" | "csv") => {
    if (!trace) return;
    const escapeCsv = (value: string | number | boolean | null | undefined) => {
      const text = value === null || value === undefined ? "" : String(value);
      return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
    };
    const content = format === "json"
      ? JSON.stringify(trace, null, 2)
      : [
        "query,chunk_id,document_id,ticker,section,filing_date,final_rank,fusion_rank,bm25_rank,dense_rank,lexical_rank,bm25_score,dense_score,rrf_score,cross_encoder_score,selected,dropped_reason",
        ...trace.candidates.map((candidate) => [
          trace.query,
          candidate.chunk_id,
          candidate.document_id ?? "",
          candidate.ticker ?? "",
          candidate.section ?? "",
          candidate.filing_date ?? "",
          candidate.final_rank ?? "",
          candidate.fusion_rank ?? "",
          candidate.bm25_rank ?? "",
          candidate.dense_rank ?? "",
          candidate.lexical_rank ?? "",
          candidate.bm25_score ?? "",
          candidate.dense_score ?? "",
          candidate.rrf_score ?? "",
          candidate.cross_encoder_score ?? "",
          candidate.selected,
          candidate.dropped_reason ?? "",
        ].map(escapeCsv).join(",")),
      ].join("\n");
    const url = URL.createObjectURL(new Blob([content], { type: format === "json" ? "application/json" : "text/csv" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `retrieval-trace.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [trace]);

  return (
    <section className="workspace-page workspace-page--wide retrieval-page console-view-enter" aria-labelledby="retrieval-lab-title">
      <div className="console-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><Activity aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="retrieval-lab-title" className="console-page-header__title">{vi ? "Retrieval" : "Retrieval"}</h1>
            <p className="console-page-header__subtitle">
              {vi
                ? "Kiểm tra từng stage xếp hạng trên pool ứng viên thật. Không gọi mô hình ngôn ngữ."
                : "Inspect each ranking stage over a real candidate pool. No language model is called."}
            </p>
          </div>
        </div>
        <div className="console-page-header__actions">
          <span className="console-chip">
            {isBackendConnected === false
              ? <ShieldAlert className="h-3.5 w-3.5" style={{ color: "var(--danger)" }} aria-hidden="true" />
              : <ShieldCheck className="h-3.5 w-3.5" style={{ color: "var(--success)" }} aria-hidden="true" />}
            {isBackendConnected === false ? (vi ? "Backend offline" : "Backend offline") : (vi ? "Provider-free" : "Provider-free")}
          </span>
        </div>
      </div>

      <div className="retrieval-layout">
        <div className="retrieval-layout__main">
          <RetrievalQueryCard
            vi={vi}
            label={vi ? "Câu hỏi retrieval" : "Retrieval Query"}
            question={question}
            onQuestionChange={setQuestion}
            questionPlaceholder={vi ? "Ví dụ: Doanh thu của Apple năm 2024 là bao nhiêu?" : "For example: What was Apple's total revenue in 2024?"}
            filters={filters}
            onFilterChange={setFilters}
            tickerOptions={tickerOptions}
            yearOptions={categories.years}
            documentOptions={documentOptions}
            documentNote={categories.documentNote}
            sectionOptions={sectionOptions}
            preset={preset}
            onPresetChange={setPreset}
            topK={topK}
            onTopKChange={setTopK}
            candidatePool={candidatePool}
            onCandidatePoolChange={setCandidatePool}
            isSubmitting={isSubmitting}
            disabled={isBackendConnected === false}
            draftDiffers={draftDiffers}
            onSubmit={() => void runInspection()}
            submitLabel={vi ? "Chạy retrieval" : "Run Retrieval"}
            submitAriaLabel={vi ? "Chạy retrieval" : "Run retrieval"}
            onUseInResearch={() => onUseQuestion(question, { ticker: filters.ticker || null, section: filters.section || null })}
          />

          {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}
          {isSubmitting && (
            <div className="workspace-alert" role="status" aria-live="polite">
              {vi ? "Đang chạy inspection cho cấu hình đã gửi." : "Running inspection for the submitted configuration."}
            </div>
          )}
          {interpretation && (
            <div className="workspace-alert" role="status">
              <span className="font-semibold">{vi ? "Câu dùng để retrieval:" : "Retrieval query:"}</span>{" "}
              <code className="font-mono">{interpretation}</code>
            </div>
          )}

          {trace && (
            <div className="retrieval-submitted" data-testid="submitted-retrieval-configuration">
              <span className="retrieval-submitted__text">
                <span className="font-semibold">{vi ? "Cấu hình đã gửi:" : "Submitted configuration:"}</span>{" "}
                <code className="font-mono">{trace.query}</code>{" · "}
                <span>{traceConfigurationSummary(trace, vi)}</span>
              </span>
              <span className="retrieval-submitted__actions">
                <button type="button" className="console-btn" onClick={() => downloadTrace("json")}>
                  <Download aria-hidden="true" />
                  JSON
                </button>
                <button type="button" className="console-btn" onClick={() => downloadTrace("csv")}>
                  <Download aria-hidden="true" />
                  CSV
                </button>
              </span>
            </div>
          )}

          {trace && (
            <>
              <div className="console-stats" data-testid="retrieval-analyst-summary">
                <div className="console-stat">
                  <div className="console-stat__icon"><Layers aria-hidden="true" /></div>
                  <div className="min-w-0">
                    <div className="console-stat__value">{formatCount(trace.candidate_count ?? trace.candidates.length, vi)}</div>
                    <div className="console-stat__label">{vi ? "Ứng viên đã lấy" : "Candidates Retrieved"}</div>
                    <div className="console-stat__hint">
                      {vi
                        ? `Từ ${candidateSectionCount(trace.candidates)} mục tài liệu`
                        : `From ${candidateSectionCount(trace.candidates)} document sections`}
                    </div>
                  </div>
                </div>
                <div className="console-stat">
                  <div className="console-stat__icon console-stat__icon--success"><CheckCircle2 aria-hidden="true" /></div>
                  <div className="min-w-0">
                    <div className="console-stat__value">{formatCount(trace.selected_count ?? trace.selected_chunk_ids.length, vi)}</div>
                    <div className="console-stat__label">{vi ? "Kết quả đã chọn" : "Selected Results"}</div>
                    <div className="console-stat__hint">{vi ? `top K ${trace.top_k} của preset` : `top K ${trace.top_k} of the preset`}</div>
                  </div>
                </div>
                <div className="console-stat">
                  <div className="console-stat__icon"><Clock3 aria-hidden="true" /></div>
                  <div className="min-w-0">
                    <div className="console-stat__value">{formatDuration(trace.elapsed_ms, vi)}</div>
                    <div className="console-stat__label">{vi ? "Thời lượng inspection" : "Inspection Latency"}</div>
                    <div className="console-stat__hint">{latencyBreakdown(trace, vi) ?? (vi ? "Trace không báo cáo thời lượng stage." : "The trace reported no stage durations.")}</div>
                  </div>
                </div>
                <div className="console-stat">
                  <div className="console-stat__icon console-stat__icon--warning"><GitCompare aria-hidden="true" /></div>
                  <div className="min-w-0">
                    <div className="console-stat__value">{rerankStatus ? stageStatusLabel(rerankStatus, vi) : (vi ? "Không có stage" : "No stage")}</div>
                    <div className="console-stat__label">{vi ? "Reranker" : "Reranker"}</div>
                    <div className="console-stat__hint">
                      {rerankModel
                        ? rerankModel
                        : rerankStage?.reason ?? (vi ? "Trace không báo cáo stage rerank." : "The trace reported no reranker stage.")}
                    </div>
                  </div>
                </div>
              </div>

              <CandidateTable
                candidates={pageCandidates}
                totalCandidates={orderedCandidates.length}
                page={Math.min(page, range.pageCount)}
                pageSize={pageSize}
                order={order}
                orderOptionsList={orderOptionsList}
                onOrderChange={(value) => { setOrder(value); setPage(1); }}
                onPageSizeChange={(value) => { setPageSize(PAGE_SIZES.includes(value) ? value : DEFAULT_PAGE_SIZE); setPage(1); }}
                onPageChange={setPage}
                orderScoreKey={orderScoreKey}
                orderScoreLabel={SCORE_LABELS[orderScoreKey]}
                orderScoreNote={trace.score_semantics?.note ?? null}
                selectedChunkId={selectedChunkId}
                onSelect={(candidate) => setSelectedChunkId(candidate.chunk_id)}
                onOpenDocument={onOpenDocument ? openDocument : undefined}
                onOpenSource={onOpenSource ? (candidate) => onOpenSource({
                  citation: candidate.citation,
                  text_preview: candidate.text_preview,
                  chunk_id: candidate.chunk_id,
                  document_id: candidate.document_id,
                  ticker: candidate.ticker,
                  section: candidate.section,
                  filing_date: candidate.filing_date,
                }) : undefined}
                onSaveEvidence={onSaveEvidence}
                vi={vi}
                isBusy={isSubmitting}
                focusIdFor={(candidate) => retrievalFocusId(candidate.chunk_id)}
              />

              <div className="console-card">
                <div className="console-card__header">
                  <div className="min-w-0">
                    <h2 className="console-card__title">{vi ? "Stage đã chạy" : "Stages in this trace"}</h2>
                    <p className="console-card__subtitle">
                      {vi ? "Trạng thái và thời lượng do endpoint báo cáo" : "Status and duration as reported by the endpoint"}
                    </p>
                  </div>
                </div>
                <div className="console-card__body">
                  <StageSummary vi={vi} stages={trace.stages} />
                </div>
              </div>

              <TraceDisclosures vi={vi} trace={trace} candidates={candidates} />
            </>
          )}

          {!trace && !isSubmitting && !error && (
            <div className="console-card">
              <div className="console-empty">
                <Activity aria-hidden="true" />
                <strong>{vi ? "Chạy một câu hỏi để bắt đầu" : "Run a question to start"}</strong>
                <p>
                  {vi
                    ? "Inspection trả về pool ứng viên thật cùng hạng và điểm từng stage — không tốn quota LLM."
                    : "Inspection returns the real candidate pool with its ranks and per-stage scores — no LLM quota."}
                </p>
              </div>
            </div>
          )}
        </div>

        <EvidencePreviewRail
          vi={vi}
          trace={trace ?? ({ preset } as RetrievalTrace)}
          candidate={selectedCandidate}
          isPinned={selectedChunkId !== null}
          onClearSelection={() => setSelectedChunkId(null)}
          onOpenDocument={openDocument}
          onOpenSource={onOpenSource ? (candidate) => onOpenSource({
            citation: candidate.citation,
            text_preview: candidate.text_preview,
            chunk_id: candidate.chunk_id,
            document_id: candidate.document_id,
            ticker: candidate.ticker,
            section: candidate.section,
            filing_date: candidate.filing_date,
          }) : undefined}
          onSaveEvidence={onSaveEvidence}
        />
      </div>
    </section>
  );
}
