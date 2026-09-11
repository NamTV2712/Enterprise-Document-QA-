import { ArrowLeft, ChevronLeft, ChevronRight, Download, FileText, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getReaderContent, getReaderLocation, getReaderManifest, getReaderOutline, getReaderSectionExportUrl, searchReader } from "../lib/api";
import type { CanonicalSource, EvidenceLocation, EvidenceRange, ReaderManifest, Source, StructuredBlock, StructuredSearchMatch } from "../types";
import { describeRequestError } from "../lib/requestError";
import { useLocale } from "../lib/i18n";
import type { ReaderSessionController } from "../hooks/useReaderSession";
import "../styles/document-reader.css";
import type { ReactNode } from "react";

interface StructuredDocumentReaderProps {
  documentId: string;
  indexedSource?: Source;
  onBack: () => void;
  readerSession?: ReaderSessionController;
  embedded?: boolean;
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

function Block({ block, onAnchor, evidenceRange }: { block: StructuredBlock; onAnchor: (id: string) => void; evidenceRange?: EvidenceRange }) {
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
  return (
    <figure className={`structured-reader__table ${evidenceRange ? "is-evidence" : ""}`} data-reader-block={block.block_id}>
      {block.caption && <figcaption>{block.caption}</figcaption>}
      {block.continuation_index && block.continuation_count && block.continuation_count > 1 && <p className="structured-reader__continuation">Continuation {block.continuation_index} of {block.continuation_count}</p>}
      <div className="structured-reader__table-scroll" tabIndex={0} role="region" aria-label={block.caption || "Financial table"}>
        <table>
          <thead><tr>{block.columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead>
          <tbody>{block.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => {
            const Cell = cell.header ? "th" : "td";
            return <Cell key={`${rowIndex}-${cellIndex}`} scope={cell.header ? "row" : undefined} rowSpan={cell.rowspan} colSpan={cell.colspan}>{cell.text}</Cell>;
          })}</tr>)}</tbody>
        </table>
      </div>
      <button type="button" className="structured-reader__anchor-link" onClick={() => onAnchor(block.block_id)}>Keep this table in view</button>
    </figure>
  );
}

export function StructuredDocumentReader({ documentId, indexedSource, onBack, readerSession, embedded = false }: StructuredDocumentReaderProps) {
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
    setSourceId("");
    setBlocks([]);
    setOutline([]);
    void getReaderManifest(documentId, controller.signal).then((response) => {
      if (requestId !== manifestRequestId.current || !isCurrentSession()) return;
      setManifest(response);
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

  useEffect(() => {
    if (!sourceParams?.document_revision || !selectedSource || selectedSource.status !== "available") return;
    const controller = new AbortController();
    const requestId = ++outlineRequestId.current;
    void getReaderOutline(documentId, { ...sourceParams, limit: 50 }, controller.signal).then((response) => {
      if (requestId === outlineRequestId.current && isCurrentSession()) setOutline(response.items);
    }).catch((reason) => {
      if (requestId === outlineRequestId.current && isCurrentSession() && !isAbortError(reason)) setOutline([]);
    });
    return () => controller.abort();
  }, [documentId, isCurrentSession, selectedSource, sourceParams]);

  useEffect(() => {
    setCursor(0);
    setNextCursor(null);
    setBlocks([]);
    setFindStatus(null);
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
    if (!sourceParams?.document_revision || !selectedSource || selectedSource.status !== "available") {
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
    }).catch((reason) => {
      if (requestId !== contentRequestId.current || !isCurrentSession() || isAbortError(reason)) return;
      setError(describeRequestError(reason, vi ? "Không thể tải nội dung có cấu trúc." : "Could not load structured document content.", vi ? "vi" : "en").message);
    }).finally(() => {
      if (requestId === contentRequestId.current && isCurrentSession()) setLoadingContent(false);
    });
    return () => controller.abort();
  }, [cursor, documentId, isCurrentSession, selectedSource, sourceParams, vi]);

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
    try {
      const response = await searchReader(documentId, { ...sourceParams, q: query, limit: 50 }, controller.signal);
      const match: StructuredSearchMatch | undefined = response.matches[0];
      if (!match) {
        setFindStatus(vi ? "Không tìm thấy trong tài liệu này." : "No matches in this document.");
        return;
      }
      setFocusBlockId(match.block_id);
      setFindStatus(`${response.total} ${vi ? "kết quả" : "matches"}`);
    } catch (reason) {
      if (!isAbortError(reason)) setFindStatus(describeRequestError(reason, vi ? "Không thể tìm trong tài liệu." : "Could not search this document.", vi ? "vi" : "en").message);
    }
  };

  if (loadingManifest) return <section className="structured-reader" aria-labelledby="structured-reader-title">{!embedded && <ReaderHeader onBack={onBack} vi={vi} />}<p className="structured-reader__status" role="status">{vi ? "Đang kiểm tra tài liệu…" : "Checking document…"}</p></section>;
  if (error && !manifest) return <section className="structured-reader" aria-labelledby="structured-reader-title">{!embedded && <ReaderHeader onBack={onBack} vi={vi} />}<div className="structured-reader__error" role="alert">{error}</div></section>;

  const available = Boolean(selectedSource && selectedSource.status === "available" && sourceParams?.document_revision);
  const identity = manifest?.identity;
  const primaryUrl = manifest?.sources.find((source) => source.role === "primary_filing")?.canonical_url;
  const sourceSet = manifest?.sources ?? [];
  return (
    <section className={`structured-reader ${wide ? "is-wide" : ""}`} aria-labelledby="structured-reader-title">
      {!embedded && <ReaderHeader onBack={onBack} vi={vi} />}
      <header className="structured-reader__identity">
        <div>
          <p className="evidence-rail-eyebrow">{vi ? "Tài liệu có cấu trúc" : "Structured document"}</p>
          <h2 id="structured-reader-title">{identity?.ticker ?? documentId}</h2>
          <p>{identity?.accession_number ?? (vi ? "Chưa xác minh accession" : "Accession not verified")} {identity?.filing_date ? ` · ${identity.filing_date}` : ""}</p>
        </div>
        <FileText aria-hidden="true" />
      </header>
      <div className="structured-reader__toolbar" aria-label={vi ? "Công cụ đọc tài liệu" : "Document reading tools"}>
        <label><span>{vi ? "Nguồn" : "Source"}</span><select value={sourceId} onChange={(event) => setSourceId(event.target.value)} aria-label={vi ? "Chọn nguồn tài liệu" : "Select document source"}>{sourceSet.map((source) => <option key={source.source_document_id} value={source.source_document_id} disabled={source.status !== "available"}><SourceLabel source={source} /></option>)}</select></label>
        <div className="structured-reader__controls"><button type="button" onClick={() => setTextScale((value) => Math.max(90, value - 10))} disabled={textScale <= 90} aria-label={vi ? "Giảm cỡ chữ" : "Decrease text size"}>A−</button><span>{textScale}%</span><button type="button" onClick={() => setTextScale((value) => Math.min(130, value + 10))} disabled={textScale >= 130} aria-label={vi ? "Tăng cỡ chữ" : "Increase text size"}>A+</button><button type="button" onClick={() => setWide((value) => !value)} aria-pressed={wide}>{wide ? (vi ? "Độ rộng chuẩn" : "Standard width") : (vi ? "Mở rộng" : "Widen")}</button>{primaryUrl && <a href={primaryUrl} target="_blank" rel="noreferrer">{vi ? "Mở SEC" : "Open SEC"}</a>}<a href={sourceParams ? getReaderSectionExportUrl(documentId, { ...sourceParams, format: "html" }) : undefined} download>{<Download aria-hidden="true" />}{vi ? "Xuất mục đọc" : "Export reading"}</a></div>
      </div>
      <div className="structured-reader__availability" role="status"><span>{available ? (vi ? "Nguồn HTML có cấu trúc sẵn sàng" : "Structured HTML source ready") : (vi ? "Nguồn đầy đủ chưa khả dụng" : "Full source unavailable")}</span><span>{vi ? "PDF chưa khả dụng trong corpus hiện tại" : "PDF is not available in the current corpus"}</span></div>
      {!available ? <div className="structured-reader__fallback" role="status">{vi ? "Bản đọc có cấu trúc chưa khả dụng; indexed excerpt vẫn được giữ nguyên." : "The structured document is unavailable; the indexed excerpt remains available."}</div> : <>
        <div className="structured-reader__find"><Search aria-hidden="true" /><label className="sr-only" htmlFor="structured-reader-find">{vi ? "Tìm trong tài liệu" : "Find in document"}</label><input id="structured-reader-find" value={findQuery} onChange={(event) => setFindQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runFind(); }} placeholder={vi ? "Tìm trong tài liệu…" : "Find in document…"} maxLength={200} /><button type="button" onClick={() => void runFind()}>{vi ? "Tìm" : "Find"}</button>{findStatus && <span role="status">{findStatus}</span>}</div>
        {locationError && <p className="structured-reader__limitation" role="status">{locationError}</p>}
        {location && <p className={`structured-reader__location structured-reader__location--${location.status}`} role="status">{location.status === "exact" ? (vi ? "Evidence đã được xác minh trong tài liệu có cấu trúc." : "Evidence correspondence verified in the structured document.") : location.reason}</p>}
        <div className="structured-reader__layout">
          <nav className="structured-reader__outline" aria-label={vi ? "Mục lục tài liệu" : "Document outline"}><h3>{vi ? "Mục lục" : "Outline"}</h3>{outline.length === 0 ? <p>{vi ? "Không phát hiện tiêu đề." : "No source headings detected."}</p> : outline.map((item) => <button type="button" key={item.block_id} onClick={() => { manualNavigationRef.current = true; setFocusBlockId(item.block_id); if (!blocks.some((block) => block.block_id === item.block_id)) setFindStatus(vi ? "Tiếp tục đọc để tải mục này." : "Continue reading to load this section."); }}>{item.label}</button>)}</nav>
          <article className="structured-reader__canvas" ref={contentRef} data-original-window style={{ fontSize: `${textScale / 100}em` }} aria-busy={loadingContent}>{loadingContent && <p role="status">{vi ? "Đang tải nội dung…" : "Loading document content…"}</p>}{blocks.map((block) => <Block key={block.block_id} block={block} evidenceRange={location?.status === "exact" ? location.ranges.find((range) => range.block_id === block.block_id) : undefined} onAnchor={setFocusBlockId} />)}{manifest?.reason && <p className="structured-reader__limitation">{manifest.reason}</p>}{nextCursor !== null && <button type="button" className="structured-reader__continue" onClick={() => { manualNavigationRef.current = true; setCursor(nextCursor); }} disabled={loadingContent}>{vi ? "Tiếp tục đọc" : "Continue reading"}<ChevronRight aria-hidden="true" /></button>}{cursor > 0 && <button type="button" className="structured-reader__previous" onClick={() => { manualNavigationRef.current = true; setCursor(Math.max(0, cursor - CONTENT_LIMIT)); }} disabled={loadingContent}><ChevronLeft aria-hidden="true" />{vi ? "Về phần trước" : "Previous section"}</button>}</article>
        </div>
        {manifest?.representations.filter((representation) => representation.status !== "available").map((representation) => <p key={representation.kind} className="structured-reader__limitation">{representation.reason}</p>)}
      </>}
    </section>
  );
}

function ReaderHeader({ onBack, vi }: { onBack: () => void; vi: boolean }) {
  return <div className="structured-reader__header"><button type="button" onClick={onBack} className="structured-reader__back"><ArrowLeft aria-hidden="true" />{vi ? "Về indexed excerpt" : "Back to indexed excerpt"}</button><span>{vi ? "Trình đọc tài liệu" : "Document reader"}</span></div>;
}
