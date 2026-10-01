import { useCallback, useEffect, useState } from "react";

export type NavigationLayout = "expanded" | "compact";

export const NAVIGATION_LAYOUT_STORAGE_KEY = "sec_qa_navigation_layout_v1";

type NavigationLayoutUpdate = NavigationLayout | ((current: NavigationLayout) => NavigationLayout);

function isNavigationLayout(value: string | null): value is NavigationLayout {
  return value === "expanded" || value === "compact";
}

function defaultLayoutForViewport(): NavigationLayout {
  // Desktop screenshots and the inline-navigation contract both begin at the
  // same 1025px breakpoint. Keep the full information architecture visible
  // unless a person explicitly chooses the compact rail.
  return typeof window !== "undefined" && window.innerWidth >= 1025
    ? "expanded"
    : "compact";
}

function readStoredLayout(): NavigationLayout {
  const fallback = defaultLayoutForViewport();
  if (typeof window === "undefined") return fallback;
  try {
    const stored = window.localStorage.getItem(NAVIGATION_LAYOUT_STORAGE_KEY);
    return isNavigationLayout(stored) ? stored : fallback;
  } catch {
    return fallback;
  }
}

/**
 * Owns only the user's desktop navigation preference. Responsive breakpoints
 * may choose an effective layout in the shell, but never rewrite this value.
 */
export function useNavigationLayout() {
  const [layout, setLayoutState] = useState<NavigationLayout>(readStoredLayout);

  const setLayout = useCallback((update: NavigationLayoutUpdate) => {
    setLayoutState((current) => {
      const next = typeof update === "function" ? update(current) : update;
      if (typeof window !== "undefined") {
        try {
          window.localStorage.setItem(NAVIGATION_LAYOUT_STORAGE_KEY, next);
        } catch {
          // Keep the preference for this tab when storage is unavailable or full.
        }
      }
      return next;
    });
  }, []);

  const toggleLayout = useCallback(() => {
    setLayout((current) => (current === "expanded" ? "compact" : "expanded"));
  }, [setLayout]);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== NAVIGATION_LAYOUT_STORAGE_KEY || !isNavigationLayout(event.newValue)) return;
      setLayoutState(event.newValue);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return {
    layout,
    isCompact: layout === "compact",
    isExpanded: layout === "expanded",
    setLayout,
    toggleLayout,
  };
}
