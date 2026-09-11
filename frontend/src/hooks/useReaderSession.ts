import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export interface ReaderSessionTarget {
  conversationId?: string | null;
  messageId?: string | null;
  variantId?: string | null;
  documentId?: string | null;
  sourceKey?: string | null;
  representation?: "indexed" | "normalized" | "structured";
}

export interface ReaderSessionSnapshot {
  generation: number;
  target: ReaderSessionTarget | null;
  signal: AbortSignal;
}

export interface ReaderSessionController {
  snapshot: ReaderSessionSnapshot | null;
  select: (target: ReaderSessionTarget | null) => number;
  clear: () => void;
  isCurrent: (generation: number, target?: ReaderSessionTarget | null) => boolean;
}

function sameTarget(left: ReaderSessionTarget | null, right: ReaderSessionTarget | null): boolean {
  if (left === right) return true;
  if (!left || !right) return false;
  return left.conversationId === right.conversationId
    && left.messageId === right.messageId
    && left.variantId === right.variantId
    && left.documentId === right.documentId
    && left.sourceKey === right.sourceKey
    && left.representation === right.representation;
}

/**
 * The mounted App owns the active reader generation. Every representation
 * uses the same generation so a late source/content/location response cannot
 * paint underneath a newer filing selection.
 */
export function useReaderSession(): ReaderSessionController {
  const generationRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const targetRef = useRef<ReaderSessionTarget | null>(null);
  const snapshotRef = useRef<ReaderSessionSnapshot | null>(null);
  const [snapshot, setSnapshot] = useState<ReaderSessionSnapshot | null>(null);

  const select = useCallback((target: ReaderSessionTarget | null): number => {
    if (sameTarget(targetRef.current, target) && snapshotRef.current?.generation) {
      return snapshotRef.current.generation;
    }
    controllerRef.current?.abort();
    const generation = ++generationRef.current;
    const controller = new AbortController();
    targetRef.current = target;
    controllerRef.current = controller;
    const nextSnapshot = { generation, target, signal: controller.signal };
    snapshotRef.current = nextSnapshot;
    setSnapshot(nextSnapshot);
    return generation;
  }, []);

  const clear = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    targetRef.current = null;
    const generation = ++generationRef.current;
    snapshotRef.current = null;
    setSnapshot(null);
    return generation;
  }, []);

  const isCurrent = useCallback((generation: number, target?: ReaderSessionTarget | null): boolean => {
    const snapshotValue = snapshotRef.current;
    return Boolean(
      snapshotValue
      && snapshotValue.generation === generation
      && !snapshotValue.signal.aborted
      && (target === undefined || sameTarget(snapshotValue.target, target)),
    );
  }, []);

  useEffect(() => () => {
    controllerRef.current?.abort();
    controllerRef.current = null;
  }, []);

  return useMemo(() => ({ snapshot, select, clear, isCurrent }), [clear, isCurrent, select, snapshot]);
}
