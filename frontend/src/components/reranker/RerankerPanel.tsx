import { useCallback, useMemo, useRef, useState } from "react";
import { ArrowDown, ArrowUp, GitCompare, Minus } from "lucide-react";

import { inspectRetrieval } from "../../lib/api";
import { useLocale } from "../../lib/i18n";
import { describeRequestError } from "../../lib/requestError";
import { formatCompanyLabel } from "../../lib/displayMetadata";
import { getSectionDisplay } from "../../lib/sourcePresentation";
import {
  candidateStatus,
  formatCount,
  formatDuration,
  formatScoreForFamily,
  poolHasRerankerScores,
  rankMovement,
  rerankerModel,
  rerankerStage,
  sortCandidates,
  stageStatus,
  stageStatusLabel,
  traceConfigurationKey,
  traceConfigurationSummary,
} from "../../lib/traceModel";
import type { RetrievalCandidate, RetrievalPreset, RetrievalTrace, RetrievalWorkspaceTarget, Source } from "../../types";
import { EvidencePreviewRail } from "../retrieval/EvidencePreviewRail";
import { RetrievalQueryCard, type RetrievalFilterDraft } from "../retrieval/RetrievalQueryCard";
import { TraceDisclosures } from "../retrieval/TraceDisclosures";
import { retrievalFocusId } from "../retrieval/RetrievalPanel";

interface RerankerPanelProps {
  tickers: string[];
  sections: string[];
  isBackendConnected: boolean | null;
  onUseQuestion: (question: string, scope?: { ticker: string | null; section: string | null }) => void;
  onOpenDocument?: (target: RetrievalWorkspaceTarget) => void;
  onOpenSource?: (source: Source) => void;
  onSaveEvidence?: (source: Source) => void;
}

const EMPTY_FILTERS: RetrievalFilterDraft = { ticker: "", year: "", documentId: "", section: "" };

function MovementCell({ candidate, vi }: { candidate: RetrievalCandidate; vi: boolean }) {
  const movement = rankMovement(candidate, vi);
  if (movement.delta === null) {
    return <span className="reranker-movement reranker-movement--none">
      <Minus aria-hidden="true" />
      {vi ? "Chưa có dữ liệu" : "Not reported"}
    </span>;
  }
  if (movement.delta === 0) {
    return <span className="reranker-movement reranker-movement--none">
      <Minus aria-hidden="true" />
      {vi ? "Không đổi" : "No change"}
    </span>;
  }
  const up = movement.delta > 0;
  return (
    <span className={`reranker-movement ${up ? "reranker-movement--up" : "reranker-movement--down"}`}>
      {up ? <ArrowUp aria-hidden="true" /> : <ArrowDown aria-hidden="true" />}
      {movement.label}
    </span>
  );
}

/**
 * Reranker inspection.
 *
 * One trace answers both questions: the fused order (`rrf_score`, `fusion_rank`)
 * and the cross-encoder order (`cross_encoder_score`, `final_rank`) come from
 * the same ranked pool in a single response, so the comparison never reranks a
 * second time and never compares two pools. When the reranker stage did not run,
 * the page says exactly that instead of plotting an absent score.
 */
export function RerankerPanel({
  tickers = [],
  sections = [],
  isBackendConnected,
  onUseQuestion,
  onOpenDocument,
  onOpenSource,
  onSaveEvidence,
}: RerankerPanelProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";

  const [question, setQuestion] = useState("");
  const [filters, setFilters] = useState<RetrievalFilterDraft>(EMPTY_FILTERS);
  const [preset, setPreset] = useState<RetrievalPreset>("hybrid_rerank");
  const [topK, setTopK] = useState(5);
  const [candidatePool, setCandidatePool] = useState(10);
  const [trace, setTrace] = useState<RetrievalTrace | null>(null);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);

  const requestId = useRef(0);
  const controller = useRef<AbortController | null>(null);

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
  const draftDiffers = submitted !== null && submitted !== configurationKey;

  const runComparison = useCallback(async () => {
    const trimmed = question.trim();
    if (trimmed.length < 5 || isBackendConnected === false) return;
    const currentRequestId = ++requestId.current;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setIsSubmitting(true);
    setError(null);
    setTrace(null);
    setSelectedChunkId(null);
    setSubmitted(configurationKey);
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
    } catch (reason) {
      if (currentRequestId !== requestId.current) return;
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(describeRequestError(reason, vi ? "Không thể so sánh reranker." : "Reranker comparison failed.", vi ? "vi" : "en").message);
    } finally {
      if (currentRequestId === requestId.current) setIsSubmitting(false);
    }
  }, [candidatePool, configurationKey, filters, isBackendConnected, preset, question, topK, vi]);

  const candidates = trace?.candidates ?? [];
  const ordered = useMemo(() => sortCandidates(candidates, "trace_order"), [candidates]);
  const selectedCandidate = useMemo(
    () => candidates.find((candidate) => candidate.chunk_id === selectedChunkId) ?? ordered[0] ?? null,
    [candidates, ordered, selectedChunkId],
  );
  const stage = trace ? rerankerStage(trace) : null;
  const status = stage ? stageStatus(stage) : null;
  const model = trace ? rerankerModel(trace) : null;
  const reranked = useMemo(() => candidates.filter((candidate) => typeof candidate.cross_encoder_score === "number"), [candidates]);
  const poolComplete = poolHasRerankerScores(candidates);
  const missingScores = candidates.length - reranked.length;

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

  const openDocument = useCallback((candidate: RetrievalCandidate) => {
    const source: Source = {
      citation: candidate.citation,
      text_preview: candidate.text_preview,
      chunk_id: candidate.chunk_id,
      document_id: candidate.document_id,
      ticker: candidate.ticker,
      section: candidate.section,
      filing_date: candidate.filing_date,
    };
    if (!candidate.document_id || !onOpenDocument) {
      onOpenSource?.(source);
      return;
    }
    onOpenDocument({
      kind: "retrieval",
      documentId: candidate.document_id,
      title: `${candidate.ticker ? formatCompanyLabel(candidate.ticker) : "SEC filing"} · ${candidate.filing_date ?? "date unavailable"}`,
      selectedSource: source,
      returnView: "retrieval",
      returnFocusId: retrievalFocusId(candidate.chunk_id),
    });
  }, [onOpenDocument, onOpenSource]);

  return (
    <section className="workspace-page workspace-page--wide retrieval-page console-view-enter" aria-labelledby="reranker-title">
      <div className="console-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><GitCompare aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="reranker-title" className="console-page-header__title">{vi ? "Reranker" : "Reranker"}</h1>
            <p className="console-page-header__subtitle">
              {vi
                ? "So sánh thứ tự fusion với thứ tự cross-encoder trong cùng một trace và cùng một pool ứng viên."
                : "Compare the fused order with the cross-encoder order inside one trace and one candidate pool."}
            </p>
          </div>
        </div>
      </div>

      <div className="retrieval-layout">
        <div className="retrieval-layout__main">
          <RetrievalQueryCard
            vi={vi}
            label={vi ? "Câu hỏi so sánh" : "Comparison Query"}
            question={question}
            onQuestionChange={setQuestion}
            questionPlaceholder={vi ? "Ví dụ: Rủi ro chuỗi cung ứng của nhà sản xuất ô tô" : "For example: supply chain risk for a manufacturer"}
            filters={filters}
            onFilterChange={setFilters}
            tickerOptions={tickerOptions}
            yearOptions={[]}
            documentOptions={[{ value: "", label: vi ? "Tất cả tài liệu" : "All documents" }]}
            documentNote={null}
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
            onSubmit={() => void runComparison()}
            submitLabel={vi ? "Chạy so sánh" : "Run Comparison"}
            submitAriaLabel={vi ? "Chạy so sánh reranker" : "Run reranker comparison"}
            onUseInResearch={() => onUseQuestion(question, { ticker: filters.ticker || null, section: filters.section || null })}
          />

          {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}

          {trace && (
            <div className="retrieval-submitted" data-testid="reranker-query-context">
              <span className="retrieval-submitted__text">
                <span className="font-semibold">{vi ? "Truy vấn đã gửi:" : "Submitted query:"}</span>{" "}
                <code className="font-mono">{trace.query}</code>{" · "}
                <span>{traceConfigurationSummary(trace, vi)}</span>
              </span>
            </div>
          )}

          {trace && (
            <>
              <div className="console-stats" data-testid="reranker-stage-summary">
                <div className="console-stat">
                  <div className="console-stat__icon console-stat__icon--warning"><GitCompare aria-hidden="true" /></div>
                  <div className="min-w-0">
                    <div className="console-stat__value console-stat__value--status">
                      {status ? stageStatusLabel(status, vi) : (vi ? "Không có stage" : "No stage")}
                    </div>
                    <div className="console-stat__label">{vi ? "Stage reranker" : "Reranker stage"}</div>
                    <div className="console-stat__hint">
                      {stage?.reason ?? (vi ? "Do endpoint báo cáo" : "Reported by the endpoint")}
                    </div>
                  </div>
                </div>
                <div className="console-stat">
                  <div className="console-stat__icon"><GitCompare aria-hidden="true" /></div>
                  <div className="min-w-0">
                    <div className="console-stat__value">{formatCount(reranked.length, vi)}</div>
                    <div className="console-stat__label">{vi ? "Ứng viên có điểm reranker" : "Candidates with a reranker score"}</div>
                    <div className="console-stat__hint">
                      {vi ? `Trong pool ${formatCount(candidates.length, vi)} ứng viên` : `Of the ${formatCount(candidates.length, vi)}-candidate pool`}
                    </div>
                  </div>
                </div>
                <div className="console-stat">
                  <div className="console-stat__icon"><GitCompare aria-hidden="true" /></div>
                  <div className="min-w-0">
                    <div className="console-stat__value">{stage ? formatDuration(stage.elapsed_ms, vi) : (vi ? "Chưa có dữ liệu" : "Not reported")}</div>
                    <div className="console-stat__label">{vi ? "Thời lượng rerank" : "Rerank duration"}</div>
                    <div className="console-stat__hint">{model ?? (vi ? "Không có mô hình nào chạy" : "No model was run")}</div>
                  </div>
                </div>
                <div className="console-stat">
                  <div className="console-stat__icon"><GitCompare aria-hidden="true" /></div>
                  <div className="min-w-0">
                    <div className="console-stat__value">{formatCount(trace.selected_count ?? trace.selected_chunk_ids.length, vi)}</div>
                    <div className="console-stat__label">{vi ? "Ứng viên được chọn" : "Selected candidates"}</div>
                    <div className="console-stat__hint">{vi ? `top K ${trace.top_k} của preset` : `top K ${trace.top_k} of the preset`}</div>
                  </div>
                </div>
              </div>

              <div className="console-card">
                <div className="console-card__header">
                  <div className="min-w-0">
                    <h2 className="console-card__title">{vi ? "Fusion so với cross-encoder" : "Fusion versus cross-encoder"}</h2>
                    <p className="console-card__subtitle">
                      {poolComplete
                        ? (vi
                            ? "Cùng một pool: mọi ứng viên đều có hạng fusion và điểm reranker."
                            : "Same pool: every candidate carries both a fusion rank and a reranker score.")
                        : (vi
                            ? `${formatCount(missingScores, vi)} ứng viên không có điểm reranker trong trace này.`
                            : `${formatCount(missingScores, vi)} ${missingScores === 1 ? "candidate has" : "candidates have"} no reranker score in this trace.`)}
                    </p>
                  </div>
                </div>
                <div className="console-table-wrap">
                  <table className="console-table">
                    <thead>
                      <tr>
                        <th scope="col" className="w-12 text-right">{vi ? "Hạng cuối" : "Final"}</th>
                        <th scope="col">{vi ? "Ứng viên" : "Candidate"}</th>
                        <th scope="col" className="text-right">{vi ? "Hạng fusion" : "Fusion rank"}</th>
                        <th scope="col" className="retrieval-score-column">{vi ? "Điểm reranker" : "Reranker score"}</th>
                        <th scope="col">{vi ? "Dịch chuyển" : "Movement"}</th>
                        <th scope="col">{vi ? "Trạng thái" : "Status"}</th>
                        <th scope="col" className="text-right">{vi ? "Hành động" : "Actions"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ordered.map((candidate) => {
                        const movement = rankMovement(candidate, vi);
                        const statusInfo = candidateStatus(candidate, vi);
                        const isSelected = candidate.chunk_id === selectedChunkId;
                        return (
                          <tr
                            key={candidate.chunk_id}
                            className={isSelected ? "is-selected" : ""}
                            aria-selected={isSelected}
                            tabIndex={0}
                            onClick={() => setSelectedChunkId(candidate.chunk_id)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                if (event.key === " ") event.preventDefault();
                                setSelectedChunkId(candidate.chunk_id);
                              }
                            }}
                          >
                            <td className="text-right console-table__secondary">{candidate.final_rank ?? "—"}</td>
                            <td>
                              <div className="console-table__primary">{candidate.citation}</div>
                              <div className="console-table__secondary line-clamp-1">{candidate.text_preview}</div>
                            </td>
                            <td className="text-right console-table__secondary">
                              <span className="reranker-track" aria-hidden="true">
                                <span
                                  className="reranker-track__dot reranker-track__dot--before"
                                  style={{ left: `${Math.min(100, Math.max(0, ((movement.before ?? 0) / Math.max(1, candidates.length)) * 100))}%` }}
                                />
                                <span
                                  className="reranker-track__dot reranker-track__dot--after"
                                  style={{ left: `${Math.min(100, Math.max(0, ((movement.after ?? 0) / Math.max(1, candidates.length)) * 100))}%` }}
                                />
                              </span>
                              {movement.before ?? "—"}
                            </td>
                            <td className="retrieval-score-column">
                              {typeof candidate.cross_encoder_score === "number"
                                ? formatScoreForFamily("cross_encoder_score", candidate.cross_encoder_score, vi)
                                : (vi ? "Không có điểm" : "No score")}
                            </td>
                            <td><MovementCell candidate={candidate} vi={vi} /></td>
                            <td><span className="console-chip">{statusInfo.label}</span></td>
                            <td className="text-right">
                              <span className="flex items-center justify-end gap-1">
                                {onOpenSource && (
                                  <button
                                    type="button"
                                    className="console-btn console-btn--ghost console-btn--icon"
                                    aria-label={vi ? "Mở đoạn đã lập chỉ mục" : "Open indexed source"}
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      onOpenSource({
                                        citation: candidate.citation,
                                        text_preview: candidate.text_preview,
                                        chunk_id: candidate.chunk_id,
                                        document_id: candidate.document_id,
                                        ticker: candidate.ticker,
                                        section: candidate.section,
                                        filing_date: candidate.filing_date,
                                      });
                                    }}
                                  >
                                    <GitCompare aria-hidden="true" />
                                  </button>
                                )}
                                {onOpenDocument && (
                                  <button
                                    id={retrievalFocusId(candidate.chunk_id)}
                                    type="button"
                                    className="console-btn console-btn--ghost console-btn--icon"
                                    aria-label={vi ? "Mở tài liệu" : "Open document workspace"}
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      openDocument(candidate);
                                    }}
                                  >
                                    <GitCompare aria-hidden="true" />
                                  </button>
                                )}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                      {ordered.length === 0 && (
                        <tr>
                          <td colSpan={7}>
                            <div className="console-empty">
                              <GitCompare aria-hidden="true" />
                              <strong>{vi ? "Không có ứng viên" : "No candidates"}</strong>
                              <p>
                                {vi
                                  ? "Trace này không trả về ứng viên nào trong phạm vi đã gửi."
                                  : "This trace returned no candidates in the submitted scope."}
                              </p>
                            </div>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="console-card__footer">
                  <span className="text-xs text-[var(--text-muted)]">
                    {vi
                      ? "Hạng fusion là thứ tự vào reranker; hạng cuối là thứ tự trace trả về. Điểm là logit cross-encoder, chỉ so sánh trong cùng pool."
                      : "The fusion rank is the order entering the reranker; the final rank is the order the trace returned. The score is a cross-encoder logit, comparable only within this pool."}
                  </span>
                </div>
              </div>

              <TraceDisclosures vi={vi} trace={trace} candidates={candidates} />
            </>
          )}

          {!trace && !isSubmitting && !error && (
            <div className="console-card">
              <div className="console-empty">
                <GitCompare aria-hidden="true" />
                <strong>{vi ? "Chạy một câu hỏi để so sánh" : "Run a question to compare"}</strong>
                <p>
                  {vi
                    ? "Một trace trả về cả thứ tự fusion và thứ tự cross-encoder, nên reranker không được chạy lần thứ hai để vẽ trang này."
                    : "One trace returns both the fused and the cross-encoder order, so this page never runs the reranker a second time."}
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
          onOpenSource={onOpenSource}
          onSaveEvidence={onSaveEvidence}
        />
      </div>
    </section>
  );
}
