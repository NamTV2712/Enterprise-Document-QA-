import { beforeEach, describe, expect, test } from "vitest";
import {
  COLLECTION_FAVORITES_STORAGE_KEY,
  readCollectionFavorites,
  readCollectionFavoritesSnapshot,
  writeCollectionFavorites,
} from "./collectionFavorites";

describe("collectionFavorites", () => {
  beforeEach(() => localStorage.clear());

  test("reads and writes the existing version-one string array", () => {
    writeCollectionFavorites(["collection-2", "collection-1", "collection-1"]);
    expect(readCollectionFavorites()).toEqual(["collection-1", "collection-2"]);
    expect(readCollectionFavoritesSnapshot()).toEqual({
      schemaVersion: 1,
      ids: ["collection-1", "collection-2"],
      unsupported: false,
      reason: null,
    });
  });

  test("reports malformed bytes without clearing them", () => {
    localStorage.setItem(COLLECTION_FAVORITES_STORAGE_KEY, '{"future":2}');
    expect(readCollectionFavoritesSnapshot().unsupported).toBe(true);
    expect(localStorage.getItem(COLLECTION_FAVORITES_STORAGE_KEY)).toBe('{"future":2}');
  });
});
