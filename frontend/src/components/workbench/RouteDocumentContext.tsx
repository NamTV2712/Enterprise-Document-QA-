import { useRef } from "react";
import type { ReactNode } from "react";
import { useLocale } from "../../lib/i18n";
import type { WorkbenchLayoutMode } from "../../lib/workbench";
import { formatCompanyLabel } from "../../lib/displayMetadata";
import { sanitizeSecBrowserUrl } from "../../lib/secUrls";
import type { DocumentWorkspaceTarget, Source } from "../../types";
import type { ReaderSessionController } from "../../hooks/useReaderSession";
import { ModalDialog } from "../ui/ModalDialog";
import { DocumentPane } from "./DocumentPane";
import { useOptionalWorkbenchContext } from "./WorkbenchContext";

interface RouteDocumentContextProps {
  target: DocumentWorkspaceTarget;
  onBack: () => void;
  readerSession: ReaderSessionController;
}

function originFor(target: DocumentWorkspaceTarget): "catalog" | "search" | "retrieval" {
  return target.kind;
}

function sourceFor(target: DocumentWorkspaceTarget): Source | undefined {
  return target.selectedSource;
}

function titleFor(target: DocumentWorkspaceTarget): string {
  if ("title" in target && target.title) return target.title;
  const source = sourceFor(target);
  if (source?.ticker) return `${formatCompanyLabel(source.ticker)} · ${source.filing_date ?? "SEC filing"}`;
  return source?.citation ?? target.documentId;
}

function indexedExcerptFor(source: Source | undefined): ReactNode {
  if (!source) return undefined;
  return (
    <div className="document-workspace__excerpt-content">
      <p className="context-viewer-citation">{source.citation}</p>
      <p>{source.text_preview || source.text || ""}</p>
    </div>
  );
}

function metadataFor(target: DocumentWorkspaceTarget, locale: "en" | "vi"): ReactNode {
  const source = sourceFor(target);
  const rows: Array<[string, string | null | undefined] | null> = [
    ["Document ID", target.documentId],
    source?.ticker ? [locale === "vi" ? "Công ty" : "Company", formatCompanyLabel(source.ticker)] : null,
    source?.section ? [locale === "vi" ? "Mục" : "Section", source.section] : null,
    source?.filing_date ? [locale === "vi" ? "Ngày nộp" : "Filed", source.filing_date] : null,
    source?.report_date ? [locale === "vi" ? "Ngày báo cáo" : "Report date", source.report_date] : null,
    target.kind === "catalog" && target.accessionNumber ? ["Accession", target.accessionNumber] : null,
    target.kind === "catalog" && sanitizeSecBrowserUrl(target.sourceUrl)
      ? [locale === "vi" ? "Source URL" : "Source URL", sanitizeSecBrowserUrl(target.sourceUrl)]
      : null,
  ].filter((row): row is [string, string | null | undefined] => Boolean(row));

  return (
    <dl>
      {rows.map(([label, value]) => (
        <div key={`${label}-${value}`}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function RouteDocumentAside({ target, onBack, readerSession }: RouteDocumentContextProps) {
  const { locale } = useLocale();
  const source = sourceFor(target);
  const backButtonRef = useRef<HTMLButtonElement>(null);
  return (
    <aside
      className="workbench-route-document-layout"
      data-workbench-context="true"
      data-workbench-route-origin={target.kind}
      aria-label="Document workspace"
    >
      <DocumentPane
        key={`${target.kind}:${target.documentId}:${source?.chunk_id ?? "document"}`}
        documentId={target.documentId}
        title={titleFor(target)}
        indexedSource={source}
        indexedExcerpt={indexedExcerptFor(source)}
        metadata={metadataFor(target, locale)}
        onBack={onBack}
        backButtonRef={backButtonRef}
        readerSession={readerSession}
        origin={originFor(target)}
        initialTab={target.initialTab}
      />
    </aside>
  );
}

/**
 * Keeps route-local catalog/search/retrieval state mounted in Research while
 * rendering their exact document target in the shared contextual slot. The
 * shell owns the responsive downgrade; this adapter only chooses the
 * appropriate presentation for the measured mode.
 */
export function RouteDocumentContext(props: RouteDocumentContextProps) {
  const { locale } = useLocale();
  const workbench = useOptionalWorkbenchContext();
  const mode: WorkbenchLayoutMode = workbench?.controller.state.layoutMode ?? "single-surface";
  const backButtonRef = useRef<HTMLButtonElement>(null);
  const source = sourceFor(props.target);

  if (mode === "four-pane" || mode === "context-dock") {
    return <RouteDocumentAside {...props} />;
  }

  return (
    <ModalDialog
      open
      onClose={props.onBack}
      ariaLabel={locale === "vi" ? "Không gian tài liệu" : "Document workspace"}
      initialFocusRef={backButtonRef}
      overlayClassName="workbench-route-document-overlay"
      className="workbench-route-document-dialog"
    >
      <aside
        className="workbench-route-document-layout"
        data-workbench-context="true"
        data-workbench-route-origin={props.target.kind}
        aria-label={locale === "vi" ? "Không gian tài liệu" : "Document workspace"}
      >
        <DocumentPane
          key={`${props.target.kind}:${props.target.documentId}:${source?.chunk_id ?? "document"}`}
          documentId={props.target.documentId}
          title={titleFor(props.target)}
          indexedSource={source}
          indexedExcerpt={indexedExcerptFor(source)}
          metadata={metadataFor(props.target, locale)}
          onBack={props.onBack}
          backButtonRef={backButtonRef}
          readerSession={props.readerSession}
          origin={originFor(props.target)}
          initialTab={props.target.initialTab}
        />
      </aside>
    </ModalDialog>
  );
}

export default RouteDocumentContext;
