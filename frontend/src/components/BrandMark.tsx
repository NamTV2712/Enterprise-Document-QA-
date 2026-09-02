/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { TrendingUp } from "lucide-react";

interface BrandMarkProps {
  size?: "sm" | "md";
  className?: string;
}

/**
 * A compact, high-contrast brand mark that remains legible in both themes.
 * The glow is CSS-only so it does not add an image request or another asset.
 */
export const BrandMark = React.memo<BrandMarkProps>(
  ({ size = "md", className = "" }) => (
    <span
      className={`brand-mark brand-mark--${size} ${className}`.trim()}
      aria-hidden="true"
    >
      <span className="brand-mark__glow" />
      <span className="brand-mark__surface">
        <TrendingUp className="brand-mark__icon" strokeWidth={2.4} />
      </span>
    </span>
  ),
);

BrandMark.displayName = "BrandMark";
