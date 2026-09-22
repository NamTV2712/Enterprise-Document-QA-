import type { EvidenceLocation, OriginalLocation, PdfEvidenceLocation, Source } from "../types";

/** A representation-neutral view while retaining the original API response. */
export type DocumentLocationView =
  | { representation: "structured"; raw: EvidenceLocation }
  | { representation: "normalized"; raw: OriginalLocation }
  | { representation: "pdf"; raw: PdfEvidenceLocation };

export type ReaderLocationStatus =
  | "exact"
  | "ambiguous"
  | "not_found"
  | "unavailable"
  | "stale";

export interface LocationValidationTarget {
  documentId: string;
  chunkId: string;
  chunkTextHash: string;
  sourceSetRevision: string;
  /** Optional when the reader-location response is allowed to choose a companion source. */
  sourceDocumentId?: string | null;
  /** Optional when the reader-location response is allowed to choose a companion revision. */
  documentRevision?: string | null;
}

export interface LocationValidation {
  ok: boolean;
  state: "ready" | "stale" | "unavailable";
  reason: string | null;
}

export type ReaderLocationEvent =
  | { state: "resolving"; generation: number; source: Source }
  | { state: "resolved"; generation: number; source: Source; location: DocumentLocationView }
  | { state: "stale" | "unavailable" | "error"; generation: number; source: Source; reason: string };

/**
 * The selected source remains the source of truth for identity. This bound
 * shape only carries the facts needed by the presentation coordinator and
 * never persists source content.
 */
export interface BoundSource {
  source: Source;
  chunkId: string | null;
  chunkTextHash: string | null;
  documentId: string | null;
  sourceDocumentId: string | null;
  sourceSetRevision: string | null;
  documentRevision: string | null;
  representationRevision: string | null;
}

export type EvidenceBinding =
  | { state: "idle" }
  | { state: "resolving"; generation: number }
  | { state: "ready"; source: BoundSource; location?: DocumentLocationView }
  | { state: "stale"; reason: string }
  | { state: "unavailable"; reason: string }
  | { state: "error"; reason: string };

export function toDocumentLocationView(
  representation: "structured",
  raw: EvidenceLocation,
): DocumentLocationView;
export function toDocumentLocationView(
  representation: "normalized",
  raw: OriginalLocation,
): DocumentLocationView;
export function toDocumentLocationView(
  representation: "pdf",
  raw: PdfEvidenceLocation,
): DocumentLocationView;
export function toDocumentLocationView(
  representation: "structured" | "normalized" | "pdf",
  raw: EvidenceLocation | OriginalLocation | PdfEvidenceLocation,
): DocumentLocationView {
  if (representation === "structured") return { representation, raw: raw as EvidenceLocation };
  if (representation === "normalized") return { representation, raw: raw as OriginalLocation };
  return { representation, raw: raw as PdfEvidenceLocation };
}

/**
 * Bind only metadata already present on a Source. Missing provenance facts
 * stay null; this function never guesses a source-document identity.
 */
export function bindSource(source: Source, location?: DocumentLocationView): BoundSource {
  const snapshot = source.stored_snapshot;
  let locationSourceDocumentId: string | null = null;
  let locationDocumentRevision: string | null = null;
  let locationSourceSetRevision: string | null = null;
  let representationRevision: string | null = null;
  if (location?.representation === "structured") {
    locationSourceDocumentId = location.raw.source_document_id;
    locationDocumentRevision = location.raw.document_revision;
    locationSourceSetRevision = location.raw.source_set_revision;
    representationRevision = location.raw.representation_revision;
  } else if (location?.representation === "normalized") {
    locationSourceSetRevision = location.raw.source_set_revision;
    locationSourceDocumentId = location.raw.location?.source_document_id ?? null;
    locationDocumentRevision = location.raw.location?.document_revision ?? null;
  } else if (location?.representation === "pdf") {
    locationSourceSetRevision = location.raw.source_set_revision;
    locationSourceDocumentId = location.raw.source_document_id;
    locationDocumentRevision = location.raw.document_revision;
  }
  return {
    source,
    chunkId: source.chunk_id ?? snapshot?.chunk_id ?? null,
    chunkTextHash: source.chunk_text_hash ?? null,
    documentId: source.document_id ?? null,
    sourceDocumentId: locationSourceDocumentId ?? null,
    sourceSetRevision: locationSourceSetRevision ?? snapshot?.source_set_revision ?? null,
    documentRevision: locationDocumentRevision ?? snapshot?.document_revision ?? null,
    representationRevision: representationRevision ?? null,
  };
}

function mismatchReason(): string {
  return "The reader location no longer matches the selected source identity.";
}

function unavailableReason(): string {
  return "The selected source has no verifiable location in this representation.";
}

/**
 * Validate the identity envelope before a reader can paint a highlight. A
 * non-exact response may still be rendered as a truthful status, but it can
 * never authorize an approximate range.
 */
export function validateDocumentLocation(
  location: DocumentLocationView,
  target: LocationValidationTarget,
): LocationValidation {
  if (location.representation === "structured") {
    const raw = location.raw;
    if (
      raw.chunk_id !== target.chunkId
      || raw.chunk_text_hash !== target.chunkTextHash
      || raw.document_id !== target.documentId
      || raw.source_set_revision !== target.sourceSetRevision
    ) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
    if (target.sourceDocumentId && raw.source_document_id !== target.sourceDocumentId) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
    if (raw.status === "exact" && (
      !raw.source_document_id
      || !raw.document_revision
      || !raw.representation_revision
      || raw.ranges.length === 0
    )) {
      return { ok: false, state: "unavailable", reason: unavailableReason() };
    }
    if (target.documentRevision && raw.document_revision && raw.document_revision !== target.documentRevision) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
  } else if (location.representation === "normalized") {
    const raw = location.raw;
    if (
      raw.chunk_id !== target.chunkId
      || raw.chunk_text_hash !== target.chunkTextHash
      || raw.document_id !== target.documentId
      || raw.source_set_revision !== target.sourceSetRevision
    ) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
    if (target.sourceDocumentId && raw.location?.source_document_id !== target.sourceDocumentId) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
    if (raw.status !== "exact") return { ok: true, state: "ready", reason: null };
    if (!raw.location || !raw.location.source_document_id || !raw.location.document_revision) {
      return { ok: false, state: "unavailable", reason: unavailableReason() };
    }
    if (target.documentRevision && raw.location.document_revision !== target.documentRevision) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
  } else {
    const raw = location.raw;
    if (
      raw.chunk_id !== target.chunkId
      || raw.chunk_text_hash !== target.chunkTextHash
      || raw.document_id !== target.documentId
      || raw.source_set_revision !== target.sourceSetRevision
    ) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
    if (target.sourceDocumentId && raw.source_document_id !== target.sourceDocumentId) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
    if (target.documentRevision && raw.document_revision !== target.documentRevision) {
      return { ok: false, state: "stale", reason: mismatchReason() };
    }
    if (raw.status === "exact" && (!raw.artifact_key || !raw.artifact_hash || raw.rects.length === 0)) {
      return { ok: false, state: "unavailable", reason: unavailableReason() };
    }
  }

  return { ok: true, state: "ready", reason: null };
}

export function getDocumentLocationMessage(
  location: DocumentLocationView,
  vi = false,
): string {
  const status = location.raw.status;
  if (status === "exact") return vi
    ? "Evidence đã được xác minh trong biểu diễn tài liệu này."
    : "Evidence correspondence verified in this document representation.";
  if (status === "ambiguous") return vi
    ? "Không đánh dấu evidence vì đoạn được chọn khớp nhiều vị trí."
    : "Evidence is not highlighted because the selected text maps to multiple locations.";
  if (status === "not_found") return vi
    ? "Không tìm thấy toàn bộ chunk trong biểu diễn tài liệu này."
    : "The full indexed chunk was not found in this document representation.";
  if (status === "stale") return vi
    ? "Phiên bản tài liệu đã thay đổi; evidence vẫn được giữ nhưng không được đánh dấu."
    : "The document revision changed; the source remains selected but is not highlighted.";
  return vi
    ? "Không thể xác minh vị trí evidence trong biểu diễn tài liệu này."
    : "Evidence location is unavailable in this document representation.";
}

export function getDocumentLocationErrorMessage(
  error: unknown,
  vi = false,
): string | null {
  const candidate = error && typeof error === "object"
    ? error as { status?: unknown; code?: unknown }
    : {};
  if (candidate.code === "source_changed" || candidate.status === 409) return vi
    ? "Phiên bản nguồn đã thay đổi; evidence vẫn được giữ nhưng không được đánh dấu."
    : "The source revision changed; the source remains selected but is not highlighted.";
  if (candidate.code === "chunk_changed") return vi
    ? "Chunk đã thay đổi; evidence vẫn được giữ nhưng không được đánh dấu."
    : "The indexed chunk changed; the source remains selected but is not highlighted.";
  if (candidate.status === 404) return vi
    ? "Không tìm thấy vị trí evidence trong biểu diễn tài liệu này."
    : "The evidence location was not found in this document representation.";
  return null;
}

export function getDocumentLocationStatus(
  location: DocumentLocationView,
): ReaderLocationStatus {
  return location.raw.status;
}

export function isExactDocumentLocation(
  location: DocumentLocationView | undefined,
): boolean {
  return location?.raw.status === "exact";
}

/** Return a useful text offset when the selected representation exposes one. */
export function getDocumentLocationOffsets(
  location: DocumentLocationView,
): { start: number; end: number } | null {
  if (location.representation === "normalized") {
    const mapped = location.raw.location;
    return mapped ? { start: mapped.start, end: mapped.end } : null;
  }

  if (location.representation === "pdf") return null;

  const firstRange = location.raw.ranges[0];
  return firstRange ? { start: firstRange.start, end: firstRange.end } : null;
}

export function createIdleEvidenceBinding(): EvidenceBinding {
  return { state: "idle" };
}

export function createResolvingEvidenceBinding(generation: number): EvidenceBinding {
  return {
    state: "resolving",
    generation: Math.max(0, Math.floor(generation)),
  };
}

export function createReadyEvidenceBinding(
  source: BoundSource,
  location?: DocumentLocationView,
): EvidenceBinding {
  return location ? { state: "ready", source, location } : { state: "ready", source };
}

export function createStaleEvidenceBinding(reason: string): EvidenceBinding {
  return { state: "stale", reason };
}

export function createUnavailableEvidenceBinding(reason: string): EvidenceBinding {
  return { state: "unavailable", reason };
}

export function createErrorEvidenceBinding(reason: string): EvidenceBinding {
  return { state: "error", reason };
}

export function isEvidenceResolutionCurrent(
  binding: EvidenceBinding,
  generation: number,
): boolean {
  return binding.state === "resolving" && binding.generation === generation;
}

/**
 * Guard a location response against a newer target or representation. A
 * response from any other generation is ignored by returning the current
 * state unchanged.
 */
export function resolveEvidenceBinding(
  current: EvidenceBinding,
  generation: number,
  source: BoundSource,
  location?: DocumentLocationView,
): EvidenceBinding {
  return isEvidenceResolutionCurrent(current, generation)
    ? createReadyEvidenceBinding(source, location)
    : current;
}

export function rejectEvidenceBinding(
  current: EvidenceBinding,
  generation: number,
  state: "stale" | "unavailable" | "error",
  reason: string,
): EvidenceBinding {
  if (!isEvidenceResolutionCurrent(current, generation)) return current;
  if (state === "stale") return createStaleEvidenceBinding(reason);
  if (state === "unavailable") return createUnavailableEvidenceBinding(reason);
  return createErrorEvidenceBinding(reason);
}
