import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Bookmark,
  BookmarkCheck,
  Download,
  Edit3,
  MessageSquare,
  Search,
  Trash2,
  X,
} from "lucide-react";
import {
  ConversationRecord,
  ConversationStorageMode,
  WriterStatus,
} from "../lib/conversationStore";
import { ConversationImportResult, SaveIndicator } from "../hooks/useConversationLibrary";
import { Locale, normalizeLocaleSearch, useLocale } from "../lib/i18n";
import type { EvidenceItem } from "../lib/evidenceCollections";
import { EvidenceCollectionsPanel } from "./EvidenceCollectionsPanel";
import { searchConversationRecords } from "../lib/conversationSearch";
import {
  ConversationBackupBundle,
  MAX_BACKUP_BYTES,
  parseConversationBackupBundle,
} from "../lib/conversationExport";

interface ConversationLibraryProps {
  conversations: ConversationRecord[];
  activeConversationId: string;
  storageMode: ConversationStorageMode;
  storageWarning: string | null;
  saveIndicator?: SaveIndicator;
  onSelect: (conversation: ConversationRecord) => void;
  onRename: (conversationId: string, title: string) => void;
  onToggleBookmark: (conversationId: string, messageId: string) => void;
  onDelete: (conversationId: string) => void;
  onExport: (conversation: ConversationRecord) => void;
  onExportBackup?: () => void;
  onImportBackup?: (bundle: ConversationBackupBundle) => Promise<ConversationImportResult>;
  onUpdateMetadata?: (conversationId: string, patch: { tags?: string[]; notes?: ConversationRecord["notes"] }) => Promise<unknown>;
  writerStatus?: WriterStatus;
  onRequestWriter?: () => Promise<WriterStatus>;
  /** Open a conversation and focus one bookmarked answer. */
  onOpenMessage?: (conversationId: string, messageId: string) => void;
  /** Open a saved evidence snapshot without replacing it with live indexed text. */
  onOpenEvidence?: (item: EvidenceItem) => void;
  onClose: () => void;
}

interface BookmarkedAnswer {
  conversation: ConversationRecord;
  messageId: string;
  excerpt: string;
}

function relativeTime(timestamp: number, locale: Locale): string {
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 60) return locale === "vi" ? "Vừa xong" : "Just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return locale === "vi" ? `${minutes} phút trước` : `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return locale === "vi" ? `${hours} giờ trước` : `${hours}h ago`;
  const days = Math.round(hours / 24);
  return locale === "vi" ? `${days} ngày trước` : `${days}d ago`;
}

function storageLabel(mode: ConversationStorageMode, saveIndicator: SaveIndicator | undefined, locale: Locale): string {
  if (mode === "memory" || saveIndicator === "volatile") return locale === "vi" ? "Chỉ giữ trong tab này" : "Only kept in this tab";
  if (saveIndicator === "saved") return locale === "vi" ? "Đã lưu trên thiết bị này" : "Saved on this device";
  if (mode === "localstorage") return locale === "vi" ? "Bộ nhớ trình duyệt dự phòng" : "Browser storage fallback";
  return locale === "vi" ? "Đã lưu trên thiết bị này" : "Saved on this device";
}

function collectBookmarkedAnswers(
  conversations: ConversationRecord[],
  normalizedSearch: string,
): BookmarkedAnswer[] {
  const answers: BookmarkedAnswer[] = [];
  const matchingConversationIds = normalizedSearch
    ? new Set(searchConversationRecords(conversations, normalizedSearch).map((item) => item.id))
    : null;
  for (const conversation of conversations) {
    if (matchingConversationIds && !matchingConversationIds.has(conversation.id)) continue;
    for (const messageId of conversation.bookmarkedMessageIds) {
      const message = conversation.messages.find(
        (item) => item.id === messageId && item.sender === "assistant" && item.text,
      );
      if (!message) continue;
      answers.push({
        conversation,
        messageId,
        excerpt: message.text.trim().replace(/\s+/g, " ").slice(0, 160),
      });
    }
  }
  return answers;
}

export const ConversationLibrary: React.FC<ConversationLibraryProps> = ({
  conversations,
  activeConversationId,
  storageMode,
  storageWarning,
  saveIndicator,
  onSelect,
  onRename,
  onToggleBookmark,
  onDelete,
  onExport,
  onExportBackup,
  onImportBackup,
  onUpdateMetadata,
  writerStatus,
  onRequestWriter,
  onOpenMessage,
  onOpenEvidence,
  onClose,
}) => {
  const { locale, t } = useLocale();
  const [search, setSearch] = useState("");
  const [bookmarkedOnly, setBookmarkedOnly] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [backupStatus, setBackupStatus] = useState<string | null>(null);
  const [pendingBackup, setPendingBackup] = useState<{
    bundle: ConversationBackupBundle;
    fileName: string;
    byteLength: number;
  } | null>(null);
  const [tagDrafts, setTagDrafts] = useState<Record<string, string>>({});
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({});
  const importInputRef = useRef<HTMLInputElement>(null);
  const normalizedSearch = normalizeLocaleSearch(search.trim());

  const handlePreviewBackup = async (file: File | undefined) => {
    if (!file) return;
    setBackupStatus(null);
    try {
      if (file.size > MAX_BACKUP_BYTES) throw new Error("The backup is larger than the 25 MiB import limit.");
      const bundle = parseConversationBackupBundle(await file.text());
      setPendingBackup({ bundle, fileName: file.name, byteLength: file.size });
    } catch (error) {
      setBackupStatus(error instanceof Error ? error.message : "Could not import this backup.");
    } finally {
      if (importInputRef.current) importInputRef.current.value = "";
    }
  };

  const handleConfirmImport = async () => {
    if (!pendingBackup || !onImportBackup) return;
    setBackupStatus(null);
    try {
      const result = await onImportBackup(pendingBackup.bundle);
      const evidenceSummary = result.evidenceFailed
        ? locale === "vi"
          ? ` Bộ sưu tập evidence lỗi ${result.evidenceFailed}; cuộc trò chuyện vẫn đã được nhập. ${result.evidenceWarning ?? ""}`
          : ` ${result.evidenceFailed} evidence collections failed; conversations were imported. ${result.evidenceWarning ?? ""}`
        : result.evidencePersisted
          ? locale === "vi" ? `, evidence ${result.evidencePersisted} bộ sưu tập` : `, ${result.evidencePersisted} evidence collections`
          : "";
      setBackupStatus(
        locale === "vi"
          ? `Đã nhập ${result.imported}: lưu bền vững ${result.persisted}, chỉ trong tab ${result.volatile}, lỗi ${result.failed}.${evidenceSummary}`
          : `Imported ${result.imported}: ${result.persisted} persisted, ${result.volatile} tab-only, ${result.failed} failed.${evidenceSummary}`,
      );
      setPendingBackup(null);
    } catch (error) {
      setBackupStatus(error instanceof Error ? error.message : "Could not import this backup.");
    }
  };

  const filteredConversations = useMemo(
    () => searchConversationRecords(conversations, normalizedSearch).filter((conversation) =>
      bookmarkedOnly ? conversation.bookmarkedMessageIds.length > 0 : true,
    ),
    [bookmarkedOnly, conversations, normalizedSearch],
  );

  const bookmarkedAnswers = useMemo(
    () => (bookmarkedOnly ? collectBookmarkedAnswers(conversations, normalizedSearch) : []),
    [bookmarkedOnly, conversations, normalizedSearch],
  );

  const beginRename = (conversation: ConversationRecord) => {
    setEditingId(conversation.id);
    setEditingTitle(conversation.title);
  };

  const commitRename = (conversation: ConversationRecord) => {
    const title = editingTitle.trim().replace(/\s+/g, " ").slice(0, 80);
    if (title && title !== conversation.title) onRename(conversation.id, title);
    setEditingId(null);
  };

  const commitTags = (conversation: ConversationRecord, raw: string) => {
    if (!onUpdateMetadata) return;
    const tags = Array.from(new Set(raw.split(",").map((tag) => tag.trim().replace(/\s+/g, " ")).filter(Boolean))).slice(0, 10);
    void onUpdateMetadata(conversation.id, { tags });
  };

  const commitNote = (conversation: ConversationRecord, raw: string) => {
    if (!onUpdateMetadata) return;
    const text = raw.slice(0, 10_000);
    const now = Date.now();
    const existing = conversation.notes?.[0];
    const notes = text
      ? [{ id: existing?.id ?? `note-${now}`, text, createdAt: existing?.createdAt ?? now, updatedAt: now }]
      : [];
    void onUpdateMetadata(conversation.id, { notes });
  };

  return (
    <section className="conversation-library" aria-labelledby="library-heading">
      <div className="library-heading-row">
        <div>
          <p className="library-eyebrow">Your workspace</p>
          <h2 id="library-heading">{t("library.title")}</h2>
        </div>
        <button type="button" className="icon-button library-close" onClick={onClose} aria-label="Close conversation library">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="library-storage-status" role="status" aria-live="polite">
        <span className="library-status-dot" aria-hidden="true" />
        <span>{storageLabel(storageMode, saveIndicator, locale)}</span>
      </div>
      {storageMode === "memory" && (
        <p className="library-warning">
          {locale === "vi"
            ? "Chỉ giữ trong tab này: trình duyệt không cho phép lưu trữ nên cuộc trò chuyện sẽ mất khi đóng tab."
            : "Only kept in this tab: browser storage is unavailable, so conversations disappear when the tab closes."}
        </p>
      )}
      {storageWarning && <p className="library-warning">{storageWarning}</p>}
      {writerStatus?.readOnly && (
        <div className="library-warning" role="status">
          <strong>{locale === "vi" ? "Chế độ chỉ đọc" : "Read-only mode"}</strong>{" "}
          {writerStatus.reason === "unsupported"
            ? locale === "vi" ? "Trình duyệt không hỗ trợ Web Locks; bạn vẫn có thể đọc và xuất dữ liệu." : "This browser has no Web Locks; you can still read and export your data."
            : locale === "vi" ? "Một tab khác đang giữ quyền ghi Library." : "Another tab currently owns the Library writer lock."}
          {onRequestWriter && writerStatus.reason === "busy" && (
            <button type="button" className="ml-2 underline" onClick={() => void onRequestWriter()}>
              {locale === "vi" ? "Lấy lại quyền ghi" : "Request writer access"}
            </button>
          )}
        </div>
      )}

      <label className="library-search" data-composite-field>
        <Search className="h-4 w-4" aria-hidden="true" />
        <span className="sr-only">{t("library.search")}</span>
        <input data-composite-input
          id="library-search-input"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t("library.search")}
          aria-label={t("library.searchSaved")}
        />
      </label>

      <button
        type="button"
        className={`library-filter ${bookmarkedOnly ? "is-selected" : ""}`}
        aria-pressed={bookmarkedOnly}
        onClick={() => setBookmarkedOnly((current) => !current)}
      >
        <BookmarkCheck className="h-4 w-4" />
        {t("library.bookmarks")}
      </button>

      {(onExportBackup || onImportBackup) && (
        <div className="library-backup-actions">
          {onExportBackup && (
            <button type="button" className="library-secondary-action" onClick={onExportBackup}>
              <Download className="h-4 w-4" />
              {locale === "vi" ? "Xuất bản sao" : "Export backup"}
            </button>
          )}
          {onImportBackup && (
            <>
              <input
                ref={importInputRef}
                type="file"
                accept="application/json,.json"
                className="sr-only"
                onChange={(event) => void handlePreviewBackup(event.target.files?.[0])}
              />
              <button
                type="button"
                className="library-secondary-action"
                onClick={() => importInputRef.current?.click()}
              >
                <Download className="h-4 w-4 rotate-180" />
                {locale === "vi" ? "Nhập bản sao" : "Import backup"}
              </button>
            </>
          )}
        </div>
      )}
      {pendingBackup && (
        <div className="library-backup-preview" role="dialog" aria-labelledby="backup-preview-title" aria-modal="false">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 id="backup-preview-title" className="text-sm font-semibold text-[var(--text-primary)]">
                {locale === "vi" ? "Xem trước bản sao" : "Review backup before import"}
              </h3>
              <p className="mt-1 text-xs text-[var(--text-muted)]">{pendingBackup.fileName}</p>
            </div>
            <button type="button" className="icon-button" onClick={() => setPendingBackup(null)} aria-label={locale === "vi" ? "Hủy xem trước" : "Cancel backup import"}>
              <X className="h-4 w-4" />
            </button>
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--text-muted)]">
            <div><dt className="font-semibold">{locale === "vi" ? "Phiên bản" : "Version"}</dt><dd>{pendingBackup.bundle.version}</dd></div>
            <div><dt className="font-semibold">{locale === "vi" ? "Dung lượng" : "Size"}</dt><dd>{Math.ceil(pendingBackup.byteLength / 1024)} KiB</dd></div>
            <div><dt className="font-semibold">{locale === "vi" ? "Cuộc trò chuyện" : "Conversations"}</dt><dd>{pendingBackup.bundle.conversations.length}</dd></div>
            <div><dt className="font-semibold">{locale === "vi" ? "Bộ sưu tập" : "Collections"}</dt><dd>{pendingBackup.bundle.collections.length}</dd></div>
          </dl>
          <p className="mt-3 text-xs leading-relaxed text-[var(--text-muted)]">
            {locale === "vi"
              ? "Import sẽ tạo ID mới và không ghi đè cuộc trò chuyện hiện có."
              : "Import creates fresh IDs and does not overwrite existing conversations."}
          </p>
          <div className="mt-3 flex flex-wrap justify-end gap-2">
            <button type="button" className="library-secondary-action" onClick={() => setPendingBackup(null)}>
              {locale === "vi" ? "Hủy" : "Cancel"}
            </button>
            <button type="button" className="primary-action-button rounded-lg px-3 py-1.5 text-xs font-semibold" onClick={() => void handleConfirmImport()} disabled={!onImportBackup}>
              {locale === "vi" ? "Xác nhận nhập" : "Confirm import"}
            </button>
          </div>
        </div>
      )}
      {backupStatus && <p className="library-backup-status" role="status">{backupStatus}</p>}

      <EvidenceCollectionsPanel onOpenEvidence={onOpenEvidence} />

      <div className="library-list" aria-live="polite">
        {bookmarkedOnly ? (
          bookmarkedAnswers.length === 0 ? (
            <div className="library-empty">
              <Bookmark className="h-7 w-7" aria-hidden="true" />
              <p>
                {conversations.some((conversation) => conversation.bookmarkedMessageIds.length > 0)
                  ? t("library.noBookmarkMatch")
                  : t("library.bookmarkHint")}
              </p>
            </div>
          ) : (
            bookmarkedAnswers.map(({ conversation, messageId, excerpt }) => (
              <article className="library-item" key={`${conversation.id}-${messageId}`}>
                <button
                  type="button"
                  className="library-item-main"
                  onClick={() =>
                    onOpenMessage
                      ? onOpenMessage(conversation.id, messageId)
                      : onSelect(conversation)
                  }
                >
                  <span className="library-item-title">{conversation.title}</span>
                  <span className="library-item-excerpt">{excerpt}</span>
                  <span className="library-item-meta">
                    {relativeTime(conversation.updatedAt, locale)}
                  </span>
                </button>
                <div className="library-item-actions">
                  {!conversation.deletionPending && (
                    <button
                      type="button"
                      className="icon-button is-bookmarked"
                      onClick={() => onToggleBookmark(conversation.id, messageId)}
                      aria-label="Remove answer bookmark"
                      title="Remove bookmark"
                    >
                      <BookmarkCheck className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => onExport(conversation)}
                    aria-label="Export conversation"
                    title="Export Markdown"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                </div>
              </article>
            ))
          )
        ) : filteredConversations.length === 0 ? (
          <div className="library-empty">
            <MessageSquare className="h-7 w-7" aria-hidden="true" />
            <p>{conversations.length === 0 ? t("library.empty") : t("library.noMatch")}</p>
          </div>
        ) : (
          filteredConversations.map((conversation) => (
            <article
              className={`library-item ${conversation.id === activeConversationId ? "is-active" : ""}`}
              key={conversation.id}
            >
              {editingId === conversation.id ? (
                <div className="library-rename-row">
                  <input
                    value={editingTitle}
                    onChange={(event) => setEditingTitle(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") commitRename(conversation);
                      if (event.key === "Escape") setEditingId(null);
                    }}
                    aria-label="Conversation title"
                    autoFocus
                  />
                  <button type="button" onClick={() => commitRename(conversation)} aria-label="Save conversation title">Save</button>
                </div>
              ) : (
                <button type="button" className="library-item-main" onClick={() => onSelect(conversation)}>
                  <span className="library-item-title">{conversation.title}</span>
                  <span className="library-item-meta">
                    {conversation.messages.length} messages · {relativeTime(conversation.updatedAt, locale)}
                  </span>
                </button>
              )}

              {onUpdateMetadata && !conversation.deletionPending && (
                <div className="library-metadata-editor">
                  <label>
                    <span>{locale === "vi" ? "Tags" : "Tags"}</span>
                    <input
                      value={tagDrafts[conversation.id] ?? (conversation.tags ?? []).join(", ")}
                      onChange={(event) => setTagDrafts((current) => ({ ...current, [conversation.id]: event.target.value }))}
                      onBlur={(event) => commitTags(conversation, event.target.value)}
                      placeholder={locale === "vi" ? "tag1, tag2" : "tag1, tag2"}
                      aria-label={locale === "vi" ? `Tags cho ${conversation.title}` : `Tags for ${conversation.title}`}
                    />
                  </label>
                  <label>
                    <span>{locale === "vi" ? "Ghi chú cuộc trò chuyện" : "Conversation note"}</span>
                    <textarea
                      value={noteDrafts[conversation.id] ?? (conversation.notes?.[0]?.text ?? "")}
                      onChange={(event) => setNoteDrafts((current) => ({ ...current, [conversation.id]: event.target.value.slice(0, 10_000) }))}
                      onBlur={(event) => commitNote(conversation, event.target.value)}
                      maxLength={10_000}
                      rows={2}
                      aria-label={locale === "vi" ? `Ghi chú cho ${conversation.title}` : `Note for ${conversation.title}`}
                    />
                  </label>
                </div>
              )}

              {conversation.deletionPending && (
                <p className="library-item-pending" role="status">
                  Deletion pending — retry to finish removing it. You can still
                  read and export this conversation.
                </p>
              )}
              <div className="library-item-actions">
                {!conversation.deletionPending &&
                  conversation.messages
                    .filter((message) => message.sender === "assistant" && message.text)
                    .slice(-1)
                    .map((message) => (
                      <button
                        type="button"
                        key={message.id}
                        className={`icon-button ${conversation.bookmarkedMessageIds.includes(message.id) ? "is-bookmarked" : ""}`}
                        onClick={() => onToggleBookmark(conversation.id, message.id)}
                        aria-label={conversation.bookmarkedMessageIds.includes(message.id) ? "Remove answer bookmark" : "Bookmark latest answer"}
                        title={conversation.bookmarkedMessageIds.includes(message.id) ? "Remove bookmark" : "Bookmark latest answer"}
                      >
                        {conversation.bookmarkedMessageIds.includes(message.id) ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
                      </button>
                    ))}
                <button type="button" className="icon-button" onClick={() => onExport(conversation)} aria-label="Export conversation" title="Export Markdown">
                  <Download className="h-4 w-4" />
                </button>
                {conversation.deletionPending ? (
                  <button
                    type="button"
                    className="icon-button is-danger"
                    onClick={() => onDelete(conversation.id)}
                    aria-label="Retry deletion"
                    title="Retry deletion"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                ) : (
                  <>
                    <button type="button" className="icon-button" onClick={() => beginRename(conversation)} aria-label="Rename conversation" title="Rename">
                      <Edit3 className="h-4 w-4" />
                    </button>
                    {pendingDeleteId === conversation.id ? (
                      <span className="library-delete-confirm">
                        <button type="button" onClick={() => { onDelete(conversation.id); setPendingDeleteId(null); }}>Delete</button>
                        <button type="button" onClick={() => setPendingDeleteId(null)}>Cancel</button>
                      </span>
                    ) : (
                      <button type="button" className="icon-button is-danger" onClick={() => setPendingDeleteId(conversation.id)} aria-label="Delete conversation" title="Delete">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </>
                )}
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
};
