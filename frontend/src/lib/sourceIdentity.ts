import { EvidenceSelection, Source } from "../types";

function normalizePart(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function encodePart(value: string | null | undefined): string {
  return encodeURIComponent(normalizePart(value));
}

/**
 * Return a stable key without inventing a backend identifier.
 * Backend IDs win; metadata and finally the stored excerpt provide the
 * conservative fallback for legacy responses that have no IDs.
 */
export function getSourceKey(source: Source): string {
  if (normalizePart(source.chunk_id)) return `chunk:${encodePart(source.chunk_id)}`;
  if (normalizePart(source.document_id)) {
    return [
      "document",
      encodePart(source.document_id),
      encodePart(source.citation),
      encodePart(source.ticker),
      encodePart(source.section),
      encodePart(source.filing_date),
    ].join("|");
  }
  return [
    "excerpt",
    encodePart(source.citation),
    encodePart(source.ticker),
    encodePart(source.section),
    encodePart(source.filing_date),
    encodePart(source.text || source.text_preview),
  ].join("|");
}

export function createEvidenceSelection(
  conversationId: string,
  messageId: string,
  citationIndex: number,
  source: Source,
  variantId?: string,
): EvidenceSelection {
  return {
    conversationId,
    messageId,
    ...(variantId ? { variantId } : {}),
    citationIndex,
    ...(source.chunk_id ? { chunkId: source.chunk_id } : {}),
    ...(source.document_id ? { documentId: source.document_id } : {}),
    sourceKey: getSourceKey(source),
  };
}

/**
 * Match only the requested citation slot and its immutable identity. Never
 * search another source as a fallback when the selected source disappears.
 */
export function sourceMatchesSelection(
  source: Source | undefined,
  selection: EvidenceSelection,
  citationIndex: number,
): boolean {
  if (!source || citationIndex !== selection.citationIndex) return false;
  if (getSourceKey(source) !== selection.sourceKey) return false;
  if (selection.chunkId && source.chunk_id !== selection.chunkId) return false;
  if (selection.documentId && source.document_id !== selection.documentId) return false;
  return true;
}
