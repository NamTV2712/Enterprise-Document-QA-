import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw, Search, SearchX, ShieldAlert } from "lucide-react";

import { createDiscoverySearch, getDiscoverySnapshot } from "../../lib/api";
import { useLocale } from "../../lib/i18n";
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  describeDiscoveryError,
  pageRangeLabel,
  readRecentSearches,
  rememberRecentSearch,
  scopeSummary,
  submittableQuery,
  type DiscoveryErrorInfo,
  type RecentSearch,
} from "../../lib/searchModel";
import { formatCompanyLabel } from "../../lib/displayMetadata";
import { getSectionDisplay } from "../../lib/sourcePresentation";
import { SelectField } from "../ui/SelectField";
import type {
  CatalogFacet,
  DiscoveryGroup,
  DiscoveryGrouping,
  DiscoveryHit,
  DiscoverySnapshotResponse,
  SearchWorkspaceTarget,
  Source,
} from "../../types";
import { SearchQueryCard, type SearchFilterDraft } from "./SearchQueryCard";
import { SearchRail } from "./SearchRail";
import { SearchResultCard } from "./SearchResultCard";

export interface DiscoverySearchPageProps {
  tickers?: string[];
  sections?: string[];
  isBackendConnected: boolean | null;
  onUseQuestion: (question: string, scope?: { ticker: string | null; section: string | null }) => void;
  onOpenDocument?: (target: SearchWorkspaceTarget) => void;
  onOpenSource?: (source: Source, returnFocusId?: string) => void;
  onSaveEvidence?: (source: Source) => void;
}

const EMPTY_FILTERS: SearchFilterDraft = { ticker: "", section: "", year: "" };

function focusId(chunkId: string | null, documentId: string): string {
  const identity = chunkId ?? documentId;
  return `search-document-workspace-${identity.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

function sameFilters(left: SearchFilterDraft, right: SearchFilterDraft): boolean {
  return left.ticker === right.ticker && left.section === right.section && left.year === right.year;
}

/**
 * Discovery Search.
 *
 * One submitted search creates exactly one API-004 snapshot. Paging, the page
 * size, opening a result, and every purely visual change read from that same
 * snapshot; only a newly committed query, filter scope, or grouping POSTs
 * again. The query and scope on screen are always the snapshot's own, so the
 * results can never be relabelled by unsubmitted typing.
 */
export function DiscoverySearchPage({
  tickers = [],
  sections = [],
  isBackendConnected,
  onUseQuestion,
  onOpenDocument,
  onOpenSource,
  onSaveEvidence,
}: DiscoverySearchPageProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";

  const [draft, setDraft] = useState("");
  const [filters, setFilters] = useState<SearchFilterDraft>(EMPTY_FILTERS);
  const [snapshot, setSnapshot] = useState<DiscoverySnapshotResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPaging, setIsPaging] = useState(false);
  const [error, setError] = useState<DiscoveryErrorInfo | null>(null);
  const [recents, setRecents] = useState<RecentSearch[]>(() => readRecentSearches());

  const pageSize = snapshot?.page_size ?? DEFAULT_PAGE_SIZE;
  const grouping: DiscoveryGrouping = snapshot?.grouping.group_by ?? "document";
  const page = snapshot?.page ?? 1;

  // Request identity guards: a late response from an earlier submission can
  // never replace the snapshot a reader is looking at.
  const searchRequestId = useRef(0);
  const pageRequestId = useRef(0);
  const searchController = useRef<AbortController | null>(null);
  const pageController = useRef<AbortController | null>(null);

  useEffect(() => () => {
    searchRequestId.current += 1;
    pageRequestId.current += 1;
    searchController.current?.abort();
    pageController.current?.abort();
  }, []);

  const submittedQuery = snapshot?.query.text ?? "";
  const submittedFilters: SearchFilterDraft = {
    ticker: snapshot?.scope.ticker ?? "",
    section: snapshot?.scope.section ?? "",
    year: snapshot?.scope.year != null ? String(snapshot.scope.year) : "",
  };
  const draftDiffers = Boolean(snapshot) && (draft.trim() !== submittedQuery || !sameFilters(filters, submittedFilters));
  const filtersDiffer = Boolean(snapshot) && !sameFilters(filters, submittedFilters);

  /** One committed search: exactly one POST, one snapshot. */
  const runSearch = useCallback(async (rawQuery: string, nextFilters: SearchFilterDraft, groupBy: DiscoveryGrouping) => {
    const query = submittableQuery(rawQuery);
    if (query === null || isBackendConnected === false) return;
    const requestId = ++searchRequestId.current;
    searchController.current?.abort();
    pageController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    setIsSubmitting(true);
    setIsPaging(false);
    setError(null);
    try {
      const response = await createDiscoverySearch(
        {
          query,
          group_by: groupBy,
          ticker: nextFilters.ticker || null,
          section: nextFilters.section || null,
          year: nextFilters.year ? Number(nextFilters.year) : null,
          page: 1,
          page_size: DEFAULT_PAGE_SIZE,
        },
        controller.signal,
      );
      if (requestId !== searchRequestId.current) return;
      setSnapshot(response);
      setRecents(rememberRecentSearch(response.query.text, response.total));
    } catch (reason) {
      if (requestId !== searchRequestId.current) return;
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(describeDiscoveryError(reason, vi));
    } finally {
      if (requestId === searchRequestId.current) setIsSubmitting(false);
    }
  }, [isBackendConnected, vi]);

  /** One read of an already stored snapshot: never re-runs the search. */
  const readPage = useCallback(async (nextPage: number, nextPageSize: number) => {
    const searchId = snapshot?.search_id;
    if (!searchId) return;
    const requestId = ++pageRequestId.current;
    pageController.current?.abort();
    const controller = new AbortController();
    pageController.current = controller;
    setIsPaging(true);
    setError(null);
    try {
      const response = await getDiscoverySnapshot(searchId, { page: nextPage, page_size: nextPageSize }, controller.signal);
      if (requestId !== pageRequestId.current) return;
      setSnapshot(response);
    } catch (reason) {
      if (requestId !== pageRequestId.current) return;
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(describeDiscoveryError(reason, vi));
    } finally {
      if (requestId === pageRequestId.current) setIsPaging(false);
    }
  }, [snapshot?.search_id, vi]);

  const submit = useCallback(() => {
    void runSearch(draft, filters, grouping);
  }, [draft, filters, grouping, runSearch]);

  const rerunFromRecent = useCallback((query: string) => {
    setDraft(query);
    void runSearch(query, filters, grouping);
  }, [filters, grouping, runSearch]);

  const changeGrouping = useCallback((next: DiscoveryGrouping) => {
    if (!snapshot || next === snapshot.grouping.group_by) return;
    // Grouping is part of the stored snapshot, so changing it is a new
    // committed search with the same submitted query and scope.
    void runSearch(
      snapshot.query.text,
      {
        ticker: snapshot.scope.ticker ?? "",
        section: snapshot.scope.section ?? "",
        year: snapshot.scope.year != null ? String(snapshot.scope.year) : "",
      },
      next,
    );
  }, [runSearch, snapshot]);

  const retry = useCallback(() => {
    if (!snapshot) {
      void runSearch(draft, filters, grouping);
      return;
    }
    void runSearch(
      snapshot.query.text,
      {
        ticker: snapshot.scope.ticker ?? "",
        section: snapshot.scope.section ?? "",
        year: snapshot.scope.year != null ? String(snapshot.scope.year) : "",
      },
      snapshot.grouping.group_by,
    );
  }, [draft, filters, grouping, runSearch, snapshot]);

  const tickerOptions = useMemo(
    () => [
      { value: "", label: vi ? "Tất cả công ty" : "All Companies" },
      ...tickers.map((ticker) => ({ value: ticker, label: formatCompanyLabel(ticker) })),
    ],
    [tickers, vi],
  );
  const sectionOptions = useMemo(
    () => [
      { value: "", label: vi ? "Tất cả mục" : "All Sections" },
      ...sections.map((section) => ({ value: section, label: getSectionDisplay("", section).section })),
    ],
    [sections, vi],
  );
  const facetValues = useCallback(
    (dimension: CatalogFacet["dimension"]) =>
      snapshot?.facets
        .find((facet) => facet.dimension === dimension)
        ?.values.map((value) => ({ value: String(value.value), count: value.count, label: String(value.value) })) ?? [],
    [snapshot],
  );
  const yearOptions = useMemo(
    () => [
      { value: "", label: vi ? "Tất cả các năm" : "All Years" },
      ...facetValues("year").map((value) => ({ value: value.value, label: `${value.label} (${value.count})` })),
    ],
    [facetValues, vi],
  );
  const quickSections = useMemo(
    // A scope filter that cannot match any document is not offered as a chip.
    () => (snapshot ? { values: facetValues("section").filter((value) => value.count > 0) } : null),
    [facetValues, snapshot],
  );

  const items: Array<DiscoveryGroup | DiscoveryHit> = snapshot?.items ?? [];
  const rangeLabel = snapshot ? pageRangeLabel(page, pageSize, snapshot.total, grouping, vi) : "";
  const canRerun = isBackendConnected !== false && !isSubmitting;

  return (
    <section className="workspace-page workspace-page--standard search-page console-view-enter" aria-labelledby="search-title">
      <div className="console-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><Search aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="search-title" className="console-page-header__title">{vi ? "Tìm kiếm" : "Search"}</h1>
            <p className="console-page-header__subtitle">
              {vi
                ? "Tìm kiếm từ khóa trên danh mục 10-K đã lập chỉ mục — xếp hạng BM25 trên văn bản đoạn nguồn."
                : "Keyword discovery across the indexed filings — BM25 ranking over excerpt text."}
            </p>
          </div>
        </div>
      </div>

      <div className="search-layout">
        <div className="search-layout__main">
          <SearchQueryCard
            vi={vi}
            draft={draft}
            onDraftChange={setDraft}
            filters={filters}
            onFilterChange={setFilters}
            tickerOptions={tickerOptions}
            sectionOptions={sectionOptions}
            yearOptions={yearOptions}
            isSubmitting={isSubmitting}
            disabled={isBackendConnected === false}
            draftDiffers={draftDiffers}
            onSubmit={submit}
          />

          {error && (
            <div className="workspace-alert workspace-alert--error search-alert" role="alert">
              <ShieldAlert aria-hidden="true" />
              <span>{error.message}</span>
              {error.canRerun && (
                <button type="button" className="console-btn" onClick={retry}>
                  <RefreshCw aria-hidden="true" />
                  {error.kind === "expired" || error.kind === "unknown_snapshot"
                    ? (vi ? "Chạy lại tìm kiếm" : "Run the search again")
                    : (vi ? "Thử lại" : "Retry")}
                </button>
              )}
            </div>
          )}

          {snapshot && snapshot.total > 0 && (
            <div className="console-card search-results-card" aria-busy={isPaging || isSubmitting}>
              <div className="console-card__header search-results-card__header">
                <div className="min-w-0">
                  <h2 className="console-card__title">
                    {vi ? `Kết quả cho "${submittedQuery}"` : `Results for “${submittedQuery}”`}
                  </h2>
                  <p className="console-card__subtitle" aria-live="polite">
                    {rangeLabel} · {vi ? "phạm vi" : "scope"}: {scopeSummary(snapshot.scope, vi)}
                  </p>
                </div>
                <div className="search-results-card__controls">
                  {filtersDiffer && (
                    <span className="console-chip search-chip--pending">
                      {vi ? "Bộ lọc mới sẽ áp dụng ở lần tìm kế tiếp" : "New filters apply on the next search"}
                    </span>
                  )}
                  <span className="console-chip" title={snapshot.engine.definition}>
                    {vi ? "Xếp hạng" : "Ranked by"} {snapshot.engine.key} {snapshot.engine.version}
                  </span>
                  <label className="search-switch">
                    <input
                      type="checkbox"
                      checked={grouping === "document"}
                      onChange={(event) => changeGrouping(event.target.checked ? "document" : "chunk")}
                    />
                    <span>{vi ? "Nhóm theo hồ sơ" : "Group by filing"}</span>
                  </label>
                  <SelectField
                    className="console-header-select"
                    label={vi ? "Số dòng mỗi trang" : "Rows per page"}
                    value={String(pageSize)}
                    options={PAGE_SIZE_OPTIONS.map((size) => ({ value: String(size), label: `${size} ${vi ? "/ trang" : "per page"}` }))}
                    onValueChange={(value) => void readPage(1, Number(value))}
                  />
                </div>
              </div>

              {snapshot.scope.limited_by_ceiling && (
                <p className="search-results-card__bounded">
                  {vi
                    ? `Discovery chỉ chấm ${snapshot.scope.candidate_ceiling} ứng viên đầu tiên, nên con số trên là giới hạn khám phá, không phải tổng toàn danh mục; có thể còn kết quả khớp khác.`
                    : `Discovery ranked the first ${snapshot.scope.candidate_ceiling} candidates, so this is a bounded discovery count rather than a corpus total; further matches may exist.`}
                </p>
              )}

              <div className="console-card__body search-results-card__body">
                {items.map((item, index) => {
                  const hit = grouping === "document" ? (item as DiscoveryGroup).hits[0] : (item as DiscoveryHit);
                  const identity = hit?.chunk_id ?? null;
                  const cardFocusId = focusId(identity, item.document_id);
                  const rank = (page - 1) * pageSize + index + 1;
                  return (
                    <SearchResultCard
                      key={grouping === "document" ? item.document_id : (item as DiscoveryHit).chunk_id}
                      item={item}
                      grouping={grouping}
                      rank={rank}
                      vi={vi}
                      focusId={cardFocusId}
                      onUseInResearch={() => onUseQuestion(snapshot.query.text, {
                        ticker: item.ticker ?? (submittedFilters.ticker || null),
                        section: (grouping === "document" ? (item as DiscoveryGroup).sections[0] : (item as DiscoveryHit).section) ?? (submittedFilters.section || null),
                      })}
                      onOpenDocument={onOpenDocument ? () => onOpenDocument({
                        kind: "search",
                        documentId: item.document_id,
                        selectedSource: hit ? {
                          citation: `${item.ticker ?? "SEC"} indexed excerpt · ${hit.section ?? "Unknown section"}`,
                          text_preview: hit.snippet.text,
                          text: hit.snippet.text,
                          chunk_id: hit.chunk_id,
                          document_id: item.document_id,
                          ticker: item.ticker,
                          section: hit.section,
                          filing_date: item.filing_date,
                          report_date: item.report_date,
                          chunk_index: hit.chunk_index,
                          score: hit.score,
                          score_kind: "retrieval",
                        } : undefined,
                        initialTab: "document",
                        returnView: "search",
                        returnFocusId: cardFocusId,
                      }) : undefined}
                      onSaveEvidence={onSaveEvidence}
                    />
                  );
                })}
                {isPaging && (
                  <div className="console-loading py-3">
                    <span className="console-loading__spinner" aria-hidden="true" />
                    {vi ? "Đang tải trang kết quả…" : "Loading the next page…"}
                  </div>
                )}
              </div>

              <div className="console-card__footer search-results-card__footer">
                <span className="text-xs text-[var(--text-muted)]">{rangeLabel}</span>
                <nav className="console-pager" aria-label={vi ? "Phân trang kết quả" : "Search result pagination"}>
                  <button
                    type="button"
                    className="console-pager__page"
                    disabled={page <= 1 || isPaging}
                    onClick={() => void readPage(page - 1, pageSize)}
                    aria-label={vi ? "Trang trước" : "Previous page"}
                  >
                    {vi ? "Trước" : "Previous"}
                  </button>
                  <span className="console-pager__gap" aria-hidden="true">
                    {vi ? `Trang ${page} / ${Math.max(1, Math.ceil(snapshot.total / pageSize))}` : `Page ${page} of ${Math.max(1, Math.ceil(snapshot.total / pageSize))}`}
                  </span>
                  <button
                    type="button"
                    className="console-pager__page"
                    disabled={page >= Math.max(1, Math.ceil(snapshot.total / pageSize)) || isPaging}
                    onClick={() => void readPage(page + 1, pageSize)}
                    aria-label={vi ? "Trang sau" : "Next page"}
                  >
                    {vi ? "Sau" : "Next"}
                  </button>
                </nav>
              </div>
            </div>
          )}

          {snapshot && snapshot.total === 0 && (
            <div className="console-card search-empty">
              <div className="console-empty">
                <SearchX aria-hidden="true" />
                <strong>
                  {vi
                    ? `Không có kết quả cho "${snapshot.query.text}"`
                    : `No matches for “${snapshot.query.text}”`}
                </strong>
                <p>
                  {snapshot.scope.documents > 0
                    ? (vi
                        ? `Đã tìm trong ${snapshot.scope.documents} hồ sơ thuộc phạm vi ${scopeSummary(snapshot.scope, vi)}.`
                        : `Searched ${snapshot.scope.documents} filings in scope ${scopeSummary(snapshot.scope, vi)}.`)
                    : (vi
                        ? `Không có hồ sơ nào trong phạm vi ${scopeSummary(snapshot.scope, vi)}.`
                        : `No filings exist in scope ${scopeSummary(snapshot.scope, vi)}.`)}
                </p>
                <p className="search-empty__hint">
                  {vi
                    ? "Thử từ khóa khác, hoặc nới bộ lọc rồi chạy lại tìm kiếm."
                    : "Try other words, or widen the filters and run the search again."}
                </p>
              </div>
            </div>
          )}

          {!snapshot && !error && (
            <div className="console-card search-empty">
              <div className="console-empty">
                <Search aria-hidden="true" />
                <strong>{vi ? "Bắt đầu bằng một truy vấn từ khóa" : "Start with a keyword query"}</strong>
                <p>
                  {vi
                    ? "Kết quả là các đoạn nguồn thật trong danh mục đã lập chỉ mục, kèm trích dẫn và điểm xếp hạng BM25."
                    : "Results are real excerpts from the indexed catalog, with their citations and BM25 ranking scores."}
                </p>
              </div>
            </div>
          )}
        </div>

        <SearchRail
          vi={vi}
          snapshot={snapshot}
          filters={filters}
          tickerOptions={tickerOptions}
          sectionOptions={sectionOptions}
          yearOptions={yearOptions}
          onFilterChange={setFilters}
          quickSections={quickSections}
          recents={recents}
          onRerun={rerunFromRecent}
          canRerun={canRerun}
        />
      </div>
    </section>
  );
}
