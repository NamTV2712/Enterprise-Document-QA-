import {
  AnswerVariant,
  ConversationNote,
  Message,
  MessageFeedback,
  RequestSnapshot,
  Source,
} from "../types";

/**
 * Local conversation library repository.
 *
 * Storage model:
 * - IndexedDB holds `conversations` (schema-v4 records) and `tombstones` in
 *   one transaction per write.
 * - localStorage holds one v4 envelope key (`records` + `tombstones`) so a
 *   mirror write is a single atomic setItem. The older v1/v2 keys are read
 *   as migration inputs and never rewritten in this cycle.
 * - A backend whose payload cannot be fully read (corrupt JSON, malformed
 *   records, or a record with a newer schema) is write-locked for the whole
 *   session: its bytes are preserved, its readable records still merge, and
 *   a sticky warning explains the state until the tab closes.
 * - Saves are admitted against the durable snapshot only (100 conversations,
 *   25 MiB of UTF-8 JSON). Records that do not fit stay in memory where they
 *   remain readable and exportable, and they are never written to storage by
 *   their own autosave or by another conversation's save.
 */

export const CONVERSATION_SCHEMA_VERSION = 4;
export const LIBRARY_ENVELOPE_VERSION = 4;
export const MAX_CONVERSATIONS = 100;
export const MAX_LIBRARY_BYTES = 25 * 1024 * 1024;
export const MAX_TAGS_PER_CONVERSATION = 10;
export const MAX_TAG_LENGTH = 32;
export const MAX_NOTES_PER_CONVERSATION = 50;
export const MAX_NOTE_LENGTH = 10_000;
export const MAX_VARIANTS_PER_CONVERSATION = 100;

const DATABASE_NAME = "enterprise-document-qa";
const DATABASE_VERSION = 2;
const STORE_NAME = "conversations";
const TOMBSTONE_STORE_NAME = "tombstones";
// The key is intentionally stable; `envelopeVersion` carries the migration.
const LOCAL_ENVELOPE_KEY = "sec_qa_library_v3";
// Legacy inputs: read for migration and merge, never rewritten here.
const LOCAL_STORAGE_V1_KEY = "sec_qa_conversations_v1";
const LOCAL_STORAGE_V2_KEY = "sec_qa_conversations_v2";
const LOCAL_TOMBSTONES_V2_KEY = "sec_qa_tombstones_v2";
const MIGRATION_KEY = "sec_qa_conversations_migrated_v1";
const LEGACY_MESSAGES_KEY = "sec_qa_messages";
const LEGACY_SESSION_KEY = "sec_qa_session_id";

export type ConversationStorageMode = "indexeddb" | "localstorage" | "memory";
export type ConversationPersistStatus = "persisted" | "volatile" | "failed";
export type TitleMode = "auto" | "custom";

export interface ConversationRecord {
  schemaVersion: number;
  id: string;
  sessionId: string;
  title: string;
  titleMode: TitleMode;
  revision: number;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
  draft: string;
  bookmarkedMessageIds: string[];
  /** User-controlled labels used by Library search and filtering. */
  tags?: string[];
  /** Plain-text research notes owned by this conversation. */
  notes?: ConversationNote[];
  /** Saved answer alternatives with independent evidence provenance. */
  variants?: AnswerVariant[];
  /**
   * Set by the repository for records that a durable tombstone suppresses
   * while a writable backend still holds a copy. Never persisted.
   */
  deletionPending?: boolean;
}

export interface TombstoneRecord {
  id: string;
  revision: number;
  deletedAt: number;
}

export interface ConversationWriteResult {
  status: ConversationPersistStatus;
  storageMode: ConversationStorageMode;
  warning: string | null;
}

export interface ConversationLibraryState {
  conversations: ConversationRecord[];
  storageMode: ConversationStorageMode;
  warning: string | null;
}

interface BackendLock {
  readable: boolean;
  writable: boolean;
  reason: string | null;
  /**
   * Permanent locks protect data integrity (corrupt payloads, newer
   * schemas) and never re-arm. Transient locks (write failures, quota)
   * re-arm before every queued operation so a recovered backend is used
   * again instead of being abandoned for the session.
   */
  permanent: boolean;
}

const IDB_UNAVAILABLE = "IndexedDB is unavailable";

const persistedRecords = new Map<string, ConversationRecord>();
const pendingRecords = new Map<string, ConversationRecord>();
const tombstones = new Map<string, TombstoneRecord>();
// Tombstones confirmed durable in at least one backend; only these mark a
// still-present record as deletion-pending.
const durableTombstoneIds = new Set<string>();
const knownIdbCopies = new Set<string>();
const knownLocalCopies = new Set<string>();
let snapshotLoaded = false;
let libraryWarning: string | null = null;
let transientWarning: string | null = null;
let activeStorageMode: ConversationStorageMode = "memory";
let idbLock: BackendLock = { readable: true, writable: true, reason: null, permanent: true };
let localLock: BackendLock = { readable: true, writable: true, reason: null, permanent: true };
let databasePromise: Promise<IDBDatabase | null> | null = null;
const WRITER_LOCK_NAME = "enterprise-document-qa-conversation-writer";
const LIBRARY_CHANNEL_NAME = "enterprise-document-qa-library";
let libraryChannel: BroadcastChannel | null = null;
const libraryListeners = new Set<() => void>();
const writerListeners = new Set<() => void>();
let writerOwned = false;
let writerSupported = false;
let writerAcquisitionStarted = false;
let writerRelease: (() => void) | null = null;
let writerRetryTimer: number | null = null;

function browserBroadcastChannel(): typeof BroadcastChannel | null {
  // Node exposes a worker BroadcastChannel globally, but its MessageEvent is
  // not compatible with jsdom's EventTarget. Only use the browser-owned
  // implementation when a window exists; this keeps storage tests hermetic.
  if (
    import.meta.env.MODE === "test" ||
    typeof window === "undefined" ||
    typeof window.BroadcastChannel !== "function"
  ) {
    return null;
  }
  return window.BroadcastChannel;
}

export interface WriterStatus {
  supported: boolean;
  owned: boolean;
  readOnly: boolean;
  reason: "unsupported" | "busy" | "unavailable" | null;
}

function isTestRuntime(): boolean {
  return import.meta.env.MODE === "test";
}

function currentWriterStatus(): WriterStatus {
  if (isTestRuntime()) {
    return { supported: true, owned: true, readOnly: false, reason: null };
  }
  if (!writerSupported) {
    return { supported: false, owned: false, readOnly: true, reason: "unsupported" };
  }
  return writerOwned
    ? { supported: true, owned: true, readOnly: false, reason: null }
    : {
        supported: true,
        owned: false,
        readOnly: true,
        reason: writerAcquisitionStarted ? "busy" : "unavailable",
      };
}

function notifyWriterChanged(): void {
  for (const listener of writerListeners) listener();
  const Channel = browserBroadcastChannel();
  if (Channel) {
    if (!libraryChannel) libraryChannel = new Channel(LIBRARY_CHANNEL_NAME);
    libraryChannel.postMessage({ type: "writer-changed", at: Date.now() });
  }
}

/** Subscribe to writer ownership changes so the UI can explain read-only tabs. */
export function subscribeConversationWriter(listener: () => void): () => void {
  writerListeners.add(listener);
  return () => writerListeners.delete(listener);
}

export function getWriterStatus(): WriterStatus {
  return currentWriterStatus();
}

// All durable writes are serialized so read-modify-write cycles on the
// localStorage envelope can never interleave.
let writeQueue: Promise<unknown> = Promise.resolve();

function enqueue<T>(operation: () => Promise<T>): Promise<T> {
  const run = writeQueue.then(operation, operation);
  writeQueue = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

async function acquireWriterOwnership(): Promise<boolean> {
  if (isTestRuntime()) {
    writerSupported = true;
    writerOwned = true;
    return true;
  }
  if (writerOwned) return true;
  if (typeof navigator === "undefined" || !navigator.locks) {
    writerSupported = false;
    writerAcquisitionStarted = true;
    notifyWriterChanged();
    return false;
  }
  writerSupported = true;
  writerAcquisitionStarted = true;
  let acquired = false;
  const result = new Promise<boolean>((resolve) => {
    void navigator.locks
      .request(
        WRITER_LOCK_NAME,
        { mode: "exclusive", ifAvailable: true },
        (lock) => {
          if (!lock) {
            resolve(false);
            return undefined;
          }
          acquired = true;
          writerOwned = true;
          notifyWriterChanged();
          resolve(true);
          return new Promise<void>((releaseLock) => {
            writerRelease = () => {
              writerRelease = null;
              writerOwned = false;
              notifyWriterChanged();
              releaseLock();
            };
          });
        },
      )
      .catch(() => {
        writerSupported = true;
        writerOwned = false;
        resolve(false);
      });
  });
  await result;
  if (!acquired) {
    writerOwned = false;
    if (writerRetryTimer === null && typeof window !== "undefined") {
      writerRetryTimer = window.setTimeout(() => {
        writerRetryTimer = null;
        void acquireWriterOwnership().then((owned) => {
          if (owned) notifyLibraryChanged();
        });
      }, 3_000);
    }
    notifyWriterChanged();
  }
  return acquired;
}

/** Ask the browser for the Library writer lock again after another tab closes. */
export async function requestWriterOwnership(): Promise<WriterStatus> {
  await acquireWriterOwnership();
  return currentWriterStatus();
}

async function withWriterLock<T>(operation: () => Promise<T>): Promise<T> {
  return operation();
}

function notifyLibraryChanged(): void {
  for (const listener of libraryListeners) listener();
  const Channel = browserBroadcastChannel();
  if (!Channel) return;
  if (!libraryChannel) libraryChannel = new Channel(LIBRARY_CHANNEL_NAME);
  libraryChannel.postMessage({ type: "library-changed", at: Date.now() });
}

export function subscribeConversationLibrary(listener: () => void): () => void {
  writerListeners.add(listener);
  const Channel = browserBroadcastChannel();
  if (!Channel) return () => writerListeners.delete(listener);
  if (!libraryChannel) libraryChannel = new Channel(LIBRARY_CHANNEL_NAME);
  libraryListeners.add(listener);
  const handleMessage = (event: MessageEvent) => {
    if (event.data?.type === "library-changed" || event.data?.type === "writer-changed") listener();
  };
  libraryChannel.addEventListener("message", handleMessage);
  return () => {
    writerListeners.delete(listener);
    libraryListeners.delete(listener);
    libraryChannel?.removeEventListener("message", handleMessage);
  };
}

function sortRecords(records: ConversationRecord[]): ConversationRecord[] {
  return [...records].sort((a, b) => b.updatedAt - a.updatedAt);
}

function utf8Length(value: string): number {
  return new TextEncoder().encode(value).length;
}

function isMessage(value: unknown): value is Message {
  if (!value || typeof value !== "object") return false;
  const message = value as Partial<Message>;
  return (
    typeof message.id === "string" &&
    (message.sender === "user" || message.sender === "assistant") &&
    typeof message.text === "string"
  );
}

function normalizeTags(value: unknown): string[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;
  const tags: string[] = [];
  for (const item of value) {
    if (typeof item !== "string") return null;
    const tag = item.trim().replace(/\s+/g, " ");
    if (tag.length > MAX_TAG_LENGTH) return null;
    if (!tag || tags.includes(tag)) continue;
    tags.push(tag);
    if (tags.length > MAX_TAGS_PER_CONVERSATION) return null;
  }
  return tags;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function normalizeNotes(value: unknown): ConversationNote[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;
  const notes: ConversationNote[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") return null;
    const candidate = item as Partial<ConversationNote>;
    if (
      typeof candidate.id !== "string" ||
      typeof candidate.text !== "string" ||
      candidate.text.length > MAX_NOTE_LENGTH ||
      !isFiniteNumber(candidate.createdAt) ||
      !isFiniteNumber(candidate.updatedAt)
    ) return null;
    notes.push({
      id: candidate.id,
      text: candidate.text,
      createdAt: candidate.createdAt,
      updatedAt: candidate.updatedAt,
    });
    if (notes.length > MAX_NOTES_PER_CONVERSATION) return null;
  }
  return notes;
}

function normalizeSource(value: unknown): Source | null {
  if (!value || typeof value !== "object") return null;
  const source = value as Partial<Source>;
  if (
    typeof source.citation !== "string" ||
    typeof source.text_preview !== "string" ||
    typeof source.score !== "number" ||
    !Number.isFinite(source.score)
  ) return null;
  return {
    citation: source.citation,
    score: source.score,
    text_preview: source.text_preview,
    ...(typeof source.text === "string" ? { text: source.text } : {}),
    ...(typeof source.chunk_id === "string" ? { chunk_id: source.chunk_id } : {}),
    ...(typeof source.ticker === "string" ? { ticker: source.ticker } : {}),
    ...(typeof source.section === "string" ? { section: source.section } : {}),
    ...(typeof source.filing_date === "string" ? { filing_date: source.filing_date } : {}),
  };
}

function normalizeRequestSnapshot(value: unknown): RequestSnapshot | undefined | null {
  if (value === undefined) return undefined;
  if (!value || typeof value !== "object") return null;
  const snapshot = value as Partial<RequestSnapshot>;
  if (
    (snapshot.ticker !== null && typeof snapshot.ticker !== "string") ||
    (snapshot.section !== null && typeof snapshot.section !== "string") ||
    typeof snapshot.topK !== "number" ||
    !Number.isInteger(snapshot.topK) ||
    snapshot.topK < 1 ||
    typeof snapshot.enableComparative !== "boolean" ||
    (snapshot.answerLanguage !== "en" && snapshot.answerLanguage !== "vi")
  ) return null;
  return {
    ticker: snapshot.ticker ?? null,
    section: snapshot.section ?? null,
    topK: snapshot.topK,
    enableComparative: snapshot.enableComparative,
    answerLanguage: snapshot.answerLanguage,
  };
}

function normalizeMessageFeedback(value: unknown): MessageFeedback | undefined | null {
  if (value === undefined) return undefined;
  if (!value || typeof value !== "object") return null;
  const feedback = value as Partial<MessageFeedback>;
  if (
    (feedback.rating !== "up" && feedback.rating !== "down") ||
    (feedback.category !== undefined &&
      feedback.category !== "inaccurate" &&
      feedback.category !== "incomplete" &&
      feedback.category !== "irrelevant" &&
      feedback.category !== "citation_issue" &&
      feedback.category !== "other") ||
    typeof feedback.at !== "number" ||
    !Number.isFinite(feedback.at)
  ) return null;
  return {
    rating: feedback.rating,
    ...(feedback.category ? { category: feedback.category } : {}),
    at: feedback.at,
  };
}

function normalizeVariants(value: unknown, messages: Message[]): AnswerVariant[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > MAX_VARIANTS_PER_CONVERSATION) return null;
  const messageIds = new Set(messages.map((message) => message.id));
  const assistantMessageIds = new Set(messages.filter((message) => message.sender === "assistant").map((message) => message.id));
  const variants: AnswerVariant[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") return null;
    const candidate = item as Partial<AnswerVariant>;
    if (
      typeof candidate.id !== "string" ||
      typeof candidate.originMessageId !== "string" ||
      !messageIds.has(candidate.originMessageId) ||
      !assistantMessageIds.has(candidate.originMessageId) ||
      typeof candidate.text !== "string" ||
      !Array.isArray(candidate.sources) ||
      !candidate.sources.every((source) => normalizeSource(source) !== null) ||
      (candidate.answerLanguage !== "en" && candidate.answerLanguage !== "vi") ||
      (candidate.status !== "completed" && candidate.status !== "stopped" && candidate.status !== "error") ||
      !isFiniteNumber(candidate.createdAt) ||
      !isFiniteNumber(candidate.updatedAt) ||
      normalizeRequestSnapshot(candidate.requestSnapshot) === null
    ) return null;
    variants.push({
      id: candidate.id,
      originMessageId: candidate.originMessageId,
      text: candidate.text,
      sources: candidate.sources.map((source) => normalizeSource(source) as Source),
      requestSnapshot: normalizeRequestSnapshot(candidate.requestSnapshot) as RequestSnapshot | undefined,
      answerLanguage: candidate.answerLanguage,
      status: candidate.status,
      createdAt: candidate.createdAt,
      updatedAt: candidate.updatedAt,
    });
  }
  return variants;
}

/**
 * Convert any in-flight streaming message into its durable stopped form so
 * partial answers are never stored (or shown) as still-streaming. Completed
 * messages are never rewritten, and no message is ever dropped here.
 */
export function normalizeStoredMessages(messages: Message[]): Message[] {
  return messages.filter(isMessage).map((message) => {
    const feedback = normalizeMessageFeedback(message.feedback);
    const normalized = feedback === null
      ? (() => {
          const { feedback: _ignored, ...withoutFeedback } = message;
          return withoutFeedback;
        })()
      : feedback === undefined
        ? message
        : { ...message, feedback };
    return normalized.isStreaming
      ? {
          ...normalized,
          text: normalized.text || "Generation stopped.",
          isStreaming: false,
          status: normalized.status === "error" ? "error" : "stopped",
        }
      : normalized;
  });
}

/**
 * Normalize an unknown persisted payload into a schema-v4 record. Returns
 * null for shapes that cannot be trusted and "future" for records that a
 * newer app version wrote; callers use the distinction to write-lock the
 * backend that holds them.
 */
function normalizeRecord(value: unknown): ConversationRecord | null | "future" {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<ConversationRecord>;
  if (
    typeof candidate.id !== "string" ||
    typeof candidate.sessionId !== "string" ||
    typeof candidate.title !== "string" ||
    !Array.isArray(candidate.messages)
  ) {
    return null;
  }

  const schemaVersion =
    typeof candidate.schemaVersion === "number" && candidate.schemaVersion >= 1
      ? Math.floor(candidate.schemaVersion)
      : 1;
  if (schemaVersion > CONVERSATION_SCHEMA_VERSION) return "future";

  const now = Date.now();
  if (!candidate.messages.every(isMessage)) return null;
  const messageIds = candidate.messages.map((message) => message.id);
  if (new Set(messageIds).size !== messageIds.length) return null;
  const messages = normalizeStoredMessages(candidate.messages as Message[]);
  if (messages.length !== candidate.messages.length) return null;
  if (messages.some((message) => normalizeRequestSnapshot(message.requestSnapshot) === null)) return null;
  const tags = normalizeTags(candidate.tags);
  const notes = normalizeNotes(candidate.notes);
  const variants = normalizeVariants(candidate.variants, messages);
  if (!tags || !notes || !variants) return null;
  let bookmarkedMessageIds: string[] = [];
  if (candidate.bookmarkedMessageIds !== undefined) {
    if (!Array.isArray(candidate.bookmarkedMessageIds) || !candidate.bookmarkedMessageIds.every((id) => typeof id === "string")) return null;
    const assistantIds = new Set(messages.filter((message) => message.sender === "assistant").map((message) => message.id));
    // Legacy records may contain a stale bookmark; preserve that historical
    // payload while requiring schema-v4 records to reference an answer.
    if (schemaVersion >= 4 && candidate.bookmarkedMessageIds.some((id) => !assistantIds.has(id))) return null;
    bookmarkedMessageIds = [...candidate.bookmarkedMessageIds];
  }
  const generatedTitle = conversationTitle(messages);
  const title = candidate.title.slice(0, 80) || "Untitled conversation";
  const titleMode: TitleMode =
    schemaVersion >= 2 && (candidate.titleMode === "auto" || candidate.titleMode === "custom")
      ? candidate.titleMode
      : title !== generatedTitle
        ? "custom"
        : "auto";

  return {
    schemaVersion: CONVERSATION_SCHEMA_VERSION,
    id: candidate.id,
    sessionId: candidate.sessionId,
    title,
    titleMode,
    revision:
      schemaVersion >= 2 && typeof candidate.revision === "number" && candidate.revision > 0
        ? Math.floor(candidate.revision)
        : 1,
    createdAt: typeof candidate.createdAt === "number" ? candidate.createdAt : now,
    updatedAt: typeof candidate.updatedAt === "number" ? candidate.updatedAt : now,
    messages,
    draft: typeof candidate.draft === "string" ? candidate.draft : "",
    bookmarkedMessageIds,
    tags,
    notes,
    variants,
  };
}

interface ParsedRecords {
  records: ConversationRecord[];
  hasFutureSchema: boolean;
  hasUnreadable: boolean;
}

function parseRecordPayload(raw: unknown): ParsedRecords {
  const result: ParsedRecords = { records: [], hasFutureSchema: false, hasUnreadable: false };
  if (!Array.isArray(raw)) return result;
  for (const item of raw) {
    const normalized = normalizeRecord(item);
    if (normalized === "future") {
      result.hasFutureSchema = true;
    } else if (normalized === null) {
      result.hasUnreadable = true;
    } else {
      result.records.push(normalized);
    }
  }
  return result;
}

/**
 * Strict tombstone validation: every field must be present and well typed.
 * Invalid entries are never repaired with defaults — they mark the payload
 * unreadable so the holding backend is write-locked and preserved.
 */
function isPositiveFiniteInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0 && Number.isFinite(value);
}

function parseTombstones(raw: unknown): { tombstones: TombstoneRecord[]; hasUnreadable: boolean } {
  if (raw === null || raw === undefined) return { tombstones: [], hasUnreadable: false };
  if (!Array.isArray(raw)) return { tombstones: [], hasUnreadable: true };
  const tombstones: TombstoneRecord[] = [];
  let hasUnreadable = false;
  for (const item of raw) {
    if (!item || typeof item !== "object") {
      hasUnreadable = true;
      continue;
    }
    const candidate = item as Partial<TombstoneRecord>;
    const validId = typeof candidate.id === "string" && candidate.id.length > 0;
    if (!validId || !isPositiveFiniteInteger(candidate.revision) || !isFiniteNumber(candidate.deletedAt)) {
      hasUnreadable = true;
      continue;
    }
    tombstones.push({ id: candidate.id, revision: candidate.revision, deletedAt: candidate.deletedAt });
  }
  return { tombstones, hasUnreadable };
}

export function conversationTitle(messages: Message[]): string {
  const firstQuestion = messages.find(
    (message) => message.sender === "user" && message.text.trim(),
  );
  if (!firstQuestion) return "Untitled conversation";
  const title = firstQuestion.text.trim().replace(/\s+/g, " ");
  return title.length > 80 ? `${title.slice(0, 77)}…` : title;
}

export function createConversationRecord(
  id: string,
  sessionId: string,
  messages: Message[] = [],
  draft = "",
  bookmarkedMessageIds: string[] = [],
  createdAt = Date.now(),
): ConversationRecord {
  return {
    schemaVersion: CONVERSATION_SCHEMA_VERSION,
    id,
    sessionId,
    title: conversationTitle(messages),
    titleMode: "auto",
    revision: 1,
    createdAt,
    updatedAt: Date.now(),
    messages,
    draft,
    bookmarkedMessageIds,
    tags: [],
    notes: [],
    variants: [],
  };
}

export interface BuildRecordInput {
  id: string;
  sessionId: string;
  messages: Message[];
  draft: string;
  bookmarkedMessageIds: string[];
  createdAt: number;
  tags?: string[];
  notes?: ConversationNote[];
  variants?: AnswerVariant[];
}

/**
 * Build the next record for a conversation while preserving user state that
 * autosave must never reset: a custom title stays custom, the auto title
 * only follows the first question while it has never been renamed.
 */
export function buildConversationRecord(
  existing: ConversationRecord | null,
  input: BuildRecordInput,
): ConversationRecord {
  const titleMode: TitleMode = existing?.titleMode === "custom" ? "custom" : "auto";
  return {
    schemaVersion: CONVERSATION_SCHEMA_VERSION,
    id: input.id,
    sessionId: input.sessionId,
    title:
      titleMode === "custom" && existing
        ? existing.title
        : conversationTitle(input.messages),
    titleMode,
    revision: existing?.revision ?? 1,
    createdAt: existing?.createdAt ?? input.createdAt,
    updatedAt: Date.now(),
    messages: input.messages,
    draft: input.draft,
    bookmarkedMessageIds: input.bookmarkedMessageIds,
    tags: input.tags ?? existing?.tags ?? [],
    notes: input.notes ?? existing?.notes ?? [],
    variants: input.variants ?? existing?.variants ?? [],
  };
}

function recordFingerprint(record: ConversationRecord): string {
  return JSON.stringify({
    sessionId: record.sessionId,
    title: record.title,
    titleMode: record.titleMode,
    messages: record.messages,
    draft: record.draft,
    bookmarkedMessageIds: record.bookmarkedMessageIds,
    tags: record.tags ?? [],
    notes: record.notes ?? [],
    variants: record.variants ?? [],
    createdAt: record.createdAt,
  });
}

function effectiveRevision(record: ConversationRecord): number {
  return record.schemaVersion >= 2 ? record.revision : 0;
}

interface MergeOutcome {
  winner: ConversationRecord;
  conflict: boolean;
}

function mergeRecordPair(a: ConversationRecord, b: ConversationRecord): MergeOutcome {
  const revisionA = effectiveRevision(a);
  const revisionB = effectiveRevision(b);
  if (revisionA !== revisionB) {
    return { winner: revisionA > revisionB ? a : b, conflict: false };
  }
  if (a.updatedAt !== b.updatedAt) {
    return { winner: a.updatedAt > b.updatedAt ? a : b, conflict: false };
  }
  return { winner: a, conflict: recordFingerprint(a) !== recordFingerprint(b) };
}

function recoveryRecordId(id: string): string {
  return `${id}#recovered`;
}

function createConversationIdFor(sessionId: string): string {
  return `conversation-${sessionId}`;
}

interface MergeResult {
  records: ConversationRecord[];
  warnings: string[];
}

/**
 * Merge record sets from multiple backends and legacy inputs. Higher
 * revision wins; version-1 records fall back to updatedAt. Ties with
 * different content keep the primary record and preserve the losing copy as
 * a separate recovery entry so no data is silently discarded. A tombstone
 * never deletes a recovery entry; deleting that copy is its own operation.
 */
function mergeRecordSets(
  sets: { records: ConversationRecord[]; durable: boolean }[],
  tombstones: Map<string, TombstoneRecord>,
): MergeResult {
  const byId = new Map<string, ConversationRecord>();
  const sourcesById = new Map<string, { durable: boolean; legacyOnly: boolean }>();
  const warnings: string[] = [];
  const recoveryCandidates: ConversationRecord[] = [];

  for (const set of sets) {
    for (const record of set.records) {
      const existing = byId.get(record.id);
      const sources = sourcesById.get(record.id) ?? { durable: false, legacyOnly: true };
      if (set.durable) {
        sources.durable = true;
        sources.legacyOnly = false;
      }
      sourcesById.set(record.id, sources);
      if (!existing) {
        byId.set(record.id, record);
        continue;
      }
      const outcome = mergeRecordPair(existing, record);
      if (outcome.conflict) {
        const loser = outcome.winner === existing ? record : existing;
        recoveryCandidates.push(loser);
        warnings.push(
          `Two different saved copies of "${existing.title}" were found; the losing copy was kept as a recovered entry.`,
        );
      }
      byId.set(record.id, outcome.winner);
    }
  }

  // Tombstones suppress records for deletion. A copy held only by read-only
  // legacy inputs stays suppressed forever (the tombstone always outranks
  // it), while a copy a writable backend still holds stays visible as
  // deletion-pending until the retry completes.
  const suppressedLegacyOnly = new Set<string>();
  for (const [id, tombstone] of tombstones) {
    const record = byId.get(id);
    if (!record) continue;
    if (effectiveRevision(record) > tombstone.revision) continue;
    if (sourcesById.get(id)?.durable) {
      record.deletionPending = true;
    } else {
      byId.delete(id);
      suppressedLegacyOnly.add(id);
    }
  }
  for (const candidate of recoveryCandidates) {
    if (!byId.has(candidate.id)) continue;
    const recoveryId = recoveryRecordId(candidate.id);
    if (byId.has(recoveryId)) continue;
    byId.set(recoveryId, {
      ...candidate,
      id: recoveryId,
      title: `${candidate.title} (recovered copy)`.slice(0, 80),
      revision: candidate.revision,
    });
  }

  return { records: sortRecords(Array.from(byId.values())), warnings };
}

// --- IndexedDB backend ---------------------------------------------------

function openDatabase(): Promise<IDBDatabase | null> {
  if (databasePromise) return databasePromise;
  if (typeof indexedDB === "undefined") {
    idbLock = { readable: false, writable: false, reason: IDB_UNAVAILABLE, permanent: true };
    return Promise.resolve(null);
  }

  databasePromise = new Promise((resolve) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
      if (!database.objectStoreNames.contains(TOMBSTONE_STORE_NAME)) {
        database.createObjectStore(TOMBSTONE_STORE_NAME, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => {
      const detail =
        request.error?.name === "VersionError" ? "newer-schema" : "open-failed";
      idbLock = { readable: false, writable: false, reason: detail, permanent: true };
      databasePromise = null;
      resolve(null);
    };
    request.onblocked = () => {
      idbLock = { readable: false, writable: false, reason: "blocked", permanent: false };
      databasePromise = null;
      resolve(null);
    };
  });
  return databasePromise;
}

function idbRequest<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Conversation storage request failed"));
  });
}

function idbTransactionDone(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error || new Error("Could not save conversation"));
    transaction.onabort = () => reject(transaction.error || new Error("Could not save conversation"));
  });
}

interface IndexedDbSnapshot {
  records: ConversationRecord[];
  tombstones: TombstoneRecord[];
  hasFutureSchema: boolean;
  hasUnreadable: boolean;
  hasUnreadableTombstones: boolean;
}

async function readIndexedDbSnapshot(): Promise<IndexedDbSnapshot> {
  const database = await openDatabase();
  if (!database) throw new Error(idbLock.reason || IDB_UNAVAILABLE);
  const transaction = database.transaction([STORE_NAME, TOMBSTONE_STORE_NAME], "readonly");
  const [rawRecords, rawTombstones] = await Promise.all([
    idbRequest(transaction.objectStore(STORE_NAME).getAll()),
    idbRequest(transaction.objectStore(TOMBSTONE_STORE_NAME).getAll()),
  ]);
  const parsed = parseRecordPayload(rawRecords);
  const parsedTombstones = parseTombstones(rawTombstones);
  return {
    records: parsed.records,
    tombstones: parsedTombstones.tombstones,
    hasFutureSchema: parsed.hasFutureSchema,
    hasUnreadable: parsed.hasUnreadable,
    hasUnreadableTombstones: parsedTombstones.hasUnreadable,
  };
}

/**
 * Write records and tombstones in one transaction. The tombstone for an id
 * is stored in the same transaction that removes its record, so a partial
 * deletion state can never be committed to IndexedDB.
 */
async function writeIndexedDbSnapshot(
  records: ConversationRecord[],
  allTombstones: TombstoneRecord[],
): Promise<void> {
  const database = await openDatabase();
  if (!database) throw new Error(idbLock.reason || IDB_UNAVAILABLE);
  const transaction = database.transaction([STORE_NAME, TOMBSTONE_STORE_NAME], "readwrite");
  const recordStore = transaction.objectStore(STORE_NAME);
  const tombstoneStore = transaction.objectStore(TOMBSTONE_STORE_NAME);
  for (const record of records) recordStore.put(record);
  for (const tombstone of allTombstones) tombstoneStore.put(tombstone);
  await idbTransactionDone(transaction);
}

/**
 * Delete one record and store its tombstone in the same transaction. A
 * recovered copy (`id#recovered`) is a separate conversation and is never
 * removed by its base record's tombstone.
 */
async function deleteIndexedDbRecord(
  id: string,
  tombstone: TombstoneRecord,
): Promise<void> {
  const database = await openDatabase();
  if (!database) throw new Error(idbLock.reason || IDB_UNAVAILABLE);
  const transaction = database.transaction([STORE_NAME, TOMBSTONE_STORE_NAME], "readwrite");
  transaction.objectStore(STORE_NAME).delete(id);
  transaction.objectStore(TOMBSTONE_STORE_NAME).put(tombstone);
  await idbTransactionDone(transaction);
}

// --- localStorage backend ------------------------------------------------

type LocalReadResult =
  | { status: "missing" }
  | { status: "parsed"; value: unknown }
  | { status: "corrupt" }
  | { status: "unavailable" };

function readLocalJson(key: string): LocalReadResult {
  if (typeof window === "undefined") return { status: "unavailable" };
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return { status: "missing" };
    return { status: "parsed", value: JSON.parse(raw) };
  } catch {
    return { status: "corrupt" };
  }
}

interface LocalEnvelope {
  envelopeVersion: number;
  records: ConversationRecord[];
  tombstones: TombstoneRecord[];
  hasFutureSchema: boolean;
  hasUnreadable: boolean;
  /** Tombstone entries that failed strict validation. */
  hasUnreadableTombstones: boolean;
  /**
   * True when the envelope exists but its structure or tombstone entries
   * cannot be understood. The payload is preserved and the backend is
   * write-locked; it is never silently replaced by an empty library.
   */
  hasInvalidStructure: boolean;
}

function readLocalEnvelope(): LocalEnvelope {
  const empty: LocalEnvelope = {
    envelopeVersion: LIBRARY_ENVELOPE_VERSION,
    records: [],
    tombstones: [],
    hasFutureSchema: false,
    hasUnreadable: false,
    hasUnreadableTombstones: false,
    hasInvalidStructure: false,
  };
  const parsed = readLocalJson(LOCAL_ENVELOPE_KEY);
  if (parsed.status !== "parsed") return empty;
  const value = parsed.value as Partial<LocalEnvelope> | null;
  if (!value || typeof value !== "object") {
    return { ...empty, hasInvalidStructure: true };
  }
  const version = value.envelopeVersion;
  if (!isPositiveFiniteInteger(version) || version > LIBRARY_ENVELOPE_VERSION) {
    return { ...empty, hasInvalidStructure: true };
  }
  if (!Array.isArray(value.records)) {
    return { ...empty, hasInvalidStructure: true };
  }
  // A missing tombstones key is a valid envelope; a present-but-malformed
  // one, or malformed entries, mark the payload unreadable.
  const hasTombstonesKey = "tombstones" in value;
  const parsedTombstones = parseTombstones(value.tombstones);
  if (hasTombstonesKey && !Array.isArray(value.tombstones)) {
    return { ...empty, hasInvalidStructure: true };
  }
  const parsedRecords = parseRecordPayload(value.records);
  return {
    envelopeVersion: version,
    records: parsedRecords.records,
    tombstones: parsedTombstones.tombstones,
    hasFutureSchema: parsedRecords.hasFutureSchema,
    hasUnreadable: parsedRecords.hasUnreadable,
    hasUnreadableTombstones: parsedTombstones.hasUnreadable,
    hasInvalidStructure: false,
  };
}

function readLegacyRecords(key: string): ParsedRecords {
  const parsed = readLocalJson(key);
  if (parsed.status !== "parsed") return { records: [], hasFutureSchema: false, hasUnreadable: false };
  return parseRecordPayload(parsed.value);
}

function writeLocalEnvelope(records: ConversationRecord[], allTombstones: TombstoneRecord[]): void {
  if (typeof window === "undefined") throw new Error("Browser storage is unavailable");
  const envelope = {
    envelopeVersion: LIBRARY_ENVELOPE_VERSION,
    records,
    tombstones: allTombstones,
  };
  const payload = JSON.stringify(envelope);
  if (utf8Length(payload) > MAX_LIBRARY_BYTES) {
    throw new Error("Conversation library is full. Export or remove an older conversation.");
  }
  // One key, one write: records and tombstones move together.
  window.localStorage.setItem(LOCAL_ENVELOPE_KEY, payload);
}

// --- Legacy (pre-library) record import ----------------------------------

function readLegacyRecord(sessionId: string, conversationId: string): ConversationRecord | null {
  if (typeof window === "undefined") return null;
  try {
    if (window.localStorage.getItem(MIGRATION_KEY) === "done") return null;
    const raw = window.localStorage.getItem(LEGACY_MESSAGES_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    const messages = (parsed as unknown[]).filter(isMessage);
    if (messages.length === 0) return null;
    return createConversationRecord(
      conversationId,
      sessionId,
      normalizeStoredMessages(messages as Message[]),
    );
  } catch {
    return null;
  }
}

function markMigrationComplete(): boolean {
  try {
    window.localStorage.setItem(MIGRATION_KEY, "done");
    return true;
  } catch {
    return false;
  }
}

// --- Repository state helpers --------------------------------------------

export function listConversations(): ConversationRecord[] {
  const merged = new Map<string, ConversationRecord>();
  for (const record of persistedRecords.values()) merged.set(record.id, record);
  for (const record of pendingRecords.values()) merged.set(record.id, record);
  for (const id of durableTombstoneIds) {
    const tombstone = tombstones.get(id);
    const record = merged.get(id);
    if (tombstone && record && effectiveRevision(record) <= tombstone.revision) {
      merged.set(id, { ...record, deletionPending: true });
    }
  }
  return sortRecords(Array.from(merged.values()));
}

/**
 * The durable snapshot always comes from the persisted records, never from
 * the merged UI list: a pending update covers only the UI, a pending
 * update of one conversation never removes the persisted copy of another,
 * and a record pending its first save is never admitted. The computed
 * deletion-pending flag is also never persisted.
 */
function durableSnapshotRecords(): ConversationRecord[] {
  return Array.from(persistedRecords.values()).map((record) => ({
    ...record,
    deletionPending: undefined,
  }));
}

/**
 * The snapshot for one save: the persisted set with the record being saved
 * replacing its own persisted entry. Other conversations' pending changes
 * are invisible to it.
 */
function buildSaveSnapshot(full: ConversationRecord): ConversationRecord[] {
  return durableSnapshotRecords()
    .filter((record) => record.id !== full.id)
    .concat(full);
}

/**
 * Only tombstones confirmed durable in at least one backend are written
 * into snapshots. A deletion whose tombstone never reached any backend is
 * still an attempt: persisting it through another conversation's autosave
 * would harden that intent without the user's knowledge. The id being
 * deleted right now is always included when its own write succeeds.
 */
function durableTombstonesForWrite(includeId?: string): TombstoneRecord[] {
  return Array.from(tombstones.values()).filter(
    (tombstone) => durableTombstoneIds.has(tombstone.id) || tombstone.id === includeId,
  );
}

function collectTombstones(): Map<string, TombstoneRecord> {
  // Module-level `tombstones` is already the union of every source merged
  // at load time plus in-session deletions.
  return tombstones;
}

function combineWarning(transient: string | null): string | null {
  const parts = [...stickyWarnings];
  if (transient) parts.push(transient);
  return parts.length > 0 ? parts.join(" ") : null;
}

const stickyWarnings: string[] = [];

// --- Repository API ------------------------------------------------------

export async function loadConversationLibrary(
  sessionId?: string,
  conversationId?: string,
): Promise<ConversationLibraryState> {
  const hasWriter = await acquireWriterOwnership();
  const resolvedSessionId = sessionId ?? legacySessionId() ?? "session";
  const resolvedConversationId =
    conversationId ?? createConversationIdFor(resolvedSessionId);
  const legacy = readLegacyRecord(resolvedSessionId, resolvedConversationId);
  const warnings: string[] = [];
  if (!hasWriter) {
    warnings.push(
      currentWriterStatus().reason === "unsupported"
        ? "This browser does not provide Web Locks; the Library is read-only and can still be exported."
        : "Another tab owns the Library writer lock; this tab is read-only until the lock is released.",
    );
  }

  // --- Read IndexedDB ---
  let idbSnapshot: IndexedDbSnapshot | null = null;
  try {
    idbSnapshot = await readIndexedDbSnapshot();
    if (idbSnapshot.hasUnreadableTombstones) {
      idbLock = {
        readable: true,
        writable: false,
        reason: "unreadable-tombstones",
        permanent: true,
      };
      warnings.push(
        "The deletion state in IndexedDB could not be verified; it was opened read-only so it is preserved.",
      );
    }
    if (idbSnapshot.hasFutureSchema || idbSnapshot.hasUnreadable) {
      // Preserve what we cannot understand: reads continue, writes to this
      // backend are locked for the whole session so a re-save can never
      // drop the records we do not understand.
      const reason = idbSnapshot.hasFutureSchema ? "newer-schema" : "unreadable-record";
      idbLock = { readable: true, writable: false, reason, permanent: true };
      warnings.push(
        reason === "newer-schema"
          ? "Some saved conversations use a newer app schema; IndexedDB was opened read-only so they are preserved."
          : "Some saved conversations could not be read from IndexedDB; it was opened read-only so they are preserved.",
      );
    }
  } catch (error) {
    const detail = idbLock.reason ?? "read-failed";
    const benign = detail === IDB_UNAVAILABLE || detail === "newer-schema";
    idbLock = { readable: false, writable: false, reason: benign ? detail : "read-failed", permanent: true };
    if (!benign) {
      console.warn("Could not read the IndexedDB conversation library:", error);
    }
  }

  // --- Read the localStorage v3 envelope ---
  let localSnapshot: LocalEnvelope = readLocalEnvelope();
  const envelopeParsed = readLocalJson(LOCAL_ENVELOPE_KEY);
  if (envelopeParsed.status === "corrupt") {
    localLock = { readable: false, writable: false, reason: "corrupt", permanent: true };
    localSnapshot = readLocalEnvelope(); // empty
    warnings.push(
      "Saved conversation data in browser storage could not be read and was left untouched; that backend cannot be written until the data is recovered.",
    );
  } else if (envelopeParsed.status === "parsed") {
    if (localSnapshot.hasInvalidStructure) {
      localLock = { readable: false, writable: false, reason: "unreadable-envelope", permanent: true };
      warnings.push(
        "Saved conversation data in browser storage has an unexpected structure and was left untouched; that backend cannot be written until the data is recovered.",
      );
    } else {
      if (localSnapshot.envelopeVersion > LIBRARY_ENVELOPE_VERSION) {
        localLock = { readable: false, writable: false, reason: "newer-envelope", permanent: true };
        warnings.push(
          "The browser conversation library was written by a newer app version and was left untouched.",
        );
      }
      if (localSnapshot.hasFutureSchema || localSnapshot.hasUnreadable) {
        const reason = localSnapshot.hasFutureSchema ? "newer-schema" : "unreadable-record";
        localLock = { readable: true, writable: false, reason, permanent: true };
        warnings.push(
          reason === "newer-schema"
            ? "Some saved conversations in browser storage use a newer app schema; that storage is read-only so they are preserved."
            : "Some saved conversations in browser storage could not be read; that storage is read-only so they are preserved.",
        );
      } else if (localSnapshot.hasUnreadableTombstones) {
        localLock = {
          readable: true,
          writable: false,
          reason: "unreadable-tombstones",
          permanent: true,
        };
        warnings.push(
          "The deletion state in browser storage could not be verified; that storage is read-only so it is preserved.",
        );
      }
    }
  }

  // --- Read legacy inputs (v1/v2); they are never rewritten ---
  const legacyV2 = readLegacyRecords(LOCAL_STORAGE_V2_KEY);
  const legacyV1 = readLegacyRecords(LOCAL_STORAGE_V1_KEY);
  if (readLocalJson(LOCAL_STORAGE_V2_KEY).status === "corrupt") {
    warnings.push("An older conversation backup could not be read and was left untouched.");
  }
  if (readLocalJson(LOCAL_STORAGE_V1_KEY).status === "corrupt") {
    warnings.push("An older conversation backup could not be read and was left untouched.");
  }
  const legacyTombstoneRaw = readLocalJson(LOCAL_TOMBSTONES_V2_KEY);
  const legacyTombstones = parseTombstones(
    legacyTombstoneRaw.status === "parsed" ? legacyTombstoneRaw.value : null,
  );
  if (legacyTombstoneRaw.status === "parsed" && legacyTombstones.hasUnreadable) {
    warnings.push(
      "The deletion state of an older conversation backup could not be read and was left untouched; deletions involving it cannot be verified.",
    );
  }

  // --- Merge tombstones from every source before merging records ---
  tombstones.clear();
  for (const tombstone of idbSnapshot?.tombstones ?? []) {
    const existing = tombstones.get(tombstone.id);
    if (!existing || existing.revision < tombstone.revision) tombstones.set(tombstone.id, tombstone);
  }
  for (const tombstone of localSnapshot.tombstones) {
    const existing = tombstones.get(tombstone.id);
    if (!existing || existing.revision < tombstone.revision) tombstones.set(tombstone.id, tombstone);
  }
  for (const tombstone of legacyTombstones.tombstones) {
    const existing = tombstones.get(tombstone.id);
    if (!existing || existing.revision < tombstone.revision) tombstones.set(tombstone.id, tombstone);
  }

  // Tombstones read from a backend are durable by definition.
  for (const id of tombstones.keys()) durableTombstoneIds.add(id);

  const merge = mergeRecordSets(
    [
      { records: idbSnapshot?.records ?? [], durable: idbSnapshot !== null },
      { records: localSnapshot.records, durable: localLock.reason !== "corrupt" && localLock.reason !== "newer-envelope" },
      { records: legacyV2.records, durable: false },
      { records: legacyV1.records, durable: false },
      { records: legacy ? [legacy] : [], durable: false },
    ],
    tombstones,
  );
  warnings.push(...merge.warnings);

  persistedRecords.clear();
  for (const record of merge.records) persistedRecords.set(record.id, record);
  pendingRecords.clear();
  snapshotLoaded = true;

  // Track which durable backends hold which records so a deletion is only
  // complete when every backend known to hold a copy has been updated.
  knownIdbCopies.clear();
  for (const record of idbSnapshot?.records ?? []) knownIdbCopies.add(record.id);
  knownLocalCopies.clear();
  if (localLock.reason !== "corrupt" && localLock.reason !== "newer-envelope") {
    for (const record of localSnapshot.records) knownLocalCopies.add(record.id);
  }
  // Legacy-input copies stay suppressed by any tombstone and never block
  // completion: they are read-only inputs this cycle.

  // --- Reconcile durable backends that are writable ---
  const mergedRecords = merge.records;
  let idbDurable = false;
  let localDurable = false;
  if (hasWriter && idbSnapshot !== null && idbLock.writable) {
    try {
      await writeIndexedDbSnapshot(mergedRecords, Array.from(tombstones.values()));
      idbDurable = true;
    } catch (error) {
      idbLock = { readable: true, writable: false, reason: "write-failed", permanent: false };
      console.warn("Could not write merged snapshot to IndexedDB:", error);
    }
  }
  if (hasWriter && localLock.writable) {
    try {
      writeLocalEnvelope(mergedRecords, Array.from(tombstones.values()));
      localDurable = true;
    } catch (error) {
      localLock = {
        readable: true,
        writable: false,
        reason: /full/i.test(error instanceof Error ? error.message : "") ? "quota" : "write-failed",
        permanent: false,
      };
      console.warn("Could not write the localStorage conversation mirror:", error);
    }
  }

  // Cross-copying during reconciliation means every successfully written
  // backend now holds the full merged set.
  if (idbDurable) for (const record of mergedRecords) knownIdbCopies.add(record.id);
  if (localDurable) for (const record of mergedRecords) knownLocalCopies.add(record.id);

  let migrationMarked = false;
  if (legacy && (idbDurable || localDurable)) {
    migrationMarked = markMigrationComplete();
  }

  const idbUsable = hasWriter && Boolean(idbSnapshot) && idbLock.writable;
  const localUsable = hasWriter && localLock.writable;
  const localHasData =
    localLock.readable &&
    (localSnapshot.records.length > 0 || localSnapshot.tombstones.length > 0);
  if (idbUsable) {
    activeStorageMode = "indexeddb";
  } else if (localUsable) {
    activeStorageMode = "localstorage";
  } else if (idbSnapshot !== null) {
    // Read-only IndexedDB (newer schema): data stays visible.
    activeStorageMode = "indexeddb";
  } else if (localHasData) {
    activeStorageMode = "localstorage";
  } else {
    // Nothing can be persisted and there is no readable data to keep.
    activeStorageMode = "memory";
  }
  if (!idbDurable && !localDurable) {
    warnings.push(
      "Conversation storage could not be updated; this session keeps changes in memory only.",
    );
  }

  if (idbLock.reason === "newer-schema") {
    warnings.push(
      "The IndexedDB conversation library was saved by a newer app version; it is opened read-only for this session.",
    );
  }
  if (localLock.reason === "newer-envelope") {
    warnings.push(
      "The browser conversation library was written by a newer app version and was left untouched.",
    );
  }

  stickyWarnings.splice(0, stickyWarnings.length, ...warnings);
  libraryWarning = combineWarning(null);
  return {
    conversations: listConversations(),
    storageMode: activeStorageMode,
    warning: libraryWarning,
  };
}

function rearmTransientLocks(): void {
  for (const lock of [idbLock, localLock]) {
    if (!lock.permanent && !lock.writable) {
      lock.writable = true;
      lock.reason = null;
    }
  }
}

export async function saveConversationRecord(
  record: ConversationRecord,
): Promise<ConversationWriteResult> {
  return enqueue(() => withWriterLock(async () => {
    rearmTransientLocks();
    if (!snapshotLoaded) {
      await loadConversationLibrary(record.sessionId, record.id).catch(() => undefined);
    }

    const normalized = normalizeRecord(record);
    if (normalized === null || normalized === "future") {
      transientWarning = "The conversation could not be saved because its data was invalid.";
      libraryWarning = combineWarning(transientWarning);
      return { status: "failed", storageMode: activeStorageMode, warning: libraryWarning };
    }

    if (!currentWriterStatus().owned) {
      pendingRecords.set(normalized.id, { ...normalized, deletionPending: undefined });
      transientWarning =
        "This tab is read-only because it does not own the Library writer lock. Export the Library or take ownership in the other tab before editing it.";
      libraryWarning = combineWarning(transientWarning);
      return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
    }

    const existingPersisted = persistedRecords.get(normalized.id);
    const existingPending = pendingRecords.get(normalized.id);
    if (existingPersisted?.deletionPending || existingPending?.deletionPending) {
      // A record with a durable tombstone is slated for removal: saves,
      // renames, and bookmarks must not resurrect it.
      transientWarning =
        "This conversation is pending deletion. Retry the deletion or export it instead of editing it.";
      libraryWarning = combineWarning(transientWarning);
      return { status: "failed", storageMode: activeStorageMode, warning: libraryWarning };
    }
    const wasPersisted = Boolean(existingPersisted);
    const baseRevision = Math.max(
      existingPersisted?.revision ?? 0,
      existingPending?.revision ?? 0,
      normalized.revision,
    );
    const full: ConversationRecord = {
      ...normalized,
      deletionPending: undefined,
      revision: baseRevision + 1,
      updatedAt: Date.now(),
    };

    // --- Admission against the durable snapshot only ---
    const saveSnapshot = buildSaveSnapshot(full);
    const intendedCount = persistedRecords.size + (wasPersisted ? 0 : 1);
    // Both backends are admitted against the same measure: the envelope
    // serialization of the snapshot plus its tombstones.
    const intendedBytes = utf8Length(
      JSON.stringify({ records: saveSnapshot, tombstones: durableTombstonesForWrite() }),
    );
    let blockedWarning: string | null = null;
    if (!wasPersisted && intendedCount > MAX_CONVERSATIONS) {
      blockedWarning = `The library keeps at most ${MAX_CONVERSATIONS} conversations. This conversation is only kept in this tab until you export or delete an older one.`;
    } else if (intendedBytes > MAX_LIBRARY_BYTES) {
      blockedWarning =
        "The conversation library is at its 25 MB storage limit. This conversation is only kept in this tab; export or delete older conversations to free space, then try saving again.";
    }
    if (blockedWarning) {
      pendingRecords.set(full.id, full);
      transientWarning = null;
      libraryWarning = combineWarning(blockedWarning);
      return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
    }

    // --- Durable write: pending records and deletion intents are never
    // part of the snapshot ---
    const durableSnapshot = saveSnapshot;
    const allTombstones = durableTombstonesForWrite();
    let anyDurable = false;
    let reportedMode: ConversationStorageMode = activeStorageMode;

    if (idbLock.writable) {
      try {
        await writeIndexedDbSnapshot(durableSnapshot, allTombstones);
        anyDurable = true;
        reportedMode = "indexeddb";
        knownIdbCopies.add(full.id);
      } catch (error) {
        idbLock = { readable: true, writable: false, reason: "write-failed", permanent: false };
        console.warn("IndexedDB save failed; falling back to browser storage:", error);
      }
    }
    if (localLock.writable) {
      try {
        writeLocalEnvelope(durableSnapshot, allTombstones);
        anyDurable = true;
        if (!anyDurable || reportedMode !== "indexeddb") reportedMode = "localstorage";
        knownLocalCopies.add(full.id);
      } catch (error) {
        localLock = {
          readable: true,
          writable: false,
          reason: /full/i.test(error instanceof Error ? error.message : "") ? "quota" : "write-failed",
          permanent: false,
        };
        console.warn("Could not write the localStorage conversation mirror:", error);
      }
    }

    if (anyDurable) {
      for (const id of tombstones.keys()) durableTombstoneIds.add(id);
      persistedRecords.set(full.id, full);
      pendingRecords.delete(full.id);
      transientWarning = null;
      libraryWarning = combineWarning(null);
      notifyLibraryChanged();
      return { status: "persisted", storageMode: reportedMode, warning: libraryWarning };
    }

    pendingRecords.set(full.id, full);
    transientWarning =
      "Conversations could not be saved to browser storage right now; they are only kept in this tab.";
    libraryWarning = combineWarning(transientWarning);
    return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
  }));
}

export async function deleteConversationRecord(id: string): Promise<ConversationWriteResult> {
  return enqueue(() => withWriterLock(async () => {
    rearmTransientLocks();
    if (!snapshotLoaded) {
      await loadConversationLibrary().catch(() => undefined);
    }

    if (!currentWriterStatus().owned) {
      transientWarning =
        "This tab is read-only because it does not own the Library writer lock. The conversation was not deleted.";
      libraryWarning = combineWarning(transientWarning);
      return { status: "failed", storageMode: activeStorageMode, warning: libraryWarning };
    }

    const persisted = persistedRecords.get(id);
    const pending = pendingRecords.get(id);
    const existingTombstone = tombstones.get(id);
    // Retries never lower the revision or recreate the record.
    const tombstone: TombstoneRecord = {
      id,
      revision: Math.max(
        existingTombstone?.revision ?? 0,
        (persisted?.revision ?? pending?.revision ?? 0) + 1,
      ),
      deletedAt: existingTombstone?.deletedAt ?? Date.now(),
    };
    tombstones.set(id, tombstone);

    const hasIdbCopy = knownIdbCopies.has(id);
    const hasLocalCopy = knownLocalCopies.has(id);

    // Memory-only deletion: no durable backend ever held this record.
    if (!persisted && !hasIdbCopy && !hasLocalCopy) {
      pendingRecords.delete(id);
      transientWarning =
        activeStorageMode === "memory"
          ? "Browser storage is unavailable; the conversation was removed for this tab only."
          : null;
      libraryWarning = combineWarning(transientWarning);
      return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
    }

    let remainingCopies = 0;
    let anyDurable = false;
    let reportedMode: ConversationStorageMode = activeStorageMode;

    // The tombstone is written to every writable backend in the same
    // transaction that removes the record there, so cross-copied records
    // can never resurrect from a backend the known-copies set missed.
    if (idbLock.writable) {
      try {
        await deleteIndexedDbRecord(id, tombstone);
        knownIdbCopies.delete(id);
        anyDurable = true;
        reportedMode = "indexeddb";
      } catch (error) {
        idbLock = { readable: true, writable: false, reason: "write-failed", permanent: false };
        console.warn("IndexedDB delete failed; trying browser storage:", error);
      }
    }
    if (localLock.writable) {
      try {
        const remaining = durableSnapshotRecords().filter((record) => record.id !== id);
        writeLocalEnvelope(remaining, durableTombstonesForWrite(id));
        knownLocalCopies.delete(id);
        anyDurable = true;
        if (reportedMode !== "indexeddb") reportedMode = "localstorage";
      } catch (error) {
        localLock = {
          readable: true,
          writable: false,
          reason: /full/i.test(error instanceof Error ? error.message : "") ? "quota" : "write-failed",
          permanent: false,
        };
        console.warn("Could not write the localStorage conversation mirror:", error);
      }
    }

    // A backend that could not be written keeps its copy.
    if (hasIdbCopy && !idbLock.writable) remainingCopies += 1;
    if (hasLocalCopy && !localLock.writable) remainingCopies += 1;

    if (remainingCopies === 0 && anyDurable) {
      // Copies held only by read-only legacy inputs stay permanently
      // suppressed by the durable tombstone; they never block completion.
      durableTombstoneIds.add(id);
      persistedRecords.delete(id);
      pendingRecords.delete(id);
      transientWarning = null;
      libraryWarning = combineWarning(null);
      notifyLibraryChanged();
      return { status: "persisted", storageMode: reportedMode, warning: libraryWarning };
    }

    // At least one writable backend still holds a copy. Keep the record
    // listed as deletion-pending so it can be exported and retried; without
    // a durable tombstone the record simply stays as it was.
    if (persisted && anyDurable) {
      persistedRecords.set(id, { ...persisted, deletionPending: true });
    }
    pendingRecords.delete(id);
    if (anyDurable) durableTombstoneIds.add(id);
    if (anyDurable) notifyLibraryChanged();
    transientWarning =
      "Deletion pending — one storage backend could not be updated. The conversation stays visible and exportable; retry the deletion to finish removing it.";
    libraryWarning = combineWarning(transientWarning);
    return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
  }));
}

export async function replaceConversationRecord(
  record: ConversationRecord,
): Promise<ConversationWriteResult> {
  return saveConversationRecord(record);
}

export function getStorageStatus(): { storageMode: ConversationStorageMode; warning: string | null } {
  return { storageMode: activeStorageMode, warning: libraryWarning };
}

export function getLibrarySnapshotLoaded(): boolean {
  return snapshotLoaded;
}

export function legacySessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(LEGACY_SESSION_KEY);
  } catch {
    return null;
  }
}
