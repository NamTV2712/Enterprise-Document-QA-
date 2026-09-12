import React, { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectFieldProps {
  label: string;
  value: string;
  options: SelectOption[];
  onValueChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
  ariaInvalid?: boolean;
  ariaDescribedBy?: string;
}

/**
 * Shared listbox-based select for compact, app-owned controls. It intentionally
 * replaces browser-native menus while preserving keyboard semantics.
 */
export function SelectField({
  label,
  value,
  options,
  onValueChange,
  disabled = false,
  className = "",
  ariaInvalid = false,
  ariaDescribedBy,
}: SelectFieldProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const typeaheadRef = useRef("");
  const typeaheadTimeoutRef = useRef<number | undefined>(undefined);
  const listboxId = useId();
  const [menuPosition, setMenuPosition] = useState<React.CSSProperties>();
  const selectedIndex = Math.max(0, options.findIndex((option) => option.value === value));
  const selected = options[selectedIndex] ?? options[0];

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!rootRef.current?.contains(target) && !menuRef.current?.contains(target)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  useEffect(() => {
    if (open && menuPosition) optionRefs.current[selectedIndex]?.focus();
  }, [menuPosition, open, selectedIndex]);

  useLayoutEffect(() => {
    if (!open) return;
    const updatePosition = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const viewportPadding = 8;
      const maxHeight = Math.min(240, window.innerHeight - viewportPadding * 2);
      const belowSpace = window.innerHeight - rect.bottom - viewportPadding;
      const openUpward = belowSpace < Math.min(160, maxHeight) && rect.top > belowSpace;
      setMenuPosition({
        position: "fixed",
        zIndex: 70,
        left: Math.max(viewportPadding, Math.min(rect.left, window.innerWidth - rect.width - viewportPadding)),
        top: openUpward ? undefined : rect.bottom + 6,
        bottom: openUpward ? window.innerHeight - rect.top + 6 : undefined,
        width: Math.min(rect.width, window.innerWidth - viewportPadding * 2),
        maxHeight,
      });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open]);

  const closeAndReturnFocus = () => {
    setOpen(false);
    requestAnimationFrame(() => triggerRef.current?.focus());
  };

  const selectOption = (option: SelectOption) => {
    if (!option.disabled) onValueChange(option.value);
    closeAndReturnFocus();
  };

  const moveFocus = (from: number, direction: 1 | -1) => {
    let index = from;
    for (let attempts = 0; attempts < options.length; attempts += 1) {
      index = (index + direction + options.length) % options.length;
      if (!options[index]?.disabled) {
        optionRefs.current[index]?.focus();
        return;
      }
    }
  };

  const focusBoundary = (direction: 1 | -1) => {
    const indexes = options.map((_, index) => index);
    const ordered = direction === 1 ? indexes : indexes.reverse();
    const index = ordered.find((candidate) => !options[candidate]?.disabled);
    if (index !== undefined) optionRefs.current[index]?.focus();
  };

  const focusByPrefix = (key: string) => {
    window.clearTimeout(typeaheadTimeoutRef.current);
    typeaheadRef.current += key.toLocaleLowerCase();
    const prefix = typeaheadRef.current;
    const option = options.findIndex((candidate) =>
      !candidate.disabled && candidate.label.toLocaleLowerCase().startsWith(prefix),
    );
    if (option >= 0) optionRefs.current[option]?.focus();
    typeaheadTimeoutRef.current = window.setTimeout(() => { typeaheadRef.current = ""; }, 500);
  };

  useEffect(() => () => window.clearTimeout(typeaheadTimeoutRef.current), []);

  return (
    <div ref={rootRef} className={`select-field ${className}`.trim()}>
      <span className="select-field__label">{label}</span>
      <button
        ref={triggerRef}
        type="button"
        className="select-field__trigger"
        aria-label={label}
        aria-invalid={ariaInvalid || undefined}
        aria-describedby={ariaDescribedBy}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        disabled={disabled || options.length === 0}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp" || event.key === " ") {
            event.preventDefault();
            setOpen(true);
          } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
            event.preventDefault();
            setOpen(true);
            requestAnimationFrame(() => focusByPrefix(event.key));
          }
        }}
      >
        <span>{selected?.label ?? "—"}</span>
        <svg viewBox="0 0 16 16" aria-hidden="true" className="select-field__chevron">
          <path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && menuPosition && createPortal(
        <div ref={menuRef} id={listboxId} role="listbox" aria-label={label} className="select-field__menu" style={menuPosition}>
          {options.map((option, index) => (
            <button
              key={option.value}
              ref={(element) => { optionRefs.current[index] = element; }}
              type="button"
              role="option"
              aria-selected={option.value === value}
              disabled={option.disabled}
              className="select-field__option"
              onClick={() => selectOption(option)}
              onKeyDown={(event) => {
                if (event.key === "ArrowDown") { event.preventDefault(); moveFocus(index, 1); }
                if (event.key === "ArrowUp") { event.preventDefault(); moveFocus(index, -1); }
                if (event.key === "Home") { event.preventDefault(); focusBoundary(1); }
                if (event.key === "End") { event.preventDefault(); focusBoundary(-1); }
                if (event.key === "Escape") { event.preventDefault(); closeAndReturnFocus(); }
                if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
                  event.preventDefault();
                  focusByPrefix(event.key);
                }
              }}
            >
              {option.label}
            </button>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
}
