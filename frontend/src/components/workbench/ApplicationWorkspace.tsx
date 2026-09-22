import React, { type ReactNode } from "react";
import { useWorkbenchController } from "../../hooks/useWorkbenchController";
import { useWorkbenchPreferences } from "../../hooks/useWorkbenchPreferences";
import { ResearchWorkbench } from "./ResearchWorkbench";
import { WorkbenchLayout } from "./WorkbenchLayout";
import { WorkbenchContextProvider } from "./WorkbenchContext";
import type { WorkbenchTarget } from "../../lib/workbench";

export interface ApplicationWorkspaceProps {
  /** Global navigation remains owned by the application shell. */
  navigation: ReactNode;
  /** The global header remains outside the route-local research surface. */
  header: ReactNode;
  /** The existing route-local main surface, passed through unchanged. */
  children: ReactNode;
  /** Optional contextual Sources/Document surface rendered beside Research. */
  context?: ReactNode;
  /** Identifies the contextual surface so the shell can size route handoffs. */
  contextKind?: "evidence" | "document";
  /** Cross-route identity mirrored into the presentation controller. */
  target?: WorkbenchTarget | null;
  /** Composer or other route-local footer content that follows the canvas. */
  footer?: ReactNode;
  /** Global dialogs and overlays owned by App.tsx. */
  overlays?: ReactNode;
  className?: string;
}

/**
 * Application-level composition boundary for the V5 workbench.
 *
 * This component deliberately does not own questions, answers, source
 * identity, reader transport, or persistence. It mounts the presentation
 * controller/preferences seam and lets the existing route content continue
 * to own those concerns while the shell is migrated incrementally.
 */
export function ApplicationWorkspace({
  navigation,
  header,
  children,
  context,
  contextKind,
  target = null,
  footer,
  overlays,
  className,
}: ApplicationWorkspaceProps) {
  const controller = useWorkbenchController();
  const preferences = useWorkbenchPreferences();
  const { setTarget, rememberFocus, clearFocusReturn } = controller;

  // A new route target must update presentation state before the document
  // surface paints. Depend only on the stable action callbacks: depending on
  // the controller object would replay this handoff after every reader-state
  // update and could clear a freshly resolved evidence binding.
  React.useLayoutEffect(() => {
    setTarget(target);
    if (target && "returnFocusId" in target) rememberFocus(target.returnFocusId);
    else clearFocusReturn();
  }, [clearFocusReturn, rememberFocus, setTarget, target]);

  return (
    <WorkbenchContextProvider value={{ controller, preferences }}>
    <div
      className={`app-shell flex w-screen max-w-full h-dvh font-sans text-[var(--text-primary)] overflow-hidden bg-grid-pattern workbench-application-shell${className ? ` ${className}` : ""}`}
      data-workbench-app="true"
    >
      {navigation}

      <div className="workbench-application-main w-0 flex-1 min-w-0 max-w-full flex flex-col h-full overflow-hidden">
        {header}
        <WorkbenchLayout controller={controller} preferences={preferences} context={context} contextKind={contextKind}>
          <ResearchWorkbench>{children}</ResearchWorkbench>
        </WorkbenchLayout>
        {footer}
      </div>

      {overlays}
    </div>
    </WorkbenchContextProvider>
  );
}
