import { memo } from "react";
import { Copy, FolderOpen, MessageSquarePlus } from "lucide-react";

import { formatCompanyLabel } from "../../lib/displayMetadata";
import { getSectionDisplay } from "../../lib/sourcePresentation";
import { filingYear, formatScore, itemScore, primaryHit, resultSections } from "../../lib/searchModel";
import type { DiscoveryGroup, DiscoveryGrouping, DiscoveryHit, Source } from "../../types";
import { SearchResultSnippet } from "./SearchResultSnippet";

interface SearchResultCardProps {
  item: DiscoveryGroup | DiscoveryHit;
  grouping: DiscoveryGrouping;
  /** One-based position in the whole bounded set, not in the page. */
  rank: number;
  vi: boolean;
  focusId: string;
  onUseInResearch: () => void;
  onOpenDocument?: () => void;
  onSaveEvidence?: (source: Source) => void;
}

/**
 * One discovery result: the excerpt API-004 ranked, with its canonical chunk
 * and document identity, real filing metadata, and its raw BM25 score.
 *
 * A grouped result (one filing) shows its best excerpt and how many excerpts
 * matched in that filing; the actions always act on that excerpt's identity.
 */
export const SearchResultCard = memo(function SearchResultCard({
  item,
  grouping,
  rank,
  vi,
  focusId,
  onUseInResearch,
  onOpenDocument,
  onSaveEvidence,
}: SearchResultCardProps) {
  const hit = primaryHit(item, grouping);
  const score = itemScore(item, grouping);
  const sections = resultSections(item, grouping);
  const year = filingYear(item.filing_date);
  const hitCount = grouping === "document" ? (item as DiscoveryGroup).hit_count : 0;
  const sectionLabel = sections.length > 0 ? getSectionDisplay("", sections[0]).section : null;

  const source: Source | null = hit
    ? {
        citation: `${item.ticker ?? "SEC"} indexed excerpt · ${sections[0] ?? "Unknown section"}`,
        text_preview: hit.snippet.text,
        text: hit.snippet.text,
        chunk_id: hit.chunk_id,
        document_id: item.document_id,
        ticker: item.ticker,
        section: sections[0] ?? null,
        filing_date: item.filing_date,
        report_date: item.report_date,
        chunk_index: hit.chunk_index,
        score,
        score_kind: "retrieval",
      }
    : null;

  return (
    <article className="console-result search-result" aria-labelledby={`${focusId}-title`}>
      <span className="console-result__rank" aria-hidden="true">{rank}</span>
      <div className="console-result__body">
        <div className="console-result__meta">
          <span className="console-chip">{item.ticker ? formatCompanyLabel(item.ticker) : "SEC filing"}</span>
          {item.ticker && <span className="console-chip">{item.ticker}</span>}
          {year != null && <span className="console-chip">{year}</span>}
          {/* The heading is the best excerpt's section, so only the group's
              further sections appear as chips. */}
          {sections.slice(1, 3).map((section) => (
            <span key={section} className="console-chip">{getSectionDisplay("", section).section}</span>
          ))}
          {hitCount > 1 && (
            <span className="console-chip">
              {vi ? `${hitCount} đoạn khớp` : `${hitCount} matching excerpts`}
            </span>
          )}
          {/* The raw BM25 score is a ranking signal: it is labelled as a score,
              never as a confidence, a probability, or a percentage. */}
          <span className="search-score" title={vi ? "Điểm xếp hạng BM25 (tín hiệu xếp hạng)" : "BM25 ranking score (a ranking signal)"}>
            <span className="search-score__value">{formatScore(score)}</span>
            <span className="search-score__label">BM25</span>
          </span>
        </div>
        <h3 id={`${focusId}-title`} className="console-result__title">
          {sectionLabel ?? (vi ? "Đoạn đã lập chỉ mục" : "Indexed excerpt")}
        </h3>
        {hit && <SearchResultSnippet snippet={hit.snippet} />}
        <div className="console-result__actions">
          <button type="button" className="console-btn" onClick={onUseInResearch}>
            <MessageSquarePlus aria-hidden="true" />
            {vi ? "Dùng trong Research" : "Use in Research"}
          </button>
          {onOpenDocument && hit ? (
            <button id={focusId} type="button" className="console-btn" aria-label="Open document workspace" onClick={onOpenDocument}>
              <FolderOpen aria-hidden="true" />
              {vi ? "Mở tài liệu" : "Open Document"}
            </button>
          ) : null}
          {onSaveEvidence && source && (
            <button type="button" className="console-btn" aria-label="Save evidence" onClick={() => onSaveEvidence(source)}>
              <Copy aria-hidden="true" />
              {vi ? "Lưu evidence" : "Save as Evidence"}
            </button>
          )}
        </div>
      </div>
    </article>
  );
});
