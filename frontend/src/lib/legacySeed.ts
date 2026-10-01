import type { Message } from "../types";
import type { ConversationRecord } from "./conversationStore";

/**
 * Identifiers left by the former startup example. They are migration markers,
 * not display content. The migration is deliberately conservative: an exact
 * untouched record may be removed, while any edited record is preserved and
 * surfaced as a non-live legacy example.
 */
export const LEGACY_SEED_USER_MESSAGE_ID = "sample-msg-user-1";
export const LEGACY_SEED_ASSISTANT_MESSAGE_ID = "sample-msg-asst-1";

const LEGACY_SEED_USER_TEXT = "What are Apple's main risks mentioned in the 2024 10-K?";
const LEGACY_SEED_ASSISTANT_TEXT_SHA256 = "2a5c4c0ba4769a680b0d1a74270ae4c1e673fd1e1e30d6dbd2ecdcae38ac2bf9";
const LEGACY_SEED_SOURCE_DIGEST = "b93c24cde18fddbadf96a9b8a8a6fca38955a4f41cd6b5fa4233fc3782aaae3a";
const LEGACY_SEED_SOURCE_KEYS = [
  "citation",
  "chunk_id",
  "document_id",
  "filing_date",
  "score",
  "section",
  "text",
  "text_preview",
  "ticker",
] as const;
const LEGACY_SEED_MESSAGE_KEYS = ["id", "sender", "sources", "text", "model_used", "numChunks"] as const;
const LEGACY_SEED_USER_MESSAGE_KEYS = ["id", "sender", "text"] as const;
const SOURCE_DIGEST_FIELDS = [
  "citation",
  "document_id",
  "chunk_id",
  "ticker",
  "section",
  "score",
  "filing_date",
  "text_preview",
  "text",
] as const;

function hasExactKeys(value: object, expected: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  const normalizedExpected = [...expected].sort();
  return actual.length === normalizedExpected.length && normalizedExpected.every((key, index) => actual[index] === key);
}

function sourceDigestValue(value: unknown): string {
  return value === null || value === undefined ? "" : String(value);
}

function legacySourceCanonicalValue(sources: Message["sources"]): string {
  return (sources ?? [])
    .map((source) => SOURCE_DIGEST_FIELDS.map((field) => `${field}=${sourceDigestValue(source[field])}`).join("|"))
    .join("\n");
}

async function sha256Hex(value: string): Promise<string | null> {
  if (typeof globalThis.crypto?.subtle?.digest !== "function" || typeof TextEncoder === "undefined") return null;
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function hasLegacySeedMessageMarkers(messages: Message[]): boolean {
  return messages.some(
    (message) => message.id === LEGACY_SEED_USER_MESSAGE_ID || message.id === LEGACY_SEED_ASSISTANT_MESSAGE_ID,
  );
}

/** True when the record still contains an identifier from the former example. */
export function isLegacySeedRecord(record: ConversationRecord | null): boolean {
  return Boolean(record && hasLegacySeedMessageMarkers(record.messages));
}

/**
 * Match only the exact untouched startup example. A failed or unavailable
 * digest is a safe false-negative: the record remains visible and is never
 * deleted on an uncertain match.
 */
export async function isPristineLegacySeedRecord(record: ConversationRecord): Promise<boolean> {
  if (
    record.titleMode !== "auto" ||
    record.title !== LEGACY_SEED_USER_TEXT ||
    record.draft !== "" ||
    record.bookmarkedMessageIds.length !== 0 ||
    (record.tags?.length ?? 0) !== 0 ||
    (record.notes?.length ?? 0) !== 0 ||
    (record.variants?.length ?? 0) !== 0 ||
    record.deletionPending ||
    record.messages.length !== 2
  ) return false;

  const [userMessage, assistantMessage] = record.messages;
  if (
    !hasExactKeys(userMessage, LEGACY_SEED_USER_MESSAGE_KEYS) ||
    userMessage.id !== LEGACY_SEED_USER_MESSAGE_ID ||
    userMessage.sender !== "user" ||
    userMessage.text !== LEGACY_SEED_USER_TEXT ||
    !hasExactKeys(assistantMessage, LEGACY_SEED_MESSAGE_KEYS) ||
    assistantMessage.id !== LEGACY_SEED_ASSISTANT_MESSAGE_ID ||
    assistantMessage.sender !== "assistant" ||
    assistantMessage.model_used !== "GPT-4o" ||
    assistantMessage.numChunks !== 5 ||
    !Array.isArray(assistantMessage.sources) ||
    assistantMessage.sources.length !== 5 ||
    assistantMessage.sources.some((source) => !hasExactKeys(source, LEGACY_SEED_SOURCE_KEYS))
  ) return false;

  const [assistantTextHash, sourceDigest] = await Promise.all([
    sha256Hex(assistantMessage.text.replace(/\r\n/g, "\n")),
    sha256Hex(legacySourceCanonicalValue(assistantMessage.sources)),
  ]);
  return assistantTextHash === LEGACY_SEED_ASSISTANT_TEXT_SHA256 && sourceDigest === LEGACY_SEED_SOURCE_DIGEST;
}
