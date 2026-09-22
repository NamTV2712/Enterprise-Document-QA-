/** Versioned browser storage for collection favorite identities. */

export const COLLECTION_FAVORITES_SCHEMA_VERSION = 1;
export const COLLECTION_FAVORITES_STORAGE_KEY = "sec_qa_collection_stars_v1";

export interface CollectionFavoritesSnapshot {
  schemaVersion: typeof COLLECTION_FAVORITES_SCHEMA_VERSION;
  ids: string[];
  unsupported: boolean;
  reason: string | null;
}

function normalizeIds(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  if (!value.every((item) => typeof item === "string" && item.length > 0)) return null;
  return Array.from(new Set(value)).sort();
}

/** Read without rewriting or clearing malformed bytes. */
export function readCollectionFavoritesSnapshot(): CollectionFavoritesSnapshot {
  try {
    const raw = window.localStorage.getItem(COLLECTION_FAVORITES_STORAGE_KEY);
    if (raw === null) {
      return { schemaVersion: 1, ids: [], unsupported: false, reason: null };
    }
    const ids = normalizeIds(JSON.parse(raw));
    if (ids === null) {
      return {
        schemaVersion: 1,
        ids: [],
        unsupported: true,
        reason: "Collection favorites contain an unsupported or malformed value and were left untouched.",
      };
    }
    return { schemaVersion: 1, ids, unsupported: false, reason: null };
  } catch {
    return {
      schemaVersion: 1,
      ids: [],
      unsupported: true,
      reason: "Collection favorites could not be read and were left untouched.",
    };
  }
}

export function readCollectionFavorites(): string[] {
  return readCollectionFavoritesSnapshot().ids;
}

export function writeCollectionFavorites(ids: string[]): void {
  const normalized = normalizeIds(ids);
  if (normalized === null) throw new Error("Collection favorites are invalid.");
  window.localStorage.setItem(COLLECTION_FAVORITES_STORAGE_KEY, JSON.stringify(normalized));
}
