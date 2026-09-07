import {
  ConversationRecord,
  CONVERSATION_SCHEMA_VERSION,
  MAX_CONVERSATIONS,
  normalizeStoredMessages,
} from "./conversationStore";

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
          `#### [Source ${index + 1}] ${escapeMarkdown(source.citation)}`,
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
export const CONVERSATION_BACKUP_VERSION = 1;
export const MAX_BACKUP_BYTES = 25 * 1024 * 1024;

export interface ConversationBackup {
  format: typeof CONVERSATION_BACKUP_FORMAT;
  version: typeof CONVERSATION_BACKUP_VERSION;
  exportedAt: string;
  conversations: ConversationRecord[];
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

function isImportedMessage(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const message = value as { id?: unknown; sender?: unknown; text?: unknown };
  return (
    typeof message.id === "string" &&
    (message.sender === "user" || message.sender === "assistant") &&
    typeof message.text === "string"
  );
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
        !candidate.bookmarkedMessageIds.every((id) => typeof id === "string")))
  ) {
    return null;
  }

  const messages = normalizeStoredMessages(candidate.messages);
  const now = Date.now();
  const createdAt = isFiniteTimestamp(candidate.createdAt) ? candidate.createdAt : now;
  const updatedAt = isFiniteTimestamp(candidate.updatedAt) ? candidate.updatedAt : createdAt;
  const title = candidate.title.trim().replace(/\s+/g, " ").slice(0, 80) || "Untitled conversation";
  const bookmarks = (candidate.bookmarkedMessageIds ?? []).filter((id) =>
    messages.some((message) => message.id === id && message.sender === "assistant"),
  );

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
  };
}

export function conversationsToJson(conversations: ConversationRecord[]): string {
  const backup: ConversationBackup = {
    format: CONVERSATION_BACKUP_FORMAT,
    version: CONVERSATION_BACKUP_VERSION,
    exportedAt: new Date().toISOString(),
    conversations: conversations.map(({ deletionPending: _deletionPending, ...record }) => record),
  };
  return `${JSON.stringify(backup, null, 2)}\n`;
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

export function parseConversationBackup(text: string): ConversationRecord[] {
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
    candidate.version !== CONVERSATION_BACKUP_VERSION ||
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
  return records as ConversationRecord[];
}
