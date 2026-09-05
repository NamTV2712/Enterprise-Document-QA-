import React, { useMemo, useState } from "react";
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
} from "../lib/conversationStore";
import { SaveIndicator } from "../hooks/useConversationLibrary";

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
  /** Open a conversation and focus one bookmarked answer. */
  onOpenMessage?: (conversationId: string, messageId: string) => void;
  onClose: () => void;
}

interface BookmarkedAnswer {
  conversation: ConversationRecord;
  messageId: string;
  excerpt: string;
}

function relativeTime(timestamp: number): string {
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 60) return "Just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function storageLabel(mode: ConversationStorageMode, saveIndicator?: SaveIndicator): string {
  if (mode === "memory") return "Only kept in this tab";
  if (saveIndicator === "volatile") return "Only kept in this tab";
  if (saveIndicator === "saved") return "Saved on this device";
  if (mode === "localstorage") return "Browser storage fallback";
  return "Saved on this device";
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
        !`${conversation.title} ${message.text}`.toLowerCase().includes(normalizedSearch)
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
  onOpenMessage,
  onClose,
}) => {
  const [search, setSearch] = useState("");
  const [bookmarkedOnly, setBookmarkedOnly] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const normalizedSearch = search.trim().toLowerCase();

  const filteredConversations = useMemo(
    () =>
      conversations.filter((conversation) => {
        const matchesSearch = normalizedSearch
          ? `${conversation.title} ${conversation.messages
              .map((message) => message.text)
              .join(" ")}`
              .toLowerCase()
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
          <h2 id="library-heading">Saved conversations</h2>
        </div>
        <button type="button" className="icon-button library-close" onClick={onClose} aria-label="Close conversation library">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="library-storage-status" role="status" aria-live="polite">
        <span className="library-status-dot" aria-hidden="true" />
        <span>{storageLabel(storageMode, saveIndicator)}</span>
      </div>
      {storageMode === "memory" && (
        <p className="library-warning">
          Only kept in this tab: browser storage is unavailable, so conversations
          disappear when the tab closes.
        </p>
      )}
      {storageWarning && <p className="library-warning">{storageWarning}</p>}

      <label className="library-search">
        <Search className="h-4 w-4" aria-hidden="true" />
        <span className="sr-only">Search saved conversations</span>
        <input
          id="library-search-input"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search questions and answers"
          aria-label="Search saved conversations"
        />
      </label>

      <button
        type="button"
        className={`library-filter ${bookmarkedOnly ? "is-selected" : ""}`}
        aria-pressed={bookmarkedOnly}
        onClick={() => setBookmarkedOnly((current) => !current)}
      >
        <BookmarkCheck className="h-4 w-4" />
        Bookmarked answers
      </button>

      <div className="library-list" aria-live="polite">
        {bookmarkedOnly ? (
          bookmarkedAnswers.length === 0 ? (
            <div className="library-empty">
              <Bookmark className="h-7 w-7" aria-hidden="true" />
              <p>
                {conversations.some((conversation) => conversation.bookmarkedMessageIds.length > 0)
                  ? "No bookmarked answers match this search."
                  : "Bookmark an answer to find it quickly here."}
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
                    {relativeTime(conversation.updatedAt)}
                  </span>
                </button>
                <div className="library-item-actions">
                  <button
                    type="button"
                    className="icon-button is-bookmarked"
                    onClick={() => onToggleBookmark(conversation.id, messageId)}
                    aria-label="Remove answer bookmark"
                    title="Remove bookmark"
                  >
                    <BookmarkCheck className="h-4 w-4" />
                  </button>
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
            <p>{conversations.length === 0 ? "Your saved conversations will appear here." : "No conversations match this search."}</p>
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
                    {conversation.messages.length} messages · {relativeTime(conversation.updatedAt)}
                  </span>
                </button>
              )}

              <div className="library-item-actions">
                {conversation.messages
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
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
};
