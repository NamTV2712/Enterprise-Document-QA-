import React from "react";

interface NumberRangeFieldProps {
  id: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
  hint?: string;
  onChange: (value: number) => void;
}

/**
 * A small, accessible range control for bounded numeric retrieval settings.
 * The value remains visible and is committed to React state; callers decide
 * when that state becomes a backend request.
 */
export function NumberRangeField({
  id,
  label,
  value,
  min,
  max,
  step = 1,
  disabled = false,
  hint,
  onChange,
}: NumberRangeFieldProps) {
  return (
    <div className="number-range-field">
      <div className="number-range-field__header">
        <label htmlFor={id}>{label}</label>
        <output htmlFor={id} aria-label={`${label}: ${value}`}>{value}</output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        aria-valuetext={`${value}`}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      {hint && <p className="number-range-field__hint">{hint}</p>}
    </div>
  );
}
