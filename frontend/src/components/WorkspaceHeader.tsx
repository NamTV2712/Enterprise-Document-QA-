/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef, useState } from "react";
import {
  CircleHelp,
  Menu,
  Moon,
  Monitor,
  RefreshCw,
  Sun,
  Check,
  Search,
} from "lucide-react";
import { ConnectionStatus } from "./ConnectionStatus";
import { BrandMark } from "./BrandMark";
import { SelectField } from "./ui/SelectField";
import { ThemePreference } from "../types";
import { useLocale } from "../lib/i18n";
import { WORKSPACE_NAV_SECTIONS, type WorkspaceView } from "../lib/workspace";

interface WorkspaceHeaderProps {
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
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
    activeView,
    onSelectView,
    hasMessages,
    isBackendConnected,
    isPipelineReady,
    companyCount,
    theme,
    onSelectTheme,
    isClearingSession,
    onReset,
    onOpenHelp,
    onOpenCommandPalette,
  }) => {
    const { locale, setLocale, t } = useLocale();
    const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
    const themeMenuRef = useRef<HTMLDivElement>(null);
    const themeTriggerRef = useRef<HTMLButtonElement>(null);
    const themeMenuListRef = useRef<HTMLDivElement>(null);

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

    return (
    <header className="workspace-header">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          id="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-controls="control-sidebar"
          aria-expanded={isSidebarOpen}
          aria-label={
            isSidebarOpen ? t("nav.closeSearch") : t("nav.openSearch")
          }
          className="min-h-9 min-w-9 p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden text-slate-600 dark:text-slate-300 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="header-product-identity flex items-center gap-2.5 min-w-0">
          <BrandMark size="sm" />
          <div className="flex flex-col min-w-0">
            <span className="header-product-title-long font-bold text-sm md:text-base text-[var(--text-primary)] truncate leading-tight tracking-tight">
              Enterprise Document QA
            </span>
            <span className="header-product-title-short font-bold text-sm text-[var(--text-primary)] leading-tight tracking-tight">
              SEC Research
            </span>
            <span className="hidden sm:inline text-[10px] font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wider font-mono">
              SEC 10-K Intelligence
            </span>
          </div>
        </div>
        {hasMessages && activeView === "conversation" && (
          <button
            type="button"
            onClick={() => onSelectView("overview")}
            aria-label={t("nav.showOverview")}
            className="lg:hidden min-h-9 inline-flex items-center gap-1.5 px-2.5 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <span className="text-xs">{t("nav.overview")}</span>
          </button>
        )}
        <SelectField
          label={t("nav.workspaceViews")}
          value={activeView}
          onValueChange={(value) => onSelectView(value as WorkspaceView)}
          className="header-view-select lg:hidden"
          options={[
            ...WORKSPACE_NAV_SECTIONS.flatMap((section) => section.items.map((item) => ({
              value: item.view,
              label: t(item.labelKey),
              disabled: item.requiresMessages && !hasMessages,
            }))),
          ]}
        />
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        <ConnectionStatus
          isBackendConnected={isBackendConnected}
          isPipelineReady={isPipelineReady}
          companyCount={companyCount}
        />
        {onOpenCommandPalette && <button type="button" onClick={onOpenCommandPalette} className="hidden min-h-9 items-center gap-2 rounded-lg border border-[var(--border-subtle)] px-2.5 text-xs font-semibold text-[var(--text-muted)] hover:surface-muted-hover md:inline-flex" aria-label="Open command palette" title="Open command palette (Ctrl+Shift+P)"><Search className="h-3.5 w-3.5" /><span className="hidden xl:inline">{locale === "vi" ? "Lệnh" : "Command"}</span><kbd className="hidden rounded border border-[var(--border-subtle)] px-1 py-0.5 text-[10px] xl:inline">Ctrl+Shift+P</kbd></button>}
        <div className="theme-menu" ref={themeMenuRef}>
          <button
            type="button"
            id="theme-switcher-btn"
            ref={themeTriggerRef}
            onClick={() => setIsThemeMenuOpen((open) => !open)}
            aria-expanded={isThemeMenuOpen}
            aria-haspopup="menu"
            className="theme-toggle"
            title={`${t("theme.system")} / ${themeLabel}`}
            aria-label={`Theme ${themeLabel}. ${t("theme.choose")}`}
          >
            <span className="theme-toggle__icon" aria-hidden="true">
              <ThemeOptionIcon
                option={theme}
                className="w-4 h-4"
              />
            </span>
            <span className="theme-toggle__label">{themeLabel}</span>
          </button>
          {isThemeMenuOpen && (
            <div
              className="theme-menu__popover"
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
                    className="theme-menu__item"
                    onClick={() => {
                      onSelectTheme(option);
                      setIsThemeMenuOpen(false);
                      themeTriggerRef.current?.focus();
                    }}
                  >
                    <ThemeOptionIcon option={option} className="h-4 w-4" />
                    <span>
                      {option === "system" ? t("theme.system") : option === "light" ? t("theme.light") : t("theme.dark")}
                    </span>
                    {isSelected && <Check className="ml-auto h-4 w-4" aria-hidden="true" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <div className="locale-switcher" role="group" aria-label={t("language.label")}>
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
            onClick={onOpenHelp}
            aria-haspopup="dialog"
            aria-label={t("nav.help")}
            title={t("nav.help")}
            className="theme-toggle"
          >
            <CircleHelp className="w-4 h-4" aria-hidden="true" />
          </button>
        )}
        <button
          type="button"
          id="quick-reset-btn"
          disabled={isClearingSession || !hasMessages}
          aria-busy={isClearingSession}
          onClick={onReset}
          className="quick-reset-button"
          title="Start a new conversation"
          aria-label="Start a new conversation"
        >
          <RefreshCw
            className={`w-4 h-4 ${isClearingSession ? "animate-spin" : ""}`}
          />
        </button>
      </div>
    </header>
    );
  },
);

WorkspaceHeader.displayName = "WorkspaceHeader";
