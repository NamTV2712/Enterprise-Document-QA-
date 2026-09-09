/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";

interface BrandMarkProps {
  size?: "xs" | "sm" | "md";
  className?: string;
}

/**
 * Two offset filing pages joined by an evidence mark: compact enough for the
 * sidebar, but specific to document retrieval rather than generic AI.
 */
export const BrandMark = React.memo<BrandMarkProps>(
  ({ size = "md", className = "" }) => (
    <span
      className={`brand-mark brand-mark--${size} ${className}`.trim()}
      aria-hidden="true"
    >
      <span className="brand-mark__glow" />
      <span className="brand-mark__surface">
        <svg viewBox="0 0 24 24" className="brand-mark__icon" fill="none" aria-hidden="true">
          <path d="M7.5 4.5h7l3 3v10a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
          <path d="M14.5 4.5v3h3M8.5 12h6M8.5 15h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          <path d="m15.5 15.5 1.25 1.25 2.75-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </span>
  ),
);

BrandMark.displayName = "BrandMark";
