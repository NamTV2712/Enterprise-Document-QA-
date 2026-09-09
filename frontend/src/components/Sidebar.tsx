/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useRef } from "react";
import {
  BarChart3,
  BookOpen,
  FileSpreadsheet,
  FlaskConical,
  Network,
  Search,
  Server,
  Sparkles,
  X,
  type LucideIcon,
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
import { WORKSPACE_NAV_SECTIONS, type WorkspaceIcon, type WorkspaceView } from "../lib/workspace";

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
  isClearingSession,
  activeView,
  onSelectView,
  hasMessages,
  conversations,
}: SidebarProps) {
  const { locale, t } = useLocale();
  const sidebarRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const focusedBeforeOpen = document.activeElement as HTMLElement | null;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    sidebarRef.current?.querySelector<HTMLElement>("button")?.focus();
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      focusedBeforeOpen?.focus();
    };
  }, [isOpen, onClose]);

  const selectView = (view: WorkspaceView) => {
    onSelectView(view);
    onClose();
  };
  const routeClass = (view: WorkspaceView) => `sidebar-primary-nav__item ${activeView === view ? "is-active" : ""}`;

  return (
    <>
      {isOpen && <button type="button" className="sidebar-overlay fixed inset-0 z-40 lg:hidden" aria-label={locale === "vi" ? "Đóng điều hướng" : "Close navigation"} onClick={onClose} />}
      <aside
        ref={sidebarRef}
        id="control-sidebar"
        aria-label={locale === "vi" ? "Điều hướng workspace" : "Workspace navigation"}
        className={`sidebar-shell fixed inset-y-0 left-0 z-45 flex flex-col lg:static lg:translate-x-0 ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="sidebar-header sidebar-header--compact shrink-0">
          <div className="flex min-w-0 items-center gap-2.5">
            <BrandMark size="md" />
            <div className="min-w-0">
              <h1 className="sidebar-brand-title truncate text-xs font-black uppercase">SEC RAG Engine</h1>
              <p className="sidebar-brand-subtitle truncate text-xs">SEC 10-K Research</p>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label={locale === "vi" ? "Đóng điều hướng" : "Close navigation"} className="min-h-10 min-w-10 rounded-lg text-[var(--text-muted)] hover:surface-muted-hover lg:hidden">
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
                    const Icon = SIDEBAR_ICONS[item.icon];
                    const isDisabled = item.requiresMessages && !hasMessages;
                    return (
                      <button
                        key={item.view}
                        type="button"
                        className={`${routeClass(item.view)} ${item.nested ? "sidebar-primary-nav__item--nested" : ""}`}
                        disabled={isDisabled}
                        aria-current={activeView === item.view ? "page" : undefined}
                        onClick={() => selectView(item.view)}
                      >
                        <Icon className="h-4 w-4" />
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
        <SidebarFooter healthData={healthData} isClearingSession={isClearingSession} onNewConversation={onNewConversation} />
      </aside>
    </>
  );
}

const SIDEBAR_ICONS: Record<WorkspaceIcon, LucideIcon> = {
  analytics: BarChart3,
  book: BookOpen,
  file: FileSpreadsheet,
  flask: FlaskConical,
  network: Network,
  search: Search,
  settings: Server,
  sparkles: Sparkles,
};
