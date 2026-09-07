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
  Plus,
} from "lucide-react";
import {
  ConversationRecord,
  ConversationStorageMode,
} from "../lib/conversationStore";
import { ConversationImportResult, SaveIndicator } from "../hooks/useConversationLibrary";
import { Locale, normalizeLocaleSearch, useLocale } from "../lib/i18n";
import { createEvidenceCollection, listEvidenceCollections, EvidenceCollection } from "../lib/evidenceCollections";

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
  onImportBackup?: (file: File) => Promise<ConversationImportResult>;
  /** Open a conversation and focus one bookmarked answer. */
  onOpenMessage?: (conversationId: string, messageId: string) => void;
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
  for (const conversation of conversations) {
    for (const messageId of conversation.bookmarkedMessageIds) {
      const message = conversation.messages.find(
        (item) => item.id === messageId && item.sender === "assistant" && item.text,
      );
      if (!message) continue;
      if (
        normalizedSearch &&
        !normalizeLocaleSearch(`${conversation.title} ${message.text}`).includes(normalizedSearch)
      ) {
        continue;
      }
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
  onOpenMessage,
  onClose,
}) => {
  const { locale, t } = useLocale();
  const [search, setSearch] = useState("");
  const [bookmarkedOnly, setBookmarkedOnly] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [backupStatus, setBackupStatus] = useState<string | null>(null);
  const [collections, setCollections] = useState<EvidenceCollection[]>(listEvidenceCollections);
  const [collectionName, setCollectionName] = useState("");
  const importInputRef = useRef<HTMLInputElement>(null);
  const normalizedSearch = normalizeLocaleSearch(search.trim());

  useEffect(() => {
    const refresh = () => setCollections(listEvidenceCollections());
    window.addEventListener("sec-qa-evidence-updated", refresh);
    return () => window.removeEventListener("sec-qa-evidence-updated", refresh);
  }, []);

  const handleCreateCollection = () => {
    if (!collectionName.trim()) return;
    try {
      createEvidenceCollection(collectionName);
      setCollectionName("");
      setCollections(listEvidenceCollections());
    } catch (error) {
      setBackupStatus(error instanceof Error ? error.message : "Could not create collection.");
    }
  };

  const handleImportBackup = async (file: File | undefined) => {
    if (!file || !onImportBackup) return;
    setBackupStatus(null);
    try {
      const result = await onImportBackup(file);
      setBackupStatus(
        locale === "vi"
          ? `Đã nhập ${result.imported}: lưu bền vững ${result.persisted}, chỉ trong tab ${result.volatile}, lỗi ${result.failed}.`
          : `Imported ${result.imported}: ${result.persisted} persisted, ${result.volatile} tab-only, ${result.failed} failed.`,
      );
    } catch (error) {
      setBackupStatus(error instanceof Error ? error.message : "Could not import this backup.");
    } finally {
      if (importInputRef.current) importInputRef.current.value = "";
    }
  };

  const filteredConversations = useMemo(
    () =>
      conversations.filter((conversation) => {
        const matchesSearch = normalizedSearch
          ? `${conversation.title} ${conversation.messages
              .map((message) => message.text)
              .join(" ")}`
              .normalize("NFD")
              .replace(/[\u0300-\u036f]/g, "")
              .replace(/đ/g, "d")
              .replace(/Đ/g, "D")
              .toLocaleLowerCase(locale)
              .includes(normalizedSearch)
          : true;
        const matchesBookmark = bookmarkedOnly
          ? conversation.bookmarkedMessageIds.length > 0
          : true;
        return matchesSearch && matchesBookmark;
      }),
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

      <label className="library-search">
        <Search className="h-4 w-4" aria-hidden="true" />
        <span className="sr-only">{t("library.search")}</span>
        <input
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
                onChange={(event) => void handleImportBackup(event.target.files?.[0])}
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
      {backupStatus && <p className="library-backup-status" role="status">{backupStatus}</p>}

      <div className="library-collections" aria-label={locale === "vi" ? "Bộ sưu tập evidence" : "Evidence collections"}>
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{locale === "vi" ? "Bộ sưu tập evidence" : "Evidence collections"}</span>
          <span className="text-[10px] text-[var(--text-subtle)]">{collections.reduce((total, collection) => total + collection.items.length, 0)} {locale === "vi" ? "mục" : "items"}</span>
        </div>
        <div className="mt-2 flex gap-2">
          <input value={collectionName} onChange={(event) => setCollectionName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") handleCreateCollection(); }} placeholder={locale === "vi" ? "Tên bộ sưu tập mới" : "New collection name"} aria-label={locale === "vi" ? "Tên bộ sưu tập mới" : "New collection name"} className="min-w-0 flex-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] px-2 py-1.5 text-xs text-[var(--text-primary)]" />
          <button type="button" onClick={handleCreateCollection} aria-label={locale === "vi" ? "Tạo bộ sưu tập" : "Create collection"} className="icon-button"><Plus className="h-4 w-4" /></button>
        </div>
        {collections.length > 0 && <div className="mt-2 flex flex-wrap gap-1.5">{collections.map((collection) => <span key={collection.id} className="rounded-full border border-[var(--border-subtle)] px-2 py-1 text-[10px] text-[var(--text-muted)]">{collection.name} · {collection.items.length}</span>)}</div>}
      </div>

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
