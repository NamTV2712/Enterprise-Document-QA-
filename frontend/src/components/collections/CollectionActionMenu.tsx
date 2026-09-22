import { useEffect, useRef, useState } from "react";
import { MoreHorizontal } from "lucide-react";

export interface CollectionActionMenuItem {
  key: string;
  label: string;
  onSelect: () => void;
  danger?: boolean;
  disabled?: boolean;
}

interface CollectionActionMenuProps {
  /** Accessible name for the trigger, e.g. "Actions for Risk Analysis". */
  label: string;
  items: CollectionActionMenuItem[];
  className?: string;
}

/**
 * The reference's per-card "…" control. It only ever carries actions the
 * workspace can really perform, and it behaves like a menu: Escape closes it
 * and returns focus, an outside press closes it, and the arrow keys move
 * between items.
 */
export function CollectionActionMenu({ label, items, className = "" }: CollectionActionMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (open) requestAnimationFrame(() => itemRefs.current[0]?.focus());
  }, [open]);

  const move = (offset: 1 | -1) => {
    const enabled = items.map((item, index) => (item.disabled ? -1 : index)).filter((index) => index >= 0);
    if (enabled.length === 0) return;
    const current = itemRefs.current.findIndex((element) => element === document.activeElement);
    const position = enabled.indexOf(current);
    const next = enabled[(position + offset + enabled.length) % enabled.length];
    itemRefs.current[next]?.focus();
  };

  return (
    <span className={`collection-menu ${className}`.trim()} ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="collection-menu__trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        onClick={() => setOpen((current) => !current)}
      >
        <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
      </button>
      {open && (
        <span
          className="collection-menu__surface"
          role="menu"
          aria-label={label}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              move(1);
            }
            if (event.key === "ArrowUp") {
              event.preventDefault();
              move(-1);
            }
          }}
        >
          {items.map((item, index) => (
            <button
              key={item.key}
              ref={(element) => {
                itemRefs.current[index] = element;
              }}
              type="button"
              role="menuitem"
              className={`collection-menu__item ${item.danger ? "collection-menu__item--danger" : ""}`.trim()}
              disabled={item.disabled}
              onClick={() => {
                setOpen(false);
                triggerRef.current?.focus();
                item.onSelect();
              }}
            >
              {item.label}
            </button>
          ))}
        </span>
      )}
    </span>
  );
}
