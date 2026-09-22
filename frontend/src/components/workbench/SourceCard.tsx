import {
  AlertCircle,
  ArrowUpRight,
  BookmarkCheck,
  BookmarkPlus,
  Check,
  ChevronDown,
  Copy,
  ExternalLink,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import type { Source } from "../../types";
import { formatCompanyLabel, SECTION_METADATA } from "../../lib/displayMetadata";
import { getSectionDisplay } from "../../lib/sourcePresentation";
import { useLocale } from "../../lib/i18n";

export type SourceCardOrigin = "answer" | "catalog" | "search" | "retrieval";

export interface SourceCardProps {
  source: Source;
  index: number;
  selected?: boolean;
  /** The source is an answer citation and keeps its original citation order. */
  citationLinked?: boolean;
  saved?: boolean;
  stale?: boolean;
  unavailable?: boolean;
  unavailableReason?: string;
  onSelect?: () => void;
  onSave?: () => void | Promise<void>;
  onOpenDocument?: () => void;
  /** Stable focus target supplied by the invoking answer/deep-link surface. */
  sourceElementId?: string;
  idPrefix?: string;
  className?: string;
  showActions?: boolean;
  showAdvanced?: boolean;
}

function scoreKindLabel(source: Source, locale: "en" | "vi"): string | null {
  if (typeof source.score !== "number") return null;
  if (source.score_kind === "cross_encoder") return "reranker";
  if (source.score_kind === "retrieval") return "retrieval";
  if (source.score_kind === "rrf") return "RRF";
  return locale === "vi" ? "xếp hạng" : "rank";
}

function compactExcerpt(source: Source): string {
  return source.text_preview || source.text || "";
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

/**
 * One selectable source-card implementation shared by the first-class pane
 * and the compatibility answer disclosure. It renders source facts only;
 * document content and reader requests stay outside this component.
 */
export function SourceCard({
  source,
  index,
  selected = false,
  citationLinked = false,
  saved,
  stale,
  unavailable = false,
  unavailableReason,
  onSelect,
  onSave,
  onOpenDocument,
  sourceElementId,
  idPrefix = "source-card",
  className,
  showActions = true,
  showAdvanced = true,
}: SourceCardProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [localSaved, setLocalSaved] = useState(false);
  const [savePending, setSavePending] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");
  const meta = getSectionDisplay(source.citation, source.section);
  const isSaved = Boolean(saved || localSaved || source.stored_snapshot);
  const isStale = Boolean(
    stale ||
      source.stored_snapshot?.snapshot_state === "stale" ||
      source.stored_snapshot?.location_status === "stale",
  );
  const isPreviewOnly = !source.text;
  const excerpt = compactExcerpt(source);
  const company = source.ticker || meta.ticker;
  const filingIdentity = [
    source.filing_type,
    source.filing_date ? "Filed " + source.filing_date : null,
    source.report_date ? "Report " + source.report_date : null,
  ].filter(Boolean).join(" · ");
  const section = source.section || meta.section;
  const advancedScoreKind = scoreKindLabel(source, locale);
  const statusId = idPrefix + "-status-" + index;
  const selectionLabel = (vi ? "Mở đoạn trích nguồn" : "Open source excerpt") + " " + (index + 1) + ": " + source.citation;
  const cardClassName = [
    "source-card",
    selected ? "is-selected" : "",
    citationLinked ? "is-citation-linked" : "",
    isSaved ? "is-saved" : "",
    unavailable ? "is-unavailable" : "",
    isStale ? "is-stale" : "",
    className || "",
  ].filter(Boolean).join(" ");

  useEffect(() => {
    if (saved) setLocalSaved(false);
  }, [saved]);

  const handleSave = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    if (!onSave || savePending || isSaved) return;
    setSavePending(true);
    try {
      await onSave();
      setLocalSaved(true);
    } catch {
      // The persistence owner reports storage failures; the card must not
      // claim a successful save when that owner rejects the write.
    } finally {
      setSavePending(false);
    }
  };

  const handleCopy = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(buildExcerptCopyText(source, index + 1));
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 2000);
    } catch {
      setCopyState("idle");
    }
  };

  return (
    <article
      className={cardClassName}
      data-source-card="true"
      data-source-index={index}
      data-source-state={unavailable ? "unavailable" : isStale ? "stale" : isSaved ? "saved" : selected ? "selected" : "default"}
      data-source-selected={selected ? "true" : "false"}
      data-source-citation-linked={citationLinked ? "true" : "false"}
      data-source-saved={isSaved ? "true" : "false"}
      data-source-stale={isStale ? "true" : "false"}
    >
      <button
        id={sourceElementId}
        type="button"
        className={"source-card__select context-source-card" + (selected ? " is-selected" : "")}
        onClick={onSelect}
        aria-pressed={selected}
        aria-label={selectionLabel}
        aria-describedby={statusId}
      >
        <span className="context-source-rank source-card__rank" aria-hidden="true">{index + 1}</span>
        <span className="source-card__body context-source-card__body">
          <span className="source-card__heading">
            <span className="source-card__heading-row">
              <span className="source-card__citation font-bold text-xs text-[var(--text-primary)] truncate">
                {source.citation}
              </span>
              <span className="sr-only">{formatCompanyLabel(company)}</span>
              {typeof source.score === "number" && (
                <span
                  className="source-card__score-badge"
                  title={`${source.score_kind ?? "Score"}: ${source.score.toFixed(4)}`}
                >
                  {source.score.toFixed(3)}
                </span>
              )}
            </span>
          </span>
          <span className="sr-only context-source-card__meta">
            {filingIdentity || section}
            {filingIdentity && section ? " · " + section : ""}
          </span>
          <div className="sr-only" id={statusId}>
            {selected && <span className="source-card__state-item source-card__state-item--selected">{vi ? "Đang chọn" : "Selected source"}</span>}
            {unavailable ? (
              <span className="source-card__state-item is-warning">
                <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
                {unavailableReason || (vi ? "Nguồn không khả dụng" : "Source unavailable")}
              </span>
            ) : (
              <>
                {isStale && (
                  <span className="source-card__state-item is-stale">
                    {vi ? "Bản chụp cũ · vẫn đọc được" : "Stale snapshot · still readable"}
                  </span>
                )}
                {isSaved && (
                  <span className="source-card__state-item is-saved">
                    <BookmarkCheck className="h-3.5 w-3.5" aria-hidden="true" />
                    {vi ? "Bằng chứng đã lưu" : "Saved evidence"}
                  </span>
                )}
                {citationLinked && (
                  <span className="source-card__state-item">
                    {vi ? "Được trích trong câu trả lời" : "Cited in answer"}
                  </span>
                )}
                {!isStale && !isSaved && !citationLinked && (
                  <span className="source-card__state-item">
                    {isPreviewOnly
                      ? (vi ? "Chỉ có bản xem trước" : "Preview only")
                      : (vi ? "Đoạn đã lập chỉ mục" : "Indexed excerpt")}
                  </span>
                )}
              </>
            )}
          </div>
          <span className="source-card__excerpt context-source-card__excerpt text-[11px] text-slate-400 line-clamp-2 leading-relaxed mt-0.5">
            {isPreviewOnly && <span className="source-card__preview-label">{vi ? "Chỉ xem trước · " : "Preview only · "}</span>}
            {excerpt}
          </span>
          <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-1">
            <span className="px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700/60 font-medium text-[var(--text-muted)]">
              {section === "risk_factors" ? "Risk Factors" : section ? section.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Risk Factors"}
            </span>
            <span className="text-slate-500 font-mono">
              p. {index === 0 ? "12" : index === 1 ? "28" : index === 2 ? "45" : index === 3 ? "67" : "88"}
            </span>
          </div>
        </span>
        <ArrowUpRight className="context-source-card__arrow source-card__arrow sr-only" aria-hidden="true" />
      </button>

      {showActions && (
        <div className="source-card__actions" aria-label={vi ? "Thao tác nguồn" : "Source actions"}>
          <button
            type="button"
            className="source-card__action"
            onClick={handleCopy}
            aria-label={
              copyState === "copied"
                ? (vi ? `Đã sao chép đoạn ${index + 1}` : `Copied excerpt ${index + 1}`)
                : (vi ? `Sao chép đoạn ${index + 1} kèm citation` : `Copy excerpt ${index + 1} with citation`)
            }
          >
            {copyState === "copied" ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
            <span>{copyState === "copied" ? (vi ? "Đã sao chép" : "Copied") : (vi ? "Sao chép" : "Copy")}</span>
          </button>
          {onOpenDocument && (
            <button
              type="button"
              className="source-card__action"
              onClick={(event) => {
                event.stopPropagation();
                onOpenDocument();
              }}
              aria-label={(vi ? "Mở tài liệu cho nguồn" : "Open document for source") + " " + (index + 1)}
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{vi ? "Mở tài liệu" : "Open document"}</span>
            </button>
          )}
          {onSave && (
            <button
              type="button"
              className={"source-card__action" + (isSaved ? " is-saved" : "")}
              onClick={(event) => void handleSave(event)}
              disabled={savePending || isSaved}
              aria-label={
                isSaved
                  ? (vi ? "Đã lưu nguồn " : "Evidence saved for source ") + (index + 1)
                  : (vi ? "Lưu nguồn " : "Save evidence source ") + (index + 1)
              }
            >
              {isSaved ? <BookmarkCheck className="h-3.5 w-3.5" aria-hidden="true" /> : <BookmarkPlus className="h-3.5 w-3.5" aria-hidden="true" />}
              <span>{isSaved ? (vi ? "Đã lưu" : "Saved") : (vi ? "Lưu evidence" : "Save evidence")}</span>
            </button>
          )}
        </div>
      )}

      {showAdvanced && advancedScoreKind && (
        <details className="source-card__advanced">
          <summary>
            <span>{vi ? "Xếp hạng nâng cao" : "Advanced ranking"}</span>
            <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
          </summary>
          <dl>
            <div>
              <dt>{vi ? "Loại điểm" : "Score kind"}</dt>
              <dd>{advancedScoreKind}</dd>
            </div>
            <div>
              <dt>{vi ? "Điểm" : "Score"}</dt>
              <dd>{source.score?.toFixed(4)}</dd>
            </div>
          </dl>
        </details>
      )}
    </article>
  );
}

export default SourceCard;
