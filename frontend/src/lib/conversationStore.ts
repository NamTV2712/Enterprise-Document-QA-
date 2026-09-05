import { Message } from "../types";

export const CONVERSATION_SCHEMA_VERSION = 2;
export const MAX_CONVERSATIONS = 100;
export const MAX_LIBRARY_BYTES = 25 * 1024 * 1024;
const MAX_PERSISTED_MESSAGES = 200;

const DATABASE_NAME = "enterprise-document-qa";
const DATABASE_VERSION = 2;
const STORE_NAME = "conversations";
const TOMBSTONE_STORE_NAME = "tombstones";
const LOCAL_STORAGE_KEY = "sec_qa_conversations_v2";
const LOCAL_TOMBSTONES_KEY = "sec_qa_tombstones_v2";
// The v1 key is read for migration and merge but never rewritten in this
// cycle so a failed v2 write can never lose the only durable copy.
const LOCAL_STORAGE_V1_KEY = "sec_qa_conversations_v1";
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

interface StorageCapability {
  available: boolean;
  usable: boolean;
  detail: string | null;
}

const memoryRecords = new Map<string, ConversationRecord>();
const memoryTombstones = new Map<string, TombstoneRecord>();
let snapshotLoaded = false;
let libraryWarning: string | null = null;
let activeStorageMode: ConversationStorageMode = "memory";
let idbCapability: StorageCapability = { available: true, usable: true, detail: null };
let localCapability: StorageCapability = { available: true, usable: true, detail: null };
let databasePromise: Promise<IDBDatabase | null> | null = null;

// All durable writes are serialized so read-modify-write cycles on the
// localStorage mirror can never interleave.
let writeQueue: Promise<unknown> = Promise.resolve();

function enqueue<T>(operation: () => Promise<T>): Promise<T> {
  const run = writeQueue.then(operation, operation);
  writeQueue = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
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

/**
 * Convert any in-flight streaming message into its durable stopped form so
 * partial answers are never stored (or shown) as still-streaming.
 */
export function normalizeStoredMessages(messages: Message[]): Message[] {
  return messages
    .filter(isMessage)
    .slice(-MAX_PERSISTED_MESSAGES)
    .map((message) =>
      message.isStreaming
        ? {
            ...message,
            text: message.text || "Generation stopped.",
            isStreaming: false,
            status: message.status === "error" ? "error" : "stopped",
          }
        : message,
    );
}

/**
 * Normalize an unknown persisted payload into a schema-v2 record. Returns
 * null for shapes that cannot be trusted. Version-1 payloads (no
 * titleMode/revision) are upgraded here: a title that differs from the
 * generated title is treated as user-customized.
 */
function normalizeRecord(value: unknown): ConversationRecord | null {
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

  const now = Date.now();
  const schemaVersion =
    typeof candidate.schemaVersion === "number" && candidate.schemaVersion >= 1
      ? Math.floor(candidate.schemaVersion)
      : 1;
  if (schemaVersion > CONVERSATION_SCHEMA_VERSION) return null;

  const messages = normalizeStoredMessages(candidate.messages as Message[]);
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
    bookmarkedMessageIds: Array.isArray(candidate.bookmarkedMessageIds)
      ? candidate.bookmarkedMessageIds.filter((id): id is string => typeof id === "string")
      : [],
  };
}

function normalizeTombstone(value: unknown): TombstoneRecord | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<TombstoneRecord>;
  if (typeof candidate.id !== "string") return null;
  return {
    id: candidate.id,
    revision: typeof candidate.revision === "number" && candidate.revision > 0 ? candidate.revision : 1,
    deletedAt: typeof candidate.deletedAt === "number" ? candidate.deletedAt : Date.now(),
  };
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
  };
}

export interface BuildRecordInput {
  id: string;
  sessionId: string;
  messages: Message[];
  draft: string;
  bookmarkedMessageIds: string[];
  createdAt: number;
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
    createdAt: record.createdAt,
  });
}

function effectiveRevision(record: ConversationRecord): number {
  return record.schemaVersion >= 2 ? record.revision : 0;
}

function isSameContent(a: ConversationRecord, b: ConversationRecord): boolean {
  return recordFingerprint(a) === recordFingerprint(b);
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
  return { winner: a, conflict: !isSameContent(a, b) };
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
 * Merge record sets from multiple backends. Higher revision wins; version-1
 * records fall back to updatedAt. Ties with different content keep the
 * primary record and preserve the losing copy as a separate recovery entry
 * so no data is silently discarded.
 */
function mergeRecordSets(
  sets: ConversationRecord[][],
  tombstones: Map<string, TombstoneRecord>,
): MergeResult {
  const byId = new Map<string, ConversationRecord>();
  const warnings: string[] = [];
  const recoveryCandidates: ConversationRecord[] = [];

  for (const set of sets) {
    for (const record of set) {
      const existing = byId.get(record.id);
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

  for (const [id, tombstone] of tombstones) {
    const record = byId.get(id);
    if (record && effectiveRevision(record) <= tombstone.revision) {
      byId.delete(id);
    }
    const recovery = byId.get(recoveryRecordId(id));
    if (recovery && effectiveRevision(recovery) <= tombstone.revision) {
      byId.delete(recoveryRecordId(id));
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

// --- IndexedDB backend ---

function openDatabase(): Promise<IDBDatabase | null> {
  if (databasePromise) return databasePromise;
  if (typeof indexedDB === "undefined") {
    idbCapability = { available: false, usable: false, detail: "IndexedDB is unavailable" };
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
      idbCapability = {
        available: true,
        usable: false,
        detail: request.error?.name === "VersionError" ? "newer-schema" : "open-failed",
      };
      databasePromise = null;
      resolve(null);
    };
    request.onblocked = () => {
      idbCapability = { available: true, usable: false, detail: "blocked" };
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
}

async function readIndexedDbSnapshot(): Promise<IndexedDbSnapshot> {
  const database = await openDatabase();
  if (!database) throw new Error(idbCapability.detail || "IndexedDB is unavailable");
  const transaction = database.transaction([STORE_NAME, TOMBSTONE_STORE_NAME], "readonly");
  const [rawRecords, rawTombstones] = await Promise.all([
    idbRequest(transaction.objectStore(STORE_NAME).getAll()),
    idbRequest(transaction.objectStore(TOMBSTONE_STORE_NAME).getAll()),
  ]);
  return {
    records: (rawRecords as unknown[])
      .map(normalizeRecord)
      .filter((record): record is ConversationRecord => record !== null),
    tombstones: (rawTombstones as unknown[])
      .map(normalizeTombstone)
      .filter((tombstone): tombstone is TombstoneRecord => tombstone !== null),
  };
}

async function writeIndexedDbSnapshot(
  records: ConversationRecord[],
  tombstones: TombstoneRecord[],
): Promise<void> {
  const database = await openDatabase();
  if (!database) throw new Error(idbCapability.detail || "IndexedDB is unavailable");
  const transaction = database.transaction([STORE_NAME, TOMBSTONE_STORE_NAME], "readwrite");
  const recordStore = transaction.objectStore(STORE_NAME);
  const tombstoneStore = transaction.objectStore(TOMBSTONE_STORE_NAME);
  for (const record of records) recordStore.put(record);
  for (const tombstone of tombstones) tombstoneStore.put(tombstone);
  await idbTransactionDone(transaction);
}

async function deleteIndexedDbRecord(id: string): Promise<void> {
  const database = await openDatabase();
  if (!database) throw new Error(idbCapability.detail || "IndexedDB is unavailable");
  const transaction = database.transaction([STORE_NAME, TOMBSTONE_STORE_NAME], "readwrite");
  transaction.objectStore(STORE_NAME).delete(id);
  transaction.objectStore(TOMBSTONE_STORE_NAME).delete(recoveryRecordId(id));
  await idbTransactionDone(transaction);
}

// --- localStorage backend ---

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

function readLocalRecords(): ConversationRecord[] {
  const v2 = readLocalJson(LOCAL_STORAGE_KEY);
  if (v2.status === "parsed" && Array.isArray(v2.value)) {
    return (v2.value as unknown[])
      .map(normalizeRecord)
      .filter((record): record is ConversationRecord => record !== null);
  }
  if (v2.status === "missing" || v2.status === "corrupt") {
    // Fall back to the untouched v1 payload for merge; never rewrite it.
    const v1 = readLocalJson(LOCAL_STORAGE_V1_KEY);
    if (v1.status !== "parsed" || !Array.isArray(v1.value)) return [];
    return (v1.value as unknown[])
      .map(normalizeRecord)
      .filter((record): record is ConversationRecord => record !== null);
  }
  return [];
}

function readLocalTombstones(): TombstoneRecord[] {
  const parsed = readLocalJson(LOCAL_TOMBSTONES_KEY);
  if (parsed.status !== "parsed" || !Array.isArray(parsed.value)) return [];
  return (parsed.value as unknown[])
    .map(normalizeTombstone)
    .filter((tombstone): tombstone is TombstoneRecord => tombstone !== null);
}

function writeLocalSnapshot(records: ConversationRecord[], tombstones: TombstoneRecord[]): void {
  if (typeof window === "undefined") throw new Error("Browser storage is unavailable");
  const payload = JSON.stringify(records);
  if (utf8Length(payload) > MAX_LIBRARY_BYTES) {
    throw new Error("Conversation library is full. Export or remove an older conversation.");
  }
  window.localStorage.setItem(LOCAL_STORAGE_KEY, payload);
  window.localStorage.setItem(LOCAL_TOMBSTONES_KEY, JSON.stringify(tombstones));
}

function collectTombstones(): Map<string, TombstoneRecord> {
  const merged = new Map<string, TombstoneRecord>();
  for (const tombstone of memoryTombstones.values()) {
    const existing = merged.get(tombstone.id);
    if (!existing || existing.revision < tombstone.revision) merged.set(tombstone.id, tombstone);
  }
  for (const tombstone of readLocalTombstones()) {
    const existing = merged.get(tombstone.id);
    if (!existing || existing.revision < tombstone.revision) merged.set(tombstone.id, tombstone);
  }
  return merged;
}

// --- Legacy (pre-library) record import ---

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
    return createConversationRecord(conversationId, sessionId, normalizeStoredMessages(messages as Message[]));
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

// --- Repository API ---

export async function loadConversationLibrary(
  sessionId?: string,
  conversationId?: string,
): Promise<ConversationLibraryState> {
  const resolvedSessionId = sessionId ?? legacySessionId() ?? "session";
  const resolvedConversationId =
    conversationId ?? createConversationIdFor(resolvedSessionId);
  const legacy = readLegacyRecord(resolvedSessionId, resolvedConversationId);
  const warnings: string[] = [];

  let idbSnapshot: IndexedDbSnapshot | null = null;
  try {
    idbSnapshot = await readIndexedDbSnapshot();
  } catch (error) {
    // Preserve the newer-schema/unavailable signals so benign cases (a
    // browser without IndexedDB) never log a scary warning.
    const detail = idbCapability.detail ?? "read-failed";
    const isBenign = detail === "newer-schema" || detail === "IndexedDB is unavailable";
    idbCapability = { available: true, usable: false, detail: isBenign ? detail : "read-failed" };
    if (!isBenign) {
      console.warn("Could not read the IndexedDB conversation library:", error);
    }
  }

  let localUsable = true;
  let localRecords: ConversationRecord[] = [];
  const v2Probe = readLocalJson(LOCAL_STORAGE_KEY);
  const v1Probe = readLocalJson(LOCAL_STORAGE_V1_KEY);
  const corruptLocal = v2Probe.status === "corrupt" || v1Probe.status === "corrupt";
  if (!corruptLocal) {
    localRecords = readLocalRecords();
  } else {
    localUsable = false;
    warnings.push(
      "Saved conversation data in browser storage could not be read and was left untouched; that backend is excluded from this session.",
    );
  }

  // Collect tombstones from every readable backend BEFORE merging so a
  // stale fallback copy can never resurrect a deleted conversation.
  const tombstones = collectTombstones();
  if (idbSnapshot?.tombstones.length) {
    for (const tombstone of idbSnapshot.tombstones) {
      const existing = tombstones.get(tombstone.id);
      if (!existing || existing.revision < tombstone.revision) tombstones.set(tombstone.id, tombstone);
    }
  }

  const sets: ConversationRecord[][] = [];
  if (idbSnapshot) sets.push(idbSnapshot.records);
  if (localUsable) sets.push(localRecords);
  if (legacy) sets.push([legacy]);

  const merge = mergeRecordSets(sets, tombstones);
  warnings.push(...merge.warnings);

  memoryRecords.clear();
  for (const record of merge.records) memoryRecords.set(record.id, record);
  memoryTombstones.clear();
  for (const [id, tombstone] of tombstones) memoryTombstones.set(id, tombstone);
  snapshotLoaded = true;

  let durableRecords = false;
  if (idbSnapshot !== null) {
    try {
      await writeIndexedDbSnapshot(merge.records, Array.from(tombstones.values()));
      durableRecords = true;
    } catch (error) {
      idbCapability = { available: true, usable: false, detail: "write-failed" };
      console.warn("Could not write merged snapshot to IndexedDB:", error);
    }
  }

  // Mirror the merged snapshot into localStorage as the recovery fallback.
  // The fallback copy is intentionally kept this cycle so a failed IndexedDB
  // transaction can still be restored later.
  let localMirrorWritten = false;
  if (localUsable) {
    localMirrorWritten = writeLocalSnapshotSafely(
      merge.records,
      Array.from(tombstones.values()),
    );
  }

  let migrationMarked = false;
  if (legacy && (durableRecords || localMirrorWritten)) {
    migrationMarked = markMigrationComplete();
  }

  if (idbSnapshot !== null) {
    activeStorageMode = "indexeddb";
    if (!durableRecords) {
      warnings.push("IndexedDB could not be updated; changes are being kept in the other storage backend.");
    }
  } else if (localUsable && localMirrorWritten) {
    activeStorageMode = "localstorage";
  } else {
    activeStorageMode = "memory";
    warnings.push(
      warnings.length === 0
        ? "Browser storage is unavailable; conversations will remain until this tab closes."
        : "Browser storage is unavailable; this session is running in memory.",
    );
  }
  if (idbCapability.detail === "newer-schema") {
    warnings.push(
      "The conversation library was saved by a newer app version; it is opened read-only for this session.",
    );
  }

  libraryWarning = warnings.length > 0 ? warnings.join(" ") : null;
  return {
    conversations: listConversations(),
    storageMode: activeStorageMode,
    warning: libraryWarning,
  };
}

function writeLocalSnapshotSafely(records: ConversationRecord[], tombstones: TombstoneRecord[]): boolean {
  try {
    writeLocalSnapshot(records, tombstones);
    localCapability = { available: true, usable: true, detail: null };
    return true;
  } catch (error) {
    localCapability = {
      available: true,
      usable: false,
      detail: error instanceof Error && /full/i.test(error.message) ? "quota" : "write-failed",
    };
    console.warn("Could not write the localStorage conversation mirror:", error);
    return false;
  }
}

function persistLocalMirror(): boolean {
  if (!localCapability.usable) return false;
  return writeLocalSnapshotSafely(listConversations(), Array.from(memoryTombstones.values()));
}

export function listConversations(): ConversationRecord[] {
  return sortRecords(Array.from(memoryRecords.values()));
}

function libraryBytes(): number {
  return utf8Length(JSON.stringify(listConversations()));
}

export async function saveConversationRecord(
  record: ConversationRecord,
): Promise<ConversationWriteResult> {
  return enqueue(async () => {
    if (!snapshotLoaded) {
      await loadConversationLibrary(
        record.sessionId,
        record.id,
      ).catch(() => undefined);
    }

    const normalized = normalizeRecord(record);
    if (!normalized) {
      libraryWarning = "The conversation could not be saved because its data was invalid.";
      return { status: "failed", storageMode: activeStorageMode, warning: libraryWarning };
    }

    const existing = memoryRecords.get(normalized.id);
    const isNew = !existing;
    const full: ConversationRecord = {
      ...normalized,
      revision: (existing?.revision ?? normalized.revision) + 1,
      updatedAt: Date.now(),
    };

    if (isNew && memoryRecords.size >= MAX_CONVERSATIONS) {
      libraryWarning = `The library keeps at most ${MAX_CONVERSATIONS} conversations. This conversation is only kept in this tab until you export or delete an older one.`;
      memoryRecords.set(full.id, full);
      return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
    }
    if (isNew && libraryBytes() + utf8Length(JSON.stringify(full)) > MAX_LIBRARY_BYTES) {
      libraryWarning =
        "The conversation library is at its 25 MB storage limit. This conversation is only kept in this tab; export or delete older conversations to free space.";
      memoryRecords.set(full.id, full);
      return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
    }

    memoryRecords.set(full.id, full);

    let durable = false;
    if (activeStorageMode === "indexeddb" && idbCapability.usable) {
      try {
        await writeIndexedDbSnapshot(listConversations(), Array.from(memoryTombstones.values()));
        durable = true;
      } catch (error) {
        console.warn("IndexedDB save failed; falling back to browser storage:", error);
      }
    }
    // Mirror successful saves into localStorage so the fallback copy stays
    // current; a mirrored save alone also counts as durable.
    if (localCapability.usable) {
      durable = persistLocalMirror() || durable;
    }

    if (durable) {
      libraryWarning = null;
      return { status: "persisted", storageMode: activeStorageMode, warning: null };
    }

    libraryWarning =
      "Conversations could not be saved to browser storage right now; they are only kept in this tab.";
    return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
  });
}

export async function deleteConversationRecord(id: string): Promise<ConversationWriteResult> {
  return enqueue(async () => {
    const existing = memoryRecords.get(id);
    const tombstone: TombstoneRecord = {
      id,
      revision: (existing?.revision ?? 0) + 1,
      deletedAt: Date.now(),
    };

    let durable = false;
    if (idbCapability.usable && activeStorageMode !== "memory") {
      try {
        await deleteIndexedDbRecord(id);
        // Keep the localStorage mirror consistent so a later IndexedDB
        // failure cannot resurrect the deleted conversation.
        const tombstones = Array.from(memoryTombstones.values());
        tombstones.push(tombstone);
        if (persistLocalMirrorWithTombstones(tombstones)) {
          durable = true;
        } else {
          durable = true; // IndexedDB delete succeeded; mirror failure is non-fatal.
        }
      } catch (error) {
        console.warn("IndexedDB delete failed; trying browser storage:", error);
      }
    }
    if (!durable && localCapability.usable) {
      memoryTombstones.set(id, tombstone);
      durable = persistLocalMirror();
    }

    if (durable || activeStorageMode === "memory") {
      memoryTombstones.set(id, tombstone);
      memoryRecords.delete(id);
      memoryRecords.delete(recoveryRecordId(id));
      if (activeStorageMode === "memory") {
        libraryWarning =
          "Browser storage is unavailable; the conversation was removed for this tab only.";
        return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
      }
      libraryWarning = null;
      return { status: "persisted", storageMode: activeStorageMode, warning: null };
    }

    libraryWarning =
      "The conversation could not be removed from browser storage. It stays in your Library; please try again.";
    return { status: "volatile", storageMode: activeStorageMode, warning: libraryWarning };
  });
}

function persistLocalMirrorWithTombstones(tombstones: TombstoneRecord[]): boolean {
  if (!localCapability.usable) return false;
  return writeLocalSnapshotSafely(listConversations(), tombstones);
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
