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
} from "lucide-react";
import { ConnectionStatus } from "./ConnectionStatus";
import { BrandMark } from "./BrandMark";
import { SelectField } from "./ui/SelectField";
import { ThemePreference } from "../types";
import { useLocale } from "../lib/i18n";
import { WORKSPACE_NAV_SECTIONS, type WorkspaceView } from "../lib/workspace";
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
    onSelectTheme,
    isClearingSession,
    onReset,
    onOpenHelp,
    onOpenCommandPalette,
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
    const moreControlsLabel = locale === "vi" ? "Mở điều khiển workspace" : "More workspace controls";
    const workspaceControlsLabel = locale === "vi" ? "Điều khiển workspace" : "Workspace controls";
    const closeWorkspaceControlsLabel = locale === "vi" ? "Đóng điều khiển workspace" : "Close workspace controls";
    const openHelpFromMore = () => {
      setIsMoreOpen(false);
      window.requestAnimationFrame(() => onOpenHelp?.());
    };

    return (
    <>
      <header className="workspace-header">
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
          className="sidebar-layout-toggle"
          aria-label={navigationLayout === "expanded" ? t("nav.compactNavigation") : t("nav.expandNavigation")}
          title={navigationLayout === "expanded" ? t("nav.compactNavigation") : t("nav.expandNavigation")}
          aria-pressed={navigationLayout === "compact"}
        >
          <NavigationLayoutIcon className="h-4 w-4" aria-hidden="true" />
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
            <span className="header-product-subtitle hidden sm:inline">
              SEC 10-K Intelligence
            </span>
          </div>
        </div>
        {hasMessages && activeView === "conversation" && (
          <button
            type="button"
            onClick={() => onSelectView("overview")}
            aria-label={t("nav.showOverview")}
            className="header-overview-button lg:hidden"
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
        {onOpenCommandPalette && <button type="button" onClick={onOpenCommandPalette} className="header-command-button" aria-label="Open command palette" title="Open command palette (Ctrl+Shift+P)"><Search className="h-3.5 w-3.5" aria-hidden="true" /><span className="header-command-button__label">{locale === "vi" ? "Lệnh" : "Command"}</span><kbd className="header-command-button__shortcut">Ctrl+Shift+P</kbd></button>}
        <div className="theme-menu header-wide-control" ref={themeMenuRef}>
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
            onClick={onOpenHelp}
            aria-haspopup="dialog"
            aria-label={t("nav.help")}
            title={t("nav.help")}
            className="theme-toggle header-wide-control"
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
          className="quick-reset-button header-wide-control"
          title="Start a new conversation"
          aria-label="Start a new conversation"
        >
          <RefreshCw
            className={`w-4 h-4 ${isClearingSession ? "animate-spin" : ""}`}
          />
        </button>
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
