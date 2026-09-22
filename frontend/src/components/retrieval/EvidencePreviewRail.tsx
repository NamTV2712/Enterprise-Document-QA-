import { memo } from "react";
import { Copy, ExternalLink, FileText, FolderOpen, X } from "lucide-react";

import { getSectionDisplay } from "../../lib/sourcePresentation";
import { formatCompanyLabel } from "../../lib/displayMetadata";
import {
  SCORE_KEYS,
  SCORE_LABELS,
  candidateStatus,
  formatScoreForFamily,
  rankMovement,
  rerankerModel,
} from "../../lib/traceModel";
import type { RetrievalCandidate, RetrievalTrace, Source } from "../../types";

interface EvidencePreviewRailProps {
  vi: boolean;
  trace: RetrievalTrace;
  candidate: RetrievalCandidate | null;
  isPinned: boolean;
  onClearSelection: () => void;
  onOpenDocument: (candidate: RetrievalCandidate) => void;
  onOpenSource?: (candidate: RetrievalCandidate) => void;
  onSaveEvidence?: (source: Source) => void;
}

function sourceOf(candidate: RetrievalCandidate): Source {
  return {
    citation: candidate.citation,
    text_preview: candidate.text_preview,
    chunk_id: candidate.chunk_id,
    document_id: candidate.document_id,
    ticker: candidate.ticker,
    section: candidate.section,
    filing_date: candidate.filing_date,
  };
}

/**
 * The selected candidate, read straight from the trace.
 *
 * Every number here is one of the trace's own values for this candidate: its
 * rank lineage, the families it reports, and — only when the trace supplied one
 * — the reason it was dropped. Nothing is normalised into a percentage, and a
 * family the candidate does not report says so.
 */
export const EvidencePreviewRail = memo(function EvidencePreviewRail({
  vi,
  trace,
  candidate,
  isPinned,
  onClearSelection,
  onOpenDocument,
  onOpenSource,
  onSaveEvidence,
}: EvidencePreviewRailProps) {
  if (!candidate) {
    return (
      <aside className="retrieval-rail" aria-label={vi ? "Xem trước evidence" : "Evidence preview"}>
        <div className="console-card">
          <div className="console-card__header">
            <h2 className="console-card__title">{vi ? "Xem trước evidence" : "Evidence Preview"}</h2>
          </div>
          <div className="console-empty">
            <FileText aria-hidden="true" />
            <strong>{vi ? "Chưa chọn ứng viên nào" : "No candidate selected"}</strong>
            <p>
              {vi
                ? "Chạy inspection, rồi chọn một hàng trong bảng để xem đoạn evidence cùng hạng và điểm của chính ứng viên đó."
                : "Run an inspection, then pick a row to inspect that candidate's excerpt, ranks, and own scores."}
            </p>
          </div>
        </div>
      </aside>
    );
  }

  const source = sourceOf(candidate);
  const status = candidateStatus(candidate, vi);
  const movement = rankMovement(candidate, vi);
  const sectionLabel = candidate.section ? getSectionDisplay("", candidate.section).section : null;
  const reranker = rerankerModel(trace);

  return (
    <aside className="retrieval-rail" aria-label={vi ? "Xem trước evidence" : "Evidence preview"}>
      <div className="console-card">
        <div className="console-card__header">
          <div className="min-w-0">
            <h2 className="console-card__title">{vi ? "Xem trước evidence" : "Evidence Preview"}</h2>
            <p className="console-card__subtitle">
              {candidate.ticker ? formatCompanyLabel(candidate.ticker) : (vi ? "Công ty chưa xác minh" : "Company not verified")}
              {candidate.filing_date ? ` · ${candidate.filing_date}` : ""}
            </p>
          </div>
          {isPinned && (
            <button
              type="button"
              className="console-btn console-btn--ghost console-btn--icon"
              aria-label={vi ? "Bỏ chọn ứng viên" : "Clear selected candidate"}
              onClick={onClearSelection}
            >
              <X aria-hidden="true" />
            </button>
          )}
        </div>
        <div className="console-card__body retrieval-preview__body">
          {sectionLabel && <p className="retrieval-preview__eyebrow">{sectionLabel}</p>}
          <div className="console-paper">
            <p className="console-paper__eyebrow">{candidate.chunk_id}</p>
            <p className="whitespace-pre-wrap">{candidate.text_preview}</p>
          </div>

          <div className="retrieval-preview__row">
            <span className={`console-chip search-chip retrieval-status--${status.kind === "selected" ? "selected" : status.kind === "dropped" ? "dropped" : "none"}`}>
              {status.label}
            </span>
            <span className="console-chip">{vi ? `Hạng cuối ${candidate.final_rank ?? "—"}` : `Final rank ${candidate.final_rank ?? "—"}`}</span>
            {movement.delta !== null && movement.delta !== 0 && (
              <span className="console-chip">{vi ? `${movement.label} sau rerank` : `${movement.label} after rerank`}</span>
            )}
          </div>

          <ul className="retrieval-preview__scores" data-testid="candidate-score-families">
            {SCORE_KEYS.map((key) => {
              const value = candidate[key];
              const reported = typeof value === "number";
              return (
                <li key={key} className="retrieval-preview__score">
                  <span className="retrieval-preview__score-label">{SCORE_LABELS[key]}</span>
                  <span className={`retrieval-preview__score-value ${reported ? "" : "retrieval-preview__score-value--missing"}`}>
                    {formatScoreForFamily(key, value, vi)}
                  </span>
                </li>
              );
            })}
          </ul>

          <div className="retrieval-preview__ranks">
            <span className="console-chip">BM25 #{candidate.bm25_rank ?? "—"}</span>
            <span className="console-chip">Dense #{candidate.dense_rank ?? "—"}</span>
            <span className="console-chip">Lexical #{candidate.lexical_rank ?? "—"}</span>
            <span className="console-chip">Fusion #{candidate.fusion_rank ?? "—"}</span>
            <span className="console-chip">Final #{candidate.final_rank ?? "—"}</span>
          </div>

          {reranker && candidate.cross_encoder_score !== null && candidate.cross_encoder_score !== undefined && (
            <p className="retrieval-preview__note">
              {vi ? `Điểm reranker do ${reranker} tính trong cùng pool ứng viên này.` : `Reranker score from ${reranker} within this same candidate pool.`}
            </p>
          )}
          {status.kind === "dropped" && (
            <p className="retrieval-preview__note">{vi ? `Lý do trace cung cấp: ${status.label}` : `Reason reported by the trace: ${status.label}`}</p>
          )}

          <div className="retrieval-preview__actions">
            <button type="button" className="console-btn console-btn--primary" onClick={() => onOpenDocument(candidate)}>
              <FolderOpen aria-hidden="true" />
              {vi ? "Mở trong tài liệu" : "Open in Document"}
            </button>
            {onOpenSource && (
              <button type="button" className="console-btn" onClick={() => onOpenSource(candidate)}>
                <ExternalLink aria-hidden="true" />
                {vi ? "Mở đoạn đã lập chỉ mục" : "Open indexed source"}
              </button>
            )}
            {onSaveEvidence && (
              <button type="button" className="console-btn" onClick={() => onSaveEvidence(source)}>
                <Copy aria-hidden="true" />
                {vi ? "Lưu evidence" : "Save as Evidence"}
              </button>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
});
