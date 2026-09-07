import { ConversationRecord } from "./conversationStore";
import { normalizeLocaleSearch } from "./i18n";

/** Search the same public fields used by the Library UI, including tags. */
export function searchConversationRecords(
  conversations: ConversationRecord[],
  query: string,
): ConversationRecord[] {
  const normalized = normalizeLocaleSearch(query.trim());
  if (!normalized) return conversations;
  return conversations.filter((conversation) =>
    normalizeLocaleSearch(
      `${conversation.title} ${(conversation.tags ?? []).join(" ")} ${conversation.messages
        .map((message) => message.text)
        .join(" ")}`,
    ).includes(normalized),
  );
}
