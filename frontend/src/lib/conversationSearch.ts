import { ConversationRecord } from "./conversationStore";
import { normalizeLocaleSearch } from "./i18n";

type IndexedRecord = {
  fingerprint: string;
  normalizedText: string;
};

/**
 * Reuse normalized record text between keystrokes. Conversation writes bump
 * revision/updatedAt, so the fingerprint invalidates a changed record without
 * rescanning every message for every query.
 */
export class ConversationSearchIndex {
  private readonly records = new Map<string, IndexedRecord>();

  private fingerprint(conversation: ConversationRecord): string {
    return [
      conversation.revision,
      conversation.updatedAt,
      conversation.title,
      (conversation.tags ?? []).join("\u001f"),
      conversation.messages.map((message) => `${message.id}:${message.text.length}`).join("\u001e"),
    ].join("\u001d");
  }

  private textFor(conversation: ConversationRecord): string {
    const fingerprint = this.fingerprint(conversation);
    const cached = this.records.get(conversation.id);
    if (cached?.fingerprint === fingerprint) return cached.normalizedText;
    const normalizedText = normalizeLocaleSearch(
      `${conversation.title} ${(conversation.tags ?? []).join(" ")} ${conversation.messages
        .map((message) => message.text)
        .join(" ")}`,
    );
    this.records.set(conversation.id, { fingerprint, normalizedText });
    return normalizedText;
  }

  search(conversations: ConversationRecord[], query: string): ConversationRecord[] {
    const normalized = normalizeLocaleSearch(query.trim());
    if (!normalized) return conversations;
    const activeIds = new Set(conversations.map((conversation) => conversation.id));
    for (const id of this.records.keys()) {
      if (!activeIds.has(id)) this.records.delete(id);
    }
    return conversations.filter((conversation) => this.textFor(conversation).includes(normalized));
  }

  clear(): void {
    this.records.clear();
  }
}

const defaultSearchIndex = new ConversationSearchIndex();

/** Search the same public fields used by the Library UI, including tags. */
export function searchConversationRecords(
  conversations: ConversationRecord[],
  query: string,
  index: ConversationSearchIndex = defaultSearchIndex,
): ConversationRecord[] {
  return index.search(conversations, query);
}
