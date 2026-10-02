import {
  CONVERSATION_SCHEMA_VERSION,
  MAX_CONVERSATIONS,
  exportConversationWorkspaceSnapshot,
  normalizeStoredMessages,
  type ConversationRecord,
  type TombstoneRecord,
} from "./conversationStore";
import {
  EVIDENCE_COLLECTION_SCHEMA_VERSION,
  MAX_COLLECTIONS,
  MAX_ITEMS_PER_COLLECTION,
  exportEvidenceCollections,
  getEvidenceStorageStatus,
  type EvidenceCollection,
  type EvidenceItem,
} from "./evidenceCollections";
import { readCollectionFavoritesSnapshot } from "./collectionFavorites";

export const WORKSPACE_BACKUP_FORMAT = "enterprise-document-qa.workspace";
export const WORKSPACE_BACKUP_VERSION = 1;
export const MAX_WORKSPACE_BACKUP_BYTES = 25 * 1024 * 1024;

const OPAQUE_ID = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$/;
const DIGEST = /^[0-9a-f]{64}$/;
const SECRET_KEYS = new Set([
  "authorization",
  "api_key",
  "apikey",
  "password",
  "secret",
  "token",
  "access_token",
  "refresh_token",
  "local_workspace_token",
  "groq_api_key",
  "qdrant_api_key",
]);

export interface WorkspaceBackupRecord<T extends Record<string, unknown> = Record<string, unknown>> {
  legacy_id: string;
  schema_version: number;
  revision: number;
  created_at: number;
  updated_at: number;
  payload: T;
}

export interface WorkspaceEvidenceItemRecord extends WorkspaceBackupRecord<Record<string, unknown>> {
  parent_legacy_id: string;
}

export interface WorkspaceBackupTombstone {
  kind: "conversation";
  legacy_id: string;
  schema_version: 1;
  revision: number;
  deleted_at: number;
}

export interface UnsupportedBrowserSource {
  source: string;
  schema_version: number | null;
  count: number;
  reason: string;
}

export interface WorkspaceBackup {
  format: typeof WORKSPACE_BACKUP_FORMAT;
  version: typeof WORKSPACE_BACKUP_VERSION;
  exported_at: string;
  source_schemas: {
    conversations: number[];
    evidence_collections: number[];
    favorites: number[];
    tombstones: number[];
  };
  source_counts: {
    conversations: number;
    collections: number;
    evidence_items: number;
    favorites: number;
    tombstones: number;
    unsupported: number;
  };
  conversations: WorkspaceBackupRecord[];
  collections: WorkspaceBackupRecord[];
  evidence_items: WorkspaceEvidenceItemRecord[];
  favorites: string[];
  tombstones: WorkspaceBackupTombstone[];
  unsupported: UnsupportedBrowserSource[];
  digest: string;
}

export interface BrowserWorkspaceSnapshot {
  conversations: ConversationRecord[];
  tombstones: TombstoneRecord[];
  collections: EvidenceCollection[];
  favoriteCollectionIds: string[];
  unsupported?: UnsupportedBrowserSource[];
}

const UNPAIRED_SURROGATE = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;

/**
 * Cross-runtime canonical key/record ordering: Unicode code points, matching
 * the Python canonical serializer's `sorted()` semantics (UTF-16 code-unit
 * ordering would diverge for astral-plane versus U+E000–U+FFFF keys).
 */
export function compareUnicodeCodePoints(left: string, right: string): number {
  const leftPoints = Array.from(left);
  const rightPoints = Array.from(right);
  const shared = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < shared; index += 1) {
    const leftCode = leftPoints[index]?.codePointAt(0) ?? 0;
    const rightCode = rightPoints[index]?.codePointAt(0) ?? 0;
    if (leftCode !== rightCode) return leftCode - rightCode;
  }
  return leftPoints.length - rightPoints.length;
}

function canonicalValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === "object") {
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort(compareUnicodeCodePoints)) {
      const entry = (value as Record<string, unknown>)[key];
      if (entry !== undefined) result[key] = canonicalValue(entry);
    }
    return result;
  }
  return value;
}

export function canonicalWorkspaceJson(value: unknown): string {
  return JSON.stringify(canonicalValue(value));
}

function digestPayload(backup: Omit<WorkspaceBackup, "digest"> | WorkspaceBackup): Record<string, unknown> {
  const { digest: _digest, exported_at: _exportedAt, ...payload } = backup as WorkspaceBackup;
  return payload;
}

async function sha256(value: string): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error("Secure digest support is unavailable in this browser.");
  const bytes = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function computeWorkspaceBackupDigest(backup: Omit<WorkspaceBackup, "digest"> | WorkspaceBackup): Promise<string> {
  return sha256(canonicalWorkspaceJson(digestPayload(backup)));
}

function cloneRecord<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function validOpaqueId(value: unknown): value is string {
  return typeof value === "string" && OPAQUE_ID.test(value) && !value.includes("..") && !value.includes("/") && !value.includes("\\") && !(value.length >= 2 && value[1] === ":" && /[A-Za-z]/.test(value[0]));
}

function validateJsonTree(value: unknown, depth = 0, state = { nodes: 0 }): void {
  state.nodes += 1;
  if (depth > 40 || state.nodes > 250_000) throw new Error("Workspace backup exceeds structural limits.");
  if (value === null || typeof value === "boolean") return;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("Workspace backup contains a non-finite number.");
    // Python preserves arbitrary-precision integers while JavaScript numbers
    // cannot represent them exactly; both runtimes reject them so the digest
    // can never silently diverge.
    if (Number.isInteger(value) && !Number.isSafeInteger(value)) {
      throw new Error("Workspace backup contains an integer outside the safe cross-runtime range.");
    }
    return;
  }
  if (typeof value === "string") {
    if (value.length > 1_000_000) throw new Error("Workspace backup contains text exceeding the size limit.");
    if (UNPAIRED_SURROGATE.test(value)) throw new Error("Workspace backup contains unpaired surrogate code points.");
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) validateJsonTree(item, depth + 1, state);
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      if (SECRET_KEYS.has(key.toLowerCase().replaceAll("-", "_"))) {
        throw new Error("Workspace backup contains a credential field.");
      }
      if (UNPAIRED_SURROGATE.test(key)) throw new Error("Workspace backup contains unpaired surrogate code points.");
      validateJsonTree(item, depth + 1, state);
    }
    return;
  }
  throw new Error("Workspace backup contains a non-JSON value.");
}

function sortedUnique(values: number[]): number[] {
  return Array.from(new Set(values)).sort((left, right) => left - right);
}

function collectionRecord(collection: EvidenceCollection): WorkspaceBackupRecord {
  const { items: _items, ...payload } = cloneRecord(collection) as EvidenceCollection;
  const schemaVersion = collection.schemaVersion ?? 1;
  return {
    legacy_id: collection.id,
    schema_version: schemaVersion,
    revision: 1,
    created_at: collection.createdAt,
    updated_at: collection.updatedAt,
    payload: payload as unknown as Record<string, unknown>,
  };
}

function evidenceItemRecord(collection: EvidenceCollection, item: EvidenceItem): WorkspaceEvidenceItemRecord {
  return {
    legacy_id: item.id,
    parent_legacy_id: collection.id,
    schema_version: collection.schemaVersion ?? 1,
    revision: 1,
    created_at: item.savedAt,
    updated_at: item.savedAt,
    payload: cloneRecord(item) as unknown as Record<string, unknown>,
  };
}

export async function createWorkspaceBackup(
  snapshot: BrowserWorkspaceSnapshot,
  exportedAt = new Date().toISOString(),
): Promise<WorkspaceBackup> {
  const conversations: WorkspaceBackupRecord[] = snapshot.conversations.map(({ deletionPending: _pending, ...record }) => ({
    legacy_id: record.id,
    schema_version: record.schemaVersion,
    revision: record.revision,
    created_at: record.createdAt,
    updated_at: record.updatedAt,
    payload: cloneRecord({ ...record, messages: normalizeStoredMessages(record.messages) }) as unknown as Record<string, unknown>,
  })).sort((left, right) => compareUnicodeCodePoints(left.legacy_id, right.legacy_id));
  const collections = snapshot.collections.map(collectionRecord).sort((left, right) => compareUnicodeCodePoints(left.legacy_id, right.legacy_id));
  const evidenceItems = snapshot.collections.flatMap((collection) => collection.items.map((item) => evidenceItemRecord(collection, item)))
    .sort((left, right) => compareUnicodeCodePoints(left.parent_legacy_id, right.parent_legacy_id) || compareUnicodeCodePoints(left.legacy_id, right.legacy_id));
  const collectionIds = new Set(collections.map((record) => record.legacy_id));
  const favorites = Array.from(new Set(snapshot.favoriteCollectionIds.filter((id) => collectionIds.has(id)))).sort(compareUnicodeCodePoints);
  const tombstones: WorkspaceBackupTombstone[] = snapshot.tombstones.map((tombstone) => ({
    kind: "conversation" as const,
    legacy_id: tombstone.id,
    schema_version: 1 as const,
    revision: tombstone.revision,
    deleted_at: tombstone.deletedAt,
  })).sort((left, right) => compareUnicodeCodePoints(left.legacy_id, right.legacy_id));
  const unsupported = [...(snapshot.unsupported ?? [])].sort((left, right) =>
    compareUnicodeCodePoints(left.source, right.source) ||
    (left.schema_version ?? 0) - (right.schema_version ?? 0) ||
    compareUnicodeCodePoints(left.reason, right.reason));
  const withoutDigest: Omit<WorkspaceBackup, "digest"> = {
    format: WORKSPACE_BACKUP_FORMAT,
    version: WORKSPACE_BACKUP_VERSION,
    exported_at: exportedAt,
    source_schemas: {
      conversations: sortedUnique(conversations.map((record) => record.schema_version)),
      evidence_collections: sortedUnique([...collections, ...evidenceItems].map((record) => record.schema_version)),
      favorites: favorites.length > 0 ? [1] : [],
      tombstones: tombstones.length > 0 ? [1] : [],
    },
    source_counts: {
      conversations: conversations.length,
      collections: collections.length,
      evidence_items: evidenceItems.length,
      favorites: favorites.length,
      tombstones: tombstones.length,
      unsupported: unsupported.reduce((total, source) => total + source.count, 0),
    },
    conversations,
    collections,
    evidence_items: evidenceItems,
    favorites,
    tombstones,
    unsupported,
  };
  const backup: WorkspaceBackup = { ...withoutDigest, digest: await computeWorkspaceBackupDigest(withoutDigest) };
  await validateWorkspaceBackup(backup);
  return backup;
}

/** Capture supported sources only; this never loads, writes, or clears storage. */
export function captureBrowserWorkspaceSnapshot(): BrowserWorkspaceSnapshot {
  const conversations = exportConversationWorkspaceSnapshot();
  const collections = exportEvidenceCollections();
  const favorites = readCollectionFavoritesSnapshot();
  const evidenceStatus = getEvidenceStorageStatus();
  const unsupported: UnsupportedBrowserSource[] = conversations.unsupported.map((source) => ({
    source: source.source,
    schema_version: source.schemaVersion,
    count: source.count,
    reason: source.reason,
  }));
  if (favorites.unsupported) {
    unsupported.push({
      source: "localstorage.collection-favorites",
      schema_version: 1,
      count: 1,
      reason: favorites.reason ?? "Collection favorites could not be read.",
    });
  }
  if (evidenceStatus.readOnly && /invalid data|left untouched/i.test(evidenceStatus.reason ?? "")) {
    unsupported.push({
      source: "localstorage.evidence-collections",
      schema_version: null,
      count: 1,
      reason: "Evidence collections contain unsupported or malformed data and were left untouched.",
    });
  }
  return {
    conversations: conversations.conversations,
    tombstones: conversations.tombstones,
    collections,
    favoriteCollectionIds: favorites.ids,
    unsupported,
  };
}

function requireObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Workspace backup must be a JSON object.");
  return value as Record<string, unknown>;
}

function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === keys.length && actual.every((key, index) => key === [...keys].sort()[index]);
}

export async function validateWorkspaceBackup(value: unknown): Promise<WorkspaceBackup> {
  const backup = requireObject(value);
  const topKeys = ["format", "version", "exported_at", "source_schemas", "source_counts", "conversations", "collections", "evidence_items", "favorites", "tombstones", "unsupported", "digest"];
  if (!exactKeys(backup, topKeys)) throw new Error("Workspace backup schema contains missing or unknown fields.");
  const size = new TextEncoder().encode(JSON.stringify(backup)).byteLength;
  if (size > MAX_WORKSPACE_BACKUP_BYTES) throw new Error("Workspace backup exceeds the 25 MiB limit.");
  if (backup.format !== WORKSPACE_BACKUP_FORMAT || backup.version !== WORKSPACE_BACKUP_VERSION) {
    throw new Error("Workspace backup format or version is not supported.");
  }
  if (typeof backup.exported_at !== "string" || Number.isNaN(Date.parse(backup.exported_at))) throw new Error("Workspace backup timestamp is malformed.");
  if (typeof backup.digest !== "string" || !DIGEST.test(backup.digest)) throw new Error("Workspace backup digest is malformed.");
  const typed = backup as unknown as WorkspaceBackup;
  const arrays: Array<[unknown, number, string]> = [
    [typed.conversations, MAX_CONVERSATIONS, "conversations"],
    [typed.collections, MAX_COLLECTIONS, "collections"],
    [typed.evidence_items, MAX_COLLECTIONS * MAX_ITEMS_PER_COLLECTION, "evidence items"],
    [typed.favorites, MAX_COLLECTIONS, "favorites"],
    [typed.tombstones, 1_000, "tombstones"],
    [typed.unsupported, 100, "unsupported sources"],
  ];
  for (const [items, limit, label] of arrays) {
    if (!Array.isArray(items) || items.length > limit) throw new Error(`Workspace backup ${label} exceed limits.`);
  }
  validateJsonTree(typed);
  const allRecords = [...typed.conversations, ...typed.collections, ...typed.evidence_items];
  for (const record of allRecords) {
    if (!record || !validOpaqueId(record.legacy_id) || !Number.isInteger(record.schema_version) || record.schema_version < 1 || !Number.isInteger(record.revision) || record.revision < 1 || !Number.isInteger(record.created_at) || !Number.isInteger(record.updated_at) || !record.payload || typeof record.payload !== "object") {
      throw new Error("Workspace backup contains a malformed record.");
    }
    if ((record.payload as Record<string, unknown>).id !== record.legacy_id) throw new Error("Workspace backup record identity does not match its payload.");
  }
  if (typed.conversations.some((record) => ![4, CONVERSATION_SCHEMA_VERSION].includes(record.schema_version) || record.payload.schemaVersion !== record.schema_version)) throw new Error("Unsupported conversation schema version.");
  if ([...typed.collections, ...typed.evidence_items].some((record) => ![1, 2].includes(record.schema_version))) throw new Error("Unsupported evidence collection schema version.");
  const collectionIds = new Set(typed.collections.map((record) => record.legacy_id));
  if (typed.evidence_items.some((record) => !validOpaqueId(record.parent_legacy_id) || !collectionIds.has(record.parent_legacy_id))) throw new Error("Evidence item references a missing collection.");
  if (typed.favorites.some((id) => !validOpaqueId(id) || !collectionIds.has(id))) throw new Error("Favorite references a missing collection.");
  if (typed.tombstones.some((record) => record.kind !== "conversation" || record.schema_version !== 1 || !validOpaqueId(record.legacy_id) || !Number.isInteger(record.revision) || record.revision < 1 || !Number.isInteger(record.deleted_at))) throw new Error("Workspace backup contains a malformed tombstone.");
  if (!typed.source_schemas || typeof typed.source_schemas !== "object") throw new Error("Workspace source schemas are malformed.");
  const expectedSchemas = {
    conversations: sortedUnique(typed.conversations.map((record) => record.schema_version)),
    evidence_collections: sortedUnique([...typed.collections, ...typed.evidence_items].map((record) => record.schema_version)),
    favorites: typed.favorites.length > 0 ? [1] : [],
    tombstones: typed.tombstones.length > 0 ? [1] : [],
  };
  if (canonicalWorkspaceJson(typed.source_schemas) !== canonicalWorkspaceJson(expectedSchemas)) throw new Error("Workspace source schemas do not match the payload.");
  if (typed.unsupported.some((source) => !source || typeof source.source !== "string" || source.source.length === 0 || source.source.length > 128 || (source.schema_version !== null && (!Number.isInteger(source.schema_version) || source.schema_version < 1)) || !Number.isInteger(source.count) || source.count < 1 || typeof source.reason !== "string" || source.reason.length === 0 || source.reason.length > 256)) {
    throw new Error("Workspace backup contains a malformed unsupported-source descriptor.");
  }
  const expected = {
    conversations: typed.conversations.length,
    collections: typed.collections.length,
    evidence_items: typed.evidence_items.length,
    favorites: typed.favorites.length,
    tombstones: typed.tombstones.length,
    unsupported: typed.unsupported.reduce((total, source) => total + source.count, 0),
  };
  if (canonicalWorkspaceJson(typed.source_counts) !== canonicalWorkspaceJson(expected)) throw new Error("Workspace source counts do not match the payload.");
  const calculated = await computeWorkspaceBackupDigest(typed);
  if (calculated !== typed.digest) throw new Error("Workspace backup digest does not match its contents.");
  return typed;
}

export async function parseWorkspaceBackupJson(text: string): Promise<WorkspaceBackup> {
  if (new TextEncoder().encode(text).byteLength > MAX_WORKSPACE_BACKUP_BYTES) throw new Error("Workspace backup exceeds the 25 MiB limit.");
  let value: unknown;
  try {
    value = JSON.parse(text) as unknown;
  } catch {
    throw new Error("The selected workspace backup is not valid JSON.");
  }
  return validateWorkspaceBackup(value);
}

export function serializeWorkspaceBackup(backup: WorkspaceBackup): string {
  return `${JSON.stringify(backup, null, 2)}\n`;
}
