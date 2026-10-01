import type { EvidenceSelection } from "../types";

/**
 * URL-safe presentation of an evidence selection. The source itself is not
 * serialized into the URL; source identity remains resolved from the active
 * answer/variant and current repository data.
 */
export interface EvidenceDeepLink {
  messageId: string;
  citationIndex: number;
  variantId: string | null;
  conversationId: string | null;
  sourceKey: string | null;
}

export type EvidenceDeepLinkInput = Omit<EvidenceDeepLink, "variantId" | "conversationId" | "sourceKey"> & {
  variantId?: string | null;
  conversationId?: string | null;
  sourceKey?: string | null;
};

function nonEmpty(value: string | null | undefined): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function decodePart(value: string): string | null {
  try {
    return nonEmpty(decodeURIComponent(value));
  } catch {
    return null;
  }
}

function readOptionalParam(
  params: URLSearchParams,
  ...keys: string[]
): string | null {
  for (const key of keys) {
    const value = nonEmpty(params.get(key));
    if (value !== null) return value;
  }
  return null;
}

/**
 * Build the backwards-compatible evidence hash. The legacy base form stays
 * `#evidence=<message>-<citation>`; variant/conversation/source identity is
 * added as encoded query parameters only when present.
 */
export function buildEvidenceDeepLink(
  input: EvidenceDeepLinkInput,
): string | null {
  if (
    !nonEmpty(input.messageId) ||
    !Number.isSafeInteger(input.citationIndex) ||
    input.citationIndex < 0
  ) {
    return null;
  }

  const params = new URLSearchParams();
  if (nonEmpty(input.conversationId)) params.set("conversationId", input.conversationId!);
  if (nonEmpty(input.variantId)) params.set("variantId", input.variantId!);
  if (nonEmpty(input.sourceKey)) params.set("sourceKey", input.sourceKey!);

  const base = `#evidence=${encodeURIComponent(input.messageId)}-${input.citationIndex}`;
  const query = params.toString();
  return query ? `${base}?${query}` : base;
}

export function parseEvidenceDeepLink(
  hash: string,
): EvidenceDeepLink | null {
  if (typeof hash !== "string") return null;
  const fragment = hash.startsWith("#") ? hash.slice(1) : hash;
  const queryIndex = fragment.indexOf("?");
  const base = queryIndex >= 0 ? fragment.slice(0, queryIndex) : fragment;
  const query = queryIndex >= 0 ? fragment.slice(queryIndex + 1) : "";
  const match = base.match(/^evidence=(.+)-(\d+)$/);
  if (!match) return null;

  const messageId = decodePart(match[1]);
  const citationIndex = Number(match[2]);
  if (
    messageId === null ||
    !Number.isSafeInteger(citationIndex) ||
    citationIndex < 0
  ) {
    return null;
  }

  let params: URLSearchParams;
  try {
    params = new URLSearchParams(query);
  } catch {
    return null;
  }

  return {
    messageId,
    citationIndex,
    // Accept the short names used by an early V5 prototype as well as the
    // explicit canonical names. This keeps old copied links resolvable.
    conversationId: readOptionalParam(params, "conversationId", "conversation"),
    variantId: readOptionalParam(params, "variantId", "variant"),
    sourceKey: readOptionalParam(params, "sourceKey", "source"),
  };
}

export function evidenceDeepLinkFromSelection(
  selection: EvidenceSelection,
): EvidenceDeepLink {
  return {
    messageId: selection.messageId,
    citationIndex: selection.citationIndex,
    variantId: selection.variantId ?? null,
    conversationId: selection.conversationId,
    sourceKey: selection.sourceKey,
  };
}

export function buildEvidenceDeepLinkForSelection(
  selection: EvidenceSelection,
): string | null {
  return buildEvidenceDeepLink(evidenceDeepLinkFromSelection(selection));
}

// Explicit aliases make the serialization/parsing boundary readable at call
// sites without maintaining a second implementation.
export const serializeEvidenceDeepLink = buildEvidenceDeepLink;
export const parseEvidenceHash = parseEvidenceDeepLink;
