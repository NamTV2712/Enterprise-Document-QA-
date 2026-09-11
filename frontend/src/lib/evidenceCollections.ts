import { Source } from "../types";
import { getWriterStatus } from "./conversationStore";

export interface EvidenceItem {
  id: string;
  citation: string;
  excerpt: string;
  chunkId?: string;
  ticker?: string;
  section?: string;
  filingDate?: string;
  sourceConversationId?: string;
  sourceMessageId?: string;
  note?: string;
  savedAt: number;
}

export interface EvidenceCollection {
  id: string;
  name: string;
  items: EvidenceItem[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = "sec_qa_evidence_collections_v1";
export const MAX_COLLECTIONS = 50;
export const MAX_ITEMS_PER_COLLECTION = 100;
export const MAX_EVIDENCE_NOTE_LENGTH = 10_000;

let storageReadError: string | null = null;

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isOptionalString(value: unknown): value is string | undefined {
  return value === undefined || typeof value === "string";
}

function isOptionalEvidenceNote(value: unknown): value is string | undefined {
  return value === undefined || (typeof value === "string" && value.length <= MAX_EVIDENCE_NOTE_LENGTH);
}

function isEvidenceItem(value: unknown): value is EvidenceItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<EvidenceItem>;
  return typeof item.id === "string" && item.id.length > 0 &&
    typeof item.citation === "string" && typeof item.excerpt === "string" &&
    isOptionalString(item.chunkId) && isOptionalString(item.ticker) &&
    isOptionalString(item.section) && isOptionalString(item.filingDate) &&
    isOptionalString(item.sourceConversationId) && isOptionalString(item.sourceMessageId) &&
    isOptionalEvidenceNote(item.note) &&
    isFiniteNumber(item.savedAt);
}

function validateCollections(value: unknown): value is EvidenceCollection[] {
  if (!Array.isArray(value) || value.length > MAX_COLLECTIONS) return false;
  return value.every((entry) => {
    if (!entry || typeof entry !== "object") return false;
    const collection = entry as Partial<EvidenceCollection>;
    return typeof collection.id === "string" && collection.id.length > 0 &&
      typeof collection.name === "string" && collection.name.trim().length > 0 && collection.name.length <= 80 &&
      Array.isArray(collection.items) && collection.items.length <= MAX_ITEMS_PER_COLLECTION &&
      collection.items.every(isEvidenceItem) &&
      isFiniteNumber(collection.createdAt) && isFiniteNumber(collection.updatedAt);
  });
}

export interface EvidenceStorageStatus {
  readOnly: boolean;
  reason: string | null;
}

export function getEvidenceStorageStatus(): EvidenceStorageStatus {
  try {
    if (localStorage.getItem(STORAGE_KEY) === null) storageReadError = null;
  } catch {
    // The writer check below still reports a read-only state when storage is unavailable.
  }
  const writer = getWriterStatus();
  if (storageReadError) return { readOnly: true, reason: storageReadError };
  if (writer.readOnly) {
    return {
      readOnly: true,
      reason: writer.reason === "unsupported"
        ? "Evidence collections are read-only because this browser does not support the Library writer lock."
        : "Evidence collections are read-only while another tab owns the Library writer lock.",
    };
  }
  return { readOnly: false, reason: null };
}

export function assertEvidenceCollectionsWritable(): void {
  const status = getEvidenceStorageStatus();
  if (status.readOnly) throw new Error(status.reason ?? "Evidence collections are read-only.");
}

function readCollections(): EvidenceCollection[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    if (!validateCollections(parsed)) throw new Error("invalid shape");
    storageReadError = null;
    return parsed;
  } catch {
    // Never replace malformed bytes with an empty collection. The caller can
    // still read the rest of the Library, but evidence mutations fail closed.
    storageReadError = "Evidence storage contains invalid data and was left untouched. Export or clear it manually before saving new evidence.";
    return [];
  }
}

function writeCollections(collections: EvidenceCollection[]): void {
  assertEvidenceCollectionsWritable();
  if (!validateCollections(collections)) throw new Error("Evidence collection data is invalid and was not saved.");
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(collections));
    window.dispatchEvent(new Event("sec-qa-evidence-updated"));
  } catch {
    // Callers must not announce a successful save when the browser rejected
    // the write (quota, private mode, or a disabled storage backend).
    throw new Error("Evidence storage is unavailable. The excerpt was not saved.");
  }
}

/** Return a validated snapshot suitable for a local backup. */
export function exportEvidenceCollections(): EvidenceCollection[] {
  return readCollections().map((collection) => ({
    ...collection,
    items: collection.items.map((item) => ({ ...item })),
  }));
}

function importId(prefix: string): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `${prefix}-${globalThis.crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Import collections with fresh IDs and remapped collection/item references.
 * Source excerpts are copied as independent snapshots so deleting a
 * conversation never deletes evidence already saved in a collection.
 */
export function importEvidenceCollections(value: unknown): EvidenceCollection[] {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > MAX_COLLECTIONS) {
    throw new Error(`The backup must contain at most ${MAX_COLLECTIONS} evidence collections.`);
  }
  const now = Date.now();
  const imported: EvidenceCollection[] = [];
  for (const raw of value) {
    if (!raw || typeof raw !== "object") throw new Error("The backup contains an invalid evidence collection.");
    const candidate = raw as Partial<EvidenceCollection>;
    if (
      typeof candidate.name !== "string" ||
      candidate.name.trim().length > 80 ||
      !Array.isArray(candidate.items) ||
      candidate.items.length > MAX_ITEMS_PER_COLLECTION ||
      (candidate.createdAt !== undefined && (typeof candidate.createdAt !== "number" || !Number.isFinite(candidate.createdAt))) ||
      (candidate.updatedAt !== undefined && (typeof candidate.updatedAt !== "number" || !Number.isFinite(candidate.updatedAt)))
    ) {
      throw new Error("The backup contains an invalid evidence collection.");
    }
    const collectionId = importId("collection-import");
    const items: EvidenceItem[] = [];
    for (const entry of candidate.items) {
      if (!entry || typeof entry !== "object") throw new Error("The backup contains an invalid evidence item.");
      const item = entry as Partial<EvidenceItem>;
      if (
        typeof item.citation !== "string" ||
        typeof item.excerpt !== "string" ||
        (item.chunkId !== undefined && typeof item.chunkId !== "string") ||
        (item.ticker !== undefined && typeof item.ticker !== "string") ||
        (item.section !== undefined && typeof item.section !== "string") ||
        (item.filingDate !== undefined && typeof item.filingDate !== "string") ||
        (item.sourceConversationId !== undefined && typeof item.sourceConversationId !== "string") ||
        (item.sourceMessageId !== undefined && typeof item.sourceMessageId !== "string") ||
        !isOptionalEvidenceNote(item.note) ||
        (item.savedAt !== undefined && (typeof item.savedAt !== "number" || !Number.isFinite(item.savedAt)))
      ) throw new Error("The backup contains an invalid evidence item.");
      items.push({
        id: importId("evidence-import"),
        citation: item.citation,
        excerpt: item.excerpt,
        ...(typeof item.chunkId === "string" ? { chunkId: item.chunkId } : {}),
        ...(typeof item.ticker === "string" ? { ticker: item.ticker } : {}),
        ...(typeof item.section === "string" ? { section: item.section } : {}),
        ...(typeof item.filingDate === "string" ? { filingDate: item.filingDate } : {}),
        ...(typeof item.sourceConversationId === "string" ? { sourceConversationId: item.sourceConversationId } : {}),
        ...(typeof item.sourceMessageId === "string" ? { sourceMessageId: item.sourceMessageId } : {}),
        ...(typeof item.note === "string" ? { note: item.note } : {}),
        savedAt: typeof item.savedAt === "number" && Number.isFinite(item.savedAt) ? item.savedAt : now,
      });
    }
    imported.push({
      id: collectionId,
      name: candidate.name.trim().slice(0, 80) || "Imported evidence",
      items,
      createdAt: typeof candidate.createdAt === "number" ? candidate.createdAt : now,
      updatedAt: now,
    });
  }
  return imported;
}

export function mergeEvidenceCollections(imported: EvidenceCollection[]): void {
  if (imported.length === 0) return;
  assertEvidenceCollectionsWritable();
  const existing = readCollections();
  const merged = [...existing, ...imported];
  if (merged.length > MAX_COLLECTIONS) throw new Error(`Import would exceed the ${MAX_COLLECTIONS}-collection limit. No collections were changed.`);
  writeCollections(merged);
}

export function preflightEvidenceCollectionsImport(imported: EvidenceCollection[]): void {
  if (imported.length === 0) return;
  assertEvidenceCollectionsWritable();
  const existing = readCollections();
  if (existing.length + imported.length > MAX_COLLECTIONS) {
    throw new Error(`Import would exceed the ${MAX_COLLECTIONS}-collection limit. No collections were changed.`);
  }
}

export function listEvidenceCollections(): EvidenceCollection[] {
  return readCollections().sort((a, b) => b.updatedAt - a.updatedAt);
}

export function createEvidenceCollection(name: string): EvidenceCollection {
  assertEvidenceCollectionsWritable();
  const trimmed = name.trim().slice(0, 80);
  if (!trimmed) throw new Error("Collection name is required");
  const collections = readCollections();
  if (collections.length >= MAX_COLLECTIONS) throw new Error("Collection limit reached");
  const now = Date.now();
  const collection: EvidenceCollection = { id: `collection-${now}-${Math.random().toString(36).slice(2, 8)}`, name: trimmed, items: [], createdAt: now, updatedAt: now };
  writeCollections([...collections, collection]);
  return collection;
}

export function saveEvidence(source: Source, options: { collectionId?: string; conversationId?: string; messageId?: string } = {}): EvidenceCollection {
  assertEvidenceCollectionsWritable();
  const collections = readCollections();
  let collection = options.collectionId
    ? collections.find((item) => item.id === options.collectionId)
    : collections[0];
  if (options.collectionId && !collection) throw new Error("The selected evidence collection does not exist.");
  const now = Date.now();
  const item: EvidenceItem = {
    id: `evidence-${now}-${Math.random().toString(36).slice(2, 8)}`,
    citation: source.citation,
    excerpt: source.text || source.text_preview,
    ...(source.chunk_id ? { chunkId: source.chunk_id } : {}),
    ...(source.ticker ? { ticker: source.ticker } : {}),
    ...(source.section ? { section: source.section } : {}),
    ...(source.filing_date ? { filingDate: source.filing_date } : {}),
    ...(options.conversationId ? { sourceConversationId: options.conversationId } : {}),
    ...(options.messageId ? { sourceMessageId: options.messageId } : {}),
    savedAt: now,
  };

  if (!collection) {
    const createdAt = now;
    collection = {
      id: `collection-${now}-${Math.random().toString(36).slice(2, 8)}`,
      name: "Research evidence",
      items: [],
      createdAt,
      updatedAt: now,
    };
  }
  const sameSnapshot = collection.items.find((existing) =>
    existing.chunkId === item.chunkId &&
    existing.citation === item.citation &&
    existing.excerpt === item.excerpt &&
    existing.ticker === item.ticker &&
    existing.section === item.section &&
    existing.filingDate === item.filingDate,
  );
  if (sameSnapshot) return collection;
  if (collection.items.length >= MAX_ITEMS_PER_COLLECTION) throw new Error("Collection item limit reached. No evidence was changed.");
  const next = { ...collection, items: [...collection.items, item], updatedAt: now };
  const nextCollections = collections.some((existing) => existing.id === collection?.id)
    ? collections.map((existing) => existing.id === next.id ? next : existing)
    : [...collections, next];
  if (nextCollections.length > MAX_COLLECTIONS) throw new Error(`The ${MAX_COLLECTIONS}-collection limit was reached. No evidence was changed.`);
  writeCollections(nextCollections);
  return next;
}

export function updateEvidenceNote(collectionId: string, itemId: string, note: string): EvidenceCollection {
  assertEvidenceCollectionsWritable();
  const collections = readCollections();
  const collection = collections.find((entry) => entry.id === collectionId);
  if (!collection) throw new Error("The selected evidence collection does not exist.");
  const item = collection.items.find((entry) => entry.id === itemId);
  if (!item) throw new Error("The selected evidence item does not exist.");
  const nextNote = note.slice(0, MAX_EVIDENCE_NOTE_LENGTH);
  const nextCollection: EvidenceCollection = {
    ...collection,
    updatedAt: Date.now(),
    items: collection.items.map((entry) => entry.id === itemId ? { ...entry, note: nextNote || undefined } : entry),
  };
  writeCollections(collections.map((entry) => entry.id === collectionId ? nextCollection : entry));
  return nextCollection;
}

export function clearEvidenceCollections(): void {
  assertEvidenceCollectionsWritable();
  try {
    localStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new Event("sec-qa-evidence-updated"));
  } catch {
    throw new Error("Evidence storage is unavailable. Collections were not cleared.");
  }
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (event) => {
    if (event.key === STORAGE_KEY) window.dispatchEvent(new Event("sec-qa-evidence-updated"));
  });
}
