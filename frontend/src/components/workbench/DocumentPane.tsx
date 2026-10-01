import { useCallback, useEffect, useRef, useState } from "react";
import type { ActiveRepresentation, DocumentContextTab } from "../../lib/workbench";
import { bindSource, type ReaderLocationEvent } from "../../lib/readerLocationView";
import { useOptionalWorkbenchContext } from "./WorkbenchContext";
import { DocumentWorkspace, type DocumentWorkspaceProps } from "../DocumentWorkspace";

export interface DocumentPaneProps extends DocumentWorkspaceProps {}

/**
 * Shared workbench adapter for the existing document workspace and readers.
 * It owns no transport or document identity; those remain in the callers and
 * in the reader session passed through to DocumentWorkspace.
 */
export function DocumentPane({ className, initialTab = "document", ...workspaceProps }: DocumentPaneProps) {
  const workbench = useOptionalWorkbenchContext();
  const controller = workbench?.controller;
  const [localRepresentation, setLocalRepresentation] = useState<ActiveRepresentation>("structured");
  const [localContextTab, setLocalContextTab] = useState<DocumentContextTab>("evidence");
  const [localFindQuery, setLocalFindQuery] = useState("");
  const [localExpanded, setLocalExpanded] = useState(false);
  const identityKey = workspaceProps.documentId + "::" + (workspaceProps.indexedSource?.chunk_id ?? workspaceProps.indexedSource?.document_id ?? "document");
  // The workbench controller survives responsive layout changes. A document
  // pane can therefore remount while the same document is still active; do
  // not reset its selected representation merely because its DOM parent
  // changed from a four-pane track to a dock/drawer surface.
  const previousIdentityRef = useRef<string | null>(null);
  const initialContextTab: DocumentContextTab = workspaceProps.initialContextTab ?? (initialTab === "metadata" ? "metadata" : "evidence");
  const setControllerRepresentation = controller?.setRepresentation;
  const setControllerContextTab = controller?.setDocumentContextTab;
  const setControllerFindQuery = controller?.setDocumentFindQuery;
  const setControllerActivePane = controller?.setActivePane;
  const clearControllerEvidenceBinding = controller?.clearEvidenceBinding;
  const beginControllerEvidenceResolution = controller?.beginEvidenceResolution;
  const resolveControllerEvidence = controller?.resolveEvidence;
  const rejectControllerEvidence = controller?.rejectEvidence;
  const externalLocationEvent = workspaceProps.onLocationEvent;
  // When a route-level target is present, its controller is the sole owner
  // of cross-document reset semantics. A DocumentPane can unmount and mount
  // again solely because the responsive shell changed shape, so its initial
  // mount must not overwrite the target-owned reader state.
  const controllerOwnsTarget = controller?.state.target != null;

  useEffect(() => {
    const previousIdentity = previousIdentityRef.current;
    const firstMount = previousIdentity === null;
    const identityChanged = previousIdentity !== null && previousIdentity !== identityKey;
    previousIdentityRef.current = identityKey;
    setControllerActivePane?.("document");
    if (!firstMount && !identityChanged) return;
    setLocalRepresentation("structured");
    setLocalContextTab(initialContextTab);
    setLocalFindQuery("");
    setLocalExpanded(false);
    if (controllerOwnsTarget) return;
    clearControllerEvidenceBinding?.();
    if (identityChanged) setControllerRepresentation?.("structured");
    setControllerContextTab?.(initialContextTab);
    setControllerFindQuery?.("");
  }, [clearControllerEvidenceBinding, controllerOwnsTarget, identityKey, initialContextTab, setControllerActivePane, setControllerContextTab, setControllerFindQuery, setControllerRepresentation]);

  const handleRepresentationChange = useCallback((next: ActiveRepresentation) => {
    setLocalRepresentation(next);
    setControllerRepresentation?.(next);
  }, [setControllerRepresentation]);
  const handleContextTabChange = useCallback((next: DocumentContextTab) => {
    setLocalContextTab(next);
    setControllerContextTab?.(next);
  }, [setControllerContextTab]);
  const handleFindQueryChange = useCallback((next: string) => {
    setLocalFindQuery(next);
    setControllerFindQuery?.(next);
  }, [setControllerFindQuery]);
  const handleExpandedChange = useCallback((next: boolean) => {
    setLocalExpanded(next);
  }, []);

  const handleLocationEvent = useCallback((event: ReaderLocationEvent) => {
    externalLocationEvent?.(event);
    if (event.state === "resolving") {
      beginControllerEvidenceResolution?.(event.generation);
    } else if (event.state === "resolved") {
      resolveControllerEvidence?.(event.generation, bindSource(event.source, event.location), event.location);
    } else {
      rejectControllerEvidence?.(event.generation, event.state === "error" ? "error" : event.state, event.reason);
    }
  }, [beginControllerEvidenceResolution, externalLocationEvent, rejectControllerEvidence, resolveControllerEvidence]);

  const representation = controller?.state.activeRepresentation ?? localRepresentation;
  const contextTab = controller?.state.documentContextTab ?? localContextTab;
  const findQuery = controller?.state.documentFindQuery ?? localFindQuery;

  return (
    <section
      className={["document-pane", className ?? ""].filter(Boolean).join(" ")}
      data-workbench-region="document"
      data-document-pane="true"
      data-active-representation={representation}
      aria-label="Document pane"
    >
      <DocumentWorkspace
        {...workspaceProps}
        initialTab={initialTab}
        initialContextTab={initialContextTab}
        representation={representation}
        onRepresentationChange={handleRepresentationChange}
        activeContextTab={contextTab}
        onContextTabChange={handleContextTabChange}
        findQuery={findQuery}
        onFindQueryChange={handleFindQueryChange}
        onLocationEvent={handleLocationEvent}
        expanded={localExpanded}
        onExpandedChange={handleExpandedChange}
        showLegacyTabs={initialTab !== "document"}
        showContextTabs
      />
    </section>
  );
}

export default DocumentPane;
