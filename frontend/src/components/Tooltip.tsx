/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  align?: "left" | "center" | "right";
  placement?: "top" | "bottom";
  maxWidth?: string;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  align = "center",
  placement = "top",
  maxWidth = "250px",
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    // Start a 300ms timer
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, 300);
  };

  const handleMouseLeave = () => {
    // Clear the timeout and hide immediately
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsVisible(false);
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Determine alignment classes
  let alignmentClass = "left-1/2 -translate-x-1/2";
  if (align === "left") {
    alignmentClass = "left-0";
  } else if (align === "right") {
    alignmentClass = "right-0";
  }

  // Determine placement classes
  const placementClass =
    placement === "top" ? "bottom-full mb-2" : "top-full mt-2";

  return (
    <div
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{
              opacity: 0,
              scale: 0.95,
              y: placement === "top" ? 4 : -4,
            }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: placement === "top" ? 4 : -4 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className={`absolute z-[9999] ${placementClass} ${alignmentClass} pointer-events-none`}
            style={{ width: "max-content", maxWidth }}
          >
            <div className="bg-[#1B2430] dark:bg-slate-900 border border-slate-700/55 text-[#F7F7F5] text-[10px] md:text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-xl leading-normal break-words font-sans text-center">
              {content}
            </div>
            {/* Optional subtle arrow */}
            <div
              className={`absolute left-1/2 -translate-x-1/2 border-4 border-transparent ${
                placement === "top"
                  ? "top-full border-t-[#1B2430] dark:border-t-slate-900"
                  : "bottom-full border-b-[#1B2430] dark:border-b-slate-900"
              }`}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
