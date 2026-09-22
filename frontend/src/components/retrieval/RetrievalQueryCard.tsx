import { memo, useId } from "react";
import { ArrowRight, Search } from "lucide-react";

import { SelectField } from "../ui/SelectField";
import { PRESET_LABELS, PRESET_ORDER } from "../../lib/traceModel";
import type { RetrievalPreset } from "../../types";

export interface RetrievalFilterDraft {
  ticker: string;
  year: string;
  documentId: string;
  section: string;
}

interface RetrievalQueryCardProps {
  vi: boolean;
  label: string;
  question: string;
  onQuestionChange: (value: string) => void;
  questionPlaceholder: string;
  filters: RetrievalFilterDraft;
  onFilterChange: (next: RetrievalFilterDraft) => void;
  tickerOptions: Array<{ value: string; label: string }>;
  yearOptions: Array<{ value: string; label: string }>;
  documentOptions: Array<{ value: string; label: string }>;
  /** Truthful note about the bounded document list, when it is bounded. */
  documentNote: string | null;
  sectionOptions: Array<{ value: string; label: string }>;
  preset: RetrievalPreset;
  onPresetChange: (value: RetrievalPreset) => void;
  topK: number;
  onTopKChange: (value: number) => void;
  candidatePool: number;
  onCandidatePoolChange: (value: number) => void;
  isSubmitting: boolean;
  disabled: boolean;
  /** Set when the draft no longer matches the trace on screen. */
  draftDiffers: boolean;
  onSubmit: () => void;
  submitLabel: string;
  submitAriaLabel: string;
  onUseInResearch?: () => void;
}

/**
 * The inspection query card: the question, every filter the API-005 request
 * actually accepts, the real pool bounds, and the submit button. Typing only
 * edits the draft; nothing is requested until this form is submitted.
 */
export const RetrievalQueryCard = memo(function RetrievalQueryCard({
  vi,
  label,
  question,
  onQuestionChange,
  questionPlaceholder,
  filters,
  onFilterChange,
  tickerOptions,
  yearOptions,
  documentOptions,
  documentNote,
  sectionOptions,
  preset,
  onPresetChange,
  topK,
  onTopKChange,
  candidatePool,
  onCandidatePoolChange,
  isSubmitting,
  disabled,
  draftDiffers,
  onSubmit,
  submitLabel,
  submitAriaLabel,
  onUseInResearch,
}: RetrievalQueryCardProps) {
  const inputId = useId();
  const hintId = useId();
  // A run in flight cannot be submitted again unchanged (no accidental
  // duplicate), but an edited configuration can be committed immediately: the
  // previous request is aborted and its late response is ignored.
  const canSubmit = question.trim().length >= 5 && !disabled && (!isSubmitting || draftDiffers);
  const tooShort = question.trim().length > 0 && question.trim().length < 5;
  const presetOptions = PRESET_ORDER.map((value) => ({
    value,
    label: vi ? PRESET_LABELS[value].vi : PRESET_LABELS[value].label,
  }));

  return (
    <div className="console-card retrieval-query-card">
      <div className="console-card__body retrieval-query-card__body">
        <form
          className="retrieval-query-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (canSubmit) onSubmit();
          }}
        >
          <label className="retrieval-query-form__label" htmlFor={inputId}>{label}</label>
          <div className="console-input-row retrieval-query-form__input-row">
            <Search aria-hidden="true" />
            <input
              id={inputId}
              className="console-input retrieval-query-form__input"
              value={question}
              maxLength={500}
              onChange={(event) => onQuestionChange(event.target.value)}
              aria-describedby={hintId}
              placeholder={questionPlaceholder}
              autoComplete="off"
            />
          </div>
          <p id={hintId} className="retrieval-query-form__hint">
            {tooShort
              ? (vi ? "Cần ít nhất 5 ký tự để kiểm tra retrieval." : "At least 5 characters are needed to inspect retrieval.")
              : draftDiffers
                ? (vi ? "Cấu hình khác với trace đang hiển thị; chạy lại để cập nhật." : "This configuration differs from the trace on screen; run again to refresh it.")
                : (vi
                    ? "Inspection chạy các stage xếp hạng cục bộ; không gọi mô hình ngôn ngữ và không tốn quota."
                    : "Inspection runs the local ranking stages; it never calls a language model and costs no quota.")}
          </p>

          <div className="retrieval-query-form__filters">
            <SelectField
              label={vi ? "Công ty" : "Company"}
              value={filters.ticker}
              options={tickerOptions}
              onValueChange={(value) => onFilterChange({ ...filters, ticker: value })}
            />
            {yearOptions.length > 1 && (
              <SelectField
                label={vi ? "Năm nộp" : "Year"}
                value={filters.year}
                options={yearOptions}
                onValueChange={(value) => onFilterChange({ ...filters, year: value })}
              />
            )}
            <SelectField
              label={vi ? "Tài liệu" : "Document"}
              value={filters.documentId}
              options={documentOptions}
              onValueChange={(value) => onFilterChange({ ...filters, documentId: value })}
            />
            <SelectField
              label={vi ? "Mục" : "Section"}
              value={filters.section}
              options={sectionOptions}
              onValueChange={(value) => onFilterChange({ ...filters, section: value })}
            />
            <SelectField
              label={vi ? "Preset" : "Preset"}
              value={preset}
              options={presetOptions}
              onValueChange={(value) => onPresetChange(value as RetrievalPreset)}
            />
          </div>

          {documentNote && <p className="retrieval-query-form__note">{documentNote}</p>}

          <div className="retrieval-query-form__bounds">
            <label className="retrieval-bound">
              <span className="retrieval-bound__label">{vi ? "Kết quả cuối (top K)" : "Final results (top K)"}</span>
              <input
                type="number"
                className="console-input retrieval-bound__input"
                min={1}
                max={10}
                value={topK}
                aria-label={vi ? "Kết quả cuối (top K)" : "Final results (top K)"}
                onChange={(event) => onTopKChange(Math.min(10, Math.max(1, Number(event.target.value) || 1)))}
              />
            </label>
            <label className="retrieval-bound">
              <span className="retrieval-bound__label">{vi ? "Candidate pool" : "Candidate pool"}</span>
              <input
                type="number"
                className="console-input retrieval-bound__input"
                min={10}
                max={50}
                step={5}
                value={candidatePool}
                aria-label={vi ? "Candidate pool" : "Candidate pool"}
                onChange={(event) => onCandidatePoolChange(Math.min(50, Math.max(10, Number(event.target.value) || 10)))}
              />
            </label>
            <div className="retrieval-query-form__actions">
              {onUseInResearch && (
                <button type="button" className="console-btn" onClick={onUseInResearch}>
                  {vi ? "Dùng trong Research" : "Use in Research"}
                  <ArrowRight aria-hidden="true" />
                </button>
              )}
              <button type="submit" className="console-btn console-btn--primary" aria-label={submitAriaLabel} disabled={!canSubmit}>
                {isSubmitting ? <span className="console-loading__spinner" aria-hidden="true" /> : <Search aria-hidden="true" />}
                {isSubmitting ? (vi ? "Đang chạy…" : "Running…") : submitLabel}
                <ArrowRight aria-hidden="true" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
});
