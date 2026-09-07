/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  CircleHelp,
  FileText,
  Server,
  FlaskConical,
  Menu,
  MessageSquare,
  BarChart3,
  Activity,
  Moon,
  Monitor,
  RefreshCw,
  Sun,
  Check,
  Search,
} from "lucide-react";
import { ConnectionStatus } from "./ConnectionStatus";
import { BrandMark } from "./BrandMark";
import { ThemePreference } from "../types";
import { useLocale } from "../lib/i18n";

export type WorkspaceView = "overview" | "conversation" | "retrieval" | "documents" | "evaluation" | "analytics" | "system";

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
      const currentIndex = THEME_OPTIONS.indexOf(theme);
      if (event.key === "Escape") {
        event.stopPropagation();
        setIsThemeMenuOpen(false);
        themeTriggerRef.current?.focus();
        return;
      }
      if (event.key === "ArrowDown" || event.key === "ArrowRight") {
        event.preventDefault();
        const next = themeMenuListRef.current?.querySelectorAll<HTMLElement>("button");
        next?.[(currentIndex + 1) % THEME_OPTIONS.length]?.focus();
        return;
      }
      if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
        event.preventDefault();
        const items = themeMenuListRef.current?.querySelectorAll<HTMLElement>("button");
        items?.[(currentIndex - 1 + THEME_OPTIONS.length) % THEME_OPTIONS.length]?.focus();
        return;
      }
      if (event.key === "Home") {
        event.preventDefault();
        themeMenuListRef.current?.querySelector<HTMLElement>("button")?.focus();
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        const items = themeMenuListRef.current?.querySelectorAll<HTMLElement>("button");
        items?.[items.length - 1]?.focus();
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
        <div className="flex items-center gap-2.5 min-w-0">
          <BrandMark size="sm" />
          <div className="flex flex-col min-w-0">
            <span className="font-bold text-sm md:text-base text-slate-900 dark:text-white truncate leading-tight tracking-tight">
              Enterprise Document QA
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
            <BookOpen className="w-4 h-4" />
            <span className="hidden sm:inline">{t("nav.overview")}</span>
          </button>
        )}
        <label className="lg:hidden">
          <span className="sr-only">{t("nav.workspaceViews")}</span>
          <select
            value={activeView}
            onChange={(event) => onSelectView(event.target.value as WorkspaceView)}
            aria-label={t("nav.workspaceViews")}
            className="control-select min-h-9 py-1 text-xs"
          >
            <option value="overview">{t("nav.overview")}</option>
            <option value="conversation" disabled={!hasMessages}>{t("nav.conversation")}</option>
            <option value="retrieval">{t("nav.retrieval")}</option>
            <option value="documents">{t("nav.documents")}</option>
            <option value="evaluation">{t("nav.evaluation")}</option>
            <option value="analytics">{t("nav.analytics")}</option>
            <option value="system">{t("nav.system")}</option>
          </select>
        </label>
        <nav
          className="hidden lg:flex items-center gap-1.5 ml-2 pl-3 border-l border-slate-200 dark:border-slate-800"
          aria-label={t("nav.overview")}
        >
          <button
            type="button"
            onClick={() => onSelectView("overview")}
            aria-pressed={activeView === "overview"}
            className={`workspace-nav-button ${
              activeView === "overview"
                ? "workspace-nav-button--active"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            {t("nav.overview")}
          </button>
          <button
            type="button"
            onClick={() => onSelectView("conversation")}
            disabled={!hasMessages}
            aria-pressed={activeView === "conversation"}
            className={`workspace-nav-button ${
              activeView === "conversation"
                ? "workspace-nav-button--active"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            {t("nav.conversation")}
          </button>
          <button
            type="button"
            onClick={() => onSelectView("retrieval")}
            aria-pressed={activeView === "retrieval"}
            className={`workspace-nav-button ${
              activeView === "retrieval"
                ? "workspace-nav-button--active"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <FlaskConical className="w-3.5 h-3.5" />
            {t("nav.retrieval")}
          </button>
          <button
            type="button"
            onClick={() => onSelectView("documents")}
            aria-pressed={activeView === "documents"}
            className={`workspace-nav-button ${
              activeView === "documents"
                ? "workspace-nav-button--active"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            {t("nav.documents")}
          </button>
          <button
            type="button"
            onClick={() => onSelectView("evaluation")}
            aria-pressed={activeView === "evaluation"}
            className={`workspace-nav-button ${
              activeView === "evaluation"
                ? "workspace-nav-button--active"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            {t("nav.evaluation")}
          </button>
          <button
            type="button"
            onClick={() => onSelectView("analytics")}
            aria-pressed={activeView === "analytics"}
            className={`workspace-nav-button ${
              activeView === "analytics"
                ? "workspace-nav-button--active"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            {t("nav.analytics")}
          </button>
          <button
            type="button"
            onClick={() => onSelectView("system")}
            aria-pressed={activeView === "system"}
            className={`workspace-nav-button ${
              activeView === "system"
                ? "workspace-nav-button--active"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <Server className="w-3.5 h-3.5" />
            {t("nav.system")}
          </button>
        </nav>
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
