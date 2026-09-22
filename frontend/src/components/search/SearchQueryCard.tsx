import { memo, useId } from "react";
import { ArrowRight, Search, X } from "lucide-react";

import { MAX_QUERY_LENGTH, MIN_QUERY_LENGTH, submittableQuery } from "../../lib/searchModel";
import { SelectField } from "../ui/SelectField";

export interface SearchFilterDraft {
  ticker: string;
  section: string;
  year: string;
}

interface SearchQueryCardProps {
  vi: boolean;
  draft: string;
  onDraftChange: (value: string) => void;
  filters: SearchFilterDraft;
  onFilterChange: (next: SearchFilterDraft) => void;
  tickerOptions: Array<{ value: string; label: string }>;
  sectionOptions: Array<{ value: string; label: string }>;
  yearOptions: Array<{ value: string; label: string }>;
  isSubmitting: boolean;
  disabled: boolean;
  /** Set when the draft no longer matches the snapshot on screen. */
  draftDiffers: boolean;
  onSubmit: () => void;
}

/**
 * The query card: the query field every search starts from, the real filter
 * axes API-004 supports, and the submit button. Typing only edits the draft;
 * nothing is requested until this form is submitted.
 */
export const SearchQueryCard = memo(function SearchQueryCard({
  vi,
  draft,
  onDraftChange,
  filters,
  onFilterChange,
  tickerOptions,
  sectionOptions,
  yearOptions,
  isSubmitting,
  disabled,
  draftDiffers,
  onSubmit,
}: SearchQueryCardProps) {
  const inputId = useId();
  const hintId = useId();
  const canSubmit = submittableQuery(draft) !== null && !disabled;
  const tooShort = draft.trim().length > 0 && draft.trim().length < MIN_QUERY_LENGTH;

  return (
    <div className="console-card search-query-card">
      <div className="console-card__body search-query-card__body">
        <form
          className="search-query-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (canSubmit) onSubmit();
          }}
        >
          <label className="search-query-form__label" htmlFor={inputId}>
            {vi ? "Truy vấn tìm kiếm" : "Search Query"}
          </label>
          <div className="console-input-row search-query-form__input-row">
            <Search aria-hidden="true" />
            <input
              id={inputId}
              className="console-input search-query-form__input"
              value={draft}
              maxLength={MAX_QUERY_LENGTH}
              onChange={(event) => onDraftChange(event.target.value)}
              aria-describedby={hintId}
              placeholder={vi ? "Ví dụ: supply chain risk, cloud revenue…" : "For example: supply chain risk, cloud revenue…"}
              autoComplete="off"
            />
            {draft && (
              <button
                type="button"
                className="console-input-row__clear"
                aria-label={vi ? "Xóa truy vấn" : "Clear query"}
                onClick={() => onDraftChange("")}
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            )}
          </div>
          <p id={hintId} className="search-query-form__hint">
            {tooShort
              ? (vi ? `Cần ít nhất ${MIN_QUERY_LENGTH} ký tự để tìm kiếm.` : `At least ${MIN_QUERY_LENGTH} characters are needed to search.`)
              : draftDiffers
                ? (vi ? "Bản nháp khác với kết quả đang hiển thị; nhấn Tìm kiếm để chạy truy vấn này." : "This draft differs from the results on screen; press Search to run it.")
                : (vi
                    ? "Tìm kiếm từ khóa trên văn bản đoạn nguồn đã lập chỉ mục; không gọi mô hình hay nhà cung cấp."
                    : "Keyword discovery over indexed excerpt text; no model or provider is called.")}
          </p>

          <div className="search-query-form__filters">
            <SelectField
              label={vi ? "Công ty" : "Company"}
              value={filters.ticker}
              options={tickerOptions}
              onValueChange={(value) => onFilterChange({ ...filters, ticker: value })}
            />
            {yearOptions.length > 0 && (
              <SelectField
                label={vi ? "Năm nộp" : "Year"}
                value={filters.year}
                options={yearOptions}
                onValueChange={(value) => onFilterChange({ ...filters, year: value })}
              />
            )}
            <SelectField
              label={vi ? "Mục" : "Section"}
              value={filters.section}
              options={sectionOptions}
              onValueChange={(value) => onFilterChange({ ...filters, section: value })}
            />
            <div className="search-query-form__submit">
              <button type="submit" className="console-btn console-btn--primary search-query-form__button" disabled={!canSubmit}>
                {isSubmitting ? <span className="console-loading__spinner" aria-hidden="true" /> : <Search aria-hidden="true" />}
                {isSubmitting ? (vi ? "Đang tìm…" : "Searching…") : (vi ? "Tìm kiếm" : "Search")}
                <ArrowRight aria-hidden="true" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
});
