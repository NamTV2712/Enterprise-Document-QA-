/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect, useLayoutEffect } from "react";
import { createPortal } from "react-dom";
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
  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    arrowLeft: 0,
    placement,
  });
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

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

  useLayoutEffect(() => {
    if (!isVisible) return;

    const updatePosition = () => {
      const trigger = triggerRef.current?.getBoundingClientRect();
      const tooltip = tooltipRef.current?.getBoundingClientRect();
      if (!trigger || !tooltip) return;

      const viewportPadding = 8;
      const gap = 8;
      let left = trigger.left + trigger.width / 2 - tooltip.width / 2;
      if (align === "left") left = trigger.left;
      if (align === "right") left = trigger.right - tooltip.width;
      left = Math.min(
        Math.max(left, viewportPadding),
        window.innerWidth - tooltip.width - viewportPadding,
      );

      let resolvedPlacement = placement;
      if (placement === "top" && trigger.top - tooltip.height - gap < viewportPadding) {
        resolvedPlacement = "bottom";
      } else if (
        placement === "bottom" &&
        trigger.bottom + tooltip.height + gap > window.innerHeight - viewportPadding
      ) {
        resolvedPlacement = "top";
      }

      const top =
        resolvedPlacement === "top"
          ? trigger.top - tooltip.height - gap
          : trigger.bottom + gap;
      const arrowLeft = Math.min(
        Math.max(trigger.left + trigger.width / 2 - left, 10),
        tooltip.width - 10,
      );

      setPosition({ top, left, arrowLeft, placement: resolvedPlacement });
    };

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [align, isVisible, placement]);

  const tooltip = (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          ref={tooltipRef}
          role="tooltip"
          initial={{
            opacity: 0,
            scale: 0.95,
            y: position.placement === "top" ? 4 : -4,
          }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{
            opacity: 0,
            scale: 0.95,
            y: position.placement === "top" ? 4 : -4,
          }}
          transition={{ duration: 0.15, ease: "easeOut" }}
          className="fixed z-[9999] pointer-events-none"
          style={{
            top: position.top,
            left: position.left,
            width: "max-content",
            maxWidth: `min(${maxWidth}, calc(100vw - 16px))`,
          }}
        >
          <div className="bg-[#1B2430] dark:bg-slate-900 border border-slate-700/55 text-[#F7F7F5] text-[10px] md:text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-xl leading-normal break-words font-sans text-center">
            {content}
          </div>
          <div
            className={`absolute -translate-x-1/2 border-4 border-transparent ${
              position.placement === "top"
                ? "top-full border-t-[#1B2430] dark:border-t-slate-900"
                : "bottom-full border-b-[#1B2430] dark:border-b-slate-900"
            }`}
            style={{ left: position.arrowLeft }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <div
      ref={triggerRef}
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocusCapture={() => setIsVisible(true)}
      onBlurCapture={() => setIsVisible(false)}
    >
      {children}
      {typeof document !== "undefined" && createPortal(tooltip, document.body)}
    </div>
  );
};
