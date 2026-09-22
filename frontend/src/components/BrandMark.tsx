/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";

interface BrandMarkProps {
  size?: "xs" | "sm" | "md" | "lg";
  className?: string;
}

/** A compact, project-owned mark for the document/evidence workspace. */
export const BrandMark = React.memo<BrandMarkProps>(
  ({ size = "md", className = "" }) => (
    <span
      className={`brand-mark brand-mark--${size} ${className}`.trim()}
      aria-hidden="true"
    >
      <span className="brand-mark__surface">
        <svg viewBox="0 0 32 32" className="brand-mark__icon" fill="none" aria-hidden="true">
          <path d="m3 8.5 13-6 13 6-13 6-13-6Z" stroke="currentColor" strokeWidth="2.35" strokeLinejoin="round" />
          <path d="m3 15.5 13 6 13-6" stroke="currentColor" strokeWidth="2.35" strokeLinecap="round" strokeLinejoin="round" />
          <path d="m3 22.5 13 6 13-6" stroke="var(--evidence-accent)" strokeWidth="2.35" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </span>
  ),
);

BrandMark.displayName = "BrandMark";
