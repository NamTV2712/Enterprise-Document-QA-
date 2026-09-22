import React, {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { useLocale } from "../../lib/i18n";
import {
  deriveEffectivePaneWidths,
  deriveWorkbenchLayoutMode,
  type WorkbenchGeometry,
} from "../../lib/workbench";
import type { WorkbenchController } from "../../hooks/useWorkbenchController";
import type { WorkbenchPreferencesController } from "../../hooks/useWorkbenchPreferences";

export interface WorkbenchLayoutProps {
  controller: WorkbenchController;
  preferences: WorkbenchPreferencesController;
  children: ReactNode;
  context?: ReactNode;
  contextKind?: "evidence" | "document";
}

const INITIAL_GEOMETRY: WorkbenchGeometry = {
  containerWidth: 0,
  containerHeight: 0,
  navigationWidth: 0,
};

function measureWorkbench(element: HTMLElement): WorkbenchGeometry {
  const shell = element.closest<HTMLElement>("[data-workbench-app]");
  const navigation = shell?.querySelector<HTMLElement>("[data-workbench-region=\"navigation\"]");
  const elementRect = element.getBoundingClientRect();
  const shellRect = shell?.getBoundingClientRect();

  return {
    // The shell width is the true available geometry. The fallback keeps the
    // component useful in isolated embedding/test hosts.
    containerWidth: shellRect?.width || elementRect.width,
    containerHeight: elementRect.height,
    navigationWidth: navigation?.getBoundingClientRect().width ?? 0,
  };
}

/**
 * Shared layout seam for the application shell. It measures the rendered
 * container and navigation rather than selecting a mode from viewport
 * breakpoints alone. Route content and contextual evidence are sibling
 * surfaces so the mode can own their composition without owning their data.
 */
export function WorkbenchLayout({ controller, preferences, children, context, contextKind }: WorkbenchLayoutProps) {
  const { t } = useLocale();
  const { state, setLayoutMode } = controller;
  const layoutRef = useRef<HTMLDivElement>(null);
  const [geometry, setGeometry] = useState<WorkbenchGeometry>(INITIAL_GEOMETRY);

  useLayoutEffect(() => {
    const element = layoutRef.current;
    if (!element) return;

    const sync = () => setGeometry(measureWorkbench(element));
    sync();

    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(sync);
      observer.observe(element);
      const shell = element.closest<HTMLElement>("[data-workbench-app]");
      if (shell && shell !== element) observer.observe(shell);
      return () => observer.disconnect();
    }

    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, []);

  const measuredLayoutMode = useMemo(
    () => deriveWorkbenchLayoutMode({
      ...geometry,
      sourcesWidth: preferences.sourcesWidth,
      documentWidth: preferences.documentWidth,
    }),
    [geometry, preferences.documentWidth, preferences.sourcesWidth],
  );

  // The rendered tracks must match the widths the mode decision used, so a
  // narrower desktop shrinks the document pane instead of overflowing it.
  const effectiveWidths = useMemo(
    () => deriveEffectivePaneWidths({
      ...geometry,
      sourcesWidth: preferences.sourcesWidth,
      documentWidth: preferences.documentWidth,
    }),
    [geometry, preferences.documentWidth, preferences.sourcesWidth],
  );

  useEffect(() => {
    if (geometry.containerWidth <= 0 || geometry.containerHeight <= 0) return;
    setLayoutMode(measuredLayoutMode);
  }, [geometry.containerHeight, geometry.containerWidth, measuredLayoutMode, setLayoutMode]);

  const style = {
    "--workbench-navigation-width": `${geometry.navigationWidth}px`,
    "--workbench-sources-width": `${preferences.sourcesWidth}px`,
    "--workbench-document-width": `${preferences.documentWidth}px`,
    "--workbench-sources-track-width": `${preferences.sourcesCollapsed ? 56 : effectiveWidths.sourcesWidth}px`,
    "--workbench-document-track-width": `${preferences.documentCollapsed ? 56 : effectiveWidths.documentWidth}px`,
    "--workbench-splitter-width": "8px",
  } as CSSProperties;

  return (
    <div
      ref={layoutRef}
      className="workbench-layout"
      data-workbench-layout="true"
      data-workbench-layout-mode={state.layoutMode}
      data-workbench-measured={geometry.containerWidth > 0 && geometry.containerHeight > 0 ? "true" : "false"}
      data-workbench-navigation-width={Math.round(geometry.navigationWidth)}
      data-workbench-short-height={geometry.containerHeight > 0 && geometry.containerHeight < 720 ? "true" : "false"}
      data-workbench-context={context ? "true" : "false"}
      data-workbench-context-kind={context ? (contextKind ?? "evidence") : "none"}
      aria-label={t("workbench.layout")}
      style={style}
    >
      <div className="workbench-layout__content" data-workbench-has-context={context ? "true" : "false"} data-workbench-context-kind={context ? (contextKind ?? "evidence") : "none"}>
        {children}
        {context}
      </div>
    </div>
  );
}
