import { ArrowLeft, ChevronDown, ChevronUp, FileText, Maximize2, Minimize2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { useLocale } from "../lib/i18n";
import type { ReaderSessionController } from "../hooks/useReaderSession";
import { getPdfEvidenceLocation, getPdfManifest } from "../lib/api";
import type { PdfEvidenceLocation, PdfRepresentationManifest, Source } from "../types";
import { formatCompanyLabel } from "../lib/displayMetadata";
import { sanitizeSecBrowserUrl } from "../lib/secUrls";
import type { ActiveRepresentation, DocumentContextTab } from "../lib/workbench";
import { getDocumentLocationErrorMessage, getDocumentLocationMessage, toDocumentLocationView, validateDocumentLocation, type ReaderLocationEvent } from "../lib/readerLocationView";
import { DocumentContextTabs } from "./workbench/DocumentContextTabs";
import { StructuredDocumentReader } from "./StructuredDocumentReader";
import { OriginalDocumentReader } from "./OriginalDocumentReader";
import { PdfDocumentViewer } from "./PdfDocumentViewer";
import "../styles/document-reader.css";

export type WorkspaceTab = "document" | "excerpt" | "metadata";
type WorkspaceLayout = "wide-reading" | "two-column" | "single-surface";

export interface DocumentWorkspaceProps {
  documentId: string;
  indexedSource?: Source;
  indexedExcerpt?: ReactNode;
  metadata?: ReactNode;
  notes?: ReactNode;
  onBack: () => void;
  /** Optional focus target for contextual route handoffs and dialogs. */
  backButtonRef?: RefObject<HTMLButtonElement | null>;
  onSaveEvidence?: () => void;
  onShowContext?: () => void;
  saved?: boolean;
  readerSession?: ReaderSessionController;
  title?: string;
  origin?: "answer" | "catalog" | "search" | "retrieval" | "library";
  initialTab?: WorkspaceTab;
  initialContextTab?: DocumentContextTab;
  representation?: ActiveRepresentation;
  onRepresentationChange?: (representation: ActiveRepresentation) => void;
  activeContextTab?: DocumentContextTab;
  onContextTabChange?: (tab: DocumentContextTab) => void;
  findQuery?: string;
  onFindQueryChange?: (query: string) => void;
  onLocationEvent?: (event: ReaderLocationEvent) => void;
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
  /** Collapse this document track while retaining its last committed width. */
  onCollapse?: () => void;
  /** Keep the pre-workbench view tabs available for direct compatibility consumers. */
  showLegacyTabs?: boolean;
  /** Show the workbench Evidence/Metadata/Notes context surface below the reader. */
  showContextTabs?: boolean;
  className?: string;
}

function layoutForWidth(width: number): WorkspaceLayout {
  if (width >= 1440) return "wide-reading";
  if (width >= 864) return "two-column";
  return "single-surface";
}

function PdfProvenanceMetadata({
  manifest,
  source,
  vi,
}: {
  manifest: PdfRepresentationManifest;
  source?: Source;
  vi: boolean;
}) {
  const sourceUrl = sanitizeSecBrowserUrl(source?.sec_index_url)
    ?? sanitizeSecBrowserUrl(source?.source_url);
  const representationLabel = manifest.representation_type === "OFFICIAL_PDF"
    ? (vi ? "PDF chính thức" : "Official PDF")
    : (vi ? "PDF được tạo" : "Generated PDF");
  const pageSemantics = manifest.page_semantics === "official_pdf_pages"
    ? (vi ? "Trang của PDF chính thức" : "Official PDF pages")
    : (vi ? "Trang của bản biểu diễn được tạo" : "Generated-representation pages");
  return (
    <section className="document-workspace__pdf-provenance" aria-label={vi ? "Nguồn gốc bản biểu diễn PDF" : "PDF representation provenance"}>
      <p className="evidence-rail-eyebrow">{vi ? "Bản biểu diễn PDF" : "PDF representation"}</p>
      <dl>
        <div><dt>{vi ? "Loại" : "Type"}</dt><dd>{representationLabel}</dd></div>
        <div><dt>{vi ? "Trạng thái" : "Status"}</dt><dd>{manifest.artifact_status}</dd></div>
        <div><dt>{vi ? "Ngữ nghĩa trang" : "Page semantics"}</dt><dd>{pageSemantics}</dd></div>
        {manifest.page_count !== null && <div><dt>{vi ? "Số trang" : "Pages"}</dt><dd>{manifest.page_count}</dd></div>}
        {manifest.source_document_id && <div><dt>{vi ? "Nguồn" : "Source document"}</dt><dd>{manifest.source_document_id}</dd></div>}
        {manifest.source_set_revision && <div><dt>{vi ? "Revision bộ nguồn" : "Source-set revision"}</dt><dd>{manifest.source_set_revision}</dd></div>}
        {manifest.document_revision && <div><dt>{vi ? "Revision tài liệu" : "Document revision"}</dt><dd>{manifest.document_revision}</dd></div>}
        {manifest.renderer && <div><dt>{vi ? "Renderer" : "Renderer"}</dt><dd>{manifest.renderer.renderer} {manifest.renderer.renderer_version}</dd></div>}
        {sourceUrl && <div><dt>{vi ? "Nguồn SEC" : "SEC source"}</dt><dd><a href={sourceUrl} target="_blank" rel="noreferrer">{sourceUrl}</a></dd></div>}
      </dl>
      <details>
        <summary>{vi ? "Hash và identity nâng cao" : "Advanced hashes and identity"}</summary>
        <dl>
          <div><dt>Representation ID</dt><dd><code>{manifest.representation_id}</code></dd></div>
          <div><dt>Artifact key</dt><dd><code>{manifest.artifact_key}</code></dd></div>
          {manifest.source_content_hash && <div><dt>Source content hash</dt><dd><code>{manifest.source_content_hash}</code></dd></div>}
          {manifest.artifact_hash && <div><dt>Artifact hash</dt><dd><code>{manifest.artifact_hash}</code></dd></div>}
        </dl>
      </details>
    </section>
  );
}

export function DocumentWorkspace({
  documentId,
  indexedSource,
  indexedExcerpt,
  metadata,
  notes,
  onBack,
  backButtonRef,
  onSaveEvidence,
  onShowContext,
  saved = false,
  readerSession,
  title: providedTitle,
  origin = "answer",
  initialTab = "document",
  initialContextTab,
  representation,
  onRepresentationChange,
  activeContextTab,
  onContextTabChange,
  findQuery,
  onFindQueryChange,
  onLocationEvent,
  expanded,
  onExpandedChange,
  onCollapse,
  showLegacyTabs = true,
  showContextTabs = false,
  className,
}: DocumentWorkspaceProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const rootRef = useRef<HTMLElement>(null);
  const identityKey = documentId + "::" + (indexedSource?.chunk_id ?? indexedSource?.document_id ?? "document");
  const initialContext = initialContextTab ?? (initialTab === "metadata" ? "metadata" : "evidence");
  const [activeTab, setActiveTab] = useState<WorkspaceTab>(initialTab);
  const [internalRepresentation, setInternalRepresentation] = useState<ActiveRepresentation>("structured");
  const [internalContextTab, setInternalContextTab] = useState<DocumentContextTab>(initialContext);
  const [internalFindQuery, setInternalFindQuery] = useState("");
  const [internalExpanded, setInternalExpanded] = useState(false);
  const [contextCollapsed, setContextCollapsed] = useState(false);
  const [layout, setLayout] = useState<WorkspaceLayout>("single-surface");
  const [pdfManifest, setPdfManifest] = useState<PdfRepresentationManifest | null>(null);
  const [pdfEvidenceLocation, setPdfEvidenceLocation] = useState<PdfEvidenceLocation | null>(null);
  const previousIdentityRef = useRef(identityKey);

  const activeRepresentation = representation ?? internalRepresentation;
  const requestedContextTab = activeContextTab ?? internalContextTab;
  const hasNotes = Boolean(notes);
  const effectiveContextTab = requestedContextTab === "notes" && !hasNotes ? "evidence" : requestedContextTab;
  const effectiveFindQuery = findQuery ?? internalFindQuery;
  const isExpanded = expanded ?? internalExpanded;
  const selectReaderSession = readerSession?.select;
  const isReaderSessionCurrent = readerSession?.isCurrent;

  useEffect(() => {
    const controller = new AbortController();
    setPdfManifest(null);
    void getPdfManifest(documentId, controller.signal)
      .then(setPdfManifest)
      .catch(() => {
        // A missing/unsupported representation is intentionally hidden from
        // the switcher; Structured and Normalized remain the safe fallback.
      });
    return () => controller.abort();
  }, [documentId, identityKey]);

  useEffect(() => {
    const controller = new AbortController();
    setPdfEvidenceLocation(null);
    const source = indexedSource;
    const canResolve = activeRepresentation === "pdf"
      && pdfManifest?.artifact_status === "available"
      && Boolean(pdfManifest.artifact_hash)
      && Boolean(source?.chunk_id && source.chunk_text_hash)
      && Boolean(pdfManifest.source_document_id && pdfManifest.source_set_revision && pdfManifest.document_revision);
    if (!canResolve || !source?.chunk_id || !source.chunk_text_hash || !pdfManifest?.source_document_id || !pdfManifest.source_set_revision || !pdfManifest.document_revision) {
      return () => controller.abort();
    }
    const generation = selectReaderSession?.({
      documentId,
      sourceKey: source.chunk_id ?? source.chunk_text_hash ?? null,
      representation: "pdf",
    }) ?? 0;
    const isCurrent = () => !isReaderSessionCurrent || isReaderSessionCurrent(generation);
    onLocationEvent?.({ state: "resolving", generation, source });
    void getPdfEvidenceLocation(documentId, {
      chunk_id: source.chunk_id,
      chunk_text_hash: source.chunk_text_hash,
      source_document_id: pdfManifest.source_document_id,
      source_set_revision: pdfManifest.source_set_revision,
      document_revision: pdfManifest.document_revision,
    }, controller.signal).then((response) => {
      if (!isCurrent()) return;
      const view = toDocumentLocationView("pdf", response);
      const validation = validateDocumentLocation(view, {
        documentId,
        chunkId: source.chunk_id,
        chunkTextHash: source.chunk_text_hash,
        sourceSetRevision: pdfManifest.source_set_revision,
        sourceDocumentId: pdfManifest.source_document_id,
        documentRevision: pdfManifest.document_revision,
      });
      if (!validation.ok) {
        setPdfEvidenceLocation(response);
        const reason = validation.reason || getDocumentLocationMessage(view, vi);
        const state = validation.state === "stale" ? "stale" : "unavailable";
        onLocationEvent?.({ state, generation, source, reason });
        return;
      }
      setPdfEvidenceLocation(response);
      if (response.status === "exact") {
        onLocationEvent?.({ state: "resolved", generation, source, location: view });
      } else {
        onLocationEvent?.({ state: response.status === "stale" ? "stale" : "unavailable", generation, source, reason: response.reason || getDocumentLocationMessage(view, vi) });
      }
    }).catch((reason) => {
      if (!isCurrent() || (reason instanceof DOMException && reason.name === "AbortError")) return;
      const message = getDocumentLocationErrorMessage(reason, vi) || (vi ? "Không thể xác minh vị trí evidence trong PDF." : "Could not verify the PDF evidence location.");
      setPdfEvidenceLocation(null);
      onLocationEvent?.({ state: reason?.status === 409 ? "stale" : "unavailable", generation, source, reason: message });
    });
    return () => controller.abort();
  }, [activeRepresentation, documentId, indexedSource?.chunk_id, indexedSource?.chunk_text_hash, onLocationEvent, pdfManifest?.artifact_hash, pdfManifest?.artifact_status, pdfManifest?.document_revision, pdfManifest?.source_document_id, pdfManifest?.source_set_revision, selectReaderSession, isReaderSessionCurrent, vi]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const syncLayout = () => setLayout(layoutForWidth(root.clientWidth));
    syncLayout();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(syncLayout);
      observer.observe(root);
      return () => observer.disconnect();
    }
    window.addEventListener("resize", syncLayout);
    return () => window.removeEventListener("resize", syncLayout);
  }, []);

  useEffect(() => {
    if (previousIdentityRef.current === identityKey) return;
    previousIdentityRef.current = identityKey;
    setInternalRepresentation("structured");
    setInternalContextTab(initialContext);
    setInternalFindQuery("");
    onRepresentationChange?.("structured");
    onContextTabChange?.(initialContext);
    onFindQueryChange?.("");
  }, [identityKey, initialContext, onContextTabChange, onFindQueryChange, onRepresentationChange]);

  useEffect(() => {
    if (!showContextTabs) return;
    const root = rootRef.current;
    if (!root) return;
    const syncContextHeight = () => {
      // In jsdom and isolated unit mounts clientHeight is zero; leave the
      // context open there so compatibility tests and embedding hosts retain
      // the same useful default.
      if (root.clientHeight > 0) setContextCollapsed(root.clientHeight < 720);
    };
    syncContextHeight();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(syncContextHeight);
      observer.observe(root);
      return () => observer.disconnect();
    }
    window.addEventListener("resize", syncContextHeight);
    return () => window.removeEventListener("resize", syncContextHeight);
  }, [showContextTabs]);

  const title = providedTitle || (indexedSource?.ticker ? formatCompanyLabel(indexedSource.ticker) : indexedSource?.citation) || indexedSource?.document_id || (vi ? "Tài liệu" : "Document");
  const backLabel = origin === "catalog"
    ? (vi ? "Về danh sách tài liệu" : "Back to Documents")
    : origin === "search"
      ? (vi ? "Về tìm kiếm" : "Back to Search")
      : origin === "retrieval"
        ? (vi ? "Về phòng truy xuất" : "Back to Retrieval")
        : origin === "library"
          ? (vi ? "Về bộ sưu tập" : "Back to Collections")
          : (vi ? "Về trình kiểm tra" : "Back to inspector");
  const excerptEyebrow = origin === "answer"
    ? (vi ? "Nguồn gốc câu trả lời" : "Answer origin")
    : origin === "search"
      ? (vi ? "Ngữ cảnh kết quả tìm kiếm" : "Search result context")
      : origin === "retrieval"
        ? (vi ? "Ngữ cảnh truy xuất" : "Retrieval context")
        : origin === "library"
          ? (vi ? "Mục trong bộ sưu tập" : "Collection member")
          : (vi ? "Đoạn trích tài liệu" : "Document excerpt");
  const excerptHelp = origin === "answer"
    ? (vi ? "Đây là snapshot của citation hiện tại. Nó giữ nguyên nội dung khi bạn chuyển sang tài liệu." : "This is the citation snapshot for the selected answer source. It remains unchanged while you review the document.")
    : origin === "search"
      ? (vi ? "Đoạn trích này đến từ kết quả tìm kiếm hiện tại." : "This excerpt comes from the current search result.")
      : origin === "retrieval"
        ? (vi ? "Đoạn trích này đến từ kết quả truy xuất hiện tại." : "This excerpt comes from the current retrieval result.")
        : origin === "library"
          ? (vi ? "Tài liệu này được mở từ một bộ sưu tập theo định danh đã lưu." : "This document was opened from a collection by its stored identity.")
          : (vi ? "Đoạn trích được chọn từ tài liệu trong catalog." : "This excerpt was selected from the catalog document.");
  const layoutLabel = layout === "wide-reading"
    ? (vi ? "Bề mặt đọc rộng" : "Wide reading surface")
    : layout === "two-column"
      ? (vi ? "Chế độ xem hai cột" : "Two-column review")
      : (vi ? "Một bề mặt đọc" : "Single-surface reading");
  const setRepresentation = (next: ActiveRepresentation) => {
    if (next === "pdf" && !pdfManifest) return;
    setInternalRepresentation(next);
    onRepresentationChange?.(next);
  };
  const setContextTab = (next: DocumentContextTab) => {
    setInternalContextTab(next);
    onContextTabChange?.(next);
  };
  const setFindQuery = (next: string) => {
    setInternalFindQuery(next);
    onFindQueryChange?.(next);
  };
  const setExpanded = (next: boolean) => {
    setInternalExpanded(next);
    onExpandedChange?.(next);
  };
  const renderDocument = !showLegacyTabs || activeTab === "document";
  const pdfSelectable = pdfManifest !== null && ["supported", "generating", "available", "stale", "failed"].includes(pdfManifest.artifact_status);
  const renderedRepresentation = activeRepresentation === "pdf" && pdfManifest ? "pdf" : activeRepresentation === "normalized" ? "normalized" : "structured";
  const pdfEvidenceStatus = activeRepresentation === "pdf" && pdfManifest?.artifact_status === "available"
    ? pdfEvidenceLocation?.status ?? (indexedSource?.chunk_id ? "unavailable" : null)
    : null;
  const pdfEvidenceMessage = pdfEvidenceLocation?.reason ?? null;
  const handlePdfManifestChange = useCallback((next: PdfRepresentationManifest) => {
    setPdfManifest(next);
  }, []);

  return (
    <section
      ref={rootRef}
      className={["document-workspace", "document-workspace--" + layout, isExpanded ? "is-expanded" : "", className ?? ""].filter(Boolean).join(" ")}
      data-layout-mode={layout}
      data-document-representation={activeRepresentation}
      data-expanded={isExpanded ? "true" : "false"}
      aria-labelledby="document-workspace-title"
    >
      <header className="document-workspace__header">
        <div className="document-workspace__identity">
          <button ref={backButtonRef} type="button" className="document-workspace__back" onClick={onBack}>
            <ArrowLeft aria-hidden="true" />
            {backLabel}
          </button>
          <div className="document-workspace__title-row">
            <FileText aria-hidden="true" />
            <div>
              <p className="evidence-rail-eyebrow">{vi ? "Không gian tài liệu" : "Document workspace"}</p>
              <h2 id="document-workspace-title">{title}</h2>
            <p>{documentId} · {layoutLabel}</p>
            </div>
          </div>
        </div>
        <div className="document-workspace__header-actions">
          <div className="document-workspace__representation-switcher" role="group" aria-label={vi ? "Chế độ biểu diễn tài liệu" : "Document representation"}>
            <span>{vi ? "Biểu diễn" : "Representation"}</span>
            <button type="button" data-representation="structured" aria-pressed={activeRepresentation === "structured"} onClick={() => setRepresentation("structured")}>
              {vi ? "Có cấu trúc" : "Structured"}
            </button>
            <button type="button" data-representation="normalized" aria-pressed={activeRepresentation === "normalized"} onClick={() => setRepresentation("normalized")}>
              {vi ? "Văn bản chuẩn hóa" : "Normalized text"}
            </button>
            {pdfSelectable && <button type="button" data-representation="pdf" aria-pressed={activeRepresentation === "pdf"} onClick={() => setRepresentation("pdf")}>
              {vi ? "PDF" : "PDF"}
            </button>}
          </div>
          <button type="button" className="document-workspace__expand" onClick={() => setExpanded(!isExpanded)} aria-label={isExpanded ? (vi ? "Khôi phục tài liệu" : "Restore document") : (vi ? "Mở rộng tài liệu" : "Expand document")} aria-pressed={isExpanded}>
            {isExpanded ? <Minimize2 aria-hidden="true" /> : <Maximize2 aria-hidden="true" />}
          </button>
          {onCollapse && (
            <button type="button" className="document-workspace__collapse" onClick={onCollapse} aria-label={vi ? "Thu gọn bảng tài liệu" : "Collapse document pane"}>
              <Minimize2 aria-hidden="true" />
            </button>
          )}
          <button type="button" className="document-workspace__close" onClick={onBack} aria-label={vi ? "Đóng không gian tài liệu" : "Close document workspace"}>×</button>
        </div>
      </header>

      {showLegacyTabs && <div className="document-workspace__tabs" role="tablist" aria-label={vi ? "Các chế độ tài liệu" : "Document views"}>
        {([
          ["document", vi ? "Tài liệu" : "Document"],
          ["excerpt", vi ? "Đoạn đã lập chỉ mục" : "Indexed excerpt"],
          ["metadata", vi ? "Siêu dữ liệu" : "Metadata"],
        ] as const).map(([tab, label]) => (
          <button key={tab} type="button" role="tab" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)}>{label}</button>
        ))}
      </div>}

      <div className="document-workspace__body">
        {renderDocument && (
          <div className="document-workspace__document" role="tabpanel" aria-label={vi ? "Tài liệu" : "Document"}>
            <div className="document-workspace__reader">
              {renderedRepresentation === "structured" ? (
                <StructuredDocumentReader
                  documentId={documentId}
                  indexedSource={indexedSource}
                  onBack={onBack}
                  readerSession={readerSession}
                  onOpenNormalized={() => setRepresentation("normalized")}
                  findQuery={effectiveFindQuery}
                  onFindQueryChange={setFindQuery}
                  onLocationEvent={onLocationEvent}
                  embedded
                />
              ) : renderedRepresentation === "normalized" ? (
                <OriginalDocumentReader
                  documentId={documentId}
                  indexedSource={indexedSource}
                  onBack={() => setRepresentation("structured")}
                  readerSession={readerSession}
                  backLabel={vi ? "Về chế độ xem có cấu trúc" : "Back to structured view"}
                  embedded
                  findQuery={effectiveFindQuery}
                  onFindQueryChange={setFindQuery}
                  onLocationEvent={onLocationEvent}
                />
              ) : (
                <PdfDocumentViewer
                  documentId={documentId}
                  manifest={pdfManifest as PdfRepresentationManifest}
                  indexedSource={indexedSource}
                  readerSession={readerSession}
                  findQuery={effectiveFindQuery}
                  onFindQueryChange={setFindQuery}
                  onManifestChange={handlePdfManifestChange}
                  highlightRects={pdfEvidenceLocation?.status === "exact" ? pdfEvidenceLocation.rects : []}
                  evidenceStatus={pdfEvidenceStatus}
                  evidenceMessage={pdfEvidenceMessage}
                  focusPage={pdfEvidenceLocation?.status === "exact" ? pdfEvidenceLocation.rects[0]?.page ?? null : null}
                  onEvidenceActivate={() => { setContextTab("evidence"); onShowContext?.(); }}
                  downloadName={`${documentId.replace(/[^A-Za-z0-9_-]+/g, "_")}_${pdfManifest?.representation_type === "OFFICIAL_PDF" ? "official" : "derived"}.pdf`}
                />
              )}
            </div>
            {showContextTabs && (
              <section className="document-workspace__context" aria-label={vi ? "Ngữ cảnh tài liệu" : "Document context"}>
                <div className="document-workspace__context-header">
                  <DocumentContextTabs activeTab={effectiveContextTab} onTabChange={setContextTab} hasNotes={hasNotes} />
                  <button
                    type="button"
                    className="document-workspace__context-toggle"
                    aria-expanded={!contextCollapsed}
                    aria-controls="document-context-content"
                    aria-label={contextCollapsed ? (vi ? "Mở rộng ngữ cảnh tài liệu" : "Expand document context") : (vi ? "Thu gọn ngữ cảnh tài liệu" : "Collapse document context")}
                    onClick={() => setContextCollapsed((collapsed) => !collapsed)}
                  >
                    {contextCollapsed ? <ChevronDown aria-hidden="true" /> : <ChevronUp aria-hidden="true" />}
                  </button>
                </div>
                <div id="document-context-content" className="document-workspace__context-content" hidden={contextCollapsed}>
                  {effectiveContextTab === "evidence" && (
                    <section id="document-context-panel-evidence" className="document-context-panel" role="tabpanel" aria-labelledby="document-context-tab-evidence">
                      <div className="document-context-panel__header">
                        <div>
                          <p className="evidence-rail-eyebrow">{vi ? "Bằng chứng đã chọn" : "Selected evidence"}</p>
                          <h3>{indexedSource?.citation ?? (vi ? "Không có citation được chọn" : "No citation selected")}</h3>
                          {indexedSource?.section && <p className="document-context-panel__section">{indexedSource.section}</p>}
                        </div>
                        <div className="document-context-panel__actions">
                          {onShowContext && <button type="button" onClick={onShowContext}>{vi ? "Hiện ngữ cảnh" : "Show context"}</button>}
                          {onSaveEvidence && <button type="button" onClick={onSaveEvidence} disabled={saved}>{saved ? (vi ? "Đã lưu" : "Saved") : (vi ? "Lưu evidence" : "Save evidence")}</button>}
                        </div>
                      </div>
                      <div className="document-context-panel__excerpt">{indexedExcerpt ?? <p>{vi ? "Không có đoạn trích được chọn." : "No indexed excerpt selected."}</p>}</div>
                      <p className="document-context-panel__binding" role="status">
                        {indexedSource
                          ? (vi ? "Liên kết evidence giữ nguyên identity của nguồn; trạng thái khớp chính xác được báo cáo bởi trình đọc." : "The evidence link preserves the source identity; exact correspondence is reported by the active reader.")
                          : (vi ? "Chưa có nguồn evidence được gắn với tài liệu này." : "No evidence source is attached to this document.")}
                      </p>
                    </section>
                  )}
                  {effectiveContextTab === "metadata" && (
                    <section id="document-context-panel-metadata" className="document-context-panel" role="tabpanel" aria-labelledby="document-context-tab-metadata">
                      <p className="evidence-rail-eyebrow">{vi ? "Nguồn và phiên bản" : "Source and revision"}</p>
                      <h3>{vi ? "Metadata tài liệu" : "Document metadata"}</h3>
                      <div className="document-workspace__metadata">
                        {metadata ?? <p>{vi ? "Không có siêu dữ liệu bổ sung." : "No additional metadata available."}</p>}
                        {pdfManifest && <PdfProvenanceMetadata manifest={pdfManifest} source={indexedSource} vi={vi} />}
                      </div>
                    </section>
                  )}
                  {effectiveContextTab === "notes" && hasNotes && (
                    <section id="document-context-panel-notes" className="document-context-panel" role="tabpanel" aria-labelledby="document-context-tab-notes">
                      <p className="evidence-rail-eyebrow">{vi ? "Ghi chú đã tồn tại" : "Existing notes"}</p>
                      <h3>Notes</h3>
                      <div className="document-context-panel__notes">{notes}</div>
                    </section>
                  )}
                </div>
              </section>
            )}
          </div>
        )}
        {showLegacyTabs && activeTab === "excerpt" && (
          <section className="document-workspace__panel" role="tabpanel" aria-label={vi ? "Đoạn đã lập chỉ mục" : "Indexed excerpt"}>
            <p className="evidence-rail-eyebrow">{excerptEyebrow}</p>
            <h3>{vi ? "Đoạn trích đã chọn" : "Selected indexed excerpt"}</h3>
            <p className="document-workspace__help">{excerptHelp}</p>
            <div className="document-workspace__excerpt">{indexedExcerpt ?? <p>{vi ? "Không có đoạn trích được chọn." : "No indexed excerpt selected."}</p>}</div>
            <button type="button" className="document-workspace__primary" onClick={() => setActiveTab("document")}>{vi ? "Mở tài liệu" : "Open document"}</button>
          </section>
        )}
        {showLegacyTabs && activeTab === "metadata" && (
          <section className="document-workspace__panel" role="tabpanel" aria-label={vi ? "Siêu dữ liệu tài liệu" : "Document metadata"}>
            <p className="evidence-rail-eyebrow">{vi ? "Nguồn và phiên bản" : "Source and revision"}</p>
            <h3>{vi ? "Provenance" : "Provenance"}</h3>
            <div className="document-workspace__metadata">
              {metadata ?? <p>{vi ? "Không có siêu dữ liệu bổ sung." : "No additional metadata available."}</p>}
              {pdfManifest && <PdfProvenanceMetadata manifest={pdfManifest} source={indexedSource} vi={vi} />}
            </div>
          </section>
        )}
      </div>
    </section>
  );
}
