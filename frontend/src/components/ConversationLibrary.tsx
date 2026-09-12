import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Bookmark,
  BookmarkCheck,
  Clock3,
  Download,
  Edit3,
  FileText,
  Layers2,
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
import { EvidenceCollectionsPanel, type CurrentSourceCheckResult } from "./EvidenceCollectionsPanel";
import { searchConversationRecords } from "../lib/conversationSearch";
import { formatCompanyLabel, SECTION_METADATA } from "../lib/displayMetadata";
import type { AnswerVariant, Message, RequestSnapshot } from "../types";
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
  /** Open an exact current corpus source after a fresh identity check. */
  onOpenCurrentSource?: (item: EvidenceItem) => Promise<CurrentSourceCheckResult>;
  /** Open one immutable saved answer variant, never the latest answer by position. */
  onOpenVariant?: (conversationId: string, messageId: string, variantId: string) => void | Promise<void>;
  /** Fill the research composer with existing context without submitting it. */
  onContinueResearch?: (conversation: ConversationRecord) => void | Promise<void>;
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

interface SavedAnswerVersionItem {
  conversation: ConversationRecord;
  message: Message;
  variant: AnswerVariant;
  index: number;
}

const MAX_RECENT_RESEARCH = 8;
const MAX_SAVED_ANSWER_VERSIONS = 100;

function normalizedText(value: string | undefined | null): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

function latestMessage(conversation: ConversationRecord, sender: Message["sender"]): Message | null {
  return [...conversation.messages].reverse().find((message) => message.sender === sender) ?? null;
}

function requestSnapshotFor(conversation: ConversationRecord, variant?: AnswerVariant, message?: Message): RequestSnapshot | null {
  return variant?.requestSnapshot ?? message?.requestSnapshot ?? latestMessage(conversation, "assistant")?.requestSnapshot ?? null;
}

function scopeLabelFor(
  conversation: ConversationRecord,
  locale: Locale,
  variant?: AnswerVariant,
  message?: Message,
): string | null {
  const snapshot = requestSnapshotFor(conversation, variant, message);
  if (!snapshot) return null;
  return [
    snapshot.ticker ? formatCompanyLabel(snapshot.ticker) : (locale === "vi" ? "Tất cả công ty" : "All companies"),
    snapshot.section ? SECTION_METADATA[snapshot.section]?.shortLabel ?? snapshot.section : (locale === "vi" ? "Tất cả mục" : "All sections"),
    `Top ${snapshot.topK}`,
  ].join(" · ");
}

function companyLabelFor(conversation: ConversationRecord, variant?: AnswerVariant, message?: Message): string | null {
  const snapshot = requestSnapshotFor(conversation, variant, message);
  const source = variant?.sources?.find((item) => item.ticker) ?? message?.sources?.find((item) => item.ticker) ?? latestMessage(conversation, "assistant")?.sources?.find((item) => item.ticker);
  const ticker = snapshot?.ticker ?? source?.ticker;
  return ticker ? formatCompanyLabel(ticker) : null;
}

function variantMatchesSearch(item: SavedAnswerVersionItem, query: string): boolean {
  if (!query) return true;
  const snapshot = requestSnapshotFor(item.conversation, item.variant, item.message);
  const haystack = [
    item.conversation.title,
    ...(item.conversation.tags ?? []),
    item.variant.text,
    snapshot?.ticker,
    snapshot?.section,
    ...item.variant.sources.map((source) => source.citation),
    ...item.variant.sources.map((source) => source.ticker),
  ].filter(Boolean).join(" ");
  return normalizeLocaleSearch(haystack).includes(query);
}

function storageLabel(mode: ConversationStorageMode, saveIndicator: SaveIndicator | undefined, storageWarning: string | null, locale: Locale): string {
  if (mode === "memory" || saveIndicator === "volatile") return locale === "vi" ? "Chỉ giữ trong tab này" : "Only kept in this tab";
  if (storageWarning) return locale === "vi" ? "Lưu trữ cần được xử lý" : "Storage needs attention";
  if (saveIndicator === "saved") return locale === "vi" ? "Đã lưu trên thiết bị này" : "Saved on this device";
  if (mode === "localstorage") return locale === "vi" ? "Bộ nhớ trình duyệt dự phòng" : "Browser storage fallback";
  return locale === "vi" ? "Đã lưu trên thiết bị này" : "Saved on this device";
}

function answerStateLabel(conversation: ConversationRecord, assistant: Message | null, locale: Locale): string | null {
  if (assistant?.isStreaming || assistant?.status === "streaming") return locale === "vi" ? "Đang tạo" : "In progress";
  if (assistant?.error || assistant?.status === "error") return locale === "vi" ? "Lỗi" : "Error";
  if (assistant?.status === "stopped") return locale === "vi" ? "Đã dừng" : "Stopped";
  if (assistant?.status === "completed") return locale === "vi" ? "Đã hoàn tất" : "Completed";
  const savedVersions = conversation.variants?.filter((variant) => variant.status !== "error" && Boolean(variant.text.trim())).length ?? 0;
  if (savedVersions > 0) return locale === "vi" ? `${savedVersions} phiên bản đã lưu` : `${savedVersions} saved version${savedVersions === 1 ? "" : "s"}`;
  return null;
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
  onOpenCurrentSource,
  onOpenVariant,
  onContinueResearch,
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

  // These are bounded derived views over the existing conversation records.
  // They deliberately do not write a second Library index or copy artifacts.
  const recentResearch = useMemo(
    () => filteredConversations
      .filter((conversation) => conversation.messages.length > 0)
      .sort((left, right) => right.updatedAt - left.updatedAt)
      .slice(0, MAX_RECENT_RESEARCH),
    [filteredConversations],
  );

  const savedAnswerVersions = useMemo(() => {
    const items: SavedAnswerVersionItem[] = [];
    for (const conversation of conversations) {
      for (const [index, variant] of (conversation.variants ?? []).entries()) {
        const message = conversation.messages.find((candidate) => candidate.id === variant.originMessageId);
        if (!message || variant.status === "error" || !variant.text.trim()) continue;
        const item = { conversation, message, variant, index };
        if (variantMatchesSearch(item, normalizedSearch)) items.push(item);
      }
    }
    return items
      .filter(({ conversation, variant }) => !bookmarkedOnly || conversation.bookmarkedMessageIds.includes(variant.originMessageId))
      .sort((left, right) => (right.variant.createdAt || right.variant.updatedAt) - (left.variant.createdAt || left.variant.updatedAt))
      .slice(0, MAX_SAVED_ANSWER_VERSIONS);
  }, [bookmarkedOnly, conversations, normalizedSearch]);

  const totalSavedAnswerVersions = useMemo(
    () => conversations.reduce((total, conversation) => total + (conversation.variants?.filter((variant) => variant.status !== "error" && Boolean(variant.text.trim())).length ?? 0), 0),
    [conversations],
  );

  const bookmarkedAnswers = useMemo(
    () => (bookmarkedOnly ? collectBookmarkedAnswers(conversations, normalizedSearch) : []),
    [bookmarkedOnly, conversations, normalizedSearch],
  );

  // Keep the bounded Recent Research view separate from the complete saved
  // conversation list below. Bookmarked-answer filtering has its own exact
  // message targets, so hiding the duplicate recent cards avoids ambiguous
  // focus/open actions while the filter is active.
  const visibleRecentResearch = bookmarkedOnly ? [] : recentResearch;

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
        <span>{storageLabel(storageMode, saveIndicator, storageWarning, locale)}</span>
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

      <section className="library-section" aria-labelledby="library-recent-heading">
        <div className="library-section__heading">
          <div>
            <p className="library-section__eyebrow"><Clock3 className="h-3.5 w-3.5" />{locale === "vi" ? "Tiếp tục" : "Continue"}</p>
            <h3 id="library-recent-heading">{locale === "vi" ? "Nghiên cứu gần đây" : "Recent Research"}</h3>
            <p>{locale === "vi" ? `Tối đa ${MAX_RECENT_RESEARCH} cuộc trò chuyện gần nhất, lấy từ hoạt động đã lưu.` : `Up to ${MAX_RECENT_RESEARCH} recent conversations from saved activity.`}</p>
          </div>
          <span className="library-section__count">{visibleRecentResearch.length}/{MAX_RECENT_RESEARCH}</span>
        </div>
        <div className="library-list" aria-live="polite">
          {visibleRecentResearch.length === 0 ? (
            <div className="library-empty">
              <MessageSquare className="h-7 w-7" aria-hidden="true" />
              <p>
                <strong>{conversations.every((conversation) => conversation.messages.length === 0) ? (locale === "vi" ? "Chưa có nghiên cứu gần đây." : "No recent research yet.") : (locale === "vi" ? "Không có nghiên cứu phù hợp." : "No recent research matches this filter.")}</strong>
                <span>{conversations.every((conversation) => conversation.messages.length === 0) ? (locale === "vi" ? "Gửi câu hỏi filing đầu tiên; cuộc trò chuyện sẽ xuất hiện ở đây để mở lại." : "Ask your first filing question; the conversation will appear here for reopening.") : (locale === "vi" ? "Thử xóa bộ lọc hoặc tìm kiếm khác." : "Try clearing the filter or searching for something else.")}</span>
              </p>
            </div>
          ) : visibleRecentResearch.map((conversation) => {
            const latestAssistant = latestMessage(conversation, "assistant");
            const latestUser = latestMessage(conversation, "user");
            const latestAnswerText = latestAssistant?.text ? normalizedText(latestAssistant.text).slice(0, 220) : normalizedText(latestUser?.text).slice(0, 220);
            // Avoid rendering an answer excerpt that repeats the exact title;
            // the full list below owns the single visible title instance.
            const latestAnswer = latestAnswerText && !normalizeLocaleSearch(latestAnswerText).includes(normalizeLocaleSearch(conversation.title)) ? latestAnswerText : "";
            const answerState = answerStateLabel(conversation, latestAssistant, locale);
            return (
              <article className={`library-recent-card ${conversation.id === activeConversationId ? "is-active" : ""}`} key={conversation.id}>
                <button
                  type="button"
                  className="library-item-main"
                  aria-label={`${locale === "vi" ? "Mở nghiên cứu gần đây" : "Open recent research"}: ${conversation.title}`}
                  onClick={() => onSelect(conversation)}
                >
                  <span className="library-recent-title" data-title={conversation.title} aria-hidden="true" />
                  {companyLabelFor(conversation, undefined, latestAssistant) && <span className="library-item-company">{companyLabelFor(conversation, undefined, latestAssistant)}</span>}
                  {scopeLabelFor(conversation, locale, undefined, latestAssistant) && <span className="library-item-scope">{scopeLabelFor(conversation, locale, undefined, latestAssistant)}</span>}
                  {latestAnswer && <span className="library-item-excerpt">{latestAnswer}</span>}
                  <span className="library-item-meta">{conversation.messages.length} {locale === "vi" ? "tin nhắn" : "messages"} · {relativeTime(conversation.updatedAt, locale)}{latestAssistant?.sources?.length ? ` · ${latestAssistant.sources.length} ${locale === "vi" ? "nguồn" : "sources"}` : ""}{answerState ? ` · ${answerState}` : ""}</span>
                </button>
                <div className="library-continuation-actions">
                  <button type="button" className="library-primary-action" onClick={() => onSelect(conversation)}>{locale === "vi" ? "Mở nghiên cứu" : "Open research"}</button>
                  {onContinueResearch && <button type="button" className="library-secondary-action" onClick={() => void onContinueResearch(conversation)}>{locale === "vi" ? "Tiếp tục (điền bản nháp)" : "Continue (fill draft)"}</button>}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="library-section" aria-labelledby="library-all-heading">
        <div className="library-section__heading">
          <div>
            <p className="library-section__eyebrow"><MessageSquare className="h-3.5 w-3.5" />{locale === "vi" ? "Lịch sử đã lưu" : "Saved history"}</p>
            <h3 id="library-all-heading">{locale === "vi" ? "Lịch sử cuộc trò chuyện" : "Conversation history"}</h3>
            <p>{locale === "vi" ? "Mở, tìm kiếm, đánh dấu, đổi tên hoặc xuất mọi cuộc trò chuyện đã lưu." : "Open, search, bookmark, rename, or export every saved conversation."}</p>
          </div>
          <span className="library-section__count">{filteredConversations.length}</span>
        </div>
        <div className="library-list" aria-live="polite">
          {filteredConversations.length === 0 ? (
            <div className="library-empty">
              <MessageSquare className="h-7 w-7" aria-hidden="true" />
              <p>
                <strong>{conversations.length === 0 ? (locale === "vi" ? "Chưa có cuộc trò chuyện đã lưu." : "No saved conversations yet.") : (locale === "vi" ? "Không có cuộc trò chuyện phù hợp." : "No saved conversations match this filter.")}</strong>
                <span>{conversations.length === 0 ? (locale === "vi" ? "Các câu hỏi filing đã lưu sẽ xuất hiện ở đây." : "Saved filing questions will appear here.") : (locale === "vi" ? "Thử xóa bộ lọc hoặc tìm kiếm khác." : "Try clearing the filter or searching for something else.")}</span>
              </p>
            </div>
          ) : filteredConversations.map((conversation) => {
            const latestAssistant = latestMessage(conversation, "assistant");
            const answerState = answerStateLabel(conversation, latestAssistant, locale);
            const latestAnswerId = latestAssistant?.id;
            return (
              <article className={`library-item ${conversation.id === activeConversationId ? "is-active" : ""}`} key={conversation.id}>
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
                    {companyLabelFor(conversation, undefined, latestAssistant) && <span className="library-item-company">{companyLabelFor(conversation, undefined, latestAssistant)}</span>}
                    {scopeLabelFor(conversation, locale, undefined, latestAssistant) && <span className="library-item-scope">{scopeLabelFor(conversation, locale, undefined, latestAssistant)}</span>}
                    <span className="library-item-meta">{conversation.messages.length} {locale === "vi" ? "tin nhắn" : "messages"} · {relativeTime(conversation.updatedAt, locale)}{latestAssistant?.sources?.length ? ` · ${latestAssistant.sources.length} ${locale === "vi" ? "nguồn" : "sources"}` : ""}{answerState ? ` · ${answerState}` : ""}</span>
                  </button>
                )}
                <div className="library-continuation-actions">
                  <button type="button" className="library-primary-action" onClick={() => onSelect(conversation)}>{locale === "vi" ? "Mở nghiên cứu" : "Open research"}</button>
                  {onContinueResearch && <button type="button" className="library-secondary-action" onClick={() => void onContinueResearch(conversation)}>{locale === "vi" ? "Tiếp tục (điền bản nháp)" : "Continue (fill draft)"}</button>}
                </div>
                {onUpdateMetadata && !conversation.deletionPending && (
                  <div className="library-metadata-editor">
                    <label>
                      <span>Tags</span>
                      <input
                        value={tagDrafts[conversation.id] ?? (conversation.tags ?? []).join(", ")}
                        onChange={(event) => setTagDrafts((current) => ({ ...current, [conversation.id]: event.target.value }))}
                        onBlur={(event) => commitTags(conversation, event.target.value)}
                        placeholder="tag1, tag2"
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
                {conversation.deletionPending && <p className="library-item-pending" role="status">{locale === "vi" ? "Đang chờ xóa — hãy thử lại; bạn vẫn có thể đọc và xuất cuộc trò chuyện." : "Deletion pending — retry to finish removing it. You can still read and export this conversation."}</p>}
                <div className="library-item-actions">
                  {!conversation.deletionPending && latestAnswerId && (
                    <button type="button" className={`icon-button ${conversation.bookmarkedMessageIds.includes(latestAnswerId) ? "is-bookmarked" : ""}`} onClick={() => onToggleBookmark(conversation.id, latestAnswerId)} aria-label={conversation.bookmarkedMessageIds.includes(latestAnswerId) ? "Remove answer bookmark" : "Bookmark latest answer"} title={conversation.bookmarkedMessageIds.includes(latestAnswerId) ? "Remove bookmark" : "Bookmark latest answer"}>
                      {conversation.bookmarkedMessageIds.includes(latestAnswerId) ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
                    </button>
                  )}
                  <button type="button" className="icon-button" onClick={() => onExport(conversation)} aria-label="Export conversation" title="Export Markdown"><Download className="h-4 w-4" /></button>
                  {conversation.deletionPending ? (
                    <button type="button" className="icon-button is-danger" onClick={() => onDelete(conversation.id)} aria-label="Retry deletion" title="Retry deletion"><Trash2 className="h-4 w-4" /></button>
                  ) : (
                    <>
                      <button type="button" className="icon-button" onClick={() => beginRename(conversation)} aria-label="Rename conversation" title="Rename"><Edit3 className="h-4 w-4" /></button>
                      {pendingDeleteId === conversation.id ? (
                        <span className="library-delete-confirm">
                          <button type="button" onClick={() => { onDelete(conversation.id); setPendingDeleteId(null); }}>Delete</button>
                          <button type="button" onClick={() => setPendingDeleteId(null)}>Cancel</button>
                        </span>
                      ) : <button type="button" className="icon-button is-danger" onClick={() => setPendingDeleteId(conversation.id)} aria-label="Delete conversation" title="Delete"><Trash2 className="h-4 w-4" /></button>}
                    </>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="library-section" aria-labelledby="library-versions-heading">
        <div className="library-section__heading">
          <div>
            <p className="library-section__eyebrow"><Layers2 className="h-3.5 w-3.5" />{locale === "vi" ? "Ảnh chụp câu trả lời" : "Answer snapshots"}</p>
            <h3 id="library-versions-heading">{locale === "vi" ? "Phiên bản câu trả lời đã lưu" : "Saved Answer Versions"}</h3>
            <p>{locale === "vi" ? "Mỗi phiên bản là bản bất biến; mở lại đúng văn bản và nguồn đã lưu." : "Each version is immutable; reopen the exact saved text and sources."}</p>
          </div>
          <span className="library-section__count">{savedAnswerVersions.length}/{Math.min(totalSavedAnswerVersions, MAX_SAVED_ANSWER_VERSIONS)}</span>
        </div>
        <div className="library-list" aria-live="polite">
          {savedAnswerVersions.length === 0 ? (
            <div className="library-empty">
              <Layers2 className="h-7 w-7" aria-hidden="true" />
              <p>
                <strong>{totalSavedAnswerVersions === 0 ? (locale === "vi" ? "Chưa có phiên bản câu trả lời." : "No saved answer versions yet.") : (locale === "vi" ? "Không có phiên bản phù hợp." : "No saved answer versions match this filter.")}</strong>
                <span>{totalSavedAnswerVersions === 0 ? (locale === "vi" ? "Dùng “Lưu phiên bản” trên một câu trả lời grounded để giữ lại đúng bản cần kiểm chứng." : "Use “Save answer version” on a grounded answer to preserve the exact version you want to verify.") : (locale === "vi" ? "Thử xóa bộ lọc hoặc tìm kiếm khác." : "Try clearing the filter or searching for something else.")}</span>
              </p>
            </div>
          ) : savedAnswerVersions.map(({ conversation, message, variant, index }) => (
            <article className="library-item library-version-item" key={`${conversation.id}-${variant.id}`}>
              <div className="library-version-item__identity">
                <span className="library-item-title">{conversation.title}</span>
                {companyLabelFor(conversation, variant, message) && <span className="library-item-company">{companyLabelFor(conversation, variant, message)}</span>}
                {scopeLabelFor(conversation, locale, variant, message) && <span className="library-item-scope">{scopeLabelFor(conversation, locale, variant, message)}</span>}
              </div>
              <p className="library-item-excerpt">{normalizedText(variant.text).slice(0, 280)}</p>
              <div className="library-version-item__meta">
                <span><Clock3 className="h-3.5 w-3.5" aria-hidden="true" />{locale === "vi" ? "Đã lưu" : "Saved"} {relativeTime(variant.createdAt || variant.updatedAt, locale)}</span>
                <span><FileText className="h-3.5 w-3.5" aria-hidden="true" />{variant.sources.length} {locale === "vi" ? "nguồn" : "sources"}</span>
                <span>{locale === "vi" ? `Bản ${index + 1} · Snapshot bất biến` : `Variant ${index + 1} · Immutable snapshot`}</span>
              </div>
              <p className="library-local-disclosure">{locale === "vi" ? "Đã lưu trên thiết bị này · nguồn liên kết chỉ được mở khi định danh exact còn tồn tại." : "Saved on this device · linked sources open only when their exact identity still resolves."}</p>
              <div className="library-continuation-actions">
                <button type="button" className="library-primary-action" onClick={() => onOpenVariant ? void onOpenVariant(conversation.id, message.id, variant.id) : onOpenMessage?.(conversation.id, message.id)}>{locale === "vi" ? "Mở phiên bản đã lưu" : "Open saved answer"}</button>
                <button type="button" className="library-secondary-action" onClick={() => onSelect(conversation)}>{locale === "vi" ? "Mở ngữ cảnh" : "Open context"}</button>
              </div>
            </article>
          ))}
        </div>
        {bookmarkedOnly && bookmarkedAnswers.length > 0 && (
          <div className="library-subsection">
            <h4>{locale === "vi" ? "Câu trả lời đã đánh dấu" : "Bookmarked answers"}</h4>
            {bookmarkedAnswers.map(({ conversation, messageId, excerpt }) => (
              <article className="library-item library-bookmark-item" key={`${conversation.id}-${messageId}`}>
                <button type="button" className="library-item-main" onClick={() => onOpenMessage ? onOpenMessage(conversation.id, messageId) : onSelect(conversation)}>
                  <span className="library-item-title">{conversation.title}</span>
                  <span className="library-item-excerpt">{excerpt}</span>
                  <span className="library-item-meta">{relativeTime(conversation.updatedAt, locale)}</span>
                </button>
                <div className="library-item-actions"><button type="button" className="icon-button is-bookmarked" onClick={() => onToggleBookmark(conversation.id, messageId)} aria-label="Remove answer bookmark" title="Remove bookmark"><BookmarkCheck className="h-4 w-4" /></button><button type="button" className="icon-button" onClick={() => onExport(conversation)} aria-label="Export conversation" title="Export Markdown"><Download className="h-4 w-4" /></button></div>
              </article>
            ))}
          </div>
        )}
      </section>

      <EvidenceCollectionsPanel searchQuery={normalizedSearch} onOpenEvidence={onOpenEvidence} onOpenCurrentSource={onOpenCurrentSource} />
    </section>
  );
};
