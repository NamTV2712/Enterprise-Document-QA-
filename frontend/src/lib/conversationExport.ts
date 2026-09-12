import {
  ConversationRecord,
  CONVERSATION_SCHEMA_VERSION,
  MAX_CONVERSATIONS,
  MAX_NOTE_LENGTH,
  MAX_NOTES_PER_CONVERSATION,
  MAX_TAGS_PER_CONVERSATION,
  MAX_TAG_LENGTH,
  MAX_VARIANTS_PER_CONVERSATION,
  normalizeStoredMessages,
} from "./conversationStore";
import { EvidenceCollection, exportEvidenceCollections, importEvidenceCollections } from "./evidenceCollections";
import { AnswerVariant, ConversationNote, MessageFeedback, Source } from "../types";

function escapeMarkdown(value: string): string {
  return value.replace(/\r\n/g, "\n").trim();
}
export function conversationToMarkdown(conversation: ConversationRecord): string {
  const lines = [
    `# ${escapeMarkdown(conversation.title)}`,
    "",
    `Exported: ${new Date(conversation.updatedAt).toISOString()}`,
    "Stored locally on this device.",
    "",
  ];

  const messages = conversation.messages;
  let question = "";
  for (const message of messages) {
    if (message.sender === "user") {
      question = message.text;
      continue;
    }
    if (!message.text) continue;

    lines.push("## Question", "", escapeMarkdown(question || "Question unavailable"), "");
    lines.push("## Answer", "", escapeMarkdown(message.text), "");
    if (message.note) {
      lines.push("### Private note", "", escapeMarkdown(message.note), "");
    }
    if (message.status === "stopped" || message.status === "error") {
      lines.push(
        `> Status: ${message.status === "stopped" ? "partial answer; generation stopped" : "answer ended with an error"}.`,
        "",
      );
    }
    if (message.requestSnapshot) {
      const snapshot = message.requestSnapshot;
      lines.push(
        "### Request scope",
        "",
        `- Company: ${snapshot.ticker || "All companies"}`,
        `- Section: ${snapshot.section || "All sections"}`,
        `- Context breadth: ${snapshot.topK}`,
        "",
      );
    }
    if (message.sources?.length) {
      lines.push("### Retrieved filing evidence", "");
      message.sources.forEach((source, index) => {
        lines.push(
          `#### <a id="evidence-${message.id}-${index}"></a>[Source ${index + 1}] ${escapeMarkdown(source.citation)}`,
          "",
          `Rank score: ${source.score}`,
          "",
          escapeMarkdown(source.text || source.text_preview),
          "",
        );
      });
    }
  }

  return `${lines.join("\n").trim()}\n`;
}

export function downloadConversationMarkdown(conversation: ConversationRecord): void {
  const blob = new Blob([conversationToMarkdown(conversation)], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${conversation.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "conversation"}.md`;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export const CONVERSATION_BACKUP_FORMAT = "enterprise-document-qa.conversations";
export const CONVERSATION_BACKUP_VERSION = 2;
export const LEGACY_CONVERSATION_BACKUP_VERSION = 1;
export const MAX_BACKUP_BYTES = 25 * 1024 * 1024;

export interface ConversationBackup {
  format: typeof CONVERSATION_BACKUP_FORMAT;
  version: typeof CONVERSATION_BACKUP_VERSION | typeof LEGACY_CONVERSATION_BACKUP_VERSION;
  exportedAt: string;
  conversations: ConversationRecord[];
  collections?: EvidenceCollection[];
}

export interface ConversationBackupBundle {
  conversations: ConversationRecord[];
  collections: EvidenceCollection[];
  version: number;
}

function createImportId(prefix: string): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `${prefix}-${globalThis.crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function isFiniteTimestamp(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isImportedRequestSnapshot(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const snapshot = value as {
    ticker?: unknown;
    section?: unknown;
    topK?: unknown;
    enableComparative?: unknown;
    answerLanguage?: unknown;
  };
  return (
    (snapshot.ticker === null || typeof snapshot.ticker === "string") &&
    (snapshot.section === null || typeof snapshot.section === "string") &&
    typeof snapshot.topK === "number" && Number.isInteger(snapshot.topK) && snapshot.topK >= 1 &&
    typeof snapshot.enableComparative === "boolean" &&
    (snapshot.answerLanguage === "en" || snapshot.answerLanguage === "vi")
  );
}

function isImportedMessage(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const message = value as {
    id?: unknown;
    sender?: unknown;
    text?: unknown;
    status?: unknown;
    isStreaming?: unknown;
    sources?: unknown;
    requestSnapshot?: unknown;
    note?: unknown;
    feedback?: unknown;
  };
  const validSources =
    message.sources === undefined ||
    (Array.isArray(message.sources) &&
      message.sources.every((source) => {
        if (!source || typeof source !== "object") return false;
        const item = source as { citation?: unknown; score?: unknown; text_preview?: unknown };
        return (
          typeof item.citation === "string" &&
          typeof item.score === "number" &&
          Number.isFinite(item.score) &&
          typeof item.text_preview === "string"
        );
      }));
  const validSnapshot =
    message.requestSnapshot === undefined ||
    isImportedRequestSnapshot(message.requestSnapshot);
  const validFeedback =
    message.feedback === undefined ||
    (() => {
      if (!message.feedback || typeof message.feedback !== "object") return false;
      const feedback = message.feedback as Partial<MessageFeedback>;
      return (
        (feedback.rating === "up" || feedback.rating === "down") &&
        (feedback.category === undefined ||
          feedback.category === "inaccurate" ||
          feedback.category === "incomplete" ||
          feedback.category === "irrelevant" ||
          feedback.category === "citation_issue" ||
          feedback.category === "other") &&
        (feedback.variantId === undefined || feedback.variantId === null || typeof feedback.variantId === "string") &&
        (feedback.otherText === undefined || (typeof feedback.otherText === "string" && feedback.otherText.length <= 2_000)) &&
        (feedback.category !== "other" || Boolean(feedback.otherText?.trim())) &&
        (feedback.category === "other" || feedback.otherText === undefined) &&
        typeof feedback.at === "number" &&
        Number.isFinite(feedback.at)
      );
    })();
  return (
    typeof message.id === "string" &&
    message.id.length > 0 &&
    (message.sender === "user" || message.sender === "assistant") &&
    typeof message.text === "string" &&
    (message.status === undefined ||
      message.status === "streaming" ||
      message.status === "stopped" ||
      message.status === "completed" ||
      message.status === "error") &&
    (message.isStreaming === undefined || typeof message.isStreaming === "boolean") &&
    (message.note === undefined || typeof message.note === "string") &&
    validSources &&
    validSnapshot &&
    validFeedback
  );
}

function isImportedSource(value: unknown): value is Source {
  if (!value || typeof value !== "object") return false;
  const source = value as Partial<Source>;
  return typeof source.citation === "string" &&
    typeof source.text_preview === "string" &&
    (source.score === undefined || source.score === null || (typeof source.score === "number" && Number.isFinite(source.score)));
}

function isImportedNote(value: unknown): value is ConversationNote {
  if (!value || typeof value !== "object") return false;
  const note = value as Partial<ConversationNote>;
  return typeof note.id === "string" && typeof note.text === "string" &&
    note.text.length <= MAX_NOTE_LENGTH && isFiniteTimestamp(note.createdAt) &&
    isFiniteTimestamp(note.updatedAt);
}

function isImportedVariant(value: unknown): value is AnswerVariant {
  if (!value || typeof value !== "object") return false;
  const variant = value as Partial<AnswerVariant>;
  return typeof variant.id === "string" && typeof variant.originMessageId === "string" &&
    typeof variant.text === "string" && Array.isArray(variant.sources) &&
    variant.sources.every(isImportedSource) &&
    (variant.answerLanguage === "en" || variant.answerLanguage === "vi") &&
    (variant.status === "completed" || variant.status === "stopped" || variant.status === "error") &&
    (variant.requestSnapshot === undefined || isImportedRequestSnapshot(variant.requestSnapshot)) &&
    isFiniteTimestamp(variant.createdAt) && isFiniteTimestamp(variant.updatedAt);
}

function normalizeImportedRecord(value: unknown): ConversationRecord | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<ConversationRecord>;
  if (
    typeof candidate.title !== "string" ||
    typeof candidate.sessionId !== "string" ||
    !Array.isArray(candidate.messages) ||
    !candidate.messages.every(isImportedMessage) ||
    (candidate.draft !== undefined && typeof candidate.draft !== "string") ||
    (candidate.bookmarkedMessageIds !== undefined &&
      (!Array.isArray(candidate.bookmarkedMessageIds) ||
        !candidate.bookmarkedMessageIds.every((id) => typeof id === "string"))) ||
    (candidate.tags !== undefined &&
      (!Array.isArray(candidate.tags) || candidate.tags.length > MAX_TAGS_PER_CONVERSATION ||
        !candidate.tags.every((tag) => typeof tag === "string" && tag.trim().length <= MAX_TAG_LENGTH))) ||
    (candidate.notes !== undefined &&
      (!Array.isArray(candidate.notes) || candidate.notes.length > MAX_NOTES_PER_CONVERSATION ||
        !candidate.notes.every(isImportedNote))) ||
    (candidate.variants !== undefined &&
      (!Array.isArray(candidate.variants) || candidate.variants.length > MAX_VARIANTS_PER_CONVERSATION ||
        !candidate.variants.every(isImportedVariant)))
  ) {
    return null;
  }

  const sourceMessages = normalizeStoredMessages(candidate.messages);
  const sourceMessageIds = sourceMessages.map((message) => message.id);
  if (new Set(sourceMessageIds).size !== sourceMessageIds.length) return null;
  const messageIds = new Map<string, string>();
  const messages = sourceMessages.map((message) => {
    const nextId = createImportId("message-import");
    messageIds.set(message.id, nextId);
    return { ...message, id: nextId };
  });
  const now = Date.now();
  const createdAt = isFiniteTimestamp(candidate.createdAt) ? candidate.createdAt : now;
  const updatedAt = isFiniteTimestamp(candidate.updatedAt) ? candidate.updatedAt : createdAt;
  const title = candidate.title.trim().replace(/\s+/g, " ").slice(0, 80) || "Untitled conversation";
  const assistantSourceIds = new Set(sourceMessages.filter((message) => message.sender === "assistant").map((message) => message.id));
  if ((candidate.bookmarkedMessageIds ?? []).some((id) => !assistantSourceIds.has(id))) return null;
  const bookmarks = (candidate.bookmarkedMessageIds ?? []).map((id) => messageIds.get(id) as string);
  const variants: AnswerVariant[] = [];
  for (const variant of candidate.variants ?? []) {
    const originMessageId = messageIds.get(variant.originMessageId);
    if (!originMessageId || !assistantSourceIds.has(variant.originMessageId)) return null;
    variants.push({
      ...variant,
      id: createImportId("variant-import"),
      originMessageId,
      sources: variant.sources.map((source) => ({ ...source })),
    });
  }

  return {
    schemaVersion: CONVERSATION_SCHEMA_VERSION,
    id: createImportId("conversation-import"),
    sessionId: createImportId("session-import"),
    title,
    titleMode: candidate.titleMode === "custom" ? "custom" : "auto",
    revision: 1,
    createdAt,
    updatedAt,
    messages,
    draft: candidate.draft ?? "",
    bookmarkedMessageIds: bookmarks,
    tags: Array.from(new Set((candidate.tags ?? []).map((tag) => tag.trim().replace(/\s+/g, " ")))).slice(0, MAX_TAGS_PER_CONVERSATION),
    notes: (candidate.notes ?? []).map((note) => ({ ...note, id: createImportId("note-import") })),
    variants,
  };
}

export function conversationsToJson(
  conversations: ConversationRecord[],
  collections: EvidenceCollection[] = exportEvidenceCollections(),
): string {
  const backup: ConversationBackup = {
    format: CONVERSATION_BACKUP_FORMAT,
    version: CONVERSATION_BACKUP_VERSION,
    exportedAt: new Date().toISOString(),
    conversations: conversations.map(({ deletionPending: _deletionPending, ...record }) => record),
    collections,
  };
  const text = `${JSON.stringify(backup, null, 2)}\n`;
  if (new TextEncoder().encode(text).byteLength > MAX_BACKUP_BYTES) {
    throw new Error("The backup is larger than the 25 MiB export limit.");
  }
  return text;
}

export function downloadConversationBackup(conversations: ConversationRecord[]): void {
  const blob = new Blob([conversationsToJson(conversations)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `enterprise-document-qa-backup-${new Date().toISOString().slice(0, 10)}.json`;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function parseConversationBackupBundle(text: string): ConversationBackupBundle {
  if (new TextEncoder().encode(text).byteLength > MAX_BACKUP_BYTES) {
    throw new Error("The backup is larger than the 25 MiB import limit.");
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("The selected file is not valid JSON.");
  }
  if (!parsed || typeof parsed !== "object") {
    throw new Error("The backup must be a JSON object.");
  }
  const candidate = parsed as Partial<ConversationBackup>;
  if (
    candidate.format !== CONVERSATION_BACKUP_FORMAT ||
    (candidate.version !== CONVERSATION_BACKUP_VERSION && candidate.version !== LEGACY_CONVERSATION_BACKUP_VERSION) ||
    typeof candidate.exportedAt !== "string"
  ) {
    throw new Error("This backup format is not supported by the current app.");
  }
  if (!Array.isArray(candidate.conversations) || candidate.conversations.length > MAX_CONVERSATIONS) {
    throw new Error(`The backup must contain between 1 and ${MAX_CONVERSATIONS} conversations.`);
  }
  const records = candidate.conversations.map(normalizeImportedRecord);
  if (records.some((record) => record === null)) {
    throw new Error("The backup contains an invalid conversation or message.");
  }
  return {
    conversations: records as ConversationRecord[],
    collections: candidate.version === CONVERSATION_BACKUP_VERSION
      ? importEvidenceCollections(candidate.collections)
      : [],
    version: candidate.version,
  };
}

export function parseConversationBackup(text: string): ConversationRecord[] {
  return parseConversationBackupBundle(text).conversations;
}
