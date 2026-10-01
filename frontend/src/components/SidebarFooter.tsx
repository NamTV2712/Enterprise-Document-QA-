/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Database, LockKeyhole } from "lucide-react";
import { ConversationStorageMode, WriterStatus } from "../lib/conversationStore";
import type { SaveIndicator } from "../hooks/useConversationLibrary";
import { useLocale } from "../lib/i18n";

interface SidebarFooterProps {
  storageMode: ConversationStorageMode;
  storageWarning: string | null;
  saveIndicator?: SaveIndicator;
  writerStatus?: WriterStatus;
  isCompact?: boolean;
}

export const SidebarFooter = React.memo<SidebarFooterProps>(
  ({ storageMode, storageWarning, saveIndicator = "idle", writerStatus, isCompact }) => {
    const { locale } = useLocale();
    const storageLabel = storageMode === "memory"
      ? locale === "vi" ? "Chỉ trong phiên" : "Session only"
      : locale === "vi" ? "Lưu trên trình duyệt" : "Browser storage";
    const storageDetail = storageWarning ?? (
      storageMode === "memory"
        ? locale === "vi" ? "Bộ nhớ trình duyệt chưa khả dụng; dữ liệu không bền vững." : "Browser storage is unavailable; data is not durable."
        : locale === "vi" ? "Thư viện hội thoại lưu cục bộ trong trình duyệt này." : "Conversation library is stored locally in this browser."
    );
    const saveLabel = saveIndicator === "saved"
      ? locale === "vi" ? "Đã lưu" : "Saved"
      : saveIndicator === "volatile"
        ? locale === "vi" ? "Chỉ trong phiên" : "Session only"
        : locale === "vi" ? "Chưa có thay đổi" : "No pending save";
    const writerLabel = writerStatus?.readOnly
      ? locale === "vi" ? "Tab chỉ đọc" : "Read-only tab"
      : null;

    if (isCompact) {
      return (
        <div className="sidebar-footer p-2 flex flex-col items-center gap-2" title={`${storageLabel}: ${storageDetail}`}>
          <Database className="h-4 w-4 text-slate-400" aria-hidden="true" />
          <span className="sr-only">{storageLabel}</span>
        </div>
      );
    }

    return (
      <div className="sidebar-footer px-3 py-3 border-t border-[var(--border-subtle)] flex flex-col gap-3 shrink-0">
        <div className="sidebar-storage-widget rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-2.5 text-left">
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-1.5 text-[11px] font-semibold text-[var(--text-primary)]">
              <Database className="h-3.5 w-3.5 shrink-0 text-[var(--accent-text)]" aria-hidden="true" />
              <span>{locale === "vi" ? "Lưu trữ" : "Storage"}</span>
            </div>
            <span className="text-[10px] text-[var(--text-subtle)]">{storageLabel}</span>
          </div>
          <p className="mt-1.5 text-[11px] leading-snug text-[var(--text-subtle)]">{storageDetail}</p>
          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-[var(--text-muted)]">
            <span>{saveLabel}</span>
            {writerLabel && (
              <span className="inline-flex items-center gap-1">
                <LockKeyhole className="h-3 w-3" aria-hidden="true" />
                {writerLabel}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  },
);

SidebarFooter.displayName = "SidebarFooter";
