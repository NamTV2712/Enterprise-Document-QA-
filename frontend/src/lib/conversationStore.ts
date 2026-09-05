import { Message } from "../types";

export const CONVERSATION_SCHEMA_VERSION = 1;
export const MAX_CONVERSATIONS = 100;
export const MAX_CONVERSATION_BYTES = 25 * 1024 * 1024;

const DATABASE_NAME = "enterprise-document-qa";
const DATABASE_VERSION = 1;
const STORE_NAME = "conversations";
const LOCAL_STORAGE_KEY = "sec_qa_conversations_v1";
const MIGRATION_KEY = "sec_qa_conversations_migrated_v1";
const LEGACY_MESSAGES_KEY = "sec_qa_messages";
const LEGACY_SESSION_KEY = "sec_qa_session_id";

export type ConversationStorageMode = "indexeddb" | "localstorage" | "memory";

export interface ConversationRecord {
  schemaVersion: number;
  id: string;
  sessionId: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
  draft: string;
  bookmarkedMessageIds: string[];
}

export interface ConversationLibraryState {
  conversations: ConversationRecord[];
  storageMode: ConversationStorageMode;
  warning: string | null;
}

export interface ConversationWriteResult {
  storageMode: ConversationStorageMode;
  warning: string | null;
}

const memoryRecords = new Map<string, ConversationRecord>();
let activeStorageMode: ConversationStorageMode = "memory";
let storageWarning: string | null = null;
let databasePromise: Promise<IDBDatabase> | null = null;

function sortRecords(records: ConversationRecord[]): ConversationRecord[] {
  return [...records].sort((a, b) => b.updatedAt - a.updatedAt);
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

  const messages = candidate.messages.filter(isMessage);
  const now = Date.now();
  return {
    schemaVersion: CONVERSATION_SCHEMA_VERSION,
    id: candidate.id,
    sessionId: candidate.sessionId,
    title: candidate.title.slice(0, 80) || "Untitled conversation",
    createdAt: typeof candidate.createdAt === "number" ? candidate.createdAt : now,
    updatedAt: typeof candidate.updatedAt === "number" ? candidate.updatedAt : now,
    messages,
    draft: typeof candidate.draft === "string" ? candidate.draft : "",
    bookmarkedMessageIds: Array.isArray(candidate.bookmarkedMessageIds)
      ? candidate.bookmarkedMessageIds.filter((id): id is string => typeof id === "string")
      : [],
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
    createdAt,
    updatedAt: Date.now(),
    messages,
    draft,
    bookmarkedMessageIds,
  };
}

function readLegacyRecord(sessionId: string, conversationId: string): ConversationRecord | null {
  if (typeof window === "undefined") return null;
  try {
    if (window.localStorage.getItem(MIGRATION_KEY) === "done") return null;
    const raw = window.localStorage.getItem(LEGACY_MESSAGES_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    const messages = parsed.filter(isMessage);
    if (messages.length === 0) return null;
    return createConversationRecord(conversationId, sessionId, messages);
  } catch {
    return null;
  }
}

function markMigrationComplete(): void {
  try {
    window.localStorage.setItem(MIGRATION_KEY, "done");
  } catch {
    // Storage may be disabled. The next load can safely attempt migration again.
  }
}

function readLocalRecords(): ConversationRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed)
      ? sortRecords(parsed.map(normalizeRecord).filter((record): record is ConversationRecord => record !== null))
      : [];
  } catch {
    return [];
  }
}

function writeLocalRecords(records: ConversationRecord[]): void {
  if (typeof window === "undefined") throw new Error("Browser storage is unavailable");
  const trimmed = sortRecords(records).slice(0, MAX_CONVERSATIONS);
  const payload = JSON.stringify(trimmed);
  if (payload.length > MAX_CONVERSATION_BYTES) {
    throw new Error("Conversation library is full. Export or remove an older conversation.");
  }
  window.localStorage.setItem(LOCAL_STORAGE_KEY, payload);
}

function openDatabase(): Promise<IDBDatabase> {
  if (databasePromise) return databasePromise;
  if (typeof indexedDB === "undefined") {
    return Promise.reject(new Error("IndexedDB is unavailable"));
  }

  databasePromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE_NAME)) {
        request.result.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Could not open conversation library"));
  });
  return databasePromise;
}

function idbRequest<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Conversation storage request failed"));
  });
}

async function readIndexedDbRecords(): Promise<ConversationRecord[]> {
  const database = await openDatabase();
  const transaction = database.transaction(STORE_NAME, "readonly");
  const records = await idbRequest(transaction.objectStore(STORE_NAME).getAll());
  return sortRecords(
    (records as unknown[])
      .map(normalizeRecord)
      .filter((record): record is ConversationRecord => record !== null),
  );
}

async function putIndexedDbRecord(record: ConversationRecord): Promise<void> {
  const database = await openDatabase();
  const transaction = database.transaction(STORE_NAME, "readwrite");
  transaction.objectStore(STORE_NAME).put(record);
  await new Promise<void>((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error || new Error("Could not save conversation"));
    transaction.onabort = () => reject(transaction.error || new Error("Could not save conversation"));
  });
}

async function deleteIndexedDbRecord(id: string): Promise<void> {
  const database = await openDatabase();
  const transaction = database.transaction(STORE_NAME, "readwrite");
  transaction.objectStore(STORE_NAME).delete(id);
  await new Promise<void>((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error || new Error("Could not delete conversation"));
    transaction.onabort = () => reject(transaction.error || new Error("Could not delete conversation"));
  });
}

function useMemoryRecords(): ConversationRecord[] {
  return sortRecords(Array.from(memoryRecords.values()));
}

export async function loadConversationLibrary(
  sessionId: string,
  conversationId: string,
): Promise<ConversationLibraryState> {
  const legacy = readLegacyRecord(sessionId, conversationId);

  try {
    let records = await readIndexedDbRecords();
    if (records.length === 0 && legacy) {
      await putIndexedDbRecord(legacy);
      markMigrationComplete();
      records = [legacy];
    }
    activeStorageMode = "indexeddb";
    storageWarning = null;
    return { conversations: records, storageMode: activeStorageMode, warning: null };
  } catch (indexedDbError) {
    try {
      let records = readLocalRecords();
      if (records.length === 0 && legacy) {
        records = [legacy];
        writeLocalRecords(records);
        markMigrationComplete();
      }
      activeStorageMode = "localstorage";
      storageWarning = "IndexedDB is unavailable; the library is using browser storage.";
      return { conversations: records, storageMode: activeStorageMode, warning: storageWarning };
    } catch (localStorageError) {
      if (legacy) memoryRecords.set(legacy.id, legacy);
      activeStorageMode = "memory";
      storageWarning = "Browser storage is unavailable; conversations will remain until this tab closes.";
      console.warn("Conversation storage unavailable:", indexedDbError, localStorageError);
      return { conversations: useMemoryRecords(), storageMode: activeStorageMode, warning: storageWarning };
    }
  }
}

export async function saveConversationRecord(
  record: ConversationRecord,
): Promise<ConversationWriteResult> {
  const normalized = normalizeRecord(record) || record;
  try {
    if (activeStorageMode === "indexeddb") {
      await putIndexedDbRecord(normalized);
    } else if (activeStorageMode === "localstorage") {
      const records = readLocalRecords().filter((item) => item.id !== normalized.id);
      writeLocalRecords([normalized, ...records]);
    } else {
      memoryRecords.set(normalized.id, normalized);
    }
    storageWarning = null;
    return { storageMode: activeStorageMode, warning: null };
  } catch (error) {
    if (activeStorageMode === "indexeddb") {
      try {
        const records = readLocalRecords().filter((item) => item.id !== normalized.id);
        writeLocalRecords([normalized, ...records]);
        activeStorageMode = "localstorage";
        storageWarning = "IndexedDB became unavailable; the library switched to browser storage.";
        console.warn("Could not save to IndexedDB; switched to localStorage:", error);
        return { storageMode: activeStorageMode, warning: storageWarning };
      } catch (localStorageError) {
        console.warn("Could not save to browser storage:", localStorageError);
      }
    }
    memoryRecords.set(normalized.id, normalized);
    activeStorageMode = "memory";
    storageWarning = "Conversation could not be saved to browser storage; it remains in memory for this tab.";
    console.warn("Could not save conversation:", error);
    return { storageMode: activeStorageMode, warning: storageWarning };
  }
}

export async function deleteConversationRecord(id: string): Promise<ConversationWriteResult> {
  try {
    if (activeStorageMode === "indexeddb") {
      await deleteIndexedDbRecord(id);
    } else if (activeStorageMode === "localstorage") {
      writeLocalRecords(readLocalRecords().filter((record) => record.id !== id));
    } else {
      memoryRecords.delete(id);
    }
    storageWarning = null;
    return { storageMode: activeStorageMode, warning: null };
  } catch (error) {
    if (activeStorageMode === "indexeddb") {
      try {
        writeLocalRecords(readLocalRecords().filter((record) => record.id !== id));
        activeStorageMode = "localstorage";
        storageWarning = "IndexedDB became unavailable; the library switched to browser storage.";
        console.warn("Could not delete from IndexedDB; switched to localStorage:", error);
        return { storageMode: activeStorageMode, warning: storageWarning };
      } catch (localStorageError) {
        console.warn("Could not delete from browser storage:", localStorageError);
      }
    }
    storageWarning = "Conversation could not be removed from browser storage.";
    console.warn("Could not delete conversation:", error);
    return { storageMode: activeStorageMode, warning: storageWarning };
  }
}

export async function replaceConversationRecord(record: ConversationRecord): Promise<ConversationWriteResult> {
  return saveConversationRecord(record);
}

export function getStorageStatus(): { storageMode: ConversationStorageMode; warning: string | null } {
  return { storageMode: activeStorageMode, warning: storageWarning };
}

export function legacySessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(LEGACY_SESSION_KEY);
  } catch {
    return null;
  }
}
