/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useId, useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  FileText,
  ArrowUpRight,
  Search,
  X,
  BookmarkPlus,
} from "lucide-react";
import { Source } from "../types";
import { formatCompanyLabel, SECTION_METADATA } from "../lib/displayMetadata";
import { normalizeLocaleSearch, useLocale } from "../lib/i18n";
import { saveEvidence, snapshotProvenanceFromSource } from "../lib/evidenceCollections";

interface SourcesPanelProps {
  sources: Source[];
  messageId?: string;
  focusSourceIndex?: number | null;
  onFocusHandled?: () => void;
}

export function getSectionDisplay(
  citation: string,
  sectionField?: string | null,
): { section: string; ticker: string; year: string } {
  const citationLower = citation.toLowerCase();

  const tickerMatch = citation.match(/^([A-Z]{1,5}(?:-[A-Z])?)(?:\s|_)/i);
  const ticker = tickerMatch?.[1]?.toUpperCase() || "SEC";

  // Extract year (4 digit number)
  const yearMatch =
    citation.match(/_(20\d{2})_/) ||
    citation.match(/_(19\d{2})_/) ||
    citation.match(/\b(20\d{2})\b/) ||
    citation.match(/\b(19\d{2})\b/);
  const year = yearMatch ? yearMatch[1] : "";

  // Extract Section Item
  let matchedItem = sectionField || "";
  const explicitSection = citation.match(/Section:\s*([^,]+)/i)?.[1]?.trim();
  if (!matchedItem && explicitSection) {
    const normalizedSection = explicitSection.toLowerCase().replace(/\s+/g, "_");
    if (SECTION_METADATA[normalizedSection]) {
      matchedItem = normalizedSection;
    }
  }
  if (!matchedItem) {
    const itemMatch =
      citationLower.match(/item_(\d+[a-z]?)/) ||
      citationLower.match(/item\s+(\d+[a-z]?)/);
    if (itemMatch) {
      matchedItem = `item_${itemMatch[1]}`;
    }
  }

  if (!matchedItem) {
    const items = [
      "item_1a",
      "item_1b",
      "item_7a",
      "item_9a",
      "item_9b",
      "item_1",
      "item_2",
      "item_3",
      "item_4",
      "item_5",
      "item_6",
      "item_7",
      "item_8",
      "item_9",
      "item_10",
      "item_11",
      "item_12",
      "item_13",
      "item_14",
      "item_15",
    ];
    for (const it of items) {
      if (
        citationLower.includes(it) ||
        citationLower.includes(it.replace("_", " "))
      ) {
        matchedItem = it;
        break;
      }
    }
  }

  if (SECTION_METADATA[matchedItem]) {
    return {
      section: SECTION_METADATA[matchedItem].label,
      ticker,
      year,
    };
  }

  const cleanItem = matchedItem.toLowerCase().replace(/_/g, " ").trim();

  const secMap: Record<string, string> = {
    "item 1": "Business Overview",
    "item 1a": "Risk Factors",
    "item 1b": "Unresolved Staff Comments",
    "item 2": "Properties",
    "item 3": "Legal Proceedings",
    "item 4": "Mine Safety Disclosures",
    "item 5": "Market and Shareholder Matters",
    "item 6": "Selected Financial Data",
    "item 7": "Management Discussion & Analysis (MD&A)",
    "item 7a": "Market Risk Disclosures",
    "item 8": "Financial Statements & Supplementary Data",
    "item 9": "Accountant Disagreements",
    "item 9a": "Controls and Procedures",
    "item 9b": "Other Information",
    "item 10": "Directors & Officers",
    "item 11": "Executive Compensation",
    "item 12": "Security Ownership",
    "item 13": "Related Transactions",
    "item 14": "Accountant Fees & Services",
    "item 15": "Exhibits & Schedules",
  };

  const sectionName =
    secMap[cleanItem] ||
    (cleanItem ? cleanItem.toUpperCase() : "General Document");
  return { section: sectionName, ticker, year };
}

function getSectionBadgeClass(sectionName: string): string {
  const lower = sectionName.toLowerCase();
  if (lower.includes("risk")) return "section-badge--risk";
  if (lower.includes("table") || lower.includes("financial") || lower.includes("statement"))
    return "section-badge--financial";
  if (lower.includes("md&a") || lower.includes("discussion")) return "section-badge--mdna";
  return "section-badge--business";
}

/** Escape user input so evidence search stays literal, never a regex. */
function escapeLiteral(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildExcerptCopyText(source: Source, sourceNumber: number): string {
  const lines = [`[Source ${sourceNumber}] ${source.citation}`];
  if (source.ticker) lines.push(`Company: ${formatCompanyLabel(source.ticker)}`);
  if (source.section) {
    lines.push(`Section: ${SECTION_METADATA[source.section]?.label ?? source.section}`);
  }
  if (source.filing_date) lines.push(`Filed: ${source.filing_date}`);
  lines.push("", source.text || source.text_preview);
  return lines.join("\n");
}

export const SourcesPanel: React.FC<SourcesPanelProps> = ({
  sources,
  messageId = "message",
  focusSourceIndex = null,
  onFocusHandled,
}) => {
  const { locale } = useLocale();
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [copyStateIndex, setCopyStateIndex] = useState<number | null>(null);
  const [savedStateIndex, setSavedStateIndex] = useState<number | null>(null);
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null);
  const panelId = `sources-panel-${useId().replace(/:/g, "")}`;
  const safeMessageId = messageId.replace(/[^a-zA-Z0-9_-]/g, "-");

  const { companySummary, remainingCompanies } = useMemo(() => {
    const sourceTickers = Array.from(
      new Set(sources.map((source) => source.ticker || getSectionDisplay(source.citation).ticker)),
    );
    return {
      companySummary: sourceTickers
        .slice(0, 2)
        .map(formatCompanyLabel)
        .join(" · "),
      remainingCompanies: Math.max(0, sourceTickers.length - 2),
    };
  }, [sources]);

  // Literal, case-insensitive filtering over the excerpt text. The source
  // number always follows the original array order, so [Source N] labels
  // stay stable while excerpts are filtered.
  const visibleIndexes = useMemo(() => {
    const needle = normalizeLocaleSearch(searchQuery.trim());
    if (!needle) return sources.map((_, index) => index);
    return sources
      .map((source, index) => ({ source, index }))
      .filter(({ source }) =>
        normalizeLocaleSearch(`${source.text || source.text_preview} ${source.citation}`).includes(needle),
      )
      .map(({ index }) => index);
  }, [searchQuery, sources]);

  useEffect(() => {
    if (focusSourceIndex === null || focusSourceIndex < 0) return;
    // A citation jump must always reveal its source: if the requested index
    // is hidden by the active filter, clear the filter first.
    if (!visibleIndexes.includes(focusSourceIndex)) {
      setSearchQuery("");
    }
    setIsOpen(true);
    setHighlightedIndex(focusSourceIndex);
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}${window.location.search}#evidence=${safeMessageId}-${focusSourceIndex}`,
    );
    const clearHighlight = window.setTimeout(() => setHighlightedIndex(null), 1800);
    const frame = window.requestAnimationFrame(() => {
      const source = document.getElementById(
        `${safeMessageId}-source-${focusSourceIndex}`,
      );
      source?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      source?.focus({ preventScroll: true });
      onFocusHandled?.();
    });
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(clearHighlight);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusSourceIndex, onFocusHandled, safeMessageId]);

  // A citation link can be copied or restored after a reload without putting
  // question text or answer content in the URL.
  useEffect(() => {
    const match = window.location.hash.match(new RegExp(`^#evidence=${safeMessageId}-(\\d+)$`));
    const index = match ? Number(match[1]) : -1;
    if (index < 0 || index >= sources.length || focusSourceIndex !== null) return;
    setIsOpen(true);
    setHighlightedIndex(index);
    const frame = window.requestAnimationFrame(() => {
      const source = document.getElementById(`${safeMessageId}-source-${index}`);
      source?.scrollIntoView({ behavior: "auto", block: "nearest" });
      source?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [focusSourceIndex, safeMessageId, sources.length]);

  const handleCopyExcerpt = async (index: number, source: Source) => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(buildExcerptCopyText(source, index + 1));
      setCopyStateIndex(index);
      window.setTimeout(() => setCopyStateIndex((current) => (current === index ? null : current)), 2000);
    } catch {
      setCopyStateIndex(null);
    }
  };

  const handleSaveEvidence = (index: number, source: Source) => {
    try {
      saveEvidence(source, { messageId, provenance: snapshotProvenanceFromSource(source) });
      setSavedStateIndex(index);
      window.setTimeout(() => setSavedStateIndex((current) => (current === index ? null : current)), 2000);
    } catch {
      setSavedStateIndex(null);
    }
  };

  if (!sources || sources.length === 0) return null;

  const filterHidesResults = searchQuery.trim().length > 0 && visibleIndexes.length === 0;

  return (
    <div className="sources-panel overflow-hidden my-4">
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={`${isOpen ? "Hide" : "Show"} ${sources.length} retrieved filing evidence excerpts`}
        onClick={() => setIsOpen(!isOpen)}
        className="sources-toggle w-full min-h-12 flex items-center justify-between gap-3 p-3.5 text-left text-sm font-semibold transition-colors cursor-pointer"
      >
        <div className="flex items-start gap-2 min-w-0">
          <FileText className="w-4 h-4 mt-0.5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
          <span className="min-w-0">
            <span className="block font-sans uppercase tracking-wider">
              {locale === "vi" ? "Bằng chứng filing được truy xuất" : "Retrieved filing evidence"} · {sources.length} {locale === "vi" ? "đoạn trích" : "excerpts"}
            </span>
            <span className="block mt-1 text-xs font-normal text-[var(--text-muted)] normal-case tracking-normal truncate">
              {companySummary}
              {remainingCompanies > 0 ? ` · +${remainingCompanies} more` : ""}
              {" · "}{isOpen
                ? locale === "vi" ? "Ẩn nội dung nguồn" : "Hide source text"
                : locale === "vi" ? "Mở nội dung nguồn và chi tiết xếp hạng" : "Open source text and ranking details"}
            </span>
          </span>
        </div>
        <span className="flex items-center gap-1.5 flex-shrink-0 text-xs font-semibold text-[var(--accent-text)]">
          {isOpen ? (locale === "vi" ? "Ẩn" : "Hide") : (locale === "vi" ? "Xem" : "View")}
          {isOpen ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </span>
      </button>

      {isOpen && (
          <div
            id={panelId}
            className="ui-expand-enter overflow-hidden border-t border-[var(--border-subtle)]"
          >
            <div className="px-3.5 py-3 bg-[var(--surface-muted)] border-b border-[var(--border-subtle)] text-xs text-[var(--text-muted)] leading-relaxed">
              {locale === "vi"
                ? "Đây là các đoạn filing dùng để làm căn cứ cho câu trả lời. Điểm rank chỉ sắp xếp các đoạn trong tập kết quả, không phải xác suất hay phần trăm độ tin cậy."
                : "These are the filing excerpts used to ground the answer. Rank score orders excerpts within this result set; it is not a probability or confidence percentage."}
            </div>
            <div className="px-3.5 py-2.5 bg-[var(--surface-muted)] border-b border-[var(--border-subtle)]">
              <div className="evidence-search flex items-center gap-2">
                <Search className="w-3.5 h-3.5 flex-shrink-0 text-[var(--text-subtle)]" aria-hidden="true" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder={locale === "vi" ? "Tìm trong các đoạn trích" : "Search within these excerpts"}
                  aria-label={locale === "vi" ? "Tìm trong bằng chứng" : "Search within these evidence excerpts"}
                  className="evidence-search__input"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    aria-label="Clear evidence search"
                    className="icon-button"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              <p className="mt-1.5 text-[11px] text-[var(--text-muted)]">
                {filterHidesResults
                  ? locale === "vi" ? "Không có đoạn trích phù hợp. Xóa tìm kiếm để xem tất cả nguồn." : "No excerpt matches this search. Clear it to see all sources."
                  : locale === "vi"
                    ? `Hiển thị ${visibleIndexes.length}/${sources.length} đoạn trích. Số nguồn giữ theo thứ tự ban đầu.`
                    : `Showing ${visibleIndexes.length} of ${sources.length} excerpts. Source numbers follow the original order.`}
              </p>
            </div>
            <div className="p-3.5 divide-y divide-[var(--border-subtle)] md:max-h-[min(28rem,55vh)] md:overflow-y-auto bg-[var(--surface-muted)]">
              {visibleIndexes.map((index) => {
                const source = sources[index];
                const sectionField = source.section;
                const { section, ticker, year } = getSectionDisplay(
                  source.citation,
                  sectionField,
                );
                const evidenceText = source.text || source.text_preview;
                const isPreviewOnly = !source.text;
                const displayScore =
                  source.score_kind && typeof source.score === "number"
                    ? `${source.score_kind} · ${source.score.toFixed(4)}`
                    : null;
                // The filing date describes the document, not the fiscal
                // period of any number inside the excerpt.
                const filedLabel = source.filing_date || (year ? `20${year.slice(-2)} filing year` : "");

                return (
                  <div
                    key={index}
                    className={`source-item py-3 first:pt-0 last:pb-0 ${highlightedIndex === index ? "source-item--focused" : ""}`}
                    id={`${safeMessageId}-source-item-${index}`}
                    tabIndex={-1}
                    data-source-index={index}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Section-colored badge tag */}
                        <span className={`section-badge ${getSectionBadgeClass(section)} shadow-4xs`}>
                          <ArrowUpRight className="w-3.5 h-3.5" />
                          <span>
                            {formatCompanyLabel(source.ticker || ticker)}
                            {filedLabel ? ` · Filed ${filedLabel}` : year ? ` '${year.slice(-2)}` : ""} ·{" "}
                            {section}
                          </span>
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {displayScore && (
                          <div className="flex items-center gap-1.5 font-mono">
                            <span className="text-xs text-[var(--text-muted)] font-semibold">
                              Score kind
                            </span>
                            <span className="text-xs font-bold text-[var(--accent-text)] bg-brand-indigo/10 dark:bg-brand-indigo/20 border border-brand-indigo/30 px-2 py-0.5 rounded shadow-4xs">
                              {displayScore}
                            </span>
                          </div>
                        )}
                        <button
                          type="button"
                          onClick={() => void handleCopyExcerpt(index, source)}
                          aria-label={
                            copyStateIndex === index
                              ? locale === "vi" ? `Đã sao chép đoạn ${index + 1}` : `Copied excerpt ${index + 1}`
                              : locale === "vi" ? `Sao chép đoạn ${index + 1} kèm citation` : `Copy excerpt ${index + 1} with citation`
                          }
                          className="icon-button evidence-copy-button"
                        >
                          {copyStateIndex === index ? (
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSaveEvidence(index, source)}
                          aria-label={savedStateIndex === index ? (locale === "vi" ? `Đã lưu đoạn ${index + 1}` : `Saved excerpt ${index + 1}`) : (locale === "vi" ? `Lưu đoạn ${index + 1} vào bộ sưu tập` : `Save excerpt ${index + 1} to collection`)}
                          className="icon-button evidence-copy-button"
                        >
                          <BookmarkPlus className={`w-3.5 h-3.5 ${savedStateIndex === index ? "text-emerald-500" : ""}`} />
                        </button>
                      </div>
                    </div>
                    <p
                      id={`${safeMessageId}-source-${index}`}
                      tabIndex={-1}
                      className="source-preview text-sm leading-relaxed p-3.5 rounded-lg whitespace-pre-wrap select-all font-sans"
                    >
                      {isPreviewOnly && (
                        <span className="source-preview-label">Preview only · </span>
                      )}
                      {evidenceText}
                    </p>
                  </div>
                );
              })}
              {filterHidesResults && (
                <div className="py-6 text-center text-xs text-[var(--text-subtle)]">
                  {locale === "vi" ? "Không có đoạn trích phù hợp." : "No excerpt matches this search."}{" "}
                  <button
                    type="button"
                    className="text-[var(--accent-text)] font-semibold"
                    onClick={() => setSearchQuery("")}
                  >
                    {locale === "vi" ? "Xóa tìm kiếm" : "Clear the search"}
                  </button>{" "}
                  {locale === "vi" ? ` để xem toàn bộ ${sources.length} nguồn.` : ` to see all ${sources.length} sources.`}
                </div>
              )}
            </div>
          </div>
      )}
    </div>
  );
};
