import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Expand,
  FileSearch,
  Minus,
  Plus,
  RotateCcw,
  Search,
  Shrink,
} from "lucide-react";
import { describeRequestError } from "../lib/requestError";
import { useLocale } from "../lib/i18n";
import {
  generatePdfRepresentation,
  getPdfContentUrl,
  getPdfManifest,
} from "../lib/api";
import type {
  PdfMappingRect,
  PdfMappingStatus,
  PdfRepresentationManifest,
} from "../types";
import type { ReaderSessionController } from "../hooks/useReaderSession";
import type { Source } from "../types";
import "../styles/pdf-viewer.css";

type PdfJsModule = typeof import("pdfjs-dist");

export interface PdfDocumentViewerProps {
  documentId: string;
  manifest: PdfRepresentationManifest;
  indexedSource?: Source;
  readerSession?: ReaderSessionController;
  findQuery?: string;
  onFindQueryChange?: (query: string) => void;
  onManifestChange?: (manifest: PdfRepresentationManifest) => void;
  highlightRects?: PdfMappingRect[];
  evidenceStatus?: PdfMappingStatus | null;
  evidenceMessage?: string | null;
  onEvidenceActivate?: () => void;
  initialPage?: number | null;
  focusPage?: number | null;
  downloadName?: string;
}

type PdfLoadState = "idle" | "generating" | "loading" | "ready" | "error";

interface SearchResult {
  page: number;
  preview: string;
}

function isAbortError(reason: unknown): boolean {
  return reason instanceof DOMException && reason.name === "AbortError";
}

function pageRectStyle(rect: PdfMappingRect, pageHeight: number, scale: number) {
  return {
    left: `${rect.x * scale}px`,
    top: `${(pageHeight - rect.y - rect.h) * scale}px`,
    width: `${rect.w * scale}px`,
    height: `${rect.h * scale}px`,
  };
}

export function PdfDocumentViewer({
  documentId,
  manifest: initialManifest,
  indexedSource,
  readerSession,
  findQuery: controlledFindQuery,
  onFindQueryChange,
  onManifestChange,
  highlightRects = [],
  evidenceStatus = null,
  evidenceMessage = null,
  onEvidenceActivate,
  initialPage,
  focusPage,
  downloadName = "derived-sec-filing.pdf",
}: PdfDocumentViewerProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const rootRef = useRef<HTMLElement>(null);
  const pageHostRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const textLayerRef = useRef<HTMLDivElement>(null);
  const pdfjsRef = useRef<PdfJsModule | null>(null);
  const renderTaskRef = useRef<import("pdfjs-dist").RenderTask | null>(null);
  const textLayerTaskRef = useRef<import("pdfjs-dist").TextLayer | null>(null);
  const pdfRef = useRef<import("pdfjs-dist").PDFDocumentProxy | null>(null);
  const loadingTaskRef = useRef<import("pdfjs-dist").PDFDocumentLoadingTask | null>(null);
  const loadGenerationRef = useRef(0);
  const searchGenerationRef = useRef(0);
  const [manifest, setManifest] = useState(initialManifest);
  const [pdf, setPdf] = useState<import("pdfjs-dist").PDFDocumentProxy | null>(null);
  const [loadState, setLoadState] = useState<PdfLoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(Math.max(1, initialPage ?? 1));
  const [scale, setScale] = useState(1);
  const [fitMode, setFitMode] = useState<"manual" | "width" | "page">("width");
  const [findQuery, setFindQuery] = useState(controlledFindQuery ?? "");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [retryNonce, setRetryNonce] = useState(0);
  const [renderedSize, setRenderedSize] = useState({ width: 0, height: 0 });
  const selectReaderSession = readerSession?.select;
  const isReaderSessionCurrent = readerSession?.isCurrent;

  useEffect(() => setManifest(initialManifest), [initialManifest]);
  useEffect(() => {
    if (controlledFindQuery !== undefined) setFindQuery(controlledFindQuery);
  }, [controlledFindQuery]);

  const updateFindQuery = useCallback((value: string) => {
    setFindQuery(value);
    onFindQueryChange?.(value);
  }, [onFindQueryChange]);

  const setCurrentPage = useCallback((next: number) => {
    const pageCount = pdf?.numPages ?? manifest.page_count ?? 1;
    setPage(Math.max(1, Math.min(pageCount, Math.round(next))));
  }, [manifest.page_count, pdf?.numPages]);

  const refreshManifest = useCallback(async (signal: AbortSignal) => {
    const next = await getPdfManifest(documentId, signal);
    setManifest(next);
    onManifestChange?.(next);
    return next;
  }, [documentId, onManifestChange]);

  useEffect(() => {
    const generation = ++loadGenerationRef.current;
    const controller = new AbortController();
    const sessionGeneration = selectReaderSession?.({
      documentId,
      sourceKey: indexedSource?.chunk_id ?? indexedSource?.chunk_text_hash ?? null,
      representation: "pdf",
    }) ?? null;
    let cancelled = false;
    const isCurrent = () => !cancelled && (!isReaderSessionCurrent || (sessionGeneration !== null && isReaderSessionCurrent(sessionGeneration)));

    setPdf(null);
    const previousPdf = pdfRef.current;
    pdfRef.current = null;
    void previousPdf?.cleanup();
    void loadingTaskRef.current?.destroy();
    loadingTaskRef.current = null;
    setError(null);
    setSearchResults([]);
    setRenderedSize({ width: 0, height: 0 });
    setPage(Math.max(1, initialPage ?? 1));

    const load = async () => {
      try {
        let current = manifest;
        if (current.artifact_status === "supported" || current.artifact_status === "stale") {
          setLoadState("generating");
          current = await generatePdfRepresentation(documentId, controller.signal);
          if (!isCurrent()) return;
          setManifest(current);
          onManifestChange?.(current);
        } else if (current.artifact_status === "generating") {
          setLoadState("generating");
          for (let attempt = 0; attempt < 30; attempt += 1) {
            await new Promise<void>((resolve) => window.setTimeout(resolve, 500));
            current = await refreshManifest(controller.signal);
            if (current.artifact_status !== "generating") break;
          }
        }
        if (!isCurrent()) return;
        if (current.artifact_status !== "available" || !current.artifact_hash) {
          setLoadState("error");
          setError(current.reason || (vi ? "PDF không khả dụng." : "The PDF representation is not available."));
          return;
        }
        setLoadState("loading");
        const pdfjsLib = await import("pdfjs-dist");
        pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
          "pdfjs-dist/build/pdf.worker.mjs",
          import.meta.url,
        ).toString();
        pdfjsRef.current = pdfjsLib;
        const loadingTask = pdfjsLib.getDocument({ url: getPdfContentUrl(documentId) });
        loadingTaskRef.current = loadingTask;
        const loaded = await loadingTask.promise;
        if (!isCurrent() || generation !== loadGenerationRef.current) {
          await loaded.cleanup();
          return;
        }
        setPdf(loaded);
        pdfRef.current = loaded;
        setPage((currentPage) => Math.max(1, Math.min(loaded.numPages, currentPage)));
        setLoadState("ready");
      } catch (reason) {
        if (!isCurrent() || isAbortError(reason)) return;
        setLoadState("error");
        setError(describeRequestError(reason, vi ? "Không thể tải PDF." : "Could not load the PDF representation.", vi ? "vi" : "en").message);
      }
    };
    void load();
    return () => {
      cancelled = true;
      controller.abort();
      renderTaskRef.current?.cancel();
      textLayerTaskRef.current?.cancel();
      renderTaskRef.current = null;
      textLayerTaskRef.current = null;
      const current = pdfRef.current;
      pdfRef.current = null;
      void current?.cleanup();
      void loadingTaskRef.current?.destroy();
      loadingTaskRef.current = null;
      pdfjsRef.current = null;
    };
  }, [documentId, indexedSource?.chunk_id, indexedSource?.chunk_text_hash, initialPage, manifest.artifact_hash, selectReaderSession, isReaderSessionCurrent, refreshManifest, onManifestChange, retryNonce, vi]);

  const fitScale = useCallback(async (mode: "width" | "page") => {
    if (!pdf || !pageHostRef.current) return;
    const currentPage = await pdf.getPage(page);
    const base = currentPage.getViewport({ scale: 1 });
    const host = pageHostRef.current;
    const horizontalPadding = 24;
    const widthScale = Math.max(0.35, (host.clientWidth - horizontalPadding) / base.width);
    const pageScale = Math.max(0.35, Math.min(widthScale, (host.clientHeight - 24) / base.height));
    setScale(mode === "width" ? widthScale : pageScale);
  }, [page, pdf]);

  useEffect(() => {
    if (!pdf || fitMode === "manual") return;
    void fitScale(fitMode);
  }, [fitMode, fitScale, pdf]);

  useEffect(() => {
    if (!pdf || !focusPage) return;
    setCurrentPage(focusPage);
  }, [focusPage, pdf, setCurrentPage]);

  useEffect(() => {
    const pdfjsLib = pdfjsRef.current;
    if (!pdf || !pdfjsLib || !canvasRef.current || !textLayerRef.current) return;
    let cancelled = false;
    renderTaskRef.current?.cancel();
    textLayerTaskRef.current?.cancel();
    const render = async () => {
      const pdfPage = await pdf.getPage(page);
      const viewport = pdfPage.getViewport({ scale });
      const canvas = canvasRef.current;
      const textLayer = textLayerRef.current;
      if (!canvas || !textLayer || cancelled) return;
      const pixelRatio = window.devicePixelRatio || 1;
      canvas.width = Math.ceil(viewport.width * pixelRatio);
      canvas.height = Math.ceil(viewport.height * pixelRatio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      setRenderedSize({ width: viewport.width, height: viewport.height });
      textLayer.replaceChildren();
      textLayer.style.width = `${viewport.width}px`;
      textLayer.style.height = `${viewport.height}px`;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("The PDF canvas is unavailable.");
      const renderTask = pdfPage.render({
        canvas,
        canvasContext: context,
        viewport,
        transform: pixelRatio !== 1 ? [pixelRatio, 0, 0, pixelRatio, 0, 0] : undefined,
      });
      renderTaskRef.current = renderTask;
      await renderTask.promise;
      const textContent = await pdfPage.getTextContent();
      const textLayerTask = new pdfjsLib.TextLayer({ textContentSource: textContent, container: textLayer, viewport });
      textLayerTaskRef.current = textLayerTask;
      await textLayerTask.render();
    };
    void render().catch((reason) => {
      if (!cancelled && !isAbortError(reason)) setError(describeRequestError(reason, vi ? "Không thể hiển thị trang PDF." : "Could not render this PDF page.", vi ? "vi" : "en").message);
    });
    return () => {
      cancelled = true;
      renderTaskRef.current?.cancel();
      textLayerTaskRef.current?.cancel();
    };
  }, [page, pdf, scale, vi]);

  const runSearch = useCallback(async () => {
    const query = findQuery.trim().toLocaleLowerCase();
    if (!pdf || query.length < 2) {
      setSearchResults([]);
      return;
    }
    const generation = ++searchGenerationRef.current;
    setSearching(true);
    const results: SearchResult[] = [];
    try {
      for (let index = 1; index <= pdf.numPages; index += 1) {
        const pdfPage = await pdf.getPage(index);
        const content = await pdfPage.getTextContent();
        const text = content.items.map((item) => "str" in item ? item.str : "").join(" ");
        const lower = text.toLocaleLowerCase();
        const matchIndex = lower.indexOf(query);
        if (matchIndex >= 0) results.push({ page: index, preview: text.slice(Math.max(0, matchIndex - 48), matchIndex + query.length + 80) });
        if (generation !== searchGenerationRef.current) return;
      }
      setSearchResults(results);
      if (results[0]) setCurrentPage(results[0].page);
    } finally {
      if (generation === searchGenerationRef.current) setSearching(false);
    }
  }, [findQuery, pdf, setCurrentPage]);

  const toggleFullscreen = useCallback(async () => {
    const element = rootRef.current;
    if (!element) return;
    if (document.fullscreenElement) {
      await document.exitFullscreen?.();
    } else {
      await element.requestFullscreen?.();
    }
  }, []);

  useEffect(() => {
    const handleFullscreen = () => setFullscreen(document.fullscreenElement === rootRef.current);
    document.addEventListener("fullscreenchange", handleFullscreen);
    return () => document.removeEventListener("fullscreenchange", handleFullscreen);
  }, []);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.tagName === "INPUT" || target?.tagName === "TEXTAREA") {
        if (event.key === "Escape") (target as HTMLInputElement).blur();
        return;
      }
      if (event.key === "ArrowLeft") { event.preventDefault(); setCurrentPage(page - 1); }
      if (event.key === "ArrowRight") { event.preventDefault(); setCurrentPage(page + 1); }
      if (event.key === "+" || event.key === "=") { event.preventDefault(); setFitMode("manual"); setScale((value) => Math.min(3, value + 0.1)); }
      if (event.key === "-") { event.preventDefault(); setFitMode("manual"); setScale((value) => Math.max(0.35, value - 0.1)); }
      if (event.key.toLocaleLowerCase() === "f" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault(); rootRef.current?.querySelector<HTMLInputElement>("[data-pdf-find]")?.focus();
      }
    };
    const root = rootRef.current;
    root?.addEventListener("keydown", handleKey);
    return () => root?.removeEventListener("keydown", handleKey);
  }, [page, setCurrentPage]);

  const currentPageRects = useMemo(() => highlightRects.filter((rect) => rect.page === page), [highlightRects, page]);
  const pageCount = pdf?.numPages ?? manifest.page_count ?? 0;
  const pageHeight = renderedSize.height / Math.max(scale, 0.01);
  const isDerived = manifest.representation_type === "DERIVED_PDF";

  return (
    <section
      ref={rootRef}
      className={`pdf-viewer ${fullscreen ? "is-fullscreen" : ""}`}
      data-pdf-viewer="true"
      data-pdf-state={loadState}
      aria-label={vi ? "Trình xem PDF" : "PDF viewer"}
      tabIndex={0}
    >
      <div className="pdf-viewer__toolbar">
        <div className="pdf-viewer__page-controls" aria-label={vi ? "Điều khiển trang PDF" : "PDF page controls"}>
          <button type="button" onClick={() => setCurrentPage(page - 1)} disabled={page <= 1 || loadState !== "ready"} aria-label={vi ? "Trang trước" : "Previous page"}><ChevronLeft aria-hidden="true" /></button>
          <label className="pdf-viewer__page-input"><span className="sr-only">{vi ? "Trang hiện tại" : "Current page"}</span><input value={page || ""} inputMode="numeric" onChange={(event) => setCurrentPage(Number(event.target.value) || 1)} aria-label={vi ? "Nhập trang PDF" : "PDF page number"} /><span>/ {pageCount || "-"}</span></label>
          <button type="button" onClick={() => setCurrentPage(page + 1)} disabled={!pageCount || page >= pageCount || loadState !== "ready"} aria-label={vi ? "Trang sau" : "Next page"}><ChevronRight aria-hidden="true" /></button>
        </div>
        <div className="pdf-viewer__zoom-controls" aria-label={vi ? "Thu phóng PDF" : "PDF zoom controls"}>
          <button type="button" onClick={() => { setFitMode("manual"); setScale((value) => Math.max(0.35, value - 0.1)); }} disabled={loadState !== "ready"} aria-label={vi ? "Thu nhỏ" : "Zoom out"}><Minus aria-hidden="true" /></button>
          <span aria-live="polite">{Math.round(scale * 100)}%</span>
          <button type="button" onClick={() => { setFitMode("manual"); setScale((value) => Math.min(3, value + 0.1)); }} disabled={loadState !== "ready"} aria-label={vi ? "Phóng to" : "Zoom in"}><Plus aria-hidden="true" /></button>
          <button type="button" className={fitMode === "width" ? "is-selected" : ""} onClick={() => setFitMode("width")} disabled={loadState !== "ready"}>{vi ? "Chiều rộng" : "Fit width"}</button>
          <button type="button" className={fitMode === "page" ? "is-selected" : ""} onClick={() => setFitMode("page")} disabled={loadState !== "ready"}>{vi ? "Trang" : "Fit page"}</button>
        </div>
        <div className="pdf-viewer__actions">
          <form className="pdf-viewer__find" onSubmit={(event) => { event.preventDefault(); void runSearch(); }}>
            <Search aria-hidden="true" />
            <input data-pdf-find value={findQuery} onChange={(event) => updateFindQuery(event.target.value)} placeholder={vi ? "Tìm trong PDF" : "Find in PDF"} aria-label={vi ? "Tìm trong PDF" : "Find in PDF"} />
            <button type="submit" disabled={searching || loadState !== "ready"}>{searching ? "…" : vi ? "Tìm" : "Find"}</button>
          </form>
          <a className="pdf-viewer__icon-button" href={loadState === "ready" ? getPdfContentUrl(documentId) : undefined} download={downloadName} aria-label={isDerived ? (vi ? "Tải PDF dẫn xuất" : "Download generated PDF") : (vi ? "Tải PDF chính thức" : "Download official PDF")} aria-disabled={loadState !== "ready"}><Download aria-hidden="true" /></a>
          <button type="button" onClick={() => void toggleFullscreen()} aria-label={fullscreen ? (vi ? "Thu nhỏ trình xem" : "Exit full screen") : (vi ? "Mở rộng trình xem" : "Expand PDF viewer")}><>{fullscreen ? <Shrink aria-hidden="true" /> : <Expand aria-hidden="true" />}</></button>
        </div>
      </div>

      <div className="pdf-viewer__identity">
        <div>
          <strong>{isDerived ? (vi ? "PDF dẫn xuất" : "Generated PDF") : (vi ? "PDF chính thức" : "Official PDF")}</strong>
          <span>{isDerived ? (vi ? "Được tạo từ hồ sơ SEC chính thức" : "Derived from official SEC filing") : (vi ? "Artifact PDF chính thức đã xác minh" : "Verified official PDF artifact")}</span>
        </div>
        {manifest.page_semantics === "generated_representation_pages" && <span className="pdf-viewer__page-truth">{vi ? "Số trang của bản tạo" : "Generated-representation pages"}</span>}
      </div>
      {evidenceStatus && evidenceStatus !== "exact" && <div className="pdf-viewer__mapping-status" role="status"><FileSearch aria-hidden="true" /><span>{evidenceMessage || (vi ? "Không thể xác minh vị trí exact trong PDF; Structured vẫn là fallback an toàn." : "Exact PDF evidence location is unavailable; Structured remains the safe fallback.")}</span></div>}
      {evidenceStatus === "exact" && highlightRects.length > 0 && <div className="pdf-viewer__mapping-status pdf-viewer__mapping-status--exact" role="status"><span>{vi ? "Evidence PDF đã được xác minh." : "Verified PDF evidence"}</span></div>}

      <div ref={pageHostRef} className="pdf-viewer__page-host" aria-busy={loadState === "generating" || loadState === "loading"}>
        {loadState === "generating" && <div className="pdf-viewer__state" role="status"><RotateCcw aria-hidden="true" className="pdf-viewer__spinner" /><strong>{vi ? "Đang tạo PDF…" : "Generating PDF…"}</strong><span>{vi ? "Đang dùng nguồn SEC đã xác minh." : "Using the verified SEC filing source."}</span></div>}
        {loadState === "loading" && <div className="pdf-viewer__state" role="status"><RotateCcw aria-hidden="true" className="pdf-viewer__spinner" /><strong>{vi ? "Đang tải PDF…" : "Loading PDF…"}</strong></div>}
        {loadState === "error" && <div className="pdf-viewer__state pdf-viewer__state--error" role="alert"><FileSearch aria-hidden="true" /><strong>{error || (vi ? "PDF không khả dụng." : "PDF unavailable.")}</strong><span>{vi ? "Structured và Normalized vẫn là các lựa chọn đọc an toàn." : "Structured and Normalized remain available reading fallbacks."}</span><button type="button" onClick={() => { setManifest((current) => ({ ...current, artifact_status: "supported", reason: null })); setLoadState("idle"); setError(null); setRetryNonce((value) => value + 1); }}>{vi ? "Thử lại" : "Retry"}</button></div>}
        {loadState === "ready" && (
          <div className="pdf-viewer__page-scroll">
            <div className="pdf-viewer__page" style={{ width: `${renderedSize.width}px`, height: `${renderedSize.height}px` }}>
              <canvas ref={canvasRef} aria-label={`${vi ? "Trang PDF" : "PDF page"} ${page}`} />
              <div ref={textLayerRef} className="pdf-viewer__text-layer" aria-label={vi ? "Lớp văn bản PDF có thể chọn" : "Selectable PDF text layer"} />
              {currentPageRects.map((rect, index) => <button key={`${rect.page}-${index}-${rect.x}-${rect.y}`} type="button" className="pdf-viewer__evidence-highlight" style={pageRectStyle(rect, pageHeight, scale)} onClick={onEvidenceActivate} aria-label={vi ? "Hiện evidence đã xác minh" : "Reveal verified evidence"} />)}
            </div>
          </div>
        )}
      </div>

      {searchResults.length > 0 && <div className="pdf-viewer__search-results" role="status"><strong>{searchResults.length} {vi ? "trang có kết quả" : "pages with matches"}</strong><div>{searchResults.slice(0, 8).map((result) => <button key={result.page} type="button" onClick={() => setCurrentPage(result.page)}><span>{vi ? "Trang" : "Page"} {result.page}</span><span>{result.preview}</span></button>)}</div></div>}
    </section>
  );
}

export default PdfDocumentViewer;
