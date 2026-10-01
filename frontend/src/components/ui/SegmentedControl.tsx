import React, { useId, useRef } from "react";

export interface SegmentOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SegmentedControlProps {
  label: string;
  value: string;
  options: SegmentOption[];
  onValueChange: (value: string) => void;
  className?: string;
}

/** A compact radio-group for small, mutually exclusive fixed choices. */
export function SegmentedControl({ label, value, options, onValueChange, className = "" }: SegmentedControlProps) {
  const groupId = useId();
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const selectedIndex = Math.max(0, options.findIndex((option) => option.value === value));

  const selectOffset = (offset: 1 | -1) => {
    let index = selectedIndex;
    for (let attempts = 0; attempts < options.length; attempts += 1) {
      index = (index + offset + options.length) % options.length;
      if (!options[index]?.disabled) {
        onValueChange(options[index].value);
        requestAnimationFrame(() => optionRefs.current[index]?.focus());
        return;
      }
    }
  };

  return (
    <div className={`segmented-control ${className}`.trim()}>
      <span id={groupId} className="sr-only">{label}</span>
      <div role="radiogroup" aria-labelledby={groupId} className="segmented-control__group">
        {options.map((option, index) => (
          <button
            key={option.value}
            ref={(element) => { optionRefs.current[index] = element; }}
            type="button"
            role="radio"
            aria-checked={option.value === value}
            disabled={option.disabled}
            className={`segmented-control__option${option.value === value ? " is-selected" : ""}`}
            onClick={() => onValueChange(option.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); selectOffset(1); }
              if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); selectOffset(-1); }
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
