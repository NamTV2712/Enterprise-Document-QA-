import { memo } from "react";
import { Building2, Clock3, Database, FileSearch, Layers, Target } from "lucide-react";

import { getSectionDisplay } from "../../lib/sourcePresentation";
import {
  formatScore,
  relativeSearchTime,
  scopeSummary,
  topScore,
  type RecentSearch,
} from "../../lib/searchModel";
import { SelectField } from "../ui/SelectField";
import type { CatalogFacet, DiscoveryGrouping, DiscoverySnapshotResponse } from "../../types";
import type { SearchFilterDraft } from "./SearchQueryCard";

interface SearchRailProps {
  vi: boolean;
  snapshot: DiscoverySnapshotResponse | null;
  filters: SearchFilterDraft;
  tickerOptions: Array<{ value: string; label: string }>;
  sectionOptions: Array<{ value: string; label: string }>;
  yearOptions: Array<{ value: string; label: string }>;
  onFilterChange: (next: SearchFilterDraft) => void;
  /** Section quick scopes taken from the snapshot's own section facet. */
  quickSections: CatalogFacetValues;
  recents: RecentSearch[];
  onRerun: (query: string) => void;
  canRerun: boolean;
}

type CatalogFacetValues = { values: Array<{ value: string; count: number }> } | null;

function facetValues(snapshot: DiscoverySnapshotResponse | null, dimension: CatalogFacet["dimension"]): CatalogFacetValues {
  const facet = snapshot?.facets.find((candidate) => candidate.dimension === dimension);
  if (!facet) return null;
  return { values: facet.values.map((value) => ({ value: String(value.value), count: value.count })) };
}

/**
 * The Search rail: what this snapshot actually measured, the scope filters a
 * reader can refine next, and the queries this browser already ran.
 *
 * Every count here is API-003's scope count (documents in the current scope),
 * labelled as such, because it is not a match count; and every filter change
 * is a draft that applies on the next submitted search, never a silent
 * re-scoping of the snapshot on screen.
 */
export const SearchRail = memo(function SearchRail({
  vi,
  snapshot,
  filters,
  tickerOptions,
  sectionOptions,
  yearOptions,
  onFilterChange,
  quickSections,
  recents,
  onRerun,
  canRerun,
}: SearchRailProps) {
  const grouping: DiscoveryGrouping = snapshot?.grouping.group_by ?? "document";
  const sections = quickSections?.values ?? [];
  const companyCount = facetValues(snapshot, "company")?.values.length ?? null;
  const best = snapshot ? topScore(snapshot.items, grouping) : null;

  return (
    <aside className="search-rail" aria-label={vi ? "Tổng quan tìm kiếm" : "Search overview"}>
      <section className="console-card">
        <div className="console-card__header">
          <h2 className="console-card__title">{vi ? "Tổng quan tìm kiếm" : "Search Overview"}</h2>
        </div>
        <div className="console-card__body search-rail__metrics">
          {snapshot ? (
            <>
              <div className="console-stat">
                <div className="console-stat__icon"><Building2 aria-hidden="true" /></div>
                <div className="min-w-0">
                  <div className="console-stat__value">{companyCount ?? "—"}</div>
                  <div className="console-stat__label">{vi ? "Công ty trong phạm vi" : "Companies in scope"}</div>
                  <div className="console-stat__hint">{snapshot.scope.ticker ?? (vi ? "Toàn bộ danh mục" : "Whole catalog")}</div>
                </div>
              </div>
              <div className="console-stat">
                <div className="console-stat__icon"><FileSearch aria-hidden="true" /></div>
                <div className="min-w-0">
                  <div className="console-stat__value">{snapshot.total.toLocaleString(vi ? "vi-VN" : "en-US")}</div>
                  <div className="console-stat__label">{vi ? "Hồ sơ khớp" : "Result filings"}</div>
                  {/* The other unit of the same bounded set, so the page range
                      stays in the results toolbar where a reader looks for it. */}
                  <div className="console-stat__hint">
                    {grouping === "document"
                      ? (vi ? `Trên ${snapshot.scope.matched_chunks} đoạn nguồn khớp` : `Across ${snapshot.scope.matched_chunks} matching excerpts`)
                      : (vi ? `Trên ${snapshot.scope.matched_documents} hồ sơ` : `Across ${snapshot.scope.matched_documents} filings`)}
                  </div>
                </div>
              </div>
              <div className="console-stat">
                <div className="console-stat__icon"><Database aria-hidden="true" /></div>
                <div className="min-w-0">
                  <div className="console-stat__value">{snapshot.scope.matched_chunks.toLocaleString(vi ? "vi-VN" : "en-US")}</div>
                  <div className="console-stat__label">{vi ? "Đoạn nguồn khớp" : "Matching excerpts"}</div>
                  <div className="console-stat__hint">
                    {snapshot.scope.limited_by_ceiling
                      ? (vi ? `Giới hạn ${snapshot.scope.candidate_ceiling} ứng viên` : `Capped at ${snapshot.scope.candidate_ceiling} candidates`)
                      : (vi ? "Đã chấm toàn bộ ứng viên" : "Every candidate ranked")}
                  </div>
                </div>
              </div>
              <div className="console-stat">
                <div className="console-stat__icon console-stat__icon--success"><Target aria-hidden="true" /></div>
                <div className="min-w-0">
                  <div className="console-stat__value">{best != null ? formatScore(best) : "—"}</div>
                  <div className="console-stat__label">{vi ? "Điểm BM25 cao nhất" : "Top BM25 score"}</div>
                  <div className="console-stat__hint">{snapshot.engine.key} {snapshot.engine.version}</div>
                </div>
              </div>
            </>
          ) : (
            <p className="search-rail__placeholder">
              {vi
                ? "Chạy một tìm kiếm để xem số liệu thật của phạm vi và kết quả."
                : "Run a search to see the real scope and result counts."}
            </p>
          )}
        </div>
      </section>

      <section className="console-card">
        <div className="console-card__header">
          <div className="min-w-0">
            <h2 className="console-card__title">{vi ? "Tinh chỉnh tìm kiếm" : "Refine Search"}</h2>
            <p className="console-card__subtitle">
              {vi ? "Áp dụng cho lần tìm kiếm kế tiếp" : "Applies on the next search"}
            </p>
          </div>
        </div>
        <div className="console-card__body search-rail__refine">
          {sections.length > 0 && (
            <div>
              <p className="search-rail__legend">
                {vi
                  ? `Mục trong phạm vi (${snapshot?.scope.documents ?? 0} hồ sơ)`
                  : `Sections in scope (${snapshot?.scope.documents ?? 0} filings)`}
              </p>
              <div className="search-rail__chips">
                {sections.map((section) => {
                  const active = filters.section === section.value;
                  return (
                    <button
                      key={section.value}
                      type="button"
                      className={`console-chip console-chip--toggle ${active ? "console-chip--active" : ""}`}
                      aria-pressed={active}
                      onClick={() => onFilterChange({ ...filters, section: active ? "" : section.value })}
                    >
                      {getSectionDisplay("", section.value).section}
                      <span className="search-rail__chip-count">{section.count}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
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
          {/* The engine's own definition is reachable here rather than implied
              by the score pill, so ranking semantics stay inspectable. */}
          <details className="search-rail__engine">
            <summary>{vi ? "Cách xếp hạng hoạt động" : "How ranking works"}</summary>
            <p className="search-rail__engine-text">
              {snapshot?.engine.definition
                ?? (vi
                  ? "Kết quả tìm kiếm dùng điểm BM25 từ khóa trên văn bản đoạn nguồn đã lập chỉ mục."
                  : "Discovery ranks indexed excerpt text with a lexical BM25 score.")}
            </p>
            {snapshot && (
              <p className="search-rail__engine-scope">
                {vi ? "Phạm vi hiện tại" : "Current scope"}: {scopeSummary(snapshot.scope, vi)}
              </p>
            )}
          </details>
        </div>
      </section>

      <section className="console-card">
        <div className="console-card__header">
          <div className="min-w-0">
            <h2 className="console-card__title">{vi ? "Tìm kiếm gần đây" : "Recent Searches"}</h2>
            <p className="console-card__subtitle">{vi ? "Lưu cục bộ trong trình duyệt này" : "Stored locally in this browser"}</p>
          </div>
        </div>
        <div className="console-card__body">
          {recents.length === 0 ? (
            <p className="search-rail__placeholder">
              {vi ? "Chưa có tìm kiếm nào trong trình duyệt này." : "No searches in this browser yet."}
            </p>
          ) : (
            <ul className="search-recent">
              {recents.map((recent) => (
                <li key={`${recent.query}-${recent.at}`} className="search-recent__item">
                  <button
                    type="button"
                    className="search-recent__button"
                    onClick={() => onRerun(recent.query)}
                    disabled={!canRerun}
                  >
                    <Clock3 aria-hidden="true" />
                    <span className="search-recent__body">
                      <span className="search-recent__query">{recent.query}</span>
                      <span className="search-recent__meta">
                        {recent.results != null
                          ? `${recent.results.toLocaleString(vi ? "vi-VN" : "en-US")} ${vi ? "hồ sơ" : "filings"} · `
                          : ""}
                        {relativeSearchTime(recent.at, Date.now(), vi)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </aside>
  );
});
