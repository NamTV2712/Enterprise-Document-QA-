import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

let nextModalId = 1;
const modalStack: number[] = [];

interface ModalDialogProps {
  open: boolean;
  onClose: () => void;
  labelledBy?: string;
  describedBy?: string;
  ariaLabel?: string;
  initialFocusRef?: RefObject<HTMLElement | null>;
  overlayClassName?: string;
  className: string;
  children: ReactNode;
}

/** Shared modal mechanics for blocking, short-lived workspace decisions. */
export function ModalDialog({
  open,
  onClose,
  labelledBy,
  describedBy,
  ariaLabel,
  initialFocusRef,
  overlayClassName,
  className,
  children,
}: ModalDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const modalIdRef = useRef<number | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    if (modalIdRef.current === null) modalIdRef.current = nextModalId++;
    const modalId = modalIdRef.current;
    modalStack.push(modalId);
    const ownsTopLayer = () => modalStack[modalStack.length - 1] === modalId;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    const previousPaddingRight = document.body.style.paddingRight;
    const appRoot = document.getElementById("root");
    const previousAriaHidden = appRoot?.getAttribute("aria-hidden") ?? null;
    const wasInert = appRoot?.hasAttribute("inert") ?? false;
    const scrollbarWidth = Math.max(0, window.innerWidth - document.documentElement.clientWidth);
    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`;
    // The dialog is portaled outside #root, so the application can be made
    // inert without hiding the active modal from assistive technology.
    appRoot?.setAttribute("aria-hidden", "true");
    appRoot?.setAttribute("inert", "");
    initialFocusRef?.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (!ownsTopLayer()) return;
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [href], [contenteditable="true"], [tabindex]:not([tabindex="-1"])',
        ) || [],
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      const stackIndex = modalStack.lastIndexOf(modalId);
      if (stackIndex >= 0) modalStack.splice(stackIndex, 1);
      document.body.style.overflow = previousOverflow;
      document.body.style.paddingRight = previousPaddingRight;
      if (previousAriaHidden === null) appRoot?.removeAttribute("aria-hidden");
      else appRoot?.setAttribute("aria-hidden", previousAriaHidden);
      if (!wasInert) appRoot?.removeAttribute("inert");
      previouslyFocused?.focus();
    };
  }, [initialFocusRef, open]);

  if (!open) return null;
  return createPortal(
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center overlay-backdrop p-4 ${overlayClassName ?? ""}`}
      role="presentation"
      onMouseDown={(event) => {
        if (modalStack[modalStack.length - 1] === modalIdRef.current && event.target === event.currentTarget) {
          onCloseRef.current();
        }
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        aria-label={ariaLabel}
        className={className}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
