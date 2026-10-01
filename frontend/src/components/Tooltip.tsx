/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect, useLayoutEffect, useId } from "react";
import { createPortal } from "react-dom";

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
  const [isFocused, setIsFocused] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const hoveringRef = useRef(false);
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const tooltipId = useId();

  const handleMouseEnter = () => {
    hoveringRef.current = true;
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
    hoveringRef.current = false;
    // Clear the timeout and hide immediately
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (!isFocused) setIsVisible(false);
  };

  const handleFocus = () => {
    setIsFocused(true);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(true);
  };

  const handleBlur = () => {
    setIsFocused(false);
    if (!hoveringRef.current) setIsVisible(false);
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

  const tooltip = isVisible ? (
        <div
          ref={tooltipRef}
          id={tooltipId}
          role="tooltip"
          className="ui-popover-enter fixed z-[9999] pointer-events-none"
          style={{
            top: position.top,
            left: position.left,
            width: "max-content",
            maxWidth: `min(${maxWidth}, calc(100vw - 16px))`,
          }}
        >
          <div className="bg-[var(--tooltip-surface)] border border-[var(--tooltip-border)] text-[var(--tooltip-foreground)] text-[10px] md:text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-xl leading-normal break-words font-sans text-center">
            {content}
          </div>
          <div
            className={`absolute -translate-x-1/2 border-4 border-transparent ${
              position.placement === "top" ? "top-full" : "bottom-full"
            }`}
            style={{
              left: position.arrowLeft,
              ...(position.placement === "top"
                ? { borderTopColor: "var(--tooltip-surface)" }
                : { borderBottomColor: "var(--tooltip-surface)" }),
            }}
          />
        </div>
      ) : null;

  return (
    <div
      ref={triggerRef}
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocusCapture={handleFocus}
      onBlurCapture={handleBlur}
      onKeyDownCapture={(event) => {
        if (event.key === "Escape") setIsVisible(false);
      }}
    >
      {React.isValidElement(children)
        ? React.cloneElement(
            children as React.ReactElement<{ "aria-describedby"?: string }>,
            {
              "aria-describedby": [
                (children.props as { "aria-describedby"?: string })["aria-describedby"],
                isVisible ? tooltipId : null,
              ]
                .filter(Boolean)
                .join(" ") || undefined,
            },
          )
        : children}
      {typeof document !== "undefined" && createPortal(tooltip, document.body)}
    </div>
  );
};
