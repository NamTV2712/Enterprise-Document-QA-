import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";

export interface ResearchScope {
  ticker: string | null;
  section: string | null;
  topK: number;
  enableComparative: boolean;
}

type ScopePatch = Partial<ResearchScope>;

interface ScopeState {
  conversationId: string;
  scope: ResearchScope;
}

type ScopeAction =
  | { type: "replace"; conversationId: string; scope: ResearchScope }
  | { type: "patch"; conversationId: string; patch: ScopePatch };

const DEFAULT_SCOPE: ResearchScope = {
  ticker: null,
  section: null,
  topK: 5,
  enableComparative: true,
};

const DEFAULT_CONVERSATION_ID = "draft";
const SCOPE_STORAGE_PREFIX = "sec_qa_research_scope_v1:";

function clampTopK(value: number): number {
  return Math.max(1, Math.min(10, Math.round(value)));
}

function normalizeScope(value: unknown): ResearchScope | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<ResearchScope>;
  if (
    !(
      candidate.ticker === null ||
      candidate.ticker === undefined ||
      typeof candidate.ticker === "string"
    ) ||
    !(
      candidate.section === null ||
      candidate.section === undefined ||
      typeof candidate.section === "string"
    ) ||
    (candidate.topK !== undefined &&
      (typeof candidate.topK !== "number" || !Number.isFinite(candidate.topK))) ||
    (candidate.enableComparative !== undefined &&
      typeof candidate.enableComparative !== "boolean")
  ) {
    return null;
  }

  return {
    ticker: typeof candidate.ticker === "string" && candidate.ticker.trim() ? candidate.ticker : null,
    section: typeof candidate.section === "string" && candidate.section.trim() ? candidate.section : null,
    topK: clampTopK(candidate.topK ?? DEFAULT_SCOPE.topK),
    enableComparative: candidate.enableComparative ?? DEFAULT_SCOPE.enableComparative,
  };
}

function scopeStorageKey(conversationId: string): string {
  return `${SCOPE_STORAGE_PREFIX}${conversationId}`;
}

function readStoredScope(conversationId: string): ResearchScope | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(scopeStorageKey(conversationId));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const payload = parsed as { version?: unknown; scope?: unknown };
    if (payload.version !== 1) return null;
    return normalizeScope(payload.scope);
  } catch {
    return null;
  }
}

function writeStoredScope(conversationId: string, scope: ResearchScope): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      scopeStorageKey(conversationId),
      JSON.stringify({ version: 1, scope }),
    );
  } catch {
    // Scope persistence is best-effort; conversation storage remains the
    // source of truth for the question and messages.
  }
}

function scopeReducer(state: ScopeState, action: ScopeAction): ScopeState {
  if (action.type === "replace") return action;
  if (action.conversationId !== state.conversationId) return state;

  const next = { ...state.scope, ...action.patch };
  if (action.patch.topK !== undefined) next.topK = clampTopK(action.patch.topK);
  return { ...state, scope: next };
}

function createInitialState(
  conversationId: string,
  initial: Partial<ResearchScope>,
): ScopeState {
  const fallback = normalizeScope({ ...DEFAULT_SCOPE, ...initial }) ?? DEFAULT_SCOPE;
  return {
    conversationId,
    scope: readStoredScope(conversationId) ?? fallback,
  };
}

/**
 * One owner for the retrieval constraints attached to the current research
 * draft. Question text remains in the conversation library; this hook keeps
 * its scope under the same conversation identity so a reload or conversation
 * switch cannot pair a draft with an unrelated filter set.
 */
export function useResearchDraft(initial?: Partial<ResearchScope>): ReturnType<typeof useResearchDraftImpl>;
export function useResearchDraft(
  conversationId?: string,
  initial?: Partial<ResearchScope>,
  isReady?: boolean,
): ReturnType<typeof useResearchDraftImpl>;
export function useResearchDraft(
  conversationOrInitial: string | Partial<ResearchScope> = DEFAULT_CONVERSATION_ID,
  initialOrReady: Partial<ResearchScope> | boolean = {},
  ready = true,
) {
  const conversationId = typeof conversationOrInitial === "string"
    ? conversationOrInitial
    : DEFAULT_CONVERSATION_ID;
  const initial = typeof conversationOrInitial === "string"
    ? (typeof initialOrReady === "object" ? initialOrReady : {})
    : conversationOrInitial;
  const isReady = typeof conversationOrInitial === "string"
    ? (typeof initialOrReady === "boolean" ? initialOrReady : ready)
    : true;

  return useResearchDraftImpl(conversationId, initial, isReady);
}

function useResearchDraftImpl(
  conversationId: string,
  initial: Partial<ResearchScope>,
  isReady: boolean,
) {
  const [state, dispatch] = useReducer(
    scopeReducer,
    { conversationId, initial },
    ({ conversationId: id, initial: seed }) => createInitialState(id, seed),
  );
  const stateRef = useRef(state);
  stateRef.current = state;
  const previousConversationIdRef = useRef(conversationId);
  const userPatchedRef = useRef(false);
  const hydratedKeyRef = useRef<string | null>(null);
  const hydrationPendingRef = useRef(false);

  if (previousConversationIdRef.current !== conversationId) {
    previousConversationIdRef.current = conversationId;
    userPatchedRef.current = false;
  }

  const fallbackScope = useMemo(
    () => normalizeScope({ ...DEFAULT_SCOPE, ...initial }) ?? DEFAULT_SCOPE,
    [initial.enableComparative, initial.section, initial.ticker, initial.topK],
  );
  const initialSignature = JSON.stringify(fallbackScope);
  const hydrationKey = `${conversationId}:${initialSignature}`;

  useEffect(() => {
    if (!isReady || hydratedKeyRef.current === hydrationKey) return;

    hydratedKeyRef.current = hydrationKey;
    const stored = readStoredScope(conversationId);
    const stateMatchesConversation = stateRef.current.conversationId === conversationId;
    const nextScope = stored ?? (userPatchedRef.current && stateMatchesConversation
      ? stateRef.current.scope
      : fallbackScope);

    hydrationPendingRef.current = !stored && stateMatchesConversation && userPatchedRef.current
      ? false
      : true;
    dispatch({ type: "replace", conversationId, scope: nextScope });
  }, [conversationId, fallbackScope, hydrationKey, isReady]);

  useEffect(() => {
    if (!isReady) return;
    if (hydrationPendingRef.current) {
      hydrationPendingRef.current = false;
      return;
    }
    if (state.conversationId !== conversationId || hydratedKeyRef.current !== hydrationKey) return;
    writeStoredScope(conversationId, state.scope);
  }, [conversationId, hydrationKey, isReady, state]);

  const patchScope = useCallback((patch: ScopePatch) => {
    userPatchedRef.current = true;
    dispatch({ type: "patch", conversationId, patch });
  }, [conversationId]);
  const setTicker = useCallback((ticker: string | null) => patchScope({ ticker }), [patchScope]);
  const setSection = useCallback((section: string | null) => patchScope({ section }), [patchScope]);
  const setTopK = useCallback((topK: number) => patchScope({ topK }), [patchScope]);
  const setEnableComparative = useCallback(
    (enableComparative: boolean) => patchScope({ enableComparative }),
    [patchScope],
  );

  return useMemo(
    () => ({
      scope: state.conversationId === conversationId ? state.scope : fallbackScope,
      patchScope,
      setTicker,
      setSection,
      setTopK,
      setEnableComparative,
    }),
    [conversationId, fallbackScope, patchScope, setEnableComparative, setSection, setTicker, setTopK, state],
  );
}
