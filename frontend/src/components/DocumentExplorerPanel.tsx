import { memo, useEffect, useMemo, useRef, useState } from "react";
import {
  Boxes,
  Building2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleSlash2,
  Copy,
  Database,
  ExternalLink,
  FileText,
  FolderOpen,
  RefreshCw,
  Search,
  SearchX,
  X,
  XCircle,
} from "lucide-react";
import { getDocumentChunks, getDocumentFacets, getDocuments, getDocumentStats, getReaderManifest } from "../lib/api";
import {
  CatalogWorkspaceTarget,
  DocumentChunk,
  DocumentFacetsResponse,
  DocumentRow,
  DocumentSortField,
  DocumentStatsResponse,
  ReaderManifest,
  Source,
} from "../types";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";
import { SelectField } from "./ui/SelectField";
import { formatCompanyLabel } from "../lib/displayMetadata";
import { sanitizeSecBrowserUrl } from "../lib/secUrls";
import { getSectionDisplay } from "../lib/sourcePresentation";

interface DocumentExplorerPanelProps {
  tickers: string[];
  sections: string[];
  companyCount?: number | null;
  chunkCount?: number | null;
  onOpenDocument?: (target: CatalogWorkspaceTarget) => void;
  onOpenSource?: (source: Source) => void;
  onSaveEvidence?: (source: Source) => void;
}

const DEFAULT_PAGE_SIZE = 10;
const PAGE_SIZE_OPTIONS = [10, 20, 50];
const SEARCH_DEBOUNCE_MS = 250;
const MAX_SHARED_DOCUMENT_CACHE_ENTRIES = 32;

/** Catalog sort options; every one maps to an API-003 supported field. */
const SORT_OPTIONS: Array<{ value: DocumentSortField; label: string; direction: "asc" | "desc" }> = [
  { value: "filing_date", label: "Filing date (newest)", direction: "desc" },
  { value: "filing_date", label: "Filing date (oldest)", direction: "asc" },
  { value: "ticker", label: "Ticker (A-Z)", direction: "asc" },
  { value: "chunk_count", label: "Chunks (most)", direction: "desc" },
];

type DocumentCacheEntry = { items: DocumentRow[]; total: number };
type DetailsTab = "overview" | "sections" | "representations" | "metadata";

function rememberDocumentCache(cache: Map<string, DocumentCacheEntry>, key: string, entry: DocumentCacheEntry): void {
  cache.delete(key);
  cache.set(key, entry);
  while (cache.size > MAX_SHARED_DOCUMENT_CACHE_ENTRIES) {
    const oldest = cache.keys().next().value;
    if (oldest === undefined) break;
    cache.delete(oldest);
  }
}

function useDebouncedValue(value: string): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), SEARCH_DEBOUNCE_MS);
    return () => window.cancelAnimationFrame(timer);
  }, [value]);
  return debounced;
}

function focusId(documentId: string): string {
  return `document-workspace-${documentId.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

function chunkFocusId(documentId: string, chunkId: string | null): string {
  return `${focusId(documentId)}-excerpt-${(chunkId ?? "unknown").replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

function pagerItems(current: number, count: number): Array<number | "gap"> {
  if (count <= 7) return Array.from({ length: count }, (_, index) => index + 1);
  const pages = new Set<number>([1, count, current - 1, current, current + 1]);
  const ordered = [...pages].filter((page) => page >= 1 && page <= count).sort((a, b) => a - b);
  const items: Array<number | "gap"> = [];
  let previous = 0;
  for (const page of ordered) {
    if (page - previous > 1) items.push("gap");
    items.push(page);
    previous = page;
  }
  return items;
}

function tickerInitials(ticker: string | null): string {
  return (ticker ?? "SEC").slice(0, 4).toUpperCase();
}

function shortId(value: string): string {
  return value.length > 18 ? `${value.slice(0, 15)}…` : value;
}

/**
 * Append API-003's own count to a facet option label. A facet that is not
 * readable yet keeps its plain label rather than a fabricated count.
 */
function facetLabel(
  label: string,
  counts: Map<string, Map<string, number>>,
  dimension: string,
  value: string,
): string {
  const count = counts.get(dimension)?.get(value);
  return typeof count === "number" ? `${label} (${count})` : label;
}

export const DocumentExplorerPanel = memo(function DocumentExplorerPanel({
  tickers,
  sections,
  companyCount,
  chunkCount,
  onOpenDocument,
  onOpenSource,
  onSaveEvidence,
}: DocumentExplorerPanelProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [search, setSearch] = useState("");
  const [ticker, setTicker] = useState("");
  const [section, setSection] = useState("");
  const [year, setYear] = useState("");
  const [sortOption, setSortOption] = useState(() => SORT_OPTIONS[0].label);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [page, setPage] = useState(1);
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [total, setTotal] = useState(0);
  const [unfilteredTotal, setUnfilteredTotal] = useState<number | null>(null);
  const [stats, setStats] = useState<DocumentStatsResponse | null>(null);
  const [statsUnavailable, setStatsUnavailable] = useState(false);
  const [facets, setFacets] = useState<DocumentFacetsResponse | null>(null);
  const [selected, setSelected] = useState<DocumentRow | null>(null);
  const [detailsTab, setDetailsTab] = useState<DetailsTab>("overview");
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunkSearch, setChunkSearch] = useState("");
  const [chunkPage, setChunkPage] = useState(1);
  const [manifest, setManifest] = useState<ReaderManifest | null>(null);
  const [manifestError, setManifestError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [chunkError, setChunkError] = useState<string | null>(null);
  const [requestNonce, setRequestNonce] = useState(0);
  const [chunkRequestNonce, setChunkRequestNonce] = useState(0);
  const debouncedSearch = useDebouncedValue(search);
  const debouncedChunkSearch = useDebouncedValue(chunkSearch);
  const documentCache = useRef(new Map<string, DocumentCacheEntry>());
  const chunkCache = useRef(new Map<string, DocumentChunk[]>());
  const documentRequestId = useRef(0);
  const chunkRequestId = useRef(0);
  const manifestRequestId = useRef(0);
  const selectedSort = SORT_OPTIONS.find((option) => option.label === sortOption) ?? SORT_OPTIONS[0];
  const hasActiveFilters = Boolean(debouncedSearch.trim() || ticker || section || year);

  // API-003 owns catalog statistics; the panel never computes its own totals.
  useEffect(() => {
    const controller = new AbortController();
    setStatsUnavailable(false);
    void getDocumentStats(controller.signal)
      .then((response) => {
        setStats(response);
        setStatsUnavailable(false);
      })
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setStats(null);
        setStatsUnavailable(true);
      });
    return () => controller.abort();
  }, [requestNonce]);

  // Facet counts come from API-003 with its documented basis: every facet
  // counts the applied filters except its own dimension.
  useEffect(() => {
    const controller = new AbortController();
    void getDocumentFacets(
      {
        ticker: ticker || null,
        section: section || null,
        year: year ? Number(year) : null,
        search: debouncedSearch || undefined,
      },
      controller.signal,
    )
      .then((response) => setFacets(response))
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setFacets(null);
      });
    return () => controller.abort();
  }, [debouncedSearch, section, ticker, year, requestNonce]);

  useEffect(() => {
    const controller = new AbortController();
    const requestId = ++documentRequestId.current;
    const cacheKey = JSON.stringify({
      ticker,
      section,
      year,
      search: debouncedSearch,
      page,
      pageSize,
      sort: selectedSort.value,
      direction: selectedSort.direction,
    });
    const cached = documentCache.current.get(cacheKey);
    if (cached) {
      setDocuments(cached.items);
      setTotal(cached.total);
      setIsLoading(false);
      setListError(null);
      return () => controller.abort();
    }
    setIsLoading(true);
    setListError(null);
    void getDocuments(
      {
        ticker: ticker || null,
        section: section || null,
        year: year ? Number(year) : null,
        search: debouncedSearch,
        sort: selectedSort.value,
        direction: selectedSort.direction,
        page,
        page_size: pageSize,
      },
      controller.signal,
    )
      .then((response) => {
        if (requestId !== documentRequestId.current) return;
        rememberDocumentCache(documentCache.current, cacheKey, { items: response.items, total: response.total });
        setDocuments(response.items);
        setTotal(response.total);
        if (!hasActiveFilters) setUnfilteredTotal(response.total);
      })
      .catch((reason) => {
        if (requestId !== documentRequestId.current) return;
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setListError(describeRequestError(reason, vi ? "Không thể tải tài liệu." : "Could not load documents.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (requestId === documentRequestId.current) setIsLoading(false);
      });
    return () => controller.abort();
    // hasActiveFilters and selectedSort are derived from the same values in
    // this dependency list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, debouncedSearch, section, selectedSort.label, sortOption, ticker, year, requestNonce]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    const requestId = ++chunkRequestId.current;
    const cacheKey = JSON.stringify({ documentId: selected.document_id, search: debouncedChunkSearch, page: chunkPage });
    const cached = chunkCache.current.get(cacheKey);
    if (cached) {
      setChunks(cached);
      setIsLoadingChunks(false);
      return () => controller.abort();
    }
    setIsLoadingChunks(true);
    setChunkError(null);
    void getDocumentChunks(selected.document_id, { search: debouncedChunkSearch, page: chunkPage, page_size: 8 }, controller.signal)
      .then((response) => {
        if (requestId !== chunkRequestId.current) return;
        chunkCache.current.set(cacheKey, response.items);
        setChunks(response.items);
      })
      .catch((reason) => {
        if (requestId !== chunkRequestId.current) return;
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setChunkError(describeRequestError(reason, vi ? "Không thể tải đoạn nguồn." : "Could not load document excerpts.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (requestId === chunkRequestId.current) setIsLoadingChunks(false);
      });
    return () => controller.abort();
  }, [chunkPage, debouncedChunkSearch, selected?.document_id, chunkRequestNonce]);

  useEffect(() => {
    if (!selected) {
      setManifest(null);
      setManifestError(null);
      return;
    }
    const controller = new AbortController();
    const requestId = ++manifestRequestId.current;
    setManifest(null);
    setManifestError(null);
    void getReaderManifest(selected.document_id, controller.signal)
      .then((response) => {
        if (requestId !== manifestRequestId.current) return;
        setManifest(response);
      })
      .catch((reason) => {
        if (requestId !== manifestRequestId.current) return;
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setManifestError(describeRequestError(reason, vi ? "Không thể tải trạng thái biểu diễn." : "Could not load representation availability.", vi ? "vi" : "en").message);
      });
    return () => controller.abort();
  }, [selected?.document_id, vi]);

  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  /** Filter option lists carry API-003's own counts when the facets are readable. */
  const facetCounts = useMemo(() => {
    const counts = new Map<string, Map<string, number>>();
    for (const facet of facets?.facets ?? []) {
      counts.set(
        facet.dimension,
        new Map(facet.values.map((value) => [String(value.value), value.count])),
      );
    }
    return counts;
  }, [facets]);

  const tickerOptions = useMemo(
    () => [
      { value: "", label: vi ? "Tất cả công ty" : "All Companies" },
      ...tickers.map((item) => ({ value: item, label: facetLabel(formatCompanyLabel(item), facetCounts, "company", item) })),
    ],
    [tickers, vi, facetCounts],
  );
  const sectionOptions = useMemo(
    () => [
      { value: "", label: vi ? "Tất cả mục" : "All Sections" },
      ...sections.map((item) => ({ value: item, label: facetLabel(getSectionDisplay("", item).section, facetCounts, "section", item) })),
    ],
    [sections, vi, facetCounts],
  );
  // A year list is only offered once API-003 reports the dimension as
  // recorded; an empty select would be a control with nothing behind it.
  const yearOptions = useMemo(() => {
    const values = facets?.facets.find((facet) => facet.dimension === "year")?.values ?? [];
    if (values.length === 0) return [];
    return [
      { value: "", label: vi ? "Tất cả các năm" : "All Years" },
      ...values.map((value) => ({ value: String(value.value), label: facetLabel(String(value.value), facetCounts, "year", String(value.value)) })),
    ];
  }, [facets, vi, facetCounts]);
  const sortOptions = useMemo(
    () => SORT_OPTIONS.map((option) => ({ value: option.label, label: option.label })),
    [],
  );
  const pageSizeOptions = useMemo(
    () => PAGE_SIZE_OPTIONS.map((size) => ({ value: String(size), label: vi ? `${size} / trang` : `${size} per page` })),
    [vi],
  );
  const rangeLabel = useMemo(() => {
    if (total === 0) {
      return hasActiveFilters
        ? (vi ? "Không tìm thấy tài liệu phù hợp" : "No matching documents")
        : (vi ? "Không có tài liệu" : "No documents");
    }
    const start = (page - 1) * pageSize + 1;
    const end = Math.min(page * pageSize, total);
    return vi ? `${start}–${end} trên ${total} tài liệu` : `Showing ${start}–${end} of ${total} documents`;
  }, [hasActiveFilters, page, pageSize, total, vi]);

  const listStatusLabel = isLoading
    ? (vi ? "Đang tải…" : "Loading…")
    : listError
      ? (vi ? "Không khả dụng" : "Unavailable")
      : rangeLabel;

  const selectDocument = (document: DocumentRow) => {
    if (selected?.document_id === document.document_id) return;
    setSelected(document);
    setChunkPage(1);
    setChunkSearch("");
    setDetailsTab("overview");
  };

  const openWorkspace = (document: DocumentRow, selectedSource?: Source, initialTab?: "excerpt", returnId?: string) => {
    onOpenDocument?.({
      kind: "catalog",
      documentId: document.document_id,
      title: `${document.ticker ? formatCompanyLabel(document.ticker) : "SEC filing"} · ${document.filing_date ?? "date unavailable"}`,
      ticker: document.ticker,
      filingDate: document.filing_date,
      reportDate: document.report_date,
      accessionNumber: document.accession_number,
      sourceUrl: sanitizeSecBrowserUrl(document.source_url),
      selectedSource,
      initialTab,
      returnView: "documents",
      returnFocusId: returnId ?? focusId(document.document_id),
    });
  };

  const firstPreview = chunks[0] ?? null;
  const summaryText = selected
    ? vi
      ? `Hồ sơ SEC đã index của ${selected.ticker ? formatCompanyLabel(selected.ticker) : "đơn vị đăng ký"}, nộp ngày ${selected.filing_date ?? "không rõ"}. Danh mục đã index chứa ${selected.chunk_count} đoạn nguồn trên ${selected.sections.length} mục: ${selected.sections.join(", ")}.`
      : `Indexed SEC filing for ${selected.ticker ? formatCompanyLabel(selected.ticker) : "the registrant"}, filed on ${selected.filing_date ?? "an unknown date"}. The indexed catalog contains ${selected.chunk_count} chunks across ${selected.sections.length} sections: ${selected.sections.join(", ")}.`
    : null;

  // API-003 reports the form type as unknown because no stored artifact records
  // one; the panel repeats that state instead of assuming a form type.
  const filingTypeValue = vi ? "Không rõ" : "Unknown";
  const filingTypeReason = stats?.filing_type.reason
    ?? (vi ? "Không có siêu dữ liệu nào ghi loại hồ sơ." : "No indexed metadata records a filing type.");

  const statDocuments = stats?.documents ?? unfilteredTotal ?? total;
  const statCompanies = stats?.companies ?? companyCount ?? null;
  const statChunks = stats?.chunks ?? chunkCount ?? null;
  const filingDates = stats?.filing_dates ?? null;
  const filingYearRange = filingDates && filingDates.availability === "recorded" && filingDates.earliest != null && filingDates.latest != null
    ? (filingDates.earliest === filingDates.latest ? String(filingDates.earliest) : `${filingDates.earliest}–${filingDates.latest}`)
    : null;
  const unfilteredHint = statsUnavailable
    ? (vi ? "Thống kê danh mục không khả dụng" : "Catalog statistics unavailable")
    : filingYearRange
      ? (vi ? `Năm nộp ${filingYearRange}` : `Filing years ${filingYearRange}`)
      : (vi ? "Trong danh mục đã index" : "In the indexed catalog");

  const representationCards = useMemo(() => {
    if (!manifest) return [];
    return manifest.representations.map((representation) => ({
      kind: representation.kind,
      label: representation.kind === "structured" ? "Structured" : representation.kind === "normalized_text" ? "Normalized" : "PDF",
      status: representation.status,
      coverage: representation.coverage_status ?? null,
      reason: representation.reason,
    }));
  }, [manifest]);

  const detailOpenDisabled = !onOpenDocument;

  return (
    <section className="workspace-page workspace-page--standard document-explorer console-view-enter" aria-labelledby="document-explorer-title">
      <div className="console-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><FileText aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="document-explorer-title" className="console-page-header__title">{vi ? "Tài liệu" : "Documents"}</h1>
            <p className="console-page-header__subtitle">
              {vi
                ? "Duyệt, tìm và quản lý danh mục filing SEC đã index."
                : "Browse and search the indexed catalog of SEC filings."}
            </p>
          </div>
        </div>
        <div className="console-page-header__actions">
          <button type="button" className="console-btn" onClick={() => setRequestNonce((value) => value + 1)} disabled={isLoading}>
            <RefreshCw className={isLoading ? "animate-spin" : ""} aria-hidden="true" />
            {vi ? "Làm mới" : "Refresh"}
          </button>
        </div>
      </div>

      <div className="console-layout">
        <div className="console-layout__main">
          <div className="console-card">
            <div className="console-card__body space-y-3">
              <div className="console-input-row">
                <Search aria-hidden="true" />
                <input
                  className="console-input"
                  aria-label={vi ? "Tìm tài liệu" : "Search filings"}
                  value={search}
                  onChange={(event) => { setSearch(event.target.value); setPage(1); }}
                  placeholder={vi ? "Tìm theo công ty, mã, ngày nộp, accession…" : "Search by company, ticker, filing date, or accession…"}
                />
                {search && (
                  <button type="button" className="console-input-row__clear" aria-label={vi ? "Xóa tìm kiếm" : "Clear search"} onClick={() => { setSearch(""); setPage(1); }}>
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                )}
              </div>
              {/* Order follows the reference: Company, then the filing year,
                  then the section. The reference's form-type filter is absent
                  because API-003 records no form type for this corpus. */}
              <div className={`grid gap-3 sm:grid-cols-2 ${yearOptions.length > 0 ? "lg:grid-cols-3" : ""}`}>
                <SelectField label={vi ? "Công ty / Mã" : "Company / Ticker"} value={ticker} options={tickerOptions} onValueChange={(value) => { setTicker(value); setPage(1); }} />
                {yearOptions.length > 0 && (
                  <SelectField label={vi ? "Năm" : "Year"} value={year} options={yearOptions} onValueChange={(value) => { setYear(value); setPage(1); }} />
                )}
                <SelectField label={vi ? "Mục" : "Section"} value={section} options={sectionOptions} onValueChange={(value) => { setSection(value); setPage(1); }} />
              </div>
              {hasActiveFilters && (
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs text-[var(--text-muted)]">
                    {vi
                      ? "Bộ lọc đang áp dụng; số đếm trên mỗi lựa chọn tính mọi bộ lọc khác."
                      : "Filters applied; each option count already reflects every other filter."}
                  </span>
                  <button
                    type="button"
                    className="console-btn"
                    onClick={() => { setSearch(""); setTicker(""); setSection(""); setYear(""); setPage(1); }}
                  >
                    <X aria-hidden="true" />
                    {vi ? "Xóa bộ lọc" : "Clear filters"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {listError && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[color-mix(in_srgb,var(--danger)_40%,transparent)] bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
              <span>{listError}</span>
              <button type="button" onClick={() => setRequestNonce((value) => value + 1)} className="console-btn">{vi ? "Thử lại" : "Retry"}</button>
            </div>
          )}

          <div className="console-stats">
            <div className="console-stat">
              <div className="console-stat__icon"><FileText aria-hidden="true" /></div>
              <div className="min-w-0">
                <div className="console-stat__value">{statDocuments}</div>
                <div className="console-stat__label">{vi ? "Tổng tài liệu" : "Total Documents"}</div>
                <div className="console-stat__hint">{unfilteredHint}</div>
              </div>
            </div>
            <div className="console-stat">
              <div className="console-stat__icon"><Building2 aria-hidden="true" /></div>
              <div className="min-w-0">
                <div className="console-stat__value">{statCompanies ?? "—"}</div>
                <div className="console-stat__label">{vi ? "Công ty" : "Companies"}</div>
                <div className="console-stat__hint">{vi ? "Có đoạn nhúng tìm được" : "With searchable chunks"}</div>
              </div>
            </div>
            <div className="console-stat">
              <div className="console-stat__icon"><Database aria-hidden="true" /></div>
              <div className="min-w-0">
                <div className="console-stat__value">{statChunks != null ? statChunks.toLocaleString(vi ? "vi-VN" : "en-US") : "—"}</div>
                <div className="console-stat__label">{vi ? "Tổng đoạn nguồn" : "Total Chunks"}</div>
                <div className="console-stat__hint">{vi ? "Trong chỉ mục cục bộ" : "In the local index"}</div>
              </div>
            </div>
            <div className="console-stat">
              <div className="console-stat__icon console-stat__icon--warning"><CircleSlash2 aria-hidden="true" /></div>
              <div className="min-w-0">
                {/* A status word, not a number: the narrower size keeps it on
                    one line in the smallest receipt viewport. */}
                <div className="console-stat__value console-stat__value--status">{filingTypeValue}</div>
                <div className="console-stat__label">{vi ? "Loại hồ sơ" : "Filing Type"}</div>
                <div className="console-stat__hint">{filingTypeReason}</div>
              </div>
            </div>
          </div>

          <div className="console-card">
            <div className="console-card__header">
              <div className="min-w-0">
                <h2 className="console-card__title">{vi ? `Tài liệu (${total})` : `Documents (${total})`}</h2>
                <p className="console-card__subtitle" aria-live="polite">{listStatusLabel}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <SelectField
                  className="console-header-select"
                  label={vi ? "Sắp xếp theo" : "Sort by"}
                  value={sortOption}
                  options={sortOptions}
                  onValueChange={(value) => { setSortOption(value); setPage(1); }}
                />
                <SelectField
                  className="console-header-select"
                  label={vi ? "Số dòng mỗi trang" : "Rows per page"}
                  value={String(pageSize)}
                  options={pageSizeOptions}
                  onValueChange={(value) => { setPageSize(Number(value)); setPage(1); }}
                />
              </div>
            </div>
            <div className="console-table-wrap" aria-busy={isLoading}>
              <table className="console-table">
                <thead>
                  <tr>
                    <th scope="col" className="w-8"><span className="sr-only">{vi ? "Chọn" : "Select"}</span></th>
                    <th scope="col">{vi ? "Công ty" : "Company"}</th>
                    <th scope="col">Ticker</th>
                    <th scope="col">{vi ? "Ngày nộp" : "Filing Date"}</th>
                    <th scope="col" className="text-right">{vi ? "Mục" : "Sections"}</th>
                    <th scope="col" className="text-right">{vi ? "Đoạn" : "Chunks"}</th>
                    <th scope="col" className="text-right">{vi ? "Hành động" : "Actions"}</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document) => {
                    const isSelected = selected?.document_id === document.document_id;
                    return (
                      <tr
                        key={document.document_id}
                        className={isSelected ? "is-selected" : ""}
                        aria-selected={isSelected}
                        onClick={() => selectDocument(document)}
                      >
                        <td>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => selectDocument(document)}
                            onClick={(event) => event.stopPropagation()}
                            aria-label={vi ? `Xem chi tiết ${document.ticker ?? document.document_id}` : `Show details for ${document.ticker ?? document.document_id}`}
                            className="h-4 w-4 accent-[var(--primary)]"
                          />
                        </td>
                        <td>
                          <span className="flex items-center gap-2 min-w-0">
                            <span className="console-avatar" aria-hidden="true">{tickerInitials(document.ticker)}</span>
                            <span className="console-table__primary">{document.ticker ? formatCompanyLabel(document.ticker) : "SEC filing"}</span>
                          </span>
                        </td>
                        <td><span className="console-chip">{document.ticker ?? "—"}</span></td>
                        <td><span className="console-table__secondary">{document.filing_date ?? "—"}</span></td>
                        <td className="text-right console-table__secondary">{document.sections.length}</td>
                        <td className="text-right console-table__secondary">{document.chunk_count.toLocaleString(vi ? "vi-VN" : "en-US")}</td>
                        <td>
                          <span className="flex items-center justify-end gap-1" onClick={(event) => event.stopPropagation()}>
                            <button
                              id={focusId(document.document_id)}
                              type="button"
                              className="console-btn console-btn--ghost console-btn--icon"
                              aria-label={vi ? "Mở không gian tài liệu" : "Open document workspace"}
                              disabled={detailOpenDisabled}
                              onClick={() => openWorkspace(document)}
                            >
                              <FolderOpen aria-hidden="true" />
                            </button>
                            {sanitizeSecBrowserUrl(document.source_url) && (
                              <a
                                className="console-btn console-btn--ghost console-btn--icon"
                                href={sanitizeSecBrowserUrl(document.source_url) ?? undefined}
                                target="_blank"
                                rel="noreferrer"
                                aria-label={vi ? "Mở nguồn SEC" : "Open SEC source"}
                              >
                                <ExternalLink aria-hidden="true" />
                              </a>
                            )}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                  {!isLoading && !listError && documents.length === 0 && (
                    <tr>
                      <td colSpan={7}>
                        <div className="console-empty">
                          <SearchX aria-hidden="true" />
                          <strong>{hasActiveFilters ? (vi ? "Không có tài liệu khớp bộ lọc" : "No documents match the filters") : (vi ? "Danh mục chưa có tài liệu" : "Catalog is empty")}</strong>
                          <p>{vi ? "Điều chỉnh bộ lọc hoặc từ khóa tìm kiếm rồi thử lại." : "Adjust the filters or search terms and try again."}</p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {!listError && total > 0 && (
              <div className="console-card__footer">
                <span className="text-xs text-[var(--text-muted)]">{rangeLabel}</span>
                <nav className="console-pager" aria-label={vi ? "Phân trang tài liệu" : "Document pagination"}>
                  <button type="button" className="console-pager__page" disabled={page <= 1 || isLoading} onClick={() => setPage((value) => value - 1)} aria-label={vi ? "Trang trước" : "Previous page"}>
                    <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                  {pagerItems(page, pageCount).map((item, index) =>
                    item === "gap" ? (
                      <span key={`gap-${index}`} className="console-pager__gap" aria-hidden="true">…</span>
                    ) : (
                      <button
                        key={item}
                        type="button"
                        className={`console-pager__page ${item === page ? "is-current" : ""}`}
                        aria-current={item === page ? "page" : undefined}
                        disabled={isLoading}
                        onClick={() => setPage(item)}
                      >
                        {item}
                      </button>
                    ),
                  )}
                  <button type="button" className="console-pager__page" disabled={page >= pageCount || isLoading} onClick={() => setPage((value) => value + 1)} aria-label={vi ? "Trang sau" : "Next page"}>
                    <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                </nav>
              </div>
            )}
          </div>
        </div>

        <aside className="console-layout__aside" aria-label={vi ? "Chi tiết tài liệu" : "Document details"}>
          {selected ? (
            <div className="console-card">
              <div className="console-card__header">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="console-avatar" aria-hidden="true">{tickerInitials(selected.ticker)}</span>
                  <div className="min-w-0">
                    <h2 className="console-card__title truncate">{selected.ticker ? formatCompanyLabel(selected.ticker) : "SEC filing"}</h2>
                    <p className="console-card__subtitle truncate">{selected.ticker ?? "—"} · {selected.filing_date ?? "—"}</p>
                  </div>
                </div>
                <button type="button" onClick={() => setSelected(null)} aria-label={vi ? "Đóng chi tiết" : "Close document details"} className="console-btn console-btn--ghost console-btn--icon">
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              <div className="console-underline-tabs" role="tablist" aria-label={vi ? "Tab chi tiết tài liệu" : "Document detail tabs"}>
                {([
                  ["overview", vi ? "Tổng quan" : "Overview"],
                  ["sections", vi ? `Mục (${selected.sections.length})` : `Sections (${selected.sections.length})`],
                  ["representations", vi ? "Biểu diễn" : "Representations"],
                  ["metadata", "Metadata"],
                ] as Array<[DetailsTab, string]>).map(([tab, label]) => (
                  <button
                    key={tab}
                    type="button"
                    role="tab"
                    aria-selected={detailsTab === tab}
                    className={`console-underline-tab ${detailsTab === tab ? "is-active" : ""}`}
                    onClick={() => setDetailsTab(tab)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {detailsTab === "overview" && (
                <div className="console-card__body space-y-4">
                  <div>
                    <h3 className="mb-1.5 text-sm font-bold text-[var(--text-primary)]">{vi ? "Tóm tắt tài liệu" : "Document Summary"}</h3>
                    <p className="text-[13px] leading-relaxed text-[var(--text-muted)]">{summaryText}</p>
                  </div>
                  {firstPreview && (
                    <div>
                      <div className="mb-1.5 flex items-center justify-between gap-2">
                        <h3 className="text-sm font-bold text-[var(--text-primary)]">{vi ? "Xem trước nội dung" : "Content Preview"}</h3>
                        <span className="console-chip">{firstPreview.section ?? (vi ? "Mục không rõ" : "Unknown section")}</span>
                      </div>
                      <div className="console-paper">
                        <p className="console-paper__eyebrow">{selected.ticker ?? "SEC"} · {firstPreview.chunk_id ? shortId(firstPreview.chunk_id) : "excerpt"}</p>
                        <p className="whitespace-pre-wrap">{firstPreview.text_preview}</p>
                      </div>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="console-btn console-btn--primary"
                      disabled={detailOpenDisabled}
                      onClick={() => openWorkspace(selected)}
                    >
                      <FolderOpen aria-hidden="true" />
                      {vi ? "Mở trong trình xem" : "Open in Viewer"}
                    </button>
                    <button type="button" className="console-btn" onClick={() => setDetailsTab("sections")}>
                      <Search aria-hidden="true" />
                      {vi ? "Xem đoạn nguồn" : "Inspect Content"}
                    </button>
                    {onSaveEvidence && firstPreview && (
                      <button
                        type="button"
                        className="console-btn"
                        onClick={() => onSaveEvidence({
                          citation: `${firstPreview.ticker ?? "SEC"} indexed excerpt · ${firstPreview.section ?? "Unknown section"}`,
                          text_preview: firstPreview.text_preview,
                          chunk_id: firstPreview.chunk_id,
                          document_id: selected.document_id,
                          ticker: firstPreview.ticker,
                          section: firstPreview.section,
                          filing_date: firstPreview.filing_date,
                          report_date: firstPreview.report_date,
                          source_url: firstPreview.source_url,
                        })}
                      >
                        <Copy aria-hidden="true" />
                        {vi ? "Lưu vào bộ sưu tập" : "Add to Collection"}
                      </button>
                    )}
                  </div>
                </div>
              )}

              {detailsTab === "sections" && (
                <div className="console-card__body space-y-3">
                  <div className="flex flex-wrap gap-1.5">
                    {selected.sections.map((item) => (
                      <button
                        key={item}
                        type="button"
                        className={`console-chip console-chip--toggle ${chunkSearch === item ? "console-chip--active" : ""}`}
                        onClick={() => { setChunkSearch(chunkSearch === item ? "" : item); setChunkPage(1); }}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                  <div className="console-input-row">
                    <Search aria-hidden="true" />
                    <input
                      data-composite-input
                      className="console-input"
                      value={chunkSearch}
                      onChange={(event) => { setChunkSearch(event.target.value); setChunkPage(1); }}
                      placeholder={vi ? "Tìm trong đoạn nguồn…" : "Search excerpts…"}
                      aria-label={vi ? "Tìm trong đoạn nguồn" : "Search excerpts"}
                    />
                  </div>
                  {chunkError && (
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg state-warning-surface p-2.5 text-xs" role="alert">
                      <span>{chunkError}</span>
                      <button type="button" onClick={() => setChunkRequestNonce((value) => value + 1)} className="console-btn">{vi ? "Thử lại" : "Retry"}</button>
                    </div>
                  )}
                  <div className="console-rowlist" aria-busy={isLoadingChunks}>
                    {chunks.map((chunk) => {
                      const selectedSource: Source = {
                        citation: `${chunk.ticker ?? "SEC"} indexed excerpt · ${chunk.section ?? "Unknown section"}`,
                        text_preview: chunk.text_preview,
                        chunk_id: chunk.chunk_id,
                        document_id: selected.document_id,
                        ticker: chunk.ticker,
                        section: chunk.section,
                        filing_date: chunk.filing_date,
                        report_date: chunk.report_date,
                        source_url: chunk.source_url,
                      };
                      return (
                        <button
                          key={chunk.chunk_id}
                          id={chunkFocusId(selected.document_id, chunk.chunk_id)}
                          type="button"
                          className="console-rowlist__row"
                          onClick={() => openWorkspace(selected, selectedSource, "excerpt", chunkFocusId(selected.document_id, chunk.chunk_id))}
                        >
                          <span className="console-rowlist__icon"><FileText aria-hidden="true" /></span>
                          <span className="console-rowlist__body">
                            <span className="console-rowlist__title">{chunk.section ?? (vi ? "Mục không rõ" : "Unknown section")}</span>
                            <span className="console-rowlist__meta">{chunk.text_preview}</span>
                            <span className="console-rowlist__meta">{chunk.chunk_id} · {chunk.text_length.toLocaleString(vi ? "vi-VN" : "en-US")} {vi ? "ký tự" : "chars"}</span>
                          </span>
                          <span className="console-rowlist__side">{chunk.chunk_index ?? ""}</span>
                        </button>
                      );
                    })}
                    {isLoadingChunks && <div className="console-loading py-3"><span className="console-loading__spinner" aria-hidden="true" />{vi ? "Đang tải đoạn nguồn…" : "Loading excerpts…"}</div>}
                    {!isLoadingChunks && !chunkError && chunks.length === 0 && (
                      <div className="console-empty"><SearchX aria-hidden="true" /><strong>{vi ? "Không có đoạn phù hợp" : "No matching excerpts"}</strong></div>
                    )}
                  </div>
                  <div className="flex items-center justify-between border-t border-[var(--border-subtle)] pt-3">
                    <button type="button" className="console-btn" disabled={chunkPage <= 1 || isLoadingChunks} onClick={() => setChunkPage((value) => value - 1)}>
                      <ChevronLeft aria-hidden="true" />{vi ? "Trước" : "Previous"}
                    </button>
                    <span className="text-xs text-[var(--text-muted)]">{vi ? `Trang ${chunkPage}` : `Page ${chunkPage}`}</span>
                    <button type="button" className="console-btn" disabled={chunks.length < 8 || isLoadingChunks} onClick={() => setChunkPage((value) => value + 1)}>
                      {vi ? "Sau" : "Next"}<ChevronRight aria-hidden="true" />
                    </button>
                  </div>
                </div>
              )}

              {detailsTab === "representations" && (
                <div className="console-card__body space-y-3">
                  {manifestError && (
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg state-warning-surface p-2.5 text-xs" role="alert">
                      <span>{manifestError}</span>
                    </div>
                  )}
                  {!manifest && !manifestError && <div className="console-loading py-2"><span className="console-loading__spinner" aria-hidden="true" />{vi ? "Đang tải trạng thái biểu diễn…" : "Loading representation availability…"}</div>}
                  {manifest && representationCards.length === 0 && (
                    <div className="console-empty"><Boxes aria-hidden="true" /><strong>{vi ? "Không có biểu diễn nào được báo cáo" : "No representations reported"}</strong></div>
                  )}
                  {representationCards.map((card) => {
                    const available = card.status === "available";
                    const partial = card.status === "partial";
                    const Icon = available ? CheckCircle2 : partial ? CircleSlash2 : XCircle;
                    const tone = available ? "var(--success)" : partial ? "var(--warning)" : "var(--danger)";
                    return (
                      <div key={card.kind} className="flex items-start gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3">
                        <Icon className="mt-0.5 h-5 w-5 flex-shrink-0" style={{ color: tone }} aria-hidden="true" />
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-bold text-[var(--text-primary)]">{card.label}</span>
                            <span className="console-pill" style={{ color: tone, borderColor: tone, background: `color-mix(in srgb, ${tone} 12%, transparent)` }}>
                              {available ? (vi ? "Khả dụng" : "Available") : partial ? (vi ? "Một phần" : "Partial") : (vi ? "Không khả dụng" : "Unavailable")}
                            </span>
                            {card.coverage && <span className="console-chip">{vi ? "Độ phủ" : "Coverage"}: {card.coverage}</span>}
                          </div>
                          {card.reason && <p className="mt-1 text-xs leading-relaxed text-[var(--text-muted)]">{card.reason}</p>}
                        </div>
                      </div>
                    );
                  })}
                  <p className="text-xs leading-relaxed text-[var(--text-subtle)]">
                    {vi
                      ? "PDF không nằm trong phạm vi biểu diễn cục bộ hiện tại; một biểu diễn không chứng minh biểu diễn khác."
                      : "PDF is outside the current local representation scope; one representation never proves another."}
                  </p>
                </div>
              )}

              {detailsTab === "metadata" && (
                <div className="console-card__body">
                  <dl className="console-meta-grid">
                    <div><dt>{vi ? "Công ty" : "Company"}</dt><dd>{selected.ticker ? formatCompanyLabel(selected.ticker) : "—"}</dd></div>
                    <div><dt>Ticker</dt><dd>{selected.ticker ?? "—"}</dd></div>
                    <div>
                      <dt>{vi ? "Loại hồ sơ" : "Filing Type"}</dt>
                      <dd>
                        {filingTypeValue}
                        <span className="block text-xs font-normal text-[var(--text-subtle)]">{filingTypeReason}</span>
                      </dd>
                    </div>
                    <div><dt>{vi ? "Ngày nộp" : "Filing Date"}</dt><dd>{selected.filing_date ?? "—"}</dd></div>
                    <div><dt>{vi ? "Ngày báo cáo" : "Report Date"}</dt><dd>{selected.report_date ?? "—"}</dd></div>
                    <div><dt>{vi ? "Số mục" : "Sections"}</dt><dd>{selected.sections.length}</dd></div>
                    <div><dt>{vi ? "Số đoạn" : "Chunks"}</dt><dd>{selected.chunk_count.toLocaleString(vi ? "vi-VN" : "en-US")}</dd></div>
                    <div><dt>{vi ? "Nguồn" : "Source"}</dt><dd>SEC EDGAR</dd></div>
                    <div><dt>Accession No.</dt><dd className="font-mono text-xs">{selected.accession_number ?? "—"}</dd></div>
                    <div><dt>Document ID</dt><dd className="font-mono text-xs">{selected.document_id}</dd></div>
                  </dl>
                  {sanitizeSecBrowserUrl(selected.source_url) && (
                    <a href={sanitizeSecBrowserUrl(selected.source_url) ?? undefined} target="_blank" rel="noreferrer" className="console-btn mt-4 inline-flex">
                      <ExternalLink aria-hidden="true" />
                      {vi ? "Mở nguồn SEC" : "Open SEC source"}
                    </a>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="console-card">
              <div className="console-card__header"><h2 className="console-card__title">{vi ? "Chi tiết tài liệu" : "Document Details"}</h2></div>
              <div className="console-empty">
                <FileText aria-hidden="true" />
                <strong>{vi ? "Chọn một tài liệu" : "Select a document"}</strong>
                <p>{vi ? "Chọn một hàng trong bảng để xem tóm tắt, mục, biểu diễn và metadata tại đây." : "Pick a row in the table to see its summary, sections, representations, and metadata here."}</p>
              </div>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
});
