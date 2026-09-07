/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { RefreshCw } from "lucide-react";
import { HealthResponse } from "../types";
import { useLocale } from "../lib/i18n";

interface SidebarFooterProps {
  healthData: HealthResponse | null;
  isClearingSession: boolean;
  onNewConversation: () => void;
}

export const SidebarFooter = React.memo<SidebarFooterProps>(
  ({ healthData, isClearingSession, onNewConversation }) => (
    <SidebarFooterContent healthData={healthData} isClearingSession={isClearingSession} onNewConversation={onNewConversation} />
  ),
);

function SidebarFooterContent({ healthData, isClearingSession, onNewConversation }: SidebarFooterProps) {
  const { t } = useLocale();
  return (
    <div className="sidebar-footer">
      <div className="space-y-2.5 text-xs relative z-10" role="status" aria-live="polite">
        <div className="flex items-center justify-between">
          <span className="text-slate-500 dark:text-slate-400 font-semibold text-xs">
            {t("sidebar.systemMetrics")}
          </span>
          <span className="sidebar-footer__pulse" aria-hidden="true" />
        </div>

        {healthData?.memory && (
          <div className="grid grid-cols-2 gap-2 text-xs border-t border-slate-200 dark:border-slate-800/80 pt-2.5">
            <div className="sidebar-metric-card">
              <div className="text-slate-500 dark:text-slate-450 font-sans font-bold">
                {t("sidebar.activeSessions")}
              </div>
              <div className="text-[#26324A] dark:text-[#FCFBF8] font-bold mt-1 text-xs font-mono">
                {healthData.memory.active_sessions}
              </div>
              <div className="mt-1 text-xs leading-tight text-slate-400 dark:text-slate-500 font-sans">
                {t("sidebar.inMemory")}
              </div>
            </div>
            <div className="sidebar-metric-card">
              <div className="text-slate-500 dark:text-slate-450 font-sans font-bold">
                {t("sidebar.totalTurns")}
              </div>
              <div className="text-[#26324A] dark:text-[#FCFBF8] font-bold mt-1 text-xs font-mono">
                {healthData.memory.total_turns}
              </div>
              <div className="mt-1 text-xs leading-tight text-slate-400 dark:text-slate-500 font-sans">
                {t("sidebar.retained")}
              </div>
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        id="new-convo-btn"
        disabled={isClearingSession}
        onClick={onNewConversation}
        className="sidebar-new-conversation"
      >
        <RefreshCw
          className={`w-3.5 h-3.5 ${isClearingSession ? "animate-spin" : ""}`}
        />
        <span>{isClearingSession ? t("nav.resetting") : t("nav.newConversation")}</span>
      </button>
    </div>
  );
}

SidebarFooter.displayName = "SidebarFooter";
