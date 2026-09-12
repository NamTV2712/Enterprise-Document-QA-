import { ArrowLeft, ChevronLeft, ChevronRight, FileSearch, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getOriginalContent, getOriginalLocation, getOriginalManifest, searchOriginal } from "../lib/api";
import type { OriginalContent, OriginalLocation, OriginalManifest, OriginalSearchMatch, Source } from "../types";
import { describeRequestError } from "../lib/requestError";
import { useLocale } from "../lib/i18n";
import type { ReaderSessionController } from "../hooks/useReaderSession";

interface OriginalDocumentReaderProps {
  documentId: string;
  indexedSource?: Source;
  onBack: () => void;
  readerSession?: ReaderSessionController;
  backLabel?: string;
}

const WINDOW_SIZE = 16_000;

export function OriginalDocumentReader({ documentId, indexedSource, onBack, readerSession, backLabel }: OriginalDocumentReaderProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [manifest, setManifest] = useState<OriginalManifest | null>(null);
  const [sourceId, setSourceId] = useState("");
  const [content, setContent] = useState<OriginalContent | null>(null);
  const [location, setLocation] = useState<OriginalLocation | null>(null);
  const [start, setStart] = useState(0);
  const [findQuery, setFindQuery] = useState("");
  const [activeFind, setActiveFind] = useState("");
  const [matches, setMatches] = useState<OriginalSearchMatch[]>([]);
  const [loadingManifest, setLoadingManifest] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [findError, setFindError] = useState<string | null>(null);
  const manifestRequestId = useRef(0);
  const contentRequestId = useRef(0);
  const locationRequestId = useRef(0);
  const findRequestId = useRef(0);
  const findControllerRef = useRef<AbortController | null>(null);
  const readerGenerationRef = useRef<number | null>(null);

  const isCurrentReaderSession = useCallback(() => {
    const generation = readerGenerationRef.current;
    return !readerSession || (generation !== null && readerSession.isCurrent(generation));
  }, [readerSession]);

  useEffect(() => {
    readerGenerationRef.current = readerSession?.select({
      documentId,
      sourceKey: indexedSource?.chunk_id ?? indexedSource?.chunk_text_hash ?? null,
      representation: "normalized",
    }) ?? null;
    const controller = new AbortController();
    const requestId = ++manifestRequestId.current;
    setLoadingManifest(true);
    setError(null);
    setManifest(null);
    setContent(null);
    setLocation(null);
    setSourceId("");
    void getOriginalManifest(documentId, controller.signal)
      .then((response) => {
        if (requestId !== manifestRequestId.current || !isCurrentReaderSession()) return;
        setManifest(response);
        const firstAvailable = response.sources.find((source) => source.status === "available");
        setSourceId(firstAvailable?.source_document_id ?? "");
      })
      .catch((reason) => {
        if (requestId !== manifestRequestId.current || !isCurrentReaderSession() || (reason instanceof DOMException && reason.name === "AbortError")) return;
        setError(describeRequestError(reason, vi ? "Không thể tải bản gốc." : "Could not load the original-source manifest.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (requestId === manifestRequestId.current && isCurrentReaderSession()) setLoadingManifest(false);
      });
    return () => controller.abort();
  }, [documentId, indexedSource?.chunk_id, indexedSource?.chunk_text_hash, isCurrentReaderSession, readerSession, vi]);

  const selectedManifestSource = useMemo(
    () => manifest?.sources.find((source) => source.source_document_id === sourceId) ?? null,
    [manifest, sourceId],
  );

  useEffect(() => {
    if (!manifest || !selectedManifestSource || selectedManifestSource.status !== "available" || !selectedManifestSource.document_revision) {
      setContent(null);
      setLoadingContent(false);
      return;
    }
    const controller = new AbortController();
    const requestId = ++contentRequestId.current;
    setLoadingContent(true);
    setError(null);
    const hasChunkBinding = Boolean(indexedSource?.chunk_id && indexedSource.chunk_text_hash);
    void getOriginalContent(documentId, {
      source_document_id: selectedManifestSource.source_document_id,
      source_set_revision: manifest.source_set_revision,
      document_revision: selectedManifestSource.document_revision,
      start,
      limit: WINDOW_SIZE,
      chunk_id: hasChunkBinding ? indexedSource?.chunk_id : null,
      chunk_text_hash: hasChunkBinding ? indexedSource?.chunk_text_hash : null,
      find: activeFind || null,
    }, controller.signal)
      .then((response) => {
        if (requestId === contentRequestId.current && isCurrentReaderSession()) setContent(response);
      })
      .catch((reason) => {
        if (requestId !== contentRequestId.current || !isCurrentReaderSession() || (reason instanceof DOMException && reason.name === "AbortError")) return;
        setError(describeRequestError(reason, vi ? "Không thể tải cửa sổ bản gốc." : "Could not load the original text window.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (requestId === contentRequestId.current && isCurrentReaderSession()) setLoadingContent(false);
      });
    return () => controller.abort();
  }, [activeFind, documentId, indexedSource?.chunk_id, indexedSource?.chunk_text_hash, isCurrentReaderSession, manifest, selectedManifestSource, start, vi]);

  useEffect(() => {
    if (!manifest || !indexedSource?.chunk_id || !indexedSource.chunk_text_hash) {
      setLocation(null);
      return;
    }
    const controller = new AbortController();
    const requestId = ++locationRequestId.current;
    void getOriginalLocation(indexedSource.chunk_id, {
      chunk_text_hash: indexedSource.chunk_text_hash,
      source_set_revision: manifest.source_set_revision,
    }, controller.signal)
      .then((response) => {
        if (requestId === locationRequestId.current && isCurrentReaderSession()) setLocation(response);
      })
      .catch((reason) => {
        if (requestId !== locationRequestId.current || !isCurrentReaderSession() || (reason instanceof DOMException && reason.name === "AbortError")) return;
        setLocation(null);
      });
    return () => {
      controller.abort();
      locationRequestId.current += 1;
    };
  }, [indexedSource?.chunk_id, indexedSource?.chunk_text_hash, isCurrentReaderSession, manifest]);

  const runFind = async () => {
    const query = findQuery.trim();
    if (!manifest || !selectedManifestSource || selectedManifestSource.status !== "available" || !selectedManifestSource.document_revision) return;
    if (query.length < 2) {
      setFindError(vi ? "Nhập ít nhất 2 ký tự để tìm." : "Enter at least 2 characters to find.");
      return;
    }
    findControllerRef.current?.abort();
    const controller = new AbortController();
    findControllerRef.current = controller;
    const requestId = ++findRequestId.current;
    setFindError(null);
    try {
      const response = await searchOriginal(documentId, {
        source_document_id: selectedManifestSource.source_document_id,
        source_set_revision: manifest.source_set_revision,
        document_revision: selectedManifestSource.document_revision,
        q: query,
        limit: 100,
      }, controller.signal);
      if (requestId !== findRequestId.current || !isCurrentReaderSession()) return;
      setMatches(response.matches);
      setActiveFind(query);
      const first = response.matches[0];
      if (first) setStart(first.start);
      else setFindError(vi ? "Không tìm thấy trong bản gốc đã chuẩn hóa." : "No matches in the normalized original source.");
    } catch (reason) {
      if (requestId !== findRequestId.current || !isCurrentReaderSession() || (reason instanceof DOMException && reason.name === "AbortError")) return;
      setFindError(describeRequestError(reason, vi ? "Không thể tìm trong bản gốc." : "Could not search the original source.", vi ? "vi" : "en").message);
    } finally {
      if (requestId === findRequestId.current) findControllerRef.current = null;
    }
  };

  if (loadingManifest) {
    return <section className="original-reader" aria-labelledby="original-reader-title"><div className="original-reader__header"><button type="button" onClick={onBack} className="original-reader__back"><ArrowLeft className="h-4 w-4" aria-hidden="true" />{backLabel ?? (vi ? "Về indexed excerpt" : "Back to indexed excerpt")}</button><h2 id="original-reader-title">{vi ? "Original source" : "Original source"}</h2></div><p role="status" className="original-reader__status">{vi ? "Đang kiểm tra bản gốc…" : "Checking original source…"}</p></section>;
  }

  if (error && !manifest) {
    return <section className="original-reader" aria-labelledby="original-reader-title"><div className="original-reader__header"><button type="button" onClick={onBack} className="original-reader__back"><ArrowLeft className="h-4 w-4" aria-hidden="true" />{backLabel ?? (vi ? "Về indexed excerpt" : "Back to indexed excerpt")}</button><h2 id="original-reader-title">{vi ? "Original source" : "Original source"}</h2></div><div className="original-reader__error" role="alert">{error}</div></section>;
  }

  const availableSources = manifest?.sources ?? [];
  const hasAvailableSource = availableSources.some((source) => source.status === "available");
  return (
    <section className="original-reader" aria-labelledby="original-reader-title">
      <div className="original-reader__header">
        <div>
          <button type="button" onClick={onBack} className="original-reader__back"><ArrowLeft className="h-4 w-4" aria-hidden="true" />{backLabel ?? (vi ? "Về indexed excerpt" : "Back to indexed excerpt")}</button>
          <p className="evidence-rail-eyebrow">{vi ? "Bản gốc an toàn" : "Safe original browsing"}</p>
          <h2 id="original-reader-title">Original source — normalized text</h2>
        </div>
        <FileSearch className="h-5 w-5 text-[var(--accent-text)]" aria-hidden="true" />
      </div>
      {manifest?.reason && <p className="original-reader__note" role="status">{manifest.reason}</p>}
      {!hasAvailableSource ? (
        <div className="original-reader__fallback" role="status">{vi ? "Bản gốc không khả dụng; indexed excerpt vẫn còn sẵn sàng." : "The original source is unavailable; the indexed excerpt remains available."}</div>
      ) : (
        <>
          <label className="original-reader__source-picker">
            <span>{vi ? "Nguồn bản gốc" : "Original source"}</span>
            <select value={sourceId} onChange={(event) => { setSourceId(event.target.value); setStart(0); setMatches([]); setActiveFind(""); }} aria-label={vi ? "Chọn nguồn bản gốc" : "Select original source"}>
              {availableSources.map((source) => <option key={source.source_document_id} value={source.source_document_id} disabled={source.status !== "available"}>{source.label}{source.status === "unavailable" ? ` — ${vi ? "không khả dụng" : "unavailable"}` : ""}</option>)}
            </select>
          </label>
          <div className="original-reader__find">
            <Search className="h-4 w-4" aria-hidden="true" />
            <input value={findQuery} onChange={(event) => setFindQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runFind(); }} placeholder={vi ? "Tìm literal trong bản gốc…" : "Find literal text in original…"} aria-label={vi ? "Tìm trong bản gốc" : "Find in original source"} maxLength={200} />
            <button type="button" onClick={() => void runFind()} disabled={loadingContent}>{vi ? "Tìm" : "Find"}</button>
          </div>
          {findError && <p className="original-reader__error" role="alert">{findError}</p>}
          {matches.length > 0 && <p className="original-reader__note" role="status">{matches.length} {vi ? "kết quả trong trang tìm kiếm hiện tại" : "matches in this bounded search page"}</p>}
          {location?.status === "ambiguous" && <p className="original-reader__note" role="status">{vi ? "Không đánh dấu evidence: đoạn khớp nhiều vị trí." : "Evidence is not highlighted because the indexed text has multiple matches."}</p>}
          {location?.status === "not_found" && <p className="original-reader__note" role="status">{vi ? "Không tìm thấy toàn bộ chunk trong bản gốc chuẩn hóa." : "The full indexed chunk was not found in the normalized original."}</p>}
          <div className="original-reader__window" aria-busy={loadingContent}>
            {loadingContent && <p role="status">{vi ? "Đang tải…" : "Loading…"}</p>}
            {content && <div className="original-reader__text" data-original-window>{content.segments.map((segment, index) => {
              const className = segment.evidence && segment.search
                ? "original-reader__evidence-match original-reader__search-match"
                : segment.evidence
                  ? "original-reader__evidence-match"
                  : segment.search
                    ? "original-reader__search-match"
                    : undefined;
              return className ? <mark key={`${content.start}-${index}`} className={className}>{segment.text}</mark> : <span key={`${content.start}-${index}`}>{segment.text}</span>;
            })}</div>}
            {!loadingContent && !content && <p className="original-reader__fallback">{vi ? "Không có cửa sổ văn bản." : "No original text window is available."}</p>}
          </div>
          {content && <div className="original-reader__footer"><span>{content.start.toLocaleString()}–{content.end.toLocaleString()} / {content.total_length.toLocaleString()} code points</span><div><button type="button" onClick={() => setStart(content.previous_start ?? 0)} disabled={content.previous_start === null || loadingContent} aria-label={vi ? "Cửa sổ trước" : "Previous original window"}><ChevronLeft className="h-4 w-4" /></button><button type="button" onClick={() => content.next_start !== null && setStart(content.next_start)} disabled={content.next_start === null || loadingContent} aria-label={vi ? "Cửa sổ sau" : "Next original window"}><ChevronRight className="h-4 w-4" /></button></div></div>}
        </>
      )}
    </section>
  );
}
