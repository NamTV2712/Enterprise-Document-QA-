import { Source } from "../types";

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

function readCollections(): EvidenceCollection[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((collection): collection is EvidenceCollection => Boolean(
      collection && typeof collection === "object" && typeof collection.id === "string" && typeof collection.name === "string" && Array.isArray(collection.items),
    ));
  } catch {
    return [];
  }
}

function writeCollections(collections: EvidenceCollection[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(collections));
    window.dispatchEvent(new Event("sec-qa-evidence-updated"));
  } catch { /* local-only convenience must not break research */ }
}

export function listEvidenceCollections(): EvidenceCollection[] {
  return readCollections().sort((a, b) => b.updatedAt - a.updatedAt);
}

export function createEvidenceCollection(name: string): EvidenceCollection {
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
  const collections = readCollections();
  let collection = collections.find((item) => item.id === options.collectionId) ?? collections[0];
  if (!collection) collection = createEvidenceCollection("Research evidence");
  const items = collection.items.filter((item) => item.chunkId !== source.chunk_id || item.citation !== source.citation);
  if (items.length >= MAX_ITEMS_PER_COLLECTION) throw new Error("Collection item limit reached");
  const item: EvidenceItem = { id: `evidence-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, citation: source.citation, excerpt: source.text || source.text_preview, chunkId: source.chunk_id, ticker: source.ticker, section: source.section, filingDate: source.filing_date, sourceConversationId: options.conversationId, sourceMessageId: options.messageId, savedAt: Date.now() };
  const next = { ...collection, items: [...items, item], updatedAt: Date.now() };
  writeCollections(collections.some((item) => item.id === collection?.id) ? collections.map((item) => item.id === next.id ? next : item) : [...collections, next]);
  return next;
}

export function clearEvidenceCollections(): void {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore unavailable storage */ }
}
