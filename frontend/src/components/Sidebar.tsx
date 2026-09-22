/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useRef } from "react";
import { NavLink } from "react-router-dom";
import {
  PanelLeftClose,
  X,
} from "lucide-react";
import { BrandMark } from "./BrandMark";
import { SidebarFooter } from "./SidebarFooter";
import { HealthResponse } from "../types";
import {
  ConversationRecord,
  ConversationStorageMode,
  WriterStatus,
} from "../lib/conversationStore";
import { ConversationImportResult, SaveIndicator } from "../hooks/useConversationLibrary";
import type { ConversationBackupBundle } from "../lib/conversationExport";
import { SampleQuestion } from "./SampleQuestionChips";
import { useLocale } from "../lib/i18n";
import { getSemanticIcon } from "../lib/semanticIcons";
import { SHELL_NAVIGATION_SECTIONS, type ShellRouteId } from "../app/routes";
import type { NavigationLayout } from "../hooks/useNavigationLayout";
import { ModalDialog } from "./ui/ModalDialog";

interface SidebarProps {
  tickers: string[];
  sections: string[];
  selectedTicker: string | null;
  onSelectTicker: (ticker: string | null) => void;
  selectedSection: string | null;
  onSelectSection: (section: string | null) => void;
  topK: number;
  onChangeTopK: (k: number) => void;
  enableComparative: boolean;
  onToggleComparative: (val: boolean) => void;
  onNewConversation: () => void;
  onSelectSample: (question: SampleQuestion) => void;
  healthData: HealthResponse | null;
  isOpen: boolean;
  onClose: () => void;
  isDesktopNavigation: boolean;
  navigationLayout: NavigationLayout;
  onToggleNavigationLayout: () => void;
  isClearingSession: boolean;
  activePanel: "research" | "library";
  onChangePanel: (panel: "research" | "library") => void;
  activeRouteId: ShellRouteId | null;
  onSelectRoute: (routeId: ShellRouteId) => void;
  hasMessages: boolean;
  conversations: ConversationRecord[];
  activeConversationId: string;
  storageMode: ConversationStorageMode;
  storageWarning: string | null;
  saveIndicator?: SaveIndicator;
  onSelectConversation: (conversation: ConversationRecord) => void;
  onOpenMessage?: (conversationId: string, messageId: string) => void;
  onRenameConversation: (conversationId: string, title: string) => void;
  onToggleBookmark: (conversationId: string, messageId: string) => void;
  onDeleteConversation: (conversationId: string) => void;
  onExportConversation: (conversation: ConversationRecord) => void;
  onExportBackup?: () => void;
  onImportBackup?: (bundle: ConversationBackupBundle) => Promise<ConversationImportResult>;
  onUpdateMetadata?: (conversationId: string, patch: { tags?: ConversationRecord["tags"]; notes?: ConversationRecord["notes"] }) => Promise<unknown>;
  writerStatus?: WriterStatus;
  onRequestWriter?: () => Promise<WriterStatus>;
}

export function Sidebar({
  onNewConversation,
  healthData,
  isOpen,
  onClose,
  isDesktopNavigation,
  isClearingSession,
  navigationLayout,
  onToggleNavigationLayout,
  activeRouteId,
  onSelectRoute,
  storageMode,
  storageWarning,
  saveIndicator,
  writerStatus,
}: SidebarProps) {
  const { locale, t } = useLocale();
  const sidebarRef = useRef<HTMLElement>(null);
  const isDrawer = !isDesktopNavigation;

  useEffect(() => {
    if (!isOpen || !isDrawer) return;
    const frame = window.requestAnimationFrame(() => {
      sidebarRef.current?.querySelector<HTMLElement>("button:not(:disabled)")?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [isDrawer, isOpen]);

  const selectRoute = (routeId: ShellRouteId) => {
    onSelectRoute(routeId);
    onClose();
  };

  const sidebar = (
    <aside
      ref={sidebarRef}
      id="control-sidebar"
      aria-label={locale === "vi" ? "Điều hướng workspace" : "Workspace navigation"}
      className={`sidebar-shell flex flex-col ${navigationLayout === "compact" ? "sidebar-shell--compact" : ""} ${isDrawer ? "sidebar-shell--drawer" : "sidebar-shell--desktop"} ${isDrawer ? (isOpen ? "sidebar-shell--open translate-x-0" : "-translate-x-full") : ""}`}
      data-navigation-layout={navigationLayout}
      data-workbench-region="navigation"
    >
      {/* Brand Header */}
      <div className="sidebar-header sidebar-header--compact shrink-0 px-3 py-3 border-b border-[var(--border-subtle)] flex items-center justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <BrandMark size="md" />
          <div className="sidebar-brand-details min-w-0">
            <h1 className="sidebar-brand-title truncate text-[15px] font-bold text-[var(--text-primary)] leading-tight">RAG System</h1>
            <p className="sidebar-brand-subtitle truncate text-[9px] tracking-[-0.025em] text-slate-400 leading-tight">Enterprise Knowledge Assistant</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("nav.closeNavigation")}
          className="sidebar-drawer-close min-h-8 min-w-8 rounded-lg text-slate-400 hover:text-[var(--text-primary)] hover:bg-slate-800"
        >
          <X className="mx-auto h-4 w-4" />
        </button>
      </div>

      {/* Navigation Sections */}
      <nav className="sidebar-scroll min-h-0 flex-1 overflow-y-auto px-2.5 py-3 space-y-4" aria-label={locale === "vi" ? "Khu vực chính" : "Primary workspace areas"}>
        {SHELL_NAVIGATION_SECTIONS.map((section) => (
          <div key={section.id} className="sidebar-nav-group space-y-1">
            <div className="sidebar-nav-heading sidebar-nav-label px-2 text-[11px] font-medium text-slate-500">
              <span>{t(section.labelKey)}</span>
              {section.id === "workspace" && !isDrawer && (
                <button
                  type="button"
                  className="sidebar-collapse-toggle"
                  onClick={onToggleNavigationLayout}
                  aria-label={t("nav.compactNavigation")}
                  title={t("nav.compactNavigation")}
                >
                  <PanelLeftClose className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              )}
            </div>
            <div className="sidebar-nav-group__items space-y-0.5">
              {section.items.map((item) => {
                const active = activeRouteId === item.routeId;
                const IconComponent = getSemanticIcon(item.icon);
                return (
                  <NavLink
                    key={item.routeId}
                    to={item.path}
                    onClick={(event) => {
                      event.preventDefault();
                      selectRoute(item.routeId);
                    }}
                    aria-label={navigationLayout === "compact" ? t(item.labelKey) : undefined}
                    aria-current={active ? "page" : undefined}
                    data-route-id={item.routeId}
                    data-route-availability={item.availability}
                    data-feature={item.accentFamily}
                    className={`sidebar-primary-nav__item ${active ? "is-active" : ""}`}
                    title={navigationLayout === "compact" ? t(item.labelKey) : undefined}
                  >
                    <IconComponent className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{t(item.labelKey)}</span>
                    {item.availability !== "available" && (
                      <span className="sidebar-primary-nav__status" aria-label={item.availability === "deferred" ? "Unavailable" : "Existing tools"}>
                        {item.availability === "deferred" ? "—" : "•"}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom Storage Meter & Upgrade Card */}
      <SidebarFooter
        storageMode={storageMode}
        storageWarning={storageWarning}
        saveIndicator={saveIndicator}
        writerStatus={writerStatus}
        isCompact={navigationLayout === "compact"}
      />
    </aside>
  );

  if (!isDrawer) return sidebar;

  const closeDrawer = () => {
    onClose();
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        if (document.querySelector(".sidebar-drawer-dialog") || document.getElementById("root")?.hasAttribute("inert")) return;
        document.getElementById("sidebar-toggle")?.focus({ preventScroll: true });
      });
    });
  };

  return (
    <ModalDialog
      open={isOpen}
      onClose={closeDrawer}
      ariaLabel={t("nav.openNavigation")}
      overlayClassName="sidebar-drawer-overlay"
      className="sidebar-drawer-dialog"
    >
      {sidebar}
    </ModalDialog>
  );
}
