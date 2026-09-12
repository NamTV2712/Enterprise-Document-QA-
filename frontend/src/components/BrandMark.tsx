/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";

interface BrandMarkProps {
  size?: "xs" | "sm" | "md" | "lg";
  className?: string;
}

/**
 * A folded filing page with one evidence/search connection: compact enough
 * for the sidebar, but specific to document retrieval rather than generic AI.
 */
export const BrandMark = React.memo<BrandMarkProps>(
  ({ size = "md", className = "" }) => (
    <span
      className={`brand-mark brand-mark--${size} ${className}`.trim()}
      aria-hidden="true"
    >
      <span className="brand-mark__surface">
        <svg viewBox="0 0 24 24" className="brand-mark__icon" fill="none" aria-hidden="true">
          <path d="M6.5 4.5h6.1l4.9 4.4v10.6H6.5V4.5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M12.6 4.5v4.4h4.9" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
          <circle cx="14.9" cy="14.9" r="2.65" stroke="currentColor" strokeWidth="1.7" />
          <path d="m16.8 16.8 2.4 2.4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      </span>
    </span>
  ),
);

BrandMark.displayName = "BrandMark";
