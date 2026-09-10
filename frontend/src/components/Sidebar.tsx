/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
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
import { WORKSPACE_NAV_SECTIONS, type WorkspaceView } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";
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
  isClearingSession: boolean;
  activePanel: "research" | "library";
  onChangePanel: (panel: "research" | "library") => void;
  activeView: WorkspaceView;
  onSelectView: (view: WorkspaceView) => void;
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

/**
 * Navigation belongs in the sidebar. Scope, retrieval settings and saved
 * conversations have their own contextual surfaces so the sidebar has one
 * scroll region and one strong active route.
 */
export function Sidebar({
  onNewConversation,
  healthData,
  isOpen,
  onClose,
  isDesktopNavigation,
  isClearingSession,
  navigationLayout,
  activeView,
  onSelectView,
  hasMessages,
  conversations,
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

  const selectView = (view: WorkspaceView) => {
    onSelectView(view);
    onClose();
  };
  const routeClass = (view: WorkspaceView) => `sidebar-primary-nav__item ${activeView === view ? "is-active" : ""}`;

  const sidebar = (
      <aside
        ref={sidebarRef}
        id="control-sidebar"
        aria-label={locale === "vi" ? "Điều hướng workspace" : "Workspace navigation"}
        className={`sidebar-shell flex flex-col ${navigationLayout === "compact" ? "sidebar-shell--compact" : ""} ${isDrawer ? "sidebar-shell--drawer" : "sidebar-shell--desktop"} ${isDrawer ? (isOpen ? "sidebar-shell--open translate-x-0" : "-translate-x-full") : ""}`}
        data-navigation-layout={navigationLayout}
      >
        <div className="sidebar-header sidebar-header--compact shrink-0">
          <div className="flex min-w-0 items-center gap-2.5">
            <BrandMark size="md" />
            <div className="sidebar-brand-details min-w-0">
              <h1 className="sidebar-brand-title truncate text-xs font-black uppercase">SEC RAG Engine</h1>
              <p className="sidebar-brand-subtitle truncate text-xs">SEC 10-K Research</p>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label={t("nav.closeNavigation")} className="sidebar-drawer-close min-h-10 min-w-10 rounded-lg text-[var(--text-muted)] hover:surface-muted-hover">
            <X className="mx-auto h-4 w-4" />
          </button>
        </div>

        <div className="sidebar-scroll min-h-0 flex-1 overflow-y-auto">
          <nav className="sidebar-primary-nav" aria-label={locale === "vi" ? "Khu vực chính" : "Primary workspace areas"}>
            {WORKSPACE_NAV_SECTIONS.map((section) => (
              <section key={section.id} className="sidebar-nav-group" aria-labelledby={`sidebar-group-${section.id}`}>
                <p id={`sidebar-group-${section.id}`} className="sidebar-nav-label">{t(section.labelKey)}</p>
                <div className="sidebar-nav-group__items">
                  {section.items.map((item) => {
                    const Icon = getSemanticIcon(item.icon);
                    const isDisabled = item.requiresMessages && !hasMessages;
                    return (
                      <button
                        key={item.view}
                        type="button"
                        className={`${routeClass(item.view)} ${item.nested ? "sidebar-primary-nav__item--nested" : ""}`}
                        data-feature={item.accentFamily}
                        disabled={isDisabled}
                        aria-current={activeView === item.view ? "page" : undefined}
                        aria-label={navigationLayout === "compact" ? t(item.labelKey) : undefined}
                        title={navigationLayout === "compact" ? t(item.labelKey) : undefined}
                        onClick={() => selectView(item.view)}
                      >
                        <Icon className="h-4 w-4" aria-hidden="true" />
                        <span>{t(item.labelKey)}</span>
                        {item.view === "library" && conversations.length > 0 && <span className="sidebar-tab-count">{conversations.length}</span>}
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
          </nav>
        </div>
        <SidebarFooter healthData={healthData} isClearingSession={isClearingSession} onNewConversation={onNewConversation} isCompact={navigationLayout === "compact"} />
      </aside>
  );

  if (!isDrawer) return sidebar;
  return (
    <ModalDialog
      open={isOpen}
      onClose={onClose}
      ariaLabel={t("nav.openNavigation")}
      overlayClassName="sidebar-drawer-overlay"
      className="sidebar-drawer-dialog"
    >
      {sidebar}
    </ModalDialog>
  );
}
