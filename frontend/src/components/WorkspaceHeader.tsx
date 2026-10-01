/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef, useState } from "react";
import {
  CircleHelp,
  MoreHorizontal,
  Menu,
  Moon,
  Monitor,
  RefreshCw,
  Sun,
  Check,
  Search,
  X,
  ChevronDown,
  Settings,
} from "lucide-react";
import { ConnectionStatus } from "./ConnectionStatus";
import { BrandMark } from "./BrandMark";
import { SelectField } from "./ui/SelectField";
import { ThemePreference } from "../types";
import { useLocale } from "../lib/i18n";
import { type WorkspaceView } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";
import type { NavigationLayout } from "../hooks/useNavigationLayout";
import { ModalDialog } from "./ui/ModalDialog";

interface WorkspaceHeaderProps {
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  navigationLayout: NavigationLayout;
  onToggleNavigationLayout: () => void;
  activeView: WorkspaceView;
  onSelectView: (view: WorkspaceView) => void;
  hasMessages: boolean;
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  companyCount?: number;
  theme: ThemePreference;
  resolvedTheme: "light" | "dark";
  onSelectTheme: (theme: ThemePreference) => void;
  isClearingSession: boolean;
  onReset: () => void;
  onOpenHelp?: () => void;
  onOpenCommandPalette?: () => void;
  selectedTicker?: string | null;
  modelLabel?: string | null;
}

const THEME_OPTIONS: ThemePreference[] = ["system", "light", "dark"];

function ThemeOptionIcon({ option, className }: { option: ThemePreference; className: string }) {
  if (option === "system") return <Monitor className={className} />;
  if (option === "light") return <Sun className={className} />;
  return <Moon className={className} />;
}

export const WorkspaceHeader = React.memo<WorkspaceHeaderProps>(
  ({
    isSidebarOpen,
    onToggleSidebar,
    navigationLayout,
    onToggleNavigationLayout,
    activeView,
    onSelectView,
    hasMessages,
    isBackendConnected,
    isPipelineReady,
    companyCount,
    theme,
    resolvedTheme,
    onSelectTheme,
    isClearingSession,
    onReset,
    onOpenHelp,
    onOpenCommandPalette,
    selectedTicker,
    modelLabel,
  }) => {
    const { locale, setLocale, t } = useLocale();
    const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
    const [isMoreOpen, setIsMoreOpen] = useState(false);
    const themeMenuRef = useRef<HTMLDivElement>(null);
    const themeTriggerRef = useRef<HTMLButtonElement>(null);
    const themeMenuListRef = useRef<HTMLDivElement>(null);
    const moreDialogCloseRef = useRef<HTMLButtonElement>(null);
    const NavigationLayoutIcon = getSemanticIcon(navigationLayout === "expanded" ? "sidebarClose" : "sidebarOpen");

    useEffect(() => {
      if (!isThemeMenuOpen) return;
      const handlePointerDown = (event: PointerEvent) => {
        if (!themeMenuRef.current?.contains(event.target as Node)) {
          setIsThemeMenuOpen(false);
        }
      };
      document.addEventListener("pointerdown", handlePointerDown);
      return () => {
        document.removeEventListener("pointerdown", handlePointerDown);
      };
    }, [isThemeMenuOpen]);

    // Focus the selected item when the menu opens.
    useEffect(() => {
      if (!isThemeMenuOpen) return;
      const frame = window.requestAnimationFrame(() => {
        const selected = themeMenuListRef.current?.querySelector<HTMLElement>('[aria-checked="true"]');
        (selected ?? themeMenuListRef.current?.querySelector<HTMLElement>("button"))?.focus();
      });
      return () => window.cancelAnimationFrame(frame);
    }, [isThemeMenuOpen]);

    // WAI-ARIA menu pattern: Arrow keys move, Home/End jump, Enter/Space
    // activate, Escape closes and returns focus to the trigger button.
    const handleMenuKeyDown = (event: React.KeyboardEvent) => {
      const items = Array.from(
        themeMenuListRef.current?.querySelectorAll<HTMLElement>("button") ?? [],
      );
      const currentIndex = Math.max(0, items.indexOf(event.target as HTMLElement));
      if (event.key === "Escape") {
        event.stopPropagation();
        setIsThemeMenuOpen(false);
        themeTriggerRef.current?.focus();
        return;
      }
      if (event.key === "ArrowDown" || event.key === "ArrowRight") {
        event.preventDefault();
        items[(currentIndex + 1) % items.length]?.focus();
        return;
      }
      if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
        event.preventDefault();
        items[(currentIndex - 1 + items.length) % items.length]?.focus();
        return;
      }
      if (event.key === "Home") {
        event.preventDefault();
        items[0]?.focus();
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        items[items.length - 1]?.focus();
      }
    };

    const themeLabel =
      theme === "system" ? t("theme.system") : theme === "light" ? t("theme.light") : t("theme.dark");
    const moreControlsLabel = t("header.moreControls");
    const workspaceControlsLabel = t("header.workspaceControls");
    const closeWorkspaceControlsLabel = t("header.closeWorkspaceControls");
    const scopeLabel = selectedTicker
      ? t("header.sec10kScope").replace("{ticker}", selectedTicker)
      : t("header.noTicker");
    const visibleModelLabel = modelLabel?.trim() || t("header.modelUnavailable");
    const openHelpFromMore = () => {
      setIsMoreOpen(false);
      window.requestAnimationFrame(() => onOpenHelp?.());
    };

    return (
    <>
      <header
        className="workspace-header"
        data-workbench-region="header"
        aria-label={t("workbench.header")}
      >
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          id="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-controls="control-sidebar"
          aria-expanded={isSidebarOpen}
          aria-label={
            isSidebarOpen ? t("nav.closeNavigation") : t("nav.openNavigation")
          }
          className="sidebar-menu-trigger"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={onToggleNavigationLayout}
          className={`sidebar-layout-toggle${navigationLayout === "expanded" ? " sidebar-layout-toggle--header-expanded" : ""}`}
          aria-label={navigationLayout === "expanded" ? t("nav.compactNavigation") : t("nav.expandNavigation")}
          title={navigationLayout === "expanded" ? t("nav.compactNavigation") : t("nav.expandNavigation")}
          aria-pressed={navigationLayout === "compact"}
        >
          <NavigationLayoutIcon className="h-4 w-4" aria-hidden="true" />
        </button>
        <div className={`header-product-identity flex items-center gap-2.5 min-w-0${navigationLayout === "expanded" ? " header-product-identity--sidebar-owned" : ""}`}>
          <BrandMark size="sm" />
          <div className="flex flex-col min-w-0">
            <span className="font-bold text-sm text-[var(--text-primary)] truncate leading-tight tracking-tight">
              RAG System
            </span>
            <span className="text-[10px] text-slate-400 leading-none truncate">
              Enterprise Knowledge Assistant
            </span>
          </div>
        </div>
        <div className="header-scope-pill flex shrink-0 items-center gap-1.5 whitespace-nowrap px-3 py-1 rounded-lg border border-slate-800 bg-slate-900/90 text-xs text-[var(--text-primary)] font-medium">
          <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
          <span>{scopeLabel}</span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-500 ml-0.5" />
        </div>
      </div>

      {onOpenCommandPalette && (
        <button
          type="button"
          onClick={onOpenCommandPalette}
          className="header-command-button flex items-center justify-between gap-3 px-3.5 py-1.5 rounded-xl border border-slate-800 bg-slate-900/90 text-xs text-slate-400 hover:border-slate-700 transition-colors w-[260px] md:w-[380px] lg:w-[460px]"
          aria-label={t("header.openCommandPalette")}
          title={t("header.commandPaletteTitle")}
        >
          <div className="flex items-center gap-2 truncate">
            <Search className="h-3.5 w-3.5 shrink-0 text-slate-500" aria-hidden="true" />
            <span className="truncate text-slate-400">
              {t("header.commandPaletteTitle").replace(" (⌘ K)", "...")}
            </span>
          </div>
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400 shrink-0">⌘ K</kbd>
        </button>
      )}

      <div className="flex items-center gap-2 md:gap-3">
        <ConnectionStatus
          isBackendConnected={isBackendConnected}
          isPipelineReady={isPipelineReady}
          companyCount={companyCount}
        />

        <div className="header-model-label flex items-center gap-1.5 px-3 py-1 rounded-full border border-slate-800 bg-slate-900/80 text-xs font-medium text-[var(--text-muted)]">
          <span>{visibleModelLabel}</span>
        </div>

        {/* Theme Toggle Menu */}
        <div className="theme-menu header-theme-control relative" ref={themeMenuRef}>
          <button
            type="button"
            id="theme-switcher-btn"
            ref={themeTriggerRef}
            onClick={() => setIsThemeMenuOpen((open) => !open)}
            aria-expanded={isThemeMenuOpen}
            aria-haspopup="menu"
            className="theme-toggle theme-switcher-trigger p-1.5 rounded-lg text-slate-400 hover:text-[var(--text-primary)] hover:bg-slate-800 transition-colors"
            title={`${t("theme.system")} / ${themeLabel}`}
            aria-label={`Theme ${themeLabel}. ${t("theme.choose")}`}
          >
            <ThemeOptionIcon option={theme} className="w-4 h-4" />
          </button>
          {isThemeMenuOpen && (
            <div
              className="theme-menu__popover absolute right-0 mt-2 py-1 w-32 rounded-xl bg-slate-900 border border-slate-800 shadow-xl z-50 text-xs"
              role="menu"
              aria-label={t("theme.preference")}
              ref={themeMenuListRef}
              onKeyDown={handleMenuKeyDown}
            >
              {THEME_OPTIONS.map((option) => {
                const isSelected = theme === option;
                return (
                  <button
                    key={option}
                    type="button"
                    role="menuitemradio"
                    aria-checked={isSelected}
                    tabIndex={isSelected ? 0 : -1}
                    className={`flex items-center justify-between w-full px-3 py-1.5 text-xs transition-colors ${
                      isSelected ? "text-blue-400 font-medium bg-slate-800/60" : "text-[var(--text-muted)] hover:bg-slate-800"
                    }`}
                    onClick={() => {
                      onSelectTheme(option);
                      setIsThemeMenuOpen(false);
                      themeTriggerRef.current?.focus();
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <ThemeOptionIcon option={option} className="h-3.5 w-3.5" />
                      <span>
                        {option === "system" ? t("theme.system") : option === "light" ? t("theme.light") : t("theme.dark")}
                      </span>
                    </div>
                    {isSelected && <Check className="h-3.5 w-3.5" aria-hidden="true" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Settings Gear */}
        <button
          type="button"
          onClick={() => onSelectView("system")}
          className="header-settings-trigger p-1.5 rounded-lg text-slate-400 hover:text-[var(--text-primary)] hover:bg-slate-800 transition-colors"
          title={t("header.openSettings")}
          aria-label={t("header.openSettings")}
        >
          <Settings className="w-4 h-4" />
        </button>

        <div className="locale-switcher header-wide-control" role="group" aria-label={t("language.label")}>
          <button
            type="button"
            className={`locale-switcher__button ${locale === "en" ? "is-active" : ""}`}
            aria-pressed={locale === "en"}
            onClick={() => setLocale("en")}
          >
            EN
          </button>
          <button
            type="button"
            className={`locale-switcher__button ${locale === "vi" ? "is-active" : ""}`}
            aria-pressed={locale === "vi"}
            onClick={() => setLocale("vi")}
          >
            VI
          </button>
        </div>

        {onOpenHelp && (
          <button
            type="button"
            className="header-help-trigger"
            onClick={onOpenHelp}
            aria-haspopup="dialog"
            aria-label={t("nav.help")}
            title={t("nav.help")}
          >
            <CircleHelp className="h-4 w-4" aria-hidden="true" />
          </button>
        )}

        <div
          className="header-account-identity flex items-center gap-2 pl-2 border-l border-slate-800"
          aria-label={t("header.localWorkspace")}
        >
          <div className="w-7 h-7 rounded-lg border border-slate-700 bg-slate-800 flex items-center justify-center text-slate-400 shadow-sm shrink-0" aria-hidden="true">
            <Monitor className="h-3.5 w-3.5" />
          </div>
          <div className="hidden sm:flex flex-col text-left leading-none">
            <span className="text-xs font-semibold text-[var(--text-primary)]">{t("header.localWorkspace")}</span>
            <span className="text-[10px] text-slate-400 mt-0.5">{t("header.localSession")}</span>
          </div>
        </div>

        <button
          type="button"
          className="header-more-trigger"
          aria-haspopup="dialog"
          aria-expanded={isMoreOpen}
          aria-label={moreControlsLabel}
          title={moreControlsLabel}
          onClick={() => setIsMoreOpen(true)}
        >
          <MoreHorizontal className="h-5 w-5" aria-hidden="true" />
        </button>

      </div>
      </header>

      <ModalDialog
        open={isMoreOpen}
        onClose={() => setIsMoreOpen(false)}
        ariaLabel={workspaceControlsLabel}
        initialFocusRef={moreDialogCloseRef}
        className="header-more-dialog"
      >
        <div className="header-more-dialog__header">
          <div>
            <p className="header-more-dialog__eyebrow">{locale === "vi" ? "Workspace" : "Workspace"}</p>
            <h2>{workspaceControlsLabel}</h2>
          </div>
          <button
            ref={moreDialogCloseRef}
            type="button"
            className="header-more-dialog__close"
            aria-label={closeWorkspaceControlsLabel}
            onClick={() => setIsMoreOpen(false)}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="header-more-dialog__body">
          <fieldset className="header-more-dialog__group">
            <legend>{t("theme.preference")}</legend>
            <div className="header-more-dialog__theme-options">
              {THEME_OPTIONS.map((option) => {
                const isSelected = theme === option;
                const optionLabel = option === "system" ? t("theme.system") : option === "light" ? t("theme.light") : t("theme.dark");
                return (
                  <button
                    key={option}
                    type="button"
                    className={`header-more-control-option ${isSelected ? "is-selected" : ""}`}
                    aria-pressed={isSelected}
                    onClick={() => onSelectTheme(option)}
                  >
                    <ThemeOptionIcon option={option} className="h-4 w-4" />
                    <span>{optionLabel}</span>
                    {isSelected && <Check className="ml-auto h-4 w-4" aria-hidden="true" />}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div className="header-more-dialog__group" role="group" aria-label={t("language.label")}>
            <span className="header-more-dialog__label">{t("language.label")}</span>
            <div className="locale-switcher header-more-dialog__locale-switcher">
              <button type="button" className={`locale-switcher__button ${locale === "en" ? "is-active" : ""}`} aria-pressed={locale === "en"} onClick={() => setLocale("en")}>EN</button>
              <button type="button" className={`locale-switcher__button ${locale === "vi" ? "is-active" : ""}`} aria-pressed={locale === "vi"} onClick={() => setLocale("vi")}>VI</button>
            </div>
          </div>

          {onOpenHelp && (
            <button type="button" className="header-more-action" onClick={openHelpFromMore}>
              <CircleHelp className="h-4 w-4" aria-hidden="true" />
              <span>{t("nav.help")}</span>
            </button>
          )}

          <button
            type="button"
            className="header-more-action"
            disabled={isClearingSession || !hasMessages}
            aria-busy={isClearingSession}
            onClick={() => {
              setIsMoreOpen(false);
              onReset();
            }}
          >
            <RefreshCw className={`h-4 w-4 ${isClearingSession ? "animate-spin" : ""}`} aria-hidden="true" />
            <span>{isClearingSession ? t("nav.resetting") : t("nav.newConversation")}</span>
          </button>
        </div>
      </ModalDialog>
    </>
    );
  },
);

WorkspaceHeader.displayName = "WorkspaceHeader";
