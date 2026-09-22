import { useEffect, useRef, type PointerEvent as ReactPointerEvent } from "react";
import { useLocale } from "../../lib/i18n";
import {
  clampPaneWidth,
  WORKBENCH_PANE_LIMITS,
  type WorkbenchPane,
} from "../../lib/workbench";

export interface PaneResizerProps {
  pane: WorkbenchPane;
  width: number;
  collapsed: boolean;
  onCommit: (width: number) => void;
  onReset: () => void;
  onCollapsedChange?: (collapsed: boolean) => void;
}

function getWidthVariable(pane: WorkbenchPane): string {
  return pane === "sources"
    ? "--workbench-sources-width"
    : "--workbench-document-width";
}

function getTrackVariable(pane: WorkbenchPane): string {
  return pane === "sources"
    ? "--workbench-sources-track-width"
    : "--workbench-document-track-width";
}

function scheduleFrame(callback: () => void): number {
  return typeof window.requestAnimationFrame === "function"
    ? window.requestAnimationFrame(callback)
    : window.setTimeout(callback, 0);
}

function cancelFrame(handle: number): void {
  if (typeof window.cancelAnimationFrame === "function") {
    window.cancelAnimationFrame(handle);
  } else {
    window.clearTimeout(handle);
  }
}

function setLiveWidth(element: HTMLElement, pane: WorkbenchPane, width: number): void {
  const layout = element.closest<HTMLElement>("[data-workbench-layout]");
  if (!layout) return;
  const value = `${clampPaneWidth(pane, width)}px`;
  layout.style.setProperty(getWidthVariable(pane), value);
  layout.style.setProperty(getTrackVariable(pane), value);
}

/**
 * Accessible splitter for a Sources or Document track. Pointer moves update
 * CSS variables in rAF; the preference hook is called only when the gesture
 * commits, so React and storage do not rerender on every pointer event.
 */
export function PaneResizer({
  pane,
  width,
  collapsed,
  onCommit,
  onReset,
  onCollapsedChange,
}: PaneResizerProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const limits = WORKBENCH_PANE_LIMITS[pane];
  const cleanupRef = useRef<(() => void) | null>(null);
  const elementRef = useRef<HTMLDivElement>(null);
  const label = pane === "sources"
    ? (vi ? "bảng nguồn" : "Sources pane")
    : (vi ? "bảng tài liệu" : "Document pane");

  useEffect(() => () => {
    cleanupRef.current?.();
    cleanupRef.current = null;
  }, []);

  const commitWidth = (nextWidth: number) => {
    const next = clampPaneWidth(pane, nextWidth);
    onCollapsedChange?.(false);
    onCommit(next);
  };

  const reset = () => {
    onCollapsedChange?.(false);
    onReset();
  };

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    cleanupRef.current?.();

    const element = elementRef.current;
    if (!element) return;
    const startX = event.clientX;
    const startWidth = clampPaneWidth(pane, width);
    let nextWidth = startWidth;
    let frame: number | null = null;
    let finished = false;

    onCollapsedChange?.(false);
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is optional in older browser/test hosts.
    }

    const apply = () => {
      frame = null;
      if (!finished) setLiveWidth(element, pane, nextWidth);
    };
    const schedule = () => {
      if (frame === null) frame = scheduleFrame(apply);
    };
    const handleMove = (moveEvent: PointerEvent) => {
      if (finished) return;
      // The splitter sits at the left edge of its pane. Moving left makes the
      // pane wider; moving right makes it narrower.
      nextWidth = clampPaneWidth(pane, startWidth + startX - moveEvent.clientX);
      schedule();
    };
    const finish = (commit: boolean) => {
      if (finished) return;
      finished = true;
      if (frame !== null) {
        cancelFrame(frame);
        frame = null;
      }
      if (commit) {
        setLiveWidth(element, pane, nextWidth);
        onCommit(nextWidth);
      } else {
        setLiveWidth(element, pane, startWidth);
      }
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerCancel);
      cleanupRef.current = null;
    };
    const handlePointerUp = () => finish(true);
    const handlePointerCancel = () => finish(false);

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerCancel);
    cleanupRef.current = () => finish(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      commitWidth(width + 16);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      commitWidth(width - 16);
    } else if (event.key === "Home") {
      event.preventDefault();
      commitWidth(limits.min);
    } else if (event.key === "End") {
      event.preventDefault();
      commitWidth(limits.max);
    } else if (event.key === "Enter" || event.key === " ") {
      if (!onCollapsedChange) return;
      event.preventDefault();
      onCollapsedChange(!collapsed);
    }
  };

  return (
    <div
      ref={elementRef}
      className={`workbench-pane-resizer workbench-pane-resizer--${pane}`}
      data-pane-resizer={pane}
      data-pane-resizer-width={width}
      role="separator"
      tabIndex={0}
      aria-orientation="vertical"
      aria-valuemin={limits.min}
      aria-valuemax={limits.max}
      aria-valuenow={clampPaneWidth(pane, width)}
      aria-valuetext={`${clampPaneWidth(pane, width)}px ${label}`}
      aria-label={vi ? `Đổi độ rộng ${label}` : `Resize ${label}`}
      onPointerDown={handlePointerDown}
      onDoubleClick={reset}
      onKeyDown={handleKeyDown}
    >
      <span className="workbench-pane-resizer__line" aria-hidden="true" />
      <details className="workbench-pane-resizer__menu">
        <summary aria-label={vi ? `Mở điều khiển kích thước ${label}` : `Open ${label} size controls`}>⋯</summary>
        <div className="workbench-pane-resizer__controls" role="group" aria-label={vi ? `Điều khiển kích thước ${label}` : `${label} size controls`}>
          <button type="button" onClick={() => commitWidth(width + 16)} disabled={width >= limits.max}>
            {vi ? "Rộng hơn" : "Wider"}
          </button>
          <button type="button" onClick={() => commitWidth(width - 16)} disabled={width <= limits.min}>
            {vi ? "Hẹp hơn" : "Narrower"}
          </button>
          <button type="button" onClick={reset}>{vi ? "Đặt lại" : "Reset"}</button>
        </div>
      </details>
    </div>
  );
}

export default PaneResizer;
