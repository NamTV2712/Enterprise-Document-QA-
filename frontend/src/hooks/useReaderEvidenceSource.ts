import { useEffect, useState } from "react";
import { getCachedChunkDetail } from "../lib/documentCache";
import type { Source } from "../types";

export type ReaderSourceResolutionState =
  | "idle"
  | "resolving"
  | "ready"
  | "stale"
  | "unavailable"
  | "error";

export interface ReaderEvidenceSourceState {
  source: Source | undefined;
  state: ReaderSourceResolutionState;
  reason: string | null;
}

function hasHash(source: Source | undefined): source is Source & { chunk_text_hash: string } {
  return Boolean(source?.chunk_text_hash?.trim());
}

function initialState(source: Source | undefined): ReaderSourceResolutionState {
  if (!source?.chunk_id) return "idle";
  if (hasHash(source)) return "ready";
  if (source.stored_snapshot) return "unavailable";
  return "resolving";
}

/**
 * Resolve only the selected chunk's current detail when a live source lacks
 * its hash. Historical snapshots without a hash remain unavailable; they
 * must not be silently rebound to a newer corpus version.
 */
export function useReaderEvidenceSource(
  documentId: string,
  indexedSource?: Source,
): ReaderEvidenceSourceState {
  const sourceIdentity = indexedSource?.chunk_id ?? indexedSource?.document_id ?? "";
  const sourceHash = indexedSource?.chunk_text_hash ?? "";
  const snapshotState = indexedSource?.stored_snapshot?.snapshot_state ?? "";
  const [state, setState] = useState<ReaderEvidenceSourceState>(() => ({
    source: indexedSource,
    state: initialState(indexedSource),
    reason: null,
  }));

  useEffect(() => {
    let active = true;
    const source = indexedSource;
    setState({ source, state: initialState(source), reason: null });

    if (!source?.chunk_id || hasHash(source)) return () => { active = false; };
    if (source.stored_snapshot) {
      setState({
        source,
        state: "unavailable",
        reason: "The saved source snapshot has no text hash for exact location lookup.",
      });
      return () => { active = false; };
    }

    const controller = new AbortController();
    setState({ source, state: "resolving", reason: null });
    void getCachedChunkDetail(source.chunk_id, controller.signal)
      .then((detail) => {
        if (!active) return;
        if (
          detail.chunk_id !== source.chunk_id
          || detail.document_id !== documentId
          || !detail.chunk_text_hash?.trim()
        ) {
          setState({
            source,
            state: detail.document_id !== documentId ? "stale" : "unavailable",
            reason: detail.document_id !== documentId
              ? "The selected chunk belongs to a different document identity."
              : "The selected chunk has no verifiable text hash.",
          });
          return;
        }
        setState({
          source: {
            ...source,
            ...detail,
            chunk_id: source.chunk_id,
            document_id: source.document_id ?? detail.document_id,
            chunk_text_hash: detail.chunk_text_hash,
          },
          state: "ready",
          reason: null,
        });
      })
      .catch((reason) => {
        if (!active || (reason instanceof DOMException && reason.name === "AbortError")) return;
        setState({
          source,
          state: "error",
          reason: reason instanceof Error ? reason.message : "Could not resolve the selected source detail.",
        });
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [documentId, snapshotState, sourceHash, sourceIdentity]);

  return state.state === "ready" && hasHash(indexedSource)
    ? { ...state, source: indexedSource }
    : state;
}
