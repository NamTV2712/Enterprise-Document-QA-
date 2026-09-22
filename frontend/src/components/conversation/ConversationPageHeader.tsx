import { memo } from "react";
import { History, MessageSquare, Plus, Telescope } from "lucide-react";

import { useLocale } from "../../lib/i18n";
import type { ConversationMode } from "../../types";

interface ConversationPageHeaderProps {
  mode: ConversationMode;
  onNewConversation: () => void;
  onOpenHistory: () => void;
}

/**
 * Mode-aware conversation header. Chat and Research share the same geometry
 * (identity tile, title, subtitle, actions) but present their own label and
 * new-conversation action, matching the two authoritative references. The
 * action strip only exposes controls that exist; a conversation's mode is
 * presentational and never changes what the answer contains.
 */
export const ConversationPageHeader = memo(function ConversationPageHeader({
  mode,
  onNewConversation,
  onOpenHistory,
}: ConversationPageHeaderProps) {
  const { t } = useLocale();
  const isChat = mode === "chat";
  const title = isChat ? t("conversation.chatTitle") : t("conversation.researchTitle");
  const subtitle = isChat ? t("conversation.chatSubtitle") : t("conversation.researchSubtitle");
  const newLabel = isChat ? t("conversation.newChat") : t("conversation.newResearch");
  const Icon = isChat ? MessageSquare : Telescope;

  return (
    <div
      className="shrink-0 flex items-center justify-between gap-3 px-5 py-3 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur"
      data-conversation-mode={mode}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="w-8 h-8 rounded-lg bg-[var(--accent-soft)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--accent-text)] shrink-0">
          <Icon className="w-4 h-4" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-[var(--text-primary)] tracking-tight leading-tight">{title}</h2>
          {/* The subtitle yields to the title on narrow widths so the mode
              label is never truncated into an unreadable fragment. */}
          <p className="hidden sm:block text-[11px] text-[var(--text-muted)] leading-none truncate">{subtitle}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={onNewConversation}
          className="min-h-8 px-2.5 py-1 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-medium text-[var(--text-primary)] flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" aria-hidden="true" />
          <span>{newLabel}</span>
        </button>
        <button
          type="button"
          onClick={onOpenHistory}
          className="min-h-8 px-2.5 py-1 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-medium text-[var(--text-primary)] flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <History className="w-3.5 h-3.5" aria-hidden="true" />
          <span>{t("conversation.history")}</span>
        </button>
      </div>
    </div>
  );
});
