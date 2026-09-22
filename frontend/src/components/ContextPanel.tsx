import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Clipboard,
  ExternalLink,
  Loader2,
  Maximize2,
  Save,
  Search,
  X,
} from "lucide-react";
import React, { useCallback, useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import type { DocumentChunk, DocumentChunkDetail, Source } from "../types";
import { formatCompanyLabel, SECTION_METADATA } from "../lib/displayMetadata";
import { getCachedChunkDetail, getCachedDocumentChunks } from "../lib/documentCache";
import { describeRequestError } from "../lib/requestError";
import { saveEvidence, snapshotProvenanceFromSource } from "../lib/evidenceCollections";
import { useLocale } from "../lib/i18n";
import { getSourceKey } from "../lib/sourceIdentity";
import { getSectionDisplay } from "../lib/sourcePresentation";
import { sanitizeSecBrowserUrl } from "../lib/secUrls";
import { SourcesPane } from "./workbench/SourcesPane";
import { getSemanticIcon } from "../lib/semanticIcons";
import { ModalDialog } from "./ui/ModalDialog";
import { renderStructuredTableNode } from "./StructuredTable";
import { DocumentPane } from "./workbench/DocumentPane";
import { PaneResizer } from "./workbench/PaneResizer";
import { useOptionalWorkbenchContext } from "./workbench/WorkbenchContext";
import type { WorkbenchLayoutMode } from "../lib/workbench";
import { WORKBENCH_PANE_LIMITS } from "../lib/workbench";
import type { ReaderSessionController } from "../hooks/useReaderSession";

export interface ContextPanelProps {
  sources: Source[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  unavailable?: boolean;
  unavailableReason?: string;
  messageId?: string;
  conversationId?: string;
  railWidth?: number;
  onRailWidthChange?: (width: number) => void;
  isOpen?: boolean;
  presentation?: "inline" | "drawer" | "workbench";
  onClose?: () => void;
  onOpenCurrentSource?: (source: Source) => void;
  readerSession?: ReaderSessionController;
}

const CHUNK_PAGE_SIZE = 8;
const SEARCH_DEBOUNCE_MS = 250;

function useDebouncedValue(value: string): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [value]);
  return debounced;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function excerptText(source: Source): string {
  return source.text || source.text_preview;
}

function copyText(source: Source, index: number): string {
  const heading = source.stored_snapshot
    ? `[Saved evidence snapshot] ${source.citation}`
    : index >= 0
      ? `[Source ${index + 1}] ${source.citation}`
      : `[Indexed excerpt] ${source.citation}`;
  const lines = [heading];
  if (source.ticker) lines.push(`Company: ${formatCompanyLabel(source.ticker)}`);
  if (source.section) lines.push(`Section: ${SECTION_METADATA[source.section]?.label ?? source.section}`);
  if (source.filing_date) lines.push(`Filed: ${source.filing_date}`);
  lines.push("", excerptText(source));
  return lines.join("\n");
}

function HighlightedText({ text, excerpt }: { text: string; excerpt: string }): ReactNode {
  const needle = excerpt.trim();
  if (!needle) return text;
  const start = text.toLocaleLowerCase().indexOf(needle.toLocaleLowerCase());
  if (start < 0) return text;
  return (
    <>
      {text.slice(0, start)}
      <mark className="context-excerpt-highlight">{text.slice(start, start + needle.length)}</mark>
      {text.slice(start + needle.length)}
    </>
  );
}

interface DocumentViewerProps {
  source: Source | undefined;
  sourceIndex: number;
  messageId?: string;
  conversationId?: string;
  nearbySearch?: string;
  onNearbySearchChange?: (value: string) => void;
  nearbyPage?: number;
  onNearbyPageChange?: (value: number | ((page: number) => number)) => void;
  textScale?: number;
  onTextScaleChange?: (value: number | ((scale: number) => number)) => void;
  onOpenCurrentSource?: (source: Source) => void;
  showOriginal?: boolean;
  onShowOriginalChange?: (show: boolean) => void;
  onCollapse?: () => void;
  readerSession?: ReaderSessionController;
}

export function DocumentViewer({
  source,
  sourceIndex,
  messageId,
  conversationId,
  nearbySearch: controlledNearbySearch,
  onNearbySearchChange,
  nearbyPage: controlledNearbyPage,
  onNearbyPageChange,
  textScale: controlledTextScale,
  onTextScaleChange,
  onOpenCurrentSource,
  showOriginal: controlledShowOriginal,
  onShowOriginalChange,
  onCollapse,
  readerSession,
}: DocumentViewerProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [detail, setDetail] = useState<DocumentChunkDetail | null>(null);
  const [nearby, setNearby] = useState<DocumentChunk[]>([]);
  const [nearbyTotal, setNearbyTotal] = useState(0);
  const [internalNearbyPage, setInternalNearbyPage] = useState(1);
  const [internalNearbySearch, setInternalNearbySearch] = useState("");
  const [contextDetail, setContextDetail] = useState<DocumentChunkDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nearbyError, setNearbyError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [detailRetryNonce, setDetailRetryNonce] = useState(0);
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);
  const [internalShowOriginal, setInternalShowOriginal] = useState(false);
  const [internalTextScale, setInternalTextScale] = useState(100);
  const detailRequestId = useRef(0);
  const nearbyRequestId = useRef(0);
  const neighborDetailRequestId = useRef(0);
  const neighborDetailControllerRef = useRef<AbortController | null>(null);
  const latestSourceKey = useRef("");
  const previousSourceKey = useRef<string | null>(null);
  const nearbySearch = controlledNearbySearch ?? internalNearbySearch;
  const nearbyPage = controlledNearbyPage ?? internalNearbyPage;
  const textScale = controlledTextScale ?? internalTextScale;
  const setNearbySearch = onNearbySearchChange ?? setInternalNearbySearch;
  const setNearbyPage = onNearbyPageChange ?? setInternalNearbyPage;
  const setTextScale = onTextScaleChange ?? setInternalTextScale;
  const showOriginal = controlledShowOriginal ?? internalShowOriginal;
  const setShowOriginal = useCallback((next: boolean) => {
    setInternalShowOriginal(next);
    onShowOriginalChange?.(next);
  }, [onShowOriginalChange]);
  const debouncedNearbySearch = useDebouncedValue(nearbySearch);
  const selectedSourceKey = source ? getSourceKey(source) : "";
  latestSourceKey.current = selectedSourceKey;
  const isStoredSnapshot = Boolean(source?.stored_snapshot);
  const indexedText = contextDetail?.text || detail?.text || source?.text || source?.text_preview || "";
  const activeExcerpt = contextDetail ? "" : source ? excerptText(source) : "";
  const pageCount = Math.max(1, Math.ceil(nearbyTotal / CHUNK_PAGE_SIZE));
  const hasStoredExcerpt = Boolean(source && (source.text || source.text_preview));
  const readerGenerationRef = useRef<number | null>(null);

  const isCurrentReaderSession = useCallback(() => {
    const generation = readerGenerationRef.current;
    return !readerSession || (generation !== null && readerSession.isCurrent(generation));
  }, [readerSession]);

  useEffect(() => {
    if (!readerSession) {
      readerGenerationRef.current = null;
      return;
    }
    if (showOriginal) return;
    readerGenerationRef.current = readerSession.select(source ? {
      documentId: source.document_id,
      sourceKey: selectedSourceKey,
      representation: "indexed",
    } : null);
  }, [readerSession, selectedSourceKey, showOriginal, source?.document_id]);

  useEffect(() => {
    if (previousSourceKey.current !== null && previousSourceKey.current !== selectedSourceKey) {
      setShowOriginal(false);
    }
    previousSourceKey.current = selectedSourceKey;
  }, [selectedSourceKey]);

  useEffect(() => {
    const requestId = ++detailRequestId.current;
    const requestSourceKey = source ? getSourceKey(source) : "";
    setDetail(null);
    setContextDetail(null);
    setError(null);
    setActionError(null);
    setCopied(false);
    setSaved(false);
    setNearbyPage(1);
    if (!source) {
      setLoading(false);
      return;
    }
    if (!source.chunk_id || isStoredSnapshot) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    void getCachedChunkDetail(source.chunk_id, controller.signal)
      .then((response) => {
        if (requestId === detailRequestId.current && latestSourceKey.current === requestSourceKey && isCurrentReaderSession()) setDetail(response);
      })
      .catch((reason) => {
        if (requestId !== detailRequestId.current || !isCurrentReaderSession() || isAbortError(reason)) return;
        setError(describeRequestError(reason, vi ? "Không thể tải đoạn nguồn được lập chỉ mục." : "Could not load the indexed excerpt.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (requestId === detailRequestId.current && isCurrentReaderSession()) setLoading(false);
      });
    return () => {
      controller.abort();
      detailRequestId.current += 1;
      neighborDetailControllerRef.current?.abort();
      neighborDetailControllerRef.current = null;
      neighborDetailRequestId.current += 1;
    };
  }, [detailRetryNonce, isCurrentReaderSession, isStoredSnapshot, source, vi]);

  useEffect(() => {
    const requestId = ++nearbyRequestId.current;
    setNearby([]);
    setNearbyTotal(0);
    setNearbyError(null);
    if (!source?.document_id) {
      setNearbyLoading(false);
      return;
    }
    const controller = new AbortController();
    setNearbyLoading(true);
    void getCachedDocumentChunks(source.document_id, {
      search: debouncedNearbySearch,
      page: nearbyPage,
      page_size: CHUNK_PAGE_SIZE,
    }, controller.signal)
      .then((response) => {
        if (requestId !== nearbyRequestId.current || !isCurrentReaderSession()) return;
        setNearby(response.items);
        setNearbyTotal(response.total);
      })
      .catch((reason) => {
        if (requestId !== nearbyRequestId.current || !isCurrentReaderSession() || isAbortError(reason)) return;
        setNearbyError(describeRequestError(reason, vi ? "Không thể tải các đoạn liên quan." : "Could not load nearby indexed excerpts.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (requestId === nearbyRequestId.current && isCurrentReaderSession()) setNearbyLoading(false);
      });
    return () => {
      controller.abort();
      nearbyRequestId.current += 1;
    };
  }, [debouncedNearbySearch, isCurrentReaderSession, nearbyPage, source?.document_id, vi]);

  useEffect(() => () => {
    detailRequestId.current += 1;
    nearbyRequestId.current += 1;
    neighborDetailRequestId.current += 1;
    neighborDetailControllerRef.current?.abort();
    neighborDetailControllerRef.current = null;
  }, []);

  if (!source) {
    return <section className="context-viewer context-viewer--empty" aria-label={vi ? "Trình đọc bằng chứng" : "Evidence reader"}>{vi ? "Chọn một nguồn để xem đoạn trích." : "Select a source to inspect its excerpt."}</section>;
  }

  // `source` remains the immutable answer origin. A nearby read is a new
  // cursor, and all visible metadata/actions must move with that cursor.
  const currentSource: Source = contextDetail
    ? { ...source, ...contextDetail }
    : detail
      ? { ...source, ...detail }
      : source;
  const handleSave = () => {
    try {
      saveEvidence(currentSource, { conversationId, messageId, provenance: snapshotProvenanceFromSource(currentSource) });
      setSaved(true);
      setActionError(null);
      window.setTimeout(() => setSaved(false), 1800);
    } catch (reason) {
      setActionError(describeRequestError(reason, vi ? "Không thể lưu evidence." : "Could not save evidence.", vi ? "vi" : "en").message);
    }
  };

  if (showOriginal && currentSource.document_id) {
    const workspaceText = currentSource.text || currentSource.text_preview || "";
    const workspaceMetadata = [
      currentSource.document_id ? [vi ? "Document ID" : "Document ID", currentSource.document_id] : null,
      currentSource.chunk_id ? ["Chunk", currentSource.chunk_id] : null,
      currentSource.ticker ? [vi ? "Công ty" : "Company", formatCompanyLabel(currentSource.ticker)] : null,
      currentSource.section ? [vi ? "Mục" : "Section", currentSource.section] : null,
      currentSource.filing_date ? [vi ? "Ngày nộp" : "Filed", currentSource.filing_date] : null,
      currentSource.report_date ? [vi ? "Ngày báo cáo" : "Report date", currentSource.report_date] : null,
    ].filter(Boolean) as string[][];
    return <DocumentPane
      documentId={currentSource.document_id}
      indexedSource={currentSource}
      indexedExcerpt={<div className="document-workspace__excerpt-content"><p className="context-viewer-citation">{currentSource.citation}</p><p>{<HighlightedText text={workspaceText} excerpt={currentSource.text_preview || ""} />}</p></div>}
      metadata={<dl>{workspaceMetadata.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>}
      onBack={() => setShowOriginal(false)}
      onShowContext={() => setShowOriginal(false)}
      onCollapse={onCollapse}
      onSaveEvidence={handleSave}
      saved={saved}
      readerSession={readerSession}
    />;
  }
  const currentSourceIndex = contextDetail ? -1 : sourceIndex;
  const selectedSection = getSectionDisplay(currentSource.citation, currentSource.section).section;
  const displayText = loading ? (vi ? "Đang tải đoạn nguồn được lập chỉ mục…" : "Loading indexed excerpt…") : indexedText;
  const currentDetail = contextDetail ?? detail;
  const openSec = sanitizeSecBrowserUrl(currentSource.sec_index_url)
    ?? sanitizeSecBrowserUrl(currentSource.source_url);
  const metadata = [
    currentSource.ticker ? `${vi ? "Công ty" : "Company"}: ${formatCompanyLabel(currentSource.ticker)}` : null,
    currentSource.filing_type ? `${vi ? "Loại hồ sơ" : "Filing type"}: ${currentSource.filing_type}` : null,
    currentSource.filing_date ? `${vi ? "Ngày nộp" : "Filed"}: ${currentSource.filing_date}` : null,
    currentSource.report_date ? `${vi ? "Ngày báo cáo" : "Report date"}: ${currentSource.report_date}` : null,
    currentSource.chunk_id ? `${vi ? "Chunk" : "Chunk"}: ${currentSource.chunk_id}` : null,
  ].filter(Boolean) as string[];

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(copyText(currentSource, currentSourceIndex));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setActionError(vi ? "Không thể sao chép excerpt." : "Could not copy the excerpt.");
    }
  };

  const openNearby = async (chunk: DocumentChunk) => {
    if (!chunk.chunk_id) return;
    neighborDetailControllerRef.current?.abort();
    const controller = new AbortController();
    neighborDetailControllerRef.current = controller;
    const requestId = ++neighborDetailRequestId.current;
    setLoading(true);
    setError(null);
    try {
      const response = await getCachedChunkDetail(chunk.chunk_id, controller.signal);
      if (requestId === neighborDetailRequestId.current && latestSourceKey.current === selectedSourceKey && isCurrentReaderSession()) setContextDetail(response);
    } catch (reason) {
      if (requestId === neighborDetailRequestId.current && isCurrentReaderSession() && !isAbortError(reason)) {
        setError(describeRequestError(reason, vi ? "Không thể mở đoạn lân cận." : "Could not open the nearby excerpt.", vi ? "vi" : "en").message);
      }
    } finally {
      if (requestId === neighborDetailRequestId.current && isCurrentReaderSession()) {
        setLoading(false);
        neighborDetailControllerRef.current = null;
      }
    }
  };

  return (
    <section className="context-viewer" aria-labelledby="context-viewer-title">
      <div className="context-viewer-header">
        <div className="min-w-0">
          <p className="evidence-rail-eyebrow">{isStoredSnapshot ? (vi ? "Đã lưu" : "Saved evidence") : "Indexed excerpts"}</p>
          <h2 id="context-viewer-title">{selectedSection}</h2>
          <p className="context-viewer-citation">{isStoredSnapshot ? "[Saved evidence snapshot] " : currentSourceIndex >= 0 ? `[Source ${currentSourceIndex + 1}] ` : "[Nearby indexed excerpt] "}{currentSource.citation}</p>
        </div>
        <span className="context-indexed-badge">{React.createElement(getSemanticIcon("reader"), { className: "h-3.5 w-3.5", "aria-hidden": true })}{isStoredSnapshot ? (vi ? "Bản chụp đã lưu" : "Stored snapshot") : (vi ? "Đoạn đã lập chỉ mục" : "Indexed excerpt")}</span>
      </div>
      <div className="context-viewer-actions" aria-label={vi ? "Thao tác evidence" : "Evidence actions"}>
        {contextDetail && <button type="button" onClick={() => setContextDetail(null)} disabled={loading}>{vi ? "Về đoạn đã trích" : "Return to cited excerpt"}</button>}
        {isStoredSnapshot && onOpenCurrentSource && currentSource.chunk_id && <button type="button" onClick={() => onOpenCurrentSource({ ...currentSource, stored_snapshot: undefined })} disabled={loading}>{vi ? "Mở bản lập chỉ mục hiện tại" : "Inspect current indexed excerpt"}</button>}
        {currentSource.document_id && <button type="button" onClick={() => setShowOriginal(true)} disabled={loading}>{vi ? "Mở bản gốc chuẩn hóa" : "Open normalized original"}</button>}
        <button type="button" onClick={handleCopy} disabled={loading}><Clipboard className="h-3.5 w-3.5" aria-hidden="true" />{copied ? (vi ? "Đã sao chép" : "Copied") : (vi ? "Sao chép" : "Copy")}</button>
        <button type="button" onClick={handleSave} disabled={loading}><Save className="h-3.5 w-3.5" aria-hidden="true" />{saved ? (vi ? "Đã lưu" : "Saved") : (vi ? "Lưu" : "Save")}</button>
        {openSec && <a href={openSec} target="_blank" rel="noreferrer" className="context-viewer-link"><ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />{vi ? "Mở SEC" : "Open SEC"}</a>}
      </div>
      <details className="context-viewer-disclosure">
        <summary>{vi ? "Về nguồn này" : "About this source"}</summary>
        <p>{vi ? "Đây là đoạn trích từ chỉ mục SEC hiện có, không phải bản filing đầy đủ." : "This is an excerpt from the indexed SEC corpus, not a reconstructed full filing."}</p>
        {metadata.length > 0 && <div className="context-metadata">{metadata.map((item) => <span key={item}>{item}</span>)}</div>}
      </details>
      {actionError && <div className="context-action-error" role="alert"><AlertCircle className="h-4 w-4" aria-hidden="true" />{actionError}</div>}
      {error && <div className="context-action-error" role="alert"><AlertCircle className="h-4 w-4" aria-hidden="true" /><span>{error} {vi ? "Excerpt đã lưu vẫn còn khả dụng." : "The saved excerpt remains available."}</span><button type="button" onClick={() => setDetailRetryNonce((value) => value + 1)}>{vi ? "Thử lại" : "Retry"}</button></div>}
      <div className="context-viewer-text" style={{ fontSize: `${textScale / 100}em` }}>
        {loading && <Loader2 className="mr-2 inline-block h-4 w-4 animate-spin" aria-label={vi ? "Đang tải" : "Loading"} />}
        {renderStructuredTableNode(currentDetail ?? {}) ?? <HighlightedText text={displayText} excerpt={contextDetail ? "" : activeExcerpt} />}
      </div>
      {!detail && hasStoredExcerpt && !loading && <p className="context-offline-note">{isStoredSnapshot ? (vi ? "Đang hiển thị bản chụp tại thời điểm lưu; dữ liệu này không tự động bị thay thế." : "Showing the saved snapshot from the time it was captured; it is not replaced automatically.") : (vi ? "Đang hiển thị excerpt đã lưu; dữ liệu chỉ mục hiện không khả dụng." : "Showing the stored excerpt; indexed data is currently unavailable.")}</p>}
      <div className="context-viewer-footer">
        <span>{vi ? "Kích thước chữ" : "Text size"}</span>
        <button type="button" onClick={() => setTextScale((value) => Math.max(90, value - 10))} disabled={textScale <= 90} aria-label={vi ? "Giảm kích thước chữ" : "Decrease text size"}>−</button>
        <span>{textScale}%</span>
        <button type="button" onClick={() => setTextScale((value) => Math.min(150, value + 10))} disabled={textScale >= 150} aria-label={vi ? "Tăng kích thước chữ" : "Increase text size"}>+</button>
      </div>
      {currentSource.document_id && (
        <section className="context-nearby" aria-labelledby="context-nearby-title">
          <div className="context-nearby-header">
            <h3 id="context-nearby-title">{vi ? "Các đoạn trong document" : "Indexed document chunks"}</h3>
            <span>{nearbyTotal}</span>
          </div>
          <label className="context-indexed-search context-indexed-search--small" data-composite-field>
            <Search className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="sr-only">{vi ? "Tìm trong document" : "Search indexed document"}</span>
            <input data-composite-input type="search" value={nearbySearch} onChange={(event) => { setNearbySearch(event.target.value); setNearbyPage(1); }} placeholder={vi ? "Tìm trong đoạn…" : "Search chunks…"} />
          </label>
          {nearbyError && <p className="context-indexed-error" role="alert">{nearbyError}</p>}
          <div className="context-nearby-list">
            {nearbyLoading && <p className="evidence-rail-empty">{vi ? "Đang tải…" : "Loading…"}</p>}
            {!nearbyLoading && nearby.map((chunk) => (
              <button type="button" key={`${chunk.chunk_id ?? "missing"}-${chunk.chunk_index ?? ""}`} className={`context-neighbor-row ${chunk.chunk_id === currentSource.chunk_id ? "is-current" : ""}`} onClick={() => void openNearby(chunk)}>
                <span>{chunk.chunk_index ?? "—"}</span>
                <span>{chunk.text_preview}</span>
              </button>
            ))}
            {!nearbyLoading && nearby.length === 0 && <p className="evidence-rail-empty">{vi ? "Không có đoạn phù hợp." : "No matching indexed chunks."}</p>}
          </div>
          {pageCount > 1 && <div className="context-pagination"><button type="button" onClick={() => setNearbyPage((page) => Math.max(1, page - 1))} disabled={nearbyPage <= 1} aria-label={vi ? "Trang trước" : "Previous page"}><ChevronLeft className="h-4 w-4" /></button><span>{nearbyPage} / {pageCount}</span><button type="button" onClick={() => setNearbyPage((page) => Math.min(pageCount, page + 1))} disabled={nearbyPage >= pageCount} aria-label={vi ? "Trang sau" : "Next page"}><ChevronRight className="h-4 w-4" /></button></div>}
        </section>
      )}
    </section>
  );
}

const MIN_RAIL_WIDTH = 360;
const MAX_RAIL_WIDTH = 560;

function clampRailWidth(value: number): number {
  return Math.min(MAX_RAIL_WIDTH, Math.max(MIN_RAIL_WIDTH, Math.round(value)));
}

function CollapsedDocumentPane({ onExpand }: { onExpand: () => void }) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  return (
    <section className="workbench-document-collapsed" data-document-pane-collapsed="true" aria-label={vi ? "Bảng tài liệu đã thu gọn" : "Collapsed document pane"}>
      <button
        type="button"
        className="workbench-document-collapsed__button"
        aria-label={vi ? "Mở rộng bảng tài liệu" : "Expand document pane"}
        onClick={onExpand}
      >
        <Maximize2 className="h-4 w-4" aria-hidden="true" />
        <span>{vi ? "Tài liệu" : "Document"}</span>
      </button>
    </section>
  );
}

export function ContextPanel({
  sources,
  selectedIndex,
  onSelectIndex,
  unavailable = false,
  unavailableReason,
  messageId,
  conversationId,
  railWidth = 384,
  onRailWidthChange,
  isOpen = true,
  presentation = "inline",
  onClose,
  onOpenCurrentSource,
  readerSession,
}: ContextPanelProps) {
  const selected = Number.isInteger(selectedIndex) && selectedIndex >= 0 && selectedIndex < sources.length
    ? sources[selectedIndex]
    : undefined;
  const { locale } = useLocale();
  const [nearbySearch, setNearbySearch] = useState("");
  const [nearbyPage, setNearbyPage] = useState(1);
  const [textScale, setTextScale] = useState(100);
  const [showOriginal, setShowOriginal] = useState(false);
  const workbench = useOptionalWorkbenchContext();
  const workbenchMode: WorkbenchLayoutMode | null = presentation === "workbench"
    ? workbench?.controller.state.layoutMode ?? null
    : null;
  const isFourPane = workbenchMode === "four-pane";
  const isContextDock = workbenchMode === "context-dock";
  const sourceCollapsed = workbench?.preferences.sourcesCollapsed ?? false;
  const documentCollapsed = workbench?.preferences.documentCollapsed ?? false;
  const dragRef = useRef<{ startX: number; startWidth: number } | null>(null);
  const cleanupResizeListenersRef = useRef<(() => void) | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const updateWidth = (next: number) => onRailWidthChange?.(clampRailWidth(next));
  const stopResizeDrag = useCallback(() => {
    cleanupResizeListenersRef.current?.();
    cleanupResizeListenersRef.current = null;
    dragRef.current = null;
  }, []);

  useEffect(() => () => stopResizeDrag(), [stopResizeDrag]);

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!onRailWidthChange) return;
    stopResizeDrag();
    dragRef.current = { startX: event.clientX, startWidth: railWidth };
    event.currentTarget.setPointerCapture(event.pointerId);
    const handleMove = (move: PointerEvent) => {
      if (!dragRef.current) return;
      updateWidth(dragRef.current.startWidth + dragRef.current.startX - move.clientX);
    };
    const handleEnd = () => {
      stopResizeDrag();
    };
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleEnd);
    window.addEventListener("pointercancel", handleEnd);
    cleanupResizeListenersRef.current = () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleEnd);
      window.removeEventListener("pointercancel", handleEnd);
    };
  };
  const handleResizeKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (!onRailWidthChange) return;
    if (event.key === "ArrowLeft") { event.preventDefault(); updateWidth(railWidth + 16); }
    if (event.key === "ArrowRight") { event.preventDefault(); updateWidth(railWidth - 16); }
    if (event.key === "Home") { event.preventDefault(); updateWidth(MIN_RAIL_WIDTH); }
    if (event.key === "End") { event.preventDefault(); updateWidth(MAX_RAIL_WIDTH); }
  };

  const selectSource = useCallback((index: number) => {
    onSelectIndex(index);
    if (isFourPane) setShowOriginal(true);
    if (isContextDock) workbench?.controller.setActivePane("sources");
  }, [isContextDock, isFourPane, onSelectIndex, workbench]);

  const openDocument = useCallback((source: Source, index: number) => {
    onSelectIndex(index);
    if (source.document_id) setShowOriginal(true);
    if (isContextDock) workbench?.controller.setActivePane("document");
  }, [isContextDock, onSelectIndex, workbench]);

  const handleShowOriginalChange = useCallback((next: boolean) => {
    setShowOriginal(next);
    if (isContextDock) workbench?.controller.setActivePane(next ? "document" : "sources");
  }, [isContextDock, workbench]);

  const sourcePane = (
    <SourcesPane
      sources={sources}
      selectedIndex={selectedIndex}
      onSelectIndex={selectSource}
      unavailable={unavailable}
      unavailableReason={unavailableReason}
      messageId={messageId}
      conversationId={conversationId}
      collapsed={presentation === "workbench" && isFourPane ? sourceCollapsed : undefined}
      onCollapsedChange={presentation === "workbench" && isFourPane ? workbench?.preferences.setSourcesCollapsed : undefined}
      onOpenDocument={openDocument}
    />
  );

  const documentViewer = (
    <DocumentViewer
      source={selected}
      sourceIndex={selected ? sources.indexOf(selected) : -1}
      messageId={messageId}
      conversationId={conversationId}
      nearbySearch={nearbySearch}
      onNearbySearchChange={setNearbySearch}
      nearbyPage={nearbyPage}
      onNearbyPageChange={setNearbyPage}
      textScale={textScale}
      onTextScaleChange={setTextScale}
      onOpenCurrentSource={onOpenCurrentSource}
      showOriginal={isFourPane ? true : showOriginal}
      onShowOriginalChange={handleShowOriginalChange}
      onCollapse={presentation === "workbench" && isFourPane ? () => workbench?.preferences.setDocumentCollapsed(true) : undefined}
      readerSession={readerSession}
    />
  );

  if (!isOpen) return null;

  if (presentation === "workbench" && (isFourPane || isContextDock)) {
    const activePane = workbench?.controller.state.activePane ?? "sources";
    const contextToolbar = (
      <div className="context-panel__toolbar workbench-context__toolbar">
        {isContextDock ? (
          <div className="workbench-context__switcher" role="tablist" aria-label={locale === "vi" ? "Bảng ngữ cảnh" : "Context panes"}>
            <button type="button" role="tab" aria-selected={activePane === "sources"} onClick={() => workbench?.controller.setActivePane("sources")}>
              {locale === "vi" ? "Nguồn" : "Sources"}
            </button>
            <button type="button" role="tab" aria-selected={activePane === "document"} onClick={() => { setShowOriginal(true); workbench?.controller.setActivePane("document"); }}>
              {locale === "vi" ? "Tài liệu" : "Document"}
            </button>
          </div>
        ) : <span>{locale === "vi" ? "Nguồn và tài liệu" : "Sources and document"}</span>}
        <button
          ref={closeButtonRef}
          type="button"
          className="context-panel__close"
          aria-label={locale === "vi" ? "Đóng trình kiểm tra bằng chứng" : "Close evidence inspector"}
          onClick={onClose}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    );

    if (isFourPane) {
      return (
        <aside
          className="workbench-evidence-layout workbench-evidence-layout--four-pane context-panel"
          data-workbench-context="true"
          data-workbench-layout-mode="four-pane"
          aria-label={locale === "vi" ? "Nguồn và tài liệu" : "Sources and document"}
        >
          {contextToolbar}
          <PaneResizer
            pane="sources"
            width={workbench?.preferences.sourcesWidth ?? WORKBENCH_PANE_LIMITS.sources.default}
            collapsed={sourceCollapsed}
            onCommit={workbench?.preferences.setSourcesWidth ?? (() => undefined)}
            onReset={() =>
              workbench?.preferences.commit({ sourcesWidth: WORKBENCH_PANE_LIMITS.sources.default })
            }
            onCollapsedChange={workbench?.preferences.setSourcesCollapsed}
          />
          {sourcePane}
          <PaneResizer
            pane="document"
            width={workbench?.preferences.documentWidth ?? WORKBENCH_PANE_LIMITS.document.default}
            collapsed={documentCollapsed}
            onCommit={workbench?.preferences.setDocumentWidth ?? (() => undefined)}
            onReset={() =>
              workbench?.preferences.commit({ documentWidth: WORKBENCH_PANE_LIMITS.document.default })
            }
            onCollapsedChange={workbench?.preferences.setDocumentCollapsed}
          />
          {documentCollapsed ? (
            <CollapsedDocumentPane onExpand={() => workbench?.preferences.setDocumentCollapsed(false)} />
          ) : (
            documentViewer
          )}
        </aside>
      );
    }

    return (
      <aside
        className="workbench-evidence-layout workbench-evidence-layout--context-dock context-panel"
        data-workbench-context="true"
        data-workbench-layout-mode="context-dock"
        aria-label={locale === "vi" ? "Nguồn và tài liệu" : "Sources and document"}
      >
        {contextToolbar}
        {activePane === "document" ? documentViewer : sourcePane}
      </aside>
    );
  }

  const panel = (
    <aside className="evidence-workspace-rail context-panel" aria-label={locale === "vi" ? "Nguồn và bằng chứng" : "Sources and evidence"}>
      <div className="context-panel__toolbar">
        <span>{locale === "vi" ? "Trình kiểm tra bằng chứng" : "Evidence inspector"}</span>
        <button
          ref={closeButtonRef}
          type="button"
          className="context-panel__close"
          aria-label={locale === "vi" ? "Đóng trình kiểm tra bằng chứng" : "Close evidence inspector"}
          onClick={onClose}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      {presentation === "inline" && onRailWidthChange && <div
        className="context-panel__resize-handle"
        role="separator"
        tabIndex={0}
        aria-orientation="vertical"
        aria-valuemin={MIN_RAIL_WIDTH}
        aria-valuemax={MAX_RAIL_WIDTH}
        aria-valuenow={railWidth}
        aria-label={locale === "vi" ? "Đổi độ rộng bảng bằng chứng" : "Resize evidence panel"}
        onPointerDown={handlePointerDown}
        onKeyDown={handleResizeKeyDown}
      />}
      {sourcePane}
      {documentViewer}
    </aside>
  );

  const useEvidenceModal = presentation === "drawer" || (
    presentation === "workbench" &&
    workbenchMode !== null &&
    !isFourPane &&
    !isContextDock
  );

  if (useEvidenceModal) {
    return (
      <ModalDialog
        open
        onClose={onClose ?? (() => undefined)}
        ariaLabel={locale === "vi" ? "Trình kiểm tra bằng chứng" : "Evidence inspector"}
        initialFocusRef={closeButtonRef}
        overlayClassName="evidence-drawer-overlay"
        className="evidence-drawer-dialog"
      >
        {panel}
      </ModalDialog>
    );
  }

  return panel;
}
