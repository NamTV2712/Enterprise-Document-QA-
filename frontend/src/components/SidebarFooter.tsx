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

function SidebarFooterContent({ isClearingSession, onNewConversation }: SidebarFooterProps) {
  const { t } = useLocale();
  return (
    <div className="sidebar-footer">
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
