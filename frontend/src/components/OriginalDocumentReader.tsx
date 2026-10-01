import { ArrowLeft, ChevronLeft, ChevronRight, FileSearch, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getOriginalContent, getOriginalLocation, getOriginalManifest, searchOriginal } from "../lib/api";
import type { OriginalContent, OriginalLocation, OriginalManifest, OriginalSearchMatch, Source } from "../types";
import { describeRequestError } from "../lib/requestError";
import { useLocale } from "../lib/i18n";
import type { ReaderSessionController } from "../hooks/useReaderSession";
import { useReaderEvidenceSource } from "../hooks/useReaderEvidenceSource";
import { getDocumentLocationErrorMessage, getDocumentLocationMessage, toDocumentLocationView, validateDocumentLocation, type ReaderLocationEvent } from "../lib/readerLocationView";

interface OriginalDocumentReaderProps {
  documentId: string;
  indexedSource?: Source;
  onBack: () => void;
  readerSession?: ReaderSessionController;
  backLabel?: string;
  embedded?: boolean;
  findQuery?: string;
  onFindQueryChange?: (query: string) => void;
  onLocationEvent?: (event: ReaderLocationEvent) => void;
}

const WINDOW_SIZE = 16_000;

function isStaleLocationError(reason: unknown): boolean {
  if (!reason || typeof reason !== "object") return false;
  const candidate = reason as { status?: unknown; code?: unknown };
  return candidate.status === 409 || candidate.code === "source_changed" || candidate.code === "chunk_changed";
}

function isNotFoundLocationError(reason: unknown): boolean {
  return Boolean(reason && typeof reason === "object" && (reason as { status?: unknown }).status === 404);
}

export function OriginalDocumentReader({ documentId, indexedSource, onBack, readerSession, backLabel, embedded = false, findQuery: controlledFindQuery, onFindQueryChange, onLocationEvent }: OriginalDocumentReaderProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [manifest, setManifest] = useState<OriginalManifest | null>(null);
  const [sourceId, setSourceId] = useState("");
  const [content, setContent] = useState<OriginalContent | null>(null);
  const [location, setLocation] = useState<OriginalLocation | null>(null);
  const [start, setStart] = useState(0);
  const [internalFindQuery, setInternalFindQuery] = useState("");
  const [activeFind, setActiveFind] = useState("");
  const [matches, setMatches] = useState<OriginalSearchMatch[]>([]);
  const [loadingManifest, setLoadingManifest] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [findError, setFindError] = useState<string | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const manifestRequestId = useRef(0);
  const contentRequestId = useRef(0);
  const locationRequestId = useRef(0);
  const findRequestId = useRef(0);
  const findControllerRef = useRef<AbortController | null>(null);
  const readerGenerationRef = useRef<number | null>(null);
  const readerSourceResolution = useReaderEvidenceSource(documentId, indexedSource);
  const resolvedIndexedSource = readerSourceResolution.source;
  const findQuery = controlledFindQuery ?? internalFindQuery;
  const updateFindQuery = useCallback((next: string) => {
    setInternalFindQuery(next);
    onFindQueryChange?.(next);
  }, [onFindQueryChange]);

  const isCurrentReaderSession = useCallback(() => {
    const generation = readerGenerationRef.current;
    return !readerSession || (generation !== null && readerSession.isCurrent(generation));
  }, [readerSession]);

  useEffect(() => {
    readerGenerationRef.current = readerSession?.select({
      documentId,
      sourceKey: resolvedIndexedSource?.chunk_id ?? resolvedIndexedSource?.chunk_text_hash ?? null,
      representation: "normalized",
    }) ?? null;
    const controller = new AbortController();
    const requestId = ++manifestRequestId.current;
    setLoadingManifest(true);
    setError(null);
    setManifest(null);
    setContent(null);
    setLocation(null);
    setLocationError(null);
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
  }, [documentId, isCurrentReaderSession, readerSession, resolvedIndexedSource?.chunk_id, resolvedIndexedSource?.chunk_text_hash, vi]);

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
    const hasChunkBinding = Boolean(resolvedIndexedSource?.chunk_id && resolvedIndexedSource.chunk_text_hash);
    void getOriginalContent(documentId, {
      source_document_id: selectedManifestSource.source_document_id,
      source_set_revision: manifest.source_set_revision,
      document_revision: selectedManifestSource.document_revision,
      start,
      limit: WINDOW_SIZE,
      chunk_id: hasChunkBinding ? resolvedIndexedSource?.chunk_id : null,
      chunk_text_hash: hasChunkBinding ? resolvedIndexedSource?.chunk_text_hash : null,
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
  }, [activeFind, documentId, isCurrentReaderSession, manifest, resolvedIndexedSource?.chunk_id, resolvedIndexedSource?.chunk_text_hash, selectedManifestSource, start, vi]);

  useEffect(() => {
    const source = resolvedIndexedSource;
    const requestId = ++locationRequestId.current;
    const generation = readerGenerationRef.current ?? requestId;
    if (!manifest || !source?.chunk_id) {
      setLocation(null);
      setLocationError(null);
      return;
    }
    if (readerSourceResolution.state === "resolving") {
      setLocation(null);
      setLocationError(null);
      onLocationEvent?.({ state: "resolving", generation, source });
      return;
    }
    if (!source.chunk_text_hash) {
      const reason = readerSourceResolution.reason || (vi ? "Không thể xác minh hash của chunk đã chọn." : "The selected chunk has no verifiable text hash.");
      setLocation(null);
      setLocationError(reason);
      onLocationEvent?.({
        state: readerSourceResolution.state === "stale" ? "stale" : readerSourceResolution.state === "error" ? "error" : "unavailable",
        generation,
        source,
        reason,
      });
      return;
    }
    const controller = new AbortController();
    setLocationError(null);
    onLocationEvent?.({ state: "resolving", generation, source });
    void getOriginalLocation(source.chunk_id, {
      chunk_text_hash: source.chunk_text_hash,
      source_set_revision: manifest.source_set_revision,
    }, controller.signal)
      .then((response) => {
        if (requestId !== locationRequestId.current || !isCurrentReaderSession()) return;
        const view = toDocumentLocationView("normalized", response);
        const validation = validateDocumentLocation(view, {
          documentId,
          chunkId: source.chunk_id,
          chunkTextHash: source.chunk_text_hash,
          sourceSetRevision: manifest.source_set_revision,
        });
        const responseSource = response.location
          ? manifest.sources.find((candidate) => candidate.source_document_id === response.location?.source_document_id)
          : null;
        const sourceRevisionMatches = response.status !== "exact"
          || Boolean(response.location && responseSource?.status === "available" && responseSource.document_revision === response.location.document_revision);
        if (!validation.ok || !sourceRevisionMatches) {
          const reason = validation.reason || (vi ? "Không thể liên kết vị trí exact với revision tài liệu." : "The exact location could not be linked to a verified document revision.");
          setLocation(null);
          setLocationError(reason);
          onLocationEvent?.({ state: validation.state === "ready" ? "stale" : validation.state, generation, source, reason });
          return;
        }
        setLocation(response);
        setLocationError(null);
        if (response.status === "unavailable") {
          onLocationEvent?.({ state: "unavailable", generation, source, reason: response.reason || getDocumentLocationMessage(view, vi) });
        } else {
          onLocationEvent?.({ state: "resolved", generation, source, location: view });
        }
        if (response.status === "exact" && response.location && response.location.source_document_id !== sourceId) {
          setSourceId(response.location.source_document_id);
        }
      })
      .catch((reason) => {
        if (requestId !== locationRequestId.current || !isCurrentReaderSession() || (reason instanceof DOMException && reason.name === "AbortError")) return;
        setLocation(null);
        const errorMessage = getDocumentLocationErrorMessage(reason, vi) || describeRequestError(reason, vi ? "Không thể xác minh vị trí evidence." : "Could not verify evidence location.", vi ? "vi" : "en").message;
        setLocationError(errorMessage);
        onLocationEvent?.({
          state: isStaleLocationError(reason) ? "stale" : isNotFoundLocationError(reason) ? "unavailable" : "error",
          generation,
          source,
          reason: errorMessage,
        });
      });
    return () => {
      controller.abort();
      locationRequestId.current += 1;
    };
  }, [documentId, isCurrentReaderSession, manifest, onLocationEvent, readerSourceResolution.reason, readerSourceResolution.state, resolvedIndexedSource?.chunk_id, resolvedIndexedSource?.chunk_text_hash, vi]);

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
    return <section className="original-reader" data-reader-representation="normalized" aria-labelledby={!embedded ? "original-reader-title" : undefined} aria-label={embedded ? (vi ? "Văn bản chuẩn hóa" : "Normalized text") : undefined}>{!embedded && <div className="original-reader__header"><button type="button" onClick={onBack} className="original-reader__back"><ArrowLeft className="h-4 w-4" aria-hidden="true" />{backLabel ?? (vi ? "Về indexed excerpt" : "Back to indexed excerpt")}</button><h2 id="original-reader-title">{vi ? "Original source" : "Original source"}</h2></div>}<p role="status" className="original-reader__status">{vi ? "Đang kiểm tra bản gốc…" : "Checking original source…"}</p></section>;
  }

  if (error && !manifest) {
    return <section className="original-reader" data-reader-representation="normalized" aria-labelledby={!embedded ? "original-reader-title" : undefined} aria-label={embedded ? (vi ? "Văn bản chuẩn hóa" : "Normalized text") : undefined}>{!embedded && <div className="original-reader__header"><button type="button" onClick={onBack} className="original-reader__back"><ArrowLeft className="h-4 w-4" aria-hidden="true" />{backLabel ?? (vi ? "Về indexed excerpt" : "Back to indexed excerpt")}</button><h2 id="original-reader-title">{vi ? "Original source" : "Original source"}</h2></div>}<div className="original-reader__error" role="alert">{error}</div></section>;
  }

  const availableSources = manifest?.sources ?? [];
  const hasAvailableSource = availableSources.some((source) => source.status === "available");
  return (
    <section className="original-reader" data-reader-representation="normalized" aria-labelledby={!embedded ? "original-reader-title" : undefined} aria-label={embedded ? (vi ? "Văn bản chuẩn hóa" : "Normalized text") : undefined}>
      {!embedded && <div className="original-reader__header">
        <div>
          <button type="button" onClick={onBack} className="original-reader__back"><ArrowLeft className="h-4 w-4" aria-hidden="true" />{backLabel ?? (vi ? "Về indexed excerpt" : "Back to indexed excerpt")}</button>
          <p className="evidence-rail-eyebrow">{vi ? "Bản gốc an toàn" : "Safe original browsing"}</p>
          <h2 id="original-reader-title">Original source — normalized text</h2>
        </div>
        <FileSearch className="h-5 w-5 text-[var(--accent-text)]" aria-hidden="true" />
      </div>}
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
            <input value={findQuery} onChange={(event) => updateFindQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runFind(); }} placeholder={vi ? "Tìm literal trong bản gốc…" : "Find literal text in original…"} aria-label={vi ? "Tìm trong bản gốc" : "Find in original source"} maxLength={200} />
            <button type="button" onClick={() => void runFind()} disabled={loadingContent}>{vi ? "Tìm" : "Find"}</button>
          </div>
          {findError && <p className="original-reader__error" role="alert">{findError}</p>}
          {locationError && <p className="original-reader__error" role="status">{locationError}</p>}
          {matches.length > 0 && <p className="original-reader__note" role="status">{matches.length} {vi ? "kết quả trong trang tìm kiếm hiện tại" : "matches in this bounded search page"}</p>}
          {location && <p className="original-reader__note" role="status">{location.status === "exact" ? getDocumentLocationMessage(toDocumentLocationView("normalized", location), vi) : location.reason || getDocumentLocationMessage(toDocumentLocationView("normalized", location), vi)}</p>}
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
