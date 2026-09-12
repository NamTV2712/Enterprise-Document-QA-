import { ArrowLeft, FileText } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useLocale } from "../lib/i18n";
import type { ReaderSessionController } from "../hooks/useReaderSession";
import type { Source } from "../types";
import { formatCompanyLabel } from "../lib/displayMetadata";
import { StructuredDocumentReader } from "./StructuredDocumentReader";
import { OriginalDocumentReader } from "./OriginalDocumentReader";
import "../styles/document-reader.css";

type WorkspaceTab = "document" | "excerpt" | "metadata";
type WorkspaceLayout = "wide-reading" | "two-column" | "single-surface";

export interface DocumentWorkspaceProps {
  documentId: string;
  indexedSource?: Source;
  indexedExcerpt?: ReactNode;
  metadata?: ReactNode;
  onBack: () => void;
  readerSession?: ReaderSessionController;
  title?: string;
  origin?: "answer" | "catalog" | "search";
  initialTab?: WorkspaceTab;
}

function layoutForWidth(width: number): WorkspaceLayout {
  if (width >= 1440) return "wide-reading";
  if (width >= 864) return "two-column";
  return "single-surface";
}

export function DocumentWorkspace({ documentId, indexedSource, indexedExcerpt, metadata, onBack, readerSession, title: providedTitle, origin = "answer", initialTab = "document" }: DocumentWorkspaceProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const rootRef = useRef<HTMLElement>(null);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>(initialTab);
  const [readerRepresentation, setReaderRepresentation] = useState<"structured" | "normalized">("structured");
  const [layout, setLayout] = useState<WorkspaceLayout>("single-surface");

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
    setReaderRepresentation("structured");
  }, [documentId]);

  const title = providedTitle || (indexedSource?.ticker ? formatCompanyLabel(indexedSource.ticker) : indexedSource?.citation) || indexedSource?.document_id || (vi ? "Tài liệu" : "Document");
  const backLabel = origin === "catalog" ? (vi ? "Về danh sách tài liệu" : "Back to Documents") : origin === "search" ? (vi ? "Về tìm kiếm" : "Back to Search") : (vi ? "Về trình kiểm tra" : "Back to inspector");
  const excerptEyebrow = origin === "answer" ? (vi ? "Nguồn gốc câu trả lời" : "Answer origin") : origin === "search" ? (vi ? "Ngữ cảnh kết quả tìm kiếm" : "Search result context") : (vi ? "Đoạn trích tài liệu" : "Document excerpt");
  const excerptHelp = origin === "answer" ? (vi ? "Đây là snapshot của citation hiện tại. Nó giữ nguyên nội dung khi bạn chuyển sang tài liệu." : "This is the citation snapshot for the selected answer source. It remains unchanged while you review the document.") : origin === "search" ? (vi ? "Đoạn trích này đến từ kết quả tìm kiếm hiện tại." : "This excerpt comes from the current search result.") : (vi ? "Đoạn trích được chọn từ tài liệu trong catalog." : "This excerpt was selected from the catalog document.");
  const layoutLabel = layout === "wide-reading"
    ? (vi ? "Bề mặt đọc rộng" : "Wide reading surface")
    : layout === "two-column"
      ? (vi ? "Chế độ xem hai cột" : "Two-column review")
      : (vi ? "Một bề mặt đọc" : "Single-surface reading");

  return (
    <section ref={rootRef} className={`document-workspace document-workspace--${layout}`} data-layout-mode={layout} aria-labelledby="document-workspace-title">
      <header className="document-workspace__header">
        <div className="document-workspace__identity">
          <button type="button" className="document-workspace__back" onClick={onBack}>
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
        <button type="button" className="document-workspace__close" onClick={onBack} aria-label={vi ? "Đóng không gian tài liệu" : "Close document workspace"}>×</button>
      </header>

      <div className="document-workspace__tabs" role="tablist" aria-label={vi ? "Các chế độ tài liệu" : "Document views"}>
        {([
          ["document", vi ? "Tài liệu" : "Document"],
          ["excerpt", vi ? "Đoạn đã lập chỉ mục" : "Indexed excerpt"],
          ["metadata", vi ? "Siêu dữ liệu" : "Metadata"],
        ] as const).map(([tab, label]) => (
          <button key={tab} type="button" role="tab" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)}>{label}</button>
        ))}
      </div>

      <div className="document-workspace__body">
        {activeTab === "document" && (
          <div className="document-workspace__document" role="tabpanel" aria-label={vi ? "Tài liệu có cấu trúc" : "Structured document"}>
            {readerRepresentation === "structured" ? (
              <StructuredDocumentReader documentId={documentId} indexedSource={indexedSource} onBack={onBack} readerSession={readerSession} onOpenNormalized={() => setReaderRepresentation("normalized")} embedded />
            ) : (
              <OriginalDocumentReader documentId={documentId} indexedSource={indexedSource} onBack={() => setReaderRepresentation("structured")} readerSession={readerSession} backLabel={vi ? "Về chế độ xem có cấu trúc" : "Back to structured view"} />
            )}
          </div>
        )}
        {activeTab === "excerpt" && (
          <section className="document-workspace__panel" role="tabpanel" aria-label={vi ? "Đoạn đã lập chỉ mục" : "Indexed excerpt"}>
            <p className="evidence-rail-eyebrow">{excerptEyebrow}</p>
            <h3>{vi ? "Đoạn trích đã chọn" : "Selected indexed excerpt"}</h3>
            <p className="document-workspace__help">{excerptHelp}</p>
            <div className="document-workspace__excerpt">{indexedExcerpt ?? <p>{vi ? "Không có đoạn trích được chọn." : "No indexed excerpt selected."}</p>}</div>
            <button type="button" className="document-workspace__primary" onClick={() => setActiveTab("document")}>{vi ? "Mở tài liệu" : "Open document"}</button>
          </section>
        )}
        {activeTab === "metadata" && (
          <section className="document-workspace__panel" role="tabpanel" aria-label={vi ? "Siêu dữ liệu tài liệu" : "Document metadata"}>
            <p className="evidence-rail-eyebrow">{vi ? "Nguồn và phiên bản" : "Source and revision"}</p>
            <h3>{vi ? "Provenance" : "Provenance"}</h3>
            <div className="document-workspace__metadata">{metadata ?? <p>{vi ? "Không có siêu dữ liệu bổ sung." : "No additional metadata available."}</p>}</div>
          </section>
        )}
      </div>
    </section>
  );
}
