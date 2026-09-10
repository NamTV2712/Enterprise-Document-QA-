/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { RefreshCw } from "lucide-react";
import { HealthResponse } from "../types";
import { useLocale } from "../lib/i18n";
import { getSemanticIcon } from "../lib/semanticIcons";

interface SidebarFooterProps {
  healthData: HealthResponse | null;
  isClearingSession: boolean;
  onNewConversation: () => void;
  isCompact?: boolean;
}

export const SidebarFooter = React.memo<SidebarFooterProps>(
  ({ healthData, isClearingSession, onNewConversation, isCompact }) => (
    <SidebarFooterContent healthData={healthData} isClearingSession={isClearingSession} onNewConversation={onNewConversation} isCompact={isCompact} />
  ),
);

function SidebarFooterContent({ isClearingSession, onNewConversation, isCompact }: SidebarFooterProps) {
  const { t } = useLocale();
  const NewConversationIcon = getSemanticIcon("newConversation");
  const label = isClearingSession ? t("nav.resetting") : t("nav.newConversation");
  return (
    <div className="sidebar-footer">
      <button
        type="button"
        id="new-convo-btn"
        disabled={isClearingSession}
        onClick={onNewConversation}
        className="sidebar-new-conversation"
        aria-label={label}
        title={isCompact ? label : undefined}
      >
        {isClearingSession ? (
          <RefreshCw className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
        ) : (
          <NewConversationIcon className="w-3.5 h-3.5" aria-hidden="true" />
        )}
        <span>{label}</span>
      </button>
    </div>
  );
}

SidebarFooter.displayName = "SidebarFooter";
