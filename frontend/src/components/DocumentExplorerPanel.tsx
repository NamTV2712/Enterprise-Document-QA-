import { memo, useEffect, useMemo, useRef, useState } from "react";
import { BookOpen, ExternalLink, FileText, Search, X } from "lucide-react";
import { getDocumentChunks, getDocuments } from "../lib/api";
import { CatalogWorkspaceTarget, DocumentChunk, DocumentRow, Source } from "../types";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";
import { SelectField } from "./ui/SelectField";
import { getWorkspaceNavItem } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";
import { formatCompanyLabel } from "../lib/displayMetadata";

interface DocumentExplorerPanelProps {
  tickers: string[];
  sections: string[];
  onOpenDocument?: (target: CatalogWorkspaceTarget) => void;
  onOpenSource?: (source: Source) => void;
}

const PAGE_SIZE = 12;
const SEARCH_DEBOUNCE_MS = 250;
const MAX_SHARED_DOCUMENT_CACHE_ENTRIES = 32;
const WORKSPACE_META = getWorkspaceNavItem("documents");

type DocumentCacheEntry = { items: DocumentRow[]; total: number };

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
    return () => window.clearTimeout(timer);
  }, [value]);
  return debounced;
}

function focusId(documentId: string): string {
  return `document-workspace-${documentId.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

export const DocumentExplorerPanel = memo(function DocumentExplorerPanel({ tickers, sections, onOpenDocument, onOpenSource }: DocumentExplorerPanelProps) {
  const { locale, t } = useLocale();
  const vi = locale === "vi";
  const ToolIcon = getSemanticIcon(WORKSPACE_META.icon);
  const [search, setSearch] = useState("");
  const [ticker, setTicker] = useState("");
  const [section, setSection] = useState("");
  const [page, setPage] = useState(1);
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<DocumentRow | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunkSearch, setChunkSearch] = useState("");
  const [chunkPage, setChunkPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [chunkError, setChunkError] = useState<string | null>(null);
  const [requestNonce, setRequestNonce] = useState(0);
  const [chunkRequestNonce, setChunkRequestNonce] = useState(0);
  const debouncedSearch = useDebouncedValue(search);
  const debouncedChunkSearch = useDebouncedValue(chunkSearch);
  // The panel is route-lazy and unmounts when the user returns to Research.
  // Keep the bounded catalog cache at module scope so a warm route switch does
  // not repeat the same metadata request after that intentional unmount.
  const documentCache = useRef(new Map<string, DocumentCacheEntry>());
  const chunkCache = useRef(new Map<string, DocumentChunk[]>());
  const documentRequestId = useRef(0);
  const chunkRequestId = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const requestId = ++documentRequestId.current;
    const cacheKey = JSON.stringify({ ticker, section, search: debouncedSearch, page });
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
    void getDocuments({ ticker: ticker || null, section: section || null, search: debouncedSearch, page, page_size: PAGE_SIZE }, controller.signal)
      .then((response) => {
        if (requestId !== documentRequestId.current) return;
        rememberDocumentCache(documentCache.current, cacheKey, { items: response.items, total: response.total });
        setDocuments(response.items);
        setTotal(response.total);
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
  }, [page, debouncedSearch, section, ticker, requestNonce]);

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

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const tickerOptions = useMemo(
    () => [{ value: "", label: vi ? "Tất cả công ty" : "All companies" }, ...tickers.map((item) => ({ value: item, label: formatCompanyLabel(item) }))],
    [tickers, vi],
  );
  const sectionOptions = useMemo(
    () => [{ value: "", label: vi ? "Tất cả mục" : "All sections" }, ...sections.map((item) => ({ value: item, label: item }))],
    [sections, vi],
  );
  const rangeLabel = useMemo(() => {
    if (total === 0) {
      const hasFilters = Boolean(debouncedSearch.trim() || ticker || section);
      return hasFilters
        ? (vi ? "Không tìm thấy tài liệu phù hợp" : "No matching documents")
        : (vi ? "Không có tài liệu" : "No documents");
    }
    const start = (page - 1) * PAGE_SIZE + 1;
    const end = Math.min(page * PAGE_SIZE, total);
    return vi ? `${start}–${end} trên ${total}` : `${start}–${end} of ${total}`;
  }, [debouncedSearch, page, section, ticker, total, vi]);

  const listStatusLabel = isLoading
    ? (vi ? "Đang tải…" : "Loading…")
    : listError
      ? (vi ? "Không khả dụng" : "Unavailable")
      : rangeLabel;

  const selectDocument = (document: DocumentRow) => {
    setSelected(document);
    setChunkPage(1);
    setChunkSearch("");
  };

  return (
    <section className="workspace-page workspace-page--standard document-explorer space-y-5" aria-labelledby="document-explorer-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-semibold text-violet-700 dark:text-violet-300">
            <ToolIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {t(WORKSPACE_META.labelKey)}
          </div>
          <h1 id="document-explorer-title" className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            {vi ? "Document Explorer" : "Document Explorer"}
          </h1>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[var(--text-muted)]">
            {t(WORKSPACE_META.descriptionKey)} {vi ? "Không truy cập đường dẫn filesystem." : "Filesystem paths are never exposed."}
          </p>
        </div>
      </div>

      <div className="documents-filter-grid rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4">
        <label className="select-field relative block" data-composite-field>
          <span className="select-field__label">{vi ? "Tìm tài liệu" : "Search documents"}</span>
          <Search className="documents-filter-search-icon pointer-events-none absolute left-3 h-4 w-4 text-[var(--text-muted)]" aria-hidden="true" />
          <input data-composite-input
            aria-label={vi ? "Tìm tài liệu" : "Search documents"}
            value={search}
            onChange={(event) => { setSearch(event.target.value); setPage(1); }}
            placeholder={vi ? "Tìm ticker, ngày filing, accession…" : "Search ticker, filing date, accession…"}
            className="min-h-10 w-full rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] pl-9 pr-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
          />
        </label>
        <SelectField label={vi ? "Công ty" : "Company"} value={ticker} options={tickerOptions} onValueChange={(value) => { setTicker(value); setPage(1); }} />
        <SelectField label={vi ? "Mục" : "Section"} value={section} options={sectionOptions} onValueChange={(value) => { setSection(value); setPage(1); }} />
      </div>

      {listError && <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-300/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-700 dark:text-rose-300" role="alert"><span>{listError}</span><button type="button" onClick={() => setRequestNonce((value) => value + 1)} className="rounded-lg border border-current px-3 py-1.5 text-xs font-semibold">{vi ? "Thử lại" : "Retry"}</button></div>}

      <div className="overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)]">
        <div className="flex items-center justify-between gap-3 border-b border-[var(--border-subtle)] px-4 py-3" aria-busy={isLoading}>
          <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]"><BookOpen className="h-4 w-4 text-violet-600 dark:text-violet-300" />{vi ? "Filing đã nạp" : "Loaded filings"}</div>
          <span className="text-xs text-[var(--text-muted)]" aria-live="polite">{listStatusLabel}</span>
        </div>
        <div className="divide-y divide-[var(--border-subtle)]">
          {documents.map((document) => (
            <button key={document.document_id} type="button" onClick={() => selectDocument(document)} className="flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-[var(--surface-muted)]">
              <span className="min-w-0"><span className="block font-semibold text-[var(--text-primary)]">{document.ticker ? formatCompanyLabel(document.ticker) : "SEC filing"} · {document.filing_date ?? "Unknown date"}</span><span className="block truncate text-xs text-[var(--text-muted)]">{document.document_id}</span></span>
              <span className="flex items-center gap-3 text-xs text-[var(--text-muted)]"><span>{document.chunk_count} chunks</span><span>{document.sections.length} sections</span><ExternalLink className="h-4 w-4" aria-hidden="true" /></span>
            </button>
          ))}
          {!isLoading && !listError && documents.length === 0 && <div className="px-5 py-12 text-center text-sm text-[var(--text-muted)]">{vi ? "Không tìm thấy tài liệu phù hợp." : "No matching documents."}</div>}
        </div>
        {!listError && <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-4 py-3">
          <button type="button" disabled={page <= 1 || isLoading} onClick={() => setPage((value) => value - 1)} className="rounded-lg border border-[var(--border-strong)] px-3 py-1.5 text-xs font-semibold disabled:opacity-40">{vi ? "Trước" : "Previous"}</button>
          <span className="text-xs text-[var(--text-muted)]">{page} / {pageCount}</span>
          <button type="button" disabled={page >= pageCount || isLoading} onClick={() => setPage((value) => value + 1)} className="rounded-lg border border-[var(--border-strong)] px-3 py-1.5 text-xs font-semibold disabled:opacity-40">{vi ? "Sau" : "Next"}</button>
        </div>}
      </div>

      {selected && (
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)]">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border-subtle)] px-4 py-4">
            <div><div className="text-sm font-bold text-[var(--text-primary)]">{selected.ticker ? formatCompanyLabel(selected.ticker) : "SEC filing"} · {selected.filing_date}</div><div className="mt-1 text-xs text-[var(--text-muted)]">{selected.document_id} · {selected.chunk_count} chunks</div></div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              {onOpenDocument && <button id={focusId(selected.document_id)} type="button" onClick={() => onOpenDocument({ kind: "catalog", documentId: selected.document_id, title: `${selected.ticker ? formatCompanyLabel(selected.ticker) : "SEC filing"} · ${selected.filing_date ?? "date unavailable"}`, ticker: selected.ticker, filingDate: selected.filing_date, reportDate: selected.report_date, accessionNumber: selected.accession_number, sourceUrl: selected.source_url, returnView: "documents", returnFocusId: focusId(selected.document_id) })} className="rounded-lg border border-[var(--primary)] px-3 py-1.5 text-xs font-semibold text-[var(--primary)]">{vi ? "Mở không gian tài liệu" : "Open document workspace"}</button>}
              <button type="button" onClick={() => setSelected(null)} aria-label={vi ? "Đóng chi tiết" : "Close document details"} className="rounded-lg p-2 text-[var(--text-muted)] hover:bg-[var(--surface-muted)]"><X className="h-4 w-4" /></button>
            </div>
          </div>
          <div className="grid gap-3 border-b border-[var(--border-subtle)] p-4 md:grid-cols-[minmax(0,1fr)_160px]" data-composite-field>
            <input data-composite-input value={chunkSearch} onChange={(event) => { setChunkSearch(event.target.value); setChunkPage(1); }} placeholder={vi ? "Tìm trong đoạn nguồn…" : "Search excerpts…"} aria-label={vi ? "Tìm trong đoạn nguồn" : "Search excerpts"} className="min-h-10 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--primary)]" />
            <div className="flex items-center justify-end text-xs text-[var(--text-muted)]">{isLoadingChunks ? (vi ? "Đang tải…" : "Loading…") : `${chunks.length} ${vi ? "đoạn" : "excerpts"}`}</div>
          </div>
          <div className="space-y-3 p-4">
            {chunkError && <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg state-warning-surface p-3 text-xs" role="alert"><span>{chunkError}</span><button type="button" onClick={() => setChunkRequestNonce((value) => value + 1)} className="rounded border border-current px-2 py-1 font-semibold">{vi ? "Thử lại" : "Retry"}</button></div>}
            {chunks.map((chunk) => {
              const selectedSource: Source = { citation: `${chunk.ticker ?? "SEC"} indexed excerpt · ${chunk.section ?? "Unknown section"}`, text_preview: chunk.text_preview, chunk_id: chunk.chunk_id, document_id: selected.document_id, ticker: chunk.ticker, section: chunk.section, filing_date: chunk.filing_date, report_date: chunk.report_date, source_url: chunk.source_url };
              return <article key={chunk.chunk_id} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-3"><div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-muted)]"><span className="font-semibold text-[var(--text-primary)]">{chunk.section ?? "Unknown section"}</span><span>{chunk.chunk_id} · {chunk.text_length} chars</span></div><p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--text-primary)]">{chunk.text_preview}</p><div className="mt-2 flex flex-wrap items-center gap-3">{(onOpenDocument || onOpenSource) && <button type="button" className="text-xs font-semibold text-[var(--primary)] hover:underline" onClick={() => onOpenDocument
                ? onOpenDocument({ kind: "catalog", documentId: selected.document_id, ticker: selected.ticker, filingDate: selected.filing_date, reportDate: selected.report_date, accessionNumber: selected.accession_number, sourceUrl: selected.source_url, selectedSource, initialTab: "excerpt", returnView: "documents", returnFocusId: focusId(selected.document_id) })
                : onOpenSource?.(selectedSource)}>{vi ? "Mở đoạn indexed" : "Open indexed excerpt"}</button>}{chunk.source_url && <a href={chunk.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] hover:underline">{vi ? "Mở nguồn SEC" : "Open SEC source"}<ExternalLink className="h-3 w-3" /></a>}</div></article>;
            })}
            {!isLoadingChunks && !chunkError && chunks.length === 0 && <p className="py-5 text-center text-sm text-[var(--text-muted)]">{vi ? "Không có đoạn phù hợp." : "No matching excerpts."}</p>}
          </div>
          <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-4 py-3"><button type="button" disabled={chunkPage <= 1 || isLoadingChunks} onClick={() => setChunkPage((value) => value - 1)} className="rounded-lg border border-[var(--border-strong)] px-3 py-1.5 text-xs font-semibold disabled:opacity-40">{vi ? "Trước" : "Previous"}</button><span className="text-xs text-[var(--text-muted)]">Page {chunkPage}</span><button type="button" disabled={chunks.length < 8 || isLoadingChunks} onClick={() => setChunkPage((value) => value + 1)} className="rounded-lg border border-[var(--border-strong)] px-3 py-1.5 text-xs font-semibold disabled:opacity-40">{vi ? "Sau" : "Next"}</button></div>
        </div>
      )}
    </section>
  );
});
