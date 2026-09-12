import { ArrowLeft, ChevronLeft, ChevronRight, Download, FileText, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getReaderContent, getReaderLocation, getReaderManifest, getReaderOutline, getReaderSectionExportUrl, searchReader } from "../lib/api";
import type { CanonicalSource, EvidenceLocation, EvidenceRange, ReaderCoverageStatus, ReaderManifest, Source, StructuredBlock, StructuredCell, StructuredSearchMatch, StructuredTableMode } from "../types";
import { describeRequestError } from "../lib/requestError";
import { useLocale } from "../lib/i18n";
import { formatCompanyLabel } from "../lib/displayMetadata";
import type { ReaderSessionController } from "../hooks/useReaderSession";
import "../styles/document-reader.css";
import type { ReactNode } from "react";

interface StructuredDocumentReaderProps {
  documentId: string;
  indexedSource?: Source;
  onBack: () => void;
  readerSession?: ReaderSessionController;
  embedded?: boolean;
  onOpenNormalized?: () => void;
}

const CONTENT_LIMIT = 64;

function isAbortError(reason: unknown): boolean {
  return reason instanceof DOMException && reason.name === "AbortError";
}

function SourceLabel({ source }: { source: CanonicalSource }) {
  return <>{source.label}{source.status === "unavailable" ? " — unavailable" : ""}</>;
}

function EvidenceText({ text, range }: { text: string; range?: EvidenceRange }) {
  if (!range) return <>{text}</>;
  const start = Math.max(0, Math.min(text.length, range.start));
  const end = Math.max(start, Math.min(text.length, range.end));
  return <>{text.slice(0, start)}<mark className="structured-reader__evidence-match">{text.slice(start, end)}</mark>{text.slice(end)}</>;
}

function isNumericCell(text: string): boolean {
  return /^\s*(?:[$€£¥]\s*)?\(?[-+]?\d[\d,]*(?:\.\d+)?%?\)?\s*$/.test(text);
}

function renderTableRow(row: StructuredCell[], rowIndex: number, mode: StructuredTableMode) {
  return <tr key={`row-${rowIndex}`}>{row.map((cell, cellIndex) => {
    const Cell = mode === "semantic" && cell.header ? "th" : "td";
    const numeric = isNumericCell(cell.text);
    return <Cell
      key={cell.cell_id ?? `${rowIndex}-${cellIndex}`}
      scope={Cell === "th" ? (rowIndex === 0 ? "col" : "row") : undefined}
      rowSpan={cell.rowspan}
      colSpan={cell.colspan}
      className={numeric ? "structured-reader__numeric-cell" : undefined}
    >{cell.text}</Cell>;
  })}</tr>;
}

function SourceLayoutText({ rows }: { rows: StructuredCell[][] }) {
  return <pre className="structured-reader__source-layout-text">{rows.map((row) => row.map((cell) => cell.text).join("\t")).join("\n")}</pre>;
}

function Block({ block, onAnchor, evidenceRange, onOpenNormalized, vi }: { block: StructuredBlock; onAnchor: (id: string) => void; evidenceRange?: EvidenceRange; onOpenNormalized?: () => void; vi: boolean }) {
  if (block.kind === "heading") {
    const Heading = `h${block.level ?? 2}` as "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
    return <Heading id={block.anchor ?? block.block_id} data-reader-block={block.block_id}><EvidenceText text={block.text} range={evidenceRange} /></Heading>;
  }
  if (block.kind === "paragraph") {
    return <p data-reader-block={block.block_id}>{evidenceRange ? <EvidenceText text={block.text} range={evidenceRange} /> : block.runs.length > 0 ? block.runs.map((run, index) => {
      let value: ReactNode = run.text;
      if (run.strong) value = <strong key={index}>{value}</strong>;
      if (run.emphasis) value = <em key={index}>{value}</em>;
      if (run.superscript) value = <sup key={index}>{value}</sup>;
      if (run.subscript) value = <sub key={index}>{value}</sub>;
      return <span key={index}>{value} </span>;
    }) : block.text}</p>;
  }
  if (block.kind === "list") return <ul data-reader-block={block.block_id}>{block.items.map((item) => <li key={item}><EvidenceText text={item} range={evidenceRange} /></li>)}</ul>;
  if (block.kind === "separator") return <hr data-reader-block={block.block_id} />;
  if (block.kind === "unsupported") return <aside className="structured-reader__unsupported" role="note" data-reader-block={block.block_id}>{block.text}</aside>;
  const mode: StructuredTableMode = block.table_mode ?? "source_layout";
  const headerRows = block.header_rows ?? [];
  const bodyRows = mode === "semantic" && headerRows.length > 0 ? block.rows.slice(block.header_row_count ?? headerRows.length) : block.rows;
  const label = block.caption || (vi ? "Bảng nguồn" : "Source table");
  return (
    <figure className={`structured-reader__table structured-reader__table--${mode} ${evidenceRange ? "is-evidence" : ""}`} data-reader-block={block.block_id}>
      {block.caption && <figcaption>{block.caption}</figcaption>}
      <p className="structured-reader__table-mode" role="status">
        {mode === "semantic"
          ? (vi ? "Bảng có tiêu đề cấu trúc được xác minh." : "Semantic headers verified from the source.")
          : mode === "source_layout"
            ? (vi ? "Bố cục nguồn: giữ nguyên thứ tự ô, không suy diễn tiêu đề tài chính." : "Source layout: cell order is preserved; financial headers are not inferred.")
            : (vi ? "Không thể xác minh cấu trúc bảng; dùng văn bản chuẩn hóa." : "Table structure could not be verified; use normalized text.")}
      </p>
      {block.continuation_index && block.continuation_count && block.continuation_count > 1 && <p className="structured-reader__continuation">Continuation {block.continuation_index} of {block.continuation_count}</p>}
      {mode === "unsupported" ? <>
        <aside className="structured-reader__unsupported" role="note">{block.table_reason || (vi ? "Bảng không được hỗ trợ ở chế độ có cấu trúc." : "This table is not supported in the structured representation.")}</aside>
        {block.rows.length > 0 && <SourceLayoutText rows={block.rows} />}
        {onOpenNormalized && <button type="button" className="structured-reader__fallback-action" onClick={onOpenNormalized}>{vi ? "Mở văn bản chuẩn hóa" : "Open normalized text"}</button>}
      </> : <div className="structured-reader__table-scroll" tabIndex={0} role="region" aria-label={label}>
        <table>
          {mode === "semantic" && headerRows.length > 0 && <thead>{headerRows.map((row, rowIndex) => renderTableRow(row, rowIndex, mode))}</thead>}
          <tbody>{bodyRows.map((row, rowIndex) => renderTableRow(row, rowIndex + (mode === "semantic" ? headerRows.length : 0), mode))}</tbody>
        </table>
      </div>}
      <button type="button" className="structured-reader__anchor-link" onClick={() => onAnchor(block.block_id)}>{vi ? "Đặt bảng vào tiêu điểm" : "Focus table"}</button>
    </figure>
  );
}

export function StructuredDocumentReader({ documentId, indexedSource, onBack, readerSession, embedded = false, onOpenNormalized }: StructuredDocumentReaderProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [manifest, setManifest] = useState<ReaderManifest | null>(null);
  const [sourceId, setSourceId] = useState("");
  const [outline, setOutline] = useState<ReaderManifest["sources"] extends never ? never : Array<{ block_id: string; label: string; level: number; anchor: string }>>([]);
  const [blocks, setBlocks] = useState<StructuredBlock[]>([]);
  const [cursor, setCursor] = useState(0);
  const [nextCursor, setNextCursor] = useState<number | null>(null);
  const [loadingManifest, setLoadingManifest] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [findQuery, setFindQuery] = useState("");
  const [findStatus, setFindStatus] = useState<string | null>(null);
  const [showNormalizedFallback, setShowNormalizedFallback] = useState(false);
  const [coverageStatus, setCoverageStatus] = useState<ReaderCoverageStatus>("unknown");
  const [coverageReason, setCoverageReason] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [textScale, setTextScale] = useState(100);
  const [wide, setWide] = useState(false);
  const [focusBlockId, setFocusBlockId] = useState<string | null>(null);
  const [location, setLocation] = useState<EvidenceLocation | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const manifestRequestId = useRef(0);
  const contentRequestId = useRef(0);
  const outlineRequestId = useRef(0);
  const locationRequestId = useRef(0);
  const manualNavigationRef = useRef(false);
  const readerGenerationRef = useRef<number | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const sessionSelect = readerSession?.select;
  const sessionIsCurrent = readerSession?.isCurrent;

  const isCurrentSession = useCallback(() => {
    const generation = readerGenerationRef.current;
    return !sessionIsCurrent || (generation !== null && sessionIsCurrent(generation));
  }, [sessionIsCurrent]);

  useEffect(() => {
    readerGenerationRef.current = sessionSelect?.({ documentId, sourceKey: indexedSource?.chunk_id ?? null, representation: "structured" }) ?? null;
    const controller = new AbortController();
    const requestId = ++manifestRequestId.current;
    setLoadingManifest(true);
    setError(null);
    setManifest(null);
    setCoverageStatus("unknown");
    setCoverageReason(null);
    setSourceId("");
    setBlocks([]);
    setOutline([]);
    void getReaderManifest(documentId, controller.signal).then((response) => {
      if (requestId !== manifestRequestId.current || !isCurrentSession()) return;
      setManifest(response);
      const structuredRepresentation = response.representations.find((representation) => representation.kind === "structured");
      setCoverageStatus(structuredRepresentation?.coverage_status ?? "unknown");
      setCoverageReason(structuredRepresentation?.coverage_reason ?? null);
      setSourceId(response.sources.find((source) => source.status === "available")?.source_document_id ?? "");
    }).catch((reason) => {
      if (requestId !== manifestRequestId.current || !isCurrentSession() || isAbortError(reason)) return;
      setError(describeRequestError(reason, vi ? "Không thể tải thông tin tài liệu." : "Could not load the document manifest.", vi ? "vi" : "en").message);
    }).finally(() => {
      if (requestId === manifestRequestId.current && isCurrentSession()) setLoadingManifest(false);
    });
    return () => controller.abort();
  }, [documentId, indexedSource?.chunk_id, isCurrentSession, sessionSelect, vi]);

  const selectedSource = useMemo(() => manifest?.sources.find((source) => source.source_document_id === sourceId) ?? null, [manifest, sourceId]);
  const sourceParams = useMemo(() => selectedSource && manifest ? {
    source_document_id: selectedSource.source_document_id,
    source_set_revision: manifest.source_set_revision,
    document_revision: selectedSource.document_revision ?? "",
  } : null, [manifest, selectedSource]);
  const structuredRepresentation = useMemo(
    () => manifest?.representations.find((representation) => representation.kind === "structured") ?? null,
    [manifest],
  );

  useEffect(() => {
    if (!sourceParams?.document_revision || !selectedSource || selectedSource.status !== "available" || structuredRepresentation?.status === "unavailable") return;
    const controller = new AbortController();
    const requestId = ++outlineRequestId.current;
    void getReaderOutline(documentId, { ...sourceParams, limit: 50 }, controller.signal).then((response) => {
      if (requestId === outlineRequestId.current && isCurrentSession()) setOutline(response.items);
    }).catch((reason) => {
      if (requestId === outlineRequestId.current && isCurrentSession() && !isAbortError(reason)) setOutline([]);
    });
    return () => controller.abort();
  }, [documentId, isCurrentSession, selectedSource, sourceParams, structuredRepresentation]);

  useEffect(() => {
    setCursor(0);
    setNextCursor(null);
    setBlocks([]);
    setFindStatus(null);
    setShowNormalizedFallback(false);
  }, [sourceId]);

  useEffect(() => {
    if (!sourceParams?.source_document_id || !indexedSource?.chunk_id || !indexedSource.chunk_text_hash) {
      setLocation(null);
      setLocationError(null);
      return;
    }
    const controller = new AbortController();
    const requestId = ++locationRequestId.current;
    setLocationError(null);
    void getReaderLocation(indexedSource.chunk_id, {
      chunk_text_hash: indexedSource.chunk_text_hash,
      source_set_revision: sourceParams.source_set_revision,
    }, controller.signal).then((response) => {
      if (requestId !== locationRequestId.current || !isCurrentSession()) return;
      setLocation(response);
      if (response.status === "exact" && !manualNavigationRef.current) {
        if (response.source_document_id && response.source_document_id !== sourceId) setSourceId(response.source_document_id);
        const range = response.ranges[0];
        if (range) setFocusBlockId(range.block_id);
      }
    }).catch((reason) => {
      if (requestId !== locationRequestId.current || !isCurrentSession() || isAbortError(reason)) return;
      setLocation(null);
      setLocationError(describeRequestError(reason, vi ? "Không thể xác minh vị trí evidence." : "Could not verify evidence location.", vi ? "vi" : "en").message);
    });
    return () => {
      controller.abort();
      locationRequestId.current += 1;
    };
  }, [documentId, indexedSource?.chunk_id, indexedSource?.chunk_text_hash, isCurrentSession, sourceId, sourceParams]);

  useEffect(() => {
    if (!sourceParams?.document_revision || !selectedSource || selectedSource.status !== "available" || structuredRepresentation?.status === "unavailable") {
      setLoadingContent(false);
      return;
    }
    const controller = new AbortController();
    const requestId = ++contentRequestId.current;
    setLoadingContent(true);
    setError(null);
    void getReaderContent(documentId, { ...sourceParams, cursor, limit: CONTENT_LIMIT }, controller.signal).then((response) => {
      if (requestId !== contentRequestId.current || !isCurrentSession()) return;
      setBlocks(response.blocks);
      setNextCursor(response.next_cursor);
      if (response.coverage_status) setCoverageStatus(response.coverage_status);
      if (response.coverage_reason !== undefined) setCoverageReason(response.coverage_reason ?? null);
    }).catch((reason) => {
      if (requestId !== contentRequestId.current || !isCurrentSession() || isAbortError(reason)) return;
      setError(describeRequestError(reason, vi ? "Không thể tải nội dung có cấu trúc." : "Could not load structured document content.", vi ? "vi" : "en").message);
    }).finally(() => {
      if (requestId === contentRequestId.current && isCurrentSession()) setLoadingContent(false);
    });
    return () => controller.abort();
  }, [cursor, documentId, isCurrentSession, selectedSource, sourceParams, structuredRepresentation, vi]);

  useEffect(() => {
    if (!focusBlockId) return;
    const node = contentRef.current?.querySelector<HTMLElement>(`[data-reader-block="${CSS.escape(focusBlockId)}"]`);
    node?.scrollIntoView({ block: "start" });
  }, [blocks, focusBlockId]);

  const runFind = async () => {
    const query = findQuery.trim();
    if (!sourceParams?.document_revision) return;
    if (query.length < 2) {
      setFindStatus(vi ? "Nhập ít nhất 2 ký tự để tìm." : "Enter at least 2 characters to find.");
      return;
    }
    const controller = new AbortController();
    setFindStatus(null);
    setShowNormalizedFallback(false);
    try {
      const response = await searchReader(documentId, { ...sourceParams, q: query, limit: 50 }, controller.signal);
      if (response.coverage_status) setCoverageStatus(response.coverage_status);
      if (response.coverage_reason !== undefined) setCoverageReason(response.coverage_reason ?? null);
      const match: StructuredSearchMatch | undefined = response.matches[0];
      if (!match) {
        const incomplete = (response.coverage_status ?? coverageStatus) !== "complete";
        setFindStatus(incomplete ? (vi ? "Không tìm thấy trong chế độ xem có cấu trúc này." : "No matches in this structured view.") : (vi ? "Không tìm thấy trong tài liệu này." : "No matches in this document."));
        setShowNormalizedFallback(incomplete);
        return;
      }
      setFocusBlockId(match.block_id);
      setFindStatus(`${response.total} ${vi ? "kết quả" : "matches"}`);
    } catch (reason) {
      if (!isAbortError(reason)) setFindStatus(describeRequestError(reason, vi ? "Không thể tìm trong tài liệu." : "Could not search this document.", vi ? "vi" : "en").message);
    }
  };

  if (loadingManifest) return <section className="structured-reader" aria-labelledby={!embedded ? "structured-reader-title" : undefined} aria-label={embedded ? (vi ? "Tài liệu có cấu trúc" : "Structured document") : undefined}>{!embedded && <ReaderHeader onBack={onBack} vi={vi} />}<p className="structured-reader__status" role="status">{vi ? "Đang kiểm tra tài liệu…" : "Checking document…"}</p></section>;
  if (error && !manifest) return <section className="structured-reader" aria-labelledby={!embedded ? "structured-reader-title" : undefined} aria-label={embedded ? (vi ? "Tài liệu có cấu trúc" : "Structured document") : undefined}>{!embedded && <ReaderHeader onBack={onBack} vi={vi} />}<div className="structured-reader__error" role="alert">{error}</div></section>;

  const available = Boolean(selectedSource && selectedSource.status === "available" && sourceParams?.document_revision && structuredRepresentation?.status !== "unavailable");
  const identity = manifest?.identity;
  const primaryUrl = manifest?.sources.find((source) => source.role === "primary_filing")?.canonical_url;
  const sourceSet = manifest?.sources ?? [];
  const coverageLabel = coverageStatus === "complete"
    ? (vi ? "Đã xác minh phạm vi văn bản của chế độ xem có cấu trúc" : "Structured view coverage verified")
    : coverageStatus === "partial"
      ? (vi ? "Chế độ xem có cấu trúc chỉ bao phủ một phần; hãy tìm trong văn bản chuẩn hóa để có đầy đủ văn bản cục bộ." : "Structured view has partial coverage; search normalized text for complete local text.")
      : (vi ? "Chưa xác minh phạm vi của chế độ xem có cấu trúc; hãy tìm trong văn bản chuẩn hóa." : "Structured view coverage is unknown; search normalized text for complete local text.");
  return (
    <section className={`structured-reader ${wide ? "is-wide" : ""}`} aria-labelledby={!embedded ? "structured-reader-title" : undefined} aria-label={embedded ? (vi ? "Tài liệu có cấu trúc" : "Structured document") : undefined}>
      {!embedded && <ReaderHeader onBack={onBack} vi={vi} />}
      {!embedded && <header className="structured-reader__identity">
        <div>
          <p className="evidence-rail-eyebrow">{vi ? "Tài liệu có cấu trúc" : "Structured document"}</p>
          <h2 id="structured-reader-title">{identity?.ticker ? formatCompanyLabel(identity.ticker) : documentId}</h2>
          <p>{identity?.accession_number ?? (vi ? "Chưa xác minh accession" : "Accession not verified")} {identity?.filing_date ? ` · ${identity.filing_date}` : ""}</p>
        </div>
        <FileText aria-hidden="true" />
      </header>}
      <div className="structured-reader__toolbar" aria-label={vi ? "Công cụ đọc tài liệu" : "Document reading tools"}>
        <label><span>{vi ? "Nguồn" : "Source"}</span><select value={sourceId} onChange={(event) => setSourceId(event.target.value)} aria-label={vi ? "Chọn nguồn tài liệu" : "Select document source"}>{sourceSet.map((source) => <option key={source.source_document_id} value={source.source_document_id} disabled={source.status !== "available"}><SourceLabel source={source} /></option>)}</select></label>
        <div className="structured-reader__controls"><button type="button" onClick={() => setTextScale((value) => Math.max(90, value - 10))} disabled={textScale <= 90} aria-label={vi ? "Giảm cỡ chữ" : "Decrease text size"}>A−</button><span>{textScale}%</span><button type="button" onClick={() => setTextScale((value) => Math.min(130, value + 10))} disabled={textScale >= 130} aria-label={vi ? "Tăng cỡ chữ" : "Increase text size"}>A+</button><button type="button" onClick={() => setWide((value) => !value)} aria-pressed={wide}>{wide ? (vi ? "Độ rộng chuẩn" : "Standard width") : (vi ? "Mở rộng" : "Widen")}</button>{primaryUrl && <a href={primaryUrl} target="_blank" rel="noreferrer">{vi ? "Mở SEC" : "Open SEC"}</a>}<a href={sourceParams ? getReaderSectionExportUrl(documentId, { ...sourceParams, format: "html" }) : undefined} download>{<Download aria-hidden="true" />}{vi ? "Xuất mục đọc" : "Export reading"}</a></div>
      </div>
      <div className="structured-reader__availability" role="status"><span>{available ? (vi ? "Nguồn HTML có cấu trúc sẵn sàng" : "Structured HTML source ready") : (vi ? "Nguồn đầy đủ chưa khả dụng" : "Full source unavailable")}</span><span>{coverageLabel}</span><span>{vi ? "PDF chưa khả dụng trong corpus hiện tại" : "PDF is not available in the current corpus"}</span></div>
      {!available ? <div className="structured-reader__fallback" role="status">{vi ? "Bản đọc có cấu trúc chưa khả dụng; indexed excerpt vẫn được giữ nguyên." : "The structured document is unavailable; the indexed excerpt remains available."}</div> : <>
        <div className="structured-reader__find"><Search aria-hidden="true" /><label className="sr-only" htmlFor="structured-reader-find">{vi ? "Tìm trong tài liệu" : "Find in document"}</label><input id="structured-reader-find" value={findQuery} onChange={(event) => setFindQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runFind(); }} placeholder={vi ? "Tìm trong tài liệu…" : "Find in document…"} maxLength={200} /><button type="button" onClick={() => void runFind()}>{vi ? "Tìm" : "Find"}</button>{findStatus && <span role="status">{findStatus}</span>}{showNormalizedFallback && onOpenNormalized && <button type="button" className="structured-reader__fallback-action" onClick={onOpenNormalized}>{vi ? "Tìm trong văn bản chuẩn hóa" : "Search normalized text"}</button>}</div>
        {locationError && <p className="structured-reader__limitation" role="status">{locationError}</p>}
        {coverageReason && coverageStatus !== "complete" && <p className="structured-reader__limitation" role="status">{coverageReason}</p>}
        {location && <p className={`structured-reader__location structured-reader__location--${location.status}`} role="status">{location.status === "exact" ? (vi ? "Evidence đã được xác minh trong tài liệu có cấu trúc." : "Evidence correspondence verified in the structured document.") : location.reason}</p>}
        <div className="structured-reader__layout">
          <nav className="structured-reader__outline" aria-label={vi ? "Mục lục tài liệu" : "Document outline"}><h3>{vi ? "Mục lục" : "Outline"}</h3>{outline.length === 0 ? <p>{vi ? "Không phát hiện tiêu đề." : "No source headings detected."}</p> : outline.map((item) => <button type="button" key={item.block_id} onClick={() => { manualNavigationRef.current = true; setFocusBlockId(item.block_id); if (!blocks.some((block) => block.block_id === item.block_id)) setFindStatus(vi ? "Tiếp tục đọc để tải mục này." : "Continue reading to load this section."); }}>{item.label}</button>)}</nav>
          <article className="structured-reader__canvas" ref={contentRef} data-original-window style={{ fontSize: `${textScale / 100}em` }} aria-busy={loadingContent}>{loadingContent && <p role="status">{vi ? "Đang tải nội dung…" : "Loading document content…"}</p>}{blocks.map((block) => <Block key={block.block_id} block={block} evidenceRange={location?.status === "exact" ? location.ranges.find((range) => range.block_id === block.block_id) : undefined} onAnchor={setFocusBlockId} onOpenNormalized={onOpenNormalized} vi={vi} />)}{manifest?.reason && <p className="structured-reader__limitation">{manifest.reason}</p>}{nextCursor !== null && <button type="button" className="structured-reader__continue" onClick={() => { manualNavigationRef.current = true; setCursor(nextCursor); }} disabled={loadingContent}>{vi ? "Tiếp tục đọc" : "Continue reading"}<ChevronRight aria-hidden="true" /></button>}{cursor > 0 && <button type="button" className="structured-reader__previous" onClick={() => { manualNavigationRef.current = true; setCursor(Math.max(0, cursor - CONTENT_LIMIT)); }} disabled={loadingContent}><ChevronLeft aria-hidden="true" />{vi ? "Về phần trước" : "Previous section"}</button>}</article>
        </div>
        {manifest?.representations.filter((representation) => representation.status !== "available").map((representation) => <p key={representation.kind} className="structured-reader__limitation">{representation.reason}</p>)}
      </>}
    </section>
  );
}

function ReaderHeader({ onBack, vi }: { onBack: () => void; vi: boolean }) {
  return <div className="structured-reader__header"><button type="button" onClick={onBack} className="structured-reader__back"><ArrowLeft aria-hidden="true" />{vi ? "Về indexed excerpt" : "Back to indexed excerpt"}</button><span>{vi ? "Trình đọc tài liệu" : "Document reader"}</span></div>;
}
