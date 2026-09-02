/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import {
  BookOpen,
  Menu,
  MessageSquare,
  Moon,
  RefreshCw,
  Sun,
} from "lucide-react";
import { ConnectionStatus } from "./ConnectionStatus";
import { BrandMark } from "./BrandMark";

interface WorkspaceHeaderProps {
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  activeView: "overview" | "conversation";
  onSelectView: (view: "overview" | "conversation") => void;
  hasMessages: boolean;
  isBackendConnected: boolean | null;
  isPipelineReady: boolean | null;
  companyCount?: number;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  isClearingSession: boolean;
  onReset: () => void;
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
    onToggleTheme,
    isClearingSession,
    onReset,
  }) => (
    <header className="workspace-header">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          id="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-controls="control-sidebar"
          aria-expanded={isSidebarOpen}
          aria-label={
            isSidebarOpen ? "Close search controls" : "Open search controls"
          }
          className="min-h-9 min-w-9 p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden text-slate-600 dark:text-slate-300 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2.5 min-w-0">
          <BrandMark size="sm" />
          <span className="font-semibold text-sm md:text-base text-slate-900 dark:text-white truncate">
            Enterprise Document QA
          </span>
        </div>
        {hasMessages && activeView === "conversation" && (
          <button
            type="button"
            onClick={() => onSelectView("overview")}
            aria-label="Show overview"
            className="lg:hidden min-h-9 inline-flex items-center gap-1.5 px-2 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <BookOpen className="w-4 h-4" />
            <span className="hidden sm:inline">Overview</span>
          </button>
        )}
        <nav
          className="hidden lg:flex items-center gap-1 ml-2 pl-3 border-l border-slate-200 dark:border-slate-700"
          aria-label="Workspace views"
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
            Overview
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
            Conversation
          </button>
        </nav>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        <ConnectionStatus
          isBackendConnected={isBackendConnected}
          isPipelineReady={isPipelineReady}
          companyCount={companyCount}
        />
        <button
          type="button"
          id="theme-switcher-btn"
          onClick={onToggleTheme}
          aria-pressed={theme === "dark"}
          className="theme-toggle"
          title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
          <span className="theme-toggle__icon" aria-hidden="true">
            {theme === "dark" ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </span>
        </button>
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
  ),
);

WorkspaceHeader.displayName = "WorkspaceHeader";
