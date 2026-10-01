import { useCallback, useMemo, useReducer } from "react";
import type { DocumentLocationView, EvidenceBinding, BoundSource } from "../lib/readerLocationView";
import {
  createIdleEvidenceBinding,
  createResolvingEvidenceBinding,
  rejectEvidenceBinding,
  resolveEvidenceBinding,
} from "../lib/readerLocationView";
import type {
  ActiveRepresentation,
  DocumentContextTab,
  SourceFilter,
  WorkbenchLayoutMode,
  WorkbenchPane,
  WorkbenchTarget,
} from "../lib/workbench";

export interface WorkbenchControllerState {
  /** Presentation mode only; the measured layout is supplied by the shell. */
  layoutMode: WorkbenchLayoutMode;
  /** Existing identity-bearing route/citation target, held transiently. */
  target: WorkbenchTarget | null;
  activePane: WorkbenchPane;
  activeRepresentation: ActiveRepresentation;
  sourceFilter: SourceFilter;
  documentContextTab: DocumentContextTab;
  documentFindQuery: string;
  /** DOM id supplied by the invoking surface for focus restoration. */
  focusReturnId: string | null;
  /** Transient selected-source binding status; content is never persisted. */
  evidenceBinding: EvidenceBinding;
}

export interface UseWorkbenchControllerOptions {
  initialLayoutMode?: WorkbenchLayoutMode;
  initialTarget?: WorkbenchTarget | null;
  initialActivePane?: WorkbenchPane;
  initialRepresentation?: ActiveRepresentation;
  initialSourceFilter?: SourceFilter;
  initialDocumentContextTab?: DocumentContextTab;
  initialDocumentFindQuery?: string;
  initialFocusReturnId?: string | null;
}

export type WorkbenchControllerAction =
  | { type: "set-layout-mode"; mode: WorkbenchLayoutMode }
  | { type: "set-target"; target: WorkbenchTarget | null }
  | { type: "set-active-pane"; pane: WorkbenchPane }
  | { type: "set-representation"; representation: ActiveRepresentation }
  | { type: "set-source-filter"; filter: SourceFilter }
  | { type: "set-document-context-tab"; tab: DocumentContextTab }
  | { type: "set-document-find-query"; query: string }
  | { type: "set-focus-return-id"; id: string | null }
  | { type: "clear-focus-return-id" }
  | { type: "begin-evidence-resolution"; generation: number }
  | {
      type: "resolve-evidence";
      generation: number;
      source: BoundSource;
      location?: DocumentLocationView;
    }
  | {
      type: "reject-evidence";
      generation: number;
      state: "stale" | "unavailable" | "error";
      reason: string;
    }
  | { type: "clear-evidence-binding" }
  | { type: "reset-presentation" };

/**
 * Reader presentation belongs to the opened document, rather than to the
 * route object that happened to open it.  Route surfaces can recreate their
 * target object during an ordinary render, and the same document can remount
 * while the workbench changes between inline and modal layouts.  Use the
 * stable document identity so neither case clears a reader in progress.
 */
function documentIdentityForTarget(target: WorkbenchTarget | null): string | null {
  if (!target) return null;
  if (target.kind !== "answer") return `document:${target.documentId}`;

  const documentId = target.source.document_id ?? target.selection.documentId;
  if (documentId) return `document:${documentId}`;

  // An answer can legitimately lack a document id. Its source key is the
  // existing deterministic fallback identity for that case.
  const sourceIdentity = target.source.chunk_id
    ?? target.source.chunk_text_hash
    ?? target.selection.chunkId
    ?? target.selection.sourceKey;
  return `source:${sourceIdentity}`;
}

function initialDocumentContextTabForTarget(target: WorkbenchTarget | null): DocumentContextTab {
  return target?.kind !== "answer" && target?.initialTab === "metadata"
    ? "metadata"
    : "evidence";
}

export function createInitialWorkbenchControllerState(
  options: UseWorkbenchControllerOptions = {},
): WorkbenchControllerState {
  return {
    layoutMode: options.initialLayoutMode ?? "four-pane",
    target: options.initialTarget ?? null,
    activePane: options.initialActivePane ?? "sources",
    activeRepresentation: options.initialRepresentation ?? "structured",
    sourceFilter: options.initialSourceFilter ?? "all",
    documentContextTab: options.initialDocumentContextTab ?? "evidence",
    documentFindQuery: options.initialDocumentFindQuery ?? "",
    focusReturnId: options.initialFocusReturnId ?? null,
    evidenceBinding: createIdleEvidenceBinding(),
  };
}

export function workbenchControllerReducer(
  state: WorkbenchControllerState,
  action: WorkbenchControllerAction,
): WorkbenchControllerState {
  switch (action.type) {
    case "set-layout-mode":
      return state.layoutMode === action.mode
        ? state
        : { ...state, layoutMode: action.mode };
    case "set-target": {
      const identityChanged = documentIdentityForTarget(state.target)
        !== documentIdentityForTarget(action.target);
      return state.target === action.target && state.evidenceBinding.state === "idle"
        ? state
        : {
            ...state,
            target: action.target,
            activePane: action.target?.kind === "answer" ? "sources" : state.activePane,
            // A different document must never inherit a prior document's
            // representation, context tab, or find query.  Preserve those
            // fields for a same-document responsive remount instead.
            activeRepresentation: identityChanged ? "structured" : state.activeRepresentation,
            documentContextTab: identityChanged
              ? initialDocumentContextTabForTarget(action.target)
              : state.documentContextTab,
            documentFindQuery: identityChanged ? "" : state.documentFindQuery,
            evidenceBinding: createIdleEvidenceBinding(),
          };
    }
    case "set-active-pane":
      return state.activePane === action.pane ? state : { ...state, activePane: action.pane };
    case "set-representation":
      return state.activeRepresentation === action.representation
        ? state
        : {
            ...state,
            activeRepresentation: action.representation,
          };
    case "set-source-filter":
      return state.sourceFilter === action.filter ? state : { ...state, sourceFilter: action.filter };
    case "set-document-context-tab":
      return state.documentContextTab === action.tab
        ? state
        : { ...state, documentContextTab: action.tab };
    case "set-document-find-query":
      return state.documentFindQuery === action.query
        ? state
        : { ...state, documentFindQuery: action.query };
    case "set-focus-return-id":
      return state.focusReturnId === action.id ? state : { ...state, focusReturnId: action.id };
    case "clear-focus-return-id":
      return state.focusReturnId === null ? state : { ...state, focusReturnId: null };
    case "begin-evidence-resolution":
      return {
        ...state,
        evidenceBinding: createResolvingEvidenceBinding(action.generation),
      };
    case "resolve-evidence":
      {
        const evidenceBinding = resolveEvidenceBinding(
          state.evidenceBinding,
          action.generation,
          action.source,
          action.location,
        );
        return evidenceBinding === state.evidenceBinding ? state : { ...state, evidenceBinding };
      }
    case "reject-evidence":
      {
        const evidenceBinding = rejectEvidenceBinding(
          state.evidenceBinding,
          action.generation,
          action.state,
          action.reason,
        );
        return evidenceBinding === state.evidenceBinding ? state : { ...state, evidenceBinding };
      }
    case "clear-evidence-binding":
      return state.evidenceBinding.state === "idle"
        ? state
        : { ...state, evidenceBinding: createIdleEvidenceBinding() };
    case "reset-presentation":
      return {
        ...state,
        activePane: "sources",
        activeRepresentation: "structured",
        sourceFilter: "all",
        documentContextTab: "evidence",
        documentFindQuery: "",
        focusReturnId: null,
        evidenceBinding: createIdleEvidenceBinding(),
      };
  }
}

export interface WorkbenchController {
  state: WorkbenchControllerState;
  dispatch: (action: WorkbenchControllerAction) => void;
  setLayoutMode: (mode: WorkbenchLayoutMode) => void;
  setTarget: (target: WorkbenchTarget | null) => void;
  setActivePane: (pane: WorkbenchPane) => void;
  setRepresentation: (representation: ActiveRepresentation) => void;
  setSourceFilter: (filter: SourceFilter) => void;
  setDocumentContextTab: (tab: DocumentContextTab) => void;
  setDocumentFindQuery: (query: string) => void;
  rememberFocus: (id: string | null) => void;
  clearFocusReturn: () => void;
  beginEvidenceResolution: (generation: number) => void;
  resolveEvidence: (
    generation: number,
    source: BoundSource,
    location?: DocumentLocationView,
  ) => void;
  rejectEvidence: (
    generation: number,
    state: "stale" | "unavailable" | "error",
    reason: string,
  ) => void;
  clearEvidenceBinding: () => void;
  resetPresentation: () => void;
}

/**
 * Owns only workbench presentation/coordination state. Research, evidence
 * persistence, source identity, and reader transport remain in their existing
 * owners and are passed through this seam by reference.
 */
export function useWorkbenchController(
  options: UseWorkbenchControllerOptions = {},
): WorkbenchController {
  const [state, dispatch] = useReducer(
    workbenchControllerReducer,
    options,
    createInitialWorkbenchControllerState,
  );

  const setLayoutMode = useCallback((mode: WorkbenchLayoutMode) => {
    dispatch({ type: "set-layout-mode", mode });
  }, []);
  const setTarget = useCallback((target: WorkbenchTarget | null) => {
    dispatch({ type: "set-target", target });
  }, []);
  const setActivePane = useCallback((pane: WorkbenchPane) => {
    dispatch({ type: "set-active-pane", pane });
  }, []);
  const setRepresentation = useCallback((representation: ActiveRepresentation) => {
    dispatch({ type: "set-representation", representation });
  }, []);
  const setSourceFilter = useCallback((filter: SourceFilter) => {
    dispatch({ type: "set-source-filter", filter });
  }, []);
  const setDocumentContextTab = useCallback((tab: DocumentContextTab) => {
    dispatch({ type: "set-document-context-tab", tab });
  }, []);
  const setDocumentFindQuery = useCallback((query: string) => {
    dispatch({ type: "set-document-find-query", query });
  }, []);
  const rememberFocus = useCallback((id: string | null) => {
    dispatch({ type: "set-focus-return-id", id });
  }, []);
  const clearFocusReturn = useCallback(() => {
    dispatch({ type: "clear-focus-return-id" });
  }, []);
  const beginEvidenceResolution = useCallback((generation: number) => {
    dispatch({ type: "begin-evidence-resolution", generation });
  }, []);
  const resolveEvidence = useCallback(
    (generation: number, source: BoundSource, location?: DocumentLocationView) => {
      dispatch({ type: "resolve-evidence", generation, source, location });
    },
    [],
  );
  const rejectEvidence = useCallback(
    (generation: number, bindingState: "stale" | "unavailable" | "error", reason: string) => {
      dispatch({ type: "reject-evidence", generation, state: bindingState, reason });
    },
    [],
  );
  const clearEvidenceBinding = useCallback(() => {
    dispatch({ type: "clear-evidence-binding" });
  }, []);
  const resetPresentation = useCallback(() => {
    dispatch({ type: "reset-presentation" });
  }, []);

  return useMemo(
    () => ({
      state,
      dispatch,
      setLayoutMode,
      setTarget,
      setActivePane,
      setRepresentation,
      setSourceFilter,
      setDocumentContextTab,
      setDocumentFindQuery,
      rememberFocus,
      clearFocusReturn,
      beginEvidenceResolution,
      resolveEvidence,
      rejectEvidence,
      clearEvidenceBinding,
      resetPresentation,
    }),
    [
      beginEvidenceResolution,
      clearEvidenceBinding,
      clearFocusReturn,
      dispatch,
      rememberFocus,
      rejectEvidence,
      resetPresentation,
      resolveEvidence,
      setActivePane,
      setDocumentContextTab,
      setDocumentFindQuery,
      setLayoutMode,
      setRepresentation,
      setSourceFilter,
      setTarget,
      state,
    ],
  );
}
