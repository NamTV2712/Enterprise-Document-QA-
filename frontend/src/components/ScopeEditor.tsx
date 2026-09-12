import { useEffect, useId, useMemo, useRef, useState } from "react";
import { X } from "lucide-react";

import { NumberRangeField } from "./NumberRangeField";
import { SelectField } from "./ui/SelectField";
import { SECTION_METADATA, formatCompanyLabel } from "../lib/displayMetadata";
import { useLocale } from "../lib/i18n";

interface ScopeEditorProps {
  scopeLabel?: string;
  tickers: string[];
  sections: string[];
  selectedTicker: string | null;
  onSelectTicker: (ticker: string | null) => void;
  selectedSection: string | null;
  onSelectSection: (section: string | null) => void;
  topK: number;
  onChangeTopK: (topK: number) => void;
  enableComparative: boolean;
  onToggleComparative: (enabled: boolean) => void;
  disabled?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/**
 * Retrieval constraints belong next to the question, but must not expand the
 * composer dock. This popover keeps the active scope legible and the detailed
 * controls available without stealing answer-reading space.
 */
export function ScopeEditor({
  scopeLabel,
  tickers,
  sections,
  selectedTicker,
  onSelectTicker,
  selectedSection,
  onSelectSection,
  topK,
  onChangeTopK,
  enableComparative,
  onToggleComparative,
  disabled = false,
  open: controlledOpen,
  onOpenChange,
}: ScopeEditorProps) {
  const { locale, t } = useLocale();
  const vi = locale === "vi";
  const [open, setOpen] = useState(false);
  const isOpen = controlledOpen ?? open;
  const setIsOpen = (next: boolean) => {
    onOpenChange?.(next);
    if (controlledOpen === undefined) setOpen(next);
  };
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

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
      ...sections.map((section) => ({
        value: section,
        label: SECTION_METADATA[section]?.shortLabel || section,
      })),
    ],
    [sections, vi],
  );

  useEffect(() => {
    if (!isOpen) return;
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Element | null;
      if (target?.closest(".select-field__menu")) return;
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      const target = event.target;
      if (
        (target instanceof Element && target.closest(".select-field__menu"))
        || document.querySelector(".select-field__menu")
      ) return;
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    requestAnimationFrame(() => closeRef.current?.focus());
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [isOpen]);

  const close = () => {
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  return (
    <div ref={rootRef} className="composer-settings">
      <button
        ref={triggerRef}
        type="button"
        className="composer-settings__trigger"
        aria-expanded={isOpen}
        aria-controls={isOpen ? panelId : undefined}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{t("input.scope")} {scopeLabel ? `· ${scopeLabel}` : ""}</span>
        <span className="composer-settings__edit">{vi ? "Chỉnh sửa" : "Edit"}</span>
      </button>
      {isOpen && (
        <section
          id={panelId}
          className="composer-settings__popover"
          role="dialog"
          aria-label={vi ? "Phạm vi truy xuất" : "Retrieval scope"}
        >
          <div className="composer-settings__heading">
            <div>
              <p>{vi ? "Phạm vi truy xuất" : "Retrieval scope"}</p>
              <span>{vi ? "Giới hạn nguồn trước khi gửi câu hỏi" : "Limit evidence before sending your question"}</span>
            </div>
            <button ref={closeRef} type="button" className="composer-settings__close" onClick={close} aria-label={vi ? "Đóng phạm vi truy xuất" : "Close retrieval scope"}>
              <X aria-hidden="true" size={16} />
            </button>
          </div>
          <div className="composer-settings__grid">
            <SelectField label={vi ? "Công ty" : "Company"} value={selectedTicker ?? ""} options={tickerOptions} disabled={disabled} onValueChange={(value) => onSelectTicker(value || null)} />
            <SelectField label={vi ? "Mục 10-K" : "10-K section"} value={selectedSection ?? ""} options={sectionOptions} disabled={disabled} onValueChange={(value) => onSelectSection(value || null)} />
            <NumberRangeField id="composer-top-k" label="Top K" value={topK} min={1} max={10} disabled={disabled} hint={vi ? "Số đoạn nguồn giữ lại sau xếp hạng lại" : "Sources kept after reranking"} onChange={onChangeTopK} />
            <label className="composer-settings__toggle">
              <input type="checkbox" checked={enableComparative} onChange={(event) => onToggleComparative(event.target.checked)} disabled={disabled} />
              <span>{vi ? "So sánh công ty" : "Compare companies"}</span>
            </label>
          </div>
        </section>
      )}
    </div>
  );
}
