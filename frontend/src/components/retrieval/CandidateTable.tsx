import { memo } from "react";
import { ChevronLeft, ChevronRight, Copy, FileText, FolderOpen, SearchX } from "lucide-react";
import { SelectField } from "../ui/SelectField";
import {
  candidateStatus,
  formatScoreForFamily,
  pageLabel,
  pageRange,
  type ResultOrderKey,
} from "../../lib/traceModel";
import type { RetrievalCandidate, RetrievalScoreKey } from "../../types";

interface CandidateTableProps {
  candidates: RetrievalCandidate[];
  totalCandidates: number;
  page: number;
  pageSize: number;
  order: ResultOrderKey;
  orderOptionsList: Array<{ value: ResultOrderKey; label: string }>;
  onOrderChange: (value: ResultOrderKey) => void;
  onPageSizeChange: (value: number) => void;
  onPageChange: (value: number) => void;
  orderScoreKey: RetrievalScoreKey;
  orderScoreLabel: string;
  orderScoreNote: string | null;
  selectedChunkId: string | null;
  onSelect: (candidate: RetrievalCandidate) => void;
  onOpenDocument?: (candidate: RetrievalCandidate) => void;
  onOpenSource?: (candidate: RetrievalCandidate) => void;
  onSaveEvidence?: (candidate: RetrievalCandidate) => void;
  vi: boolean;
  isBusy?: boolean;
  focusIdFor: (candidate: RetrievalCandidate) => string;
}

const PAGE_SIZES = [10, 20, 50];
const COLUMN_COUNT = 6;

function pillModifier(displayRank: number): string {
  if (displayRank === 1) return "console-pill--high";
  if (displayRank === 2 || displayRank === 3) return "console-pill--mid";
  return "console-pill--info";
}

function statusModifier(kind: "selected" | "dropped" | "not_selected"): string {
  if (kind === "selected") return "retrieval-status--selected";
  if (kind === "dropped") return "retrieval-status--dropped";
  return "retrieval-status--none";
}

export const CandidateTable = memo(function CandidateTable({
  candidates,
  totalCandidates,
  page,
  pageSize,
  order,
  orderOptionsList,
  onOrderChange,
  onPageSizeChange,
  onPageChange,
  orderScoreKey,
  orderScoreLabel,
  orderScoreNote,
  selectedChunkId,
  onSelect,
  onOpenDocument,
  onOpenSource,
  onSaveEvidence,
  vi,
  isBusy = false,
  focusIdFor,
}: CandidateTableProps) {
  const range = pageRange(totalCandidates, page, pageSize);
  const pageSizeOptions = PAGE_SIZES.map((size) => ({
    value: String(size),
    label: vi ? `${size} / trang` : `${size} per page`,
  }));

  return (
    <div className="console-card">
      <div className="console-card__header">
        <div className="min-w-0">
          <h2 className="console-card__title">{vi ? "Kết quả đã lấy" : "Retrieved Results"}</h2>
          <p className="console-card__subtitle">
            {vi ? "Xếp hạng từ trace đã gửi." : "Ranked results from the submitted trace."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SelectField
            className="console-header-select"
            label={vi ? "Thứ tự" : "Order"}
            value={order}
            options={orderOptionsList.map((option) => ({ value: option.value, label: option.label }))}
            onValueChange={(value) => onOrderChange(value as ResultOrderKey)}
          />
          <SelectField
            className="console-header-select"
            label={vi ? "Số dòng mỗi trang" : "Rows per page"}
            value={String(pageSize)}
            options={pageSizeOptions}
            onValueChange={(value) => onPageSizeChange(Number(value))}
          />
        </div>
      </div>

      <div className="console-table-wrap">
        <table className="console-table">
          <thead>
            <tr>
              <th scope="col" className="w-12 text-right">#</th>
              <th scope="col" className="retrieval-score-column">{orderScoreLabel}</th>
              <th scope="col">Content Preview</th>
              <th scope="col">Source</th>
              <th scope="col">Status</th>
              <th scope="col" className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate, index) => {
              const isSelected = candidate.chunk_id === selectedChunkId;
              const status = candidateStatus(candidate, vi);
              // The emphasis follows the candidate's position in the whole
              // displayed order, not its position on this page, so page two
              // never makes its first row look like the top result.
              const displayPosition = (page - 1) * pageSize + index + 1;
              return (
                <tr
                  key={candidate.chunk_id}
                  className={isSelected ? "is-selected" : ""}
                  aria-selected={isSelected}
                  tabIndex={0}
                  onClick={() => onSelect(candidate)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      if (event.key === " ") event.preventDefault();
                      onSelect(candidate);
                    }
                  }}
                >
                  <td className="w-12 text-right console-table__secondary">
                    {candidate.final_rank ?? "—"}
                  </td>
                  <td className="retrieval-score-column">
                    <span className={`console-pill ${pillModifier(displayPosition)}`}>
                      {formatScoreForFamily(orderScoreKey, candidate[orderScoreKey], vi)}
                    </span>
                  </td>
                  <td>
                    <div className="console-table__primary">{candidate.citation}</div>
                    <div className="console-table__secondary line-clamp-2">{candidate.text_preview}</div>
                  </td>
                  <td>
                    <span className="console-chip">
                      {candidate.section ?? (vi ? "Không rõ mục" : "Unknown section")}
                    </span>
                    {candidate.filing_date && (
                      <div className="console-table__secondary">{candidate.filing_date}</div>
                    )}
                  </td>
                  <td>
                    <span className={`console-chip search-chip ${statusModifier(status.kind)}`}>
                      {status.label}
                    </span>
                  </td>
                  <td className="text-right">
                    <span className="flex items-center justify-end gap-1">
                      {onOpenSource && (
                        <button
                          id={`${focusIdFor(candidate)}-indexed`}
                          type="button"
                          className="console-btn console-btn--ghost console-btn--icon"
                          aria-label={vi ? "Mở đoạn đã lập chỉ mục" : "Open indexed source"}
                          onClick={(event) => {
                            event.stopPropagation();
                            onOpenSource(candidate);
                          }}
                        >
                          <FileText aria-hidden="true" />
                        </button>
                      )}
                      {onOpenDocument && (
                        <button
                          id={focusIdFor(candidate)}
                          type="button"
                          className="console-btn console-btn--ghost console-btn--icon"
                          aria-label={vi ? "Mở tài liệu" : "Open document workspace"}
                          onClick={(event) => {
                            event.stopPropagation();
                            onOpenDocument(candidate);
                          }}
                        >
                          <FolderOpen aria-hidden="true" />
                        </button>
                      )}
                      {onSaveEvidence && (
                        <button
                          type="button"
                          className="console-btn console-btn--ghost console-btn--icon"
                          aria-label={vi ? "Lưu evidence" : "Save evidence"}
                          onClick={(event) => {
                            event.stopPropagation();
                            onSaveEvidence(candidate);
                          }}
                        >
                          <Copy aria-hidden="true" />
                        </button>
                      )}
                    </span>
                  </td>
                </tr>
              );
            })}
            {candidates.length === 0 && (
              <tr>
                <td colSpan={COLUMN_COUNT}>
                  <div className="console-empty">
                    <SearchX aria-hidden="true" />
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
          {pageLabel(range, totalCandidates, vi)}
        </span>
        {orderScoreNote !== null && (
          <span className="text-xs text-[var(--text-muted)]">{orderScoreNote}</span>
        )}
        <nav className="console-pager" aria-label={vi ? "Phân trang ứng viên" : "Candidate pagination"}>
          <button
            type="button"
            className="console-pager__page"
            aria-label={vi ? "Trước" : "Previous page"}
            disabled={page <= 1 || isBusy}
            onClick={() => onPageChange(page - 1)}
          >
            <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          <span className="console-pager__gap">{`${page} / ${range.pageCount}`}</span>
          <button
            type="button"
            className="console-pager__page"
            aria-label={vi ? "Sau" : "Next page"}
            disabled={page >= range.pageCount || isBusy}
            onClick={() => onPageChange(page + 1)}
          >
            <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </nav>
      </div>
    </div>
  );
});
